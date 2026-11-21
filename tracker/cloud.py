"""Steam-account scoped, offline-first cloud synchronization (stdlib only)."""
import json,os,re,time,threading,urllib.request,urllib.error,platform,tempfile
from pathlib import Path
SITE='https://patryk405.github.io/custom-steam-achievements/'
API='https://wfkgkhkuuxsggxdanvfp.supabase.co/functions/v1/achievements/cloud/'
ID=re.compile(r'7656119\d{10}')

def read(path,default=None):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return {} if default is None else default

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(fd,'w') as f:json.dump(value,f);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def active_account(data,home=None):
    hint=read(data/'steam-account.json')
    if isinstance(hint.get('at'),(int,float)) and 0<=time.time()-hint['at']<30:
        value=hint.get('steamId','');return value if isinstance(value,str) and ID.fullmatch(value) else None
    # No guess among multiple users. The frontend's live Steam session is authoritative.
    home=Path.home() if home is None else home
    try:
        raw=(home/'.local/share/Steam/config/loginusers.vdf').read_text()
        ids=ID.findall(raw)
        if len(ids)==1:return ids[0]
    except OSError:pass
    return None

def merge(games,rows,catalog):
    result=json.loads(json.dumps(games))
    for row in rows:
        game,key=row.get('game'),row.get('achievement');definition=next((a for a in catalog.get(game,{}).get('achievements',[]) if a['id']==key),None)
        current=row.get('current');stamp=row.get('unlocked_at')
        if not definition or type(current) is not int or not 0<=current<=definition['target']:continue
        if stamp is not None and (type(stamp) is not int or not 946684800<=stamp<=int(time.time())+300):continue
        old=result.get(game,{}).get(key,{})
        if current<=old.get('current',0):
            if stamp and old.get('unlockedAt'):old['unlockedAt']=min(stamp,old['unlockedAt'])
            continue
        value={'current':current,'source':'cloud','adapter':'steam-cloud-v1'}
        if current==definition['target']:value['unlockedAt']=stamp or int(time.time())
        result.setdefault(game,{})[key]=value
    return result

def payload(state,catalog):
    rows=[]
    for game,entries in state.get('games',{}).items():
        defs={a['id']:a for a in catalog.get(game,{}).get('achievements',[])}
        for key,value in entries.items():
            if key not in defs or value.get('source') not in ('automatic','cloud'):continue
            n=value.get('current');date=value.get('unlockedAt')
            if type(n) is not int or not 0<=n<=defs[key]['target']:continue
            rows.append({'game':game,'achievement':key,'current':n,'unlockedAt':date})
    return rows

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def request(path,data,secret=None):
    headers={'Content-Type':'application/json','Accept':'application/json','User-Agent':'CustomSteamAchievements/0.5.0 (+https://github.com/patryk405/custom-steam-achievements)'}
    if secret:headers['Authorization']='Bearer '+secret
    req=urllib.request.Request(API+path,json.dumps(data).encode(),headers)
    with urllib.request.build_opener(NoRedirect).open(req,timeout=10) as res:
        if 'application/json' not in res.headers.get('Content-Type',''):raise ValueError('Cloud website requires access; synchronization is unavailable')
        raw=res.read(1048577)
        if len(raw)>1048576:raise ValueError('Cloud response too large')
        return json.loads(raw)

class Cloud:
    def __init__(self,data,catalog,account_reader=active_account,transport=request):
        self.data=data;self.catalog=catalog;self.account_reader=account_reader;self.transport=transport;self.account=None;self.next_sync=0
    def prepare(self,host):
        account=self.account_reader(self.data)
        if not account:
            # Do not assign progress to a guessed account after a logout/switch.
            write(self.data/'cloud-status.json',{'status':'disconnected','message':'Waiting for the active Steam account'})
            write(self.data/'state.json',{'schema':1,'games':{},'status':{}})
            return False
        if account!=self.account:
            if self.account:write(self.data/'accounts'/self.account/'state.json',host.state)
            owner=read(self.data/'legacy-owner.json').get('steamId')
            if not owner:
                write(self.data/'legacy-backup.json',host.state)
                owner=account;write(self.data/'legacy-owner.json',{'steamId':owner})
            file=self.data/'accounts'/account/'state.json'
            default=read(self.data/'legacy-backup.json',{'schema':1,'games':{},'status':{}}) if owner==account and not self.account else {'schema':1,'games':{},'status':{}}
            host.state=read(file,default);host.state['steamId']=account
            host.seen.clear();host.done.clear();self.account=account
            write(self.data/'state.json',host.state)
        return True
    def finish(self,host):
        if self.account!=host.state.get('steamId'):return
        cache=read(self.data/'accounts'/self.account/'cloud-cache.json')
        if cache.get('steamId')==self.account:host.state['games']=merge(host.state.get('games',{}),cache.get('progress',[]),self.catalog)
        write(self.data/'accounts'/self.account/'state.json',host.state)
        write(self.data/'state.json',host.state)
    def poll(self):
        account=self.account_reader(self.data)
        if not account:return
        root=self.data/'accounts'/account;cfg=read(root/'cloud.json');status={'steamId':account,'status':'disconnected','message':'Cloud sync is not connected'}
        command=read(self.data/'cloud-command.json')
        if command:
            (self.data/'cloud-command.json').unlink(missing_ok=True)
        if command.get('steamId')==account:
            if command.get('action')=='disconnect':
                (root/'cloud.json').unlink(missing_ok=True);cfg={}
            elif command.get('action')=='connect':
                response=self.transport('device/start',{'steamId':account,'name':platform.node()[:80] or 'Linux device'})
                if not re.fullmatch('[a-f0-9]{64}',response.get('token','')) or not response.get('verificationUrl','').startswith(SITE+'?view=account&device='):raise ValueError('Invalid pairing response')
                cfg={**response,'steamId':account,'paired':False};write(root/'cloud.json',cfg)
        if cfg.get('steamId')!=account:
            write(self.data/'cloud-status.json',status);return
        if not cfg.get('paired'):
            response=self.transport('device/status',{'token':cfg['token']})
            if response.get('status')=='approved':
                if response.get('steamId')!=account:raise ValueError('Steam account mismatch')
                cfg['paired']=True;write(root/'cloud.json',cfg);self.next_sync=0
            elif response.get('status')=='pending':
                write(self.data/'cloud-status.json',{**status,'status':'pairing','message':'Approve this device in your browser','verificationUrl':cfg['verificationUrl']});return
            else:
                (root/'cloud.json').unlink(missing_ok=True);write(self.data/'cloud-status.json',{**status,'message':'Pairing expired. Connect again.'});return
        if time.monotonic()<self.next_sync:return
        state=read(root/'state.json')
        if state.get('steamId')!=account:return
        result=self.transport('sync',{'steamId':account,'progress':payload(state,self.catalog)},cfg['token'])
        if result.get('steamId')!=account or not isinstance(result.get('progress'),list):raise ValueError('Invalid cloud account response')
        write(root/'cloud-cache.json',result);self.next_sync=time.monotonic()+30
        write(self.data/'cloud-status.json',{**status,'status':'synced','message':'Synced with Steam cloud account','syncedAt':int(time.time())})
    def run(self):
        while True:
            try:self.poll()
            except Exception as e:
                message='Offline — progress is saved on this device'
                if isinstance(e,urllib.error.HTTPError) and e.code in (401,403):message='Cloud access denied. Reconnect Steam or check website access.'
                write(self.data/'cloud-status.json',{'steamId':self.account_reader(self.data),'status':'offline','message':message})
            time.sleep(5)
