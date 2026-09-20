import json, math, html
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from coupons import coupon_for_round

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'outputs/seguiment.json'
def metrics(matches):
    eligible = [m for m in matches if m.get('forecast') and m.get('result') is not None and m.get('status') == 'final']
    if not eligible:
        return {'n': 0, 'hits': 0, 'accuracy': None, 'brier': None, 'logloss': None}
    hits=brier=loss=0
    for m in eligible:
        h,a=m['result']
        s='1' if h>a else '2' if h<a else 'X'
        p=m['forecast']['probabilities']
        hits+=m['forecast']['sign']==s
        brier+=sum((p[x]-(x==s))**2 for x in ['1','X','2'])
        loss-=math.log(max(p[s],1e-15))
    n=len(eligible)
    return dict(n=n,hits=hits,accuracy=hits/n,brier=brier/n,logloss=loss/n)

def build():
    data=json.loads(DATA.read_text())
    for r in data['rounds']:
        r['metrics']=metrics(r['matches'])
        r['coupon']=coupon_for_round(r)
    template=(ROOT/'work/dashboard.template.html').read_text()
    rendered=template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c'))
    for path in [ROOT/'site/dist/index.html',ROOT/'outputs/quiniela.html']:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(rendered)
    from build_schedule import build_schedule
    build_schedule(ROOT)
    print('HTML actualitzat; '+str(len(data['rounds']))+' jornada/es.')

if __name__=='__main__': build()
