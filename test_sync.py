import datetime as dt,json,pathlib,tempfile,unittest
import sync

def event(n=1,title='Parents evening',start='2026-10-13 15:30:00',end=None):
 return dict(title=title,start=start,end=end,url=f'/event/example/{n}',className='')
def page(events):
 return "$('#calendar').fullCalendar({events: [], eventSources: [{events: "+json.dumps(events)+",}]});</script>"
class Tests(unittest.TestCase):
 def test_parser_rejects_changed_format(self):
  self.assertEqual(sync.parse(page([event()])),[event()])
  with self.assertRaises(ValueError):sync.parse('<html>Maintenance</html>')
 def test_category_routing(self):
  es=[event(1),event(2,'Beech class PE'),event(3,'Ash Class PE'),event(4,'Beech trip'),event(5,'Hazel trip'),event(6,'Christmas performance')]
  categories={n:es[1:3] for n in ['Beech - Year 5','Hazel - Year 6','Other']}
  categories['Beech - Year 5']+=es[3:4]+es[5:6]
  categories['Hazel - Year 6']+=es[4:6]
  groups=sync.route(es,categories)
  self.assertEqual([e['url'] for e in groups['whole-school']],[es[0]['url'],es[5]['url']])
  self.assertEqual([e['url'] for e in groups['year-5']],[es[1]['url'],es[3]['url']])
  self.assertEqual(groups['year-6'],[es[4]])
 def test_uk_timezone(self):
  self.assertEqual(sync.utc('2026-10-13 15:30:00'),'20261013T143000Z')
  self.assertEqual(sync.utc('2026-11-13 15:30:00'),'20261113T153000Z')
 def test_update_and_cancellation(self):
  e=event(); a,s=sync.calendar([e],'Test',{},'20260101T000000Z')
  b,t=sync.calendar([e],'Test',s,'20260201T000000Z');self.assertEqual(a,b)
  e['start']='2026-10-14 15:30:00'
  c,u=sync.calendar([e],'Test',s,'20260201T000000Z')
  self.assertIn('SEQUENCE:1',c);self.assertIn('UID:schoolspider-262-1@smallwood-calendar',c)
  d,v=sync.calendar([],'Test',u,'20260301T000000Z');self.assertNotIn('BEGIN:VEVENT',d)
 def test_dates_invalid_duration_and_utf8(self):
  e=event(title='é'*100+' ,;\\\n',start='2026-10-26 00:00:00',end='2026-10-30 00:00:00')
  text,_=sync.calendar([e],'Test',{},'20260101T000000Z')
  self.assertIn('DTEND;VALUE=DATE:20261031',text)
  self.assertTrue(all(len(line.encode())<=75 for line in text.split('\r\n')))
  e=event(end='2026-10-13 15:30:00');text,_=sync.calendar([e],'Test',{},'20260101T000000Z');self.assertNotIn('DTEND',text)
 def test_failure_preserves_published_feeds(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=pathlib.Path(tmp);(out/'whole-school.ics').write_text('last good')
   with self.assertRaises(ValueError):sync.run(out,loader=lambda path:'maintenance')
   self.assertEqual((out/'whole-school.ics').read_text(),'last good')
if __name__=='__main__':unittest.main()
