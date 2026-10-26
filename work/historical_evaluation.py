"""Avaluació retrospectiva reproduïble; no modifica cap previsió publicada.

2022/23–2023/24: escalfament. 2024/25: selecció. 2025/26: prova reservada.
Cada mes simula un tall dos dies abans del dia 1, sense actualitzar dins el mes.
Tots els models esportius reben exactament el mateix historial disponible.
"""
import csv
import hashlib
import itertools
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import gammaln

ROOT = Path(__file__).resolve().parents[1]
SIGNS = ('1', 'X', '2')
CONFIGS = [dict(penalty=p, half_life=365, dc=dc, temperature=t)
           for p, dc, t in itertools.product((2., 8.), (False, True), (1., 1.15))]


def load_matches(division):
    rows = []
    seen = set()
    for season in ('2223', '2324', '2425', '2526'):
        path = ROOT / 'historical/raw' / f'{season}_{division}.csv'
        for r in csv.DictReader(path.read_text(encoding='utf-8-sig').splitlines()):
            if not r.get('FTHG') or not r.get('FTAG'):
                continue
            day = datetime.strptime(r['Date'], '%d/%m/%Y').date()
            h, a = int(r['FTHG']), int(r['FTAG'])
            sign = '1' if h > a else '2' if h < a else 'X'
            assert r['FTR'] == {'1':'H', 'X':'D', '2':'A'}[sign]
            key = (day, r['HomeTeam'], r['AwayTeam'])
            assert key not in seen, key
            seen.add(key)
            odds = None
            try:
                values = [float(r[k]) for k in ('AvgCH', 'AvgCD', 'AvgCA')]
                if all(math.isfinite(x) and x > 1 for x in values):
                    inv = [1 / x for x in values]
                    odds = [x / sum(inv) for x in inv]
            except (ValueError, KeyError):
                pass
            rows.append(dict(date=day, season=season, home=r['HomeTeam'],
                             away=r['AwayTeam'], gh=h, ga=a, sign=sign, closing=odds))
    return sorted(rows, key=lambda r:(r['date'], r['home'], r['away']))


def score_probabilities(lh, la, rho=0., temperature=1.):
    # Exact outcome sums to 30 goals, matching the production v0.1 grid.
    ph = [math.exp(-lh)]
    pa = [math.exp(-la)]
    for k in range(1, 31):
        ph.append(ph[-1] * lh / k)
        pa.append(pa[-1] * la / k)
    probs = [0., 0., 0.]
    tau = {(0,0):1-lh*la*rho, (0,1):1+lh*rho,
           (1,0):1+la*rho, (1,1):1-rho}
    if min(tau.values()) <= 0:
        raise ValueError('Correcció DC invàlida')
    for h in range(31):
        for a in range(31):
            probs[0 if h>a else 2 if h<a else 1] += ph[h]*pa[a]*tau.get((h,a),1.)
    probs = [p ** (1/temperature) for p in probs]
    return [p/sum(probs) for p in probs]


def current_probabilities(train, match):
    # Same rate(), smoothing, venue blend and home advantage as v0.1.
    def rates(name, home):
        team = dict(pj=0, gf=0, gc=0, venue_pj=0, venue_gf=0, venue_gc=0)
        for r in train:
            if r['season'] != match['season']:
                continue
            ishome = r['home']==name
            if not ishome and r['away']!=name:
                continue
            gf, gc = (r['gh'],r['ga']) if ishome else (r['ga'],r['gh'])
            team['pj']+=1; team['gf']+=gf; team['gc']+=gc
            if ishome == home:
                team['venue_pj']+=1; team['venue_gf']+=gf; team['venue_gc']+=gc
        return [0.75*(team[f]+5.2)/(team['pj']+4)
                +0.25*(team['venue_'+f]+5.2)/(team['venue_pj']+4) for f in ('gf','gc')]
    h, a = rates(match['home'],True), rates(match['away'],False)
    return score_probabilities((h[0]+a[1])/2*1.1, (a[0]+h[1])/2*.9)


def objective(theta, hi, ai, gh, ga, weights, n, penalty, dc):
    att, defence = theta[:n], theta[n:2*n]
    mu, advantage, rho = theta[-3:]
    lh = np.exp(mu+advantage+att[hi]+defence[ai])
    la = np.exp(mu+att[ai]+defence[hi])
    tau = np.ones(len(gh)); dh = np.zeros(len(gh)); da = dh.copy(); dr = dh.copy()
    if dc:
        masks = [(gh==0)&(ga==0),(gh==0)&(ga==1),(gh==1)&(ga==0),(gh==1)&(ga==1)]
        m=masks[0]; tau[m]=1-lh[m]*la[m]*rho; dh[m]=-la[m]*rho; da[m]=-lh[m]*rho; dr[m]=-lh[m]*la[m]
        m=masks[1]; tau[m]=1+lh[m]*rho; dh[m]=rho; dr[m]=lh[m]
        m=masks[2]; tau[m]=1+la[m]*rho; da[m]=rho; dr[m]=la[m]
        m=masks[3]; tau[m]=1-rho; dr[m]=-1
    if np.any(tau<=0):
        return 1e20, np.zeros_like(theta)
    loss = np.sum(weights*(lh-gh*np.log(lh)+gammaln(gh+1)
                  +la-ga*np.log(la)+gammaln(ga+1)-np.log(tau)))
    eh=weights*(lh-gh-dh*lh/tau); ea=weights*(la-ga-da*la/tau)
    grad=np.zeros_like(theta)
    np.add.at(grad,hi,eh); np.add.at(grad,ai,ea)
    np.add.at(grad,n+ai,eh); np.add.at(grad,n+hi,ea)
    grad[-3]=np.sum(eh+ea);grad[-2]=np.sum(eh);grad[-1]=-np.sum(weights*dr/tau)
    loss+=penalty*np.sum(theta[:2*n]**2)/2
    grad[:2*n]+=penalty*theta[:2*n]
    return float(loss),grad


def fit(train, cutoff, config):
    recent=[r for r in train if 0 < (cutoff-r['date']).days <= 730]
    assert recent and all(r['date'] < cutoff for r in recent)
    teams=sorted({r[k] for r in recent for k in ('home','away')}); ids={t:i for i,t in enumerate(teams)};n=len(teams)
    hi=np.array([ids[r['home']] for r in recent]);ai=np.array([ids[r['away']] for r in recent])
    gh=np.array([r['gh'] for r in recent]);ga=np.array([r['ga'] for r in recent])
    weights=np.array([.5**((cutoff-r['date']).days/config['half_life']) for r in recent])
    theta=np.zeros(2*n+3);theta[-3]=math.log(max(.1,np.average(ga,weights=weights)))
    theta[-2]=math.log(max(.1,np.average(gh,weights=weights)))-theta[-3]
    bounds=[(-1.2,1.2)]*(2*n)+[(-1.,1.),(-.4,.7),(0.,0.)]
    result=minimize(objective,theta,args=(hi,ai,gh,ga,weights,n,config['penalty'],False),
                    method='L-BFGS-B',jac=True,bounds=bounds,options={'maxiter':300,'ftol':1e-10})
    if not result.success:
        raise RuntimeError(result.message)
    theta=result.x
    if config['dc']:
        # Two-stage correction: fit team strengths first, then rho conditional
        # on those strengths. Bounds keep every possible team pairing valid.
        maxh=math.exp(theta[-3]+theta[-2]+max(theta[:n])+max(theta[n:2*n]))
        maxa=math.exp(theta[-3]+max(theta[:n])+max(theta[n:2*n]))
        def conditional(rho):
            t=theta.copy();t[-1]=rho
            return objective(t,hi,ai,gh,ga,weights,n,config['penalty'],True)[0]
        corrected=minimize_scalar(conditional,bounds=(-.99/max(maxh,maxa),min(.99,.99/(maxh*maxa))),method='bounded')
        if not corrected.success: raise RuntimeError(corrected.message)
        theta[-1]=corrected.x
    return dict(teams=ids, attack=theta[:n].tolist(), defence=theta[n:2*n].tolist(),
                mu=float(theta[-3]),home_advantage=float(theta[-2]),rho=float(theta[-1]),
                n_train=len(recent),cutoff=cutoff.isoformat(),last_train=max(r['date'] for r in recent).isoformat())


def candidate_probabilities(fitted, match, temperature):
    ids=fitted['teams'];h=ids.get(match['home']);a=ids.get(match['away'])
    def val(field,i): return fitted[field][i] if i is not None else 0.
    lh=math.exp(fitted['mu']+fitted['home_advantage']+val('attack',h)+val('defence',a))
    la=math.exp(fitted['mu']+val('attack',a)+val('defence',h))
    # Restrict rho to keep all four corrected cells positive for this matchup.
    rho=max(-.99/max(lh,la),min(fitted['rho'],.99,.99/(lh*la)))
    return score_probabilities(lh,la,rho,temperature)


def metrics(records, key):
    pairs=[(r,r['predictions'][key]) for r in records if r['predictions'].get(key) is not None]
    if not pairs: return dict(n=0,hits=0,accuracy=None,brier=None,logloss=None)
    hits=0;brier=0.;loss=0.;bins=defaultdict(list)
    for r,p in pairs:
        assert all(math.isfinite(x) and 0<x<1 for x in p) and abs(sum(p)-1)<1e-9
        y=SIGNS.index(r['sign']);best=max(range(3),key=lambda i:p[i]);hits+=best==y
        brier+=sum((p[i]-(i==y))**2 for i in range(3));loss-=math.log(p[y])
        bins[min(int(p[best]*10),9)].append((p[best],float(best==y)))
    n=len(pairs)
    return dict(n=n,hits=hits,accuracy=hits/n,brier=brier/n,logloss=loss/n,
                calibration=[dict(bin=f'{b*10}–{(b+1)*10}%',n=len(v),mean_probability=sum(x for x,y in v)/len(v),observed=sum(y for x,y in v)/len(v)) for b,v in sorted(bins.items())])


def replay(rows, season, configs):
    out=[];fits=[]
    groups=defaultdict(list)
    for r in rows:
        if r['season']==season: groups[r['date'].replace(day=1)].append(r)
    for month,matches in sorted(groups.items()):
        cutoff=month-timedelta(days=2)
        train=[r for r in rows if r['date'] < cutoff]
        counts=[1.,1.,1.]
        for r in train:
            if (cutoff-r['date']).days<=730: counts[SIGNS.index(r['sign'])]+=1
        empirical=[x/sum(counts) for x in counts]
        fitted={}
        for config in configs:
            key=(config['penalty'],config['half_life'],config['dc'])
            if key not in fitted:
                fitted[key]=fit(train,cutoff,config)
                fits.append(dict(month=month.isoformat(),config=dict(zip(('penalty','half_life','dc'),key)),**fitted[key]))
        for r in matches:
            preds={'v01':current_probabilities(train,r),'league':empirical,'uniform':[1/3]*3,'market_close':r['closing']}
            for config in configs:
                key=(config['penalty'],config['half_life'],config['dc'])
                preds[config_id(config)]=candidate_probabilities(fitted[key],r,config['temperature'])
            out.append(dict(date=r['date'].isoformat(),cutoff=cutoff.isoformat(),home=r['home'],away=r['away'],sign=r['sign'],predictions=preds))
    return out,fits


def config_id(c): return f"strength_p{c['penalty']:g}_dc{int(c['dc'])}_t{c['temperature']:g}"


def paired_interval(records, candidate, reference, block_days=28, repetitions=2000):
    # Calendar-block bootstrap preserves dependence within short periods.
    origin=min(datetime.fromisoformat(r['date']).date() for r in records);blocks=defaultdict(list)
    for r in records:
        y=SIGNS.index(r['sign']);p=r['predictions'][candidate];q=r['predictions'][reference]
        bs=sum((p[i]-(i==y))**2-(q[i]-(i==y))**2 for i in range(3))
        ll=-math.log(p[y])+math.log(q[y])
        blocks[(datetime.fromisoformat(r['date']).date()-origin).days//block_days].append((bs,ll))
    summaries=[(sum(x for x,y in b),sum(y for x,y in b),len(b)) for b in blocks.values()]
    rng=np.random.default_rng(26102026);samples=[]
    for _ in range(repetitions):
        chosen=[summaries[i] for i in rng.integers(0,len(summaries),len(summaries))]
        n=sum(x[2] for x in chosen);samples.append([sum(x[j] for x in chosen)/n for j in (0,1)])
    return {metric:dict(delta=float(np.mean([sum(x[j] for x in summaries)/sum(x[2] for x in summaries)])),
                        lower=float(np.quantile(np.array(samples)[:,j],.025)),upper=float(np.quantile(np.array(samples)[:,j],.975))) for j,metric in enumerate(('brier','logloss'))}


def main():
    report=dict(created_at=datetime.now(timezone.utc).isoformat(),status='retrospective_research',
        training='2022/23–2023/24, finestra mòbil màxima de 730 dies',validation='2024/25',test='2025/26',
        cutoff_policy='Cada mes: dia 1 menys dos dies, 00:00 Europe/Madrid; només dates estrictament anteriors. Tall mensual conservador, no una reproducció exacta dels cupons.',
        selection='Mínima pèrdua logarítmica de validació per competició; prova reservada sense reselecció.',
        candidate_method='Poisson amb atac/defensa per equip, avantatge local estimat, regularització i pes temporal de semivida 365 dies. Variant DC: rho ajustat en un segon pas, condicionat al Poisson; no ajust conjunt complet Dixon–Coles.',
        adoption_rule='No activació automàtica. Candidat només avalat si millora Brier i logloss contra v0.1 i freqüències de lliga, amb límit superior IC95% < 0 en totes quatre comparacions.',
        market_warning='AvgCH/CD/CA: quotes de tancament sense marge proporcional. Referència retrospectiva amb informació més tardana, no disponible al nostre tall; exclosa de selecció i adopció.',
        limitations=['Històric secundari Football-Data.co.uk; no acta oficial.','Sense Liga F, xG, lesions ni càrrega de competicions.','La simulació no avalua premis, rendibilitat ni cupons oficials.','L’avaluació mensual és més conservadora que una actualització setmanal.','Una prova reservada vista una vegada ja no és una nova prova independent per a iteracions futures.'],
        source_manifest=json.loads((ROOT/'historical/manifest.json').read_text()),competitions={})
    for division in ('SP1','SP2'):
        rows=load_matches(division)
        val,vfits=replay(rows,'2425',CONFIGS)
        scores={config_id(c):metrics(val,config_id(c)) for c in CONFIGS}
        selected=min(CONFIGS,key=lambda c:scores[config_id(c)]['logloss']);name=config_id(selected)
        test,tfits=replay(rows,'2526',[selected])
        comparators=['v01','league','uniform','market_close',name]
        test_scores={k:metrics(test,k) for k in comparators}
        intervals={ref:paired_interval(test,name,ref) for ref in ('v01','league')}
        supported=all(intervals[ref][metric]['upper']<0 for ref in intervals for metric in ('brier','logloss'))
        report['competitions'][division]=dict(n_total=len(rows),selected_config=selected,candidate_id=name,
             validation_scores=scores,test_scores=test_scores,paired_intervals_95=intervals,
             evidence_supports_candidate=supported,production_status='eligible_for_new_forecasts_with_verified_inputs' if supported else 'retain_v01',
             always_home_test_hits=sum(r['sign']=='1' for r in test),
             note='Mantingut en paral·lel fins a validar integració, dades futures i coincidència del tall operatiu.')
        (ROOT/'outputs'/f'historical_predictions_{division}.json').write_text(json.dumps(dict(validation=val,test=test,fits=vfits+tfits),ensure_ascii=False))
        print(division,'selected',name,'test',test_scores,'supported',supported,flush=True)
    (ROOT/'outputs/historical_evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__': main()
