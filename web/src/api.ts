export const API='https://wfkgkhkuuxsggxdanvfp.supabase.co/functions/v1/achievements';
export const HOME='/custom-steam-achievements/';
export const apiUrl=(path:string)=>API+path.replace(/^\/api/,'');
export function apiFetch(path:string,options:RequestInit={}){const headers=new Headers(options.headers),token=sessionStorage.getItem('csa-session');if(token)headers.set('Authorization','Bearer '+token);return window.fetch(apiUrl(path),{...options,headers,credentials:'omit'});}
