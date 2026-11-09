#!/usr/bin/env bash
# 全 XLP cook 扫描：逐条目跑官方 Cooker，记录退出码与九类告警到 TSV
# 用法：cook_sweep.sh --cooker-dir <目录> --project-win <工程绝对路径> --project-posix <同一路径的 posix 形式>
#        --pantry-base-win <SDK Assets 下的 Civ6 目录> --work <输出目录> --tag <批次名>
set -uo pipefail

COOKER_DIR=""
PROJECT_WIN=""
PROJECT_POSIX=""
PANTRY_BASE=""
WORK=""
TAG=""

while [ $# -gt 0 ]; do
  case "$1" in
    --cooker-dir) COOKER_DIR="$2"; shift 2 ;;
    --project-win) PROJECT_WIN="$2"; shift 2 ;;
    --project-posix) PROJECT_POSIX="$2"; shift 2 ;;
    --pantry-base-win) PANTRY_BASE="$2"; shift 2 ;;
    --work) WORK="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    *) echo "未知参数 $1" >&2; exit 2 ;;
  esac
done

if [ -z "$COOKER_DIR" ] || [ -z "$PROJECT_WIN" ] || [ -z "$PROJECT_POSIX" ] || [ -z "$PANTRY_BASE" ] || [ -z "$WORK" ] || [ -z "$TAG" ]; then
  echo "六个参数缺一不可" >&2
  exit 2
fi

OUT_DIR="$WORK/sweep_$TAG/out"
SUMMARY="$WORK/sweep_$TAG.tsv"
mkdir -p "$OUT_DIR"
printf 'xlp\texit\tmissing_file\twrong_ext\tnot_allowed\tclass\treplacing\terror_asset\tfallback\tio_error\terrors\tlast_line\n' > "$SUMMARY"

cd "$COOKER_DIR" || exit 9
for xlp in "$PROJECT_POSIX"/XLPs/*.xlp; do
  stem=$(basename "$xlp" .xlp)
  LOG="$WORK/sweep_${TAG}_${stem}.log"
  ./Civ6AssetCooker_FinalRelease.exe --absolute_paths --no_mt --platform Windows \
    --pantry "$PROJECT_WIN" \
    --pantry "$PANTRY_BASE\pantry" \
    --pantry "$PANTRY_BASE\DLC\Shared\pantry" \
    --pantry "$PANTRY_BASE\DLC\Expansion1\pantry" \
    --pantry "$PANTRY_BASE\DLC\Expansion2\pantry" \
    --config Civ6.cfg --mode XLP --stewpot "$OUT_DIR" "$xlp" > "$LOG" 2>&1
  code=$?
  printf '%s\t%s' "$stem" "$code" >> "$SUMMARY"
  for pat in "missing file" "wrong extension" "is not allowed here" "class" "Replacing asset" "error asset" "fallback" "I/O error" "ERRORS"; do
    printf '\t%s' "$(grep -ic -- "$pat" "$LOG")" >> "$SUMMARY"
  done
  printf '\t%s\n' "$(tail -n 1 "$LOG" | tr -d '\r')" >> "$SUMMARY"
  echo "DONE $stem exit=$code"
done
column -t -s $'\t' "$SUMMARY"
