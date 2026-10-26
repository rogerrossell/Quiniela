"""Exporta un ajust SP1 amb el mateix protocol mensual que l'avaluació.

L'historial JSON ha de contenir sources i matches amb date (data FINAL real),
home, away, gh, ga, division. Recollir i verificar l'historial abans d'usar-lo.
No genera pronòstics ni modifica el seguiment.
"""
import argparse
import json
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from historical_evaluation import fit


def export(history,cutoff):
    stamp=datetime.fromisoformat(cutoff)
    if stamp.tzinfo is None:raise ValueError('Falta zona horària')
    monthly=stamp.astimezone(ZoneInfo('Europe/Madrid')).date().replace(day=1)-timedelta(days=2)
    if not history.get('sources'):raise ValueError('Falten fonts')
    train=[];seen=set()
    for r in history['matches']:
        if r['division']!='SP1':continue
        r=dict(r);r['date']=datetime.fromisoformat(r['date']).date()
        if r['date']>=monthly:continue
        if type(r['gh']) is not int or type(r['ga']) is not int or min(r['gh'],r['ga'])<0:raise ValueError('Resultat invàlid')
        key=(r['date'],r['home'],r['away'])
        if key in seen:raise ValueError('Partit duplicat')
        seen.add(key);train.append(r)
    recent=[r for r in train if (monthly-r['date']).days<=730]
    if len(recent)<500:raise ValueError('Calen almenys 500 partits SP1 en els darrers dos anys')
    if (monthly-max(r['date'] for r in recent)).days>21:raise ValueError('Historial massa antic per al tall mensual')
    config=dict(penalty=2.,half_life=365,dc=False,temperature=1.)
    snapshot=fit(train,monthly,config)
    return dict(**snapshot,division='SP1',model_version='0.2-sp1-strength-20261026',config=config,sources=history['sources'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--history',required=True);p.add_argument('--cutoff',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    result=export(json.loads(Path(args.history).read_text()),args.cutoff)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
