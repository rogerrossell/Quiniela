"""Previsió anticipada J11/cupó 18; només dades locals amb fonts conservades.

No descarrega dades ni refà cap previsió passada. La manca d'avís específic
de tancament obliga a mantenir el cupó provisional.
"""
import copy
import csv
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from export_strength_snapshot import export
from coupons import coupon_for_round

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'outputs'))
from model_quiniela_v2 import predict_new
from build_dashboard import metrics

ZONE=ZoneInfo('Europe/Madrid')
STAMP=datetime.now(ZONE).isoformat(timespec='seconds')
OUT=ROOT/'outputs'
COUPON='https://www.loteriasyapuestas.es/f/loterias/web_corporativa/Comunicacion/Avisos_de_interes/COMPOSICION%20DE%20BOLETOS%20JORNADAS%2018%20DE%20LA%20QUINIELA,%20ELIGE%208%20Y%2019%20DEL%20QUINIGOL%20.zip'
NOTICE='https://www.loteriasyapuestas.es/es/avisos-de-interes'
SCRUTINY='https://www.loteriasyapuestas.es/es/la-quiniela/escrutinios/la-quiniela-premios-y-ganadores-del-18-de-octubre-de-2026'
SER='https://cadenaser.com/nacional/2026/10/26/laliga-fantasy-jugadores-sancionados-y-lesionados-para-la-jornada-11-y-posibles-sustitutos-cadena-ser/'
NAMES={
 'villarreal-cf':('Villarreal','Villarreal'),'rcd-espanyol':('Espanyol','Espanol'),
 'levante-ud':('Llevant','Levante'),'atletico-de-madrid':('Atlètic de Madrid','Ath Madrid'),
 'rayo-vallecano':('Rayo','Vallecano'),'rc-celta':('Celta','Celta'),
 'real-betis':('Betis','Betis'),'malaga-cf':('Màlaga','Malaga'),
 'fc-barcelona':('Barcelona','Barcelona'),'d-alaves':('Alabès','Alaves'),
 'getafe-cf':('Getafe','Getafe'),'sevilla-fc':('Sevilla','Sevilla'),
 'r-racing-club':('Racing','Santander'),'real-madrid':('Real Madrid','Real Madrid'),
 'elche-c-f':('Elx','Elche'),'valencia-cf':('València','Valencia'),
 'athletic-club':('Athletic','Ath Bilbao'),'real-sociedad':('Reial Societat','Sociedad'),
 'rc-deportivo':('Deportivo','La Coruna'),'c-a-osasuna':('Osasuna','Osasuna'),
 'sd-eibar':('Eibar',None),'ud-almeria':('Almeria',None),'eldense':('Eldense',None),
 'granada-cf':('Granada',None),'burgos':('Burgos',None),'cd-castellon':('Castelló',None),
 'd-alaves-femenino':('Alabès (F)',None),'r-sociedad-femenino':('Reial Societat (F)',None),
 'madrid-cff':('Madrid CFF (F)',None),'deportivo-abanca':('Deportivo (F)',None),
 'sevilla-femenino':('Sevilla (F)',None),'real-madrid-femenino':('Real Madrid (F)',None),
 'ud-granadilla-tenerife-egatesa':('Tenerife (F)',None),'athletic-femenino':('Athletic (F)',None)}
EXTRAS={'sp2':[('sd-eibar','ud-almeria'),('eldense','granada-cf'),('burgos','cd-castellon')],
        'f':[('d-alaves-femenino','r-sociedad-femenino'),('madrid-cff','deportivo-abanca'),('sevilla-femenino','real-madrid-femenino'),('ud-granadilla-tenerife-egatesa','athletic-femenino')]}


def save(name,data): (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    data=json.loads((OUT/'seguiment.json').read_text())
    if any(r['number']==11 for r in data['rounds']):raise ValueError('J11 ja existeix: no substituir una previsió')
    original=copy.deepcopy(data['rounds'])
    tables={c:json.loads((OUT/f'font_classificacio_{c}_20261026.json').read_text()) for c in ('sp1','sp2','f')}
    calendars={c:json.loads((OUT/f'font_calendari_{c}_j11_20261026.json').read_text()) for c in tables}
    # Live standings can already count a match in progress. The result is not
    # final: remove that appearance, without assuming any eventual score.
    for key in ('standings','standingsHome'):
        for r in tables['sp1']['tables'][key]:
            if r['slug']=='sevilla-fc':r['played']-=1
    for key in ('standings','standingsAway'):
        for r in tables['sp1']['tables'][key]:
            if r['slug']=='c-a-osasuna':r['played']-=1
    def team(code,slug,home):
        rows=tables[code]['tables'];overall=next(r for r in rows['standings'] if r['slug']==slug)
        venue=next(r for r in rows['standingsHome' if home else 'standingsAway'] if r['slug']==slug)
        name,history=NAMES[slug]
        return dict(name=name,history_key=history,pj=overall['played'],gf=overall['goals_for'],gc=overall['goals_against'],
                    venue_pj=venue['played'],venue_gf=venue['goals_for'],venue_gc=venue['goals_against'])
    history=[];sources=[]
    for season in ('2425','2526','2627'):
        path=ROOT/'historical/raw'/f'{season}_SP1.csv';url=f'https://www.football-data.co.uk/mmz4281/{season}/SP1.csv'
        sources.append(dict(url=url,local=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),retrieved_at=STAMP if season=='2627' else '2026-10-26'))
        for r in csv.DictReader(path.read_text(encoding='utf-8-sig').splitlines()):
            if not r.get('FTHG') or not r.get('FTAG'):continue
            history.append(dict(division='SP1',date=datetime.strptime(r['Date'],'%d/%m/%Y').date().isoformat(),home=r['HomeTeam'],away=r['AwayTeam'],gh=int(r['FTHG']),ga=int(r['FTAG'])))
    history_input=dict(sources=sources,matches=history)
    snapshot=export(history_input,STAMP)
    save('snapshot_sp1_j11_20261026.json',snapshot)
    save('historial_sp1_j11_20261026.json',history_input)
    fixtures=[];inputs=[]
    for code in ('sp1','sp2','f'):
        source_rows=calendars[code]['matches']
        selected=source_rows if code=='sp1' else [next(m for m in source_rows if (m['home'],m['away'])==pair) for pair in EXTRAS[code]]
        for m in selected:
            assert m['status']=='PreMatch' and datetime.fromisoformat(m['kickoff'])>datetime.fromisoformat(STAMP)
            fixtures.append((code,m))
            inputs.append(dict(home=team(code,m['home'],True),away=team(code,m['away'],False),time=m['kickoff'],adjust_home=1.,adjust_away=1.,competition_code={'sp1':'SP1','sp2':'SP2','f':'LIGA_F'}[code]))
    payload=dict(cutoff=STAMP,matches=inputs,strength_snapshot=snapshot,sources=[v['source'] for v in tables.values()]+[COUPON,SER],
                 assumptions=['Cap ajust manual ni pesos individuals.','SER 26/10: context de plantilla provisional; sancions pendents de resolució llegida.','Sevilla–Osasuna en curs: sense incorporar resultat; PJ finals corregits a 9 en la referència v0.1.','Primera v0.2: paràmetres congelats al tall mensual 29/09, últim final anterior; dades actuals només en referència v0.1.','Copa del Rei pendent aquesta setmana: risc qualitatiu de descans i rotació, sense ajust numèric.'])
    forecast=predict_new(payload);assert not forecast['partial'];save('dades_j11_20261026.json',payload);save('previsio_j11_20261026.json',forecast)
    matches=[]
    context={
      'fc-barcelona':'SER del 26/10 assenyala Xavi Espart i Dani Olmo lesionats; convocatòria pendent.',
      'real-madrid':'SER del 26/10 assenyala Vinícius sancionat i Valverde com a dubte; falta contrastar la resolució federativa.',
      'getafe-cf':'SER del 26/10 assenyala Mario Martín i Mojica sancionats; falta contrastar la resolució federativa.',
      'rayo-vallecano':'SER del 26/10 assenyala Pathé Ciss sancionat; falta contrastar la resolució federativa.'}
    for (code,m),i,p in zip(fixtures,inputs,forecast['results']):
        h,a=i['home'],i['away'];note=f"Gols totals: {h['name']} {h['gf']}–{h['gc']} en {h['pj']} finals; {a['name']} {a['gf']}–{a['gc']} en {a['pj']}. "
        if code=='sp1':note+='v0.2 usa força d’atac/defensa, avantatge local estimat, regularització 2 i semivida de 365 dies. Tall d’ajust mensual: 29/09/2026; les estadístiques actuals només alimenten la referència v0.1, conservada a part. '
        else:note+='v0.1: gols globals i per seu, amb avantatge local; mostra encara limitada. '
        note+=' '.join(context[s] for s in (m['home'],m['away']) if s in context)
        note+=' Cap ajust manual. Convocatòries i descans després de la Copa encara pendents.'
        if code=='f':note+=' Aplicació experimental a Liga F sense validació específica.'
        matches.append(dict(home=h['name'],away=a['name'],kickoff=m['kickoff'],forecast=p,status='scheduled',result=None,
                            competition={'sp1':'LALIGA EA SPORTS','sp2':'LALIGA HYPERMOTION','f':'Liga F Moeve'}[code],confidence='Experimental · confiança baixa',note=note,
                            sources=[tables[code]['source'],m['source']]+([SER] if code=='sp1' else []),source_verified_at=STAMP))
    pm=matches[8];lh=pm['forecast']['lambda_home'];la=pm['forecast']['lambda_away'];pp={}
    for h in range(31):
        for a in range(31):
            k=('M' if h>=3 else str(h))+'-'+('M' if a>=3 else str(a));pp[k]=pp.get(k,0.)+math.exp(-lh-la)*lh**h*la**a/math.factorial(h)/math.factorial(a)
    total=sum(pp.values());pp={k:v/total for k,v in pp.items()}
    round11=dict(number=11,label='Previsió anticipada · cupó SELAE 18 provisional',period='30 d’octubre – 2 de novembre de 2026',forecast_at=STAMP,forecast_version='j11-20261026-anticipada-v02',model='0.2 Primera · 0.1 altres',publication_status='prepared_pending_publication',matches=matches,
       warning='Previsió anticipada del 26/10, abans de la data programada del 28/10. Primera: v0.2 amb suport retrospectiu, ajust mensual al 29/09; Segona i Liga F: v0.1. Lesions i sancions de premsa són context provisional, sense ajustos manuals. El Sevilla–Osasuna encara no té resultat final incorporat. Cupó provisional fins a verificar l’avís específic de tancament.',
       coupon_note='Cupó SELAE 18: 7 de Primera, 3 de Segona i 4 de Liga F. Ple al 15 Athletic–Reial Societat. Villarreal–Espanyol i Deportivo–Osasuna només pertanyen a la previsió de Lliga. Tenerife (F)–Athletic (F) consta el 2/11 al calendari oficial, tot i el rètol 31/10–1/11 del document del cupó.',
       official_coupon=dict(number=18,verified_at=STAMP,source=COUPON,local_reference='outputs/font_cupo_selae18_20261026.pdf',document_sha256=hashlib.sha256((OUT/'font_cupo_selae18_20261026.pdf').read_bytes()).hexdigest(),order_verified=True,match_indices=[1,2,3,4,5,6,7,10,11,12,13,14,15,16],deadline_status='pending',deadline_expected='2026-10-31T14:00:00+01:00',deadline_expected_source='https://www.pizarra15.es/jornada-18/',deadline_check_source=NOTICE,deadline_checked_at=STAMP,
                            composition_note='7 de Primera, 3 de Segona i 4 de Liga F; Ple al 15 Athletic–Reial Societat.',pleno15=dict(home=pm['home'],away=pm['away'],kickoff=pm['kickoff'],probabilities=pp)),
       review=dict(summary='Previsió anticipada preparada. Resultats i imports pendents; les probabilitats i columnes es conservaran un cop publicades.',next='Revisió el 3/11/2026 a les 10:00 de Barcelona. Verificar abans l’avís SELAE de tancament; la jornada de Lliga comença el 30/10 a les 21:00.',changes=['Primera: model v0.2 amb comparació v0.1 conservada per partit.','Segona i Liga F mantenen v0.1 segons la política del 26/10.','Imports futurs calculats per columna a partir d’escrutinis oficials.']),evaluation_scope=dict(sporting_forecasts=17,official_signs=14,pleno15_separate=True))
    round11['metrics']=metrics(matches,STAMP);round11['coupon']=coupon_for_round(round11)
    assert round11['coupon'].get('provisional_coupon') and len(round11['coupon']['matches'])==14 and not round11['coupon']['complete']
    data['rounds'].insert(0,round11);data['updated']=STAMP
    for r in data['rounds']:
        if r['number']==9:r['prize_table']=dict(status='verified',checked_at=STAMP,source=SCRUTINY,currency='EUR',categories_cents={'10':0,'11':222,'12':1276,'13':16526,'14':1116213},pleno15_cents=8077813,pleno15_adds_to_14=True,note='Imports bruts oficials per aposta simple; la categoria de 10 encerts és 0,00 €. No confirma validació ni cobrament de les columnes publicades.')
    for before,after in zip(original,data['rounds'][1:]):
        assert before['forecast_at']==after['forecast_at'] and before['coupon']==after['coupon']
        assert [m.get('forecast') for m in before['matches']]==[m.get('forecast') for m in after['matches']]
    save('seguiment.json',data)
    schedule=json.loads((OUT/'programacio.json').read_text());r=next(r for r in schedule['rounds'] if r['number']==11)
    r.update(forecast_status='prepared_pending_publication',forecast_actual_at=STAMP,forecast_note='Previsió anticipada preparada el 26/10 per petició expressa; no s’ha avançat fictíciament la data de publicació.',coupon_number=18,coupon_first_match='2026-10-31',coupon_last_match='2026-11-02',coupon_deadline_status='pending',coupon_deadline_expected='2026-10-31T14:00:00+01:00',coupon_source=COUPON)
    schedule['checked_at']=STAMP;save('programacio.json',schedule)
    print(json.dumps(dict(cutoff=STAMP,snapshot_last_train=snapshot['last_train'],n_train=snapshot['n_train'],columns=[c['signs'] for c in round11['coupon']['columns']],pleno15=round11['coupon']['pleno15']),ensure_ascii=False))


if __name__=='__main__':main()
