import argparse
import math
import re
import statistics
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DUMP_DIR = WORKSPACE / "tmp" / "denia_vs_jinhsi"
REPORT_PATH = WORKSPACE / "gen" / "reports" / "pose_consistency.md"

CORE_CHAIN = ("Root", "Bip001", "Bip001Pelvis", "Bip001Spine", "Bip001Head")
LIMIT_CORE = 15.0
LIMIT_ANY = 45.0
LIMIT_ROOT = 1.0

ROW_PATTERN = re.compile(
    r"^ROW (.+?)"
    r" \| rest_p=(-?\d+(?:\.\d+)?(?:,-?\d+(?:\.\d+)?){2})"
    r" \| rest_q=(-?\d+(?:\.\d+)?(?:,-?\d+(?:\.\d+)?){3})"
    r"(?: \| cur_p=(-?\d+(?:\.\d+)?(?:,-?\d+(?:\.\d+)?){2}|none)"
    r" \| cur_q=(-?\d+(?:\.\d+)?(?:,-?\d+(?:\.\d+)?){3}|none))?$"
)

SAMPLES = (
    {
        "key": "denia",
        "label": "达妮娅（同引擎正常样本，正样本基线）",
        "dump": DUMP_DIR / "calib_denia.txt",
    },
    {
        "key": "jinhsi",
        "label": "今汐（当前部署资产）",
        "dump": DUMP_DIR / "calib_jinhsi.txt",
    },
)


def parse_vector(text):
    return [float(value) for value in text.split(",")]


def read_dump(path):
    # 控制台重定向产物使用系统代码页 936，ROW 行本身是纯 ASCII
    rows = []
    tail = []
    for line in path.read_text(encoding="gbk").splitlines():
        line = line.strip()
        if not line:
            continue
        match = ROW_PATTERN.match(line)
        if match is None:
            if line.startswith("ROW "):
                raise ValueError("%s: 无法解析的 ROW 行: %s" % (path, line))
            tail.append(line)
            continue
        name, rest_p, rest_q, cur_p, cur_q = match.groups()
        rows.append(
            {
                "name": name,
                "rest_p": parse_vector(rest_p),
                "rest_q": parse_vector(rest_q),
                "cur_p": None if cur_p in (None, "none") else parse_vector(cur_p),
                "cur_q": None if cur_q in (None, "none") else parse_vector(cur_q),
            }
        )
    return rows, tail


def quat_angle(a, b):
    lengths = math.sqrt(sum(v * v for v in a)) * math.sqrt(sum(v * v for v in b))
    dot = abs(sum(x * y for x, y in zip(a, b))) / lengths
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def position_delta(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def format_quat(values):
    return ",".join("%.4f" % v for v in values)


def format_delta(value):
    return "未取到" if value is None else "%.3f" % value


def evaluate(sample):
    rows, tail = read_dump(sample["dump"])
    paired = [row for row in rows if row["cur_q"] is not None]
    for row in paired:
        row["angle"] = quat_angle(row["rest_q"], row["cur_q"])
        row["delta"] = None if row["cur_p"] is None else position_delta(row["rest_p"], row["cur_p"])

    angles = [row["angle"] for row in paired]
    core = [(name, next((row for row in paired if row["name"] == name), None)) for name in CORE_CHAIN]
    readable_core = [(name, row) for name, row in core if row is not None]
    worst_core = max(readable_core, key=lambda item: item[1]["angle"]) if readable_core else None
    root = next((row for row in paired if row["name"] == "Root"), None)
    over = sorted((row for row in paired if row["angle"] > LIMIT_ANY), key=lambda row: -row["angle"])

    if worst_core is None:
        core_detail = "可对照核心骨 0 根"
    else:
        core_detail = "可对照核心骨 %d 根，最大 %.2f°（%s）" % (
            len(readable_core),
            worst_core[1]["angle"],
            worst_core[0],
        )
    checks = (
        (
            "判据一 核心链单骨夹角",
            "≤ %.1f°" % LIMIT_CORE,
            core_detail,
            bool(readable_core) and all(row["angle"] <= LIMIT_CORE for _, row in readable_core),
        ),
        (
            "判据二 全骨单根夹角",
            "≤ %.1f°" % LIMIT_ANY,
            "可对照 %d 根，超出 %d 根" % (len(paired), len(over)),
            not over,
        ),
        (
            "判据三 Root 通道与模型 rest",
            "≤ %.1f°" % LIMIT_ROOT,
            "未取到" if root is None else "%.2f°" % root["angle"],
            root is not None and root["angle"] <= LIMIT_ROOT,
        ),
    )
    return {
        "sample": sample,
        "rows": rows,
        "paired": paired,
        "unpaired": [row["name"] for row in rows if row["cur_q"] is None],
        "tail": tail,
        "core": core,
        "over": over,
        "root": root,
        "median": statistics.median(angles) if angles else None,
        "maximum": max(angles) if angles else None,
        "buckets": (
            sum(1 for value in angles if value < 5.0),
            sum(1 for value in angles if 5.0 <= value < 15.0),
            sum(1 for value in angles if 15.0 <= value < 45.0),
            sum(1 for value in angles if value >= 45.0),
        ),
        "checks": checks,
        "passed": all(check[3] for check in checks),
    }


def build_report(results, selected):
    lines = []
    lines.append("# 模型静止姿态与动画 t=0 曲线的一致性判据")
    lines.append("")
    lines.append("## 判据定义")
    lines.append("")
    lines.append("- 数据来源：`workspace/_tools/NexusCalibCompare.cs` 的全骨对照输出，每行格式为")
    lines.append("  `ROW <骨名> | rest_p=x,y,z | rest_q=x,y,z,w | cur_p=x,y,z | cur_q=x,y,z,w`。")
    lines.append("  `rest_*` 取自模型 fgx 中该骨的 `LocalTransform`；`cur_*` 取自动画 fgx 首个 TrackGroup")
    lines.append("  中同名轨道的曲线在 t=0 的采样值；该骨没有对应轨道时整行止于 `rest_q`。")
    lines.append("- 夹角：`2·acos(|q_rest·q_cur| / (|q_rest|·|q_cur|))`，单位度，取值域 0°~180°；")
    lines.append("  四元数取反表示同一旋转，因此点积取绝对值。")
    lines.append("- 位置差：`|p_cur - p_rest|`，单位与模型相同。")
    lines.append("- 判据一 核心链单骨夹角 ≤ %.1f°，核心链为 %s。" % (LIMIT_CORE, " / ".join(CORE_CHAIN)))
    lines.append("- 判据二 全骨单根夹角 ≤ %.1f°，可对照骨里不允许出现任何一根超过该阈值。" % LIMIT_ANY)
    lines.append("- 判据三 Root 通道取值与模型 Root rest 的夹角 ≤ %.1f°。" % LIMIT_ROOT)
    lines.append("- 三项全部通过判 PASS（退出码 0）；任意一项不通过判 FAIL（退出码 1）；无参数打印用法并退出码 2。")
    lines.append("- 判据只对可对照骨生效：同一次 dump 中同时读出 rest 与 cur 的骨；dump 里不存在的骨不计入超限。")
    lines.append("")
    lines.append("## 样本输入")
    lines.append("")
    lines.append("| 样本 | 输入文件 | ROW 行数 | 可对照骨 | 不可对照行 | 尾部异常行数 |")
    lines.append("|---|---|---|---|---|---|")
    for result in results:
        lines.append(
            "| %s | `%s` | %d | %d | %d | %d |"
            % (
                result["sample"]["label"],
                result["sample"]["dump"].relative_to(WORKSPACE).as_posix(),
                len(result["rows"]),
                len(result["paired"]),
                len(result["unpaired"]),
                len(result["tail"]),
            )
        )
    lines.append("")
    for result in results:
        title = result["sample"]["label"]
        if result["sample"]["key"] == selected:
            title += "（本次命令行选择，退出码取该样本结论）"
        lines.append("## " + title)
        lines.append("")
        lines.append("- 结论：**%s**" % ("PASS" if result["passed"] else "FAIL"))
        buckets = result["buckets"]
        if result["median"] is None:
            lines.append("- 可对照 0 根")
        else:
            lines.append(
                "- 可对照 %d 根 / 共 %d 行；夹角分档 <5° %d 根、5°~15° %d 根、15°~45° %d 根、>45° %d 根；中位数 %.2f°；最大值 %.2f°"
                % (
                    len(result["paired"]),
                    len(result["rows"]),
                    buckets[0],
                    buckets[1],
                    buckets[2],
                    buckets[3],
                    result["median"],
                    result["maximum"],
                )
            )
        lines.append("")
        lines.append("| 判据 | 阈值 | 实测 | 结果 |")
        lines.append("|---|---|---|---|")
        for name, limit, detail, passed in result["checks"]:
            lines.append("| %s | %s | %s | %s |" % (name, limit, detail, "PASS" if passed else "FAIL"))
        lines.append("")
        lines.append("### 核心链逐骨")
        lines.append("")
        lines.append("| 骨名 | rest_q | cur_q | 夹角 | 位置差 |")
        lines.append("|---|---|---|---|---|")
        for name, row in result["core"]:
            if row is None:
                lines.append("| %s | 未取到 | 未取到 | 未取到 | 未取到 |" % name)
                continue
            lines.append(
                "| %s | %s | %s | %.2f° | %s |"
                % (
                    name,
                    format_quat(row["rest_q"]),
                    format_quat(row["cur_q"]),
                    row["angle"],
                    format_delta(row["delta"]),
                )
            )
        lines.append("")
        lines.append("### 超限骨清单（夹角 > %.1f°）" % LIMIT_ANY)
        lines.append("")
        if result["over"]:
            lines.append("| 骨名 | 夹角 | 位置差 |")
            lines.append("|---|---|---|")
            for row in result["over"]:
                lines.append("| %s | %.2f° | %s |" % (row["name"], row["angle"], format_delta(row["delta"])))
        else:
            lines.append("无。")
        if result["unpaired"]:
            lines.append("")
            lines.append("### 不可对照行")
            lines.append("")
            lines.append("- " + "、".join(result["unpaired"]))
        lines.append("")
    lines.append("## 可读范围限制")
    lines.append("")
    lines.append("- 达妮娅 fgx 声明 4110 根骨，读取器在 `calib_denia_full.txt` 连续读出 188 行 ROW 后，第 189 根触发")
    lines.append("  `System.AccessViolationException`（`GrannyTransformTrack.get_Name()`）；`calib_denia.txt` 在 21 行后中断。")
    lines.append("- 本次达妮娅基线取 `calib_denia.txt`：21 行内 18 根可对照，5 根核心链骨里 4 根可对照，Bip001Head 落在中断区段。")
    lines.append("- `calib_denia_full.txt` 不参与判定：其 Root 行 rest_q=(-0.5000,-0.5000,-0.5000,0.5000)、cur_q=(0.0000,-0.7071,0.0000,0.7071)，")
    lines.append("  夹角 90.00°；该取值与今汐 7 段动画的 Root 通道常量相同，dump 无文件头，无法从文件本身判定它配了哪一份动画。")
    lines.append("- 今汐 fgx 声明 205 根骨，205 行全部读出并全部可对照，无中断。")
    return lines


def main(argv):
    parser = argparse.ArgumentParser(
        prog="jx_pose_check.py",
        description="按逐骨 rest 与动画 t=0 曲线值的夹角判定模型与动画是否处于同一空间",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--denia", action="store_true", help="以达妮娅（正样本）的结论决定退出码")
    group.add_argument("--jinhsi", action="store_true", help="以今汐（当前资产）的结论决定退出码")
    arguments = parser.parse_args(argv)
    selected = "denia" if arguments.denia else "jinhsi"

    results = [evaluate(sample) for sample in SAMPLES]
    chosen = next(result for result in results if result["sample"]["key"] == selected)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(build_report(results, selected)) + "\n", encoding="utf-8")

    print(
        "样本 %s：%s；可对照 %d 根；报告 %s"
        % (
            chosen["sample"]["label"],
            "PASS" if chosen["passed"] else "FAIL",
            len(chosen["paired"]),
            REPORT_PATH,
        )
    )
    return 0 if chosen["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
