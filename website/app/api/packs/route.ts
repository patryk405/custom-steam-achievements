import {steamAccount} from '@/lib/cloud-session';
import {getDb} from '@/db';
import {packs} from '@/db/schema';
import {desc,eq,sql} from 'drizzle-orm';
import {getChatGPTUser} from '@/app/chatgpt-auth';
import {packSchema} from '@/lib/packs';
export async function GET(){
try{const rows=await getDb().select({id:packs.id,title:packs.title,author:packs.author,description:packs.description,game:packs.game,version:packs.version,count:packs.count,createdAt:packs.createdAt,downloads:packs.downloads}).from(packs).orderBy(desc(packs.createdAt)).limit(100);return Response.json(rows);}catch{return Response.json({error:'The library is temporarily unavailable. Please retry.'},{status:503});}
}
export async function POST(request:Request){
const origin=request.headers.get('origin');if(!origin||origin!==new URL(request.url).origin)return Response.json({error:'Invalid request origin.'},{status:403});
const steam=await steamAccount(request);const user=steam?{userId:'steam:'+steam.steam_id}:await getChatGPTUser();if(!user)return Response.json({error:'Sign in to upload a pack.'},{status:401});
if(Number(request.headers.get('content-length')||0)>131072)return Response.json({error:'Packs must be smaller than 128 KB.'},{status:413});
const reader=request.body?.getReader();if(!reader)return Response.json({error:'Missing file.'},{status:400});let size=0;const chunks:Uint8Array[]=[];
for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>131072){await reader.cancel();return Response.json({error:'Packs must be smaller than 128 KB.'},{status:413});}chunks.push(value);}
let raw;try{const b=new Uint8Array(size);let pos=0;for(const c of chunks){b.set(c,pos);pos+=c.length;}raw=JSON.parse(new TextDecoder().decode(b));}catch{return Response.json({error:'Upload a valid JSON pack.'},{status:400});}
const result=packSchema.safeParse(raw);if(!result.success)return Response.json({error:result.error.issues.slice(0,3).map(x=>x.message).join(' ')},{status:400});
try{const db=getDb();const total=await db.select({count:sql<number>`count(*)`}).from(packs).where(eq(packs.owner,user.userId));if(total[0].count>=20)return Response.json({error:'The early-access limit is 20 packs per creator.'},{status:429});const p=result.data,id=crypto.randomUUID();await db.insert(packs).values({id,owner:user.userId,title:p.title,author:p.author,description:p.description,game:p.game,version:p.version,payload:JSON.stringify(p),count:p.achievements.length,createdAt:Date.now()});return Response.json({id},{status:201});}catch{return Response.json({error:'Could not save this pack. Please retry.'},{status:503});}
}
