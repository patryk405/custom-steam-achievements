import raw from '../resources/catalog.json';
export const catalog = raw;
export type Game = keyof typeof catalog;
export type Progress = Record<string, { current: number; unlockedAt?: number; source: 'manual-test' | 'automatic'; adapter?: string }>;
export function resolveGame(name: unknown): Game | null {
  if (typeof name !== 'string') return null;
  const n = name.toLowerCase();
  for(const game of Object.keys(catalog) as Game[]) {
    if(catalog[game].matchNames.some(alias=>n.includes(alias))) return game;
  }
  return null;
}
export function count(progress: Progress, id: string, target: number) {
  const v = progress[id]?.current;
  return typeof v === 'number' && Number.isFinite(v) ? Math.max(0, Math.min(target, Math.floor(v))) : 0;
}
export function summary(game: Game, progress: Progress) {
  const all = catalog[game].achievements;
  const unlocked = all.filter(a => count(progress, a.id, a.target) === a.target).length;
  return { unlocked, total: all.length, percent: all.length ? Math.round(unlocked / all.length * 100) : 0 };
}
