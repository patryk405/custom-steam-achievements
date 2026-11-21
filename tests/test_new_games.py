import hashlib,json,struct,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tracker'))
from adapters import arceus,odyssey,pokopia
from daemon import Host
from engine import apply_rules

# Fixture serializers are deliberately separate from production readers.
def byml(root):
    names=sorted(set(k for obj in walk(root) if isinstance(obj,dict) for k in obj))
    data=bytearray(b'YB\x03\0'+b'\0'*12)
    def u32(n):return struct.pack('<I',n)
    def align():
        while len(data)%4:data.append(0)
    def table(strings):
        off=len(data);data.extend(u32(0xc2|len(strings)<<8));start=len(data);data.extend(b'\0'*(4*len(strings)))
        for i,s in enumerate(strings):
            data[start+i*4:start+i*4+4]=u32(len(data)-off);data.extend(s.encode()+b'\0')
        align();return off
    keyoff=table(names)
    def node(obj):
        if isinstance(obj,dict):
            off=len(data);data.extend(u32(0xc1|len(obj)<<8));start=len(data);data.extend(b'\0'*(8*len(obj)))
            for i,(k,v) in enumerate(obj.items()):
                typ,raw=value(v);data[start+i*8:start+i*8+8]=u32(names.index(k)|typ<<24)+raw
        else:
            off=len(data);data.extend(u32(0xc0|len(obj)<<8));types=len(data);data.extend(b'\0'*len(obj));align();start=len(data);data.extend(b'\0'*(4*len(obj)))
            for i,v in enumerate(obj):
                typ,raw=value(v);data[types+i]=typ;data[start+i*4:start+i*4+4]=raw
        return off
    def value(v):
        if isinstance(v,(dict,list)):return (0xc1 if isinstance(v,dict) else 0xc0,u32(node(v)))
        if type(v)==bool:return 0xd0,u32(v)
        return 0xd1,struct.pack('<i',v)
    rootoff=node(root);data[4:16]=struct.pack('<III',keyoff,0,rootoff)
    return b'\0'*16+data

def walk(obj):
    yield obj
    if isinstance(obj,dict):
        for v in obj.values():yield from walk(v)
    if isinstance(obj,list):
        for v in obj:yield from walk(v)

def pla(blocks):
    def stream(seed):
        def advance(s):
            s=(s^(s<<2))&0xffffffff;s^=s>>15;return (s^(s<<13))&0xffffffff
        state=seed
        for _ in range(bin(seed).count('1')):state=advance(state)
        while True:
            yield from struct.pack('<I',state);state=advance(state)
    payload=bytearray()
    for key,(typ,val) in sorted(blocks.items()):
        decoded=bytes([typ])+(struct.pack('<I',val) if typ==10 else struct.pack('<I',0) if typ==4 else b'')
        rng=stream(key);payload.extend(struct.pack('<I',key));payload.extend(b^next(rng) for b in decoded)
    encoded=bytes(v^arceus.StaticXorpad[i%127] for i,v in enumerate(payload))
    return encoded+hashlib.sha256(arceus.IntroHashBytes+encoded+arceus.OutroHashBytes).digest()

class NewGameTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.catalog=json.loads((ROOT/'resources/catalog.json').read_text())
    def manifest(self,name):return json.loads((ROOT/'resources'/f'{name}-adapter.json').read_text())
    def test_arceus_checksum_identity_and_metrics(self):
        m=self.manifest('arceus')
        blocks={0x02168706:(4,0),0xF25C070E:(4,0),0x50FE632A:(10,3),0x96774421:(2,0)}
        raw=pla(blocks);metrics=arceus.decode(raw,m['blocks'])
        self.assertEqual(metrics,{'block:50FE632A':3,'block:96774421':1})
        with self.assertRaises(ValueError):arceus.decode(raw[:-1]+bytes([raw[-1]^1]),m['blocks'])
        with self.assertRaises(ValueError):arceus.decode(pla({0x50FE632A:(10,3)}),m['blocks'])
        blocks[0x50FE632A]=(10,11)
        with self.assertRaises(ValueError):arceus.decode(pla(blocks),m['blocks'])
    def test_arceus_host_stability_pause_restart_and_no_game_writes(self):
        m=self.manifest('arceus');m.update(root=str(self.root),glob='main')
        p=self.root/'main';raw=pla({0x02168706:(4,0),0xF25C070E:(4,0),0x50FE632A:(10,1) });p.write_bytes(raw)
        host=Host(self.root/'state',[m],self.catalog);host.tick()
        self.assertNotIn('arceus',host.state['games']);host.tick()
        self.assertEqual(host.state['games']['arceus']['arceus_expeditionteamrank1']['current'],1)
        self.assertNotIn('arceus_defeatedarceus',host.state['games']['arceus'])
        previous=host.state['games']['arceus']
        restarted=Host(self.root/'state',[m],self.catalog);restarted.tick();restarted.tick()
        self.assertEqual(previous,restarted.state['games']['arceus']);self.assertEqual(p.read_bytes(),raw)
    def test_odyssey_binary_and_boundaries(self):
        root={'WorldInfo':[{'UnlockedWorldId':1,'PayShineNum':3},{'UnlockedWorldId':-1,'PayShineNum':0}], 'ShineData':[], 'GameProgressData':{}}
        raw=byml(root);self.assertEqual(odyssey.extract(odyssey.parse(raw)),{'kingdom:1':1,'moons:1':3,'moons':3})
        with self.assertRaises(ValueError):odyssey.parse(raw[:22])
        with self.assertRaises(ValueError):odyssey.extract({})
        root['WorldInfo'][0]['PayShineNum']=-1
        with self.assertRaises(ValueError):odyssey.extract(root)
        cycle=bytearray(raw);rootoff=int.from_bytes(raw[28:32],'little');cycle[16+rootoff+4:16+rootoff+8]=struct.pack('<I',0xc1000000);cycle[16+rootoff+8:16+rootoff+12]=struct.pack('<I',rootoff)
        with self.assertRaises(ValueError):odyssey.parse(cycle)
    def test_pokopia_direct_save_no_mod_and_host_persistence(self):
        import zlib
        m=self.manifest('pokopia');m.pop('live',None);folder=self.root/'account'/'profile'/'G00';folder.mkdir(parents=True)
        m.update(root=str(folder),glob='CMNDAT.BIN');p=folder/'CMNDAT.BIN'
        data=bytearray(pokopia.SIZE)
        data[0x426EFF+pokopia.LAYOUT['dex'][0]]=3
        data[0x4256FF+pokopia.LAYOUT['habitats'][0]*12]=2
        struct.pack_into('<I',data,0x405047+3*8,50)
        def save(data):
            compressed=zlib.compress(data);header=bytearray(pokopia.HEADER)
            struct.pack_into('<III',header,0,0x31227687,0x0200017D,0x40001)
            struct.pack_into('<I',header,0x10,len(header)+len(compressed))
            return bytes(header)+compressed
        raw=save(data);p.write_bytes(raw)
        self.assertEqual(pokopia.read_metrics(p,m),{'dex':1,'habitats':1,'recipes':0,'water_gun_uses':50,'moves':0})
        host=Host(self.root/'state',[m],self.catalog);host.tick();host.tick()
        unlocked=host.state['games']['pokopia']
        self.assertEqual(set(unlocked),{'pokopia_first_friend','pokopia_first_habitat','pokopia_fertilizer_master'})
        restarted=Host(self.root/'state',[m],self.catalog);restarted.tick();restarted.tick()
        self.assertEqual(unlocked,restarted.state['games']['pokopia']);self.assertEqual(p.read_bytes(),raw)
        marker=folder.parent.with_name(folder.parent.name+'.commit');marker.touch()
        with self.assertRaises(ValueError):pokopia.read_metrics(p,m)
        for invalid in (raw[:20],raw[:-3],save(data+b'x')):
            with self.assertRaises((ValueError,zlib.error)):pokopia.parse(invalid)
        wrong=bytearray(raw);struct.pack_into('<I',wrong,4,0x02000046)
        with self.assertRaises(ValueError):pokopia.parse(wrong)
        data[0x426EFF+pokopia.LAYOUT['dex'][0]]=8
        data[0x4256FF+pokopia.LAYOUT['habitats'][0]*12]=1
        self.assertEqual(pokopia.metrics(data)['dex'],0);self.assertEqual(pokopia.metrics(data)['habitats'],0)
        data[0x405047+10*8+4]=1
        self.assertEqual(pokopia.metrics(data)['moves'],0)
        data[0x220F04+7]=1
        self.assertEqual(pokopia.metrics(data)['moves'],1)
    def test_all_packs_have_rules_and_missing_signals_never_unlock(self):
        for name in ('bbport','arceus','odyssey','pokopia'):
            m=self.manifest(name);defs={a['id']:a for a in self.catalog[m['game']]['achievements']}
            self.assertEqual(set(m['rules']),set(defs));self.assertEqual(len(defs),len(self.catalog[m['game']]['achievements']))
            self.assertEqual(apply_rules({},m,{},defs),{})
            metrics={key:r.get('threshold',1) for r in m['rules'].values() for key in r['flags']}
            result=apply_rules({},m,metrics,defs)
            self.assertEqual(set(result),set(defs))
            self.assertTrue(all(result[k]['current']==v['target'] for k,v in defs.items()))
    def test_unconfigured_games_never_scan_cwd(self):
        manifests=[self.manifest(n) for n in ('arceus','odyssey','pokopia')]
        for m in manifests:m.pop('live',None)
        host=Host(self.root/'state',manifests,self.catalog);host.tick()
        self.assertEqual(host.state['games'],{})
        self.assertTrue(all('Not configured' in s['message'] for s in host.state['status'].values()))
