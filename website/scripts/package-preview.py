from pathlib import Path
import zipfile,json,io,wave,math,struct,base64,hashlib
root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parents[1]/'lib/downloads/custom-steam-achievements-0.4.1-source.zip'
files={}
for folder in ['frontend','backend','tracker','tests','docs','examples','licenses']:
 for p in (root/folder).rglob('*'):
  if p.is_file() and p.suffix in ['.ts','.tsx','.lua','.py','.json','.md','.txt'] and '__pycache__' not in p.parts:
   files[p.relative_to(root).as_posix()]=p.read_text()
for name in ['package.json','bun.lock','tsconfig.json','millennium.toml','resources/catalog.json','resources/botw-adapter.json','resources/botw-reddit-original.json','resources/favicon.svg','resources/oot-adapter.json','resources/oot-signals.json','resources/bbport-adapter.json','resources/shortcut-ids.json','scripts/configure-bbport.py','scripts/configure-game.py','scripts/configure-pokopia-live.py','scripts/launch-pokopia-live.py','resources/arceus-adapter.json','resources/odyssey-adapter.json','resources/pokopia-adapter.json','resources/pokopia-layout.json']:
 files[name]=(root/name).read_text()
for name in files:
 files[name]=files[name].replace('2958877903','0').replace('4105205847','0')
files['resources/shortcut-ids.json']=json.dumps({k:0 for k in json.loads(files['resources/shortcut-ids.json'])},indent=2)
# Original neutral chime for this distribution, not the locally extracted Steam sample.
buf=io.BytesIO()
with wave.open(buf,'wb') as w:
 w.setnchannels(1);w.setsampwidth(2);w.setframerate(22050)
 samples=[]
 for i in range(13230):
  t=i/22050;v=sum(math.sin(2*math.pi*f*t) for f in [523.25,659.25,783.99])/3
  envelope=min(1,t/.02)*math.exp(-6*t)*min(1,(.6-t)/.03)
  samples.append(struct.pack('<h',int(6500*v*envelope)))
 w.writeframes(b''.join(samples))
files['resources/achievement-sound.json']=json.dumps({'url':'data:audio/wav;base64,'+base64.b64encode(buf.getvalue()).decode()})
files['millennium.toml']=files['millennium.toml'].replace('version = "0.1.0"','version = "0.4.1"')
files['README.md']='''# Custom Steam Achievements — developer preview 0.4.1

This is a source archive, not a one-click installer. Linux desktop Steam and Millennium are required. Big Picture, Decky, and Windows are not supported by this preview.

## Setup
1. Install Millennium using https://steambrew.app/ and confirm it works in desktop Steam.
2. Extract this archive. Install Bun and Python 3 if needed.
3. Add your game to Steam as a non-Steam shortcut. Set its numeric shortcut ID in `resources/shortcut-ids.json`: all IDs are intentionally 0 in this source distribution. They must match your own installation for notifications.
4. Check `resources/botw-adapter.json` and `docs/ADAPTERS.md` for the supported save locations and adapter setup. Live tracking is version-pinned to Savage Wind 0.6.0-alpha.6 / BOTW 1.9.0; start your game launcher with SAVAGEWIND_CONTROL=27777 in its environment.
5. From the extracted directory, run `bun install`, then `bun run build`. The Millennium Starlight build uses the local Millennium plugin output location (`output_path = "auto"`). Fully exit and reopen Steam and enable Custom Achievements in Millennium.
6. Start the separate tracker in a terminal with `python tracker/daemon.py`. Keep it running while playing. Stop it with Ctrl+C. This archive does not install a background service.
7. Open the achievements panel and use Test notification. Live tracking should report its status while the supported game is running. Check your shortcut ID mapping if a notification is missing.

## Contents and limits
- Native-style local achievement panels, BOTW rules and a Python tracker.
- Ocarina: 66 objectives for Longshot v3.0.0 (source bd6a0cdd). Set HOS_CONTROL to ${XDG_DATA_HOME:-$HOME/.local/share}/custom-achievements/longshot.sock in the game launcher environment. See docs/LONGSHOT.md and docs/LONGSHOT-ACHIEVEMENTS.md. Only starter goals have been verified in real gameplay; the expanded set needs playthrough testing.
- Bloodborne: full 40-trophy BBPort event pack. Arceus: 38 save-based objectives. Odyssey: 35 save-based objectives. Pokopia: 11 objectives with experimental Recompia 2.0.1 live memory tracking, no mod required. See docs/POKOPIA-LIVE.md. First Friend and First Habitat were verified in gameplay. Configure with scripts/configure-game.py; see docs/NEW-GAMES.md. These four adapters have fixture tests but await real-game verification. Third-party source/license notices are included under docs/THIRD-PARTY.md and licenses/.
- This distribution replaces machine-specific shortcut IDs with 0 and uses an original neutral chime instead of the local Steam audio sample.
- Game files, ROMs, keys, save data, user progress, screenshots, credentials and node_modules are not included.
- Steam's private interface can change. This sanitized source archive has not been validated end-to-end on a clean machine. It is intended for developers and manual setup.
- Optional Steam-account cloud synchronization is available in plugin settings; see docs/CLOUD-SYNC.md. It requires a reachable public deployment and one-time pairing per device. This does not create official Steam profile achievements.
- Downloadable website pack envelopes do not yet have a one-click plugin importer.

## Source checks
`bun test`, `bun run typecheck`, `lua tests/notifications.lua`, and `python -m unittest discover -s tests -v` are the project's development checks. The distribution's zero shortcut IDs must be configured before gameplay testing.
'''
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for name,content in sorted(files.items()):z.writestr('custom-steam-achievements/'+name,content)
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 assert not any(str(Path.home()) in z.read(n).decode(errors='ignore') for n in z.namelist())
 assert not any(n.endswith(('prod.keys','state.json','preferences.json')) for n in z.namelist())
manifest={'version':'0.4.1','kind':'Developer source preview','filename':out.name,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'fileCount':len(files)}
out.with_name('release.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
