-- Exercise the real backend against isolated in-memory file/config providers.
local config = {}
local data = {games={botw={partial={current=1,source='automatic'},done={current=2,source='automatic',unlockedAt=42},manual={current=2,source='manual-test'},obsolete={current=99,source='automatic'}}}}
local definitions={botw={achievements={{id='partial',target=2},{id='done',target=2},{id='manual',target=2}}}}
package.preload['millennium']=function() return {assets={read=function(path) if path:match("achievement%-sound") then return {url="test-sound"} end return definitions end},config={get=function(k)return config[k]end,set=function(k,v)config[k]=v;return true end}} end
package.preload['json']=function()return {decode=function(v)return v=='STATE' and data or v end,encode=function(v)return v end} end
package.preload['logger']=function()return {} end
package.preload['utils']=function()return {} end
package.preload['fs']=function()return {} end
local original=io.open
io.open=function(path,mode) if path:match('/state.json$') then return {read=function()return 'STATE'end,close=function()end} end return nil end
dofile('backend/main.lua')
local pending=get_pending_notifications()
assert(#pending==1 and pending[1].key=='local:botw:done' and pending[1].unlockedAt==42)
acknowledge_notification('local:botw:done')
assert(#get_pending_notifications()==0)
-- Reloading the backend retains acknowledgements; unknown and manual IDs never emit.
dofile('backend/main.lua')
assert(#get_pending_notifications()==0)
assert(not pcall(acknowledge_notification,'botw:bogus'))
data.games.botw.partial.current=2
assert(#get_pending_notifications()==1 and get_pending_notifications()[1].key=='local:botw:partial')
-- A second Steam account does not inherit the first account's acknowledgements.
data.steamId='76561198000000001'
assert(#get_pending_notifications()==2)
assert(not pcall(acknowledge_notification,'local:botw:done'))
acknowledge_notification('76561198000000001:botw:done')
assert(#get_pending_notifications()==1)
data.games.botw.partial.source='cloud'
assert(#get_pending_notifications()==0) -- imported historical unlocks stay silent
io.open=original
print('Notification eligibility, acknowledgement, restart and invalid ID checks passed')
