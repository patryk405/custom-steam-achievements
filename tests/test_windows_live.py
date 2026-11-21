import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tracker'))
from adapters.longshot_live import LongshotReader
from lz4_block import decompress

class PortableWindowsTests(unittest.TestCase):
    def test_lz4_overlap_and_bounds(self):
        self.assertEqual(decompress(b'\x35abc\x03\x00',12),b'abcabcabcabc')
        self.assertEqual(decompress(b'\x50hello',5),b'hello')
        for data,size in [(b'\x00\x00\x00',4),(b'\xf0',30),(b'\x50hi',5),(b'\x35abc\x03\x00',11)]:
            with self.assertRaises(ValueError):decompress(data,size)
    def test_config_rejects_launcher_and_invalid_image(self):
        from windows_setup import configure_live
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'pkp.exe';p.write_bytes(b'not a PE')
            with self.assertRaises(ValueError):configure_live(ROOT,Path(tmp)/'data','pokopia',p)
            self.assertFalse((Path(tmp)/'data').exists())

@unittest.skipUnless(os.name=='nt','Real Windows kernel integration')
class WindowsLiveTests(unittest.TestCase):
    def start_child(self,*args):
        p=subprocess.Popen([sys.executable,str(ROOT/'tests/windows_fixture.py'),*args],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def cleanup():
            p.terminate()
            try:p.communicate(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.communicate()
        self.addCleanup(cleanup)
        line=p.stdout.readline()
        if not line:self.fail(p.stderr.read())
        return p,line
    def test_named_pipe_status_flags_and_walking(self):
        name='csa-test-'+uuid.uuid4().hex
        self.start_child('pipe',name,'ok')
        reader=LongshotReader()
        first=reader.read_metrics(name,{'flag':'owned_sword'},sys.executable)
        self.assertEqual(first['rupees'],1);self.assertEqual(first['flag'],1)
        second=reader.read_metrics(name,None,sys.executable)
        self.assertEqual(second['live:distance'],5)
    def test_named_pipe_timeout_and_version_rejection(self):
        name='csa-test-'+uuid.uuid4().hex
        self.start_child('pipe',name,'timeout')
        from windows_native import NamedPipe
        start=time.monotonic()
        with NamedPipe(name,sys.executable,timeout=.1) as pipe:
            pipe.sendall(b'{"id":1,"cmd":"status"}\n')
            with self.assertRaises(TimeoutError):pipe.readline(65537)
        self.assertLess(time.monotonic()-start,2)
        name='csa-test-'+uuid.uuid4().hex
        self.start_child('pipe',name,'version')
        with self.assertRaisesRegex(ValueError,'version'):LongshotReader().read_metrics(name,None,sys.executable)
        with self.assertRaises(ValueError):NamedPipe(r'\\remote\pipe\untrusted')
    def test_process_memory_samples_without_saves(self):
        from windows_native import ProcessMemory,find_process
        from adapters.pokopia_live import Sampler
        p,line=self.start_child('memory')
        probes=[(a,bytes.fromhex(b)) for a,b in json.loads(line)['probes']]
        with self.assertRaisesRegex(ValueError,'exactly one'):find_process(sys.executable)
        memory=ProcessMemory(p.pid,sys.executable);self.addCleanup(memory.close)
        sampler=Sampler()
        with self.assertRaisesRegex(ValueError,'two stable'):sampler.sample(memory.read,probes,now=1)
        self.assertEqual(sampler.sample(memory.read,probes,now=2)['dex'],0)
        p.stdin.write('dex\n');p.stdin.flush();self.assertEqual(p.stdout.readline().strip(),'ok')
        self.assertEqual(sampler.sample(memory.read,probes,now=3)['dex'],1)
        with self.assertRaises(ValueError):memory.read(1,8)
        with self.assertRaises(ValueError):memory.read(0x71fffffff0,32)
        with self.assertRaises(ValueError):ProcessMemory(p.pid,str(ROOT/'wrong.exe'))
        p.terminate();p.wait(timeout=5)
        with self.assertRaises((OSError,ValueError)):memory.read(probes[0][0],4)
    def test_windows_reader_discards_restart_baseline(self):
        from adapters.pokopia_windows import LiveReader
        p,line=self.start_child('memory');probes=[(a,bytes.fromhex(b)) for a,b in json.loads(line)['probes']]
        with tempfile.TemporaryDirectory() as tmp:
            main=Path(tmp)/'main';main.write_bytes(b'fixture')
            manifest={'windowsExe':sys.executable,'windowsMain':str(main)}
            reader=LiveReader()
            with patch('windows_native.find_process',return_value=p.pid),patch('adapters.pokopia_windows.nso_probes',return_value=probes),patch('adapters.pokopia_live.time.monotonic',side_effect=[1,2]):
                with self.assertRaises(ValueError):reader.read_metrics(manifest)
                self.assertEqual(reader.read_metrics(manifest)['dex'],0)
            with patch('windows_native.find_process',side_effect=ValueError('exited')):
                with self.assertRaises(ValueError):reader.read_metrics(manifest)
            self.assertIsNone(reader.identity);self.assertIsNone(reader.sampler.previous)

if __name__=='__main__':unittest.main()
