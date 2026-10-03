import csv,hmac,io,os,uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI,Form,File,UploadFile,Request,HTTPException
from fastapi.responses import HTMLResponse,RedirectResponse,FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from PIL import Image
from .database import init_db,con,LEVEL,CRACKS
from .model import POINTS,campaigns,grouped,points,point
BASE=Path(__file__).parent
@asynccontextmanager
async def life(app):init_db();yield
app=FastAPI(title='Hausmonitor V5.2',version='5.2.0',lifespan=life);app.add_middleware(SessionMiddleware,secret_key=os.getenv('SECRET_KEY','x'),same_site='lax');app.mount('/static',StaticFiles(directory=BASE/'static'),name='static');templates=Jinja2Templates(directory=BASE/'templates')
def guard(r):
 if os.getenv('APP_PASSWORD','') and not r.session.get('ok'):return RedirectResponse('/login',303)
def save(raw,typ,prefix,d):
 if typ not in ('image/jpeg','image/png','image/webp'):raise HTTPException(400,'Bildformat')
 Image.open(io.BytesIO(raw)).verify();ext={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[typ];n=f'{prefix}-{uuid.uuid4().hex}{ext}';(d/n).write_bytes(raw);return n
@app.get('/health')
def health():return {'status':'ok','version':'5.2.0'}
@app.get('/login',response_class=HTMLResponse)
def loginpage(request:Request):return templates.TemplateResponse(request=request,name='login.html',context={'error':None})
@app.post('/login')
def login(request:Request,password:str=Form(...)):
 if hmac.compare_digest(password,os.getenv('APP_PASSWORD','')):request.session['ok']=True;return RedirectResponse('/',303)
 return templates.TemplateResponse(request=request,name='login.html',context={'error':'Falsch'},status_code=401)
@app.post('/logout')
def logout(request:Request):request.session.clear();return RedirectResponse('/login',303)
@app.get('/',response_class=HTMLResponse)
def home(request:Request):
 if (x:=guard(request)):return x
 cs=campaigns()
 chart=[{'date':c['measured_at'],'delta':c['stats']['house']['delta'],'se':c['stats']['house']['se'],'low':c['stats']['house']['delta']-c['stats']['house']['se'] if c['stats']['house']['delta'] is not None and c['stats']['house']['se'] is not None else None,'high':c['stats']['house']['delta']+c['stats']['house']['se'] if c['stats']['house']['delta'] is not None and c['stats']['house']['se'] is not None else None,'sd_sw':c['stats']['SW']['sd'],'sd_so':c['stats']['SO']['sd'],'snr':c['stats']['house']['snr']} for c in cs]
 return templates.TemplateResponse(request=request,name='home.html',context={'campaigns':cs,'points':points(),'noise_chart':chart})
@app.get('/level',response_class=HTMLResponse)
def level(request:Request):
 if (x:=guard(request)):return x
 return templates.TemplateResponse(request=request,name='level.html',context={'campaigns':list(reversed(campaigns()))})
@app.get('/level/new',response_class=HTMLResponse)
def levelnew(request:Request):
 if (x:=guard(request)):return x
 with con() as c:dev=[dict(r) for r in c.execute('SELECT * FROM devices ORDER BY name')]
 return templates.TemplateResponse(request=request,name='level_form.html',context={'c':None,'now':datetime.now().strftime('%Y-%m-%dT%H:%M'),'devices':dev})
@app.post('/level')
def levelcreate(request:Request,measured_at:str=Form(...),air_temp:float|None=Form(None),wall_temp_sw:float|None=Form(None),wall_temp_so:float|None=Form(None),groundwater:float|None=Form(None),rainfall_14d:float|None=Form(None),weather:str=Form(''),light_mode:str=Form(''),notes:str=Form(''),device_id:int|None=Form(None)):
 if (x:=guard(request)):return x
 with con() as db:cid=db.execute('INSERT INTO campaigns(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes,device_id) VALUES(?,?,?,?,?,?,?,?,?,?)',(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes,device_id)).lastrowid
 return RedirectResponse(f'/level/{cid}/readings',303)
@app.get('/level/{cid}/edit',response_class=HTMLResponse)
def leveledit(request:Request,cid:int):
 if (x:=guard(request)):return x
 with con() as db:c=db.execute('SELECT * FROM campaigns WHERE id=?',(cid,)).fetchone();dev=[dict(r) for r in db.execute('SELECT * FROM devices ORDER BY name')]
 if not c:raise HTTPException(404)
 return templates.TemplateResponse(request=request,name='level_form.html',context={'c':dict(c),'devices':dev,'now':''})
@app.post('/level/{cid}/edit')
def levelupdate(request:Request,cid:int,measured_at:str=Form(...),air_temp:float|None=Form(None),wall_temp_sw:float|None=Form(None),wall_temp_so:float|None=Form(None),groundwater:float|None=Form(None),rainfall_14d:float|None=Form(None),weather:str=Form(''),light_mode:str=Form(''),notes:str=Form(''),device_id:int|None=Form(None)):
 if (x:=guard(request)):return x
 with con() as db:db.execute('UPDATE campaigns SET measured_at=?,air_temp=?,wall_temp_sw=?,wall_temp_so=?,groundwater=?,rainfall_14d=?,weather=?,light_mode=?,notes=?,device_id=? WHERE id=?',(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes,device_id,cid))
 return RedirectResponse(f'/level/{cid}',303)
@app.get('/level/{cid}/readings',response_class=HTMLResponse)
def readingspage(request:Request,cid:int):
 if (x:=guard(request)):return x
 return templates.TemplateResponse(request=request,name='readings.html',context={'cid':cid,'existing':grouped(cid),'points':POINTS})
@app.post('/level/{cid}/readings')
async def readingssave(request:Request,cid:int):
 if (x:=guard(request)):return x
 f=await request.form()
 with con() as db:
  db.execute('DELETE FROM readings WHERE campaign_id=?',(cid,))
  for p in POINTS:
   seq=0
   for raw in f.getlist(p):
    raw=str(raw).strip().replace(',','.')
    if raw:seq+=1;db.execute('INSERT INTO readings(campaign_id,point,sequence,value) VALUES(?,?,?,?)',(cid,p,seq,float(raw)))
 return RedirectResponse(f'/level/{cid}',303)
@app.get('/level/{cid}',response_class=HTMLResponse)
def leveldetail(request:Request,cid:int):
 if (x:=guard(request)):return x
 c=next((x for x in campaigns() if x['id']==cid),None)
 if not c:raise HTTPException(404)
 with con() as db:photos=[dict(r) for r in db.execute('SELECT * FROM level_photos WHERE campaign_id=? ORDER BY id',(cid,))]
 return templates.TemplateResponse(request=request,name='level_detail.html',context={'c':c,'raw':grouped(cid),'photos':photos})
@app.post('/level/{cid}/photo')
async def levelphoto(request:Request,cid:int,point:str=Form(''),caption:str=Form(''),photo:UploadFile=File(...)):
 if (x:=guard(request)):return x
 n=save(await photo.read(),photo.content_type,f'level-{cid}',LEVEL)
 with con() as db:db.execute('INSERT INTO level_photos(campaign_id,point,filename,caption) VALUES(?,?,?,?)',(cid,point,n,caption))
 return RedirectResponse(f'/level/{cid}',303)
@app.get('/uploads/level/{name}')
def getlevel(request:Request,name:str):
 if (x:=guard(request)):return x
 return FileResponse(LEVEL/Path(name).name)
@app.get('/cracks',response_class=HTMLResponse)
def cracks(request:Request):
 if (x:=guard(request)):return x
 return templates.TemplateResponse(request=request,name='cracks.html',context={'points':points()})
@app.get('/cracks/new',response_class=HTMLResponse)
def cracknew(request:Request):
 if (x:=guard(request)):return x
 return templates.TemplateResponse(request=request,name='crack_form.html',context={'p':None})
@app.post('/cracks')
def crackcreate(request:Request,name:str=Form(...),location:str=Form(''),description:str=Form(''),crack_type:str=Form(''),unit:str=Form('mm'),reference_value:float|None=Form(None),warning_delta:float=Form(.3),alarm_delta:float=Form(.5)):
 if (x:=guard(request)):return x
 with con() as db:pid=db.execute('INSERT INTO crack_points(name,location,description,crack_type,unit,reference_value,warning_delta,alarm_delta) VALUES(?,?,?,?,?,?,?,?)',(name,location,description,crack_type,unit,reference_value,warning_delta,alarm_delta)).lastrowid
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/cracks/{pid}/edit',response_class=HTMLResponse)
def crackedit(request:Request,pid:int):
 if (x:=guard(request)):return x
 p=point(pid)
 if not p:raise HTTPException(404)
 return templates.TemplateResponse(request=request,name='crack_form.html',context={'p':p})
@app.post('/cracks/{pid}/edit')
def crackupdate(request:Request,pid:int,name:str=Form(...),location:str=Form(''),description:str=Form(''),crack_type:str=Form(''),unit:str=Form('mm'),reference_value:float|None=Form(None),warning_delta:float=Form(.3),alarm_delta:float=Form(.5)):
 if (x:=guard(request)):return x
 with con() as db:db.execute('UPDATE crack_points SET name=?,location=?,description=?,crack_type=?,unit=?,reference_value=?,warning_delta=?,alarm_delta=? WHERE id=?',(name,location,description,crack_type,unit,reference_value,warning_delta,alarm_delta,pid))
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/cracks/{pid}',response_class=HTMLResponse)
def crackdetail(request:Request,pid:int):
 if (x:=guard(request)):return x
 p=point(pid)
 if not p:raise HTTPException(404)
 return templates.TemplateResponse(request=request,name='crack_detail.html',context={'p':p})
@app.get('/cracks/{pid}/new',response_class=HTMLResponse)
def measnew(request:Request,pid:int):
 if (x:=guard(request)):return x
 return templates.TemplateResponse(request=request,name='crack_measure.html',context={'p':point(pid),'m':None,'now':datetime.now().strftime('%Y-%m-%dT%H:%M')})
@app.post('/cracks/{pid}/measurements')
async def meascreate(request:Request,pid:int,measured_at:str=Form(...),air_temp:float|None=Form(None),value:float=Form(...),notes:str=Form(''),photo:UploadFile|None=File(None)):
 if (x:=guard(request)):return x
 n=save(await photo.read(),photo.content_type,f'crack-{pid}',CRACKS) if photo and photo.filename else None
 with con() as db:db.execute('INSERT INTO crack_measurements(crack_point_id,measured_at,air_temp,value,notes,photo_filename) VALUES(?,?,?,?,?,?)',(pid,measured_at,air_temp,value,notes,n))
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/cracks/{pid}/measurements/{mid}/edit',response_class=HTMLResponse)
def measedit(request:Request,pid:int,mid:int):
 if (x:=guard(request)):return x
 with con() as db:m=db.execute('SELECT * FROM crack_measurements WHERE id=? AND crack_point_id=?',(mid,pid)).fetchone()
 if not m:raise HTTPException(404)
 return templates.TemplateResponse(request=request,name='crack_measure.html',context={'p':point(pid),'m':dict(m),'now':''})
@app.post('/cracks/{pid}/measurements/{mid}/edit')
async def measupdate(request:Request,pid:int,mid:int,measured_at:str=Form(...),air_temp:float|None=Form(None),value:float=Form(...),notes:str=Form(''),photo:UploadFile|None=File(None)):
 if (x:=guard(request)):return x
 with con() as db:old=db.execute('SELECT photo_filename FROM crack_measurements WHERE id=?',(mid,)).fetchone();n=old['photo_filename'] if old else None
 if photo and photo.filename:
  if n:(CRACKS/n).unlink(missing_ok=True)
  n=save(await photo.read(),photo.content_type,f'crack-{pid}',CRACKS)
 with con() as db:db.execute('UPDATE crack_measurements SET measured_at=?,air_temp=?,value=?,notes=?,photo_filename=? WHERE id=? AND crack_point_id=?',(measured_at,air_temp,value,notes,n,mid,pid))
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/uploads/cracks/{name}')
def getcrack(request:Request,name:str):
 if (x:=guard(request)):return x
 return FileResponse(CRACKS/Path(name).name)
@app.get('/exports/nivellement.csv')
def csvlevel(request:Request):
 if (x:=guard(request)):return x
 out=io.StringIO();w=csv.writer(out,delimiter=';');w.writerow(['Datum',*sum(([f'{p}{i}' for i in range(1,6)] for p in POINTS),[])])
 for c in campaigns():
  g=grouped(c['id']);w.writerow([c['measured_at'],*sum(((g[p]+['']*5)[:5] for p in POINTS),[])])
 return StreamingResponse(iter([out.getvalue()]),media_type='text/csv')
@app.get('/exports/risse.csv')
def csvcracks(request:Request):
 if (x:=guard(request)):return x
 out=io.StringIO();w=csv.writer(out,delimiter=';');w.writerow(['Messstelle','Datum','Temperatur','Messwert','Notiz'])
 for p in points():
  for m in p['measurements']:w.writerow([p['name'],m['measured_at'],m['air_temp'],m['value'],m['notes']])
 return StreamingResponse(iter([out.getvalue()]),media_type='text/csv')
