-- fc_read.lua —— 读取 FavorChanged 探针命中记录
-- 上下文：gamecore

local ok, err = pcall(function()
    print("FC_HITS_TOTAL=" .. tostring(FC_HITS))
    for i = 1, FC_HITS do
        print("FC_LOG|" .. tostring(FC_LOG[i]))
    end
    if FC_HITS == 0 then
        print("FC_LOG|<no hits>")
    end
end)
print("FC_PCALL=" .. tostring(ok) .. "|err=" .. tostring(err))
