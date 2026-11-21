import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tracker'))
from adapters.bbport import read_metrics,load_definitions,NP_ID
from daemon import Host
from engine import apply_rules
class BBPortTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.manifest={'id':'bbport-trophies-v1','game':'bloodborne','kind':'bbport-trophies','root':str(self.root),'titleId':'CUSA03173','trophies':['1','2'],'rules':{'bb_trophy_1':{'op':'any','flags':['trophy:1']},'bb_trophy_2':{'op':'any','flags':['trophy:2']}}}
    def event(self,id=1,**kw):return json.dumps({'v':1,'title_id':'CUSA03173','trophy_id':id,'unlocked_at':'2026-10-10T06:30:00Z',**kw})+'\n'
    def test_incremental_events_no_save_and_no_false_titles(self):
        p=self.root/'trophies.jsonl';p.write_text(self.event()+self.event()+self.event(2,title_id='CUSA99999')+self.event(2,v=2)+self.event(True)+self.event(2,unlocked_at='bad')+'{broken}\n'+self.event(2).rstrip())
        self.assertEqual(read_metrics(self.root,self.manifest),{'trophy:1':1})
        with p.open('a') as f:f.write('\n')
        self.assertEqual(read_metrics(self.root,self.manifest),{'trophy:1':1,'trophy:2':1})
    def test_existing_unlocks_exact_np_folder(self):
        other=self.root/'trophy/OTHER';other.mkdir(parents=True);(other/'unlocked.txt').write_text('1\n')
        with self.assertRaises(ValueError):read_metrics(self.root,self.manifest)
        good=self.root/'trophy'/NP_ID;good.mkdir();(good/'unlocked.txt').write_text('# comment\n2\n999\n-1\nabc\n')
        self.assertEqual(read_metrics(self.root,self.manifest),{'trophy:2':1})
    def test_import_english_catalog_and_reject_duplicates_entities(self):
        folder=self.root/'trophy'/NP_ID;folder.mkdir(parents=True)
        path=folder/'TROP_01.XML'
        node='<trophy id="001" ttype="B"><name>A &amp; B</name><detail>Test objective</detail></trophy>'
        path.write_text('<!--signature-->\n<trophyconf>'+node+'</trophyconf>')
        defs=load_definitions(self.root);self.assertEqual(defs[0]['name'],'A & B');self.assertEqual(defs[0]['id'],'bb_trophy_1')
        path.write_text('<trophyconf>'+node*2+'</trophyconf>')
        with self.assertRaises(ValueError):load_definitions(self.root)
        path.write_text('<!DOCTYPE trophyconf><trophyconf>'+node+'</trophyconf>')
        with self.assertRaises(ValueError):load_definitions(self.root)
    def test_host_unlock_and_restart_keep_other_games(self):
        p=self.root/'trophies.jsonl';p.write_text(self.event())
        catalog={'bloodborne':{'achievements':[{'id':'bb_trophy_1','target':1},{'id':'bb_trophy_2','target':1}]}}
        host=Host(self.root/'state',[self.manifest],catalog);host.state['games']['oot']={'kept':{'current':1}};host.tick()
        self.assertEqual(host.state['games']['bloodborne']['bb_trophy_1']['current'],1)
        stamp=host.state['games']['bloodborne']['bb_trophy_1']['unlockedAt']
        restarted=Host(self.root/'state',[self.manifest],catalog);restarted.tick()
        self.assertEqual(restarted.state['games']['bloodborne']['bb_trophy_1']['unlockedAt'],stamp)
        self.assertEqual(restarted.state['games']['oot'],{'kept':{'current':1}})
        self.assertEqual(p.read_text(),self.event())
    def test_unconfigured_host_does_not_read_working_directory(self):
        manifest={**self.manifest,'root':'','rules':{}}
        host=Host(self.root/'state',[manifest],{'bloodborne':{'achievements':[]}});host.tick()
        self.assertNotIn('bloodborne',host.state['games'])
        self.assertIn('not configured',host.state['status']['bloodborne']['message'])
if __name__=='__main__':unittest.main()
