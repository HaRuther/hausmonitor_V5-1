from math import sqrt
from statistics import mean,stdev
from .database import con
POINTS=('SW','SO','ANB','TSW','TSO')
def summ(v):
 if not v:return {'n':0,'mean':None,'sd':None,'se':None,'range':None}
 sd=stdev(v) if len(v)>1 else None;return {'n':len(v),'mean':mean(v),'sd':sd,'se':sd/sqrt(len(v)) if sd is not None else None,'range':max(v)-min(v)}
def grouped(cid):
 g={p:[] for p in POINTS}
 with con() as c:
  for r in c.execute('SELECT point,value FROM readings WHERE campaign_id=? ORDER BY sequence',(cid,)):g.setdefault(r['point'],[]).append(r['value'])
 return g
def pair(a,b,base):
 if a['mean'] is None or b['mean'] is None:return {'value':None,'se':None,'delta':None,'snr':None,'quality':'unvollständig'}
 v=b['mean']-a['mean'];se=sqrt(a['se']**2+b['se']**2) if a['se'] is not None and b['se'] is not None else None;d=v-base if base is not None else None;snr=abs(d)/se if d is not None and se else None
 return {'value':v,'se':se,'delta':d,'snr':snr,'quality':'Signal klar' if snr is not None and snr>=3 else 'Hinweis' if snr is not None and snr>=2 else 'im Rauschen' if snr is not None else 'nicht bewertbar'}
def campaigns():
 with con() as c:rows=[dict(r) for r in c.execute('SELECT campaigns.*,devices.name device_name FROM campaigns LEFT JOIN devices ON devices.id=campaigns.device_id ORDER BY measured_at,id')];settings=dict(c.execute('SELECT * FROM settings WHERE id=1').fetchone())
 base_id=settings.get('reference_campaign_id'); temp=[]
 for r in rows:
  o={p:summ(grouped(r['id'])[p]) for p in POINTS};temp.append((r,o))
 if base_id:base=next((o['SO']['mean']-o['SW']['mean'] for r,o in temp if r['id']==base_id and o['SW']['mean'] is not None and o['SO']['mean'] is not None),None)
 else:base=next((o['SO']['mean']-o['SW']['mean'] for _,o in temp if o['SW']['mean'] is not None and o['SO']['mean'] is not None),None)
 tbase=next((o['TSO']['mean']-o['TSW']['mean'] for _,o in temp if o['TSW']['mean'] is not None and o['TSO']['mean'] is not None),None)
 out=[]
 for r,o in temp:o['house']=pair(o['SW'],o['SO'],base);o['terrace']=pair(o['TSW'],o['TSO'],tbase);r['stats']=o;out.append(r)
 return out
def point(pid):
 with con() as c:
  p=c.execute('SELECT * FROM crack_points WHERE id=?',(pid,)).fetchone()
  if not p:return None
  p=dict(p);p['measurements']=[dict(r) for r in c.execute('SELECT * FROM crack_measurements WHERE crack_point_id=? ORDER BY measured_at,id',(pid,))]
 base=p['measurements'][0]['value'] if p['measurements'] else p['reference_value']
 for m in p['measurements']:m['delta']=m['value']-base if base is not None else None
 p['baseline']=base;p['latest']=p['measurements'][-1] if p['measurements'] else None;p['delta']=p['latest']['value']-base if p['latest'] and base is not None else None
 p['status']='Alarm' if p['delta'] is not None and abs(p['delta'])>=p['alarm_delta'] else 'Warnung' if p['delta'] is not None and abs(p['delta'])>=p['warning_delta'] else 'Stabil'
 return p
def points():
 with con() as c:ids=[r[0] for r in c.execute('SELECT id FROM crack_points WHERE active=1 ORDER BY name')]
 return [point(i) for i in ids]
