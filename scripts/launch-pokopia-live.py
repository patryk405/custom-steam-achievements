#!/usr/bin/env python3
"""Launch native Linux Recompia as a child and expose read-only progress to CSA.
No injection, mod, memory writes, save reads, sudo or permission changes.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tracker'))
from adapters.pokopia_live import BUILD,PROTOCOL,ProcessMemory,Sampler,nso_probes

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True,help='Actual exefs/main NSO loaded by the game (2.0.1)')
    p.add_argument('--cwd',type=Path,required=True,help='Recompia game directory')
    p.add_argument('--check',action='store_true',help='Validate main/configuration only; never launch the game')
    p.add_argument('command',nargs=argparse.REMAINDER,help='-- /absolute/path/to/native/pkp [game arguments]')
    a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command or not Path(command[0]).is_absolute() or not Path(command[0]).is_file():p.error('Provide the absolute native game executable, not Steam or its launcher')
    probes=nso_probes(a.main)
    if not a.cwd.is_dir():p.error('Game directory does not exist')
    if a.check:
        print('Supported main verified; no game was launched.');return
    data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'custom-achievements'
    data.mkdir(parents=True,exist_ok=True)
    path=data/'pokopia-live.sock'
    with (data/'pokopia-live.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if path.exists():
            if not path.is_socket() or path.stat().st_uid!=os.getuid():raise ValueError('Unsafe socket path')
            path.unlink()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
            old=os.umask(0o077)
            try:server.bind(str(path))
            finally:os.umask(old)
            server.listen(4);server.settimeout(.5)
            child=subprocess.Popen(command,cwd=a.cwd,start_new_session=True)
            memory=None;sampler=Sampler()
            def forward(sig,_):
                if child.poll() is None:os.killpg(child.pid,sig)
            for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,forward)
            try:
                while child.poll() is None:
                    try:connection,_=server.accept()
                    except socket.timeout:continue
                    with connection:
                        connection.settimeout(1)
                        _,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                        if uid!=os.getuid():continue
                        try:
                            with connection.makefile('rb') as stream:request=stream.readline(32)
                            if request!=b'status\n':continue
                            event={'protocol':PROTOCOL,'build':BUILD,'ready':False,'at':time.monotonic()}
                            try:
                                if child.poll() is not None:raise ValueError('Game exited')
                                if memory is None:memory=ProcessMemory(child.pid)
                                memory.refresh()
                                event['metrics']=sampler.sample(memory.read,probes)
                                event.update(ready=True,at=time.monotonic())
                            except (OSError,ValueError,struct.error) as error:
                                event['message']='Live reader: '+str(error)
                            connection.sendall((json.dumps(event)+'\n').encode())
                        except (OSError,ValueError):pass
            finally:
                if memory:memory.close()
                path.unlink(missing_ok=True)
                if child.poll() is None:
                    child.terminate()
                    try:child.wait(timeout=5)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
            return child.returncode
if __name__=='__main__':sys.exit(main())
