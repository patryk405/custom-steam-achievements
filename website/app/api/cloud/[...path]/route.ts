import {env} from 'cloudflare:workers';
import {token,hash,verifySteam,STEAM,NS} from '@/lib/steam-auth';
import catalog from '@/lib/cloud-catalog.json';
export const dynamic='force-dynamic';
const now=()=>Math.floor(Date.now()/1000);
const cookie=(r:Request,name:string)=>r.headers.get('cookie')?.split(';').map(x=>x.trim()).find(x=>x.startsWith(name+'='))?.slice(name.length+1)||'';
const json=(data:unknown,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store','Referrer-Policy':'no-referrer'}});
function redirect(url:string, cookies:string[]=[]){const h=new Headers({'Location':url,'Cache-Control':'no-store','Referrer-Policy':'no-referrer'});cookies.forEach(c=>h.append('Set-Cookie',c));return new Response(null,{status:303,headers:h});}
const setCookie=(name:string,value:string,age:number)=>`${name}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${age}`;
async function body(r:Request){let text='',size=0;const decoder=new TextDecoder();const reader=r.body?.getReader();if(!reader)throw Error('Missing request');for(;;){const x=await reader.read();if(x.done)break;size+=x.value.byteLength;if(size>262144){await reader.cancel();throw Error('Request too large');}text+=decoder.decode(x.value,{stream:true});}return JSON.parse(text+decoder.decode());}
async function session(r:Request,device=false){const raw=device?r.headers.get('authorization')?.replace(/^Bearer /,''):cookie(r,'__Host-csa_session');if(!raw||! /^[a-f0-9]{64}$/.test(raw))return null;return env.DB!.prepare('SELECT * FROM steam_sessions WHERE token_hash=? AND kind=? AND expires_at>?').bind(await hash(raw),device?'device':'browser',now()).first<{token_hash:string,steam_id:string,name:string}>();}
function origin(r:Request){if(r.headers.get('origin')!==new URL(r.url).origin)throw Error('Invalid request origin');}
async function handle(r:Request){
 const url=new URL(r.url),path=url.pathname.replace('/api/cloud/',''),db=env.DB;
 if(!db)return json({error:"Cloud database is unavailable"},503);
 if(['login','device/start','callback'].includes(path)){
  const bucket=Math.floor(now()/60),key=await hash((r.headers.get('cf-connecting-ip')||'local')+':'+bucket);
  await db.prepare('INSERT INTO cloud_rates(key,count,expires_at) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1').bind(key,now()+120).run();
  const limit=await db.prepare('SELECT count FROM cloud_rates WHERE key=?').bind(key).first<{count:number}>();
  if((limit?.count||0)>20)return json({error:'Too many requests. Retry in a minute.'},429);
  await db.prepare('DELETE FROM cloud_rates WHERE expires_at<?').bind(now()).run();
 }
 if(path==='login'&&r.method==='GET'){
  const state=token(),device=url.searchParams.get('device')||null;if(device&&!/^[a-f0-9]{64}$/.test(device))return json({error:'Invalid device'},400);
  await db.prepare('INSERT INTO steam_flows(state_hash,device,expires_at) VALUES(?,?,?)').bind(await hash(state),device,now()+600).run();
  const target=new URL(STEAM);target.search=new URLSearchParams({'openid.ns':NS,'openid.mode':'checkid_setup','openid.return_to':url.origin+'/api/cloud/callback?state='+state,'openid.realm':url.origin+'/','openid.identity':NS+'/identifier_select','openid.claimed_id':NS+'/identifier_select'}).toString();
  return redirect(target.href,[setCookie('__Host-csa_flow',state,600)]);
 }
 if(path==='callback'&&r.method==='GET'){
  const state=url.searchParams.get('state')||'';if(!/^[a-f0-9]{64}$/.test(state)||cookie(r,'__Host-csa_flow')!==state)throw Error('Sign-in expired. Please start again.');
  const flow=await db.prepare('SELECT * FROM steam_flows WHERE state_hash=? AND expires_at>?').bind(await hash(state),now()).first<{device:string|null}>();if(!flow)throw Error('Sign-in expired');
  const {steamId,nonce}=await verifySteam(url.searchParams,url.origin+'/api/cloud/callback?state='+state);
  const consumed=await db.prepare('DELETE FROM steam_flows WHERE state_hash=?').bind(await hash(state)).run();if(!consumed.meta.changes)throw Error('Sign-in already used');
  await db.prepare('INSERT INTO steam_nonces(nonce,expires_at) VALUES(?,?)').bind(nonce,now()+600).run();
  const secret=token();await db.prepare('INSERT INTO steam_sessions VALUES(?,?,?,?,?,?)').bind(await hash(secret),steamId,'browser','Website',now(),now()+2592000).run();
  await db.batch([db.prepare('DELETE FROM steam_flows WHERE expires_at<?').bind(now()),db.prepare('DELETE FROM steam_nonces WHERE expires_at<?').bind(now()),db.prepare('DELETE FROM steam_devices WHERE expires_at<?').bind(now()),db.prepare('DELETE FROM steam_sessions WHERE expires_at<?').bind(now())]);
  return redirect('/account'+(flow.device?'?device='+flow.device:''),[setCookie('__Host-csa_session',secret,2592000),setCookie('__Host-csa_flow','',0)]);
 }
 if(path==='me'&&r.method==='GET'){
  const s=await session(r);if(!s)return json({signedIn:false});
  const progress=await db.prepare('SELECT game,achievement,current,unlocked_at,updated_at FROM cloud_progress WHERE steam_id=? ORDER BY game,achievement').bind(s.steam_id).all();
  const devices=await db.prepare("SELECT token_hash AS id,name,created_at,expires_at FROM steam_sessions WHERE steam_id=? AND kind='device' AND expires_at>?").bind(s.steam_id,now()).all();
  return json({signedIn:true,steamId:s.steam_id,progress:progress.results,devices:devices.results});
 }
 if(path==='logout'&&r.method==='POST'){origin(r);const s=await session(r);if(s)await db.prepare('DELETE FROM steam_sessions WHERE token_hash=?').bind(s.token_hash).run();return redirect('/account',[setCookie('__Host-csa_session','',0)]);}
 if(path==='device/start'&&r.method==='POST'){
  const data=await body(r);if(!/^7656119\d{10}$/.test(data.steamId)||typeof data.name!=='string'||data.name.length<1||data.name.length>80)throw Error('Invalid device');
  // Bound anonymous pairing requests by identity and lifetime. Only Steam verification authorizes them.
  const count=await db.prepare('SELECT count(*) AS n FROM steam_devices WHERE expected_steam_id=? AND expires_at>?').bind(data.steamId,now()).first<{n:number}>();if((count?.n||0)>=5)return json({error:'Too many pairing attempts. Try again in ten minutes.'},429);
  const id=token(),secret=token();await db.prepare('INSERT INTO steam_devices VALUES(?,?,?,?,NULL,?)').bind(id,await hash(secret),data.steamId,data.name,now()+600).run();
  return json({device:id,token:secret,verificationUrl:url.origin+'/account?device='+id,expiresAt:now()+600});
 }
 if(path==='device/status'&&r.method==='POST'){
  const data=await body(r);if(!/^[a-f0-9]{64}$/.test(data.token))throw Error('Invalid token');
  const s=await db.prepare("SELECT steam_id FROM steam_sessions WHERE token_hash=? AND kind='device' AND expires_at>?").bind(await hash(data.token),now()).first();if(s)return json({status:'approved',steamId:s.steam_id});
  const pending=await db.prepare('SELECT id FROM steam_devices WHERE token_hash=? AND expires_at>?').bind(await hash(data.token),now()).first();return json({status:pending?'pending':'expired'});
 }
 if(path==='device/info'&&r.method==='GET'){
  const s=await session(r);if(!s)return json({error:'Sign in with Steam'},401);
  const d=await db.prepare('SELECT id,name,expected_steam_id FROM steam_devices WHERE id=? AND expires_at>?').bind(url.searchParams.get('id'),now()).first();return json({device:d});
 }
 if(path==='device/approve'&&r.method==='POST'){
  origin(r);const s=await session(r);if(!s)return json({error:'Sign in with Steam'},401);const data=await body(r);
  const result=await db.batch([
   db.prepare("INSERT INTO steam_sessions SELECT token_hash,expected_steam_id,'device',name,?,? FROM steam_devices WHERE id=? AND expected_steam_id=? AND expires_at>?").bind(now(),now()+15552000,data.device,s.steam_id,now()),
   db.prepare('DELETE FROM steam_devices WHERE id=? AND expected_steam_id=? AND expires_at>?').bind(data.device,s.steam_id,now())
  ]);
  if(!result[0].meta.changes)return json({error:'Device expired or belongs to a different Steam account'},403);
  return json({ok:true});
 }
 if(path==='device/revoke'&&r.method==='POST'){origin(r);const s=await session(r);if(!s)return json({error:'Sign in'},401);const data=await body(r);await db.prepare("DELETE FROM steam_sessions WHERE token_hash=? AND steam_id=? AND kind='device'").bind(data.id,s.steam_id).run();return json({ok:true});}
 if(path==='sync'&&r.method==='POST'){
  const s=await session(r,true);if(!s)return json({error:'Device is not authorized. Reconnect Steam.'},401);
  const data=await body(r);if(data.steamId!==s.steam_id)return json({error:'Steam account mismatch'},403);
  if(!Array.isArray(data.progress)||data.progress.length>2000)throw Error('Invalid progress');
  const validated=data.progress.map((p:any)=>{
   const game=(catalog as any)[p.game],def=game?.achievements.find((a:any)=>a.id===p.achievement);
   if(!def||!Number.isInteger(p.current)||p.current<0||p.current>def.target)throw Error('Unknown achievement or invalid progress');
   if(p.unlockedAt!=null&&(!Number.isInteger(p.unlockedAt)||p.unlockedAt<946684800||p.unlockedAt>now()+300))throw Error('Invalid unlock date');
   return {...p,unlockedAt:p.current===def.target?(p.unlockedAt||now()):null};
  });
  // Account is always taken from the verified device session, never from payload ownership fields.
  for(let i=0;i<validated.length;i+=80)await db.batch(validated.slice(i,i+80).map((p:any)=>db.prepare(`INSERT INTO cloud_progress(key,steam_id,game,achievement,current,unlocked_at,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET current=MAX(current,excluded.current),unlocked_at=CASE WHEN unlocked_at IS NULL THEN excluded.unlocked_at WHEN excluded.unlocked_at IS NULL THEN unlocked_at ELSE MIN(unlocked_at,excluded.unlocked_at) END,updated_at=excluded.updated_at`).bind(s.steam_id+':'+p.game+':'+p.achievement,s.steam_id,p.game,p.achievement,p.current,p.unlockedAt,now())));
  const rows=await db.prepare('SELECT game,achievement,current,unlocked_at,updated_at FROM cloud_progress WHERE steam_id=?').bind(s.steam_id).all();return json({steamId:s.steam_id,progress:rows.results,syncedAt:now()});
 }
 return json({error:'Not found'},404);
}
export async function GET(r:Request){try{return await handle(r);}catch(e){return json({error:e instanceof Error?e.message:'Request failed'},400);}}
export const POST=GET;
