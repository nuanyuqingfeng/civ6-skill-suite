# 表情数据链（A 路线）——优先于所有流程的硬闸门

> 一句话：**官方曲线决定「何时动、动多少」，PSK 形态键 delta 只决定「怎么动」**。两者合成才是表情；缺前者不许降级，缺后者没有通道。本文是领袖模型表情层的唯一默认路径；御三家（Yangyang/Maxiaofang/BaiLian）2026-11 全量实机验证，18 张逐帧权重表与已部署 `.fgx` 逐帧 MAE=0（2026-11-06 回归）。

## 一、A 路线全链（新领袖必走）

```
1. G0 探测      scripts/expr_route_gate.py probe        # 来源指纹 + 路线判定（见 §三）
2. 补导曲线     scripts/unpack_expr_curves.sh            # 无 curves/ 时按 §四 询问协议，不许静默降级
3. 权重表       scripts/morph_curves.py build/verify     # 双实现 MAE=0；E_Close 列保留供 curve_blink 读
4. 拟合表       项目侧 morph_fit（顶点 delta → 面骨刚体增量，acceptance.md §形态键转面骨）
5. 运行时合成   scripts/face_expr_runtime.py             # 长短分层/互补混合/让位/保底/限幅
6. 面骨蒙皮闸门 scripts/face_skin_gate.py（G1/G2/G3）     # 没有蒙皮权重，前面全部白做
7. 逐帧 bake → assemble → cook → 部署 → 实机（十步流程 8.6a–10）
```

## 二、硬规则（违反即任务失败）

| # | 规则 | 出处 |
|---|---|---|
| 1 | **E_Close 绝不进入 morph_fit.pose() 拟合层**：delta 约 1cm、分摊 6 骨，走拟合层 LidUp 只有 0.4 倍行程（半闭）、LidLo 反向（实测 0.659cm vs 应有 1.549cm）。逐帧权重只注入 blink 通道（`face_expr_runtime.curve_blink`） | `blink-and-eyelids.md` §二；御三家 18:36 轮 |
| 2 | **「找不到官方曲线」的严格定义** = curves/*.uecurves.json 不存在，且按 §四 补导链路尝试后仍无「曲线名 ∩ 形态键清单 ∩ 拟合表 bones>0」命中。不许一发现没有就降级 | P0 铁律 3 |
| 3 | **`morph_curves.py --require-source` 默认开**：全部 target 无白名单命中 → `CURVE_SOURCE_EMPTY` 非零退出；部分片段缺曲线（如公共体型动画 Kudos）按 SKIP，属 A2 局部补位，报告记录 | P0 铁律 4 |
| 4 | **帧对齐用实测**：一条 strip = `numFrames-1` 帧（半开区间），边界帧属于下一段；`total > source` 的帧冻结为 NLA HOLD（动作末帧采样 `v[-1]`）。targets 可显式给 `source`（身体动画保持帧） | 2026-11-06 P1 回归修复；`morph-curves.md` §四/§五 |
| 5 | **白名单含 Aa**：VISEMES = Aa/A/E/I/O/U（与御三家逐字对齐）；缺 Aa 会让 Defeat 类片段整列丢元音口型 | 同上 |
| 6 | 结论必须带数字与文件出处；C 级推理不得作为交付依据 | `SKILL.md` §三·五 |

## 三、决策状态机（`scripts/expr_route_gate.py`）

```
G0 probe：曲线来源指纹（文件数/sha8/轨道数）+ 严格命中计数
  ├─ 命中 > 0        → ROUTE A（退出码 0）；A2 局部补位照常执行但必须记录
  └─ 命中 = 0        → NEED_APPROVAL（退出码 10）：打印探测证据 + 三方案
询问答复（decide）：
  ├─ A / A2                                  → 退出码 0（A2 记入报告 A2 清单）
  ├─ B1/B2/B3 且 --approval-verbatim 含该方案号 → APPROVED_B（退出码 12，逐字记录授权）
  ├─ 多选 / 答非所问 / 「你看着办」 / 无原文 / 中断 / 超时 / 工具异常
  │                                          → ABSTAIN（退出码 11）：零写操作，只写闸门日志与报告
  └─ --inject unauthorized-fallback          → ABSTAIN（注入自检：状态机拒绝未授权降级）
```

三方案（询问文本由脚本打印，含各自影响与回退点）：

| 方案 | 内容 | 影响 | 回退点 |
|---|---|---|---|
| B1 | 手工 PRESETS 接管 | 无官方微表情/长闭眼/官方节奏 | 补导曲线后重跑 A 路线整体替换 |
| B2 | 表情层留空 | 实机面部静止 | 同上 |
| B3 | 用户补数据（放入 curves/） | 无 | 即恢复 A 路线 |

**ABSTAIN = 不做**：不写工程文件/动画/权重表、不 cook、不部署、不生成任何降级产物、不补齐、不推测、不留半成品；等待答复期间同样零写操作。

### A2 局部补位边界（照常执行，不必询问，但必须记录）

- 某段无官方曲线（如公共体型动画）→ 该段交回项目人工预置；
- 官方短眨眼脉冲（≤20 帧）→ 交回项目 `blink_plan`，频率/形状不变；
- 整段 `E_Close` 峰值 < 0.05 → 整段交回人工，不强行接管；
- `f > source` 的合成保持段（官方曲线已停更）→ 交回人工，防「瞪眼数秒」；
- 人工层以 `MANUAL_GAIN=0.55` 与曲线互补混合（`1-(1-a)(1-b)`）。

与「需要询问」的分界：**整条来源缺失 / 白名单全空**才触发询问；上面的单段级现象都是 A2。

## 四、报告固定字段（缺项按未验收处理）

```markdown
## 表情数据链
- 曲线来源：<绝对路径>／<文件数>／<每文件 sha8>／<补导命令与时间>
- 路线判定：A ／ A2 ／ B-授权编号 ／ ABSTAIN
- 询问记录：<触发原因>＋<答复原文逐字>＋<判定（退出码）>；未触发写「未触发」
- 未执行项清单：逐条
- E_Close 是否误入拟合层：必须为「否」，附静态检查证据
- curve_blink 分层与限幅：<长闭眼段帧区间/峰值>、<clamp/ensure 触发数>
- G0–G3 结果与注入自检：逐项数值
- 偏差栏：与数值口径的偏离、A2 清单、未做的实机目视复核、未接入通道（Pupil_/元音/29 情绪槽）
```

禁止把「离线全绿」写成「实机正确」；画面判断由用户口述，未口述即记未闭环。

## 五、红旗清单

- 表情整体只有一个固定强度 → 只做了形态键 delta，没接官方曲线（§一第 3/5 步缺一）；
- 闭眼只闭一半 → `E_Close` 走了拟合层（铁律 1），查 `expression_weights` 是否漏剔除；
- 某段一直「瞪眼」→ `f>source` 冻结段没交回人工；
- 多段表逐帧对不上 → 段边界帧用了闭区间或冻结取了 `v[L-1]`（2026-11-06 已修，勿回退）；
- 表生成成功但实机无表情 → 先跑 G1 几何蒙皮，别查曲线（`face-skin-gate.md`）；
- 曲线文件在但命中 0 → 白名单/形态键清单/拟合表三者交集，先跑 `expr_route_gate.py probe` 看指纹。

## 六、接线

- G0 与状态机：`scripts/expr_route_gate.py`
- 补导：`scripts/unpack_expr_curves.sh` + `unpack-expression-curves.md`
- 权重表：`scripts/morph_curves.py`（口径见 `morph-curves.md`）
- 运行时：`scripts/face_expr_runtime.py`
- 蒙皮闸门：`scripts/face_skin_gate.py`（`face-skin-gate.md`）
- 闭眼专文：`blink-and-eyelids.md`
