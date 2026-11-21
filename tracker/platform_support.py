"""Shared paths and single-instance locking for packaged and source installs."""
import os
import sys
from pathlib import Path

def data_directory():
    base = os.environ.get('LOCALAPPDATA', str(Path.home()/'AppData/Local')) if os.name == 'nt' else os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share'))
    return Path(base)/'custom-achievements'

def resource_directory():
    return Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]

def acquire_lock(file):
    if os.name == 'nt':
        import msvcrt
        file.seek(0); file.write(b'0'); file.flush(); file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
