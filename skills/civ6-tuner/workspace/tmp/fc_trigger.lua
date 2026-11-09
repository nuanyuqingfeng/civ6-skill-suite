-- fc_trigger.lua —— 给指定玩家加外交支持（触发 FavorChanged）
-- 上下文：gamecore
-- ===== CONFIG =====
local TARGET_PID = 0        -- 0=本地玩家；AI 测试时改成对应玩家 ID
local AMOUNT = -5           -- 增量
-- ===================

local ok, err = pcall(function()
    local pDiplo = Players[TARGET_PID]:GetDiplomacy()
    local before = pDiplo and pDiplo.GetFavor and pDiplo:GetFavor() or "N/A"
    if type(pDiplo) == "table" and pDiplo.ChangeFavor then
        pDiplo:ChangeFavor(AMOUNT)
        print("FC_TRIGGER|pid=" .. TARGET_PID .. "|before=" .. tostring(before)
            .. "|after=" .. tostring(pDiplo:GetFavor()) .. "|hits_before=" .. FC_HITS)
    else
        print("FC_TRIGGER|pid=" .. TARGET_PID .. "|NO_ChangeFavor|type=" .. type(pDiplo))
    end
end)
print("FC_PCALL=" .. tostring(ok) .. "|err=" .. tostring(err))
