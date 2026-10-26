"""Model per a previsions NOVES. SP1 validat; SP2 i Liga F mantenen v0.1.

Ús: python3 outputs/model_quiniela_v2.py input.json
Requereix snapshot SP1 amb fonts i tall mensual verificables. Mai refà previsions.
No consulta Internet ni executa apostes. Només biblioteca estàndard.
"""
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from model_quiniela_v1 import predict as legacy_predict

VERSION = '0.2-sp1-strength-20261026'
MADRID = ZoneInfo('Europe/Madrid')


def validated_predict(match, snapshot, cutoff):
    cutoff=datetime.fromisoformat(cutoff)
    if cutoff.tzinfo is None: raise ValueError('Data de tall sense zona horària')
    expected=cutoff.astimezone(MADRID).date().replace(day=1)-timedelta(days=2)
    if snapshot['cutoff']!=expected.isoformat():raise ValueError('Snapshot fora del tall mensual validat')
    if snapshot.get('division')!='SP1' or snapshot.get('model_version')!=VERSION:raise ValueError('Snapshot incompatible')
    if not snapshot.get('sources'):raise ValueError('Falten fonts de l’historial')
    if not snapshot.get('last_train') or snapshot['last_train']>=snapshot['cutoff']:raise ValueError('Historial posterior al tall')
    if snapshot.get('config')!={'penalty':2.,'half_life':365,'dc':False,'temperature':1.}:raise ValueError('Paràmetres sense validar')
    if match.get('adjust_home',1.)!=1. or match.get('adjust_away',1.)!=1.:raise ValueError('Ajustos manuals no validats en v0.2')
    home=match['home'];away=match['away'];ids=snapshot['teams']
    # Keys are explicit and traceable; no fuzzy name matching.
    hk=home['history_key'];ak=away['history_key'];h=ids.get(hk);a=ids.get(ak)
    if hk==ak:raise ValueError('Local i visitant idèntics')
    def value(field,idx):return snapshot[field][idx] if idx is not None else 0.
    lh=math.exp(snapshot['mu']+snapshot['home_advantage']+value('attack',h)+value('defence',a))
    la=math.exp(snapshot['mu']+value('attack',a)+value('defence',h))
    if not all(math.isfinite(x) and 0<x<100 for x in (lh,la)):raise ValueError('Intensitats invàlides')
    cells=[(i,j,math.exp(-lh-la)*lh**i*la**j/math.factorial(i)/math.factorial(j)) for i in range(31) for j in range(31)]
    mass=sum(p for i,j,p in cells)
    probs={s:sum(p for i,j,p in cells if ('1' if i>j else '2' if i<j else 'X')==s)/mass for s in ('1','X','2')}
    raw={s:100*p for s,p in probs.items()};rounded={s:math.floor(p) for s,p in raw.items()}
    for s in sorted(raw,key=lambda s:raw[s]-rounded[s],reverse=True)[:100-sum(rounded.values())]:rounded[s]+=1
    best=sorted(probs,key=probs.get,reverse=True)
    return dict(match=home['name']+' – '+away['name'],time=match['time'],lambda_home=lh,lambda_away=la,
                probabilities=probs,percentages=rounded,sign=best[0],double=''.join(s for s in ('1','X','2') if s in best[:2]),
                top_scores=[dict(score=f'{i}-{j}',probability=p/mass) for i,j,p in sorted(cells,key=lambda c:c[2],reverse=True)[:3]],
                model_version=VERSION,snapshot_cutoff=snapshot['cutoff'],
                unknown_history_teams=[key for key in (hk,ak) if key not in ids],
                note='Força d’atac/defensa, avantatge local estimat i pes temporal; sense ajustos manuals. Equips sense historial: prior neutral, confiança baixa.')


def predict_new(data, now=None):
    now=now or datetime.now(MADRID);cutoff=datetime.fromisoformat(data['cutoff'])
    if cutoff.tzinfo is None or now.tzinfo is None:raise ValueError('Dates sense zona horària')
    if cutoff>now:raise ValueError('Data de tall futura')
    results=[];excluded=[]
    for m in data['matches']:
        kickoff=datetime.fromisoformat(m['time'])
        if kickoff.tzinfo is None:raise ValueError('Inici sense zona horària')
        if kickoff<=now or kickoff<=cutoff:
            excluded.append(dict(home=m['home']['name'],away=m['away']['name'],time=m['time'],reason='Partit començat o anterior al tall; sense nova previsió'))
            continue
        competition=m['competition_code']
        if competition=='SP1':
            result=validated_predict(m,data['strength_snapshot'],data['cutoff'])
            result['reference_v01']=legacy_predict(m)
        elif competition in ('SP2','LIGA_F'):
            result=legacy_predict(m);result['model_version']='0.1-experimental'
        else:raise ValueError('Competició sense política validada')
        results.append(result)
    return dict(version=VERSION,cutoff=data['cutoff'],results=results,partial=bool(excluded),excluded_started_matches=excluded,
                warning='Primera: candidat amb suport retrospectiu, sense garantia de millora futura. Segona i Liga F: model anterior.')


if __name__=='__main__':
    data=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(predict_new(data),ensure_ascii=False,indent=2))
