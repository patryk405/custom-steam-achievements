local millennium = require('millennium')
local json = require('json')
local logger = require('logger')
local fs = require('fs')
local utils = require('utils')
local data_dir = (os.getenv('XDG_DATA_HOME') or (os.getenv('HOME') .. '/.local/share')) .. '/custom-achievements'
local function read_json_file(path)
    local file = io.open(path, 'rb')
    if not file then return {} end
    local text = file:read(2000001); file:close()
    if #text > 2000000 then return {} end
    local ok, value = pcall(json.decode, text)
    return ok and type(value) == 'table' and value or {}
end
local function preferences()
    local value = read_json_file(data_dir .. '/preferences.json')
    return {iconMode = 'original', autoEnabled = value.autoEnabled ~= false}
end
local catalog
local function definitions()
    if not catalog then catalog = json.decode(millennium.assets.read('resources/catalog.json')) end
    return catalog
end
local function check_game(game)
    if type(game) ~= 'string' or not definitions()[game] then error('Unknown game') end
end
local function state(game)
    check_game(game)
    local account = read_json_file(data_dir .. '/state.json').steamId or 'local'
    local value = millennium.config.get('test_progress_' .. account .. '_' .. game)
    return type(value) == 'table' and value or {}
end
---@ffi
---@param game string
---@return string
function get_state(game)
    local hint = read_json_file(data_dir .. '/steam-account.json')
    local active = read_json_file(data_dir .. '/state.json').steamId
    if hint.at and os.time() - hint.at < 30 and hint.steamId ~= active then return '{}' end
    local result = state(game)
    do
        local automatic = read_json_file(data_dir .. '/state.json')
        for id, value in pairs((automatic.games or {})[game] or {}) do
            if type(value) == 'table' and type(value.current) == 'number' and (not result[id] or value.current >= (result[id].current or 0)) then result[id] = value end
        end
    end
    return json.encode(result)
end
---@ffi
---@param game string
---@param id string
---@param current number
---@return string
function set_test_progress(game, id, current)
    check_game(game)
    local target
    for _, a in ipairs(definitions()[game].achievements) do
        if a.id == id then target = a.target end
    end
    if not target or type(current) ~= 'number' or current ~= current or current < 0 or current > target or current % 1 ~= 0 then
        error('Invalid achievement progress')
    end
    local data = state(game)
    local previous = data[id]
    data[id] = { current = current, source = 'manual-test', unlockedAt = current == target and (previous and previous.unlockedAt or os.time()) or nil }
    local ok, err = millennium.config.set('test_progress_' .. (read_json_file(data_dir .. '/state.json').steamId or 'local') .. '_' .. game, data)
    if not ok then error(err or 'Could not save progress') end
    return json.encode(data)
end
---@ffi
---@param game string
---@return string
function reset_test_progress(game)
    check_game(game)
    local ok, err = millennium.config.delete('test_progress_' .. (read_json_file(data_dir .. '/state.json').steamId or 'local') .. '_' .. game)
    if not ok then error(err or 'Could not reset progress') end
    return '{}'
end

---@ffi
---@param steam_id string
---@return boolean
function set_active_steam_account(steam_id)
    if steam_id ~= '' and (not steam_id:match('^7656119%d+$') or #steam_id ~= 17) then error('Invalid Steam ID') end
    fs.create_directories(data_dir)
    local path = data_dir .. '/steam-account.json'
    local file = assert(io.open(path .. '.tmp','wb'))
    file:write(json.encode({steamId=steam_id,at=os.time()}));file:close();assert(os.rename(path .. '.tmp',path))
    return true
end
---@ffi
---@param action string
---@return boolean
function cloud_action(action)
    if action ~= 'connect' and action ~= 'disconnect' then error('Invalid cloud action') end
    local account = read_json_file(data_dir .. '/state.json').steamId
    if not account then error('Waiting for Steam account') end
    local path = data_dir .. '/cloud-command.json'
    local file = assert(io.open(path .. '.tmp','wb'))
    file:write(json.encode({action=action,steamId=account}));file:close();assert(os.rename(path .. '.tmp',path))
    return true
end

---@ffi
---@return string
function get_settings()
    local value = preferences()
    local automatic = read_json_file(data_dir .. '/state.json')
    value.status = automatic.status or {}
    value.updatedAt = automatic.updatedAt
    value.cloud = read_json_file(data_dir .. '/cloud-status.json')
    value.steamId = automatic.steamId
    return json.encode(value)
end
---@ffi
---@param icon_mode string
---@param auto_enabled boolean
---@return string
function set_preferences(icon_mode, auto_enabled)
    if (icon_mode ~= 'original' and icon_mode ~= 'community') or type(auto_enabled) ~= 'boolean' then error('Invalid preferences') end
    fs.create_directories(data_dir)
    local path = data_dir .. '/preferences.json'
    local file = assert(io.open(path .. '.tmp', 'wb'))
    assert(file:write(json.encode({iconMode = 'original', autoEnabled = auto_enabled})))
    assert(file:close())
    assert(os.rename(path .. '.tmp', path))
    return get_settings()
end
---@ffi
---@return string
function get_pending_notifications()
    local automatic = read_json_file(data_dir .. '/state.json')
    local shown = millennium.config.get('shown_notifications') or {}
    local pending = {}
    for game, def in pairs(definitions()) do
        for _, a in ipairs(def.achievements) do
            local value = ((automatic.games or {})[game] or {})[a.id]
            local key = (automatic.steamId or 'local') .. ':' .. game .. ':' .. a.id
            local legacy = read_json_file(data_dir .. '/legacy-owner.json').steamId == automatic.steamId and shown[game .. ':' .. a.id]
            if value and value.source == 'automatic' and type(value.current) == 'number' and value.current >= a.target and not shown[key] and not legacy then
                table.insert(pending, {key = key, game = game, id = a.id, unlockedAt = value.unlockedAt or os.time()})
            end
        end
    end
    return json.encode(pending)
end
---@ffi
---@param key string
---@return boolean
function acknowledge_notification(key)
    local valid = false
    local account = read_json_file(data_dir .. '/state.json').steamId or 'local'
    for game, def in pairs(definitions()) do
        for _, a in ipairs(def.achievements) do if key == account .. ':' .. game .. ':' .. a.id then valid = true end end
    end
    if not valid then error('Unknown achievement') end
    local shown = millennium.config.get('shown_notifications') or {}
    shown[key] = true
    local ok, err = millennium.config.set('shown_notifications', shown)
    if not ok then error(err or 'Could not acknowledge notification') end
    return true
end
---@ffi
---@return boolean
function play_achievement_sound()
    fs.create_directories(data_dir)
    local spec = json.decode(millennium.assets.read('resources/achievement-sound.json'))
    local encoded = assert(spec.url:match('^data:audio/wav;base64,(.+)$'))
    local path = data_dir .. '/achievement.wav'
    local file = assert(io.open(path, 'wb'))
    assert(file:write(utils.base64_decode(encoded))); assert(file:close())
    local queue = data_dir .. '/audio-queue'
    fs.create_directories(queue)
    local request = queue .. '/' .. tostring(os.time()) .. '-' .. tostring(math.random(100000, 999999)) .. '.json'
    local pending = assert(io.open(request .. '.tmp', 'wb'))
    assert(pending:write('{}')); assert(pending:close())
    assert(os.rename(request .. '.tmp', request))
    return true
end
return {
    on_load = function() logger:info('Custom Achievements prototype loaded'); millennium.ready() end,
    patches = {
        {
            file = [[sp\.js]],
            find = [[it\.has\("achievements"\)&&\(0,e\.jsx\)\(n\.tH,\{children:\(0,e\.jsx\)\(je,\{name:"achievements",parent:Ve,children:\(0,e\.jsx\)\(D\.tm,\{details:ke\}\)\}\)\}\)]],
            transforms = {
                {
                    match = [[it\.has\("achievements"\)]],
                    replace = [[(0,e.jsx)(#{{self}}?.AchievementPanel||(()=>null),{details:ke,overview:nt}),it.has("achievements")]]
                }
            }
        }
    }
}
