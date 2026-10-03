import io,os
from PIL import Image
os.environ['DATABASE_PATH']='/tmp/hm51.db';os.environ['UPLOAD_DIR']='/tmp/hm51up';os.environ['APP_PASSWORD']=''
from fastapi.testclient import TestClient
from app.main import app
from app.database import DB
def setup_module():
 try:DB.unlink()
 except:pass
def png():
 b=io.BytesIO();Image.new('RGB',(10,10),'white').save(b,'PNG');return b.getvalue()
def test_edit_raw_and_photos():
 with TestClient(app) as c:
  assert c.get('/health').json()['version']=='5.2.0'
  r=c.post('/level',data={'measured_at':'2026-10-03T10:00'},follow_redirects=False);cid=r.headers['location'].split('/')[2]
  c.post(f'/level/{cid}/readings',data={'SW':['1','2','3','4','5'],'SO':['6','7','8','9','10']})
  assert '1.0 · 2.0 · 3.0' in c.get(f'/level/{cid}').text
  c.post(f'/level/{cid}/photo',data={'point':'SW','caption':'Foto'},files={'photo':('x.png',png(),'image/png')})
  assert 'Foto' in c.get(f'/level/{cid}').text
  c.post(f'/level/{cid}/edit',data={'measured_at':'2026-10-04T10:00','notes':'bearbeitet'})
  assert '2026-10-04' in c.get(f'/level/{cid}').text
  r=c.post('/cracks',data={'name':'R1'},follow_redirects=False);pid=r.headers['location'].split('/')[2]
  c.post(f'/cracks/{pid}/measurements',data={'measured_at':'2026-10-03T11:00','value':'.4'},files={'photo':('r.png',png(),'image/png')})
  page=c.get(f'/cracks/{pid}');assert '0.4' in page.text and 'Bearbeiten' in page.text
  with __import__('app.database',fromlist=['con']).con() as db:mid=db.execute('SELECT id FROM crack_measurements').fetchone()[0]
  c.post(f'/cracks/{pid}/measurements/{mid}/edit',data={'measured_at':'2026-10-03T11:00','value':'.6','notes':'korrigiert'})
  assert '0.6' in c.get(f'/cracks/{pid}').text
  home=c.get('/');assert 'levelNoiseChart' in home.text and 'levelSdChart' in home.text and 'sd_sw' in home.text
  assert c.get('/exports/nivellement.csv').status_code==200 and c.get('/exports/risse.csv').status_code==200
