import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tracker'))
from engine import apply_rules, evaluate
from daemon import Host
from adapters.botw import read_flags, read_metrics
from adapters.snapshot import read_metrics as read_snapshot

ROOT=Path(__file__).resolve().parents[1]
CAT=json.loads((ROOT/'resources/catalog.json').read_text())
BOTW=json.loads((ROOT/'resources/botw-adapter.json').read_text())
def synthetic(flags):
    entries=sorted((zlib.crc32(k.encode()),v) for k,v in flags.items())
    return struct.pack('<III',0x4730,0xffffffff,1)+b''.join(struct.pack('<II',*v) for v in entries)+b'\xff'*4

class TrackerTests(unittest.TestCase):
    def test_missing_and_invalid_signals_never_unlock(self):
        rule={'op':'all','flags':['a','b']}
        for metrics in [{},{'a':1},{'a':1,'b':2},{'a':1,'b':float('nan')},{'a':1,'b':'1'}]:
            self.assertIsNone(evaluate(rule,metrics,1))
        self.assertEqual(evaluate(rule,{'a':1,'b':0},1),0)
        self.assertEqual(evaluate(rule,{'a':1,'b':1},1),1)

    def test_partial_progress_and_monotonic_unlocks(self):
        rule={'op':'number','flags':['shrines'],'threshold':30}
        manifest={'id':'test','rules':{'x':rule}}
        defs={'x':{'target':30}}
        s=apply_rules({},manifest,{'shrines':12},defs,100)
        self.assertEqual(s['x']['current'],12);self.assertNotIn('unlockedAt',s['x'])
        s=apply_rules(s,manifest,{'shrines':30},defs,200)
        self.assertEqual(s['x']['unlockedAt'],200)
        for value in [0,5,40]:
            s=apply_rules(s,manifest,{'shrines':value},defs,300)
            self.assertEqual(s['x']['current'],30);self.assertEqual(s['x']['unlockedAt'],200)

    def test_botw_parser_rejects_wrong_revision_truncation_size(self):
        data=synthetic({'FirstTouchdown':1})
        self.assertTrue(read_flags(data,{'18224':len(data)}))
        for bad in [data[:-1],data[:-4]+b'NOPE',b'\x00'*4+data[4:]]:
            with self.assertRaises(ValueError):read_flags(bad,{'18224':len(data)})
        with self.assertRaises(ValueError):read_flags(data,{'18224':len(data)+8})
        with self.assertRaises(ValueError):read_flags(data,{'18224':len(data)-8})

    def test_real_botw_rule_set_on_synthetic_save(self):
        flags={name:0 for rule in BOTW['rules'].values() for name in rule['flags'] if not name.startswith('caption:')}
        flags.update({'FirstTouchdown':1,'HiddenKorok_Number':450,'Clear_RemainsWater':1})
        flags.update({f'Clear_Dungeon{i:03}':1 for i in range(30)})
        data=synthetic(flags)
        manifest={**BOTW,'versions':{'18224':len(data)}}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'game_data.sav';path.write_bytes(data)
            path.with_name('caption.sav').write_bytes(synthetic({'GameClear':1}))
            metrics=read_metrics(path,manifest)
            result=apply_rules({},manifest,metrics,{a['id']:a for a in CAT['botw']['achievements']},100)
            self.assertEqual(result['reddit_shrines30']['current'],30)
            self.assertEqual(result['reddit_shrines60']['current'],30)
            self.assertNotIn('unlockedAt',result['reddit_shrines60'])
            for name in ['reddit_calamity','reddit_korok_half','reddit_ruta','reddit_plateau']:
                self.assertEqual(result[name]['current'],1)
            for name in ['reddit_bomb25','reddit_korok_all','reddit_rudania']:
                self.assertNotIn(name,result)

    def test_generic_adapter_stability_restart_pause_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);saves=base/'saves';saves.mkdir();data=base/'data';data.mkdir()
            manifest={'id':'generic-example','game':'oot','kind':'json-snapshot','root':str(saves),'glob':'*.json','rules':{'deku':{'op':'any','flags':['deku_clear']}}}
            path=saves/'progress.json';path.write_text(json.dumps({'schema':1,'game':'oot','metrics':{'deku_clear':True}}))
            fixture_catalog={**CAT, 'oot':{'achievements':[{'id':'deku','target':1}]}}
            host=Host(data,[manifest],fixture_catalog);host.tick()
            self.assertNotIn('oot',host.state['games'])
            host.tick();self.assertEqual(host.state['games']['oot']['deku']['current'],1)
            original=host.state['games']['oot']['deku']['unlockedAt']
            restarted=Host(data,[manifest],fixture_catalog);restarted.tick();restarted.tick()
            self.assertEqual(restarted.state['games']['oot']['deku']['unlockedAt'],original)
            (data/'preferences.json').write_text('{"autoEnabled":false}')
            restarted.tick();self.assertIn('paused',restarted.state['status']['oot']['message'])
            (data/'preferences.json').write_text('{"autoEnabled":true}')
            path.write_text('{');restarted.tick();restarted.tick()
            self.assertTrue(restarted.state['status']['oot']['error'])
            self.assertEqual(restarted.state['games']['oot']['deku']['current'],1)
            self.assertEqual(path.read_text(),'{')  # Never repairs/writes the game input.
            self.assertNotIn('botw',restarted.state['games'])

    def test_snapshot_rejects_cross_game_input(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'p.json';p.write_text('{"schema":1,"game":"botw","metrics":{"deku_clear":true}}')
            with self.assertRaises(ValueError):read_snapshot(p,{'game':'oot'})

    def test_supported_rule_ids_exist_and_manual_only_has_no_rule(self):
        ids={a['id'] for a in CAT['botw']['achievements']}
        self.assertTrue(set(BOTW['rules'])<=ids)
        self.assertEqual(len(BOTW['rules']),39)
        for id in ['reddit_bomb25','reddit_stasis75','reddit_no_deaths','reddit_sword_boss']:
            self.assertNotIn(id,BOTW['rules'])

if __name__=='__main__':unittest.main()
