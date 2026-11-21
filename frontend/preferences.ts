import {useEffect,useState} from 'react';
export type Preferences={iconMode:'original'|'community';autoEnabled:boolean;updatedAt?:number;steamId?:string;cloud?:{status:string;message:string;steamId?:string;verificationUrl?:string;syncedAt?:number};status:Record<string,{message:string;error?:boolean;supported:number;lastReadAt?:number}>};
let current:Preferences={iconMode:'original',autoEnabled:true,status:{}};
const listeners=new Set<(p:Preferences)=>void>();
let pending:Promise<void>|undefined;
export function refreshPreferences(){
  if(!pending)pending=backend.get_settings().then(raw=>{current=typeof raw==='string'?JSON.parse(raw):raw;listeners.forEach(fn=>fn(current));}).finally(()=>{pending=undefined;});
  return pending;
}
export function usePreferences(){
  const [prefs,setPrefs]=useState(current);
  useEffect(()=>{listeners.add(setPrefs);refreshPreferences().catch(()=>{});return()=>{listeners.delete(setPrefs);};},[]);
  return prefs;
}
export async function savePreferences(iconMode:Preferences['iconMode'],autoEnabled:boolean){
  await backend.set_preferences(iconMode,autoEnabled);await refreshPreferences();
}
