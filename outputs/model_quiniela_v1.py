"""Prototip local: python3 model_quiniela_v1.py dades_j7.json.
Entrada revisada manualment; no consulta dades en directe ni fa apostes.
"""
import json
import math
import sys
from pathlib import Path


def rate(team, field):
    overall = (team[field] + 4 * 1.3) / (team['pj'] + 4)
    venue = (team['venue_' + field] + 4 * 1.3) / (team['venue_pj'] + 4)
    return .75 * overall + .25 * venue


def predict(match):
    h, a = match['home'], match['away']
    lh = (rate(h, 'gf') + rate(a, 'gc')) / 2 * 1.10 * match['adjust_home']
    la = (rate(a, 'gf') + rate(h, 'gc')) / 2 * .90 * match['adjust_away']
    cells = [(i, j, math.exp(-lh-la) * lh**i * la**j / math.factorial(i) / math.factorial(j))
             for i in range(31) for j in range(31)]
    mass = sum(p for _, _, p in cells)
    probs = {s: sum(p for i, j, p in cells if ('1' if i > j else '2' if i < j else 'X') == s) / mass
             for s in ['1', 'X', '2']}
    raw = {s: 100 * p for s, p in probs.items()}
    rounded = {s: math.floor(v) for s, v in raw.items()}
    for s in sorted(raw, key=lambda s: raw[s] - rounded[s], reverse=True)[:100-sum(rounded.values())]:
        rounded[s] += 1
    best = sorted(probs, key=probs.get, reverse=True)
    return {'match': h['name'] + ' – ' + a['name'], 'time': match['time'],
            'lambda_home': lh, 'lambda_away': la, 'probabilities': probs,
            'percentages': rounded, 'sign': best[0],
            'double': ''.join(s for s in ['1', 'X', '2'] if s in best[:2]),
            'top_scores': [{'score': f'{i}-{j}', 'probability': p / mass}
                           for i, j, p in sorted(cells, key=lambda x: x[2], reverse=True)[:3]]}


if __name__ == '__main__':
    data = json.loads(Path(sys.argv[1]).read_text())
    results = [predict(m) for m in data['matches']]
    assert all(abs(sum(r['probabilities'].values()) - 1) < 1e-10 for r in results)
    assert all(sum(r['percentages'].values()) == 100 for r in results)
    print(json.dumps({'version': '0.1-experimental', 'cutoff': data['cutoff'], 'results': results}, ensure_ascii=False, indent=2))
