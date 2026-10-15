"""Informe llegible i confirmació de publicació, sense recalcular previsions."""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def write_json(name,data):
    (ROOT/'outputs'/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def confirm(published_at):
    # Només s'invoca després de la confirmació positiva de Sites.
    published=datetime.fromisoformat(published_at)
    data=json.loads((ROOT/'outputs/seguiment.json').read_text())
    r=next(r for r in data['rounds'] if r['number']==9)
    assert datetime.fromisoformat(r['forecast_at'])<=published
    assert all(published<datetime.fromisoformat(m['kickoff']) for m in r['matches'])
    for item in [r,r['coupon']]:
        item.update(publication_status='published_site',published_at=published_at)
    r['forecast_published_at']=published_at
    data['updated']=published_at
    previous=next(r for r in data['rounds'] if r['number']==8)
    previous['review'].update(publication_status='published_site',published_at=published_at)
    write_json('seguiment.json',data)
    write_json('previsio_j9_20261015.json',r)
    schedule=json.loads((ROOT/'outputs/programacio.json').read_text())
    for item in schedule['rounds']:
        if item['number']==9:
            item.update(forecast_status='completed',forecast_published_at=published_at,
                forecast_note='Publicació confirmada el 15/10, amb un dia de retard respecte de la previsió de lliga del 14/10; abans de tots els partits. Cupó SELAE 14 verificat.')
    write_json('programacio.json',schedule)


def report():
    data=json.loads((ROOT/'outputs/seguiment.json').read_text())
    r=next(r for r in data['rounds'] if r['number']==9)
    previous=next(r for r in data['rounds'] if r['number']==8)
    t=previous['metrics']
    lines=['# Quiniela · revisió i previsió del 15/10/2026','',
        f"Tall: {r['forecast_at']} (Europe/Madrid). Publicació: {r.get('published_at','pendent de confirmació')}",'',
        f"Jornada 8 de Primera / cupó SELAE 12: {t['hits']}/{t['n']} encerts esportius ({t['accuracy']:.2%}). Brier multicategoria: {t['brier']:.6f}; pèrdua logarítmica: {t['logloss']:.6f}.",
        'Primera: 4/9 (44,44%). Segona: 3/6 (50%). Rayo–Athletic continua suspès: no es compta com a resultat esportiu final.',
        'Quatre columnes originals: 6/14, 5/14, 6/14 i 5/14. Ple al 15 previst M–1; resultat 1–0: error.',
        '', '## Propera previsió · Primera J9 / cupó SELAE 14', '',
        '14 signes en ordre oficial. 1 = local; X = empat; 2 = visitant. (F) = Liga F.', '',
        '| # | Partit | 1 | X | 2 | Signe | Doble | Col. 1 | Col. 2 | Col. 3 | Col. 4 |',
        '|---|---|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|:---:|']
    c=r['coupon']
    for pos,idx in enumerate(r['official_coupon']['match_indices']):
        m=r['matches'][idx]; f=m['forecast']; p=f['percentages']
        cols=' | '.join(col['signs'][pos] for col in c['columns'])
        lines.append(f"| {pos+1} | {m['home']} – {m['away']} | {p['1']}% | {p['X']}% | {p['2']}% | {f['sign']} | {f['double']} | {cols} |")
    lines += ['',f"Ple al 15: Getafe–Rayo, {c['pleno15']['score']} ({c['pleno15']['probability']:.2%}).",
        f"Cobertura conjunta estimada de 14 encerts de les quatre columnes: {c['coverage']:.6%}, sense incloure el Ple al 15. Hipòtesi d’independència i model sense calibratge suficient.",
        'Condensació exacta: 12 a les caselles 1 i 6, amb els altres signes de la columna 1. Quatre columnes, cap combinació addicional.',
        'Tancament oficial: dissabte 17/10/2026 a les 14:00 de Barcelona.', '',
        'Fora del cupó: Deportivo–Llevant (1; 50/24/26%) i Osasuna–Racing (1; 49/22/29%).', '',
        r['warning'],
        'Sancions documentades: Amatucci, Ángel Pérez, Pablo Marín, Vinícius i Isaac Romero. Ajustos manuals: cap; no s’ha validat encara l’impacte numèric individual de les baixes.',
        'Revisió prevista: 20/10 a les 10:00 de Barcelona; Mac disponible a les 09:50. La revisió final de la J8 espera el Rayo–Athletic.', '',
        '## Fonts', '',
        f"- [Resultats oficials del cupó 12]({previous['coupon_results']['source']})",
        f"- [Composició oficial dels cupons 13 i 14 (ZIP)]({r['official_coupon']['source']})",
        f"- [Tancament oficial]({r['official_coupon']['deadline_source']})"]
    for url in sorted({s for m in r['matches'] for s in m['sources']}):
        lines.append(f'- {url}')
    lines += ['', 'Probabilitats experimentals; no són certeses. La mostra no permet conclusions fortes sobre el model.']
    (ROOT/'outputs/revisio_i_previsio_20261015.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    if len(sys.argv)>1:
        confirm(sys.argv[1])
    report()
