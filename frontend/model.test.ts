import {test,expect} from 'bun:test';
import {catalog,count,resolveGame,summary} from './model';
import {artwork,paths} from './icons';
test('matches supported shortcuts and leaves unrelated games alone',()=>{
 expect(resolveGame('The Legend of Zelda: Breath of the Wild')).toBe('botw');
 expect(resolveGame('The Legend of Zelda: Ocarina of Time 2026')).toBe('oot');
 expect(resolveGame('KINGDOM HEARTS III')).toBeNull();expect(resolveGame(undefined)).toBeNull();
});
test('Automatic Reddit subset has unique IDs and corresponding icons',()=>{
 const all=catalog.botw.achievements;expect(all).toHaveLength(39);
 expect(new Set(all.map(a=>a.id)).size).toBe(39);
 for(const game of Object.values(catalog)) for(const a of game.achievements){expect(artwork[a.icon]).toBeDefined();expect(paths[artwork[a.icon].motif]?.length).toBeGreaterThan(5);expect(a.target).toBeGreaterThan(0);}
});
test('old prototype records cannot unlock new tasks; partial progress stays partial',()=>{
 const p={shrines10:{current:10,source:'manual-test' as const},reddit_shrines30:{current:29,source:'manual-test' as const},reddit_first:{current:1,source:'manual-test' as const}};
 expect(summary('botw',p)).toEqual({unlocked:1,total:39,percent:3});
 expect(summary('oot',p).unlocked).toBe(0);
 expect(summary('botw',{shrines10:p.shrines10}).unlocked).toBe(0);
});
test('invalid numeric progress is clamped or ignored',()=>{
 for(const [v,want] of [[NaN,0],[Infinity,0],[-1,0],[12,10],[3.9,3]]) expect(count({x:{current:v,source:'manual-test'}},'x',10)).toBe(want!);
});
test('Bloodborne full pack is recognized and starts locked',()=>{
 expect(resolveGame('Bloodborne — BBPort')).toBe('bloodborne');
 expect(summary('bloodborne',{})).toEqual({unlocked:0,total:40,percent:0});
});
