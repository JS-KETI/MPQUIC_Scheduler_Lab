/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2022 Pan Lab, Department of Computer Science, University of Victoria
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Authors: Shengjie Shu <shengjies@uvic.ca>
 */


#include "ns3/object.h"
#include "ns3/log.h"
#include "ns3/uinteger.h"
#include "ns3/double.h"
#include "ns3/boolean.h"
#include "ns3/trace-source-accessor.h"
#include "ns3/nstime.h"
#include "quic-stream.h"
#include "ns3/node.h"
#include "ns3/string.h"

#include <algorithm>
#include <iostream>
#include <iomanip>
#include <iterator>
#include <vector>
#include <bitset>
#include <numeric>
#include <limits>
#include <cmath>

#include "mp-quic-scheduler.h"
#include "ns3/random-variable-stream.h"


using Eigen::MatrixXd;
using Eigen::VectorXd;

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("MpQuicScheduler");

NS_OBJECT_ENSURE_REGISTERED (MpQuicScheduler);


TypeId
MpQuicScheduler::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::MpQuicScheduler")
    .SetParent<Object> ()
    .SetGroupName ("Internet")
    .AddAttribute ("SchedulerType",
                   "define the type of the scheduler",
                   IntegerValue (MIN_RTT),
                   MakeIntegerAccessor (&MpQuicScheduler::m_schedulerType),
                   MakeIntegerChecker<int16_t> ())
    .AddAttribute ("MabRate",
                   "define the rate of the MAB scheduler",
                   UintegerValue (100),
                   MakeUintegerAccessor (&MpQuicScheduler::m_rate),
                   MakeUintegerChecker<uint32_t> ())
    .AddAttribute ("BlestLambda",
                   "define the lambda of the BLEST",
                   UintegerValue (1000),
                   MakeUintegerAccessor (&MpQuicScheduler::m_lambda),
                   MakeUintegerChecker<uint16_t> ())
    .AddAttribute ("BlestVar",
                   "define the lambda of the BLEST",
                   UintegerValue (100),
                   MakeUintegerAccessor (&MpQuicScheduler::m_bVar),
                   MakeUintegerChecker<uint16_t> ())
    .AddAttribute ("Select",
                   "string of select",
                   UintegerValue (0),
                   MakeUintegerAccessor (&MpQuicScheduler::m_select),
                   MakeUintegerChecker<uint16_t> ())            
    .AddAttribute ("EatMargin",
                   "EAT: relative safety margin applied to the arrival estimate of a slower path",
                   DoubleValue (0.1),
                   MakeDoubleAccessor (&MpQuicScheduler::m_eatMargin),
                   MakeDoubleChecker<double> (0.0))
    .AddAttribute ("EatAlpha",
                   "EAT: EWMA gain of the scheduler-local SRTT filter",
                   DoubleValue (0.125),
                   MakeDoubleAccessor (&MpQuicScheduler::m_eatAlpha),
                   MakeDoubleChecker<double> (0.0, 1.0))
    .AddAttribute ("NewKappa",
                   "Reserved week-5 feedback gain; unused by the week-3 slot",
                   DoubleValue (0.0),
                   MakeDoubleAccessor (&MpQuicScheduler::m_newKappa),
                   MakeDoubleChecker<double> (0.0))
    .AddAttribute ("NewBeta",
                   "Reserved week-5 leakage coefficient; unused by the week-3 slot",
                   DoubleValue (0.0),
                   MakeDoubleAccessor (&MpQuicScheduler::m_newBeta),
                   MakeDoubleChecker<double> (0.0, 1.0))
    .AddAttribute ("NewSmax",
                   "Reserved week-5 integral bound; unused by the week-3 slot",
                   DoubleValue (0.0),
                   MakeDoubleAccessor (&MpQuicScheduler::m_newSmax),
                   MakeDoubleChecker<double> (0.0))
    .AddAttribute ("FixedRatio",
                   "ID 7 only: fixed-share two-path diagnostic with a ten-packet budget",
                   BooleanValue (false),
                   MakeBooleanAccessor (&MpQuicScheduler::m_fixedRatio),
                   MakeBooleanChecker ())
    .AddAttribute ("Path0Share",
                   "ID 7 fixed diagnostic: intended path-0 share before MSS quantization",
                   DoubleValue (0.3),
                   MakeDoubleAccessor (&MpQuicScheduler::m_path0Share),
                   MakeDoubleChecker<double> (0.0, 1.0))
     
  ;
  return tid;
}

MpQuicScheduler::MpQuicScheduler ()
  : Object (),
  m_socket(0),
  m_lastUsedPathId(0),
  m_newKappa(0.0),
  m_newBeta(0.0),
  m_newSmax(0.0),
  m_fixedRatio(false),
  m_path0Share(0.3),
  m_select(0)
{
  NS_LOG_FUNCTION_NOARGS ();
  m_lastUpdateRounds = 1;
  m_e = 0;
  m_eatMargin = 0.1;
  m_eatAlpha = 0.125;
}

MpQuicScheduler::~MpQuicScheduler ()
{
  NS_LOG_FUNCTION_NOARGS ();
}



std::vector<double> 
MpQuicScheduler::GetNextPathIdToUse()
{
  m_subflows = m_socket->GetActiveSubflows();
  std::vector<double> tosend(m_subflows.size(), 0.0);
  if (m_subflows.empty())
  {
    tosend.push_back(1.0);
    return tosend;
  }
  switch (m_schedulerType)
  {
    case ROUND_ROBIN:
      tosend = RoundRobin();
      break;

    case MIN_RTT:
      tosend = MinRtt();
      break;
    
    case BLEST:
      tosend = Blest();
      break;

    case ECF:
      tosend = Ecf();
      break;

    case PEEKABOO:
      tosend = Peekaboo();
      break;

    case EAT:
      tosend = Eat();
      break;

    case MIN_RTT_MULTI:
      tosend = MinRttMulti();
      break;

    case NEW_SCHED:
      tosend = NewSched();
      break;

    default:
      tosend = RoundRobin();
      break;
      
  }

  return tosend;
}

std::vector<double>
MpQuicScheduler::RoundRobin()
{
  std::vector<double> tosend(m_subflows.size(), 0.0);
  if (m_subflows.size() <= 1){
    m_lastUsedPathId = 0;
    tosend[m_lastUsedPathId] = 1.0;
    return tosend;
  }

  m_lastUsedPathId = (m_lastUsedPathId + 1) % m_subflows.size();

  tosend[m_lastUsedPathId] = 1.0;
  return tosend;
}

std::vector<double>
MpQuicScheduler::MinRtt()
{
  NS_LOG_FUNCTION (this);
  std::vector<double> tosend(m_subflows.size(), 0.0);

  if (m_subflows.size() <= 1){
    m_lastUsedPathId = 0;
    tosend[m_lastUsedPathId] = 1.0;
    return tosend;
  }

  if (m_subflows[1]->m_tcb->m_lastRtt.Get().GetSeconds() == 0) {
    m_lastUsedPathId = 1;
    tosend[m_lastUsedPathId] = 1.0;
    return tosend;
  }

  Time rttS;
  Time rttF;
  uint8_t fastPathId = 1;
  uint8_t slowPathId = 0;

  if (m_subflows[0]->m_tcb->m_lastRtt >= m_subflows[1]->m_tcb->m_lastRtt){
    rttS = m_subflows[0]->m_tcb->m_lastRtt;
    rttF = m_subflows[1]->m_tcb->m_lastRtt;
    slowPathId = 0;
    fastPathId = 1;
  } else {
    rttS = m_subflows[1]->m_tcb->m_lastRtt;
    rttF = m_subflows[0]->m_tcb->m_lastRtt;
    slowPathId = 1;
    fastPathId = 0;
  }

  if (m_socket->AvailableWindow (fastPathId) > 0){
    m_lastUsedPathId = fastPathId;
  }else {
    m_lastUsedPathId = slowPathId;
  }

  tosend[m_lastUsedPathId] = 1.0;
  return tosend;
}

void
MpQuicScheduler::SetSocket(Ptr<QuicSocketBase> sock)
{
  NS_LOG_FUNCTION (this);
  m_socket = sock;
}


std::vector<double>
MpQuicScheduler::Blest() //only allow two subflows
{
  NS_LOG_FUNCTION (this);
  std::vector<double> tosend(m_subflows.size(), 0.0);

  if (m_subflows.size() <= 1){
    m_lastUsedPathId = 0;
    tosend[m_lastUsedPathId] = 1.0;
    return tosend;
  }

  if (m_subflows[1]->m_tcb->m_lastRtt.Get().GetSeconds() == 0) {
    m_lastUsedPathId = 1;
    tosend[m_lastUsedPathId] = 1.0;
    return tosend;
  }
  
  Time rttS;
  Time rttF;
  uint8_t fastPathId = 1;
  uint8_t slowPathId = 0;
  uint32_t mss = m_socket->GetSegSize();

  if (m_subflows[0]->m_tcb->m_lastRtt > m_subflows[1]->m_tcb->m_lastRtt){
    rttS = m_subflows[0]->m_tcb->m_lastRtt;
    rttF = m_subflows[1]->m_tcb->m_lastRtt;
    slowPathId = 0;
    fastPathId = 1;
  } else {
    rttS = m_subflows[1]->m_tcb->m_lastRtt;
    rttF = m_subflows[0]->m_tcb->m_lastRtt;
    slowPathId = 1;
    fastPathId = 0;
  }

  if (m_socket->AvailableWindow (fastPathId) > 0){
    m_lastUsedPathId = fastPathId;
  } else {
    double_t rtts = rttS.GetSeconds()/rttF.GetSeconds();
    double_t cwndF = m_subflows[fastPathId]->m_tcb->m_cWnd/mss;
    double_t X = mss * (cwndF + (rtts-1)/2) * rtts;
    double_t comp = m_socket->GetTxAvailable() - (m_socket->BytesInFlight(slowPathId)+mss);
    m_lambda = m_lambda + m_bVar;
    if(X * m_lambda > comp) { //not send on slow path
      m_lastUsedPathId = fastPathId;
    } else {
      m_lastUsedPathId = slowPathId;
    }
  }
  
  tosend[m_lastUsedPathId] = 1.0;
  return tosend;
}


std::vector<double>
MpQuicScheduler::Ecf() //only allow two subflows
{
  NS_LOG_FUNCTION (this);
  std::vector<double> tosend(m_subflows.size(), 0.0);
  if (m_subflows.size() <= 1){
    m_lastUsedPathId = 0;
    tosend[m_lastUsedPathId] = 1.0;
    return tosend;
  }

  if (m_subflows[1]->m_tcb->m_lastRtt.Get().GetSeconds() == 0) {
    m_lastUsedPathId = (m_lastUsedPathId + 1) % m_subflows.size();
    tosend[m_lastUsedPathId] = 1.0;
    return tosend;
  } 
  
  
  Time rttS;
  Time rttF;
  uint8_t fastPathId = 1;
  uint8_t slowPathId = 0;

  if (m_subflows[0]->m_tcb->m_lastRtt > m_subflows[1]->m_tcb->m_lastRtt){
    rttS = m_subflows[0]->m_tcb->m_lastRtt;
    rttF = m_subflows[1]->m_tcb->m_lastRtt;
    slowPathId = 0;
    fastPathId = 1;
  } else {
    rttS = m_subflows[1]->m_tcb->m_lastRtt;
    rttF = m_subflows[0]->m_tcb->m_lastRtt;
    slowPathId = 1;
    fastPathId = 0;
  }

  if (m_socket->AvailableWindow (fastPathId) > 0){
    m_lastUsedPathId = fastPathId;
  }else {
    uint32_t k = m_socket->GetBytesInBuffer();
    double n = 1 + k/m_subflows[fastPathId]->m_tcb->m_cWnd.Get();
    double delta = max(m_subflows[fastPathId]->m_tcb->m_rttVar.GetSeconds(),m_subflows[slowPathId]->m_tcb->m_rttVar.GetSeconds());
    if (n*rttF.GetSeconds() < (1+m_waiting*1)*(rttS.GetSeconds()+delta)){
      if (k/m_subflows[slowPathId]->m_tcb->m_cWnd.Get() * rttS.GetSeconds() >= 2*rttF.GetSeconds()+delta){
        m_waiting = 1;
        m_lastUsedPathId = fastPathId;
        tosend[m_lastUsedPathId] = 1.0;
        return tosend;
      } else {
        m_lastUsedPathId = slowPathId;
      }
    } else {
      m_waiting = 0;
      m_lastUsedPathId = slowPathId;
    }
  }  

  tosend[m_lastUsedPathId] = 1.0;
  return tosend;
}

std::vector<double>
MpQuicScheduler::Peekaboo()
{
  NS_LOG_FUNCTION (this);
  uint8_t K = m_subflows.size();
  if(EPR.size() < K)
  {
    EPR.push_back(0.0);
    A.push_back(MatrixXd::Identity(6,6));
    b.push_back(VectorXd::Constant(6,0));
  }
  std::vector<double> tosend(m_subflows.size(), 0.0);

  if (m_subflows.size() <= 1){
    m_lastUsedPathId = 0;
    tosend[m_lastUsedPathId] = 1.0;
    return tosend;
  }
  if (m_subflows[1]->m_tcb->m_lastRtt.Get().GetSeconds() == 0) {
    m_lastUsedPathId = 1;
    tosend[m_lastUsedPathId] = 1.0;
    return tosend;
  }

  Time rttS;
  Time rttF;
  uint8_t fastPathId = 1;
  uint8_t slowPathId = 0;

  if (m_subflows[0]->m_tcb->m_lastRtt >= m_subflows[1]->m_tcb->m_lastRtt){
    rttS = m_subflows[0]->m_tcb->m_lastRtt;
    rttF = m_subflows[1]->m_tcb->m_lastRtt;
    slowPathId = 0;
    fastPathId = 1;
  } else {
    rttS = m_subflows[1]->m_tcb->m_lastRtt;
    rttF = m_subflows[0]->m_tcb->m_lastRtt;
    slowPathId = 1;
    fastPathId = 0;
  }

  if (m_socket->AvailableWindow (fastPathId) > 0){
    m_lastUsedPathId = fastPathId;
  }else {
    for (int i = 0; i < 2; i++){
      MatrixXd zeta = A[i]*b[i];
      EPR[i] = (peek_x.transpose() * zeta).value() + 0.8 * std::sqrt(peek_x.transpose() * A[i].inverse() * peek_x);
    }

    if(EPR[fastPathId] > EPR[slowPathId]){
      m_lastUsedPathId = fastPathId; //wait
    } else {
      m_lastUsedPathId = slowPathId; //transmit on slow path
    }

    A[m_lastUsedPathId] = A[m_lastUsedPathId] + peek_x * peek_x.transpose();
    b[m_lastUsedPathId] = b[m_lastUsedPathId] + R * peek_x;

  }

  tosend[m_lastUsedPathId] = 1.0;
  return tosend;

}


void
MpQuicScheduler::PeekabooReward(uint8_t pathId, Time lastActTime)
{
  NS_LOG_FUNCTION (this);
  
  rtt[pathId] = m_subflows[pathId]->m_tcb->m_lastRtt.Get().GetDouble();
  if (rtt[0]==0) rtt[0] = 10;     // initialize rtt0 with 20ms
  if (rtt[1]==0) rtt[1] = 10;     // initialize rtt0 with 20ms
  if(pathId == 0){
    peek_x[0] = m_subflows[pathId]->m_tcb->m_cWnd.Get()/rtt[pathId];
    peek_x[1] = m_subflows[pathId]->m_tcb->m_bytesInFlight.Get()/rtt[pathId];
    peek_x[2] = m_subflows[pathId]->m_tcb->m_cWnd.Get()/rtt[pathId];
  } else{
    peek_x[3] = m_subflows[pathId]->m_tcb->m_cWnd.Get()/rtt[pathId];
    peek_x[4] = m_subflows[pathId]->m_tcb->m_bytesInFlight.Get()/rtt[pathId];
    peek_x[5] = m_subflows[pathId]->m_tcb->m_cWnd.Get()/rtt[pathId];
  }


  double rtt_f = std::min(rtt[0], rtt[1]);
  double rtt_s = std::max(rtt[0], rtt[1]);

  T_r = std::max(2*rtt_f, rtt_s);
  T_e = (Now () - lastActTime).GetMilliSeconds();
  if (T_e < 3 * T_r)
    {
      double r = 1460 * 1000 * 1e9/ (Now() - lastActTime).GetDouble();
      R = R + r * g;
      if (T_e <= T_r)
        {
          g = 0.9 * g;
        }
      else if (T_e <= 2 * T_r)
        {
          g = 0.7 * g;
        }
      else
        {
          g = 0.5 * g;
        }
    }
  
  
}



/*
 * ---------------------------------------------------------------------------
 *  EAT: N-path Earliest-Arrival-Time scheduler  (example extension)
 * ---------------------------------------------------------------------------
 *  Idea (ECF generalised to N paths + DEMS-style bounded split):
 *   1. For every active path i estimate when the NEXT segment would arrive
 *      if it were queued on i now:
 *        T_i = max(0, inflight_i + MSS - cwnd_i) / rate_i  +  SRTT_i / 2
 *      with rate_i = cwnd_i / SRTT_i.
 *   2. The path with the smallest T (best) is always filled when open.
 *   3. Any other open path j is filled too, but only if its segment still
 *      arrives before the best path could deliver the whole remaining
 *      backlog k:  T_j(1+margin) + RTTVAR_j  <  T_best + k/rate_best,
 *      and only with the fraction of k it can deliver in that time.
 *      If nothing qualifies, wait for the best path.
 *  Unlike the built-in MinRTT/BLEST/ECF/Peekaboo (which only look at
 *  subflows 0 and 1) this works with any number of paths.
 *  RTT is filtered locally because tcb->m_smoothedRtt is not usable in this
 *  code base (RFC6298 update uses integer division 7/8 == 0).
 */
std::vector<double>
MpQuicScheduler::Eat ()
{
  NS_LOG_FUNCTION (this);
  const uint32_t n = m_subflows.size ();
  std::vector<double> tosend (n, 0.0);
  if (n <= 1)
    {
      m_lastUsedPathId = 0;
      tosend[0] = 1.0;
      return tosend;
    }
  if (m_eatSrtt.size () < n)
    {
      m_eatSrtt.resize (n, 0.0);
      m_eatRttVar.resize (n, 0.0);
      m_eatLastSample.resize (n, -1);
    }
  const double mss = m_socket->GetSegSize ();

  // (1) scheduler-local RFC6298 filter, updated only on NEW raw samples
  for (uint32_t i = 0; i < n; i++)
    {
      Time last = m_subflows[i]->m_tcb->m_lastRtt.Get ();
      if (last.IsZero () || last.GetNanoSeconds () == m_eatLastSample[i])
        {
          continue;
        }
      m_eatLastSample[i] = last.GetNanoSeconds ();
      double s = last.GetSeconds ();
      if (m_eatSrtt[i] == 0.0)
        {
          m_eatSrtt[i] = s;
          m_eatRttVar[i] = s / 2.0;
        }
      else
        {
          m_eatRttVar[i] = 0.75 * m_eatRttVar[i] + 0.25 * std::abs (m_eatSrtt[i] - s);
          m_eatSrtt[i] = (1.0 - m_eatAlpha) * m_eatSrtt[i] + m_eatAlpha * s;
        }
    }

  // (2) probe paths that have no RTT sample yet
  for (uint32_t i = 0; i < n; i++)
    {
      if (m_eatSrtt[i] == 0.0 && m_socket->AvailableWindow (i) >= mss)
        {
          m_lastUsedPathId = i;
          tosend[i] = 1.0;
          return tosend;
        }
    }

  // (3) predicted arrival time of the next segment on each path
  const double INF = std::numeric_limits<double>::infinity ();
  std::vector<double> T (n, INF), rate (n, 0.0);
  std::vector<bool> open (n, false);
  for (uint32_t i = 0; i < n; i++)
    {
      if (m_eatSrtt[i] == 0.0)
        {
          continue;
        }
      double cwnd = std::max<double> (m_subflows[i]->m_tcb->m_cWnd.Get (), mss);
      double inflight = m_socket->BytesInFlight (i);
      rate[i] = cwnd / m_eatSrtt[i];
      T[i] = std::max (0.0, inflight + mss - cwnd) / rate[i] + m_eatSrtt[i] / 2.0;
      open[i] = m_socket->AvailableWindow (i) >= mss;
    }

  uint32_t best = 0, bestOpen = n;
  for (uint32_t i = 0; i < n; i++)
    {
      if (T[i] < T[best]) best = i;
      if (open[i] && (bestOpen == n || T[i] < T[bestOpen])) bestOpen = i;
    }
  if (T[best] == INF)
    {
      m_lastUsedPathId = 0;
      tosend[0] = 1.0;
      return tosend;
    }

  if (bestOpen == n)
    {
      // no window anywhere: nothing can be sent now, just point at the best path
      m_lastUsedPathId = best;
      tosend[best] = 1.0;
      return tosend;
    }

  // (4) Fill EVERY open path that helps (one call may use several paths).
  //     The best path is always used when open.  Any other open path j is used
  //     only if its segment still arrives before the best path could deliver
  //     the whole remaining backlog k, and only for the share of k it can
  //     deliver in that time (bounded split => less tail HoL / reordering).
  const double k = std::max<double> (m_socket->GetBytesInBuffer (), mss);
  const double finishBest = T[best] + k / rate[best];
  for (uint32_t i = 0; i < n; i++)
    {
      if (!open[i])
        {
          continue;
        }
      if (i == best)
        {
          tosend[i] = 1.0;
          continue;
        }
      const double arrive = T[i] * (1.0 + m_eatMargin) + m_eatRttVar[i];
      if (arrive < finishBest)
        {
          double frac = rate[i] * (finishBest - arrive) / k;
          tosend[i] = std::min (1.0, std::max (frac, mss / k));
        }
    }
  m_lastUsedPathId = best;
  return tosend;
}

/*
 * MIN_RTT_MULTI: control baseline for EAT.  Plain MinRTT semantics, but every
 * path with an open congestion window is filled in the same call (this is how
 * MinRTT behaves in Linux MPTCP / quic-go, where the scheduler is invoked in a
 * loop until no window is left).  Comparing EAT against this baseline isolates
 * the benefit of EAT's decision logic from the benefit of multi-path filling.
 */
std::vector<double>
MpQuicScheduler::MinRttMulti ()
{
  NS_LOG_FUNCTION (this);
  std::vector<double> tosend (m_subflows.size (), 0.0);
  bool any = false;
  for (uint32_t i = 0; i < m_subflows.size (); i++)
    {
      if (m_socket->AvailableWindow (i) >= m_socket->GetSegSize ())
        {
          tosend[i] = 1.0;
          any = true;
        }
    }
  if (!any)
    {
      tosend[0] = 1.0;
    }
  return tosend;
}

std::vector<double>
MpQuicScheduler::BytesToRatio (const std::vector<uint32_t>& desired,
                               uint32_t backlog, uint32_t mss)
{
  std::vector<double> ratios (desired.size (), 0.0);
  if (mss == 0 || backlog == 0)
    {
      return ratios;
    }

  uint64_t total = 0;
  for (uint32_t bytes : desired)
    {
      total += (bytes / mss) * static_cast<uint64_t> (mss);
      if (total > backlog)
        {
          // Reject the whole request, rather than silently favoring early paths.
          return ratios;
        }
    }

  uint32_t remaining = backlog;
  for (size_t i = 0; i < desired.size (); ++i)
    {
      const uint32_t bytes = (desired[i] / mss) * mss;
      if (bytes == 0)
        {
          continue;
        }
      double ratio = static_cast<double> (bytes) / remaining;
      if (bytes < remaining)
        {
          // The sender casts remaining*ratio to uint32_t, then divides by MSS.
          // One upward ULP prevents an exact MSS request becoming MSS-1.
          ratio = std::nextafter (ratio, 1.0);
        }
      ratios[i] = ratio;
      remaining -= bytes;
    }
  return ratios;
}

std::vector<double>
MpQuicScheduler::NewSched ()
{
  if (!m_fixedRatio)
    {
      // Stage 1 must behave exactly like the existing ID 6 baseline.
      return MinRttMulti ();
    }
  if (m_subflows.size () != 2)
    {
      NS_LOG_INFO ("NEW_SCHED mode=fallback-min-rtt-multi active_paths="
                   << m_subflows.size ());
      return MinRttMulti ();
    }

  const uint32_t backlog = m_socket->GetBytesInBuffer ();
  const uint32_t mss = m_socket->GetSegSize ();
  std::vector<double> tosend (2, 0.0);
  if (backlog == 0 || mss == 0)
    {
      NS_LOG_INFO ("NEW_SCHED mode=empty-or-invalid backlog=" << backlog << " mss=" << mss);
      return tosend;
    }
  if (backlog < mss)
    {
      // Keep the existing sender's sub-MSS tail drain reachable.
      const uint32_t path = m_path0Share >= 0.5 ? 0 : 1;
      tosend[path] = 1.0;
      NS_LOG_INFO ("NEW_SCHED mode=tail path0_share=" << m_path0Share
                   << " backlog=" << backlog << " selected_path=" << path);
      return tosend;
    }

  // A ten-packet budget gives exact 3/7, 1/9 and 5/5 packet requests.
  // It is a slot diagnostic only: no measured-share or arrival feedback.
  const uint32_t packets = std::min<uint32_t> (10, backlog / mss);
  uint32_t path0Packets = static_cast<uint32_t> (std::round (packets * m_path0Share));
  if (packets >= 2 && m_path0Share > 0.0 && m_path0Share < 1.0)
    {
      // Do not floor a positive minority share to zero in a short burst.
      path0Packets = std::max<uint32_t> (1, std::min (packets - 1, path0Packets));
    }
  const std::vector<uint32_t> desired = {path0Packets * mss, (packets - path0Packets) * mss};
  tosend = BytesToRatio (desired, backlog, mss);
  NS_LOG_INFO ("NEW_SCHED mode=fixed-two-path path0_share=" << m_path0Share
               << " backlog=" << backlog << " mss=" << mss
               << " desired0=" << desired[0] << " desired1=" << desired[1]
               << " ratio0=" << tosend[0] << " ratio1=" << tosend[1]);
  return tosend;
}

void
MpQuicScheduler::SetNumOfLostPackets(uint16_t lost){
  m_lostPackets = lost;
}


} // namespace ns3
