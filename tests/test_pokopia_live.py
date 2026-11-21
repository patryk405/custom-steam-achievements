import json,os,socket,struct,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tracker'))
from adapters.pokopia_live import BASE,BUILD,PROTOCOL,Sampler,LiveReader,ProcessMemory,nso_probes
from adapters.pokopia import LAYOUT
from daemon import Host

class MemoryFixture:
    def __init__(self):
        self.root=0x7801000000;self.state=0x7803000000;self.manager=0x7804000000;self.player=0x7805000000
        self.blocks={};self.probes=[(BASE+0xb1030,struct.pack('<I',0xf2c0002d))]
        for a,b in self.probes:self.blocks[a]=bytearray(b)
        for address,value in [(BASE+0x3561930,self.root),(BASE+0x3561710,self.state),(BASE+0x3561928,self.manager),(self.manager+0x30,self.player),(self.player,BASE+0x322fda8)]:self.put(address,'<Q',value)
        self.put(self.state+0x18,'<B',1);self.put(self.player+0xa9ec,'<B',0);self.clock(100)
        for off,size in [(0x6fa1a4,1024),(0x6f89a4,512*12),(0x6cfdec,1500*6),(0x6d82f0,64*8),(0x4a26a8,32)]:self.blocks[self.root+off]=bytearray(size)
    def put(self,addr,fmt,value):self.blocks[addr]=bytearray(struct.pack(fmt,value))
    def clock(self,n):self.put(self.root+0x4a5418,'<d',n)
    def read(self,address,size):
        for a,b in self.blocks.items():
            if a<=address and address+size<=a+len(b):return bytes(b[address-a:address-a+size])
        raise ValueError('Unmapped fixture')

class LiveTests(unittest.TestCase):
    def test_no_save_clock_and_changes(self):
        f=MemoryFixture();s=Sampler()
        with self.assertRaises(ValueError):s.sample(f.read,f.probes,0)
        f.clock(102);self.assertEqual(s.sample(f.read,f.probes,2)['dex'],0)
        f.blocks[f.root+0x6fa1a4][LAYOUT['dex'][0]]=3
        f.blocks[f.root+0x6f89a4][LAYOUT['habitats'][0]*12]=2
        struct.pack_into('<I',f.blocks[f.root+0x6d82f0],24,50)
        f.clock(104);m=s.sample(f.read,f.probes,4)
        self.assertEqual((m['dex'],m['habitats'],m['water_gun_uses']),(1,1,50))
        self.assertEqual(s.sample(f.read,f.probes,6)['dex'],1) # save clock can be stationary
        f.clock(106);f.put(f.player+0xa9ec,'<B',32)
        with self.assertRaises(ValueError):s.sample(f.read,f.probes,8)
        self.assertIsNone(s.previous)
    def test_first_friend_with_stationary_save_clock(self):
        f=MemoryFixture();s=Sampler();f.clock(0)
        with self.assertRaises(ValueError):s.sample(f.read,f.probes,0)
        self.assertEqual(s.sample(f.read,f.probes,2)['dex'],0)
        f.blocks[f.root+0x6fa1a4][LAYOUT['dex'][0]]=3
        self.assertEqual(s.sample(f.read,f.probes,4)['dex'],1)
        with self.assertRaises(ValueError):s.sample(f.read,f.probes,20) # stale sampling gap
        self.assertEqual(s.sample(f.read,f.probes,22)['dex'],1)
        f.clock(1000)
        with self.assertRaises(ValueError):s.sample(f.read,f.probes,24) # loading another save
        self.assertEqual(s.sample(f.read,f.probes,26)['dex'],1)
        f.clock(0)
        with self.assertRaises(ValueError):s.sample(f.read,f.probes,28) # clock regression
        self.assertEqual(s.sample(f.read,f.probes,30)['dex'],1)

    def test_bad_build_pointer_loading_and_torn_sample(self):
        f=MemoryFixture();s=Sampler()
        for address,fmt,bad in [(BASE+0x3561930,'<Q',0),(f.player,'<Q',1),(f.state+0x18,'<B',0),(f.root+0x4a5418,'<d',float('nan'))]:
            original=bytes(f.blocks[address]);f.put(address,fmt,bad)
            with self.assertRaises(ValueError):s.sample(f.read,f.probes,0)
            f.blocks[address]=bytearray(original)
        with self.assertRaises(ValueError):s.sample(f.read,[(BASE+0xb1030,b'xxxx')],0)
        original=f.read;calls=0
        def torn(a,n):
            nonlocal calls
            if a==f.root+0x6fa1a4:
                calls+=1
                if calls==2:f.blocks[a][LAYOUT['dex'][0]]=3
            return original(a,n)
        with self.assertRaises(ValueError):s.sample(torn,f.probes,0)
        self.assertIsNone(s.previous)
    def test_socket_host_unlock_without_save_and_stale_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'live.sock';server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.bind(str(path));server.listen();self.addCleanup(server.close)
            m=json.loads((ROOT/'resources/pokopia-adapter.json').read_text());m['socket']=str(path)
            catalog=json.loads((ROOT/'resources/catalog.json').read_text())
            def exchange(event,action):
                def serve():
                    c,_=server.accept()
                    with c:
                        self.assertEqual(c.recv(32),b'status\n');c.sendall((json.dumps(event)+'\n').encode())
                t=threading.Thread(target=serve);t.start()
                try:action()
                finally:t.join(2)
            event={'protocol':PROTOCOL,'build':BUILD,'ready':True,'at':time.monotonic(),'metrics':{'dex':1,'habitats':1,'recipes':0,'moves':0,'water_gun_uses':50}}
            host=Host(root/'state',[m],catalog);host.state['games']['oot']={'kept':{'current':1}}
            exchange(event,host.tick)
            self.assertEqual(host.state['status']['pokopia']['mode'],'live')
            self.assertEqual(set(host.state['games']['pokopia']),{'pokopia_first_friend','pokopia_first_habitat','pokopia_fertilizer_master'})
            self.assertEqual(host.state['games']['oot'],{'kept':{'current':1}})
            self.assertFalse(any(root.rglob('CMNDAT.BIN')))
            def reject():
                with self.assertRaises(ValueError):LiveReader().read_metrics(path)
            exchange({**event,'at':time.monotonic()-100},reject)
            exchange({**event,'metrics':{**event['metrics'],'dex':True}},reject)
    def test_live_only_never_uses_save_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=json.loads((ROOT/'resources/pokopia-adapter.json').read_text());m.update(root=tmp,socket=tmp+'/missing.sock')
            host=Host(Path(tmp)/'state',[m]);host.tick()
            self.assertEqual(host.state['status']['pokopia']['mode'],'live-waiting');self.assertNotIn('pokopia',host.state['games'])
    @unittest.skipUnless(sys.platform=='linux','Linux process reader')
    def test_real_parent_can_read_child_without_permission_changes(self):
        # A tiny Python fixture, NOT a game. It maps its own test buffer.
        code='''import ctypes,sys
lib=ctypes.CDLL(None);lib.mmap.restype=ctypes.c_void_p
p=lib.mmap(ctypes.c_void_p(0x7100000000),4096,3,0x100022,-1,0)
if p!=0x7100000000: sys.exit(2)
ctypes.memmove(p,b"CSA!",4)
print("ready",flush=True);sys.stdin.readline()
'''
        p=subprocess.Popen([sys.executable,'-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        try:
            self.assertEqual(p.stdout.readline().strip(),'ready')
            memory=ProcessMemory(p.pid)
            try:
                self.assertEqual(memory.read(BASE,4),b'CSA!')
                with self.assertRaises(ValueError):memory.read(0,4)
            finally:memory.close()
        finally:
            p.stdin.close();p.wait(timeout=5);p.stdout.close()
    def test_main_header_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'main';p.write_bytes(b'not a game')
            with self.assertRaises(ValueError):nso_probes(p)
