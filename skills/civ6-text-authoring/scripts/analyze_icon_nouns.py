#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze_icon_nouns.py — 官方文本 名词↔Icon 映射表的挖掘、生成与校验

## 这是什么

以本 skill 语料（`reference/zh_corpus.sqlite`，风云变幻有效文本）为唯一数据源，
把官方文本里「[ICON_x] + 空格 + 名词」的实际搭配全部挖出来，生成三份参考表：

  1. `reference/icon_noun_map.tsv`            主表：**原版+风云变幻通用**图标的名词映射
  2. `reference/icon_noun_map_versioned.tsv`  专属表：**仅原版** / **仅风云变幻**可用的图标（多一列「出处」，限制引用）
  3. `reference/icon_noun_map.json`           名词→图标名（与 `civ6-modding/art/iconify_text.py --map` 直接兼容）

两个方向的用法（见 `icon-reference.md` §名词映射）：
  · **名词→Icon（写作）**：给文本补图标引用时，名词对应的图标以表内为准；
    每个名词只有一个官方图标（同名冲突已按语料频次裁决，主表「首选名词」跨图标唯一）。
  · **Icon→名词（校验）**：`--check` 校验文本中图标所配名词必须是表内已有映射，
    不允许给官方图标配一个表外新名词；项目自造图标不在表内，不纳入校验。

## 口径

  · 图标按**基础名**归并：`[ICON_X_LARGE]` / `[ICON_XLarge]` 是 `[ICON_X]` 的大尺寸
    变体；大小写不敏感，规范写法取语料中实际出现最多的大小写形式。
  · 名词 = 图标标记（及其 `[ENDCOLOR]`）之后紧跟的连续汉字串（1–6 字，语料频次 ≥2，
    尾部虚词自动剥离，再经人工黑名单去噪 + 人工增补）。
  · 出处 = 「仅原版」= 只出现在 base+DLC 口径有效文本（不含 EXP1/EXP2）；
    「仅风云变幻」= 出现在风云变幻有效文本但不出现在原版口径。
    判定复用 `export_zh_text.py` 的单遍扫描（本脚本动态加载它，不复制实现）。

## 用法

    python scripts/analyze_icon_nouns.py                      # 重新生成三份参考表（需游戏目录判出处）
    python scripts/analyze_icon_nouns.py --emit-candidates    # 只导出原始挖掘候选（人工去噪用）
    python scripts/analyze_icon_nouns.py --check <文件|目录...>  # 校验工程文本的名词搭配

退出码：0 = 通过；1 = --check 发现问题；2 = 用法/环境错误。
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE = os.path.join(SKILL_ROOT, "reference")
CORPUS = os.path.join(REFERENCE, "zh_corpus.sqlite")
FAMILY = os.path.dirname(SKILL_ROOT)

ICON_TOKEN_RE = re.compile(r"\[ICON_([A-Za-z0-9_]+)\]", re.I)
CN_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
LARGE_SUFFIX_RE = re.compile(r"_?large$", re.I)
TRAIL_PARTICLES = ("以及", "和", "或", "与", "便", "及", "的")

# ---------------------------------------------------------------- 人工校准区
# 图标基础名 → 类别。类别用于主表分栏；「符号」类不配名词，校验时跳过名词检查。
CATEGORY = {
    # 产出
    "Science": "产出", "Culture": "产出", "Faith": "产出", "Gold": "产出",
    "Production": "产出", "Food": "产出", "Tourism": "产出", "Power": "产出",
    "TechBoosted": "产出", "CivicBoosted": "产出",
    # 城市与人口
    "Citizen": "城市", "Housing": "城市", "Amenities": "城市", "Capital": "城市",
    "Governor": "城市", "Turn": "城市", "District": "城市",
    "STAT_GOVERNOR": "城市", "PowerInsufficient": "城市", "PowerRight": "城市",
    # 战斗
    "Strength": "战斗", "Ranged": "战斗", "Bombard": "战斗", "Movement": "战斗",
    "Range": "战斗", "AntiAir": "战斗", "Damaged": "战斗", "Fortified": "战斗",
    "Promotion": "战斗", "Charges": "战斗", "Corps": "战斗", "Army": "战斗",
    "Barbarian": "战斗",
    # 伟人
    "GreatPerson": "伟人", "GreatAdmiral": "伟人", "GreatArtist": "伟人",
    "GreatEngineer": "伟人", "GreatGeneral": "伟人", "GreatMerchant": "伟人",
    "GreatMusician": "伟人", "GreatProphet": "伟人", "GreatScientist": "伟人",
    "GreatWriter": "伟人",
    # 巨作与主题化
    "GreatWork_Relic": "巨作", "GreatWork_Artifact": "巨作",
    "GreatWork_Writing": "巨作", "GreatWork_Music": "巨作",
    "GreatWork_Landscape": "巨作", "GreatWork_Sculpture": "巨作",
    "GreatWork_Portrait": "巨作", "GreatWork_Product": "巨作",
    "GreatWork_Religious": "巨作", "GreatWork_HeroRelic": "巨作",
    "ThemeBonus": "巨作", "ThemeBonus_Active": "巨作",
    # 资源
    "RESOURCE_ANTIQUITY_SITE": "资源", "RESOURCE_SHIPWRECK": "资源",
    "RESOURCE_OIL": "资源", "RESOURCE_COAL": "资源", "RESOURCE_URANIUM": "资源",
    "RESOURCE_ALUMINUM": "资源", "RESOURCE_IRON": "资源", "RESOURCE_NITER": "资源",
    "RESOURCE_HORSES": "资源", "RESOURCE_SALTPETER": "资源",
    "RESOURCE_BANANAS": "资源", "RESOURCE_CINNAMON": "资源", "Resource_Coffee": "资源",
    # 时代与政体
    "GLORY_GOLDEN_AGE": "时代", "GLORY_DARK_AGE": "时代",
    "GLORY_NORMAL_AGE": "时代", "GLORY_SUPER_GOLDEN_AGE": "时代",
    "Policy": "时代", "Government": "时代",
    # 宗教
    "Religion": "宗教", "Missionary": "宗教",
    "PressureDown": "宗教", "PressureUp": "宗教",
    # 外交与议会
    "Favor": "外交", "Envoy": "外交", "STAT_GRIEVANCE": "外交",
    "GRIEVANCE": "外交", "GRIEVANCE_TT": "外交", "VisLimited": "外交",
    "VisOpen": "外交", "VisSecret": "外交", "TradeRoute": "外交",
    "TradingPost": "外交", "InfluencePerTurn": "外交", "Bolt": "外交",
    "Host": "外交", "Lifespan": "其他",
    "Reward_Bronze": "外交", "Reward_Gold": "外交", "Reward_Member": "外交",
    "Reward_None": "外交", "Reward_Silver": "外交", "Reward_Target": "外交",
    # 符号与界面（不配名词，校验时跳过）
    "Bullet": "符号", "BULLETGLOW": "符号", "CheckFail": "符号",
    "CheckSuccess": "符号", "Exclamation": "符号", "War": "符号",
    "Peace": "符号", "DefensivePact": "符号", "ResearchAgreement": "符号",
    "OPENBORDERS": "符号", "DELEGATION": "符号", "EMBASSY": "符号",
    "RESIDENCE": "符号", "ALLIANCE": "符号", "DECLAREWAR": "符号",
    "MADEPEACE": "符号", "TRADEDEAL": "符号", "DENOUNCE": "符号",
    "New": "符号", "Reports": "符号", "Unit": "符号",
}

for _g in ("ALL", "BARBARIAN", "CITY", "CLIMATE", "CULTURE", "DIPLOMACY",
           "DISCOVER", "ESPIONAGE", "GREATPERSON", "MILITARY", "RELIGION",
           "SCIENCE", "SETTLEMENT", "VICTORY"):
    CATEGORY["GOSSIP_" + _g] = "符号"

# 前缀自动归类（大小写不敏感；显式条目优先）。
def category_of(icon: str) -> str:
    cf = icon.casefold()
    if icon in CATEGORY:
        return CATEGORY[icon]
    for pre, cat in (("resource_", "资源"), ("reward_", "外交"),
                     ("gossip_", "符号"), ("greatwork_", "巨作"),
                     ("glory_", "时代")):
        if cf.startswith(pre):
            return cat
    return "其他"

# 符号类图标：后面跟什么名词都合法（列表符、勾叉、感叹等），名词校验直接跳过。
SYMBOL_ICONS = {k for k, v in CATEGORY.items() if v == "符号"}

# 首选名词人工裁决：语料高频串与语义首选不一致时在此指定。
PRIMARY_NOUN = {
    "Religion": "宗教",
}

# 挖掘噪声黑名单：语料里真实出现但不是「图标所配名词」的汉字串。
JUNK_RUNS = {
    # 带虚词/动词的短语（校验由前缀匹配覆盖，无需入表）
    "回合获得", "回合文化值", "回合结束", "回合后可对", "回合后",
    "可获得与其基础", "文化型", "探险家", "远古袭击者", "远古世纪的奇观",
    "当地再生资源提供", "云端游戏", "多人游戏", "已结束游戏", "互联网",
    "加入", "开始", "选项", "全体一致选择选项", "参与议会获得",
    "从外交胜利决议获得", "从奇观", "从积分竞赛获得", "每回合您可获得",
    "您对其他玩家宣战时", "城邦领土成为友方领土",
    "您的建造者单位能改良城邦的单元格", "获得城邦周围", "花费",
    "供电充足时", "驻扎", "用以下方式管理城市", "城市中每个公民所提供的",
    "巨作提供的", "艺术和", "艺术品或来自不同文明的同时代",
    "预言家创建了一个新宗教", "外交能见度比遇到的其他文明高",
    "贸易路线可从目的地的每个奢侈品资源", "贸易路线途径此处",
    "贸易路线处获得的", "贸易路线提供的", "贸易路线将使您途经或进入城市的",
    "伟人们独领风骚", "伟人已来到我们的文明中施展才华", "伟人的文明",
    "伟人时", "战斗力将得到提升", "战斗力相同的", "战斗加成",
    "生产力来自相邻", "生产力加成延伸到", "生产力的产出", "生产力并",
    "生产力最低的建筑", "生产力加成减半", "生产力花费最低的市中心建筑",
    "生产力来自相邻山脉", "金币便", "金币或", "金币来自相邻", "金币便减少",
    "金币每", "金币数量为", "金币数", "金币减半", "金币奖励", "金币收入",
    "黄金购买建造者和开拓者的费用降低", "信仰值购买",
    "信仰值和", "信仰值来自相邻山脉", "信仰值来自相邻", "信仰值加成",
    "信仰值获得", "信仰值便", "信仰值或", "信仰值来生产陆地战斗单位",
    "信仰值的文明", "信仰值与",
    "文化值和", "文化值加成", "文化值与", "文化值来自相邻",
    "文化值来自相邻自然奇观棉花堡", "文化值产量相等的", "文化发展",
    "文化值的文明", "文化值便", "文化值的来源", "文化值增长",
    "科技值和", "科技值加成", "科技值来自相邻山脉", "科技值来自相邻",
    "科技值产出", "科技值与", "科技值相邻加成也可提供", "科技值低的文明",
    "科技值或", "科技值提升",
    "旅游业绩的文明", "旅游业绩和", "旅游业绩的产出", "旅游业绩加成",
    "食物和", "食物或", "食物来自相邻沙漠", "食物来自相邻沙漠丘陵", "剩余食物",
    "宜居度与", "宜居度并", "宜居度也有着需求", "宜居度的来源之一是奢侈品资源",
    "宜居度加成延伸到", "宜居度额外", "宜居度和",
    "人口的城市", "公民每回合施加", "公民每回合可带来", "人口大于等于",
    "公民的忠诚度", "公民的压力", "公民输出",
    "首都就职时", "首都城市", "首都所在大陆上时", "首都所在大陆上", "首都旁边的",
    "住房数量", "住房加成", "住房上限低", "住房和", "住房与",
    "尤里卡和", "尤里卡额外提供", "尤里卡提供科技的所有",
    "鼓舞来迈向科技胜利", "鼓舞时刻获得中世纪或文艺复兴时期", "鼓舞额外提供",
    "鼓舞提供", "外交能见度则上升", "外交能见度提高",
    "总督的城市", "总督派驻此处", "总督特色改良设施", "总督升级",
    "总督可防止出现此类状况", "总督就职后将提供",
    "总督和幸福度等级则是影响城市每回合忠诚度的其他重要因素",
    "贸易站将使您途经或进入城市的", "贸易站时", "贸易站能扩大贸易网络",
    "贸易站将出现在城市中", "贸易站的任意城市中", "贸易路线而", "贸易路线获得",
    "贸易路线后", "贸易路线提供", "路线提供的", "贸易路线为埃", "路线提供",
    "首都旁边", "文物时", "遗物中获得", "生产力的文明", "战斗力相同",
    "金币加成", "生产力加成",
    "远程攻击力的陆地单位也可以攻击区域", "远程攻击机会", "远程攻击力数值",
    "射程数据决定了单位能够发动一个远程攻击的距离",
    "射程意味着目标能位于一个相邻单元格或一个单元格那么远",
    "射程意味着目标肯定与攻击者相邻", "射程为",
    "大艺术家和", "大艺术家与", "大艺术家点数便", "大艺术家都能产生一个",
    "大预言家可在巨石阵", "大预言家后", "大预言家点数建造圣地并创立宗教",
    "大音乐家点数便", "大音乐家提供", "大音乐家和", "大音乐家都能产生一个",
    "海军统帅点数便", "海军统帅后", "海军统帅首次率军击溃敌方单位",
    "大将军首次率军击溃敌方单位", "海军统帅和", "大将军点数便",
    "大将军都有特色能力", "大科学家点数便", "大科学家时将随机获得", "大科学家与",
    "大作家都能产生一个", "大工程师点数便", "大工程师点数与",
    "大工程师都会拥有特色能力", "大商人点数便", "大商人都会拥有特色能力",
    "伟人点数提供", "伟人点数上",
    "宗教的所有单位", "宗教力量", "宗教战斗力加成",
    "遗物和", "遗物中获得的", "遗物巨作槽位", "遗物能产出", "遗物和圣城的",
    "著作巨作中获得的所有", "著作巨作槽位", "英雄遗物能产出", "英雄遗物提供的",
    "雕塑艺术巨作中获得", "音乐可通过", "音乐巨作", "文物以及",
    "石油自动转换为", "石油资源", "石油的海岸或湖泊单元格上", "石油的陆地单元格上",
    "石油和", "铀矿资源", "铀资源", "铀自动转换为", "铀之类的资源",
    "煤自动转换为", "煤每回合额外产出", "铁每回合额外产出", "铁和", "铁资源",
    "铝与", "铝才能开始建造", "铝资源", "肉桂和",
    "不满降低", "不满不会下降", "不满增加", "不满记录", "不满来自",
    "使者去动摇它的忠诚度", "使者将使成员每回合的", "使者数量加倍",
    "使者派遣至城邦后", "使者点数加成", "使者从目标城邦中赶走",
    "使者数量每回合获得", "使者将视为", "使者点数",
    "黄金时代或英雄时代时", "黄金时代中时", "黄金时代的单位作战时",
    "黄金时代的临界值", "黄金时代的文明作战", "黑暗时代的临界值",
    "轰炸攻击力和", "炮击攻击力是单位的反区域战斗力",
    "炮击攻击力的单位也可以攻击其他单位", "炮击和",
    "防空战斗力将判定和来袭飞机进行战斗的结果", "对空防御力增至",
    "基础战斗力额外", "移动力消耗", "移动力减益", "移动力为", "移动力加成",
    "移动力允许", "移动力提供", "电力来强化该城市", "电力的专用改良设施",
    "电力负荷的建筑或项目效力已暂时降低", "电力的建筑正全力运行",
    "电力的", "电力与", "电力相关的建筑", "历史古迹发现和挖掘", "历史古迹资源",
}

# 人工增补：官方亦用、但语料频次不足 2 或属于 iconify 关键词习惯说法的名词。
# 键 = 图标基础名，值 = 额外名词列表（写入白名单与 JSON 映射）。
EXTRA_NOUNS = {
    "Food": ["粮食"],
    "Barbarian": ["蛮族"],
    "Charges": ["使用次数", "劳动力"],
    "Damaged": ["受伤", "生命值"],
    "Fortified": ["防御", "驻扎"],
    "Promotion": ["晋升"],
    "Corps": ["军团", "舰队"],
    "Army": ["军队", "无敌舰队"],
    "GreatWork_Relic": ["遗物"],
    "GreatWork_HeroRelic": ["英雄遗物"],
    "RESOURCE_ANTIQUITY_SITE": ["历史古迹"],
    "RESOURCE_SHIPWRECK": ["海难遗址"],
    "Policy": ["政策"],
    "Government": ["政体"],
    "Missionary": ["传教士"],
}

# JSON 映射（iconify --map）里排除的名词：语义太泛或单字，自动插入会误伤。
# 它们仍留在 TSV 白名单里（官方确实这么写），只是不作为「批量补图标」的关键词。
JSON_EXCLUDE_NOUNS = {
    "回合", "范围", "选项", "首都", "政策", "政体", "宗教", "不满", "人口",
    "公民", "伟人", "驻扎", "防御", "电力", "粮食", "蛮族", "黄金", "风景",
    "音乐", "雕塑", "肖像", "著作", "寿命", "香蕉", "咖啡", "肉桂", "铁",
    "煤", "铀", "铝", "石油", "总督",
}

# ---------------------------------------------------------------- 工具函数


def norm_icon(name: str) -> tuple[str, str]:
    """→ (基础名, LARGE标记)。`[ICON_X_LARGE]` 与 `[ICON_XLarge]` 都归并到 `[ICON_X]`。"""
    large = ""
    m = LARGE_SUFFIX_RE.search(name)
    if m:
        large = "LARGE"
        name = name[: m.start()]
    return name, large


def canonical_case(counter: Counter) -> dict[str, str]:
    """casefold → 出现频次最高的大小写形式（规范写法）。"""
    out: dict[str, str] = {}
    for name, n in counter.items():
        base, _ = norm_icon(name)
        cf = base.casefold()
        if cf not in out or n > counter[out[cf]]:
            out[cf] = base
    return out


def strip_particles(run: str) -> str:
    for p in TRAIL_PARTICLES:
        while run.endswith(p) and len(run) > len(p):
            run = run[: -len(p)]
    return run


def mine_icons(texts) -> tuple[Counter, dict[str, Counter]]:
    """扫描文本 → (图标原始名频次, {基础名: 后续名词串频次（含 LARGE 归并）})。"""
    icon_freq: Counter = Counter()
    runs: dict[str, Counter] = defaultdict(Counter)
    for t in texts:
        if not t or "TRANSLATION MISSING" in t:
            continue
        for m in ICON_TOKEN_RE.finditer(t):
            icon_freq[m.group(1)] += 1
            base, _large = norm_icon(m.group(1))
            rest = t[m.end():].lstrip()
            if rest.startswith("[ENDCOLOR]"):
                rest = rest[len("[ENDCOLOR]"):].lstrip()
            r = CN_RUN_RE.match(rest)
            if r:
                runs[base][r.group(0)] += 1
    return icon_freq, runs


def load_gs_texts():
    """GS 有效文本 = 语料库全表（已是 EXP2 口径）。"""
    import sqlite3
    con = sqlite3.connect("file:%s?mode=ro" % CORPUS.replace("\\", "/"), uri=True)
    texts = [r[0] for r in con.execute("SELECT Text FROM LocalizedText")]
    con.close()
    return texts


def load_vanilla_texts():
    """原版口径有效文本：复用 export_zh_text 的单遍扫描，剔除 Expansion1/Expansion2。"""
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    cand = os.path.join(FAMILY, "civ6-modding")
    if not os.path.isdir(cand):
        print("WARN 找不到 civ6-modding，跳过原版口径判定", file=sys.stderr)
        return None
    sys.path.insert(0, os.path.join(cand, "tools"))
    spec = importlib.util.spec_from_file_location(
        "build_localization", os.path.join(cand, "database", "scripts", "build_localization.py"))
    BL = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(BL)
    spec2 = importlib.util.spec_from_file_location(
        "export_zh_text", os.path.join(SKILL_ROOT, "scripts", "export_zh_text.py"))
    EZ = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(EZ)
    game = EZ._game_root(BL, None)
    if not game or not os.path.isdir(game):
        print("WARN 找不到游戏目录，跳过原版口径判定", file=sys.stderr)
        return None
    seg = BL.Segment(game)

    class _VanillaSeg:
        base_text_root = seg.base_text_root
        dlc_root = seg.dlc_root

        def disk_files(self, cls):
            return [(d, r, p) for (d, r, p) in seg.disk_files(cls)
                    if d not in ("Expansion1", "Expansion2")]

        def file_path(self, dlc, rel):
            return seg.file_path(dlc, rel)

        def tier_of(self, dlc):
            return seg.tier_of(dlc)

    state, _tomb, _stat = EZ.effective_zh(BL, _VanillaSeg(), "main")
    return [v[0] for v in state.values()]


# ---------------------------------------------------------------- 白名单构建


def build_noun_index(runs, canon: dict[str, str]):
    """挖掘结果 → (icon→{名词: 频次}, 名词→{icon: 频次}, 冲突列表)。"""
    icon_nouns: dict[str, dict[str, int]] = defaultdict(dict)
    sym = {s.casefold() for s in SYMBOL_ICONS}
    for base, c in runs.items():
        key = canon.get(base.casefold(), base)
        if key.casefold() in sym:
            continue  # 符号类不收集名词
        for run, n in c.items():
            run = strip_particles(run)
            if not run or len(run) > 6 or n < 2 or run in JUNK_RUNS:
                continue
            icon_nouns[key][run] = max(n, icon_nouns[key].get(run, 0))
    for extra_icon, extras in EXTRA_NOUNS.items():
        key = canon.get(extra_icon.casefold(), extra_icon)
        for w in extras:
            icon_nouns[key].setdefault(w, 0)
    noun_index: dict[str, dict[str, int]] = defaultdict(dict)
    for icon, nouns in icon_nouns.items():
        for w, n in nouns.items():
            noun_index[w][icon] = n
    conflicts = []
    for w, icons in noun_index.items():
        if len(icons) > 1:
            best = max(icons.items(), key=lambda kv: kv[1])[0]
            conflicts.append((w, dict(icons), best))
    return icon_nouns, noun_index, conflicts


def primary_of(icon: str, nouns: dict[str, int]) -> str:
    if icon in PRIMARY_NOUN:
        return PRIMARY_NOUN[icon]
    return max(nouns.items(), key=lambda kv: kv[1])[0] if nouns else ""


def display_nouns(icon: str, nouns: dict[str, int]) -> tuple[str, str]:
    """→ (首选名词, 别名串)。别名 = 非前缀扩展词；高频(≥10)的官方复合词保留展示。"""
    if not nouns:
        return "", ""
    primary = primary_of(icon, nouns)
    alts = []
    for w, n in nouns.items():
        if w == primary:
            continue
        if n < 10 and any(w != o and w.startswith(o) and nouns[o] > n
                          for o in nouns):
            continue
        alts.append(w)
    return primary, "、".join(sorted(alts, key=lambda x: -nouns[x]))


# ---------------------------------------------------------------- 生成参考表


def write_tsv_main(path, icon_nouns, canon, avail):
    sym = {s.casefold() for s in SYMBOL_ICONS}
    rows = []
    for base_cf, disp in sorted(canon.items(), key=lambda kv: kv[1].casefold()):
        if base_cf in avail["vanilla_only"] or base_cf in avail["gs_only"]:
            continue  # 版本专属 → 专属表
        nouns = icon_nouns.get(disp, {})
        variants = "、".join(avail["large"].get(base_cf, []))
        cat = category_of(disp)
        if cat == "符号" or not nouns or disp.casefold() in sym:
            primary, alts = "", ""
        else:
            primary, alts = display_nouns(disp, nouns)
        rows.append((disp, cat, primary, alts,
                     str(sum(nouns.values())) if nouns else "0", variants))
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("# 官方文本 名词↔Icon 主表（原版+风云变幻通用图标）\n")
        f.write("# 数据源：reference/zh_corpus.sqlite（风云变幻有效 zh 文本）；"
                "由 scripts/analyze_icon_nouns.py 生成\n")
        f.write("# 用法：名词→图标按「首选名词」查（唯一指向，另见同名 .json）；"
                "「别名名词」为官方亦用的其他说法\n")
        f.write("# 名词校验（图标后接的名词必须在表内）用 "
                "python scripts/analyze_icon_nouns.py --check <工程文本>\n")
        f.write("# 首选名词为空的图标：官方文本中不与名词连用（符号类，或前置式使用）\n")
        f.write("图标\t类别\t首选名词\t别名名词\t语料搭配频次\t尺寸变体\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    return len(rows)


def write_tsv_versioned(path, icon_nouns, canon, avail, van_nouns):
    n_van = n_gs = 0
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("# 官方文本 版本专属图标表（主表之外的图标，限制引用）\n")
        f.write("# 出处=仅原版：只出现在原版口径文本；风云变幻环境已无对应内容，工程**禁止**引用\n")
        f.write("# 出处=仅风云变幻：风云变幻新增；目标环境为风云变幻时可正常引用，"
                "面向纯原版环境则不可引用\n")
        f.write("图标\t出处\t类别\t语料搭配名词\t语料搭配频次\t尺寸变体\n")
        for base_cf, disp in sorted(canon.items(), key=lambda kv: kv[1].casefold()):
            variants = "、".join(avail["large"].get(base_cf, []))
            cat = category_of(disp)
            if base_cf in avail["vanilla_only"]:
                nouns = van_nouns.get(disp, {})
                primary, alts = display_nouns(disp, nouns) if nouns else ("", "")
                f.write("%s\t仅原版\t%s\t%s\t%s\t%s\n" % (
                    disp, cat, primary + (("、" + alts) if alts else ""),
                    sum(nouns.values()) if nouns else "0", variants))
                n_van += 1
            elif base_cf in avail["gs_only"]:
                nouns = icon_nouns.get(disp, {})
                primary, alts = display_nouns(disp, nouns) if nouns else ("", "")
                f.write("%s\t仅风云变幻\t%s\t%s\t%s\t%s\n" % (
                    disp, cat, primary + (("、" + alts) if alts else ""),
                    sum(nouns.values()) if nouns else "0", variants))
                n_gs += 1
    return n_van, n_gs


def write_json(path, noun_index):
    """名词→图标名，兼容 iconify_text.py --map（键=名词，值=不带前缀图标名）。"""
    mapping = {}
    for w, icons in sorted(noun_index.items()):
        if w in JSON_EXCLUDE_NOUNS or len(w) == 1:
            continue
        best_icon, _ = max(icons.items(), key=lambda kv: kv[1])
        mapping[w] = best_icon
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    return len(mapping)


# ---------------------------------------------------------------- 校验


def load_whitelist():
    """从生成的 TSV 重建 {图标基础名(casefold): 名词集合} 与版本信息。"""
    wl: dict[str, set] = defaultdict(set)
    versioned: dict[str, str] = {}  # casefold 图标 → 出处
    main = os.path.join(REFERENCE, "icon_noun_map.tsv")
    ver = os.path.join(REFERENCE, "icon_noun_map_versioned.tsv")
    for path, is_ver in ((main, False), (ver, True)):
        if not os.path.isfile(path):
            continue
        for line in open(path, encoding="utf-8"):
            if line.startswith("#") or line.startswith("图标\t"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 4:
                continue
            icon = cols[0].casefold()
            if is_ver and len(cols) >= 2 and cols[1]:
                versioned[icon] = cols[1]
            nouns = (cols[2] if len(cols) > 2 else "")
            if len(cols) > 3:
                nouns += "、" + cols[3]
            for w in filter(None, nouns.split("、")):
                wl[icon].add(w)
    return wl, versioned


def check_paths(paths, wl, versioned) -> int:
    sym = {s.casefold() for s in SYMBOL_ICONS}
    files: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            for pat in ("**/*.sql", "**/*.xml"):
                files += glob.glob(os.path.join(p, pat), recursive=True)
        else:
            files.append(p)
    issues = 0
    for fp in sorted(set(files)):
        try:
            content = open(fp, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            continue
        for m in ICON_TOKEN_RE.finditer(content):
            base, _large = norm_icon(m.group(1))
            cf = base.casefold()
            rest = content[m.end():].lstrip()
            if rest.startswith("[ENDCOLOR]"):
                rest = rest[len("[ENDCOLOR]"):].lstrip()
            r = CN_RUN_RE.match(rest)
            if not r:
                continue
            run = r.group(0)
            if cf in sym or cf not in wl:
                continue  # 符号类或表外（含项目自造）图标：不校验名词
            if versioned.get(cf) == "仅原版":
                print("FAIL %s: [ICON_%s] 为仅原版图标（风云变幻环境已无对应内容），不应引用"
                      % (fp, base))
                issues += 1
                continue
            # 名词 = 运行串的最长表内前缀；若名词写在图标前（官方顺序的反例）单独报
            hit = next((w for w in sorted(wl[cf], key=len, reverse=True)
                        if run.startswith(w)), None)
            if hit is not None:
                continue
            pre = content[: m.start()].rstrip()
            if pre.endswith("[ENDCOLOR]"):
                pre = pre[: -len("[ENDCOLOR]")].rstrip()
            pb = re.search(r"[\u4e00-\u9fff]+$", pre)
            if pb and any(pb.group(0).endswith(w) for w in wl[cf]):
                print("FAIL %s: [ICON_%s] 名词「%s」写在图标前——官方顺序为"
                      "「数值+空格+[ICON_x]+空格+名词」" % (fp, base, pb.group(0)[-8:]))
                issues += 1
                continue
            print("FAIL %s: [ICON_%s] 后接名词「%s」不在官方映射表内（允许：%s）"
                  % (fp, base, run[:8], "、".join(sorted(wl[cf]))))
            issues += 1
    print("校验完成：%d 个文件，%d 处名词搭配问题" % (len(set(files)), issues))
    return 1 if issues else 0


# ---------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description="官方文本 名词↔Icon 映射：生成与校验")
    ap.add_argument("--emit-candidates", action="store_true",
                    help="只导出原始挖掘候选（人工去噪用），不写正式表")
    ap.add_argument("--check", dest="check", nargs="+", metavar="路径",
                    help="校验工程文本：图标所配名词必须为表内已有映射")
    ap.add_argument("--out", default=REFERENCE)
    args = ap.parse_args()

    if args.check:
        wl, versioned = load_whitelist()
        if not wl:
            print("ERROR 找不到参考表，请先运行本脚本生成", file=sys.stderr)
            return 2
        return check_paths(args.check, wl, versioned)

    if not os.path.isfile(CORPUS):
        print("ERROR 缺少 %s" % CORPUS, file=sys.stderr)
        return 2

    gs_freq, gs_runs = mine_icons(load_gs_texts())
    canon = canonical_case(gs_freq)
    icon_nouns, noun_index, conflicts = build_noun_index(gs_runs, canon)

    if args.emit_candidates:
        out = os.path.join(args.out, "icon_noun_candidates.txt")
        with open(out, "w", encoding="utf-8") as f:
            for disp in sorted(canon.values(), key=str.casefold):
                nouns = icon_nouns.get(disp, {})
                f.write("== %s（%s）==\n" % (disp, category_of(disp)))
                for w, n in sorted(nouns.items(), key=lambda kv: (-kv[1], kv[0])):
                    f.write("  %s\t%d\n" % (w, n))
        print("候选已写出：%s（%d 个图标）" % (out, len(canon)))
        for w, icons, best in sorted(conflicts):
            print("名词冲突（裁决 %s）: %s ← %s" % (
                best, w, ", ".join("%s:%d" % kv for kv in sorted(icons.items()))))
        return 0

    # 出处判定：原版口径
    van_texts = load_vanilla_texts()
    van_nouns: dict[str, dict] = {}
    if van_texts is None:
        avail = {"vanilla_only": set(), "gs_only": set(), "large": {}}
        print("WARN 无原版口径数据，所有图标按「通用」处理")
    else:
        van_freq, van_runs = mine_icons(van_texts)
        van_icon_nouns, _, _ = build_noun_index(van_runs, canon)
        van_nouns = van_icon_nouns
        van_bases = {b.casefold() for b in van_freq}
        gs_bases = {b.casefold() for b in gs_freq}
        large_variants: dict[str, set] = defaultdict(set)
        for name in gs_freq:
            base, large = norm_icon(name)
            if large:
                large_variants[base.casefold()].add(base)
        avail = {"vanilla_only": van_bases - gs_bases,
                 "gs_only": gs_bases - van_bases,
                 "large": large_variants}

    os.makedirs(args.out, exist_ok=True)
    n1 = write_tsv_main(os.path.join(args.out, "icon_noun_map.tsv"),
                        icon_nouns, canon, avail)
    n_van, n_gs = write_tsv_versioned(
        os.path.join(args.out, "icon_noun_map_versioned.tsv"),
        icon_nouns, canon, avail, van_nouns)
    n3 = write_json(os.path.join(args.out, "icon_noun_map.json"), noun_index)
    print("主表：%d 个通用图标；专属表：仅原版 %d / 仅风云变幻 %d；JSON 名词映射：%d 条"
          % (n1, n_van, n_gs, n3))
    for w, icons, best in sorted(conflicts):
        print("名词冲突（已按频次裁决为 %s）: %s ← %s" % (
            best, w, ", ".join("%s:%d" % kv for kv in sorted(icons.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
