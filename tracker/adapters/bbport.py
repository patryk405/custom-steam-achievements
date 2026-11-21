"""Read BBPort v1 trophy events. No memory access or game writes.
Contract: deadinside28/bloodborne_pc @ 0fc2921c45f8ff3900f6bfa43a299e9a4f532af4,
src/runtime_trophy.c and launcher/trophy_list.py.
"""
import json
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

NP_ID = 'NPWR05818_00'
MAX_BYTES = 8 * 1024 * 1024


def bounded(path):
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('BBPort trophy file exceeds 8 MiB')
    return data


def read_metrics(user_dir, manifest):
    title = manifest['titleId']
    if not isinstance(title, str) or not title.startswith('CUSA'):
        raise ValueError('Configure the Bloodborne title ID first')
    known = set(manifest['trophies'])
    metrics = {}
    journal = user_dir / 'trophies.jsonl'
    found = False
    if journal.is_file():
        found = True
        raw = bounded(journal)
        # An unfinished final append is retried at the next tick.
        for line in raw.splitlines(keepends=True):
            if not line.endswith(b'\n'):
                continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict) or type(event.get('v')) is not int or event['v'] != 1 or event.get('title_id') != title:
                    continue
                number = event.get('trophy_id')
                if type(number) is not int or not 0 <= number <= 255:
                    continue
                stamp = event.get('unlocked_at')
                if not isinstance(stamp,str):
                    continue
                datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')
                key = str(number)
                if key in known:
                    metrics['trophy:' + key] = 1
            except (ValueError, TypeError, KeyError):
                continue
    # The exact Bloodborne communication ID only; never select another game's
    # directory by recency. This also supports older, pre-journal unlocks.
    unlocks = user_dir / 'trophy' / NP_ID / 'unlocked.txt'
    if unlocks.is_file():
        found = True
        for line in bounded(unlocks).decode('utf-8',errors='replace').splitlines():
            value=line.strip()
            if value.isascii() and value.isdigit() and len(value) <= 3:
                key=str(int(value))
                if key in known:
                    metrics['trophy:'+key]=1
    if not found:
        raise ValueError('Waiting for BBPort trophy data — start the configured game')
    return metrics


def load_definitions(user_dir):
    folder = user_dir / 'trophy' / NP_ID
    xml = next((folder/name for name in ('TROP_01.XML','TROP.XML') if (folder/name).is_file()), None)
    if xml is None:
        raise ValueError('No Bloodborne TROP_01.XML or TROP.XML. Let BBPort populate its trophy catalog first.')
    text = bounded(xml).decode('utf-8-sig')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('XML declarations with entities are not supported')
    start=text.find('<trophyconf');end=text.rfind('</trophyconf>')
    if start<0 or end<start:raise ValueError('Invalid trophy XML')
    root=ET.fromstring(text[start:end+len('</trophyconf>')])
    result=[];seen=set()
    for node in root.findall('trophy'):
        value=node.get('id','')
        if not value.isascii() or not value.isdigit():raise ValueError('Invalid trophy ID')
        number=int(value)
        if not 0<=number<=255 or number in seen:raise ValueError('Duplicate or invalid trophy ID')
        seen.add(number)
        name=(node.findtext('name') or '').strip();desc=(node.findtext('detail') or '').strip()
        if not name or len(name)>256 or len(desc)>2048:raise ValueError('Invalid trophy text')
        grade=node.get('ttype')
        if grade not in ('P','G','S','B'):raise ValueError('Unknown trophy grade')
        result.append({'id':f'bb_trophy_{number}','name':name,'description':desc,'target':1,
                       'icon':{'P':'crown','G':'star','S':'shield','B':'sword'}[grade]})
    if not result:raise ValueError('Empty trophy catalog')
    return result
