#include "ns3/test.h"
#include "ns3/quic-socket-tx-buffer.h"
#include "ns3/quic-socket-tx-scheduler.h"
#include "ns3/quic-subheader.h"
#include <vector>

using namespace ns3;

static Ptr<Packet> DataFrame (uint64_t stream, uint32_t offset, uint32_t size,
                              bool fin = false, bool length = true)
{
  std::vector<uint8_t> bytes (size);
  for (uint32_t i = 0; i < size; ++i) bytes[i] = (offset + i) % 251;
  Ptr<Packet> packet = size ? Create<Packet> (bytes.data (), size) : Create<Packet> ();
  packet->AddHeader (QuicSubheader::CreateStreamSubHeader (
    stream, offset, size, offset != 0, length, fin));
  return packet;
}

class RetransmissionFramesTest : public TestCase
{
public:
  RetransmissionFramesTest () : TestCase ("Mixed retransmission frames preserve controls, bytes and empty FIN") {}
  void DoRun () override
  {
    QuicSocketTxScheduler scheduler;
    Ptr<QuicSocketTxItem> item = CreateObject<QuicSocketTxItem> ();
    item->m_isStream = true;
    item->m_packet = DataFrame (1, 0, 63);
    std::vector<uint32_t> gaps, blocks;
    Ptr<Packet> control = Create<Packet> ();
    control->AddHeader (QuicSubheader::CreateAck (4, 0, 0, gaps, blocks));
    item->m_packet->AddAtEnd (control);
    control = Create<Packet> ();
    control->AddHeader (QuicSubheader::CreateMpAck (5, 0, 0, gaps, blocks, 1));
    item->m_packet->AddAtEnd (control);
    control = Create<Packet> ();
    control->AddHeader (QuicSubheader::CreatePadding ());
    item->m_packet->AddAtEnd (control);
    control = Create<Packet> ();
    control->AddHeader (QuicSubheader::CreateMaxData (100000));
    item->m_packet->AddAtEnd (control);
    item->m_packet->AddAtEnd (DataFrame (1, 63, 69937));
    item->m_packet->AddAtEnd (DataFrame (1, 70000, 0, true));
    item->m_packet->AddAtEnd (DataFrame (3, 0, 5, true));
    const uint32_t originalSize = item->m_packet->GetSize ();
    scheduler.Add (item, true);
    std::vector<bool> seen (70000, false);
    uint32_t received = 0, otherReceived = 0, fins = 0, controls = 0, packets = 0;
    while (scheduler.HasPendingRetransmissions () && packets < 1000)
      {
        Ptr<Packet> out = scheduler.GetNewSegment (1200, 0)->m_packet;
        NS_TEST_ASSERT_MSG_EQ ((out->GetSize () > 0), true, "Retransmission made no progress");
        NS_TEST_ASSERT_MSG_EQ ((out->GetSize () <= 1200), true, "Packet exceeded MSS budget");
        if (out->GetSize () == 0) break;
        ++packets;
        while (out->GetSize () > 0)
          {
            QuicSubheader sub;
            const uint32_t header = out->RemoveHeader (sub);
            NS_TEST_ASSERT_MSG_EQ ((header > 0), true, "Header parser stalled");
            if (sub.IsStream ())
              {
                const uint32_t length = sub.GetLength ();
                NS_TEST_ASSERT_MSG_EQ ((length <= out->GetSize ()), true, "Frame crossed packet boundary");
                if (sub.GetStreamId () == 3)
                  {
                    NS_TEST_ASSERT_MSG_EQ (sub.GetOffset (), 0, "Other stream offset changed");
                    NS_TEST_ASSERT_MSG_EQ (length, 5, "Other stream payload changed");
                    NS_TEST_ASSERT_MSG_EQ (sub.IsStreamFin (), true, "Other stream FIN lost");
                    std::vector<uint8_t> bytes (length);out->CopyData (bytes.data (), length);
                    for (uint32_t i = 0; i < length; ++i)
                      NS_TEST_ASSERT_MSG_EQ (bytes[i], i, "Other stream payload corrupted");
                    otherReceived += length;out->RemoveAtStart (length);continue;
                  }
                NS_TEST_ASSERT_MSG_EQ (sub.GetStreamId (), 1, "Stream identity changed");
                NS_TEST_ASSERT_MSG_EQ ((sub.GetOffset () + length <= seen.size ()), true, "Invalid stream offset");
                std::vector<uint8_t> bytes (length);
                if (length) out->CopyData (bytes.data (), length);
                for (uint32_t i = 0; i < length; ++i)
                  {
                    const uint32_t offset = sub.GetOffset () + i;
                    NS_TEST_ASSERT_MSG_EQ (seen[offset], false, "Duplicate retransmission payload");
                    NS_TEST_ASSERT_MSG_EQ (bytes[i], offset % 251, "Frame split changed payload bytes");
                    seen[offset] = true;
                  }
                received += length;
                out->RemoveAtStart (length);
                if (sub.IsStreamFin ())
                  {
                    ++fins;
                    NS_TEST_ASSERT_MSG_EQ (sub.GetOffset () + length, 70000, "FIN final offset changed");
                  }
              }
            else
              {
                NS_TEST_ASSERT_MSG_EQ (sub.IsMaxData (), true, "Stale ACK or padding retransmitted");
                NS_TEST_ASSERT_MSG_EQ (sub.GetMaxData (), 100000, "Control frame value changed");
                ++controls;
              }
          }
      }
    NS_TEST_ASSERT_MSG_EQ (received, 70000, "Retransmission lost stream bytes");
    NS_TEST_ASSERT_MSG_EQ (otherReceived, 5, "Second stream lost or duplicated");
    NS_TEST_ASSERT_MSG_EQ (fins, 1, "Empty FIN lost or duplicated");
    NS_TEST_ASSERT_MSG_EQ (controls, 1, "Retransmittable control lost or duplicated");
    NS_TEST_ASSERT_MSG_EQ (scheduler.AppSize (), 0, "Split header overhead left queued data");
    NS_TEST_ASSERT_MSG_EQ (item->m_packet->GetSize (), originalSize, "Normalizing mutated source packet");
    // Ordinary sends may have less than a full MSS of window available.
    Ptr<QuicSocketTxItem> onlyControl = CreateObject<QuicSocketTxItem> ();
    onlyControl->m_packet = Create<Packet> ();
    onlyControl->m_packet->AddHeader (QuicSubheader::CreateMaxData (100000));
    scheduler.Add (onlyControl, true);
    const uint32_t bufferedControl = scheduler.AppSize ();
    NS_TEST_ASSERT_MSG_EQ (scheduler.GetNewSegment (1, 0)->m_packet->GetSize (), 0,
                           "Indivisible control should wait for sufficient window");
    NS_TEST_ASSERT_MSG_EQ (scheduler.AppSize (), bufferedControl, "Small window dropped control");
    Ptr<Packet> drainedControl = scheduler.GetNewSegment (1200, 0)->m_packet;
    QuicSubheader sub;drainedControl->RemoveHeader (sub);
    NS_TEST_ASSERT_MSG_EQ (sub.IsMaxData (), true, "Queued control type changed");
    NS_TEST_ASSERT_MSG_EQ (sub.GetMaxData (), 100000, "Queued control value changed");
    NS_TEST_ASSERT_MSG_EQ (scheduler.AppSize (), 0, "Queued control was not drained once");
  }
};

class ImplicitLengthTest : public TestCase
{
public:
  ImplicitLengthTest () : TestCase ("Implicit STREAM length consumes remaining payload and retains FIN") {}
  void DoRun () override
  {
    QuicSocketTxScheduler scheduler;
    Ptr<QuicSocketTxItem> item = CreateObject<QuicSocketTxItem> ();
    item->m_packet = DataFrame (1, 4090, 100, true, false);
    scheduler.Add (item, true);
    uint32_t total = 0, fins = 0, iterations = 0;
    while (scheduler.HasPendingRetransmissions () && iterations++ < 20)
      {
        Ptr<Packet> out = scheduler.GetNewSegment (32, 0)->m_packet;
        NS_TEST_ASSERT_MSG_EQ ((out->GetSize () > 0 && out->GetSize () <= 32), true, "Invalid packet size");
        if (!out->GetSize ()) break;
        QuicSubheader sub;out->RemoveHeader (sub);
        NS_TEST_ASSERT_MSG_EQ (sub.GetOffset (), 4090 + total, "Offset changed across varint boundary");
        NS_TEST_ASSERT_MSG_EQ (sub.GetLength (), out->GetSize (), "Implicit length was not normalized");
        total += out->GetSize ();
        fins += sub.IsStreamFin ();
      }
    NS_TEST_ASSERT_MSG_EQ (total, 100, "Implicit-length payload lost");
    NS_TEST_ASSERT_MSG_EQ (fins, 1, "Implicit-length FIN lost");
    NS_TEST_ASSERT_MSG_EQ (scheduler.AppSize (), 0, "Retx budget missed added headers");
  }
};

class WirePacketCopyTest : public TestCase
{
public:
  WirePacketCopyTest () : TestCase ("Piggyback ACK cannot mutate stored sent packet or byte counters") {}
  void DoRun () override
  {
    for (uint64_t stream : {0, 1})
      {
        QuicSocketTxBuffer buffer;
        buffer.SetScheduler (CreateObject<QuicSocketTxScheduler> ());
        Ptr<Packet> frame = DataFrame (stream, 0, 100);
        const uint32_t bytes = frame->GetSize ();
        NS_TEST_ASSERT_MSG_EQ (buffer.Add (frame), true, "Could not queue test packet");
        Ptr<Packet> wire = stream == 0 ? buffer.NextStream0Sequence (SequenceNumber32 (1)) :
          buffer.NextSequence (1200, SequenceNumber32 (1), 0);
        std::vector<uint32_t> gaps, blocks;
        wire->AddHeader (QuicSubheader::CreateAck (5, 0, 0, gaps, blocks));
        NS_TEST_ASSERT_MSG_EQ (buffer.MarkAsLost (SequenceNumber32 (1), 0), true, "Lost packet not found");
        const auto lost = buffer.DetectLostPackets (0);
        NS_TEST_ASSERT_MSG_EQ (lost.size (), 1, "Expected one stored packet");
        NS_TEST_ASSERT_MSG_EQ (lost[0]->m_packet->GetSize (), bytes, "ACK altered stored packet");
        NS_TEST_ASSERT_MSG_EQ (buffer.Retransmission (SequenceNumber32 (2), 0), bytes, "Lost byte count changed");
        NS_TEST_ASSERT_MSG_EQ (buffer.AppSize (), bytes, "Retransmission size changed");
      }
  }
};

class TransferRegressionSuite : public TestSuite
{
public:
  TransferRegressionSuite () : TestSuite ("quic-transfer-regression", UNIT)
  {
    AddTestCase (new RetransmissionFramesTest, TestCase::QUICK);
    AddTestCase (new ImplicitLengthTest, TestCase::QUICK);
    AddTestCase (new WirePacketCopyTest, TestCase::QUICK);
  }
};
static TransferRegressionSuite transferRegressionSuite;
