"""Configure Windows live readers without touching games, saves or Steam files."""
import json
import os
from pathlib import Path
import subprocess
import sys
from cloud import write, read
from adapters.pokopia_live import nso_probes

def native_exe(path):
    path=Path(path).expanduser().resolve(strict=True)
    with path.open('rb') as f:
        header=f.read(64)
        if len(header)!=64 or header[:2]!=b'MZ':raise ValueError('Choose the native Windows game .exe')
        offset=int.from_bytes(header[60:64],'little')
        if not 64<=offset<=16*1024*1024:raise ValueError('Invalid Windows executable')
        f.seek(offset);pe=f.read(6)
        if pe[:4]!=b'PE\0\0' or pe[4:6]!=b'\x64\x86':raise ValueError('Choose an x64 Windows executable')
    return path

def configure_live(root,data,game,exe,main=None):
    if game not in ('oot','pokopia'):raise ValueError('Unsupported live setup')
    exe=native_exe(exe)
    manifest=json.loads((root/'resources'/f'{game}-adapter.json').read_text())
    if game=='oot':
        if exe.name.casefold()!='longshot.exe':raise ValueError('Select bin/longshot.exe, not the Longshot Launcher')
        manifest.update(windowsExe=str(exe),windowsPipe='csa-longshot-v3')
    else:
        if exe.name.casefold()!='pkp.exe':raise ValueError('Select the compiled pkp.exe, not Recompia.exe')
        main=Path(main or '').expanduser().resolve(strict=True)
        nso_probes(main)
        manifest.update(windowsExe=str(exe),windowsMain=str(main),live='recompia-memory-v1',liveOnly=True)
    write(data/'adapters'/f'{game}-adapter.json',manifest)
    return manifest

def longshot_command(data):
    manifest=read(data/'adapters/oot-adapter.json')
    exe=native_exe(manifest.get('windowsExe',''))
    if exe.name.casefold()!='longshot.exe':raise ValueError('Configure bin/longshot.exe first')
    pipe=manifest.get('windowsPipe')
    if pipe!='csa-longshot-v3':raise ValueError('Unexpected control endpoint')
    cwd=exe.parent.parent if exe.parent.name.casefold()=='bin' else exe.parent
    env={**os.environ,'HOS_CONTROL':pipe}
    # Read-only status/subscriptions never require raw-memory access or cross-user access.
    env.pop('HOS_CONTROL_MEM',None);env.pop('HOS_CONTROL_PEER_SID',None)
    return [str(exe)],cwd,env

def launch_longshot(data):
    if os.name!='nt':raise OSError('This launch helper is for Windows')
    command,cwd,env=longshot_command(data)
    return subprocess.call(command,cwd=cwd,env=env)

def create_longshot_shortcut(data):
    if os.name!='nt':return None
    if getattr(sys,'frozen',False):
        target=sys.executable;arguments='--launch-longshot'
    else:
        target=sys.executable;arguments=subprocess.list2cmdline([str(Path(__file__).with_name('daemon.py')),'--launch-longshot'])
    destination=data/'Ocarina of Time - Achievements.lnk'
    # Paths are passed as environment values, never interpolated into PowerShell code.
    script='$s=New-Object -ComObject WScript.Shell; $l=$s.CreateShortcut($env:CSA_LINK); $l.TargetPath=$env:CSA_TARGET; $l.Arguments=$env:CSA_ARGS; $l.Save()'
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
                   env={**os.environ,'CSA_LINK':str(destination),'CSA_TARGET':target,'CSA_ARGS':arguments},
                   check=True,timeout=15,capture_output=True)
    return destination
