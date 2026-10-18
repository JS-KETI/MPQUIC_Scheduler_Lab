from pathlib import Path
import sys,subprocess
root=Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic')
base=root/'artifacts/week4/analysis/2026-10-18/diagnosis-01/observational-source'
mode=sys.argv[1]
# These exact files were changed only by this task. Save every candidate patch before restoring.
for p in base.rglob('*'):
 if p.is_file():(root/p.relative_to(base)).write_bytes(p.read_bytes())
def edit(f,o,n):
 p=root/f;s=p.read_text();assert s.count(o)==1,(f,s.count(o));p.write_text(s.replace(o,n))
if mode in ['close','stream','stream_rx']:
 edit('src/quic/model/quic-socket-base.cc','  if (m_appCloseSentListNoEmpty && m_txBuffer->SentListIsEmpty()){','  if (m_appCloseSentListNoEmpty && m_txBuffer->SentListIsEmpty() && m_txBuffer->AppSize () == 0){')
if mode in ['stream','stream_rx']:
 edit('src/quic/model/quic-l5-protocol.h','  void SetSocket (Ptr<QuicSocketBase> sock);','  void SetSocket (Ptr<QuicSocketBase> sock);\n  void DiagnosticResumeStreams ();')
 edit('src/quic/model/quic-l5-protocol.cc','int\nQuicL5Protocol::DispatchRecv', '''void
QuicL5Protocol::DiagnosticResumeStreams ()
{
  for (auto stream : m_streams)
    if (stream->GetStreamId () > 0 && stream->GetStreamTxAvailable () < stream->GetStreamSndBufSize ())
      stream->SendPendingData ();
}

int
QuicL5Protocol::DispatchRecv''')
 edit('src/quic/model/quic-socket-base.cc','  // Find lost packets\n  std::vector<Ptr<QuicSocketTxItem> > lostPackets', '  m_quicl5->DiagnosticResumeStreams ();\n\n  // Find lost packets\n  std::vector<Ptr<QuicSocketTxItem> > lostPackets')
if mode in ['queue','queue_frames']:
 edit('src/quic/model/quic-socket-base.cc','  SendDataPacket (next, toRetx, m_connected,pathId);', '''  while (toRetx > 0)
    {
      uint32_t sent = SendDataPacket (next, std::min (toRetx, GetSegSize ()), m_connected, pathId);
      if (sent == 0 || sent == static_cast<uint32_t> (-1)) break;
      toRetx -= std::min (toRetx, sent);
      if (toRetx > 0) next = ++m_subflows[pathId]->m_tcb->m_nextTxSequence;
    }''')
if mode=='queue_frames':
 # A retransmitted UDP payload may contain multiple STREAM frames and ACKs.
 # The original splitter expects one frame per scheduled item.
 edit('src/quic/model/quic-socket-tx-scheduler.cc','  QuicSubheader qsb;\n  item->m_packet->PeekHeader (qsb);\n  double priority = -1;', '''  if (retx)
    {
      Ptr<Packet> remaining = item->m_packet->Copy ();
      while (remaining->GetSize () > 0)
        {
          QuicSubheader sub;
          remaining->RemoveHeader (sub);
          if (!sub.IsStream ()) continue;
          NS_ABORT_MSG_IF (sub.GetLength () > remaining->GetSize (), "Invalid diagnostic retransmission frame");
          Ptr<QuicSocketTxItem> part = CreateObject<QuicSocketTxItem> (*item);
          part->m_packet = remaining->CreateFragment (0, sub.GetLength ());
          remaining->RemoveAtStart (sub.GetLength ());
          part->m_packet->AddHeader (sub);
          AddScheduleItem (CreateObject<QuicSocketTxScheduleItem> (sub.GetStreamId (), sub.GetOffset (), -1, part), true);
        }
      return;
    }
  QuicSubheader qsb;
  item->m_packet->PeekHeader (qsb);
  double priority = -1;''')
if mode in ['rx','stream_rx']:
 edit('scratch/mpquic-sched-lab.cc','"ns3::QuicStreamBase::StreamRcvBufSize", UintegerValue (bufferBytes)', '"ns3::QuicStreamBase::StreamRcvBufSize", UintegerValue (8388608)')
if mode not in ['close','stream','stream_rx','queue','queue_frames','rx','restore']:raise ValueError(mode)
# Patch from the published source includes observation code and the specified candidate.
if mode!='restore':
 p=root/f'artifacts/week4/analysis/2026-10-18/diagnosis-01/candidate-{mode}.patch'
 p.write_bytes(subprocess.check_output(['git','diff','HEAD','--','src','scratch'],cwd=root))
print('candidate',mode,flush=True)
