/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * mpquic-sched-lab.cc  --  scheduler comparison bench (based on wns3-mpquic-two-path.cc)
 *
 * Same 2-path topology as the WNS3'23 paper (client n4 -> server n5, path0 via n1-n8,
 * path1 via n6-n9, bottleneck links d1d8 / d6d9 re-drawn every 100 ms from U[a,b]).
 *
 * Added for scheduler experiments:
 *   - precise flow completion time (FCT) from the PacketSink Rx trace (no 50 ms sampling)
 *   - simulation stops right after completion (much faster sweeps)
 *   - optional step event on path 1 at EventTime (e.g. UAV link degradation / handover)
 *   - one CSV line on stdout (prefixed with "RESULT,"):
 *       RESULT,sched,seed,size,fct_s,fct95_s,rx_app,rx_p0,rx_p1,delay_p0_ms,delay_p1_ms,done
 *
 * Example:
 *   ./waf --run "mpquic-sched-lab --SchedulerType=5 --Seed=3"
 *   ./waf --run "mpquic-sched-lab --SchedulerType=3 --EventTime=2.0 --Rate1After=2 --Delay1After=80"
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/quic-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/mpquic-bulk-send-application.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/traffic-control-module.h"
#include <iostream>
#include <iomanip>
#include <set>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("mpquic-sched-lab");

static uint64_t g_rxTotal = 0;
static uint64_t g_target = 0;     // Original benchmark done threshold: size - 3000 bytes
static uint64_t g_target95 = 0;   // paper-style criterion (WNS3 notebooks use > 5,000,000 B of 5,242,800 B)
static double g_fct = -1.0;
static double g_fct95 = -1.0;
static double g_start = 1.0;
static double g_completionGraceMs = 10.0;

// Keep the supplied benchmark's completion threshold for comparable FCTs.
// Exact receipt is reported separately as rx_app == size. CompletionGraceMs
// controls only the observation window after this threshold (default 10 ms).
static void
SinkRx (Ptr<const Packet> p, const Address &from)
{
  g_rxTotal += p->GetSize ();
  double t = Simulator::Now ().GetSeconds () - g_start;
  if (g_fct95 < 0 && g_rxTotal >= g_target95)
    {
      g_fct95 = t;
    }
  if (g_fct < 0 && g_rxTotal >= g_target)
    {
      g_fct = t;
      Simulator::Stop (Seconds (g_completionGraceMs / 1000.0));
    }
}

static void
ModifyLinkRate (NetDeviceContainer *ptp, DataRate lr, Time delay)
{
  StaticCast<PointToPointNetDevice> (ptp->Get (0))->SetDataRate (lr);
  StaticCast<PointToPointChannel> (StaticCast<PointToPointNetDevice> (ptp->Get (0))->GetChannel ())
      ->SetAttribute ("Delay", TimeValue (delay));
}

// Optional observers only read state; they do not change buffers, timers, or RNG.
static void
ObservePacket (std::string context, Ptr<const Packet> packet,
               const QuicHeader &header, Ptr<const QuicSocketBase> socket)
{
  std::cerr << "OBS,packet," << Simulator::Now ().GetSeconds () << "," << context << ","
            << socket->GetNode ()->GetId () << "," << unsigned (header.GetPathId ()) << ","
            << header.GetPacketNumber () << "," << packet->GetUid () << "," << packet->GetSize () << std::endl;
  Ptr<Packet> copy = packet->Copy ();
  while (copy->GetSize () > 0)
    {
      QuicSubheader sub;
      uint32_t n = copy->RemoveHeader (sub);
      if (n == 0) break;
      std::cerr << "OBS,frame," << Simulator::Now ().GetSeconds () << ","
                << context << "," << socket->GetNode ()->GetId () << ","
                << unsigned (header.GetPathId ()) << "," << header.GetPacketNumber () << ","
                << unsigned (sub.GetFrameType ());
      if (sub.IsStream ())
        {
          std::cerr << "," << sub.GetStreamId () << "," << sub.GetOffset ()
                    << "," << sub.GetLength () << std::endl;
          uint32_t length = sub.GetLength ();
          if (length > copy->GetSize ()) break;
          copy->RemoveAtStart (length);
        }
      else if (sub.IsAck ())
        {
          std::cerr << ",ack," << sub.GetLargestAcknowledged () << std::endl;
        }
      else std::cerr << std::endl;
    }
}

static void
ObserveState (Ptr<MpquicBulkSendApplication> app)
{
  Ptr<QuicSocketBase> socket = DynamicCast<QuicSocketBase> (app->GetSocket ());
  if (!socket) return;
  std::cerr << "OBS,state," << Simulator::Now ().GetSeconds () << ","
            << socket->GetSocketState () << "," << g_rxTotal << ","
            << socket->GetBytesInBuffer () << std::endl;
  uint32_t pathId = 0;
  for (auto flow : socket->GetActiveSubflows ())
    {
      auto tcb = flow->m_tcb;
      std::cerr << "OBS,path," << Simulator::Now ().GetSeconds () << "," << pathId++ << ","
                << tcb->m_bytesInFlight.Get () << "," << tcb->m_cWnd.Get () << ","
                << tcb->m_highTxMark.Get () << "," << tcb->m_lastAckedSeq << ","
                << tcb->m_lossDetectionAlarm.IsRunning () << ","
                << tcb->m_tlpCount << "," << tcb->m_rtoCount << std::endl;
    }
}

static void
ObserveDrop (std::string context, Ptr<const Packet> packet)
{
  std::cerr << "OBS,drop," << Simulator::Now ().GetSeconds () << "," << context << ","
            << packet->GetUid () << "," << packet->GetSize () << std::endl;
}

static void
ObserveQueueDrop (std::string context, Ptr<const QueueDiscItem> item, const char *reason)
{
  Ptr<const Ipv4QueueDiscItem> ip = DynamicCast<const Ipv4QueueDiscItem> (item);
  if (!ip) return;
  Ipv4Header header = ip->GetHeader ();
  std::cerr << "OBS,qdrop," << Simulator::Now ().GetSeconds () << "," << context << ","
            << reason << "," << header.GetSource () << "," << header.GetDestination () << ","
            << header.GetIdentification () << "," << header.GetFragmentOffset () << ","
            << item->GetPacket ()->GetSize ();
  if (header.GetFragmentOffset () == 0 && header.GetProtocol () == 17
      && item->GetPacket ()->GetSize () > 40)
    {
      Ptr<Packet> copy = item->GetPacket ()->Copy ();
      UdpHeader udp;
      QuicHeader quic;
      copy->RemoveHeader (udp);
      copy->RemoveHeader (quic);
      std::cerr << "," << unsigned (quic.GetPathId ()) << "," << quic.GetPacketNumber ();
    }
  std::cerr << std::endl;
}

static void
ObserveIpFragment (std::string context, Ptr<const Packet> packet, Ptr<Ipv4> ipv4, uint32_t interface)
{
  Ptr<Packet> copy = packet->Copy ();
  Ipv4Header header;
  copy->RemoveHeader (header);
  if (header.GetFragmentOffset () == 0 && header.IsLastFragment ()) return;
  std::cerr << "OBS,ipfrag," << Simulator::Now ().GetSeconds () << "," << context << ","
            << ipv4->GetObject<Node> ()->GetId () << "," << interface << ","
            << header.GetSource () << "," << header.GetDestination () << ","
            << header.GetIdentification () << "," << header.GetFragmentOffset () << ","
            << header.IsLastFragment () << "," << copy->GetSize ();
  if (header.GetFragmentOffset () == 0 && header.GetProtocol () == 17 && copy->GetSize () > 40)
    {
      UdpHeader udp;
      QuicHeader quic;
      copy->RemoveHeader (udp);
      copy->RemoveHeader (quic);
      std::cerr << "," << unsigned (quic.GetPathId ()) << "," << quic.GetPacketNumber ();
    }
  std::cerr << std::endl;
}

static void
ObserveIpDrop (std::string context, const Ipv4Header &header, Ptr<const Packet> packet,
               Ipv4L3Protocol::DropReason reason, Ptr<Ipv4> ipv4, uint32_t interface)
{
  std::cerr << "OBS,ipdrop," << Simulator::Now ().GetSeconds () << "," << context << ","
            << unsigned (reason) << "," << interface << "," << packet->GetUid () << ","
            << header.GetSource () << "," << header.GetDestination () << ","
            << header.GetIdentification () << "," << header.GetFragmentOffset () << ","
            << packet->GetSize () << std::endl;
}

static void
ConnectObservers ()
{
  static std::set<const QuicSocketBase *> connected;
  Config::MatchContainer matches = Config::LookupMatches ("/NodeList/*/$ns3::QuicL4Protocol/SocketList/*/QuicSocketBase");
  for (uint32_t i = 0; i < matches.GetN (); ++i)
    {
      Ptr<QuicSocketBase> socket = DynamicCast<QuicSocketBase> (matches.Get (i));
      if (socket && connected.insert (PeekPointer (socket)).second)
        {
          socket->TraceConnect ("Tx", "Tx", MakeCallback (&ObservePacket));
          socket->TraceConnect ("Rx", "Rx", MakeCallback (&ObservePacket));
        }
    }
}

int
main (int argc, char *argv[])
{
  int schedulerType = MpQuicScheduler::MIN_RTT;
  uint32_t size = 5242880;
  double lossrate = 0.0;
  double rate0a = 5.0, rate0b = 5.5, delay0a = 50.0, delay0b = 55.0;   // path 0 (Mbps, ms one-way)
  double rate1a = 10.0, rate1b = 11.0, delay1a = 10.0, delay1b = 11.0; // path 1
  double eventTime = -1.0;            // <0 : no event
  double rate1After = 2.0, delay1After = 80.0;
  double eatMargin = 0.1;
  int ccType = QuicSocketBase::OLIA;
  int seed = 1;
  int bLambda = 200, bVar = 0;
  double simEnd = 60.0;
  bool observe = false;

  CommandLine cmd;
  cmd.AddValue ("SchedulerType", "0 RR, 1 MinRTT, 2 BLEST, 3 ECF, 4 Peekaboo, 5 EAT(new), 6 MinRTT-multi(new)", schedulerType);
  cmd.AddValue ("Size", "bytes to transfer", size);
  cmd.AddValue ("Seed", "RNG seed", seed);
  cmd.AddValue ("LossRate", "packet error rate on both bottlenecks", lossrate);
  cmd.AddValue ("Rate0a", "path0 min rate [Mbps]", rate0a);
  cmd.AddValue ("Rate0b", "path0 max rate [Mbps]", rate0b);
  cmd.AddValue ("Delay0a", "path0 min one-way delay [ms]", delay0a);
  cmd.AddValue ("Delay0b", "path0 max one-way delay [ms]", delay0b);
  cmd.AddValue ("Rate1a", "path1 min rate [Mbps]", rate1a);
  cmd.AddValue ("Rate1b", "path1 max rate [Mbps]", rate1b);
  cmd.AddValue ("Delay1a", "path1 min one-way delay [ms]", delay1a);
  cmd.AddValue ("Delay1b", "path1 max one-way delay [ms]", delay1b);
  cmd.AddValue ("EventTime", "time after app start when path1 changes (<0 = none)", eventTime);
  cmd.AddValue ("Rate1After", "path1 rate after event [Mbps]", rate1After);
  cmd.AddValue ("Delay1After", "path1 one-way delay after event [ms]", delay1After);
  cmd.AddValue ("EatMargin", "EAT scheduler safety margin", eatMargin);
  cmd.AddValue ("CcType", "0 NewReno, 1 OLIA", ccType);
  cmd.AddValue ("BLambda", "BLEST lambda", bLambda);
  cmd.AddValue ("BVar", "BLEST lambda increment", bVar);
  cmd.AddValue ("SimEnd", "hard stop [s]", simEnd);
  cmd.AddValue ("CompletionGraceMs", "diagnostic wait after unchanged done threshold [ms]", g_completionGraceMs);
  cmd.AddValue ("Observe", "read-only packet and sender-state diagnostics on stderr", observe);
  cmd.Parse (argc, argv);

  Time::SetResolution (Time::NS);
  RngSeedManager::SetSeed (seed);
  g_target = size > 3000 ? size - 3000 : size;
  g_target95 = (uint64_t) (0.95 * size);

  TypeId ccTypeId = (ccType == QuicSocketBase::OLIA) ? MpQuicCongestionOps::GetTypeId ()
                                                     : QuicCongestionOps::GetTypeId ();

  Config::SetDefault ("ns3::QuicSocketBase::SocketSndBufSize", UintegerValue (40000000));
  Config::SetDefault ("ns3::QuicStreamBase::StreamSndBufSize", UintegerValue (40000000));
  Config::SetDefault ("ns3::QuicSocketBase::SocketRcvBufSize", UintegerValue (40000000));
  Config::SetDefault ("ns3::QuicStreamBase::StreamRcvBufSize", UintegerValue (40000000));
  Config::SetDefault ("ns3::QuicSocketBase::EnableMultipath", BooleanValue (true));
  Config::SetDefault ("ns3::QuicSocketBase::CcType", IntegerValue (ccType));
  Config::SetDefault ("ns3::QuicL4Protocol::SocketType", TypeIdValue (ccTypeId));
  Config::SetDefault ("ns3::MpQuicScheduler::SchedulerType", IntegerValue (schedulerType));
  Config::SetDefault ("ns3::MpQuicScheduler::BlestVar", UintegerValue (bVar));
  Config::SetDefault ("ns3::MpQuicScheduler::BlestLambda", UintegerValue (bLambda));
  Config::SetDefault ("ns3::MpQuicScheduler::EatMargin", DoubleValue (eatMargin));

  Ptr<RateErrorModel> em = CreateObjectWithAttributes<RateErrorModel> (
      "RanVar", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=1.0]"),
      "ErrorRate", DoubleValue (lossrate));

  Ptr<UniformRandomVariable> r0 = CreateObject<UniformRandomVariable> ();
  r0->SetAttribute ("Min", DoubleValue (rate0a));
  r0->SetAttribute ("Max", DoubleValue (rate0b));
  Ptr<UniformRandomVariable> r1 = CreateObject<UniformRandomVariable> ();
  r1->SetAttribute ("Min", DoubleValue (rate1a));
  r1->SetAttribute ("Max", DoubleValue (rate1b));
  Ptr<UniformRandomVariable> d0 = CreateObject<UniformRandomVariable> ();
  d0->SetAttribute ("Min", DoubleValue (delay0a));
  d0->SetAttribute ("Max", DoubleValue (delay0b));
  Ptr<UniformRandomVariable> d1 = CreateObject<UniformRandomVariable> ();
  d1->SetAttribute ("Min", DoubleValue (delay1a));
  d1->SetAttribute ("Max", DoubleValue (delay1b));

  // ---------------- topology (identical to the paper's two-path script) ----------------
  NodeContainer c;
  c.Create (10);
  NodeContainer n0n1 (c.Get (0), c.Get (1)), n1n8 (c.Get (1), c.Get (8)), n8n2 (c.Get (8), c.Get (2));
  NodeContainer n3n6 (c.Get (3), c.Get (6)), n6n9 (c.Get (6), c.Get (9)), n9n7 (c.Get (9), c.Get (7));
  NodeContainer n4n1 (c.Get (4), c.Get (1)), n8n5 (c.Get (8), c.Get (5));
  NodeContainer n4n6 (c.Get (4), c.Get (6)), n9n5 (c.Get (9), c.Get (5));

  InternetStackHelper internet;
  for (uint32_t i : {0u, 1u, 2u, 3u, 6u, 7u, 8u, 9u})
    {
      internet.Install (c.Get (i));
    }
  QuicHelper stack;
  stack.InstallQuic (c.Get (4));
  stack.InstallQuic (c.Get (5));

  PointToPointHelper p2p;
  p2p.SetDeviceAttribute ("DataRate", StringValue (std::to_string (r0->GetValue ()) + "Mbps"));
  p2p.SetChannelAttribute ("Delay", StringValue (std::to_string (d0->GetValue ()) + "ms"));
  NetDeviceContainer d1d8 = p2p.Install (n1n8);
  d1d8.Get (1)->SetAttribute ("ReceiveErrorModel", PointerValue (em));

  p2p.SetDeviceAttribute ("DataRate", StringValue (std::to_string (r1->GetValue ()) + "Mbps"));
  p2p.SetChannelAttribute ("Delay", StringValue (std::to_string (d1->GetValue ()) + "ms"));
  NetDeviceContainer d6d9 = p2p.Install (n6n9);
  d6d9.Get (1)->SetAttribute ("ReceiveErrorModel", PointerValue (em));

  p2p.SetDeviceAttribute ("DataRate", StringValue ("100Mbps"));
  p2p.SetChannelAttribute ("Delay", StringValue ("0.01ms"));
  NetDeviceContainer d4d1 = p2p.Install (n4n1);
  NetDeviceContainer d0d1 = p2p.Install (n0n1);
  NetDeviceContainer d8d5 = p2p.Install (n8n5);
  NetDeviceContainer d4d6 = p2p.Install (n4n6);
  NetDeviceContainer d9d5 = p2p.Install (n9n5);
  NetDeviceContainer d8d2 = p2p.Install (n8n2);
  NetDeviceContainer d3d6 = p2p.Install (n3n6);
  NetDeviceContainer d9d7 = p2p.Install (n9n7);

  Ipv4AddressHelper ipv4;
  ipv4.SetBase ("10.1.4.0", "255.255.255.0");  ipv4.Assign (d4d1);
  ipv4.SetBase ("10.1.9.0", "255.255.255.0");  ipv4.Assign (d1d8);
  ipv4.SetBase ("10.1.5.0", "255.255.255.0");  Ipv4InterfaceContainer i8i5 = ipv4.Assign (d8d5);
  ipv4.SetBase ("10.1.6.0", "255.255.255.0");  ipv4.Assign (d4d6);
  ipv4.SetBase ("10.1.10.0", "255.255.255.0"); ipv4.Assign (d6d9);
  ipv4.SetBase ("10.1.7.0", "255.255.255.0");  ipv4.Assign (d9d5);
  ipv4.SetBase ("10.1.1.0", "255.255.255.0");  ipv4.Assign (d0d1);
  ipv4.SetBase ("10.1.2.0", "255.255.255.0");  ipv4.Assign (d8d2);
  ipv4.SetBase ("10.1.3.0", "255.255.255.0");  ipv4.Assign (d3d6);
  ipv4.SetBase ("10.1.8.0", "255.255.255.0");  ipv4.Assign (d9d7);

  Ipv4StaticRoutingHelper rh;
  Ptr<Ipv4StaticRouting> sr4 = rh.GetStaticRouting (c.Get (4)->GetObject<Ipv4> ());
  sr4->AddHostRouteTo (Ipv4Address ("10.1.5.2"), Ipv4Address ("10.1.9.2"), 1);
  sr4->AddHostRouteTo (Ipv4Address ("10.1.7.2"), Ipv4Address ("10.1.10.2"), 2);
  Ptr<Ipv4StaticRouting> sr5 = rh.GetStaticRouting (c.Get (5)->GetObject<Ipv4> ());
  sr5->AddHostRouteTo (Ipv4Address ("10.1.4.1"), Ipv4Address ("10.1.9.1"), 1);
  sr5->AddHostRouteTo (Ipv4Address ("10.1.6.1"), Ipv4Address ("10.1.10.1"), 2);
  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

  // ---------------- application ----------------
  uint16_t port = 9;
  MpquicBulkSendHelper source ("ns3::QuicSocketFactory", InetSocketAddress (i8i5.GetAddress (1), port));
  source.SetAttribute ("MaxBytes", UintegerValue (size));
  ApplicationContainer srcApps = source.Install (c.Get (4));
  srcApps.Start (Seconds (g_start));
  srcApps.Stop (Seconds (simEnd));

  PacketSinkHelper sink ("ns3::QuicSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), port));
  ApplicationContainer sinkApps = sink.Install (c.Get (5));
  sinkApps.Start (Seconds (0.0));
  sinkApps.Stop (Seconds (simEnd));
  sinkApps.Get (0)->TraceConnectWithoutContext ("Rx", MakeCallback (&SinkRx));

  FlowMonitorHelper flowmon;
  Ptr<FlowMonitor> monitor = flowmon.InstallAll ();

  // ---------------- link dynamics ----------------
  for (double t = g_start; t < simEnd; t += 0.1)
    {
      bool after = (eventTime >= 0 && t >= g_start + eventTime);
      Simulator::Schedule (Seconds (t), &ModifyLinkRate, &d1d8,
                           DataRate (std::to_string (r0->GetValue ()) + "Mbps"),
                           Time::FromDouble (d0->GetValue (), Time::MS));
      double rate1 = after ? rate1After : r1->GetValue ();
      double delay1 = after ? delay1After : d1->GetValue ();
      Simulator::Schedule (Seconds (t), &ModifyLinkRate, &d6d9,
                           DataRate (std::to_string (rate1) + "Mbps"),
                           Time::FromDouble (delay1, Time::MS));
    }

  if (observe)
    {
      Config::Connect ("/NodeList/*/DeviceList/*/$ns3::PointToPointNetDevice/TxQueue/Drop", MakeCallback (&ObserveDrop));
      Config::Connect ("/NodeList/*/DeviceList/*/$ns3::PointToPointNetDevice/PhyRxDrop", MakeCallback (&ObserveDrop));
      Config::Connect ("/NodeList/*/$ns3::Ipv4L3Protocol/Drop", MakeCallback (&ObserveIpDrop));
      Config::Connect ("/NodeList/*/$ns3::Ipv4L3Protocol/Rx", MakeCallback (&ObserveIpFragment));
      Config::Connect ("/NodeList/*/$ns3::Ipv4L3Protocol/Tx", MakeCallback (&ObserveIpFragment));
      Config::Connect ("/NodeList/*/$ns3::TrafficControlLayer/RootQueueDiscList/*/DropBeforeEnqueue", MakeCallback (&ObserveQueueDrop));
      Config::Connect ("/NodeList/*/$ns3::TrafficControlLayer/RootQueueDiscList/*/DropAfterDequeue", MakeCallback (&ObserveQueueDrop));
      for (double t : {0.001, 1.000000001, 1.1, 1.2})
        Simulator::Schedule (Seconds (t), &ConnectObservers);
      for (double t : {2.0, 4.0, 6.0, 10.0, 30.0, simEnd - 0.001})
        if (t < simEnd) Simulator::Schedule (Seconds (t), &ObserveState,
                                              DynamicCast<MpquicBulkSendApplication> (srcApps.Get (0)));
    }
  Simulator::Stop (Seconds (simEnd));
  Simulator::Run ();

  // ---------------- per-path statistics ----------------
  monitor->CheckForLostPackets ();
  Ptr<Ipv4FlowClassifier> cls = DynamicCast<Ipv4FlowClassifier> (flowmon.GetClassifier ());
  uint64_t rx[2] = {0, 0};
  double dsum[2] = {0, 0};
  uint64_t np[2] = {0, 0};
  for (auto &kv : monitor->GetFlowStats ())
    {
      Ipv4FlowClassifier::FiveTuple t = cls->FindFlow (kv.first);
      int p = -1;
      if (t.destinationAddress == Ipv4Address ("10.1.5.2")) p = 0;
      if (t.destinationAddress == Ipv4Address ("10.1.7.2")) p = 1;
      if (p < 0) continue;
      rx[p] += kv.second.rxBytes;
      dsum[p] += kv.second.delaySum.GetSeconds ();
      np[p] += kv.second.rxPackets;
    }
  std::cout << std::fixed << std::setprecision (4) << "RESULT,"
            << schedulerType << "," << seed << "," << size << ","
            << (g_fct < 0 ? simEnd : g_fct) << "," << (g_fct95 < 0 ? simEnd : g_fct95) << ","
            << g_rxTotal << "," << rx[0] << "," << rx[1] << ","
            << (np[0] ? 1000 * dsum[0] / np[0] : 0) << ","
            << (np[1] ? 1000 * dsum[1] / np[1] : 0) << ","
            << (g_fct < 0 ? 0 : 1) << std::endl;

  Simulator::Destroy ();
  return 0;
}
