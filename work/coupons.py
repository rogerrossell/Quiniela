"""Four most likely distinct 1/X/2 columns, using unrounded probabilities."""
import math
from datetime import datetime

SIGNS = ('1', 'X', '2')

def condensed_columns(columns):
    """Cartesian envelope; explicitly count any columns added by doubles/triples."""
    if not columns:
        return {'signs': [], 'expanded_count': 0, 'additional_count': 0, 'exact': True}
    size = len(columns[0]['signs'])
    if any(len(c['signs']) != size or any(s not in SIGNS for s in c['signs']) for c in columns):
        raise ValueError('Columnes incompatibles')
    choices = [''.join(s for s in SIGNS if any(c['signs'][i] == s for c in columns)) for i in range(size)]
    expanded = math.prod(len(s) for s in choices)
    distinct = len({tuple(c['signs']) for c in columns})
    return {'signs': choices, 'expanded_count': expanded, 'additional_count': expanded - distinct, 'exact': expanded == distinct}

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
    result['condensed'] = condensed_columns(columns)
    if complete:
        score = min(pp, key=lambda s: (-pp[s], s))
        result['pleno15'] = {'home':pleno['home'], 'away':pleno['away'], 'score':score, 'probability':pp[score]}
        result['deadline'] = official['deadline']
        result['source'] = official['source']
    return result
