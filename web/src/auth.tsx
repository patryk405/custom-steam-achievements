import {createContext,useContext,useEffect,useState, type ReactNode} from 'react';
import {apiFetch,HOME} from './api';
const random=()=>Array.from(crypto.getRandomValues(new Uint8Array(32)),x=>x.toString(16).padStart(2,'0')).join('');
const sha=async(s:string)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))),x=>x.toString(16).padStart(2,'0')).join('');
type Auth={data:any,error:string,ready:boolean,login:()=>Promise<void>,logout:()=>Promise<void>,refresh:()=>Promise<void>};
const Context=createContext<Auth>(null!);export const useAuth=()=>useContext(Context);
export function AuthProvider({children}:{children:ReactNode}){
 const [data,setData]=useState<any>(null),[error,setError]=useState(''),[ready,setReady]=useState(false);
 async function refresh(){const r=await apiFetch('/api/cloud/me');if(!r.ok)throw Error('Could not load your account. Please retry.');const d=await r.json();setData(d);if(!d.signedIn)sessionStorage.removeItem('csa-session');}
 async function login(){setError('');try{const state=random(),verifier=random();sessionStorage.setItem('csa-login',JSON.stringify({state,verifier,returnTo:location.search,at:Date.now()}));const r=await apiFetch('/api/cloud/login/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state,challenge:await sha(verifier)})});const d=await r.json();if(!r.ok)throw Error(d.error);const target=new URL(d.url);if(target.origin!=='https://steamcommunity.com')throw Error('Invalid login destination');location.assign(d.url);}catch(e){setError(String(e instanceof Error?e.message:e));}}
 async function logout(){try{const r=await apiFetch('/api/cloud/logout',{method:'POST'});if(!r.ok&&r.status!==401)throw Error('Sign out failed. Retry.');sessionStorage.removeItem('csa-session');setData({signedIn:false});}catch(e){setError(String(e));}}
 useEffect(()=>{(async()=>{try{const state=new URLSearchParams(location.search).get('auth');if(state){const saved=JSON.parse(sessionStorage.getItem('csa-login')||'null');history.replaceState(null,'',HOME+'?view=account');if(!saved||saved.state!==state||Date.now()-saved.at>600000)throw Error('This sign-in was not started in this browser. Please sign in again.');const r=await apiFetch('/api/cloud/exchange',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state,verifier:saved.verifier})});const d=await r.json();if(!r.ok)throw Error(d.error);sessionStorage.removeItem('csa-login');sessionStorage.setItem('csa-session',d.token);const query=new URLSearchParams(saved.returnTo);query.set('view','account');query.delete('auth');history.replaceState(null,'',HOME+'?'+query);}
 await refresh();}catch(e){setError(String(e instanceof Error?e.message:e));}finally{setReady(true);}})();},[]);
 return <Context.Provider value={{data,error,ready,login,logout,refresh}}>{children}</Context.Provider>;
}
