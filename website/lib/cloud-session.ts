import {env} from 'cloudflare:workers';
import {headers} from 'next/headers';
import {hash} from './steam-auth';
export async function steamAccount(request?:Request){
 const cookie=(request?.headers||await headers()).get('cookie')||'';
 const raw=cookie.split(';').map(x=>x.trim()).find(x=>x.startsWith('__Host-csa_session='))?.split('=')[1];
 if(!raw||! /^[a-f0-9]{64}$/.test(raw)||!env.DB)return null;
 return env.DB.prepare("SELECT steam_id FROM steam_sessions WHERE token_hash=? AND kind='browser' AND expires_at>?").bind(await hash(raw),Math.floor(Date.now()/1000)).first<{steam_id:string}>();
}
