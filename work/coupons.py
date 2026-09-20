"""Four most likely distinct 1/X/2 columns, using unrounded probabilities."""
import math
from datetime import datetime

SIGNS = ('1', 'X', '2')

def top_columns(probabilities, count=4):
    if not probabilities:
        return []
    best = [(1.0, '')]
    for p in probabilities:
        if set(p) != set(SIGNS) or any(not math.isfinite(v) or v < 0 or v > 1 for v in p.values()) or not math.isclose(sum(p.values()), 1, abs_tol=1e-8):
            raise ValueError('Probabilitats 1/X/2 invàlides')
        best = sorted(((mass * p[s], signs + s) for mass, signs in best for s in SIGNS), key=lambda x: (-x[0], x[1]))[:count]
    return [{'signs': list(signs), 'probability': mass} for mass, signs in best]

def coupon_for_round(r):
    matches = [m for m in r['matches'] if m.get('forecast')]
    official = r.get('official_coupon', {})
    complete = False
    reason = 'Falta verificar el cupó oficial de 14 partits i el Ple al 15.'
    if official.get('verified_at') and official.get('source') and len(official.get('match_indices', [])) == 14:
        indices = official['match_indices']
        if len(set(indices)) == 14 and all(isinstance(i, int) and 0 <= i < len(r['matches']) for i in indices):
            ordered = [r['matches'][i] for i in indices]
            try:
                cutoff = datetime.fromisoformat(r['forecast_at'])
                complete = all(m.get('forecast') and datetime.fromisoformat(m['kickoff']) > cutoff for m in ordered)
                complete = complete and cutoff < datetime.fromisoformat(official['deadline'])
                pleno = official['pleno15']
                pp = pleno['probabilities']
                keys = {h+'-'+a for h in ('0','1','2','M') for a in ('0','1','2','M')}
                complete = complete and bool(pleno['home'] and pleno['away']) and cutoff < datetime.fromisoformat(pleno['kickoff'])
                complete = complete and set(pp) == keys and all(math.isfinite(v) and 0 <= v <= 1 for v in pp.values()) and math.isclose(sum(pp.values()), 1, abs_tol=1e-8)
            except (KeyError, ValueError, TypeError):
                complete = False
            if complete:
                matches = ordered
    columns = top_columns([m['forecast']['probabilities'] for m in matches])
    result = {'complete': complete, 'reason': '' if complete else reason, 'matches': [{'home':m['home'], 'away':m['away']} for m in matches], 'columns':columns, 'coverage':sum(c['probability'] for c in columns), 'objective':'all_signs', 'generated_from':r['forecast_at']}
    if complete:
        score = min(pp, key=lambda s: (-pp[s], s))
        result['pleno15'] = {'home':pleno['home'], 'away':pleno['away'], 'score':score, 'probability':pp[score]}
        result['deadline'] = official['deadline']
        result['source'] = official['source']
    return result
