import {startNotifications, testNotification} from './notifications';
import adapter from '../resources/botw-adapter.json';
import ootAdapter from '../resources/oot-adapter.json';
import bbportAdapter from '../resources/bbport-adapter.json';
import arceusAdapter from '../resources/arceus-adapter.json';
import odysseyAdapter from '../resources/odyssey-adapter.json';
import pokopiaAdapter from '../resources/pokopia-adapter.json';
const adapters = {botw: adapter, oot: ootAdapter, bloodborne: bbportAdapter, arceus: arceusAdapter, odyssey: odysseyAdapter, pokopia: pokopiaAdapter};
import {usePreferences,savePreferences,refreshPreferences} from './preferences';
import { paths, artwork } from './icons';
import { native } from './native';
import { definePlugin, showModal, ModalRoot } from 'millennium';
import { useEffect, useState, type JSX } from 'react';
import { catalog, count, resolveGame, summary, type Game, type Progress } from './model';

const listeners = new Set<() => void>();
const announce = () => listeners.forEach(fn => fn());

function Icon({kind = 'triforce', locked = false}: {kind?: string; locked?: boolean}) {
  const art=artwork[kind] || {motif:kind,color:'#79c8de',tier:''};
  return <span style={{'--art-color':art.color} as any} className={`cach-icon ${locked ? 'cach-locked' : ''}`}><svg viewBox="0 0 32 32" aria-hidden="true"><path d={paths[art.motif] || paths.star} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />{art.tier&&<><path d="M21 20h11v12H21z" fill="#17232d" stroke="none"/><text x="26.5" y="29" textAnchor="middle" fill="currentColor" fontSize="9" fontWeight="700" fontFamily="Arial">{art.tier}</text></>}</svg></span>;
}
const css = `
.cach {font-family:"Motiva Sans",Arial,sans-serif;color:#d6d7d8;font-size:13px;--ca:#64bacb;box-sizing:border-box}
.cach *{box-sizing:border-box}.cach button{font:inherit;cursor:pointer;color:#d6d7d8;background:#ffffff0b;border:1px solid #ffffff12;border-radius:2px;padding:8px 12px}.cach button:hover{background:#ffffff18;color:white}.cach button:focus-visible,.cach input:focus-visible{outline:2px solid var(--ca);outline-offset:3px}.cach button:disabled{opacity:.4;cursor:wait}
.cach-heading{display:flex;justify-content:space-between;align-items:center;color:#8f98a0;text-transform:uppercase;font-size:13px;letter-spacing:1px;margin-bottom:7px}.cach-tag{font-size:9px;letter-spacing:1px;color:#aeb5bc;border:1px solid #ffffff20;padding:3px 5px}.cach-body{background:linear-gradient(105deg,#ffffff0c,#ffffff06);padding:13px 12px;border:1px solid #ffffff04}.cach-count{color:#aeb4bb;font-size:12px;margin-bottom:9px}.cach-track{height:8px;background:#10151b;border-radius:5px;overflow:hidden}.cach-fill{height:100%;background:var(--ca);transition:width .25s}.cach-label{font-size:12px;color:#8f98a0;margin:17px 0 9px}.cach-icons{display:flex;gap:7px;flex-wrap:wrap}.cach-icon{width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;color:var(--art-color,var(--ca));background:linear-gradient(135deg,#ffffff14,#0004);border:1px solid #ffffff28;box-shadow:inset 0 0 0 2px #0002}.cach-icon svg{width:29px;height:29px}.cach-locked{color:#92989c;filter:grayscale(1);opacity:.6}.cach .cach-icon-button{border:0;padding:0;background:transparent}.cach .cach-icon-button:hover{background:transparent}.cach-icon-button:hover .cach-icon{border-color:var(--ca);opacity:1}.cach-footer{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:13px;color:#8f98a0;font-size:11px}.cach .cach-link{border:0;background:transparent;padding:6px 0;font-size:12px;color:#b4bdc6}.cach .cach-link:hover{color:white;text-decoration:underline}.cach-dialog{width:100%;max-width:740px;max-height:82vh;overflow:auto;background:#1b242e;padding:26px}.cach-dialog h2{font-weight:400;font-size:25px;color:#fff;margin:0 0 5px}.cach-subtitle{color:#929da8;font-size:13px;margin-bottom:20px;line-height:1.6}.cach-overview{padding:15px;background:#0002;margin-bottom:18px}.cach-row{display:flex;gap:15px;padding:15px 0;border-bottom:1px solid #ffffff0d;align-items:center}.cach-row-main{flex:1;min-width:0}.cach-name{font-size:15px;color:#e4e7e9;margin-bottom:5px}.cach-desc{font-size:13px;line-height:1.4;color:#9aa7b3}.cach-date{font-size:11px;color:var(--ca);margin-top:6px}.cach-small-progress{display:flex;align-items:center;gap:10px;margin-top:9px;color:#a0acb7;font-size:11px}.cach-small-progress .cach-track{height:4px;flex:1;max-width:200px}.cach-controls{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:9px}.cach-controls input{width:70px;padding:7px;background:#101820;border:1px solid #53616b;color:#fff}.cach-controls button{font-size:11px;padding:7px}.cach-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:20px}.cach-toolbar label{color:#a4afb9;font-size:12px;display:flex;gap:7px;align-items:center}.cach-error{color:#ffb2a6;font-size:12px;padding:8px 0;line-height:1.4}.cach-settings{padding:18px;line-height:1.6}.cach-settings button{display:block;margin:12px 0}.cach-empty{color:#a1adb8;padding:14px}
`;
function useProgress(game: Game) {
  const [progress, setProgress] = useState<Progress>({});
  const [error, setError] = useState('');
  const [loading,setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    const load = () => backend.get_state(game).then(raw => { if(alive) {setProgress(typeof raw === 'string' ? JSON.parse(raw) : raw);setError('');setLoading(false);} }).catch(() => {if(alive){setError('Could not load progress. Please try again.');setLoading(false);}});
    setLoading(true);load();listeners.add(load);const timer=setInterval(load,5000);
    return () => {alive = false;listeners.delete(load);clearInterval(timer);};
  },[game]);
  return {progress,error,loading};
}
function Meter({game,progress}: {game:Game;progress:Progress}) {
  const s=summary(game,progress);
  return <><div className="cach-count">You've unlocked {s.unlocked}/{s.total} ({s.percent}%)</div><div className="cach-track" role="progressbar" aria-label="Unlocked achievements" aria-valuenow={s.unlocked} aria-valuemin={0} aria-valuemax={s.total}><div className="cach-fill" style={{width:`${s.percent}%`}} /></div></>;
}
function TestControls({game,id,target,value}: {game:Game;id:string;target:number;value:number}) {
  const [draft,setDraft]=useState(value);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  useEffect(()=>setDraft(value),[value]);
  async function save(n:number) {
    if(!Number.isInteger(n)||n<0||n>target){setError(`Enter a number from 0–${target}.`);return;}
    setBusy(true);setError('');
    try {await backend.set_test_progress(game,id,n);announce();}catch{setError('Could not save progress.');}finally{setBusy(false);}
  }
  return <><div className="cach-controls">{target>1&&<><input aria-label="Test progress" type="number" min={0} max={target} value={draft} onChange={e=>setDraft(Number(e.target.value))}/><button disabled={busy} onClick={()=>save(draft)}>Save progress</button></>}<button disabled={busy} onClick={()=>save(value===target?0:target)}>{value===target?'Lock again':'Unlock manually'}</button></div>{error&&<div className="cach-error" role="alert">{error}</div>}</>;
}
function PreferencesControls({game}:{game:Game}) {
  const prefs=usePreferences();const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  useEffect(()=>{const t=setInterval(()=>refreshPreferences().catch(()=>{}),5000);return()=>clearInterval(t);},[]);
  async function change(mode:'original'|'community',auto:boolean){setBusy(true);try{await savePreferences(mode,auto);announce();setError('');}catch{setError('Could not save preferences.');}finally{setBusy(false);}}
  const status=prefs.status[game];const stale=!prefs.updatedAt||Date.now()/1000-prefs.updatedAt>30;
  return <div className="cach-overview"><div style={{marginTop:10}}><label><input disabled={busy} type="checkbox" checked={prefs.autoEnabled} onChange={e=>change(prefs.iconMode,e.target.checked)}/> Enable automatic tracking</label></div><p className="cach-desc">{!prefs.autoEnabled?'Automatic tracking paused':stale?'Tracker is not responding — automatic progress may be out of date':status?.message||'No automatic adapter installed for this game.'}{` · ${Object.keys(adapters[game].rules).length}/${catalog[game].achievements.length} objectives supported`}</p><button disabled={!catalog[game].achievements.length} onClick={async()=>{try{await testNotification(game);setError('');}catch{setError('Native Steam notifications are unavailable. Restart Steam and try again.');}}}>Test notification</button><p className="cach-desc">When the status says Live tracking, play normally — no save required. Detection usually takes a few seconds. Arceus and Odyssey update after saves or autosaves. Pokopia live tracking requires the CSA launch wrapper. Bloodborne uses a local trophy journal. Longshot requires the live connection. Steam notification and sound settings apply.</p>{error&&<div className="cach-error">{error}</div>}</div>;
}
function Details({game,closeModal}: {game:Game;closeModal?:()=>void}) {
  const {progress,error,loading}=useProgress(game);const [testing,setTesting]=useState(false);const [confirm,setConfirm]=useState(false);const [failure,setFailure]=useState('');
  const def=catalog[game];
  async function reset(){try{await backend.reset_test_progress(game);announce();setConfirm(false);}catch{setFailure('Could not reset test progress.');}}
  return <ModalRoot onCancel={closeModal}><section className="cach cach-dialog" style={{'--ca':def.color} as any}><style>{css}</style><h2>Achievements</h2><div className="cach-subtitle">{def.name}<br/>Local achievements · automatic tracking.{game==='botw'&&<><br/><a href="https://www.reddit.com/r/Breath_of_the_Wild/comments/7mypvr/decided_to_make_some_achievements_for_breath_of/" target="_blank" rel="noreferrer" style={{color:'#67c1f5'}}>Achievement names and descriptions quoted from the Reddit community list</a></>}</div><PreferencesControls game={game}/><div className="cach-overview"><Meter game={game} progress={progress}/></div>{loading&&<p>Loading progress…</p>}{error&&<div role="alert" className="cach-error">{error}</div>}{def.achievements.map(a=>{const n=count(progress,a.id,a.target),done=n===a.target;return <div className="cach-row" key={a.id}><Icon kind={a.icon} locked={!done}/><div className="cach-row-main"><div className="cach-name">{a.name}</div><div className="cach-desc">{a.description}</div>{done?<div className="cach-date">{progress[a.id]?.source==='automatic'?'Automatically unlocked':'Unlocked manually'}{progress[a.id]?.unlockedAt?` · ${new Date(progress[a.id].unlockedAt!*1000).toLocaleString('en-US')}`:''}</div>:a.target>1?<div className="cach-small-progress"><div className="cach-track"><div className="cach-fill" style={{width:`${100*n/a.target}%`}}/></div><span>{n}/{a.target}</span></div>:null}{<div className="cach-desc" style={{fontSize:11,marginTop:5}}>{a.id in adapters[game].rules?`Automatic · ${(adapters[game].rules as any)[a.id].note||'Detected live while playing; save-based fallback when offline.'}`:'Manual only · this objective needs a game-event adapter.'}</div>}{testing&&progress[a.id]?.source!=='automatic'&&<TestControls game={game} id={a.id} target={a.target} value={n}/>}</div></div>})}<div className="cach-toolbar"><label><input type="checkbox" checked={testing} onChange={e=>{setTesting(e.target.checked);setConfirm(false);}}/>Enable manual test mode</label><button onClick={closeModal}>Close</button></div>{testing&&<div className="cach-toolbar">{confirm?<><span>Reset all manual unlocks for this game?</span><button onClick={reset}>Yes, reset</button><button onClick={()=>setConfirm(false)}>Cancel</button></>:<button onClick={()=>setConfirm(true)}>Reset test progress</button>}</div>}{failure&&<div role="alert" className="cach-error">{failure}</div>}</section></ModalRoot>;
}
function openDetails(game:Game,parent?:EventTarget){showModal(<Details game={game}/>,parent,{strTitle:`Achievements — ${catalog[game].name}`,bNeverPopOut:true,popupWidth:800,popupHeight:900});}
// Native Steam class names captured from this client's own achievement section.
// Only the artwork and click handlers are custom; Steam owns the panel styling.
const nativeCss = `
.cach-native button.cach-art-button{all:unset;cursor:pointer;width:48px;height:48px;box-sizing:border-box}
.cach-native .cach-icon{display:flex;width:100%;height:100%;box-sizing:border-box;align-items:center;justify-content:center;background:linear-gradient(135deg,#425363,#19232e);border:1px solid #ffffff30;color:var(--art-color,#c5dbe5)}
.cach-native .cach-icon svg{width:32px;height:32px}.cach-native .cach-locked{filter:grayscale(1);color:#a5a5a5;background:linear-gradient(135deg,#424242,#242424)}
.cach-native .cach-art-button:hover{filter:brightness(1.2)}.cach-native button:focus-visible{outline:2px solid #67c1f5;outline-offset:2px}
.cach-native .cach-more{all:unset;box-sizing:border-box;width:48px;height:48px;display:flex;align-items:center;justify-content:center;border:1px solid var(--color-dull-9,#606770);font-size:16px;font-weight:700;color:var(--color-text-body-title,#fff);cursor:pointer}
.cach-native .cach-error{padding:8px 0;color:#ffb2a6;font-size:12px}
`;
function NativeIcons({game,achievements,progress}:{game:Game;achievements:typeof catalog.botw.achievements;progress:Progress}) {
  const total=achievements.length;
  // CSS container queries work across Millennium's React boundary; DOM refs do not.
  const rules=Array.from({length:total},(_,i)=>{
    const slots=i+1,visible=slots>=total?total:slots-1;
    const min=slots===1?0:slots*52-4,max=(slots+1)*52-5;
    return `@container cach-icons (min-width:${min}px) ${slots<total?`and (max-width:${max}px)`:''}{.cach-native .cach-total-${total} .cach-art-button:nth-of-type(-n+${visible}){display:block}.cach-native .cach-total-${total} .cach-more-${total-visible}{display:flex}}`;
  }).join('');
  return <div className={`${native.icons} cach-total-${total}`} style={{'--grid-columns':'repeat(auto-fill, var(--icon-size))','--grid-rows':'repeat(1, var(--icon-size))','--grid-gap':'var(--spacing-1)','--icon-size':'48px',containerType:'inline-size',containerName:'cach-icons'} as any}>
    <style>{`.cach-native button.cach-art-button,.cach-native button.cach-more{display:none}`+rules}</style>
    {achievements.map(a=><button type="button" className={`cach-art-button ${native.icon}`} key={a.id} aria-label={a.name} title={`${a.name}\n${a.description}`} onClick={e=>openDetails(game,e.currentTarget.ownerDocument.defaultView!)}><Icon kind={a.icon} locked={count(progress,a.id,a.target)!==a.target}/></button>)}
    {Array.from({length:total},(_,i)=>i+1).map(n=><button key={n} className={`cach-more cach-more-${n}`} aria-label={`View ${n} more achievements`} onClick={e=>openDetails(game,e.currentTarget.ownerDocument.defaultView!)}>+{n}</button>)}
  </div>;
}

function Panel({game}:{game:Game}) {
  const {progress,error,loading}=useProgress(game);const def=catalog[game],s=summary(game,progress);
  const unlocked=def.achievements.filter(a=>count(progress,a.id,a.target)===a.target);
  const locked=def.achievements.filter(a=>count(progress,a.id,a.target)!==a.target);
  return <section className={`cach-native cach-panel ${native.section}`} data-custom-achievements={game} aria-label="Custom achievements">
    <style>{nativeCss}</style>
    <h2 className={native.header}><div className={native.headerLabel}><div className={native.headerText}>Achievements</div></div></h2>
    <div className={native.container}>
      <div className={native.highlight}><div className={native.count}>{loading?'Loading achievements…':<>You've unlocked {s.unlocked}/{s.total}<span className={native.percent}> ({s.percent}%)</span></>}</div>
        <div className={native.progressRow}><div className={native.progressBox}><div className={native.track} role="progressbar" aria-label="Unlocked achievements" aria-valuenow={s.unlocked} aria-valuemin={0} aria-valuemax={s.total} style={{'--height':'10px','--background':'var(--color-dull-1)','--overflow':'hidden','--grid-columns':`${s.unlocked}fr ${s.total-s.unlocked}fr`} as any}><div className={native.fill}/><div className={native.empty}/></div></div></div>
      </div>
      <div className={native.body}>
        {unlocked.length>0&&<><div className={native.featured} role="button" tabIndex={0} onClick={e=>openDetails(game,e.currentTarget.ownerDocument.defaultView!)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openDetails(game,e.currentTarget.ownerDocument.defaultView!);}}}><div className={native.featuredIcon}><Icon kind={unlocked[0].icon}/></div><div className={native.featuredText}><div className={native.name}>{unlocked[0].name}</div><div className={native.desc}>{unlocked[0].description}</div></div></div>{unlocked.length>1&&<NativeIcons game={game} achievements={unlocked.slice(1)} progress={progress}/>}</>}
        {locked.length>0&&<div className={`${native.lockedSection}${unlocked.length?' '+native.divider:''}`}><div className={native.label}>Locked Achievements</div><NativeIcons game={game} achievements={locked} progress={progress}/></div>}
        {error&&<div role="alert" className="cach-error">{error}</div>}
        <button type="button" className={`${native.button} cach-link`} onClick={e=>openDetails(game,e.currentTarget.ownerDocument.defaultView!)}>View My Achievements</button>
      </div>
    </div>
  </section>;
}
/** @ffi */
export function AchievementPanel({overview}: {details?:any;overview?:any}): JSX.Element | null {
  const game=resolveGame(overview?.display_name);
  useEffect(()=>{if(game&&Number.isInteger(overview?.appid))void backend.register_shortcut(game,overview.appid).catch(console.warn);},[game,overview?.appid]);
  return game?<Panel key={game} game={game}/>:null;
}
function CloudSettings(){
 const prefs=usePreferences();const [error,setError]=useState('');
 useEffect(()=>{const t=setInterval(()=>refreshPreferences().catch(()=>{}),3000);return()=>clearInterval(t);},[]);
 async function act(action:string){try{await backend.cloud_action(action);setError('');await refreshPreferences();}catch{setError('Could not connect. Check that the tracker is running.');}}
 const cloud=prefs.cloud;const url=cloud?.verificationUrl;
 return <section className="cach-overview"><h3>Steam cloud sync</h3><p>{prefs.steamId?'Steam account: '+prefs.steamId:'Waiting for Steam account'}</p><p>{cloud?.message||'Connect once on each device to sync your custom achievements.'}</p>{cloud?.syncedAt&&<p>Last sync: {new Date(cloud.syncedAt*1000).toLocaleString()}</p>}{url&&url.startsWith('https://achievement-hub-patryk405.green-ray-4163.chatgpt.site/account?device=')&&<a href={url} target="_blank" rel="noreferrer" onClick={e=>{const open=(window as any).SteamClient?.System?.OpenInSystemBrowser;if(open){e.preventDefault();open(url);}}}>Approve this device in your browser</a>}<button disabled={!prefs.steamId} onClick={()=>act('connect')}>Connect Steam cloud</button><button onClick={()=>act('disconnect')}>Disconnect this device</button>{error&&<p className="cach-error">{error}</p>}</section>;
}
function startAccountHeartbeat(){
 const send=()=>{const app=(window as any).App;if(!app?.GetCurrentUser)return;const id=app.BHasCurrentUser?.()===false?'':app.GetCurrentUser()?.strSteamID||'';backend.set_active_steam_account(String(id)).catch(()=>{});};
 send();const timer=setInterval(send,5000);return()=>clearInterval(timer);
}
function Settings(){return <div className="cach cach-settings"><style>{css}</style><h2>Custom Achievements</h2><CloudSettings/><PreferencesControls game="botw"/><p>Local achievement panels for the Steam library. Tracked progress can sync across your connected devices; official Steam achievements and your profile are not modified.</p>{(Object.keys(catalog) as Game[]).map(game=><button key={game} onClick={e=>openDetails(game,e.currentTarget.ownerDocument.defaultView!)}>{catalog[game].name} — view achievements</button>)}<p>The panel appears in the right column of supported games. If a Steam update breaks the integration, you can still open the achievement list here.</p></div>}
export default definePlugin(()=>{const stop=startNotifications();const stopAccount=startAccountHeartbeat();return {icon:<Icon/>,content:<Settings/>,onDismount:()=>{stop();stopAccount();}};});
