#!/usr/bin/env python3
"""Prepare a Steam launch script for live Pokopia tracking. Never starts the game."""
import argparse,json,os,shlex,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tracker'))
from adapters.pokopia_live import nso_probes

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-exe',type=Path,required=True,help='Native Linux pkp executable, not launcher/AppImage/Steam')
    p.add_argument('--main',type=Path,required=True,help='The exefs/main NSO used by that game installation')
    p.add_argument('--game-dir',type=Path,required=True)
    p.add_argument('--steam-appid',type=int,required=True)
    p.add_argument('game_args',nargs=argparse.REMAINDER)
    a=p.parse_args()
    exe=a.game_exe.expanduser().resolve(strict=True);main=a.main.expanduser().resolve(strict=True);cwd=a.game_dir.expanduser().resolve(strict=True)
    if not cwd.is_dir() or not exe.is_file() or not os.access(exe,os.X_OK):p.error('Invalid game executable or working directory')
    with exe.open('rb') as f:
        if f.read(4)!=b'\x7fELF':p.error('This prototype requires the native Linux game executable')
    if not 0<a.steam_appid<=0xffffffff:p.error('Invalid Steam shortcut ID')
    nso_probes(main)
    data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'custom-achievements'
    data.mkdir(parents=True,exist_ok=True);launcher=data/'launch-pokopia-live.sh'
    paths=[ROOT/'resources/shortcut-ids.json',ROOT/'resources/pokopia-adapter.json']
    backup=ROOT/'backups'/f'pokopia-live-{time.time_ns()}';backup.mkdir(parents=True)
    for file in paths+([launcher] if launcher.exists() else []):shutil.copy2(file,backup/file.name)
    ids=json.loads(paths[0].read_text());ids['pokopia']=a.steam_appid
    manifest=json.loads(paths[1].read_text());manifest.update(live='recompia-memory-v1',liveOnly=True)
    for path,value in zip(paths,(ids,manifest)):
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
    args=a.game_args[1:] if a.game_args[:1]==['--'] else a.game_args
    command=[sys.executable,str(ROOT/'scripts/launch-pokopia-live.py'),'--main',str(main),'--cwd',str(cwd),'--',str(exe),*args]
    launcher.write_text('#!/bin/sh\nexec '+shlex.join(command)+'\n');launcher.chmod(0o700)
    print(f'Prepared, not launched: {launcher}')
    print('Set this script as the Steam shortcut Target, then rebuild the plugin and restart Steam/tracker.')
if __name__=='__main__':main()
