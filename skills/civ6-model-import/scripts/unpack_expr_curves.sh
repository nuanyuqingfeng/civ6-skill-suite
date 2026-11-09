#!/usr/bin/env bash
# 官方表情曲线补导（A 路线数据入口）：一位角色的 UE AnimCurve 批量解包。
# 移植自御三家 workspace/_tools/unpack_leader.sh 第 1/4/5 步（ueasset curves），
# 并补上四个已实证的坑（见 references/unpack-expression-curves.md）：
#   1) 退出码只看「作业跑完」——每条按 JSON results[].success 与产物文件双重断言；
#   2) 空壳产物——曲线 JSON 必须 numFrames>0 且 curves 非空，否则记失败；
#   3) @plan.txt 批量语法会静默失败——禁止，逐条显式传参；
#   4) 钉版 exe 必须整目录（CUE4Parse-Natives.dll / oo2core 同目录），裸拷 exe
#      每条 "Unable to load DLL" 且退出码仍为 0——启动前检查依赖。
#
# 用法：
#   unpack_expr_curves.sh <角色目录名> <体型/资产目录名> <资产前缀> [额外前缀...]
#   例：unpack_expr_curves.sh 角色_Yangyang FemaleM/Yangyang R2T1YangyangMd10011
#   丹瑾（含外交候选）：unpack_expr_curves.sh 角色_DanJin FemaleM/Danjin R2T1MicaiMd10011 \
#         DialogAnim/FemaleM/Danjin
# 产物：G:/Wuwa_3D_Assets/Characters/<角色目录名>/curves/*.uecurves.json + manifest.json
set -euo pipefail

CHAR=${1:?character folder, e.g. 角色_DanJin}
RELDIR=${2:?asset dir under Role, e.g. FemaleM/Danjin}
RIG=${3:?asset prefix, e.g. R2T1MicaiMd10011}
shift 3 || true
EXTRA_PREFIXES=("$@")   # 相对 Role 根的额外扫描前缀（如 DialogAnim/FemaleM/Danjin）

# exe：钉版目录优先（exe + 原生依赖齐全）
PINNED=$(ls -1dt "G:/Wuwa_3D_Assets/_tools/bin"/ueasset-*/ueasset.exe 2>/dev/null | head -1 || true)
UEASSET=${UEASSET:-${PINNED:-D:/documents/Deepseek_WorkPlace/dsh-ue-asset/dist/ueasset.exe}}
PROFILE=${PROFILE:-wuwa}
CFG=${CFG:-}

if [ ! -f "$UEASSET" ]; then
  echo "UEASSET_MISSING $UEASSET"; exit 2
fi
EXE_HOME=$(cd "$(dirname "$UEASSET")" && pwd)
for dep in CUE4Parse-Natives.dll oo2core_9_win64.dll; do
  if [ ! -f "$EXE_HOME/$dep" ]; then
    echo "UEASSET_DEPS_MISSING $dep（钉版 exe 必须整目录使用；裸拷单 exe 每条静默失败且退出码 0）"
    exit 2
  fi
done
echo "UEASSET $UEASSET"

UA=("$UEASSET")
[ -n "$CFG" ] && UA+=(--config "$CFG")
UA+=(--profile "$PROFILE")
OUT="G:/Wuwa_3D_Assets/Characters/$CHAR"
BASE="Client/Content/Aki/Character/Role/$RELDIR"
TOOLS=$(cd "$(dirname "$0")" && pwd)

mkdir -p "$OUT/curves"
FAIL=0

echo "== 1/4 挂载诊断"
"${UA[@]}" open "$PROFILE"

echo "== 2/4 枚举 AnimCurve 容器（CommonAnim/UiAnim + 额外前缀）"
LIST="$OUT/uianim_list.txt"
: > "$LIST"
"${UA[@]}" find '' --prefix "$BASE/CommonAnim/UiAnim" --ext .uasset --limit 200 \
  | awk '{print $1}' | grep '^Client/' >> "$LIST" || true
for pref in "${EXTRA_PREFIXES[@]}"; do
  "${UA[@]}" find '' --prefix "Client/Content/Aki/Character/Role/$pref" --ext .uasset --limit 200 \
    | awk '{print $1}' | grep '^Client/' >> "$LIST" || true
done
N=$(grep -c '^Client/' "$LIST" || true)
echo "UIANIM_COUNT $N"
if [ "$N" -eq 0 ]; then
  echo "CURVE_SOURCE_EMPTY 无任何 AnimCurve 容器（$BASE/CommonAnim/UiAnim 与额外前缀均未命中）"
  echo "CURVE_SOURCE_EMPTY A 路线禁止静默降级——运行 scripts/expr_route_gate.py probe 进入询问协议"
  exit 1
fi

echo "== 3/4 逐条 curves 导出 + 双重断言"
mkdir -p "$OUT/curves/_resp"
while read -r anim; do
  [ -z "$anim" ] && continue
  stem=$(basename "$anim")
  stem="${stem%.uasset}"
  expected="$OUT/curves/$stem.uecurves.json"
  resp="$OUT/curves/_resp/$stem.json"
  if ! "${UA[@]}" curves "$anim" --out "$OUT/curves" --json > "$resp" 2>/dev/null; then
    echo "CURVES_FAIL $anim 退出码非 0"; FAIL=$((FAIL+1)); continue
  fi
  # 断言一：响应 JSON 里本条 success（旧 exe 只看作业跑完，不看逐条 success）
  if grep -q '"success": *false' "$resp"; then
    echo "CURVES_FAIL $anim results[].success=false"; FAIL=$((FAIL+1)); continue
  fi
  # 断言二：产物存在且非空壳（等价 wuwa_export 的 TRACKS 空壳校验）
  if [ ! -s "$expected" ]; then
    echo "CURVES_FAIL $anim 产物缺失或为空：$expected"; FAIL=$((FAIL+1)); continue
  fi
  if python "$TOOLS/curves_json_check.py" "$expected"; then
    echo "CURVES_OK $anim"
  else
    echo "CURVES_FAIL $anim 曲线 JSON 空壳/非法"; FAIL=$((FAIL+1))
  fi
done < "$LIST"

echo "== 4/4 汇总指纹"
python "$TOOLS/curves_manifest.py" "$CHAR" "$OUT"
if [ "$FAIL" -ne 0 ]; then
  echo "CURVES_DONE_WITH_FAILURES fail=$FAIL"
  exit 1
fi
echo "CURVES_ALL_OK"
