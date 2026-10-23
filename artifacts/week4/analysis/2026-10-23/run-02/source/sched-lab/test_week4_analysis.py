#!/usr/bin/env python3
"""Adversarial accounting checks; no simulations and no frozen-data edits."""
import json,tempfile,unittest
from pathlib import Path
import pandas as pd
from week4_analyze import read_run,summarize,pairs,rank_changes
from week4_run import cases

class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
        self.plan=cases('pilot')[0];self.plan['scheduler']=0
        self.row=dict(run_id=self.plan['run_id'],condition='reference',scenario='dominating',scheduler=0,name='RR',seed=1,status='ok',returncode=0,
                      wall_s=.1,size=5242880,sim_end=60,loss_unit='byte',loss_rate=0,queue_packets=0,buffer_bytes=40000000,path_count=2,
                      fct_s=3,fct95_s=2.8,rx_app=5242880,rx_p0=2000000,rx_p1=3500000,delay_p0_ms=50,delay_p1_ms=10,done=1,
                      full_fct_s=3.01,queue_drops=0,error_drops=0,active_subflows=2)
        for i in range(4):
            for d in ['tx','rx']:self.row[f'{d}_payload_p{i}']=5242880 if i==0 else 0
        (self.path/'plan.json').write_text(json.dumps([self.plan]))
        self.log=self.path/'runs'/self.row['run_id']/'stdout.log';self.log.parent.mkdir(parents=True)
        self.log.write_text('CONFIG4,BufferBytes=40000000,QueueMaxPackets=0,LossUnit=byte,LossRate=0,PathCount=2,CompletionGraceMs=250,SimEnd=60\nMETRICS4,3.01,0,0,2,5242880,5242880,0,0,0,0,0,0\n')
    def tearDown(self):self.tmp.cleanup()
    def write(self):pd.DataFrame([self.row]).to_csv(self.path/'results.csv',index=False)
    def test_actual_configuration_must_match_plan(self):
        self.write();self.assertEqual(len(read_run(self.path)),1)
        self.row['buffer_bytes']=80000000;self.write()
        with self.assertRaisesRegex(ValueError,'Setting mismatch'):read_run(self.path)
    def test_missing_counters_are_not_valid_receipt_evidence(self):
        self.write();self.log.write_text('RESULT,not enough\n')
        with self.assertRaisesRegex(ValueError,'Missing required'):read_run(self.path)
    def test_incomplete_reaching_95_percent_is_included(self):
        a=self.row | dict(event_before_completion=False)
        b=a | dict(seed=2,done=0,fct_s=60,fct95_s=7,rx_app=5100000,full_fct_s=-1)
        g=summarize(pd.DataFrame([a,b])).iloc[0]
        self.assertEqual(g.completed,1);self.assertEqual(g.fct95_reached,2)
        self.assertAlmostEqual(g.mean_fct95_s,4.9)
    def test_failed_process_with_stale_values_is_not_completed(self):
        a=self.row | dict(status='process_error',event_before_completion=False)
        b=self.row | dict(scheduler=6,name='MinRTT-multi(new)',event_before_completion=False)
        result=pairs(pd.DataFrame([a,b])).iloc[0]
        self.assertEqual(result.completed_a,0);self.assertEqual(result.paired_completed,0)
        x=rank_changes(pd.DataFrame([a,b,a|dict(condition='queue100'),b|dict(condition='queue100')]))
        self.assertTrue(x.observed_sign_reversal.isna().all())

if __name__=='__main__':unittest.main()
