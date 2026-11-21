#!/usr/bin/env python3
"""Connect an installed game to its bundled read-only tracker and Steam shortcut."""
import argparse
import json
import re
import shutil
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FILES = {'bloodborne':'bbport','arceus':'arceus','odyssey':'odyssey','pokopia':'pokopia'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', choices=FILES)
    parser.add_argument('--path', type=Path, required=True, help='PLA main / Odyssey File1.bin save file; BBPort user directory; Pokopia G00/CMNDAT.BIN save file')
    parser.add_argument('--steam-appid', type=int, required=True)
    parser.add_argument('--title-id', help='Bloodborne CUSA title ID, required for BBPort')
    args = parser.parse_args()
    if not 0 < args.steam_appid <= 0xffffffff: parser.error('Invalid Steam shortcut ID')
    path = args.path.expanduser().resolve(strict=True)
    manifest_path = ROOT/'resources'/f'{FILES[args.game]}-adapter.json'
    m = json.loads(manifest_path.read_text())
    if args.game in ('arceus','odyssey','pokopia'):
        if not path.is_file() or any(x in path.name for x in '*?[]'): parser.error('Select one exact save file')
        m['root'],m['glob'] = str(path.parent),path.name
    else:
        if not path.is_dir(): parser.error('Select the game data directory')
        m['root'] = str(path)
    if args.game == 'bloodborne':
        if not args.title_id or not re.fullmatch(r'CUSA\d{5}',args.title_id): parser.error('Bloodborne requires --title-id CUSAxxxxx')
        m['titleId'] = args.title_id
    ids_path = ROOT/'resources/shortcut-ids.json'
    ids = json.loads(ids_path.read_text()); ids[args.game] = args.steam_appid
    backup = ROOT/'backups'/f'configure-{time.time_ns()}'
    backup.mkdir(parents=True)
    for file,content in ((manifest_path,m),(ids_path,ids)):
        shutil.copy2(file,backup/file.name)
        temp = file.with_suffix('.tmp');temp.write_text(json.dumps(content,ensure_ascii=False,indent=2)+'\n');temp.replace(file)
    print(f'Configured {args.game}; backup: {backup}')
    print('Rebuild the plugin, restart Steam, and restart custom-achievements-tracker.service.')
if __name__ == '__main__': main()
