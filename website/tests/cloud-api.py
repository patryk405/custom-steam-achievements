"""Local-only D1/API integration tests; never seed or call production."""
import pathlib,sqlite3,json,hashlib,time,urllib.request,urllib.error
BASE='http://127.0.0.1:4174';A='76561198000000000';B='76561198000000001'
ROOT=pathlib.Path(__file__).resolve().parents[1]
db=next(p for p in (ROOT/'.wrangler/state/v3/d1/miniflare-D1DatabaseObject').glob('*.sqlite') if p.name!='metadata.sqlite')
con=sqlite3.connect(db);now=int(time.time())
hash=lambda s:hashlib.sha256(s.encode()).hexdigest()
for raw,account,kind in [('a'*64,A,'browser'),('c'*64,B,'browser'),('d'*64,B,'device')]:con.execute('INSERT OR REPLACE INTO steam_sessions VALUES(?,?,?,?,?,?)',(hash(raw),account,kind,'Local test',now,now+3600))
con.commit()
def call(path,data=None,cookie=None,bearer=None,origin=BASE):
 time.sleep(0.1) # Allow local Workerd request contexts to finish between browser steps.
 headers={'Origin':origin}
 if cookie:headers['Cookie']='__Host-csa_session='+cookie
 if bearer:headers['Authorization']='Bearer '+bearer
 if data is not None:headers['Content-Type']='application/json'
 req=urllib.request.Request(BASE+'/api/cloud/'+path,None if data is None else json.dumps(data).encode(),headers)
 try:
  with urllib.request.urlopen(req,timeout=30) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:
  raw=e.read()
  try:return e.code,json.loads(raw)
  except ValueError:raise AssertionError((path,e.code,raw[:300]))
try:
 assert call('me')[1]['signedIn'] is False
 assert call('sync',{'steamId':A,'progress':[]})[0]==401
 assert call('callback?state=forged')[0]==400
 code,pair=call('device/start',{'steamId':A,'name':'Local test PC'});assert code==200,(code,pair)
 secret=pair['token'];device=pair['device']
 assert call('device/status',{'token':secret})[1]['status']=='pending'
 assert call('device/approve',{'device':device},cookie='c'*64)[0]==403
 assert call('device/approve',{'device':device},cookie='a'*64)[0]==200
 assert call('device/approve',{'device':device},cookie='a'*64)[0]==403
 assert call('device/status',{'token':secret})[1]['steamId']==A
 row={'game':'pokopia','achievement':'pokopia_first_friend','current':1,'unlockedAt':now-100}
 code,result=call('sync',{'steamId':A,'progress':[row]},bearer=secret);assert code==200,(code,result)
 assert result['progress'][0]['current']==1
 result=call('sync',{'steamId':A,'progress':[{**row,'current':0,'unlockedAt':None}]},bearer=secret)[1];assert result['progress'][0]['current']==1
 assert result['progress'][0]['unlocked_at']==now-100
 assert call('sync',{'steamId':A,'progress':[]},bearer='d'*64)[0]==403
 assert call('sync',{'steamId':B,'progress':[]},bearer='d'*64)[1]['progress']==[]
 assert call('sync',{'steamId':A,'progress':[{**row,'current':999}]},bearer=secret)[0]==400
 assert call('me',cookie='a'*64)[1]['progress'][0]['achievement']=='pokopia_first_friend'
 assert call('me',cookie='c'*64)[1]['progress']==[]
 assert call('device/revoke',{'id':hash(secret)},cookie='c'*64)[0]==200
 assert call('sync',{'steamId':A,'progress':[]},bearer=secret)[0]==200
 assert call('device/revoke',{'id':hash(secret)},cookie='a'*64)[0]==200
 assert call('sync',{'steamId':A,'progress':[]},bearer=secret)[0]==401
 assert call('device/approve',{'device':device},cookie='a'*64,origin='https://evil.test')[0]==400
 print('PASS: pairing, CSRF, account isolation, sync merge, idempotency, validation and revocation')
finally:
 for table in ['steam_sessions','cloud_progress']:con.execute('DELETE FROM '+table+' WHERE steam_id IN (?,?)',(A,B))
 con.execute('DELETE FROM steam_devices WHERE expected_steam_id IN (?,?)',(A,B));con.commit();con.close()
