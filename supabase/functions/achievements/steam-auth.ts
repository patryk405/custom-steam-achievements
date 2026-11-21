export const STEAM='https://steamcommunity.com/openid/login';
export const NS='http://specs.openid.net/auth/2.0';
export const token=()=>Array.from(crypto.getRandomValues(new Uint8Array(32)),n=>n.toString(16).padStart(2,'0')).join('');
export async function hash(value:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))),n=>n.toString(16).padStart(2,'0')).join('');}
export function assertion(params:URLSearchParams,returnTo:string,now=Date.now()){
 for(const key of new Set(params.keys()))if(params.getAll(key).length!==1)throw Error('Duplicate OpenID field');
 const signed=new Set((params.get('openid.signed')||'').split(','));
 for(const k of ['op_endpoint','claimed_id','identity','return_to','response_nonce','assoc_handle'])if(!signed.has(k))throw Error('Unsigned OpenID field');
 const claimed=params.get('openid.claimed_id')||'';
 if(params.get('openid.ns')!==NS||params.get('openid.mode')!=='id_res'||params.get('openid.op_endpoint')!==STEAM||params.get('openid.return_to')!==returnTo||params.get('openid.identity')!==claimed)throw Error('Invalid OpenID assertion');
 const match=/^https:\/\/steamcommunity\.com\/openid\/id\/(7656119\d{10})$/.exec(claimed);
 if(!match)throw Error('Invalid Steam identity');
 const nonce=params.get('openid.response_nonce')||'';
 if(nonce.length>255||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ[!-~]+$/.test(nonce)||!Number.isFinite(Date.parse(nonce.slice(0,20)))||Math.abs(now-Date.parse(nonce.slice(0,20)))>300000)throw Error('Expired Steam response');
 return {steamId:match[1],nonce};
}
export async function verifySteam(params:URLSearchParams,returnTo:string){
 const result=assertion(params,returnTo);
 const form=new URLSearchParams();for(const [k,v] of params)if(k.startsWith('openid.'))form.set(k,v);form.set('openid.mode','check_authentication');
 const res=await fetch(STEAM,{method:'POST',body:form,redirect:'manual',signal:AbortSignal.timeout(10000)});
 if(!res.ok||!(await res.text()).split(/\r?\n/).includes('is_valid:true'))throw Error('Steam could not verify this sign-in');
 return result;
}
