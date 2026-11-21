"""Universal input contract for game mods/exporters: versioned JSON scalar metrics."""
import json

def read_metrics(path, manifest):
    if path.stat().st_size > 1_000_000:
        raise ValueError('Snapshot too large')
    data = json.loads(path.read_text())
    if data.get('schema') != 1 or data.get('game') != manifest['game'] or not isinstance(data.get('metrics'), dict):
        raise ValueError('Wrong snapshot schema or game')
    return data['metrics']
