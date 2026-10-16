/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
// Week-3 scheduler slot and byte-request conversion regression tests.

#include "ns3/test.h"
#include "ns3/mp-quic-scheduler.h"
#include "ns3/boolean.h"
#include "ns3/double.h"
#include "ns3/quic-socket-tx-scheduler.h"
#include "ns3/quic-subheader.h"
#include "ns3/quic-stream-rx-buffer.h"
#include <cmath>
#include <limits>
#include <vector>

using namespace ns3;

class BytesToRatioTestCase : public TestCase
{
public:
  BytesToRatioTestCase () : TestCase ("Sequential byte requests, MSS boundaries and invalid inputs") {}

private:
  void Check (const std::vector<uint32_t>& desired, uint32_t backlog, uint32_t mss,
              const std::vector<double>& expected)
  {
    const auto ratios = MpQuicScheduler::BytesToRatio (desired, backlog, mss);
    NS_TEST_ASSERT_MSG_EQ (ratios.size (), expected.size (), "Path count must be preserved");
    for (size_t i = 0; i < expected.size (); ++i)
      {
        NS_TEST_ASSERT_MSG_EQ (std::isfinite (ratios[i]), true, "Ratio must be finite");
        NS_TEST_ASSERT_MSG_EQ_TOL (ratios[i], expected[i], 1e-12, "Wrong sequential ratio on path " << i);
      }
  }

  void CheckPackets (const std::vector<uint32_t>& desired, uint32_t backlog, uint32_t mss,
                     const std::vector<uint32_t>& expectedPackets)
  {
    const auto ratios = MpQuicScheduler::BytesToRatio (desired, backlog, mss);
    // Exercise the real sender's integer cast/divide contract against literal
    // expected packet counts, not the conversion's internal arithmetic.
    for (size_t i = 0; i < expectedPackets.size (); ++i)
      {
        const uint32_t request = static_cast<uint32_t> (backlog * ratios[i]);
        const uint32_t packets = request / mss;
        NS_TEST_ASSERT_MSG_EQ (packets, expectedPackets[i], "MSS boundary lost on path " << i);
        backlog -= packets * mss;
      }
  }

  void DoRun () override
  {
    Check ({}, 10000, 1000, {});
    Check ({3000, 7000}, 10000, 1000, {0.3, 1.0});
    Check ({7000, 3000}, 10000, 1000, {0.7, 1.0});
    Check ({2000, 3000, 1000}, 10000, 1000, {0.2, 0.375, 0.2});
    Check ({2000, 0, 4000}, 10000, 1000, {0.2, 0.0, 0.5});
    Check ({1499, 2510}, 10000, 1000, {0.1, 2.0 / 9.0});
    Check ({1000, 1000, 0}, 2000, 1000, {0.5, 1.0, 0.0});
    Check ({1000, 0}, 1000, 1000, {1.0, 0.0});
    Check ({1, 999}, 999, 1000, {0.0, 0.0});
    Check ({1000, 1000}, 0, 1000, {0.0, 0.0});
    Check ({1000, 1000}, 2000, 0, {0.0, 0.0});
    Check ({2000, 2000}, 3000, 1000, {0.0, 0.0});
    // Raw requests can exceed backlog if their quantized requests do not.
    Check ({1999, 1999}, 2500, 1000, {0.4, 2.0 / 3.0});
    const uint32_t max = std::numeric_limits<uint32_t>::max ();
    Check ({max, 1000}, max, 1000, {0.0, 0.0});
    CheckPackets ({3000, 7000}, 10000, 1000, {3, 7});
    CheckPackets ({7000, 3000}, 10000, 1000, {7, 3});
    CheckPackets ({1460, 1460}, 99999, 1460, {1, 1});
    CheckPackets ({4380, 10220}, 65536, 1460, {3, 7});
    CheckPackets ({max}, max, 1000, {4294967});
    CheckPackets ({1000, 1000, 0}, 2000, 1000, {1, 1, 0});
  }
};

class FramedBufferRatioTestCase : public TestCase
{
public:
  FramedBufferRatioTestCase () : TestCase ("Fixed byte requests with actual QUIC frame splitting") {}

private:
  void CheckSplit (const std::vector<uint32_t>& desired,
                   const std::vector<uint32_t>& expectedPackets)
  {
    QuicSocketTxScheduler buffer;
    Ptr<QuicSocketTxItem> item = CreateObject<QuicSocketTxItem> ();
    item->m_isStream = true;
    item->m_packet = Create<Packet> (14600);
    item->m_packet->AddHeader (QuicSubheader::CreateStreamSubHeader (
      1, 0, 14600, false, true, false));
    buffer.Add (item, false);
    const auto ratios = MpQuicScheduler::BytesToRatio (desired, buffer.AppSize (), 1460);
    for (uint8_t path = 0; path < 2; ++path)
      {
        // AppSize is reread per path just as SendPendingData does. Splitting a
        // frame reintroduces a header into the remaining buffer.
        const uint32_t packets = static_cast<uint32_t> (buffer.AppSize () * ratios[path]) / 1460;
        NS_TEST_ASSERT_MSG_EQ (packets, expectedPackets[path], "Framed-buffer request changed");
        for (uint32_t j = 0; j < packets; ++j)
          {
            const auto segment = buffer.GetNewSegment (1460, path);
            NS_TEST_ASSERT_MSG_EQ (segment->m_packet->GetSize (), 1460, "Unexpected frame segment size");
          }
      }
    NS_TEST_ASSERT_MSG_EQ ((buffer.AppSize () > 0), true,
                           "Frame-splitting overhead is an explicit residual, not exact exhaustion");
  }

  void DoRun () override
  {
    CheckSplit ({4380, 10220}, {3, 7});
    CheckSplit ({1460, 13140}, {1, 9});
    CheckSplit ({7300, 7300}, {5, 5});
  }
};

class FinStoredPayloadTestCase : public TestCase
{
public:
  FinStoredPayloadTestCase () : TestCase ("Observe stored out-of-order FIN payload without changing transport counters") {}

private:
  void DoRun () override
  {
    QuicStreamRxBuffer buffer;
    NS_TEST_ASSERT_MSG_EQ (buffer.GetStoredPayloadBytes (), 0, "Fresh buffer contains payload");
    const auto fin = QuicSubheader::CreateStreamSubHeader (1, 1000, 100, true, true, true);
    NS_TEST_ASSERT_MSG_EQ (buffer.Add (Create<Packet> (100), fin), true, "FIN insertion failed");
    NS_TEST_ASSERT_MSG_EQ (buffer.Size (), 0, "Existing FIN transport counter behavior changed");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetStoredPayloadBytes (), 100,
                           "Stored FIN payload must remain visible despite the legacy Size counter");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetWaitingPayloadBytes (1000), 100, "FIN waiting payload lost");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetWaitingPayloadBytes (1050), 50, "Delivered prefix not clipped");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetWaitingPayloadBytes (1100), 0, "Fully delivered FIN still counted");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetDeliverable (0).second, 0,
                           "A FIN frame after a missing prefix must wait for the gap");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetFinalSize (), 1100, "Unexpected final stream offset");

    const auto earlier = QuicSubheader::CreateStreamSubHeader (1, 500, 40, true, true, false);
    NS_TEST_ASSERT_MSG_EQ (buffer.Add (Create<Packet> (40), earlier), true, "Ordinary frame insertion failed");
    NS_TEST_ASSERT_MSG_EQ (buffer.Size (), 40, "Ordinary frame transport count changed");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetStoredPayloadBytes (), 140, "Stored FIN and ordinary payload must both count");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetDeliverable (0).second, 0, "Missing prefix must still prevent delivery");
    NS_TEST_ASSERT_MSG_EQ (buffer.Size (), 40, "Observation must not mutate the transport counter");

    NS_TEST_ASSERT_MSG_EQ (buffer.Add (Create<Packet> (100), fin), true,
                           "Existing duplicate FIN acceptance behavior changed");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetStoredPayloadBytes (), 240, "Raw stored payload must retain duplicate FIN");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetWaitingPayloadBytes (0), 140, "Duplicate FIN counted twice as waiting");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetWaitingPayloadBytes (520), 120, "Ordinary prefix not clipped");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetWaitingPayloadBytes (1050), 50, "Duplicate FIN union not clipped");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetWaitingPayloadBytes (1100), 0, "Delivered duplicate FIN counted");
    NS_TEST_ASSERT_MSG_EQ (buffer.GetStoredPayloadBytes (), 240, "Waiting observation mutated stored packets");
    NS_TEST_ASSERT_MSG_EQ (buffer.Size (), 40, "Waiting observation mutated transport counter");
  }
};

class SchedulerSlotAttributeTestCase : public TestCase
{
public:
  SchedulerSlotAttributeTestCase () : TestCase ("ID 7 and reserved-parameter attribute contract") {}

private:
  void DoRun () override
  {
    NS_TEST_ASSERT_MSG_EQ (MpQuicScheduler::MIN_RTT_MULTI, 6, "ID 6 changed");
    NS_TEST_ASSERT_MSG_EQ (MpQuicScheduler::NEW_SCHED, 7, "New slot must be ID 7");
    Ptr<MpQuicScheduler> scheduler = CreateObject<MpQuicScheduler> ();
    BooleanValue fixed;
    scheduler->GetAttribute ("FixedRatio", fixed);
    NS_TEST_ASSERT_MSG_EQ (fixed.Get (), false, "Fixed diagnostic must default to disabled");
    DoubleValue share;
    scheduler->GetAttribute ("Path0Share", share);
    NS_TEST_ASSERT_MSG_EQ_TOL (share.Get (), 0.3, 1e-12, "Unexpected default share");
    NS_TEST_ASSERT_MSG_EQ (scheduler->SetAttributeFailSafe ("Path0Share", DoubleValue (-0.1)),
                           false, "Negative share accepted");
    NS_TEST_ASSERT_MSG_EQ (scheduler->SetAttributeFailSafe ("Path0Share", DoubleValue (1.1)),
                           false, "Share above one accepted");
    NS_TEST_ASSERT_MSG_EQ (scheduler->SetAttributeFailSafe ("Path0Share", DoubleValue (0.0)),
                           true, "Endpoint share rejected");
    NS_TEST_ASSERT_MSG_EQ (scheduler->SetAttributeFailSafe ("Path0Share", DoubleValue (1.0)),
                           true, "Endpoint share rejected");
    for (const char* name : {"NewKappa", "NewBeta", "NewSmax"})
      {
        DoubleValue parameter;
        scheduler->GetAttribute (name, parameter);
        NS_TEST_ASSERT_MSG_EQ (parameter.Get (), 0.0, "Reserved parameter default must be zero");
      }
    NS_TEST_ASSERT_MSG_EQ (scheduler->SetAttributeFailSafe ("NewBeta", DoubleValue (1.1)),
                           false, "Leakage coefficient above one accepted");
  }
};

class MpQuicSchedulerTestSuite : public TestSuite
{
public:
  MpQuicSchedulerTestSuite () : TestSuite ("mp-quic-scheduler", UNIT)
  {
    AddTestCase (new BytesToRatioTestCase, TestCase::QUICK);
    AddTestCase (new FramedBufferRatioTestCase, TestCase::QUICK);
    AddTestCase (new FinStoredPayloadTestCase, TestCase::QUICK);
    AddTestCase (new SchedulerSlotAttributeTestCase, TestCase::QUICK);
  }
};

static MpQuicSchedulerTestSuite g_mpQuicSchedulerTestSuite;
