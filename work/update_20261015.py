"""Revisió J8 i previsió J9 amb dades verificades el 15/10/2026.

Fonts llegides manualment abans d'executar el model. No consulta marcadors
automàticament ni modifica les probabilitats de jornades anteriors.
"""
import copy
import importlib.util
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_dashboard import metrics
from coupons import coupon_for_round

ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now(ZoneInfo('Europe/Madrid')).isoformat(timespec='seconds')
FIRST = 'https://www.laliga.com/laliga-easports/clasificacion'
SECOND = 'https://www.laliga.com/laliga-hypermotion/clasificacion'
WOMEN = 'https://www.laliga.com/futbol-femenino/clasificacion'
J8 = 'https://www.laliga.com/laliga-easports/resultados/2026-27/jornada-8'
J9 = 'https://www.laliga.com/laliga-easports/resultados/2026-27/jornada-9'
J10 = 'https://www.laliga.com/laliga-hypermotion/resultados'
F7 = 'https://www.laliga.com/futbol-femenino/resultados'
SELAE_RESULTS = 'https://www.loteriasyapuestas.es/es/la-quiniela/resultados/la-quiniela-resultados-del-11-de-octubre-de-2026'
SELAE_ZIP = 'https://www.loteriasyapuestas.es/f/loterias/web_corporativa/Comunicacion/Avisos_de_interes/COMPOSICI%C3%93N%20DE%20BOLETOS%20JORNADAS%2013%20Y%2014%20DE%20LA%20QUINIELA%20Y%20ELIGE%208%20Y%20JORNADAS%2014%20Y%2015%20DEL%20QUINIGOL.zip'
DEADLINE_SOURCE = 'https://www.loteriasyapuestas.es/f/loterias/web_corporativa/Comunicacion/Avisos_de_interes/Aviso%20cierre%20La%20Quiniela%20jornada%2014%C2%AA%20y%20El%20QuiniGol%20jornada%2015%C2%AA%20de%2017%20-%2018%20de%20Octubre%20de%202026.pdf'
DISCIPLINE = 'https://rfef.es/sites/default/files/sanciones/20261014_Primera_Division_J8.pdf?cb=e8fd8730'
SER = 'https://cadenaser.com/nacional/2026/10/13/laliga-fantasy-jugadores-sancionados-y-lesionados-para-la-jornada-9-y-posibles-sustitutos-cadena-ser/'
BARCA = 'https://www.fcbarcelona.es/es/futbol/primer-equipo/resultats'
MADRID = 'https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/cronicas/cronica-roma-real-madrid-14-10-2026/'

# Cada fila: nom, PJ/GF/GC totals, PJ/GF/GC a la seu del proper partit.
# Els partits suspesos no s'inclouen en aquests totals oficials.
ROWS = [
    ('Deportivo', 8,12,11, 4,5,4), ('Llevant', 7,11,15, 4,1,6),
    ('Espanyol', 8,11,11, 4,6,6), ('Atlètic de Madrid', 8,18,8, 4,8,5),
    ('Villarreal', 8,13,13, 3,6,6), ('Elx', 8,11,17, 4,7,6),
    ('Betis', 8,14,9, 4,8,2), ('Barcelona', 8,34,7, 4,17,3),
    ('València', 8,6,15, 4,2,9), ('Athletic', 6,7,6, 2,2,2),
    ('Osasuna', 8,8,18, 4,2,3), ('Racing', 8,13,23, 4,4,16),
    ('Celta', 8,8,6, 4,7,5), ('Alabès', 8,12,8, 3,2,3),
    ('Màlaga', 8,4,13, 4,3,5), ('Reial Societat', 8,12,15, 4,7,9),
    ('Real Madrid', 8,19,8, 4,13,2), ('Sevilla', 8,13,12, 4,8,5),
    ('Getafe', 8,4,10, 4,4,2), ('Rayo', 7,11,16, 4,5,12),
    ('Eibar', 9,19,10, 4,8,5), ('Mallorca', 9,11,4, 4,1,2),
    ('Las Palmas', 9,13,16, 4,5,5), ('Castelló', 9,15,4, 5,7,3),
    ('Burgos', 9,12,10, 5,9,6), ('Sabadell', 9,10,7, 5,3,4),
    ('Athletic (F)', 6,11,8, 3,8,5), ('València (F)', 6,4,13, 3,2,7),
    ('Real Madrid (F)', 6,13,13, 3,6,3), ('Espanyol (F)', 6,9,6, 3,3,4),
    ('Eibar (F)', 6,4,4, 3,3,4), ('Deportivo (F)', 6,5,6, 2,3,0),
    ('Atlètic de Madrid (F)', 6,10,11, 2,2,0), ('Madrid CFF (F)', 6,11,9, 2,4,6),
]
FIELDS = ['name','pj','gf','gc','venue_pj','venue_gf','venue_gc']
TEAMS = {r[0]: dict(zip(FIELDS,r)) for r in ROWS}

# Ordre cronològic de Primera, després els set partits addicionals del cupó.
FIXTURES = [
    ('Deportivo','Llevant','2026-10-16T21:00:00+02:00'),
    ('Espanyol','Atlètic de Madrid','2026-10-17T14:00:00+02:00'),
    ('Villarreal','Elx','2026-10-17T16:15:00+02:00'),
    ('Betis','Barcelona','2026-10-17T18:30:00+02:00'),
    ('València','Athletic','2026-10-17T21:00:00+02:00'),
    ('Osasuna','Racing','2026-10-18T14:00:00+02:00'),
    ('Celta','Alabès','2026-10-18T16:15:00+02:00'),
    ('Màlaga','Reial Societat','2026-10-18T18:30:00+02:00'),
    ('Real Madrid','Sevilla','2026-10-18T21:00:00+02:00'),
    ('Getafe','Rayo','2026-10-19T21:00:00+02:00'),
    ('Eibar','Mallorca','2026-10-17T16:15:00+02:00'),
    ('Las Palmas','Castelló','2026-10-17T21:00:00+02:00'),
    ('Burgos','Sabadell','2026-10-18T21:00:00+02:00'),
    ('Athletic (F)','València (F)','2026-10-17T16:30:00+02:00'),
    ('Real Madrid (F)','Espanyol (F)','2026-10-17T20:30:00+02:00'),
    ('Eibar (F)','Deportivo (F)','2026-10-18T16:00:00+02:00'),
    ('Atlètic de Madrid (F)','Madrid CFF (F)','2026-10-18T18:00:00+02:00'),
]
NOTES = [
    'Deportivo té 12–11 en gols en 8 partits; Llevant, 11–15 en 7. La RFEF sanciona Amatucci: preval sobre la llista de SER del dia 13 que no el recull. Disponibilitat ofensiva pendent de convocatòria.',
    'Atlètic: 18–8 en gols en 8 partits; Espanyol, 11–11. SER assenyala Kike García lesionat i Jofre com a dubte. No es pressuposa cap alineació definitiva.',
    'Villarreal té només tres partits a casa: mostra petita. Elx: 7–6 en gols fora. Les incidències de plantilla queden pendents de convocatòria; no es considera confirmada una sanció sense resolució llegida.',
    'Barcelona: 8 victòries i 34–7 en gols. Betis ha guanyat els quatre partits a casa, 8–2 en gols. El Barça va jugar a Istanbul el 13/10; Raphinha i De Jong consten com a dubtes a SER del 13/10. El risc de rotació és una inferència, no una baixa confirmada.',
    'València: 6–15 en gols, i 2–9 a casa. Athletic només té 6 partits finals i dos fora; Rayo–Athletic continua suspès. SER situa Sancet lesionat i Nico Williams com a dubte. Mostra visitant especialment limitada.',
    'Osasuna: 2–3 en gols a casa; Racing: 4–16 fora. Són quatre partits per seu. El model no corregeix la força dels rivals i la preferència local depèn d’una mostra petita.',
    'Celta: 8–6 en gols totals; Alabès, 12–8. Ángel Pérez té un partit de sanció segons la RFEF. La càrrega de totes les competicions i les convocatòries encara no s’han verificat de manera homogènia.',
    'Màlaga no ha guanyat en 8 partits i suma 4–13 en gols. Reial Societat: 12–15 totals i 7–9 fora. Pablo Marín té un partit de sanció segons la RFEF.',
    'Real Madrid: 13–2 en gols a casa; Sevilla: 8–5 fora. La RFEF sanciona Vinícius i Isaac Romero. El Madrid va jugar a Roma el 14/10: hi ha menys descans que en una setmana ordinària, sense impacte numèric calibrat.',
    'Getafe: 4–2 en gols a casa, invicte en quatre partits. Rayo: 5–12 fora; el seu partit anterior contra Athletic no té resultat final. Les baixes i la càrrega europea no es donen per resoltes abans de la convocatòria.',
    'Eibar: 19–10 en gols en 9 partits; Mallorca: 11–4. Fora, Mallorca només ha marcat un gol i n’ha rebut dos en quatre partits. Últim partit d’Eibar: derrota 3–1 a Oviedo. Sense ajust addicional per ratxa.',
    'Castelló: 15–4 en gols en 9 partits, 7–3 fora. Las Palmas: 13–16, 5–5 a casa. Estadístiques actualitzades després del 3–1 de Mallorca i l’1–0 d’Andorra; sense duplicar aquests resultats com a ajust de forma.',
    'Burgos: 12–10 en gols en 9 partits i 9–6 a casa; Sabadell: 10–7 i 3–4 fora. El 0–1 de Burgos contra Granada ja forma part dels totals. Convocatòries encara pendents.',
    'Athletic (F): 11–8 en gols en sis partits i 8–5 a casa. València (F) ha perdut els sis partits, 4–13 en gols. Aplicació exploratòria del mateix Poisson: sense calibratge específic de Liga F ni baixes verificades exhaustivament.',
    'Real Madrid (F): 13–13 en gols en sis partits, però 6–3 a casa. Espanyol (F): 9–6, i 3–4 fora. L’empat té pes apreciable. Sense verificació completa de baixes o càrrega europea; transferència del model no validada.',
    'Eibar (F): només 4 gols a favor i 4 en contra en sis partits. Deportivo (F): 5–6, i 3–0 fora en només dos partits. Mostra petita i model sense calibratge específic; no interpretar el signe com una certesa.',
    'Atlètic (F): 10–11 en gols; Madrid CFF (F): 11–9. Només dos partits a la seu rellevant per equip: Atlètic 2–0 a casa i Madrid CFF 4–6 fora. Mostra especialment petita i transferència del Poisson no validada.',
]


def save(name, value):
    (ROOT/'outputs'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def review_round(data):
    r = next(r for r in data['rounds'] if r['number']==8)
    old_coupon = copy.deepcopy(r['coupon'])
    final = {('Llevant','Sevilla'):[3,3], ('Burgos','Granada'):[0,1], ('Oviedo','Eibar'):[3,1]}
    for version in [r, *r.get('history',[])]:
        for m in version['matches']:
            key = (m['home'],m['away'])
            if key in final:
                m.update(result=final[key],status='final',result_source=SELAE_RESULTS,result_verified_at=STAMP)
            if key == ('Rayo','Athletic'):
                assert m['result'] is None
                m.update(status='suspended',status_source=J8,status_verified_at=STAMP,
                         rescheduled_kickoff=None,status_note='Suspès; sense resultat esportiu final ni nova data confirmada al tall del 15/10.')
        version['metrics'] = metrics(version['matches'],version['forecast_at'])
    signs = ['X','2','1','X','1','1','X','X','1','1','1','1','2','1']
    for i,s in enumerate(signs,1):
        # Conserva la resolució especial de la suspensió com a font pròpia.
        if i!=1:
            r['coupon_results']['signs'][str(i)] = dict(status='verified',sign=s,
                    method='match',source=SELAE_RESULTS,checked_at=STAMP)
    r['coupon_results'].update(checked_at=STAMP,source=SELAE_RESULTS,status='complete',
                             sporting_results_awaiting_selae=[],pending_special_cases=[])
    r['coupon_results']['pleno15'].update(source=SELAE_RESULTS,checked_at=STAMP)
    column_results = [dict(column=i+1,hits=sum(a==b for a,b in zip(c['signs'],signs)),n=14)
                      for i,c in enumerate(r['coupon']['columns'])]
    by_competition = {c:metrics([m for m in r['matches'] if m.get('competition')==c],r['forecast_at'])
                      for c in ['LALIGA EA SPORTS','LALIGA HYPERMOTION']}
    total = r['metrics']
    r['label'] = 'Revisió provisional · 7/15 · cupó 12 tancat'
    r['review'].update(
        summary='7 encerts de signe sobre 15 partits esportius finals (46,67%): Primera 4/9 i Segona 3/6. Rayo–Athletic continua suspès i fora de les mètriques. Cupó SELAE 12 complet: les quatre columnes fan 6/14, 5/14, 6/14 i 5/14. Ple al 15: 1–0, error respecte al M–1 previst.',
        next='Cupó tancat i revisió esportiva provisional completada el 15/10. Revisió esportiva final pendent de la represa de Rayo–Athletic; l’endemà del seu resultat final a les 10:00 de Barcelona.',
        status='provisional_completed_pending_suspended_match',last_result_check=STAMP,
        reviewed_at=STAMP,metrics=total,metrics_by_competition=by_competition,
        column_results=column_results,
        changes=[
            'Es conserva el model 0.1 i totes les probabilitats, signes, marcadors i dates de tall originals. No s’ajusten els pesos amb aquests resultats.',
            'Quatre empats a Primera van acabar en errors de signe (Màlaga–Espanyol, Elx–Celta, Racing–València i Llevant–Sevilla). Els empats ja tenien probabilitat positiva; aquest resultat no justifica afavorir-los retrospectivament.',
            'Brier i pèrdua logarítmica es calculen només sobre 15 resultats esportius finals, separant les competicions. La X administrativa de Rayo–Athletic només compta per a les 14 caselles SELAE.',
            'Hipòtesis pendents de validació cronològica: força dels rivals, millor calibratge dels empats i un model específic per competició. La mostra encara és massa petita per afirmar una millora estable.',
        ])
    r['monitoring_notice'] = r['review']['summary']
    r['monitoring_sources'] = [J8,SELAE_RESULTS,DISCIPLINE]
    assert r['coupon']==old_coupon
    save('revisio_j8_20261015.json',dict(checked_at=STAMP,round=8,coupon_number=12,
        metrics=total,metrics_by_competition=by_competition,column_results=column_results,
        official_signs=signs,pleno15=dict(predicted='M-1',actual='1-0',hit=False),
        suspended=['Rayo – Athletic'],sources=r['monitoring_sources']))


def forecast_round(data):
    assert not any(r['number']==9 for r in data['rounds']), 'No substituir una previsió existent.'
    spec=importlib.util.spec_from_file_location('model',ROOT/'outputs/model_quiniela_v1.py')
    model=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    matches=[]
    inputs=[]
    for i,(h,a,t) in enumerate(FIXTURES):
        assert datetime.fromisoformat(STAMP)<datetime.fromisoformat(t)
        src,fixtures,comp = (FIRST,J9,'LALIGA EA SPORTS') if i<10 else (SECOND,J10,'LALIGA HYPERMOTION') if i<13 else (WOMEN,F7,'Liga F Moeve')
        entry=dict(home=TEAMS[h],away=TEAMS[a],time=t,adjust_home=1.0,adjust_away=1.0,
                   competition=comp,source=src)
        f=model.predict(entry)
        assert all(math.isfinite(p) and 0<=p<=1 for p in f['probabilities'].values())
        assert abs(sum(f['probabilities'].values())-1)<1e-10
        assert sum(f['percentages'].values())==100
        sources=[src,fixtures]+([DISCIPLINE] if i in [0,6,7,8] else [])
        if i<10: sources.append(SER)
        if i==3: sources.append(BARCA)
        if i==8: sources.append(MADRID)
        matches.append(dict(home=h,away=a,kickoff=t,forecast=f,status='scheduled',result=None,
            competition=comp,confidence='Experimental · confiança baixa' if i>=13 or max(f['probabilities'].values())<.55 else 'Experimental · confiança moderada',
            note=NOTES[i]+' Ajustos numèrics: 1.0 per equip; cap correcció manual. Gols de lliga exclusivament; les notícies són context qualitatiu.',
            sources=sources,source_verified_at=STAMP))
        inputs.append(entry)
    assumptions=('Poisson 0.1 sense reentrenament ni canvi de pesos. Estadístiques oficials totals i per seu al tall; '
        'ajustos 1.0. No xG ni correcció per força dels rivals. Sancions contrastades amb RFEF; '
        'lesions i descans només qualitatius. No hi ha una verificació homogènia de totes les convocatòries. '
        'Aplicació exploratòria a Liga F: prior de gols 1.3 heretat, no calibrat específicament; confiança baixa.')
    r=dict(number=9,label='Previsió · cupó SELAE 14 complet',period='16–19 d’octubre de 2026',
        forecast_at=STAMP,forecast_version='j9-20261015-cupo14',model='0.1',
        warning='Previsió del 15/10, amb retard respecte del 14/10 a les 10:00, però abans de tots els partits. Probabilitats experimentals sense calibratge suficient; convocatòries i càrrega de totes les competicions incompletes. Liga F: aplicació exploratòria del model, sense validació específica. Ajustos manuals: cap.',
        coupon_note='SELAE jornada 14, numeració diferent de la jornada 9 de Primera. Cupó verificat: 7 partits de Primera, 3 de Segona i 4 de Liga F entre els 14 signes. Ple al 15: Getafe–Rayo. Deportivo–Llevant i Osasuna–Racing només pertanyen a la previsió de lliga.',
        matches=matches,review=dict(summary='Jornada encara no començada. Cap resultat avaluable.',
            next='Revisió prevista el 20/10/2026 a les 10:00 de Barcelona; Mac disponible des de les 09:50.',changes=[]),
        evaluation_scope='17 pronòstics esportius: 10 de Primera, 3 de Segona i 4 de Liga F. Separar competicions i les 14 caselles SELAE.',
        publication_status='prepared_pending_confirmation')
    p15=matches[9]['forecast']
    def categories(lam):
        p=[math.exp(-lam)*lam**k/math.factorial(k) for k in range(3)]
        return dict(zip(['0','1','2','M'],p+[1-sum(p)]))
    ph,pa=categories(p15['lambda_home']),categories(p15['lambda_away'])
    pp={h+'-'+a:ph[h]*pa[a] for h in ph for a in pa}
    r['official_coupon']=dict(number=14,verified_at=STAMP,source=SELAE_ZIP,
        local_reference='outputs/font_cupo_selae14_20261006.pdf',
        deadline_source=DEADLINE_SOURCE,deadline='2026-10-17T14:00:00+02:00',
        match_indices=[1,2,3,4,6,7,8,10,11,12,13,14,15,16],
        composition_note='7 de Primera, 3 de Segona i 4 de Liga F; Getafe–Rayo al Ple al 15.',
        pleno15=dict(home='Getafe',away='Rayo',kickoff=matches[9]['kickoff'],probabilities=pp))
    r['coupon']=coupon_for_round(r)
    assert r['coupon']['complete']
    r['coupon']['publication_status']='prepared_pending_confirmation'
    r['metrics']=metrics(matches,STAMP)
    data['rounds'].insert(0,r)
    save('dades_j9_20261015.json',dict(cutoff=STAMP,round=9,assumptions=assumptions,
        verified_facts=dict(standings=[FIRST,SECOND,WOMEN],fixtures=[J9,J10,F7],
            coupon=SELAE_ZIP,deadline=DEADLINE_SOURCE,discipline=DISCIPLINE),
        heuristic_adjustments=[],matches=inputs))
    save('previsio_j9_20261015.json',copy.deepcopy(r))


def main():
    data=json.loads((ROOT/'outputs/seguiment.json').read_text())
    review_round(data)
    forecast_round(data)
    data['updated']=STAMP
    save('seguiment.json',data)
    schedule=json.loads((ROOT/'outputs/programacio.json').read_text())
    schedule.update(verified_at=STAMP[:10],checked_at=STAMP)
    for r in schedule['rounds']:
        if r['number']==8:
            r.update(review_status='provisional_completed',review_actual_at=STAMP,
                coupon_review_status='completed',review_note='Cupó SELAE 12 tancat; revisió esportiva provisional feta el 15/10. Rayo–Athletic continua pendent de resultat final i data de represa.',postponement_source=J8)
        if r['number']==9:
            r.update(forecast_status='prepared_pending_confirmation',forecast_actual_at=STAMP,
                forecast_note='Previsió preparada el 15/10, un dia després de la cita prevista del 14/10. Publicació pendent de confirmació.',
                source=J9,coupon_number=14,coupon_first_match='2026-10-17',coupon_last_match='2026-10-19',
                coupon_forecast_due='2026-10-15T10:00:00+02:00')
    save('programacio.json',schedule)
    print(json.dumps({'cutoff':STAMP,'review':data['rounds'][1]['metrics'],
        'competitions':data['rounds'][1]['review']['metrics_by_competition'],
        'columns':data['rounds'][0]['coupon']['columns'],
        'coverage':data['rounds'][0]['coupon']['coverage'],
        'pleno15':data['rounds'][0]['coupon']['pleno15'],
        'forecasts':[(m['home'],m['away'],m['forecast']['percentages'],m['forecast']['sign']) for m in data['rounds'][0]['matches']]},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
