"""Premi brut teòric de cada columna simple; no confirma joc ni cobrament."""
from datetime import datetime


def evaluate_prizes(r):
    c=r.get('coupon',{});ms=c.get('matches',[])
    if not c.get('complete') or len(ms)!=14:
        return dict(status='not_evaluable',reason='Cupó parcial o provisional; no equival a una aposta oficial completa.',columns=[],total_cents=None)
    results=r.get('coupon_results',{});signs=[]
    published=c.get('published_at') or r.get('forecast_published_at') or r['forecast_at']
    for i,cm in enumerate(ms):
        m=next((m for m in r['matches'] if m['home']==cm['home'] and m['away']==cm['away']),None)
        if not m or datetime.fromisoformat(published)>=datetime.fromisoformat(m['kickoff']):
            return dict(status='not_evaluable',reason='Publicació anterior a l’inici no confirmada.',columns=[],total_cents=None)
        official=results.get('signs',{}).get(str(i+1),{})
        if official.get('status')=='verified' and official.get('source') and official.get('sign') in ('1','X','2'):
            signs.append(official['sign'])
        elif m.get('status')=='final' and m.get('result') is not None and m.get('result_source'):
            h,a=m['result'];signs.append('1' if h>a else '2' if h<a else 'X')
        else:signs.append(None)
    n=sum(s is not None for s in signs);table=r.get('prize_table',{})
    verified=table.get('status')=='verified' and bool(table.get('source'))
    po=results.get('pleno15',{});pleno=None
    if po.get('status')=='verified' and po.get('source'):pleno=po.get('score')
    columns=[]
    for i,col in enumerate(c['columns']):
        hits=sum(s==p for s,p in zip(signs,col['signs']) if s is not None)
        amount=None;category=None;status='pending_results' if n<14 else 'pending_scrutiny'
        if n==14 and hits<10:
            amount=0;category='Sense categoria de premi';status='verified_zero_below_10'
        elif n==14 and verified:
            category=f'{hits} encerts'
            amount=table.get('categories_cents',{}).get(str(hits))
            if hits==14:
                if pleno is None:amount=None
                elif pleno==c['pleno15']['score']:
                    category='14 encerts + Ple al 15'
                    special=table.get('pleno15_cents')
                    if special is None or amount is None or table.get('pleno15_adds_to_14') is not True:amount=None
                    else:amount+=special
            if amount is not None:
                if type(amount) is not int or amount<0:raise ValueError('Import oficial invàlid')
                status='verified_scrutiny'
        columns.append(dict(column=i+1,hits=hits,resolved=n,category=category,amount_cents=amount,status=status))
    total=sum(x['amount_cents'] for x in columns) if all(x['amount_cents'] is not None for x in columns) else None
    return dict(status='complete' if total is not None else 'pending',columns=columns,total_cents=total,currency='EUR',
                source=table.get('source') if verified else None,checked_at=table.get('checked_at'),
                note='Import brut teòric per una aposta simple de cada columna, segons els signes publicats. No confirma que s’hagin validat ni cobrat apostes. Sense Elige8 ni despeses; no és un benefici net.')
