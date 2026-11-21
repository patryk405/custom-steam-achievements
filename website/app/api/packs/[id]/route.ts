import {getDb} from '@/db';import {packs} from '@/db/schema';import {eq,sql} from 'drizzle-orm';import {builtinPacks} from '@/lib/packs';
export async function GET(request:Request,{params}:{params:Promise<{id:string}>}){
const {id}=await params;let pack;
if(builtinPacks.some(p=>p.id===id))pack=builtinPacks.find(p=>p.id===id)!;
else {try{const db=getDb();const [row]=await db.select().from(packs).where(eq(packs.id,id)).limit(1);if(!row)return Response.json({error:'Pack not found.'},{status:404});pack=JSON.parse(row.payload);if(new URL(request.url).searchParams.has('download'))await db.update(packs).set({downloads:sql`${packs.downloads}+1`}).where(eq(packs.id,id));}catch{return Response.json({error:'Could not load this pack.'},{status:503});}}
const headers:Record<string,string>={'Content-Type':'application/json; charset=utf-8','X-Content-Type-Options':'nosniff'};if(new URL(request.url).searchParams.has('download'))headers['Content-Disposition']=`attachment; filename="${pack.id}.json"`;
return new Response(JSON.stringify(pack,null,2),{headers});
}
