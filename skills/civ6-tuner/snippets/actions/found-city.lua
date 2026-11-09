-- found-city.lua —— 用开拓者发起建城（ingame 上下文）
-- 用法：python tuner_exec.py act found-city
--       python tuner_exec.py act found-city --pid 2
--
-- 参数
--   PID  玩家编号，-1 表示本地玩家
--
-- 前置断言
--   Players[pid] 存在；含 UNIT_SETTLER；UnitManager.RequestOperation 为 function；
--   UnitOperationTypes.FOUND_CITY 可用
--
-- 执行步骤
--   1. 在玩家单位里找第一支 UNIT_SETTLER
--   2. 以该单位所在地块为参数发 UnitOperationTypes.FOUND_CITY
--   3. 打点说明队列已发起（结算是异步的，城市是否出现由后续 snapshot 复核）
--
-- 成功判据
--   输出 FOUND_CITY_REQUESTED；FINAL=OK
--
-- 失败码
--   1 参数错误 2 Lua 报错 3 超时 4 连接断开
--
-- 已知限制
--   1. 建城是异步结算：本动作只保证请求已发出，不等城市落地；后续用 snapshot 轮询 city_count
--   2. 只处理第一支开拓者，不校验建城地块是否合法（由引擎裁决）

-- ===== CONFIG =====
local CONFIG = {
    PID = -1,  -- 玩家编号，-1 表示本地玩家
}
-- ===================

local function S(v) if v == nil then return "nil" end return tostring(v) end

print("=== FOUND-CITY START ===")

if CONFIG.PID < 0 then CONFIG.PID = Game.GetLocalPlayer() end
local pPlayer = Players[CONFIG.PID]
if pPlayer == nil then
    print("ASSERTION_FAIL|player_missing|pid=" .. S(CONFIG.PID))
    print("FINAL=FAIL|player_missing")
    return
end
print("ASSERTION_OK|player_exist|pid=" .. S(CONFIG.PID))

local settler = nil
for _, u in pPlayer:GetUnits():Members() do
    if GameInfo.Units[u:GetType()].UnitType == "UNIT_SETTLER" then
        settler = u
        break
    end
end
if settler == nil then
    print("ASSERTION_FAIL|no_settler")
    print("FINAL=FAIL|no_settler")
    return
end
print("ASSERTION_OK|settler|id=" .. S(settler:GetID()))

local t = {}
t[UnitOperationTypes.PARAM_X] = settler:GetX()
t[UnitOperationTypes.PARAM_Y] = settler:GetY()
UnitManager.RequestOperation(settler, UnitOperationTypes.FOUND_CITY, t)
print("FOUND_CITY_REQUESTED|at=" .. S(settler:GetX()) .. "," .. S(settler:GetY()))

print("FINAL=OK")
print("=== FOUND-CITY COMPLETE ===")
