-- fc_register.lua —— 在 gamecore 注册 Events.FavorChanged 处理器，记录每次触发的入参
-- 上下文：gamecore

local ok, err = pcall(function()
    if FC_LOG == nil then
        FC_LOG = {}
        FC_HITS = 0
        local function handler(...)
            FC_HITS = FC_HITS + 1
            local cnt = select('#', ...)
            local parts = {}
            for i = 1, cnt do
                local v = select(i, ...)
                parts[#parts + 1] = tostring(v) .. "(" .. type(v) .. ")"
            end
            FC_LOG[FC_HITS] = "HIT#" .. FC_HITS .. "|argcount=" .. cnt
                .. "|args=[" .. table.concat(parts, ", ") .. "]"
        end
        Events.FavorChanged.Add(handler)
        print("FC_REGISTERED=true")
    else
        print("FC_ALREADY_REGISTERED=true|previous_hits=" .. FC_HITS)
    end
    print("FC_EVENT_TYPE=" .. type(Events.FavorChanged))
    local lp = Game.GetLocalPlayer()
    print("FC_LOCAL_PLAYER=" .. tostring(lp))
end)
print("FC_PCALL=" .. tostring(ok) .. "|err=" .. tostring(err))
