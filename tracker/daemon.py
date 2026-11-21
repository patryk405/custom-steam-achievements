#!/usr/bin/env python3
"""Local adapter host. Polls stable files, updates a private atomic progress file."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time
import threading
from audio import run_audio
from cloud import Cloud
from engine import apply_rules
from adapters import botw, snapshot, bbport, pokopia, arceus, odyssey
from adapters.botw_live import LiveReader
from adapters.longshot_live import LongshotReader
from adapters.pokopia_live import LiveReader as PokopiaLiveReader

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))/'custom-achievements'

def read_json(path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default

def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w') as file:
        json.dump(data, file)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temp, path)

def expand_root(value):
    xdg = os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share'))
    return Path(value.replace('${XDG_DATA_HOME}', xdg)).expanduser()

def fingerprint(path):
    files = [path]
    if path.name == 'game_data.sav' and path.with_name('caption.sav').is_file():
        files.append(path.with_name('caption.sav'))
    return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files)

class Host:
    def __init__(self, data=DATA, manifests=None, catalog=None):
        self.data = data
        self.manifests = manifests or [json.loads((ROOT/'resources'/name).read_text()) for name in ('botw-adapter.json', 'oot-adapter.json', 'bbport-adapter.json', 'arceus-adapter.json', 'odyssey-adapter.json', 'pokopia-adapter.json')]
        self.catalog = catalog or json.loads((ROOT/'resources/catalog.json').read_text())
        self.live = LiveReader()
        self.longshot = LongshotReader()
        self.pokopia_live = PokopiaLiveReader()
        self.seen = {}
        self.done = {}
        self.state = read_json(data/'state.json', {'schema': 1, 'games': {}, 'status': {}})
        if self.state.get('schema') != 1:
            raise ValueError('Unsupported state schema; refusing to overwrite')

    def tick(self):
        enabled = read_json(self.data/'preferences.json', {}).get('autoEnabled', True)
        for manifest in self.manifests:
            game, adapter_id = manifest['game'], manifest['id']
            status = {'adapter': adapter_id, 'supported': len(manifest['rules']), 'checkedAt': int(time.time())}
            try:
                if not enabled:
                    status['message'] = 'Automatic tracking paused'
                else:
                    if manifest.get('live') == 'recompia-memory-v1':
                        try:
                            metrics = self.pokopia_live.read_metrics(expand_root(manifest['socket']))
                        except (OSError, ValueError, TypeError, KeyError) as error:
                            if manifest.get('liveOnly', True):
                                status.update(message='Waiting for Pokopia live tracking — '+str(error), mode='live-waiting')
                                self.state['status'][game] = status
                                continue
                            status['liveError'] = str(error)
                        else:
                            definitions = {a['id']: a for a in self.catalog[game]['achievements']}
                            self.state['games'][game] = apply_rules(self.state['games'].get(game, {}), {**manifest, 'id':'pokopia-live-v1'}, metrics, definitions)
                            status.update(message='Live tracking — experimental Pokopia memory reader, no save required', mode='live', metricsRead=len(metrics), lastReadAt=int(time.time()))
                            self.state['status'][game] = status
                            continue
                    if manifest['kind'] in ('arceus-save','odyssey-save','pokopia-save') and not manifest.get('root'):
                        status['message'] = 'Not configured — select the game data path with configure-game.py'
                        self.state['status'][game] = status
                        continue
                    if manifest['kind'] == 'bbport-trophies':
                        if not manifest.get('root') or not manifest.get('rules'):
                            status['message'] = 'BBPort not configured — select its user directory and title ID'
                            self.state['status'][game] = status
                            continue
                        metrics = bbport.read_metrics(expand_root(manifest['root']), manifest)
                        definitions = {a['id']: a for a in self.catalog[game]['achievements']}
                        self.state['games'][game] = apply_rules(self.state['games'].get(game, {}), manifest, metrics, definitions)
                        status.update(message='Watching BBPort trophy unlocks — no manual save required', mode='events', metricsRead=len(metrics), lastReadAt=int(time.time()))
                        self.state['status'][game] = status
                        continue
                    if manifest['kind'] == 'longshot-live':
                        metrics = self.longshot.read_metrics(expand_root(manifest['socket']), manifest.get('watch'))
                        definitions = {a['id']: a for a in self.catalog[game]['achievements']}
                        self.state['games'][game] = apply_rules(self.state['games'].get(game, {}), manifest, metrics, definitions)
                        status.update(message='Live tracking — no save required', mode='live', metricsRead=len(metrics), lastReadAt=int(time.time()))
                        self.state['status'][game] = status
                        continue
                    if manifest.get('live') == 'savagewind-1.9.0':
                        try:
                            metrics = self.live.read_metrics(manifest)
                        except (OSError, ValueError, KeyError, TypeError) as error:
                            status['liveError'] = str(error)
                        else:
                            definitions = {a['id']: a for a in self.catalog[game]['achievements']}
                            live_manifest = {**manifest, 'id': 'botw-live-v1'}
                            self.state['games'][game] = apply_rules(self.state['games'].get(game, {}), live_manifest, metrics, definitions)
                            status.update(message='Live tracking — no save required', mode='live', metricsRead=len(metrics), lastReadAt=int(time.time()))
                            self.state['status'][game] = status
                            continue
                    root = expand_root(manifest['root'])
                    candidates = list(root.glob(manifest['glob'])) if root.is_dir() else []
                    # Follow the newest active slot only; never scan backups or merge old slots.
                    path = max(candidates, key=lambda p: p.stat().st_mtime_ns) if candidates else None
                    if path is None:
                        status['message'] = 'Waiting for the first save or autosave'
                    else:
                        sig = fingerprint(path)
                        if self.seen.get(adapter_id) != sig:
                            self.seen[adapter_id] = sig
                            status['message'] = 'Waiting for the save to finish writing'
                        elif self.done.get(adapter_id) != sig:
                            reader = {'botw-save': botw.read_metrics, 'json-snapshot': snapshot.read_metrics, 'arceus-save': arceus.read_metrics, 'odyssey-save': odyssey.read_metrics, 'pokopia-save': pokopia.read_metrics}[manifest['kind']]
                            metrics = reader(path, manifest)
                            if fingerprint(path) != sig:
                                raise ValueError('Save changed during reading; retrying')
                            definitions = {a['id']: a for a in self.catalog[game]['achievements']}
                            old = self.state['games'].get(game, {})
                            self.state['games'][game] = apply_rules(old, manifest, metrics, definitions)
                            status['message'] = 'Watching saves — updates after each save or autosave'
                            status['lastReadAt'] = int(time.time())
                            status['metricsRead'] = len(metrics)
                            self.done[adapter_id] = sig
                        else:
                            status.update({k:v for k,v in self.state['status'].get(game, {}).items() if k in ('lastReadAt','metricsRead')})
                            status['message'] = 'Watching saves — updates after each save or autosave'
            except Exception as error:
                status['message'] = 'Not tracking: ' + str(error)
                status['error'] = True
            self.state['status'][game] = status
        self.state['updatedAt'] = int(time.time())
        atomic_json(self.data/'state.json', self.state)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    os.umask(0o077)
    with (DATA/'tracker.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifests = [json.loads((ROOT/'resources'/name).read_text()) for name in ('botw-adapter.json', 'oot-adapter.json', 'bbport-adapter.json', 'arceus-adapter.json', 'odyssey-adapter.json', 'pokopia-adapter.json')]
        custom = DATA/'adapters'
        if custom.is_dir():
            manifests.extend(json.loads(p.read_text()) for p in sorted(custom.glob('*.json')))
        manifests = list({m['id']:m for m in manifests}.values())
        host = Host(manifests=manifests)
        threading.Thread(target=run_audio, args=(DATA,), daemon=True).start()
        cloud = Cloud(DATA,host.catalog)
        threading.Thread(target=cloud.run,daemon=True).start()
        while True:
            if cloud.prepare(host):
                host.tick()
                cloud.finish(host)
            if args.once:
                return
            time.sleep(2)
if __name__ == '__main__':
    main()
