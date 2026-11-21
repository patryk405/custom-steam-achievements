#!/usr/bin/env python3
"""Connect a local Bloodborne BBPort trophy catalog; no game files are changed."""
import argparse,json,re,sys,shutil,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tracker'))
from adapters.bbport import load_definitions

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user-dir',type=Path,required=True,help='BBPort user directory containing trophy/ and trophies.jsonl')
    parser.add_argument('--title-id',required=True,help='Bloodborne TITLE_ID from param.sfo or its trophy events')
    parser.add_argument('--steam-appid',type=int,required=True,help='Unsigned Steam non-Steam shortcut app ID')
    args=parser.parse_args()
    if not re.fullmatch(r'CUSA\d{5}',args.title_id):parser.error('Expected a CUSA title ID')
    if not 0<args.steam_appid<=0xffffffff:parser.error('Invalid shortcut app ID')
    user=args.user_dir.expanduser().resolve(strict=True)
    definitions=load_definitions(user)
    manifest={'schema':1,'id':'bbport-trophies-v1','game':'bloodborne','kind':'bbport-trophies','root':str(user),
              'titleId':args.title_id,'trophies':[a['id'].removeprefix('bb_trophy_') for a in definitions],
              'rules':{a['id']:{'op':'any','flags':['trophy:'+a['id'].removeprefix('bb_trophy_')],
                               'note':'Detected when BBPort records the trophy unlock.'} for a in definitions}}
    paths=[ROOT/'resources'/n for n in ('catalog.json','bbport-adapter.json','shortcut-ids.json')]
    catalog=json.loads(paths[0].read_text());catalog['bloodborne']['achievements']=definitions
    ids=json.loads(paths[2].read_text());ids['bloodborne']=args.steam_appid
    backup=ROOT/'backups'/('bbport-'+str(time.time_ns()));backup.mkdir(parents=True)
    for path in paths:shutil.copy2(path,backup/path.name)
    for path,value in zip(paths,(catalog,manifest,ids)):
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');tmp.replace(path)
    print(f'Configured {len(definitions)} trophies. Backup: {backup}')
    print('Next: bun run build; restart Steam; systemctl --user restart custom-achievements-tracker.service')
if __name__=='__main__':main()
