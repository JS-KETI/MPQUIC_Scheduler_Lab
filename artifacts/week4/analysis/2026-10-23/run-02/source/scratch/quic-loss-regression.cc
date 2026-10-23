// Loss detection regression: a received ACK-only/probe packet number need not
// have a retransmittable item in SentList. ACK gaps still identify missing data.
#include "ns3/core-module.h"
#include "ns3/quic-socket-base.h"
#include "ns3/quic-socket-tx-buffer.h"
#include "ns3/quic-socket-tx-scheduler.h"
#include "ns3/quic-subheader.h"
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

using namespace ns3;

static unsigned failures = 0;
static void
Check (bool ok, const std::string& name)
{
  std::cout << "REGRESSION," << name << "," << (ok ? "PASS" : "FAIL") << std::endl;
  if (!ok) ++failures;
}

struct Sender
{
  Ptr<QuicSocketTxBuffer> buffer;
  Ptr<QuicSocketState> state;

  Sender ()
    : buffer (CreateObject<QuicSocketTxBuffer> ()),
      state (CreateObject<QuicSocketState> ())
  {
    buffer->SetScheduler (CreateObject<QuicSocketTxScheduler> ());
    buffer->SetMaxBufferSize (4096);
    state->m_kReorderingThreshold = 3;
    state->m_kUsingTimeLossDetection = false;
  }

  uint32_t Send (uint32_t packetNumber, uint32_t offset)
  {
    std::vector<uint8_t> bytes (100);
    for (uint32_t i = 0; i < bytes.size (); ++i) bytes[i] = (offset + i) % 251;
    auto packet = Create<Packet> (bytes.data (), bytes.size ());
    auto header = QuicSubheader::CreateStreamSubHeader (
      1, offset, bytes.size (), offset != 0, true, false);
    packet->AddHeader (header);
    const uint32_t wireBytes = packet->GetSize ();
    Check (buffer->Add (packet), "tx-add-packet-" + std::to_string (packetNumber));
    auto sent = buffer->NextSequence (wireBytes, SequenceNumber32 (packetNumber), 0);
    Check (sent && sent->GetSize () == wireBytes,
           "tx-send-packet-" + std::to_string (packetNumber));
    buffer->UpdatePacketSent (SequenceNumber32 (packetNumber), wireBytes, 0, state);
    return wireBytes;
  }
};

static bool
ContainsPacket (const std::vector<Ptr<QuicSocketTxItem> >& items, uint32_t number)
{
  for (const auto& item : items)
    if (item->m_packetNumber.GetValue () == number) return true;
  return false;
}

static void
MissingLargestDataItem ()
{
  Sender sender;
  sender.Send (9, 0);
  const uint32_t missingBytes = sender.Send (10, 100);
  // Receiver reports packet 20 and packets <=9. Packets 10..19 are missing.
  // Packet 20 was ACK-only or a probe and is absent from the data SentList.
  auto acknowledged = sender.buffer->OnAckUpdate (
    sender.state, 20, std::vector<uint32_t> {9}, std::vector<uint32_t> {19}, 0);
  Check (acknowledged.size () == 1 && ContainsPacket (acknowledged, 9),
         "gap-acknowledges-only-received-packet-9");
  Check (!ContainsPacket (acknowledged, 10), "gap-does-not-acknowledge-missing-packet-10");
  Check (sender.buffer->BytesInFlight (0) == missingBytes,
         "missing-packet-10-remains-outstanding");
  auto lost = sender.buffer->DetectLostPackets (0);
  Check (lost.size () == 1 && ContainsPacket (lost, 10),
         "missing-largest-data-item-still-detects-old-packet-10-loss");
  Check (sender.buffer->GetLost (0) == missingBytes,
         "lost-byte-count-is-exactly-missing-packet-10");

  const uint32_t retransmitBytes = sender.buffer->Retransmission (SequenceNumber32 (30), 0);
  Check (retransmitBytes == missingBytes && sender.buffer->AppSize () == missingBytes,
         "retransmission-queues-missing-data-and-excludes-acked-packet-9");
  if (retransmitBytes > 0)
    {
      auto retransmission = sender.buffer->NextSequence (
        retransmitBytes, SequenceNumber32 (30), 0);
      QuicSubheader header;
      retransmission->RemoveHeader (header);
      std::vector<uint8_t> bytes (retransmission->GetSize ());
      retransmission->CopyData (bytes.data (), bytes.size ());
      std::vector<uint8_t> expected (100);
      for (uint32_t i = 0; i < expected.size (); ++i) expected[i] = (100 + i) % 251;
      Check (header.IsStream () && header.GetOffset () == 100 && bytes == expected,
             "retransmission-preserves-only-missing-payload-byte-sequence");
      // Packet 31 is again not represented by a data item, while 30 is received.
      acknowledged = sender.buffer->OnAckUpdate (sender.state, 31, {}, {}, 0);
      Check (acknowledged.size () == 1 && ContainsPacket (acknowledged, 30),
             "received-retransmission-is-acknowledged");
      Check (sender.buffer->BytesInFlight (0) == 0 &&
             sender.buffer->DetectLostPackets (0).empty (),
             "acked-retransmission-leaves-no-outstanding-or-lost-data");
    }
}

static void
DoNotDeclareRecentPacketLost ()
{
  Sender sender;
  const uint32_t missingBytes = sender.Send (10, 0);
  // Packet 10 is missing, but largest acknowledged 12 is only two numbers ahead.
  auto acknowledged = sender.buffer->OnAckUpdate (
    sender.state, 12, std::vector<uint32_t> {9}, std::vector<uint32_t> {11}, 0);
  Check (acknowledged.empty () && sender.buffer->BytesInFlight (0) == missingBytes,
         "recent-gap-packet-stays-unacknowledged");
  Check (sender.buffer->DetectLostPackets (0).empty (),
         "packet-number-distance-two-does-not-exceed-existing-threshold-three");
}

static void
LargestDataItemStillWorks ()
{
  Sender sender;
  sender.Send (10, 0);
  sender.Send (20, 100);
  auto acknowledged = sender.buffer->OnAckUpdate (
    sender.state, 20, std::vector<uint32_t> {9}, std::vector<uint32_t> {19}, 0);
  auto lost = sender.buffer->DetectLostPackets (0);
  Check (acknowledged.size () == 1 && ContainsPacket (acknowledged, 20),
         "tracked-largest-packet-20-is-acknowledged");
  Check (lost.size () == 1 && ContainsPacket (lost, 10),
         "tracked-largest-packet-keeps-existing-packet-threshold-behavior");
}

int
main (int argc, char** argv)
{
  CommandLine command;
  command.Parse (argc, argv);
  MissingLargestDataItem ();
  DoNotDeclareRecentPacketLost ();
  LargestDataItemStillWorks ();
  Simulator::Destroy ();
  std::cout << "REGRESSION_SUMMARY,failures=" << failures << std::endl;
  return failures == 0 ? 0 : 1;
}
