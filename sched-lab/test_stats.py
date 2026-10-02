import itertools
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon
from stats import mean_ci, signed_rank_exact, holm, load_sweep, paired_comparisons, SCENARIOS, ORDER, NAMES


class StatsTests(unittest.TestCase):
    def test_ci_known_sample(self):
        mean,low,high,width=mean_ci([1,2,3,4,5])
        self.assertAlmostEqual(mean,3)
        self.assertAlmostEqual(low,1.0367568385)
        self.assertAlmostEqual(high,4.9632431615)
        self.assertAlmostEqual(width,3.926486323)
        self.assertTrue(np.isnan(mean_ci([2])[3]))
        self.assertTrue(np.isnan(mean_ci([])[0]))

    def test_exact_no_ties_matches_scipy(self):
        d=[1,-2,3,4,-5,6,-7]
        stat,p,n=signed_rank_exact(d)
        reference=wilcoxon(d,method='exact')
        self.assertEqual(stat,reference.statistic)
        self.assertEqual(p,reference.pvalue)
        self.assertEqual(n,7)

    def test_ties_zeros_against_enumeration(self):
        for d in [[1,1,-2,0,2],[-1,-1,-1,2],[0,0],[.0001,-.0001,.0002]]:
            nz=np.array([x for x in d if x!=0])
            ranks=rankdata(abs(nz));obs=min(ranks[nz>0].sum(),ranks[nz<0].sum())
            outcomes=[min(sum(r*s for r,s in zip(ranks,sign)),sum(ranks)-sum(r*s for r,s in zip(ranks,sign))) for sign in itertools.product([0,1],repeat=len(nz))]
            expected=sum(v<=obs for v in outcomes)/len(outcomes)
            self.assertEqual(signed_rank_exact(d)[1],expected)
        self.assertEqual(signed_rank_exact([.3-.2,.1,-.1])[1],signed_rank_exact([.1,.1,-.1])[1])

    def test_holm(self):
        np.testing.assert_allclose(holm([.01,.04,.03,np.nan]),[.03,.06,.06,np.nan])

    def sample(self):
        rows=[]
        for sc,sid,seed in itertools.product(SCENARIOS,ORDER,range(1,4)):
            rows.append(dict(scenario=sc,scheduler=sid,name=NAMES[sid],seed=seed,size=5242880,
                             fct_s=seed+sid,fct95_s=1,rx_app=5242880,rx_p0=1,rx_p1=2,
                             delay_p0_ms=1,delay_p1_ms=2,done=1,wall_s=.1))
        return pd.DataFrame(rows)

    def test_input_validation(self):
        df=self.sample()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'s.csv'
            df.to_csv(path,index=False);self.assertEqual(len(load_sweep(path,3)),63)
            for bad in [df.iloc[:-1],pd.concat([df,df.iloc[:1]])]:
                bad.to_csv(path,index=False)
                with self.assertRaises(ValueError): load_sweep(path,3)
            df.loc[0,'done']=0;df.to_csv(path,index=False)
            with self.assertRaises(ValueError): load_sweep(path,3)

    def test_pairs_only_joint_completed_seeds(self):
        df=self.sample()
        df.loc[(df.scheduler==0)&(df.seed==1),'done']=0
        df.loc[(df.scheduler==1)&(df.seed==2),'done']=0
        pairs,obs=paired_comparisons(df)
        row=pairs[(pairs.scenario=='dominating')&(pairs.scheduler_a==0)&(pairs.scheduler_b==1)].iloc[0]
        self.assertEqual(row.paired_completed,1)
        self.assertEqual(row.paired_seeds,'3')
        self.assertEqual(row.a_only,1);self.assertEqual(row.b_only,1)
        self.assertEqual(row.mean_diff_a_minus_b_s,-1)
        self.assertTrue(np.isnan(row.ci95_width_s))


if __name__=='__main__':
    unittest.main()
