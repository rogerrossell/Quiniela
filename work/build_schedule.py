import json, re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

def events_for(data):
    events=[]
    zone=ZoneInfo(data['timezone'])
    for r in data['rounds']:
        for kind,day,status in [('Previsió',date.fromisoformat(r['first_match'])-timedelta(days=2),r['forecast_status']),('Anàlisi',date.fromisoformat(r['last_match'])+timedelta(days=1),r['review_status'])]:
            if status in ['completed','late_partial_completed','provisional_completed']:
                continue
            when=datetime.combine(day,datetime.min.time(),zone).replace(hour=data['execution_hour'])
            provisional=kind=='Anàlisi' and status=='pending_provisional'
            event_kind='Anàlisi provisional' if provisional else kind
            events.append(dict(round=r['number'],kind=event_kind,provisional=provisional,note=r.get('review_note','') if kind=='Anàlisi' else '',start=when.isoformat(),mac_ready=(when-timedelta(minutes=data['mac_ready_minutes'])).isoformat(),source=r['source'],first_match=r['first_match'],last_match=r['last_match'],status=status))
        if r.get('pending_matches') and r.get('final_review_date') and r['review_status'] != 'completed':
            day=date.fromisoformat(r['final_review_date'])
            when=datetime.combine(day,datetime.min.time(),zone).replace(hour=data['execution_hour'])
            events.append(dict(round=r['number'],kind='Anàlisi final',provisional=False,note=r.get('review_note',''),start=when.isoformat(),mac_ready=(when-timedelta(minutes=data['mac_ready_minutes'])).isoformat(),source=r.get('postponement_source',r['source']),first_match=r['first_match'],last_match=r['last_match'],status='pending'))
        if r.get('coupon_deadline_status') == 'pending' and r['forecast_status'] == 'completed':
            day=date.fromisoformat(r['first_match'])-timedelta(days=2)
            when=datetime.combine(day,datetime.min.time(),zone).replace(hour=data['execution_hour'])
            events.append(dict(round=r['number'],kind='Verificació del cupó i termini',provisional=True,note='La previsió anticipada ja està publicada. Pendent de llegir l’avís específic de tancament SELAE, sense recalcular les probabilitats.',start=when.isoformat(),mac_ready=(when-timedelta(minutes=data['mac_ready_minutes'])).isoformat(),source='https://www.loteriasyapuestas.es/es/avisos-de-interes',first_match=r['first_match'],last_match=r['last_match'],status='pending'))
    return sorted(events,key=lambda x:x['start'])

def build_schedule(root):
    data=json.loads((root/'outputs/programacio.json').read_text())
    data['events']=events_for(data)
    data['undated_events']=[dict(round=r['number'],kind='Anàlisi final',pending_matches=r['pending_matches'],source=r.get('postponement_source',r['source'])) for r in data['rounds'] if r.get('pending_matches') and not r.get('final_review_date')]
    template=(root/'work/programacio.template.html').read_text()
    style=re.search(r'<style>(.*?)</style>',(root/'work/dashboard.template.html').read_text(),re.S).group(1)
    rendered=template.replace('__STYLE__',style).replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c'))
    for p in [root/'site/dist/programacio.html',root/'outputs/programacio.html']:
        p.write_text(rendered)
    # Keep both download pages usable together.
    (root/'outputs/index.html').write_text((root/'outputs/quiniela.html').read_text())
