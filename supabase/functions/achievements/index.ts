import {token,hash,verifySteam,STEAM,NS} from './steam-auth.ts';
import catalog from './cloud-catalog.json' with {type:'json'};
import {packSchema,builtinPacks,builtinPack,summary} from './packs.ts';
const FRONT='https://patryk405.github.io/custom-steam-achievements/';
const ORIGIN=new URL(FRONT).origin;
const API=Deno.env.get('SUPABASE_URL')+'/rest/v1/';
const KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const CALLBACK=Deno.env.get('SUPABASE_URL')+'/functions/v1/achievements/cloud/callback';
const now=()=>Math.floor(Date.now()/1000),hex=(s:unknown)=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
class Problem extends Error{constructor(message:string,public status=400){super(message);}}
async function db(path:string,method='GET',data?:unknown){const res=await fetch(API+path,{method,headers:{apikey:KEY,Authorization:'Bearer '+KEY,'Content-Type':'application/json',Prefer:'return=representation'},body:data===undefined?undefined:JSON.stringify(data)});if(!res.ok){console.error('Database request failed',path.split('?')[0],res.status);throw new Problem('Service temporarily unavailable',503);}const t=await res.text();return t?JSON.parse(t):null;}
const rpc=(name:string,data:unknown)=>db('rpc/csa_'+name,'POST',data);
const json=(v:unknown,status=200)=>Response.json(v,{status});
const redirect=(url:string)=>new Response(null,{status:303,headers:{Location:url}});
async function body(r:Request,max=262144){let size=0,text='';const reader=r.body?.getReader(),decoder=new TextDecoder();if(!reader)throw new Problem('Missing request');for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>max){await reader.cancel();throw new Problem('File too large',413);}text+=decoder.decode(value,{stream:true});}try{return JSON.parse(text+decoder.decode());}catch{throw new Problem('Invalid JSON');}}
async function session(r:Request,kind='browser'){const raw=r.headers.get('authorization')?.replace(/^Bearer /,'');if(!hex(raw))throw new Problem('Sign in through Steam',401);const [s]=await db(`csa_sessions?token_hash=eq.${await hash(raw!)}&kind=eq.${kind}&expires_at=gt.${now()}`);if(!s)throw new Problem('Session expired. Sign in again.',401);return s;}
function browser(r:Request){if(r.headers.get('origin')!==ORIGIN)throw new Problem('Invalid request origin',403);}
async function profile(id:string){
 const [cached]=await db('csa_profiles?steam_id=eq.'+id);if(cached&&now()-cached.updated_at<3600)return cached;
 try{const r=await fetch('https://steamcommunity.com/profiles/'+id+'/?xml=1',{redirect:'manual',signal:AbortSignal.timeout(5000)});if(!r.ok)throw Error();const t=await r.text();const field=(n:string)=>{const value=t.match(new RegExp('<'+n+'>([\\s\\S]*?)</'+n+'>'))?.[1]||'';return value.replace(/^<!\[CDATA\[|\]\]>$/g,'').trim();};if(field('steamID64')!==id)throw Error();const avatar=field('avatarMedium');if(!/^https:\/\/(avatars\.(?:steamstatic\.com|akamai\.steamstatic\.com|cloudflare\.steamstatic\.com|fastly\.steamstatic\.com)|steamcdn-a\.akamaihd\.net)\//.test(avatar))throw Error();const p={steam_id:id,name:field('steamID').slice(0,100)||id,avatar,updated_at:now()};await db('csa_profiles?steam_id=eq.'+id,'DELETE');await db('csa_profiles','POST',p);return p;}catch{return cached||{name:id,avatar:''};}
}
async function handle(r:Request){
 const url=new URL(r.url),path=url.pathname.split('/achievements/')[1]||'';
 const o=r.headers.get('origin');if(o&&o!==ORIGIN)throw new Problem('Invalid request origin',403);
 if(r.method==='OPTIONS')return new Response(null,{status:204});
 if(['cloud/login/start','cloud/callback','cloud/exchange','cloud/device/start'].includes(path)){
  const ip=r.headers.get('x-forwarded-for')?.split(',')[0]||'unknown';const n=await rpc('rate',{k:await hash(ip+':'+Math.floor(now()/60)),ts:now()});if(n>30)throw new Problem('Too many requests. Try again in a minute.',429);
 }
 if(path==='health'&&r.method==='GET')return json({ok:true});
 if(path==='cloud/login/start'&&r.method==='POST'){
  browser(r);const x=await body(r);if(!hex(x.state)||!hex(x.challenge))throw new Problem('Invalid sign-in');
  await db('csa_flows','POST',{state_hash:await hash(x.state),challenge:x.challenge,expires_at:now()+600});
  const target=new URL(STEAM);target.search=new URLSearchParams({'openid.ns':NS,'openid.mode':'checkid_setup','openid.return_to':CALLBACK+'?state='+x.state,'openid.realm':new URL(CALLBACK).origin+'/','openid.identity':NS+'/identifier_select','openid.claimed_id':NS+'/identifier_select'}).toString();return json({url:target.href});
 }
 if(path==='cloud/callback'&&r.method==='GET'){
  const state=url.searchParams.get('state');if(!hex(state))throw new Problem('Invalid sign-in');
  const [flow]=await db(`csa_flows?state_hash=eq.${await hash(state!)}&expires_at=gt.${now()}&steam_id=is.null`);if(!flow)throw new Problem('Sign-in expired. Return to the website and retry.');
  const {steamId,nonce}=await verifySteam(url.searchParams,CALLBACK+'?state='+state);
  await db('csa_nonces','POST',{nonce,expires_at:now()+600});
  const updated=await db(`csa_flows?state_hash=eq.${await hash(state!)}&steam_id=is.null`,'PATCH',{steam_id:steamId});if(!updated.length)throw new Problem('Sign-in already used');
  return redirect(FRONT+'?auth='+state);
 }
 if(path==='cloud/exchange'&&r.method==='POST'){
  browser(r);const x=await body(r);if(!hex(x.state)||!hex(x.verifier))throw new Problem('Invalid sign-in');
  const secret=token();const id=await rpc('exchange',{s:await hash(x.state),c:await hash(x.verifier),secret_hash:await hash(secret),ts:now()});return json({token:secret,steamId:id});
 }
 if(path==='cloud/me'&&r.method==='GET'){
  let s;try{s=await session(r);}catch(e){if(e instanceof Problem&&e.status===401)return json({signedIn:false});throw e;}
  const [progress,devices,p]=await Promise.all([db('csa_progress?select=game,achievement,current,unlocked_at,updated_at&steam_id=eq.'+s.steam_id),db(`csa_sessions?select=id:token_hash,name,created_at,expires_at&steam_id=eq.${s.steam_id}&kind=eq.device&expires_at=gt.${now()}`),profile(s.steam_id)]);
  return json({signedIn:true,steamId:s.steam_id,name:p.name,avatar:p.avatar,progress,devices});
 }
 if(path==='cloud/logout'&&r.method==='POST'){browser(r);const s=await session(r);await db('csa_sessions?token_hash=eq.'+s.token_hash,'DELETE');return json({ok:true});}
 if(path==='cloud/device/start'&&r.method==='POST'){
  const x=await body(r);if(!/^7656119\d{10}$/.test(x.steamId)||typeof x.name!=='string'||!x.name.length||x.name.length>80)throw new Problem('Invalid device');
  const pending=await db(`csa_devices?select=id&expected_steam_id=eq.${x.steamId}&expires_at=gt.${now()}`);if(pending.length>=5)throw new Problem('Too many pairing attempts',429);
  const id=token(),secret=token();await db('csa_devices','POST',{id,token_hash:await hash(secret),expected_steam_id:x.steamId,name:x.name,expires_at:now()+600});return json({device:id,token:secret,verificationUrl:FRONT+'?view=account&device='+id,expiresAt:now()+600});
 }
 if(path==='cloud/device/status'&&r.method==='POST'){
  const x=await body(r);if(!hex(x.token))throw new Problem('Invalid token');const h=await hash(x.token);
  const [s]=await db(`csa_sessions?token_hash=eq.${h}&kind=eq.device&expires_at=gt.${now()}`);if(s)return json({status:'approved',steamId:s.steam_id});const [p]=await db(`csa_devices?token_hash=eq.${h}&expires_at=gt.${now()}`);return json({status:p?'pending':'expired'});
 }
 if(path==='cloud/device/info'&&r.method==='GET'){const s=await session(r);const id=url.searchParams.get('id');if(!hex(id))throw new Problem('Invalid device');const [d]=await db(`csa_devices?select=id,name,expected_steam_id&id=eq.${id}&expected_steam_id=eq.${s.steam_id}&expires_at=gt.${now()}`);return json({device:d||null});}
 if(path==='cloud/device/approve'&&r.method==='POST'){browser(r);const s=await session(r),x=await body(r);if(!hex(x.device))throw new Problem('Invalid device');if(!await rpc('approve',{d:x.device,account:s.steam_id,ts:now()}))throw new Problem('Device expired or belongs to another account',403);return json({ok:true});}
 if(path==='cloud/device/revoke'&&r.method==='POST'){browser(r);const s=await session(r),x=await body(r);if(!hex(x.id))throw new Problem('Invalid device');await db(`csa_sessions?token_hash=eq.${x.id}&steam_id=eq.${s.steam_id}&kind=eq.device`,'DELETE');return json({ok:true});}
 if(path==='cloud/sync'&&r.method==='POST'){
  const s=await session(r,'device'),x=await body(r);if(x.steamId!==s.steam_id)throw new Problem('Account mismatch',403);if(!Array.isArray(x.progress)||x.progress.length>2000)throw new Problem('Invalid progress');const seen=new Set();
  const rows=x.progress.map((p:any)=>{const def=(catalog as any)[p.game]?.achievements.find((a:any)=>a.id===p.achievement);if(!def||!Number.isInteger(p.current)||p.current<0||p.current>def.target)throw new Problem('Invalid achievement');const key=p.game+':'+p.achievement;if(seen.has(key))throw new Problem('Duplicate achievement');seen.add(key);if(p.unlockedAt!=null&&(!Number.isInteger(p.unlockedAt)||p.unlockedAt<946684800||p.unlockedAt>now()+300))throw new Problem('Invalid date');return {game:p.game,achievement:p.achievement,current:p.current,unlocked_at:p.current===def.target?(p.unlockedAt||now()):null};});
  await rpc('sync',{account:s.steam_id,items:rows,ts:now()});return json({steamId:s.steam_id,progress:await db('csa_progress?select=game,achievement,current,unlocked_at,updated_at&steam_id=eq.'+s.steam_id),syncedAt:now()});
 }
 if(path==='packs'&&r.method==='GET')return json(await db('csa_packs?select=id,title,author,description,game,version,count,createdAt:created_at,downloads&order=created_at.desc&limit=100'));
 if(path==='packs'&&r.method==='POST'){browser(r);const s=await session(r),x=await body(r,131072);const v=packSchema.safeParse(x);if(!v.success)throw new Problem(v.error.issues.slice(0,3).map(x=>x.message).join(' '));const id=crypto.randomUUID();if(!await rpc('upload',{account:'steam:'+s.steam_id,pack:v.data,ts:now(),pack_id:id}))throw new Problem('Creator limit: 20 packs',429);return json({id},201);}
 if(path==='template'&&r.method==='GET'){const a=builtinPack.achievements.find(a=>a.id==='reddit_korok_first')!;const res=json({...builtinPack,id:'my-first-pack',title:'My first achievement pack',author:'Your creator name',description:'A small starter pack: find your first Korok seed.',achievements:[a],rules:{[a.id]:builtinPack.rules[a.id]}});res.headers.set('Content-Disposition','attachment; filename="achievement-pack-template.json"');return res;}
 if(path.startsWith('packs/')&&r.method==='GET'){const id=decodeURIComponent(path.slice(6));if(!/^[\w-]{1,80}$/.test(id))throw new Problem('Invalid pack');let pack=builtinPacks.find(p=>p.id===id);if(!pack){const [row]=await db('csa_packs?select=payload&id=eq.'+id);pack=row?.payload;}if(!pack)throw new Problem('Pack not found',404);const res=json(pack);if(url.searchParams.has('download'))res.headers.set('Content-Disposition',`attachment; filename="${pack.id}.json"`);return res;}
 throw new Problem('Not found',404);
}
Deno.serve(async r=>{let res;try{res=await handle(r);}catch(e){res=json({error:e instanceof Problem?e.message:'Request failed. Please retry.'},e instanceof Problem?e.status:400);}const h=new Headers(res.headers);h.set('Cache-Control','no-store');h.set('Referrer-Policy','no-referrer');h.set('X-Content-Type-Options','nosniff');h.set('Access-Control-Allow-Origin',ORIGIN);h.set('Vary','Origin');h.set('Access-Control-Allow-Headers','authorization,content-type');h.set('Access-Control-Allow-Methods','GET,POST,OPTIONS');return new Response(res.body,{status:res.status,headers:h});});
