// Receiver regression tests: preserve byte order and byte count across reads,
// duplicate retransmissions and retransmissions overlapping delivered data.
// No topology, rate, timeout or completion threshold is changed by these tests.
#include "ns3/core-module.h"
#include "ns3/quic-socket-base.h"
#include "ns3/quic-socket-rx-buffer.h"
#include "ns3/quic-stream-base.h"
#include "ns3/quic-l5-protocol.h"
#include "ns3/quic-subheader.h"
#include <algorithm>
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

static std::vector<uint8_t>
Bytes (uint32_t offset, uint32_t count)
{
  std::vector<uint8_t> bytes (count);
  for (uint32_t i = 0; i < count; ++i) bytes[i] = (offset + i) % 251;
  return bytes;
}

static Ptr<Packet>
Payload (uint32_t offset, uint32_t count)
{
  const auto bytes = Bytes (offset, count);
  return Create<Packet> (bytes.data (), bytes.size ());
}

static void
AppendBytes (Ptr<Packet> packet, std::vector<uint8_t>& bytes)
{
  if (!packet) return;
  const auto previous = bytes.size ();
  bytes.resize (previous + packet->GetSize ());
  packet->CopyData (bytes.data () + previous, packet->GetSize ());
}

static Ptr<QuicSocketRxBuffer>
SocketInput ()
{
  auto buffer = CreateObject<QuicSocketRxBuffer> ();
  buffer->SetMaxBufferSize (4096);
  Check (buffer->Add (Payload (0, 13)), "socket-add-13");
  Check (buffer->Add (Payload (13, 7)), "socket-add-7");
  Check (buffer->Add (Payload (20, 31)), "socket-add-31");
  return buffer;
}

static void
SocketReadTests ()
{
  {
    auto buffer = SocketInput ();
    auto packet = buffer->Extract (4096);
    std::vector<uint8_t> received;
    AppendBytes (packet, received);
    Check (received == Bytes (0, 51), "socket-large-read-keeps-all-51-bytes-in-order");
    Check (buffer->Size () == 0, "socket-large-read-remaining-size-zero");
  }
  {
    auto buffer = SocketInput ();
    std::vector<uint8_t> received;
    auto first = buffer->Extract (20);
    Check (first && first->GetSize () == 20, "socket-read-limit-20-consumes-two-frames");
    AppendBytes (first, received);
    Check (buffer->Size () == 31, "socket-after-20-read-31-bytes-remain");
    auto second = buffer->Extract (31);
    Check (second && second->GetSize () == 31, "socket-next-read-consumes-31-bytes");
    AppendBytes (second, received);
    Check (received == Bytes (0, 51), "socket-bounded-reads-preserve-byte-sequence");
    Check (buffer->Size () == 0, "socket-bounded-reads-drain-buffer");
  }
  {
    auto buffer = SocketInput ();
    std::vector<uint8_t> received;
    auto first = buffer->Extract (5); // Stop inside the first 13-byte packet.
    Check (first && first->GetSize () == 5,
           "socket-partial-first-read-obeys-five-byte-limit");
    AppendBytes (first, received);
    Check (buffer->Size () == 46,
           "socket-partial-first-read-leaves-46-bytes");
    auto second = buffer->Extract (17); // Cross packets, stopping inside the last.
    Check (second && second->GetSize () == 17,
           "socket-partial-cross-packet-read-obeys-17-byte-limit");
    AppendBytes (second, received);
    Check (buffer->Size () == 29,
           "socket-partial-cross-packet-read-leaves-29-bytes");
    auto last = buffer->Extract (100);
    Check (last && last->GetSize () == 29,
           "socket-partial-final-read-consumes-only-remaining-29-bytes");
    AppendBytes (last, received);
    Check (received == Bytes (0, 51),
           "socket-partial-reads-preserve-all-51-bytes-in-order");
    Check (buffer->Size () == 0,
           "socket-partial-reads-drain-buffer");
  }
}

// Keep flow-control advertisements outside this receiver-only fixture. The
// exercised receive path is the production Recv -> L5 Recv -> AppendingRx path.
class QuietRegressionStream : public QuicStreamBase
{
public:
  void Configure (Ptr<QuicL5Protocol> l5)
  {
    SetQuicL5 (l5);
    SetStreamId (1);
    SetStreamDirectionType (QuicStream::RECEIVER);
    SetStreamStateRecv (QuicStream::RECV);
    SetMaxStreamData (1000000);
    m_maxAdvertisedData = 1000000;
  }

  bool HasDeliveredFinalData () const
  {
    return m_streamStateRecv == QuicStream::DATA_READ;
  }
};

class QuietRegressionSocket : public QuicSocketBase
{
public:
  uint32_t PendingBytes () const { return m_rxBuffer->Size (); }
};

struct StreamReceiver
{
  Ptr<QuietRegressionSocket> socket;
  Ptr<QuicL5Protocol> l5;
  Ptr<QuietRegressionStream> stream;
  Address source;

  StreamReceiver ()
    : socket (CreateObject<QuietRegressionSocket> ()),
      l5 (CreateObject<QuicL5Protocol> ()),
      stream (CreateObject<QuietRegressionStream> ())
  {
    l5->SetSocket (socket);
    stream->Configure (l5);
  }

  void Receive (uint32_t offset, uint32_t count, bool fin = false)
  {
    auto header = QuicSubheader::CreateStreamSubHeader (
      1, offset, count, offset != 0, true, fin);
    Check (stream->Recv (Payload (offset, count), header, source) == 0,
           "stream-receive-offset-" + std::to_string (offset) + (fin ? "-with-fin" : ""));
  }
};

// Validate actual application bytes after the independent pending-byte checks.
// The bounded loop prevents a corrupted buffer counter from hanging a test.
static void
CheckStreamPayload (StreamReceiver& receiver, uint32_t expectedBytes,
                    const std::string& name)
{
  std::vector<uint8_t> received;
  for (unsigned i = 0; i < 64; ++i)
    {
      auto packet = receiver.socket->Recv (4096, 0);
      if (!packet || packet->GetSize () == 0) break;
      AppendBytes (packet, received);
    }
  Check (received == Bytes (0, expectedBytes), name);
}

static void
StreamReceiveTests ()
{
  {
    StreamReceiver receiver;
    receiver.Receive (0, 200);
    // The bytes were already delivered, but FIN first arrives on this replay.
    // Discard duplicate payload while preserving the stream termination signal.
    receiver.Receive (0, 200, true);
    Check (receiver.stream->HasDeliveredFinalData (),
           "stream-duplicate-payload-first-fin-reaches-data-read");
    Check (receiver.socket->PendingBytes () == 200,
           "stream-duplicate-payload-first-fin-keeps-only-200-unique-bytes");
    CheckStreamPayload (receiver, 200,
                        "stream-duplicate-payload-first-fin-preserves-actual-byte-sequence");
  }
  {
    StreamReceiver receiver;
    receiver.Receive (0, 200);
    receiver.Receive (0, 100);   // An already delivered range is retransmitted.
    receiver.Receive (250, 50); // Buffer data beyond a genuine 50-byte hole.
    receiver.Receive (200, 50); // Fill the hole; all 300 unique bytes are ready.
    Check (receiver.socket->PendingBytes () == 300,
           "stream-old-duplicate-does-not-prevent-delivery-of-300-bytes");
    CheckStreamPayload (receiver, 300, "stream-old-duplicate-preserves-actual-byte-sequence");
  }
  {
    StreamReceiver receiver;
    receiver.Receive (0, 200);
    receiver.Receive (250, 50);
    receiver.Receive (190, 60); // 10 old bytes plus the missing 50 new bytes.
    Check (receiver.socket->PendingBytes () == 300,
           "stream-partial-overlap-delivers-300-unique-bytes");
    CheckStreamPayload (receiver, 300, "stream-partial-overlap-preserves-actual-byte-sequence");
  }
  {
    StreamReceiver receiver;
    receiver.Receive (100, 50);
    receiver.Receive (100, 50); // Duplicate still waiting in the reorder buffer.
    receiver.Receive (0, 100);
    Check (receiver.socket->PendingBytes () == 150,
           "stream-buffered-duplicate-is-not-counted-twice");
    CheckStreamPayload (receiver, 150, "stream-buffered-duplicate-preserves-actual-byte-sequence");
  }
  {
    StreamReceiver receiver;
    receiver.Receive (200, 100);
    receiver.Receive (100, 100);
    receiver.Receive (0, 100);
    Check (receiver.socket->PendingBytes () == 300,
           "stream-reversed-frames-deliver-300-bytes-after-hole-filled");
    CheckStreamPayload (receiver, 300, "stream-reversed-frames-preserve-actual-byte-sequence");
  }
}

int
main (int argc, char** argv)
{
  std::string layer = "all";
  CommandLine command;
  command.AddValue ("Layer", "Run socket, stream or all receiver tests", layer);
  command.Parse (argc, argv);
  if (layer != "socket" && layer != "stream" && layer != "all")
    {
      std::cerr << "Layer must be socket, stream or all" << std::endl;
      return 2;
    }
  if (layer == "socket" || layer == "all") SocketReadTests ();
  if (layer == "stream" || layer == "all") StreamReceiveTests ();
  Simulator::Destroy ();
  std::cout << "REGRESSION_SUMMARY,failures=" << failures << std::endl;
  return failures == 0 ? 0 : 1;
}
