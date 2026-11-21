import assert from 'node:assert/strict';
import {test} from 'node:test';
import {assertion,verifySteam,STEAM,NS} from '../lib/steam-auth.ts';
const back='https://example.test/api/cloud/callback?state=abc';
const base=()=>new URLSearchParams({'openid.ns':NS,'openid.mode':'id_res','openid.op_endpoint':STEAM,'openid.claimed_id':'https://steamcommunity.com/openid/id/76561198000000000','openid.identity':'https://steamcommunity.com/openid/id/76561198000000000','openid.return_to':back,'openid.response_nonce':new Date().toISOString().replace(/\.\d{3}Z/,'Z')+'nonce','openid.signed':'op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle','openid.assoc_handle':'handle','openid.sig':'sig'});
test('valid Steam assertion shape',()=>assert.equal(assertion(base(),back).steamId,'76561198000000000'));
test('reject unsigned, stale, duplicate, wrong return, forged provider and identity',()=>{
 for(const [key,value] of [['openid.signed','identity'],['openid.return_to','https://evil.test/'],['openid.op_endpoint','https://evil.test/'],['openid.identity','https://steamcommunity.com/openid/id/76561198000000001'],['openid.response_nonce','2000-01-01T00:00:00Znonce']]){const p=base();p.set(key,value);assert.throws(()=>assertion(p,back));}
 const dup=base();dup.append('openid.mode','id_res');assert.throws(()=>assertion(dup,back));
});
test('Steam verification failure cannot authenticate',async()=>{const fetchOriginal=globalThis.fetch;try{globalThis.fetch=async()=>new Response('is_valid:false');await assert.rejects(verifySteam(base(),back));globalThis.fetch=async(url,init)=>{assert.equal(url,STEAM);assert.equal(init?.redirect,'manual');assert.equal(new URLSearchParams(init?.body as string).get('openid.mode'),'check_authentication');return new Response('ns:'+NS+'\nis_valid:true\n');};assert.equal((await verifySteam(base(),back)).steamId,'76561198000000000');}finally{globalThis.fetch=fetchOriginal;}});
