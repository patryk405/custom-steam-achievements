import {expect,test,mock} from 'bun:test';
const desktop:any[][]=[],overlay:any[][]=[];
const store={
 GetNotificationTargets:()=>({5:{strTest:'Achievement',proto:{fromObject:(data:any)=>({serializeBinary:()=>data})}}}),
 OnNotification:(...args:any[])=>desktop.push(args),
 AddAppOverlayNotification:(...args:any[])=>overlay.push(args),
 GetAppsWithOverlayRunning:()=>[0],
};
mock.module('millennium',()=>({findModuleExport:()=>store}));
const audioCalls:string[]=[];
(globalThis as any).backend={play_achievement_sound:async()=>{audioCalls.push('played');return true;}};
const {notifyAchievement,testNotification}=await import('./notifications');
test('preview goes to desktop even in game and omits persistent-until-resolved callback',async()=>{
 await testNotification('botw');
 expect(desktop.at(-1)).toHaveLength(3);
 expect(desktop.at(-1)![2].name).toBe('Test notification');
 expect(overlay).toHaveLength(0);
});
test('real unlock uses the working desktop route even with an overlay registered',async()=>{
 await notifyAchievement('botw','reddit_calamity');
 expect(audioCalls).toHaveLength(2);
 expect(desktop.at(-1)).toHaveLength(3);
 expect(desktop.at(-1)![2].name).toBe('Calamity Adverted');
 expect(overlay).toHaveLength(0);
});
