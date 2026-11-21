import {z} from 'zod';
import signals from './signals.json';
import builtin from './builtin.json';
import oot from './oot-builtin.json';
import bloodborne from './bloodborne-builtin.json';
import arceus from './arceus-builtin.json';
import odyssey from './odyssey-builtin.json';
import pokopia from './pokopia-builtin.json';
const key=z.string().regex(/^[a-zA-Z0-9_-]{1,80}$/);
const rule=z.object({op:z.enum(['any','all','count','number','sum']),flags:z.array(z.enum(signals as [string,...string[]])).min(1).max(200),threshold:z.number().int().min(1).max(1000000).optional(),note:z.string().max(400).optional()}).strict();
export const packSchema=z.object({schema:z.literal(1),id:key,title:z.string().trim().min(3).max(80),game:z.literal('botw'),version:z.string().regex(/^\d+\.\d+\.\d+$/),author:z.string().trim().min(2).max(50),description:z.string().trim().min(12).max(1500),source:z.string().url().refine(v=>v.startsWith('https://')).optional(),achievements:z.array(z.object({id:key,name:z.string().trim().min(2).max(100),description:z.string().trim().min(3).max(500),target:z.number().int().min(1).max(1000000),icon:key}).strict()).min(1).max(200),rules:z.record(key,rule)}).strict().superRefine((p,ctx)=>{
const ids=p.achievements.map(a=>a.id);
if(new Set(ids).size!==ids.length)ctx.addIssue({code:'custom',message:'Achievement IDs must be unique.'});
if(Object.keys(p.rules).length!==ids.length||ids.some(id=>!p.rules[id]))ctx.addIssue({code:'custom',message:'Every achievement must have exactly one matching rule.'});
for(const [id,r] of Object.entries(p.rules))if(['number','sum'].includes(r.op)&&!r.threshold)ctx.addIssue({code:'custom',message:`${id}: numeric rules require a threshold.`});
});
export type Pack=Omit<z.infer<typeof packSchema>,'game'> & {game:'botw'|'oot'|'bloodborne'|'arceus'|'odyssey'|'pokopia'};
export const builtinPack=builtin as Pack;
export const builtinPacks:Pack[]=[builtinPack,oot as Pack,bloodborne as Pack,arceus as Pack,odyssey as Pack,pokopia as Pack];
export function summary(p:Pack,id=p.id,createdAt=0,downloads=0){return {id,title:p.title,author:p.author,description:p.description,game:p.game,version:p.version,count:p.achievements.length,createdAt,downloads};}
