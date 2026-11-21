import configuredShortcutIds from '../resources/shortcut-ids.json';
import {findModuleExport} from 'millennium';
import {catalog, type Game} from './model';
import {artwork, paths} from './icons';

// Local shortcut IDs; no Steamworks stats or account achievements are modified.
const shortcutIds:Record<Game,number>=configuredShortcutIds;
async function refreshShortcutIds(){
  const raw=await backend.get_settings();
  const settings=typeof raw==='string'?JSON.parse(raw):raw;
  for(const game of Object.keys(catalog) as Game[]){
    const id=settings.shortcutIds?.[game];
    if(Number.isInteger(id)&&id>0&&id<=0xffffffff)shortcutIds[game]=id;
  }
}
function iconUrl(kind:string){
  const art=artwork[kind]||{motif:kind,color:'#79c8de',tier:''};
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" fill="#243443"/><g transform="translate(8 8)" fill="none" stroke="${art.color}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"><path d="${paths[art.motif]||paths.star}"/></g>${art.tier?`<rect x="32" y="30" width="16" height="18" fill="#17232d"/><text x="40" y="43" text-anchor="middle" fill="${art.color}" font-family="Arial" font-size="12">${art.tier}</text>`:''}</svg>`;
  return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
}
export async function notifyAchievement(game:Game,id:string,preview=false){
  await refreshShortcutIds();
  if(!shortcutIds[game])throw new Error('Configure the Steam shortcut ID first');
  const achievement=catalog[game].achievements.find(a=>a.id===id);
  if(!achievement)throw new Error('Unknown achievement');
  const store=findModuleExport((x:any)=>x&&typeof x.GetNotificationTargets==='function'&&typeof x.OnNotification==='function');
  if(!store)throw new Error('Steam notification store unavailable');
  const entry=Object.entries(store.GetNotificationTargets()).find(([,v]:[string,any])=>v.strTest==='Achievement') as [string,any]|undefined;
  if(!entry?.[1]?.proto?.fromObject)throw new Error('Steam achievement notification unavailable');
  const data=entry[1].proto.fromObject({achievement_id:id,appid:shortcutIds[game],name:preview?'Test notification':achievement.name,description:preview?'Preview only — no achievement unlocked.':achievement.description,image_url:iconUrl(achievement.icon),achieved:true,rtime_unlocked:Math.floor(Date.now()/1000),min_progress:0,current_progress:achievement.target,max_progress:achievement.target});
  // Native desktop toasts do not consistently request Steam's nav sound while
  // a non-Steam game is focused. Use a dedicated audio stream for our entries.
  const target=entry[1];
  if(!target.__customAchievementSound){
    const original=target.playSound;
    target.playSound=(metadata:any,notification:any)=>{
      const id=notification?.data?.achievement_id?.();
      if(Object.values(catalog).some(g=>g.achievements.some(a=>a.id===id)))return false;
      return typeof original==='function'?original(metadata,notification):original;
    };
    target.__customAchievementSound=true;
  }
  const notificationId=Date.now();
  // Use the same native desktop route proven by the preview. Merely inserting
  // into the overlay queue does not wake its renderer for non-Steam shortcuts.
  store.OnNotification(notificationId,Number(entry[0]),data.serializeBinary());
  await backend.play_achievement_sound();
}
export function testNotification(game:Game){const first=catalog[game].achievements[0];if(!first)return Promise.reject(new Error('Import the game trophy catalog first'));return notifyAchievement(game,first.id,true);}
export function startNotifications(){
  // Older plugin versions attached a never-resolving predicate. Remove only
  // those custom entries so they cannot hold up Steam's notification queue.
  try {
    const store=findModuleExport((x:any)=>x&&typeof x.GetNotificationTargets==='function'&&typeof x.ExpireToast==='function');
    const ids=new Set(Object.values(catalog).flatMap(g=>g.achievements.map(a=>a.id)));
    // Clear our orphaned overlay entries from earlier releases only.
    for(const appid of Object.values(shortcutIds)){
      const queue=store?.m_mapAppOverlayToasts?.get(appid);
      if(Array.isArray(queue))for(let i=queue.length-1;i>=0;i--){
        if(queue[i].eType===5&&ids.has(queue[i].data?.achievement_id?.()))queue.splice(i,1);
      }
    }
    for(const item of [...(store?.m_rgNotificationToasts||[])]){
      if(item.eType===5&&ids.has(item.data?.achievement_id?.()))store.ExpireToast(item);
    }
  }catch(error){console.warn('[Custom Achievements] Could not clear old custom notifications',error);}

  let busy=false,stopped=false;
  // Also remember dispatched entries during an acknowledgement retry to avoid duplicate toasts.
  const dispatched=new Set<string>();
  async function poll(){
    if(busy||stopped)return;busy=true;
    try{
      await refreshShortcutIds();
      const raw=await backend.get_pending_notifications();
      const pending=typeof raw==='string'?JSON.parse(raw):raw;
      if(stopped||!Array.isArray(pending)||!pending.length)return;
      // Leave unconfigured games pending without blocking configured games.
      const event=pending.find((item:any)=>shortcutIds[item.game as Game]);
      if(!event)return;
      if(!dispatched.has(event.key)){await notifyAchievement(event.game,event.id);dispatched.add(event.key);}
      await backend.acknowledge_notification(event.key);
    }catch(error){console.warn('[Custom Achievements] Notification delivery deferred',error);}
    finally{busy=false;}
  }
  const timer=setInterval(poll,2000);void poll();
  return()=>{stopped=true;clearInterval(timer);};
}
