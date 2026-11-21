"""API regression test. Requires temporary, isolated fixture accounts prepared by the operator.
Never point fixture setup at real user IDs. Credentials come from CSA_TEST_FIXTURE only.
"""
import json,os,urllib.request,urllib.error
from pathlib import Path
cfg=json.loads(Path(os.environ['CSA_TEST_FIXTURE']).read_text())
BASE=os.environ['CSA_TEST_API'];ORIGIN='https://patryk405.github.io';A='76561198000000001';B='76561198000000002'
def call(path,data=None,token=None,origin=ORIGIN,status=200):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 if origin:h['Origin']=origin
 req=urllib.request.Request(BASE+path,None if data is None else json.dumps(data).encode(),h)
 try:
  r=urllib.request.urlopen(req);code=r.status;body=r.read()
 except urllib.error.HTTPError as e:code=e.code;body=e.read()
 assert code==status,(path,code,body[:200])
 return json.loads(body)
assert call('cloud/me')['signedIn'] is False
call('cloud/sync',{'steamId':A,'progress':[]},status=401)
call('cloud/login/start',{'state':'a'*64,'challenge':'b'*64},origin='https://evil.example',status=403)
# Incorrect verifier must not consume the one-time flow.
call('cloud/exchange',{'state':cfg['state'],'verifier':'0'*64},status=503)
x=call('cloud/exchange',{'state':cfg['state'],'verifier':cfg['verifier']});assert x['steamId']==A
call('cloud/exchange',{'state':cfg['state'],'verifier':cfg['verifier']},status=503)
p=call('cloud/device/start',{'steamId':A,'name':'Fixture device'})
assert p['verificationUrl'].startswith(ORIGIN+'/custom-steam-achievements/?view=account&device=')
call('cloud/device/approve',{'device':p['device']},cfg['other'],status=403)
assert call('cloud/device/info?id='+p['device'],token=cfg['other'])['device'] is None
call('cloud/device/approve',{'device':p['device']},cfg['browser'])
assert call('cloud/device/status',{'token':p['token']})['steamId']==A
call('cloud/sync',{'steamId':B,'progress':[]},p['token'],status=403)
row={'game':'pokopia','achievement':'pokopia_first_friend','current':1,'unlockedAt':1700000000}
s=call('cloud/sync',{'steamId':A,'progress':[row]},p['token']);assert len(s['progress'])==1
row['current']=0;row['unlockedAt']=None
s=call('cloud/sync',{'steamId':A,'progress':[row]},p['token']);assert s['progress'][0]['current']==1
assert call('cloud/me',token=cfg['other'])['progress']==[]
call('cloud/sync',{'steamId':A,'progress':[row,row]},p['token'],status=400)
call('packs',{'invalid':'pack'},cfg['browser'],status=400)
me=call('cloud/me',token=cfg['browser']);device=next(d for d in me['devices'] if d['name']=='Fixture device')
call('cloud/device/revoke',{'id':device['id']},cfg['other'])
call('cloud/sync',{'steamId':A,'progress':[]},p['token'])
call('cloud/device/revoke',{'id':device['id']},cfg['browser'])
call('cloud/sync',{'steamId':A,'progress':[]},p['token'],status=401)
call('cloud/logout',{},cfg['browser']);assert call('cloud/me',token=cfg['browser'])['signedIn'] is False
print('PASS: PKCE exchange, replay, CORS, pairing, cross-account isolation, monotonic merge, validation, revocation, logout')
