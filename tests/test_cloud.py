import json,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tracker'))
from cloud import Cloud,merge,payload,write,read,active_account
from engine import apply_rules
A='76561198000000001';B='76561198000000000'
CAT={'game':{'achievements':[{'id':'first','target':1},{'id':'count','target':10}]}}
class CloudTests(unittest.TestCase):
 def test_merge_monotonic_and_no_notification_replay(self):
  a={'game':{'count':{'current':7,'source':'automatic'}}}
  rows=[{'game':'game','achievement':'count','current':3},{'game':'game','achievement':'first','current':1,'unlocked_at':1700000000}]
  merged=merge(a,rows,CAT);self.assertEqual(merged['game']['count']['current'],7);self.assertEqual(merged['game']['first']['source'],'cloud');self.assertNotIn('first',a['game'])
  new=apply_rules(merged['game'],{'id':'x','rules':{'first':{'op':'number','flags':['x'],'threshold':1}}},{'x':1},{'first':{'target':1}})
  self.assertEqual(new['first']['source'],'cloud')
 def test_invalid_and_test_progress_not_uploaded(self):
  self.assertEqual(merge({},[{'game':'game','achievement':'first','current':True},{'game':'other','achievement':'first','current':1},{'game':'game','achievement':'first','current':99}],CAT),{})
  self.assertEqual(payload({'games':{'game':{'first':{'current':1,'source':'manual-test'}}}},CAT),[])
 def test_switch_preserves_local_progress_without_cross_account_leak(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);current=[A];cloud=Cloud(d,CAT,account_reader=lambda _:current[0]);host=SimpleNamespace(state={'schema':1,'games':{'game':{'first':{'current':1,'source':'automatic'}}},'status':{}},seen={},done={})
   cloud.prepare(host);cloud.finish(host);self.assertEqual(host.state['steamId'],A)
   current[0]=B;cloud.prepare(host);self.assertEqual(host.state['games'],{});cloud.finish(host)
   current[0]=None;self.assertFalse(cloud.prepare(host));self.assertEqual(read(d/'state.json')['games'],{})
   current[0]=A;cloud.prepare(host);self.assertEqual(host.state['games']['game']['first']['current'],1)
   self.assertEqual(read(d/'accounts'/B/'state.json')['games'],{})
 def test_two_devices_sync_and_offline_recovery(self):
  server=[]
  def transport(path,data,secret=None):
   self.assertEqual(path,'sync');self.assertEqual(data['steamId'],A)
   by={x['achievement']:x for x in server}
   for x in data['progress']:
    if x['current']>by.get(x['achievement'],{}).get('current',0):by[x['achievement']]={**x,'unlocked_at':x.get('unlockedAt')}
   server[:]=by.values();return {'steamId':A,'progress':server}
  with tempfile.TemporaryDirectory() as da,tempfile.TemporaryDirectory() as db:
   for root,n in [(Path(da),1),(Path(db),0)]:
    write(root/'accounts'/A/'cloud.json',{'steamId':A,'paired':True,'token':'x'})
    write(root/'accounts'/A/'state.json',{'steamId':A,'games':{'game':{'first':{'current':n,'source':'automatic'}}}})
   ca=Cloud(Path(da),CAT,lambda _:A,transport);cb=Cloud(Path(db),CAT,lambda _:A,transport);ca.poll();cb.poll()
   self.assertEqual(read(Path(db)/'accounts'/A/'cloud-cache.json')['progress'][0]['current'],1)
   local=read(Path(db)/'accounts'/A/'state.json');local['games']['game']['count']={'current':8,'source':'automatic'};write(Path(db)/'accounts'/A/'state.json',local)
   def offline(*args):raise OSError('offline')
   cb.transport=offline;cb.next_sync=0
   with self.assertRaises(OSError):cb.poll()
   self.assertEqual(read(Path(db)/'accounts'/A/'state.json')['games']['game']['count']['current'],8)
   cb.transport=transport;cb.poll();ca.next_sync=0;ca.poll();self.assertEqual(len(server),2)
 def test_token_account_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);write(d/'accounts'/A/'cloud.json',{'steamId':A,'paired':True,'token':'x'});write(d/'accounts'/A/'state.json',{'steamId':A,'games':{}})
   c=Cloud(d,CAT,lambda _:A,lambda *args:{'steamId':B,'progress':[]})
   with self.assertRaises(ValueError):c.poll()
   self.assertFalse((d/'accounts'/A/'cloud-cache.json').exists())
 def test_logout_hint_and_ambiguous_accounts(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);p=d/'.local/share/Steam/config/loginusers.vdf';p.parent.mkdir(parents=True);p.write_text('"'+A+'"{} "'+B+'"{}')
   self.assertIsNone(active_account(d,d));write(d/'steam-account.json',{'steamId':A,'at':time.time()});self.assertEqual(active_account(d,d),A)
   write(d/'steam-account.json',{'steamId':'','at':time.time()});self.assertIsNone(active_account(d,d))
if __name__=='__main__':unittest.main()
