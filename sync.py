"""School Spider -> three subscription feeds. Standard library only."""
import concurrent.futures, datetime as dt, hashlib, html, json, pathlib, re, urllib.request
from zoneinfo import ZoneInfo
BASE='https://www.smallwood.cheshire.sch.uk'
NAMES={'whole-school':'Smallwood – Whole School','year-5':'Smallwood – Beech Year 5','year-6':'Smallwood – Hazel Year 6'}
CLASS=re.compile(r'\b(willow|ash|elm|oak|maple|beech|hazel)\b|\byear\s*([1-6])\b',re.I)
YEARS={'willow':0,'ash':1,'elm':2,'oak':3,'maple':4,'beech':5,'hazel':6}
def fetch(path):
 req=urllib.request.Request(BASE+path,headers={'User-Agent':'SmallwoodCalendarBridge/1.0'})
 with urllib.request.urlopen(req,timeout=45) as r: return r.read().decode('utf-8')
def parse(text):
 block=re.search(r"\$\('#calendar'\)\.fullCalendar\(\{(.*?)</script>",text,re.S)
 if not block: raise ValueError('School Spider calendar block missing')
 arrays=re.findall(r'events:\s*(\[.*?\])\s*[,\n]',block[1],re.S)
 if len(arrays)!=2: raise ValueError('Calendar format changed')
 events=json.loads(arrays[1]); seen={}
 for e in events:
  if not isinstance(e,dict) or not re.fullmatch(r'/event/[^/]+/\d+',e.get('url','')): raise ValueError('Invalid event identity')
  dt.datetime.strptime(e['start'],'%Y-%m-%d %H:%M:%S')
  if e.get('end'): dt.datetime.strptime(e['end'],'%Y-%m-%d %H:%M:%S')
  if not isinstance(e.get('title'),str): raise ValueError('Invalid title')
  if e['url'] in seen and seen[e['url']]!=e: raise ValueError('Conflicting duplicate')
  seen[e['url']]=e
 return list(seen.values())
def route(all_events,categories):
 membership={e['url']:set() for e in all_events}
 for name,events in categories.items():
  for e in events:
   if e['url'] not in membership: raise ValueError('Category event missing from master calendar')
   membership[e['url']].add(name)
 result={k:[] for k in NAMES}; warnings=[]
 for e in all_events:
  members=membership[e['url']]
  if len(members)==len(categories):
   # School Spider places uncategorised events in every filtered view.
   years={YEARS[m[1].lower()] if m[1] else int(m[2]) for m in CLASS.finditer(e['title'])}
   targets=years & {5,6}
   key='whole-school' if not years or targets=={5,6} else 'year-5' if targets=={5} else 'year-6' if targets=={6} else None
  elif not members: key='whole-school'
  else:
   b='Beech - Year 5' in members; h='Hazel - Year 6' in members
   key='whole-school' if b and h else 'year-5' if b else 'year-6' if h else None
  if key: result[key].append(e)
 return result

def escape(s): return html.unescape(s).replace('\\','\\\\').replace('\r\n','\n').replace('\r','\n').replace('\n','\\n').replace(';','\\;').replace(',','\\,')
def fold(line):
 chunks=[]; current=''; size=0
 for ch in line:
  n=len(ch.encode('utf-8'))
  if size+n>75: chunks.append(current); current=' '; size=1
  current+=ch; size+=n
 chunks.append(current); return '\r\n'.join(chunks)
def utc(value): return dt.datetime.strptime(value,'%Y-%m-%d %H:%M:%S').replace(tzinfo=ZoneInfo('Europe/London')).astimezone(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def calendar(events,name,state,now):
 lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Smallwood Calendar Bridge//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:'+escape(name),'X-WR-TIMEZONE:Europe/London','REFRESH-INTERVAL;VALUE=DURATION:PT6H','X-PUBLISHED-TTL:PT6H']; new={}
 for e in sorted(events,key=lambda e:(e['start'],e['url'])):
  identity=e['url'].rsplit('/',1)[1]; digest=hashlib.sha256(json.dumps(e,sort_keys=True).encode()).hexdigest(); old=state.get(identity,{})
  stamp=old.get('stamp',now) if old.get('digest')==digest else now
  sequence=old.get('sequence',0)+(1 if old and old.get('digest')!=digest else 0)
  new[identity]={'digest':digest,'stamp':stamp,'sequence':sequence}
  lines+=['BEGIN:VEVENT',f'UID:schoolspider-262-{identity}@smallwood-calendar',f'DTSTAMP:{stamp}',f'LAST-MODIFIED:{stamp}',f'SEQUENCE:{sequence}','SUMMARY:'+escape(e['title'].strip()),'URL:'+BASE+e['url']]
  start=dt.datetime.strptime(e['start'],'%Y-%m-%d %H:%M:%S'); end=dt.datetime.strptime(e['end'],'%Y-%m-%d %H:%M:%S') if e.get('end') else None
  if start.time()==dt.time() and (end is None or end.time()==dt.time()):
   lines+=['DTSTART;VALUE=DATE:'+start.strftime('%Y%m%d')]
   # FullCalendar v1 uses inclusive end dates for all-day events.
   finish=(end.date() if end and end>=start else start.date())+dt.timedelta(days=1)
   lines+=['DTEND;VALUE=DATE:'+finish.strftime('%Y%m%d')]
  else:
   lines+=['DTSTART:'+utc(e['start'])]
   if end and end>start: lines+=['DTEND:'+utc(e['end'])]
  lines+=['DESCRIPTION:'+escape('Source: '+BASE+e['url']+'\nTimes are published by the school. No duration is invented when the source has no valid end time.'),'END:VEVENT']
 lines+=['END:VCALENDAR']; return '\r\n'.join(map(fold,lines))+'\r\n',new

def run(out=pathlib.Path('public'),loader=fetch,today=None):
 today=today or dt.datetime.now(ZoneInfo('Europe/London')).date(); text=loader('/events'); all_events=parse(text)
 if not all_events: raise ValueError('Master calendar unexpectedly empty')
 links=re.findall(r'href="(/events/[^\"]*)"[^>]*>([^<]+)',text)
 links=dict(links)
 if not {'Beech - Year 5','Hazel - Year 6'} <= set(links.values()) or len(links)<9: raise ValueError('Calendar categories changed')
 def read(pair): return pair[1],parse(loader(pair[0]))
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: categories=dict(pool.map(read,links.items()))
 groups=route(all_events,categories)
 cutoff=today-dt.timedelta(days=90)
 groups={k:[e for e in v if (e.get('end') or e['start'])[:10]>=cutoff.isoformat()] for k,v in groups.items()}
 out.mkdir(parents=True,exist_ok=True); state_path=out/'state.json'; state=json.loads(state_path.read_text()) if state_path.exists() else {}
 now=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'); pending={}; next_state={}
 for key,events in groups.items(): pending[key+'.ics'],part=calendar(events,NAMES[key],state,now); next_state.update(part)
 # No feeds are changed until every request and conversion succeeds.
 for name,content in pending.items(): (out/name).write_bytes(content.encode())
 state_path.write_text(json.dumps(next_state,sort_keys=True))
 status={'updated_at':now,'source_events':len(all_events),'categories':len(categories),'feeds':{k:len(v) for k,v in groups.items()}}
 (out/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Smallwood calendars</title><h1>Smallwood school calendars</h1><p>Add these links to Skylight as Calendar URL subscriptions.</p><ul><li><a href="whole-school.ics">Whole School</a></li><li><a href="year-5.ics">Beech Year 5</a></li><li><a href="year-6.ics">Hazel Year 6</a></li></ul><p>Refreshed automatically every six hours.</p><a href="status.json">Last successful refresh</a></html>')
 (out/'status.json').write_text(json.dumps(status,indent=2)); print(json.dumps(status))
if __name__=='__main__': run()
