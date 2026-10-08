import itertools
import unittest
from coupons import top_columns, coupon_for_round, condensed_columns

class CouponsTests(unittest.TestCase):
    def test_condensed_envelope_is_not_always_four_bets(self):
        exact=[{'signs':list(s)} for s in ('111','121','211','221')]
        self.assertEqual(condensed_columns(exact),{'signs':['12','12','1'],'expanded_count':4,'additional_count':0,'exact':True})
        larger=[{'signs':list(s)} for s in ('111','121','211','X11')]
        c=condensed_columns(larger)
        self.assertFalse(c['exact']);self.assertEqual(c['expanded_count'],6);self.assertEqual(c['additional_count'],2)
    def test_matches_exhaustive_search(self):
        ps=[{'1':.48,'X':.27,'2':.25},{'1':.44,'X':.24,'2':.32},{'1':.36,'X':.27,'2':.37}]
        import math
        exhaustive=sorted([(math.prod(p[s] for p,s in zip(ps,ss)), ''.join(ss)) for ss in itertools.product('1X2',repeat=3)],key=lambda x:(-x[0],x[1]))[:4]
        self.assertEqual([(x['probability'],''.join(x['signs'])) for x in top_columns(ps)],exhaustive)
    def test_missing_and_invalid(self):
        self.assertEqual(top_columns([]),[])
        with self.assertRaises(ValueError):top_columns([{'1':.5,'X':.5,'2':.5}])
    def test_official_order_and_deadline(self):
        r={'forecast_at':'2026-09-18T10:00:00+02:00','matches':[{'home':str(i),'away':'B','kickoff':'2026-09-20T14:00:00+02:00','forecast':{'probabilities':{'1':.5,'X':.3,'2':.2}}} for i in range(14)]}
        self.assertFalse(coupon_for_round(r)['complete'])
        r['official_coupon']={'verified_at':r['forecast_at'],'source':'https://example.com','match_indices':list(reversed(range(14))),'deadline':'2026-09-20T12:00:00+02:00','pleno15':{'home':'C','away':'D','kickoff':'2026-09-20T15:00:00+02:00','probabilities':{a+'-'+b:1/16 for a in '012M' for b in '012M'}}}
        c=coupon_for_round(r)
        self.assertTrue(c['complete']);self.assertEqual(c['matches'][0]['home'],'13');self.assertEqual(len(c['columns']),4)
        r['official_coupon']['deadline']='2026-09-17T10:00:00+02:00'
        self.assertFalse(coupon_for_round(r)['complete'])
    def test_results_do_not_change_columns(self):
        r={'forecast_at':'2026-09-18T10:00:00+02:00','matches':[{'home':'A','away':'B','forecast':{'probabilities':{'1':.5,'X':.3,'2':.2}}}]*3}
        before=coupon_for_round(r)
        r['matches'][0]['result']=[0,9]
        self.assertEqual(before,coupon_for_round(r))
if __name__=='__main__':unittest.main()
