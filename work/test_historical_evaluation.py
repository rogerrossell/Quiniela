import copy
import importlib.util
import math
import unittest
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from scipy.optimize import check_grad
import historical_evaluation as ev


class EvaluationTests(unittest.TestCase):
    def test_dc_gradient(self):
        hi=np.array([0,0,1,1,0]);ai=1-hi
        gh=np.array([0,0,1,1,3]);ga=np.array([0,1,0,1,2]);w=np.array([1.,.8,.5,.3,.9])
        theta=np.array([.1,-.1,.05,-.05,.2,.15,-.08])
        args=(hi,ai,gh,ga,w,2,2.,True)
        error=check_grad(lambda t:ev.objective(t,*args)[0],lambda t:ev.objective(t,*args)[1],theta)
        self.assertLess(error,1e-5)

    def test_current_matches_production(self):
        spec=importlib.util.spec_from_file_location('production',ev.ROOT/'outputs/model_quiniela_v1.py')
        production=importlib.util.module_from_spec(spec);spec.loader.exec_module(production)
        rows=ev.load_matches('SP1');m=next(r for r in rows if r['season']=='2425' and r['date'].month==12)
        train=[r for r in rows if r['date']<m['date'].replace(day=1)-timedelta(days=2)]
        def team(name,venue):
            d=dict(name=name,pj=0,gf=0,gc=0,venue_pj=0,venue_gf=0,venue_gc=0)
            for r in train:
                if r['season']!=m['season'] or name not in (r['home'],r['away']):continue
                home=r['home']==name;gf,gc=(r['gh'],r['ga']) if home else (r['ga'],r['gh'])
                d['pj']+=1;d['gf']+=gf;d['gc']+=gc
                if home==venue:d['venue_pj']+=1;d['venue_gf']+=gf;d['venue_gc']+=gc
            return d
        expected=production.predict(dict(home=team(m['home'],True),away=team(m['away'],False),time='test',adjust_home=1.,adjust_away=1.))
        np.testing.assert_allclose(ev.current_probabilities(train,m),[expected['probabilities'][s] for s in ev.SIGNS],atol=1e-12)

    def test_probability_validity(self):
        for h,a,rho in [(1.2,1.,-.1),(.2,4.,0.),(4.,.2,-.1),(2.,2.,.05)]:
            p=ev.score_probabilities(h,a,rho,1.15)
            self.assertAlmostEqual(sum(p),1.)
            self.assertTrue(all(math.isfinite(x) and 0<x<1 for x in p))

    def test_no_future_or_same_day_leakage(self):
        rows=ev.load_matches('SP1');matches=[r for r in rows if r['season']=='2526' and r['date'].month==8]
        historical=[r for r in rows if r['season']!='2526'];sample=historical+matches
        configs=[ev.CONFIGS[0]];before,_=ev.replay(sample,'2526',configs)
        corrupted=copy.deepcopy(sample)
        for r in corrupted:
            if r['season']=='2526':r['gh']=17;r['ga']=0;r['sign']='1'
        after,_=ev.replay(corrupted,'2526',configs)
        self.assertEqual([r['predictions'] for r in before],[r['predictions'] for r in after])
        self.assertTrue(all(r['cutoff']<r['date'] for r in before))

    def test_manifest_and_fit_cutoffs(self):
        import hashlib,json
        manifest=json.loads((ev.ROOT/'historical/manifest.json').read_text())
        for f in manifest['files']:
            b=(ev.ROOT/'historical/raw'/f"{f['season']}_{f['division']}.csv").read_bytes()
            self.assertEqual(hashlib.sha256(b).hexdigest(),f['sha256'])
        for div in ('SP1','SP2'):
            result=json.loads((ev.ROOT/'outputs'/f'historical_predictions_{div}.json').read_text())
            self.assertTrue(all(f['last_train']<f['cutoff']<f['month'] for f in result['fits']))

    def test_runtime_matches_validated_candidate_and_rejects_started(self):
        import sys,json
        from datetime import datetime
        sys.path.insert(0,str(ev.ROOT/'outputs'))
        import model_quiniela_v2 as runtime
        result=json.loads((ev.ROOT/'outputs/historical_predictions_SP1.json').read_text())
        fitted=next(f for f in result['fits'] if f['month']=='2025-09-01' and f['config']['penalty']==2 and not f['config']['dc'])
        snapshot=dict(fitted,division='SP1',model_version=runtime.VERSION,sources=['test'],config=dict(penalty=2.,half_life=365,dc=False,temperature=1.))
        old=next(r for r in result['test'] if r['date'].startswith('2025-09'))
        def team(name):return dict(name=name,history_key=name,pj=0,gf=0,gc=0,venue_pj=0,venue_gf=0,venue_gc=0)
        match=dict(home=team(old['home']),away=team(old['away']),time=old['date']+'T21:00:00+02:00',competition_code='SP1',adjust_home=1.,adjust_away=1.)
        cutoff='2025-09-01T10:00:00+02:00'
        actual=runtime.validated_predict(match,snapshot,cutoff)
        np.testing.assert_allclose([actual['probabilities'][s] for s in ev.SIGNS],old['predictions']['strength_p2_dc0_t1'],atol=1e-12)
        data=dict(cutoff=cutoff,matches=[match],strength_snapshot=snapshot)
        started=runtime.predict_new(data,datetime.fromisoformat(match['time']))
        self.assertTrue(started['partial']);self.assertEqual(started['results'],[])
        self.assertEqual(len(started['excluded_started_matches']),1)
        changed=dict(snapshot,cutoff='2025-09-02')
        with self.assertRaisesRegex(ValueError,'tall mensual'):
            runtime.validated_predict(match,changed,cutoff)
        fresh=runtime.predict_new(data,datetime.fromisoformat(cutoff))
        self.assertIn('reference_v01',fresh['results'][0])


if __name__=='__main__':unittest.main()
