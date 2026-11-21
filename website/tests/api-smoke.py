"""Run against a local preview only; identity headers simulate the trusted hosting edge."""
import json, urllib.request, urllib.error, uuid, time
BASE='http://127.0.0.1:4173'
def req(path, data=None, auth=False, origin=BASE, retries=3):
    h={'Origin':origin,'Content-Type':'application/json'}
    if auth:h.update({'oai-authenticated-user-id':'local-smoke-test','oai-authenticated-user-email':'smoke@example.invalid'})
    b=None if data is None else json.dumps(data).encode()
    r=urllib.request.Request(BASE+path,data=b,headers=h)
    try:
        with urllib.request.urlopen(r) as response:return response.status,response.read(),dict(response.headers)
    except urllib.error.HTTPError as e:
        body=e.read()
        if e.code==503 and b'worker restarted mid-request' in body and retries:
            time.sleep(.5);return req(path,data,auth,origin,retries-1)
        return e.code,body,dict(e.headers)
assert req('/')[0]==200
assert req('/api/packs')[0]==200
status,body,_=req('/api/template');assert status==200
p=json.loads(body);p['id']='smoke-'+uuid.uuid4().hex;p['title']='Local smoke test'
assert req('/api/packs',p)[0]==401
assert req('/api/packs',p,True,'https://untrusted.invalid')[0]==403
bad=json.loads(json.dumps(p));bad['rules'][bad['achievements'][0]['id']]['flags']=['unknown_signal'];assert req('/api/packs',bad,True)[0]==400
bad=json.loads(json.dumps(p));bad['script']='alert(1)';assert req('/api/packs',bad,True)[0]==400
bad=json.loads(json.dumps(p));bad['achievements']*=2;assert req('/api/packs',bad,True)[0]==400
big={'padding':'x'*140000};assert req('/api/packs',big,True)[0]==413
status,body,_=req('/api/packs',p,True);assert status==201,(status,body)
id=json.loads(body)['id']
status,body,h=req('/api/packs/'+id+'?download=1');assert status==200 and json.loads(body)==p and 'attachment' in h['Content-Disposition']
assert any(c['id']==id for c in json.loads(req('/api/packs')[1]))
assert len(json.loads(req('/api/packs/botw-community?download=1')[1])['achievements'])==38
print('PASS: page, list, template, auth, origin, unsupported signals, script rejection, duplicate IDs, size limit, upload, persisted download, builtin pack.')
