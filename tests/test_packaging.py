import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tracker'))
from setup_ui import save_configuration
from platform_support import data_directory, acquire_lock

class PackagingTests(unittest.TestCase):
    def test_setup_preserves_game_save_and_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp)/'data'; data.mkdir()
            save=Path(tmp)/'CMNDAT.BIN'; save.write_bytes(b'unchanged game data')
            state=data/'state.json'; state.write_text('{"existing":"progress"}')
            save_configuration(ROOT,data,'pokopia',str(save))
            manifest=json.loads((data/'adapters/pokopia-adapter.json').read_text())
            self.assertEqual(manifest['root'],str(save.parent))
            self.assertFalse(manifest['liveOnly'])
            self.assertEqual(save.read_bytes(),b'unchanged game data')
            self.assertEqual(state.read_text(),'{"existing":"progress"}')
    def test_invalid_config_leaves_no_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):save_configuration(ROOT,Path(tmp),'bloodborne',tmp,'wrong')
            self.assertFalse((Path(tmp)/'adapters').exists())
    def test_self_test_does_not_create_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            env={**os.environ,'LOCALAPPDATA':tmp,'XDG_DATA_HOME':tmp}
            result=subprocess.run([sys.executable,str(ROOT/'tracker/daemon.py'),'--self-test'],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(list(Path(tmp).iterdir()),[])
    def test_lock_excludes_another_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'lock'
            with path.open('a+b') as lock:
                acquire_lock(lock)
                code="import sys;sys.path.insert(0,sys.argv[1]);from platform_support import acquire_lock;f=open(sys.argv[2],'a+b');acquire_lock(f)"
                child=subprocess.run([sys.executable,'-c',code,str(ROOT/'tracker'),str(path)],capture_output=True)
                self.assertNotEqual(child.returncode,0)
