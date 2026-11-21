"""Create a release archive from the PyInstaller directory and compiled plugin."""
import hashlib
import shutil
import sys
from pathlib import Path
platform = sys.argv[1]
if platform not in ('linux','windows'): raise SystemExit('Expected linux or windows')
root = Path(__file__).resolve().parents[1]
out = root/'dist'
name = f'custom-steam-achievements-{platform}-x64'
stage = out/name
if stage.exists(): shutil.rmtree(stage)
stage.mkdir(parents=True)
shutil.copytree(out/'csa-tracker',stage/'tracker')
shutil.copy2(out/'local.custom-achievements.star',stage)
shutil.copy2(root/'packaging/README.txt',stage/'README.txt')
for file in (['install-linux.sh'] if platform == 'linux' else ['Install.cmd','install-windows.ps1']): shutil.copy2(root/'packaging'/file,stage/file)
shutil.copytree(root/'licenses',stage/'licenses')
shutil.copytree(root/'docs',stage/'docs')
# Ship matching source for advanced launch helpers and third-party license terms.
for folder in ('tracker','scripts','resources'):
    shutil.copytree(root/folder,stage/'source'/folder,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(root/'resources',stage/'resources')
archive = Path(shutil.make_archive(str(out/name),'zip',out,name))
(out/(name+'.sha256')).write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print(archive)
