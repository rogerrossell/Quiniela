import json, re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

def events_for(data):
    events=[]
    zone=ZoneInfo(data['timezone'])
    for r in data['rounds']:
        for kind,day,status in [('Previsió',date.fromisoformat(r['first_match'])-timedelta(days=2),r['forecast_status']),('Anàlisi',date.fromisoformat(r['last_match'])+timedelta(days=1),r['review_status'])]:
            if status in ['completed','late_partial_completed']:
                continue
            when=datetime.combine(day,datetime.min.time(),zone).replace(hour=data['execution_hour'])
            events.append(dict(round=r['number'],kind=kind,start=when.isoformat(),mac_ready=(when-timedelta(minutes=data['mac_ready_minutes'])).isoformat(),source=r['source'],first_match=r['first_match'],last_match=r['last_match'],status=status))
    return sorted(events,key=lambda x:x['start'])

def build_schedule(root):
    data=json.loads((root/'outputs/programacio.json').read_text())
    data['events']=events_for(data)
    template=(root/'work/programacio.template.html').read_text()
    style=re.search(r'<style>(.*?)</style>',(root/'work/dashboard.template.html').read_text(),re.S).group(1)
    rendered=template.replace('__STYLE__',style).replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c'))
    for p in [root/'site/dist/programacio.html',root/'outputs/programacio.html']:
        p.write_text(rendered)
    # Keep both download pages usable together.
    (root/'outputs/index.html').write_text((root/'outputs/quiniela.html').read_text())
