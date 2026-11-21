"""Protocol fixtures from Longshot v3.0.0; no game launch or real unlocks."""
import copy
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tracker'))
from adapters.longshot_live import LongshotReader
from daemon import Host
from engine import apply_rules
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'resources/oot-adapter.json').read_text())
CAT=json.loads((ROOT/'resources/catalog.json').read_text())
DEFS={a['id']:a for a in CAT['oot']['achievements']}
def sample(frame=100,x=0,rupees=0):
    return {'id':1,'ok':True,'protocol':1,'version':'v3.0.0 (source bd6a0cdd)','state':'play','stalled':False,'frame':frame,'game':{'frame':frame,'t':frame/60+1000,'map':'KokiriForest_Child','event':False,'loading':False,'age':'child','pos':[x,0,0],'rupees':rupees}}
class LongshotTests(unittest.TestCase):
    def test_two_unlocks_and_no_save_needed(self):
        r=LongshotReader();s={}
        for reply in [sample(),sample(220,3),sample(340,6,1)]:
            s=apply_rules(s,MANIFEST,r.consume(reply,1),DEFS,100)
        self.assertEqual({k:v['current'] for k,v in s.items()},{'oot_first_steps':5,'oot_pocket_change':1})
    def test_loading_menu_stale_and_unknown_version_do_not_count(self):
        for changes in [{'state':'menu'},{'stalled':True},{'version':'3.1.0'},{'protocol':2}]:
            with self.assertRaises(ValueError):LongshotReader().consume({**sample(),**changes},1)
        for changes in [{'loading':True},{'event':True},{'frame':1},{'pos':None}]:
            v=sample();v['game'].update(changes)
            with self.assertRaises(ValueError):LongshotReader().consume(v,1)
        r=LongshotReader();r.consume(sample(),1)
        with self.assertRaises(ValueError):r.consume(sample(),1)
    def test_teleport_scene_change_and_restart_do_not_add_distance(self):
        r=LongshotReader();r.consume(sample(),1)
        self.assertEqual(r.consume(sample(220,100),1)['live:distance'],0)
        v=sample(340,103);v['game']['map']='LinksHouse'
        self.assertEqual(r.consume(v,1)['live:distance'],0)
        self.assertEqual(r.consume(sample(460,106),2)['live:distance'],0)
        v=sample(580,109);v['game']['rupees']=None
        self.assertNotIn('rupees',r.consume(v,2))
    def test_host_uses_read_only_socket_and_keeps_botw_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);path=base/'control.sock';commands=[]
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
                server.bind(str(path));server.listen();server.settimeout(3)
                def serve():
                    conn,_=server.accept()
                    with conn,conn.makefile('rb') as f:
                        commands.append(json.loads(f.readline()))
                        conn.sendall((json.dumps(sample(100,0,1))+'\n').encode())
                        commands.append(json.loads(f.readline()))
                        conn.sendall(b'{"id":2,"ok":true}\n')
                        event={'event':'oot','sub':2,'frame':101,'game':{'frame':101,'loading':False,'flags':{v:0 for v in MANIFEST['watch'].values()}}}
                        conn.sendall((json.dumps(event)+'\n').encode())
                t=threading.Thread(target=serve);t.start()
                host=Host(base,[{**MANIFEST,'socket':str(path)}],CAT)
                host.state['games']['botw']={'existing':{'current':1}}
                host.tick();t.join(4)
                self.assertEqual([c['cmd'] for c in commands],['status','subscribe'])
                self.assertEqual(commands[1]['flags'],list(MANIFEST['watch'].values()))
                self.assertEqual(host.state['games']['oot']['oot_pocket_change']['current'],1)
                self.assertEqual(host.state['games']['botw'],{'existing':{'current':1}})
                self.assertEqual(host.state['status']['oot']['mode'],'live')
            host.tick()
            self.assertTrue(host.state['status']['oot']['error'])
            self.assertEqual(host.state['games']['oot']['oot_pocket_change']['current'],1)
class FullSetTests(unittest.TestCase):
    def test_every_rule_unlocks_and_missing_signals_fail_closed(self):
        self.assertEqual(len(DEFS),66)
        self.assertEqual(set(DEFS),set(MANIFEST['rules']))
        self.assertLessEqual(len(MANIFEST['watch']),64)
        for id, rule in MANIFEST['rules'].items():
            metrics={f:(rule.get('threshold',1) if rule['op']=='number' else 1) for f in rule['flags']}
            result=apply_rules({},MANIFEST,metrics,DEFS,100)
            self.assertEqual(result[id]['current'],DEFS[id]['target'],id)
            del metrics[rule['flags'][0]]
            self.assertNotIn(id,apply_rules({},MANIFEST,metrics,DEFS,100),id)
    def test_null_enum_negative_and_loading_signals_rejected(self):
        watch={'a':'0x12345678'}
        event={'event':'oot','sub':2,'frame':100,'game':{'frame':100,'loading':False,'flags':{}}}
        for bad in [None,'#1234',-1,1.5]:
            event['game']['flags']['0x12345678']=bad
            self.assertEqual(LongshotReader.flag_metrics(event,watch),{})
        event['game']['flags']['0x12345678']=True
        self.assertEqual(LongshotReader.flag_metrics(event,watch),{'a':True})
        event['game']['loading']=True
        with self.assertRaises(ValueError):LongshotReader.flag_metrics(event,watch)
    def test_real_manifest_flags_exist_in_recorded_game_schema(self):
        evidence=json.loads((ROOT/'resources/oot-signals.json').read_text())['signals']
        self.assertEqual(set(evidence),set(MANIFEST['watch']))
        for name,record in evidence.items():
            self.assertIn(record['type'],('Bool','Int','UInt'))
            self.assertEqual(record['hash'],MANIFEST['watch'][name])
            self.assertEqual(record['default'],0,name)

if __name__=='__main__':unittest.main()
