import copy
import unittest
from prizes import evaluate_prizes
from coupons import coupon_for_round


def fixture():
    ms=[dict(home=str(i),away='B',kickoff='2026-10-18T16:00:00+02:00',status='final',result=[1,0],result_source='https://official.example/result',forecast={'probabilities':{'1':.5,'X':.3,'2':.2}}) for i in range(14)]
    return dict(forecast_at='2026-10-15T10:00:00+02:00',matches=ms,
        coupon=dict(complete=True,published_at='2026-10-15T11:00:00+02:00',matches=[{'home':m['home'],'away':m['away']} for m in ms],columns=[{'signs':['1']*10+['X']*4}],pleno15=dict(score='1-1')),
        prize_table=dict(status='verified',source='https://official.example/scrutiny',categories_cents={'10':0,'11':222,'12':1276,'13':16526,'14':1116213},pleno15_cents=8077813,pleno15_adds_to_14=True))


class PrizeTests(unittest.TestCase):
    def test_ten_hits_zero_is_not_missing(self):
        p=evaluate_prizes(fixture());self.assertEqual(p['columns'][0]['hits'],10);self.assertEqual(p['total_cents'],0)

    def test_missing_scrutiny_is_pending(self):
        r=fixture();r.pop('prize_table');self.assertIsNone(evaluate_prizes(r)['total_cents'])

    def test_under_ten_zero_and_partial_not_evaluable(self):
        r=fixture();r['coupon']['columns'][0]['signs']=['X']*14;r.pop('prize_table')
        self.assertEqual(evaluate_prizes(r)['total_cents'],0)
        r['coupon']['complete']=False;self.assertIsNone(evaluate_prizes(r)['total_cents'])

    def test_pending_match_does_not_anticipate_prize(self):
        r=fixture();r['matches'][0]['status']='scheduled';r['matches'][0]['result']=None
        self.assertIsNone(evaluate_prizes(r)['total_cents'])
        r=fixture();r['matches'][0].pop('result_source');self.assertIsNone(evaluate_prizes(r)['total_cents'])

    def test_pleno_requires_fourteen_and_is_additional(self):
        r=fixture();r['coupon']['columns'][0]['signs']=['1']*14
        self.assertIsNone(evaluate_prizes(r)['total_cents'])
        r['coupon_results']={'pleno15':{'status':'verified','source':'https://official.example/pleno','score':'1-1'}}
        self.assertEqual(evaluate_prizes(r)['total_cents'],9194026)
        r['coupon_results']['pleno15']['score']='2-1';self.assertEqual(evaluate_prizes(r)['total_cents'],1116213)
        r['coupon']['columns'][0]['signs']=['1']*10+['X']*4;r['coupon_results']['pleno15']['score']='1-1'
        self.assertEqual(evaluate_prizes(r)['total_cents'],0)

    def test_late_publication_excluded(self):
        r=fixture();r['coupon']['published_at']='2026-10-19T10:00:00+02:00'
        self.assertEqual(evaluate_prizes(r)['status'],'not_evaluable')

    def test_verified_order_without_deadline_is_only_provisional(self):
        r=fixture();r.pop('coupon');r['matches'].append(copy.deepcopy(r['matches'][0]))
        r['official_coupon']=dict(number=18,source='https://official.example/coupon',verified_at=r['forecast_at'],order_verified=True,match_indices=list(reversed(range(14))),deadline_status='pending',deadline_expected='2026-10-17T14:00:00+02:00',pleno15=dict(home='A',away='B',kickoff='2026-10-19T21:00:00+02:00',probabilities={a+'-'+b:1/16 for a in '012M' for b in '012M'}))
        c=coupon_for_round(r)
        self.assertFalse(c['complete']);self.assertTrue(c['provisional_coupon']);self.assertEqual(len(c['matches']),14)
        self.assertEqual(c['matches'][0]['home'],'13');self.assertNotIn('deadline',c)


if __name__=='__main__':unittest.main()
