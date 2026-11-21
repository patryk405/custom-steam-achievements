import {steamAccount} from '@/lib/cloud-session';
import Hub from '../hub';
import {getChatGPTUser} from '../chatgpt-auth';
export const dynamic='force-dynamic';
export default async function Library(){const user=await steamAccount()||await getChatGPTUser();return <Hub signedIn={!!user}/>;}
