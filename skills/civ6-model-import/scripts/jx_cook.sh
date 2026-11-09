#!/usr/bin/env bash
set -uo pipefail
COOKER_DIR="/f/Steam/steamapps/common/Sid Meier's Civilization VI SDK/AssetModTools/Cooker"
PROJ_W='D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi'
PANTRY_BASE_W="F:\Steam\steamapps\common\Sid Meier's Civilization VI SDK Assets\Civ6"
STEWPOT_W='D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\cook_out'
XLP_W='D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi\XLPs\leader_jinhsi_qyqxp.xlp'
RUN_CWD="/d/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/cook_cwd"
LOG="/d/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/cook_20261025b.log"
mkdir -p "$RUN_CWD"
cd "$COOKER_DIR" || exit 9
./Civ6AssetCooker_FinalRelease.exe --absolute_paths --no_mt --platform Windows \
  --pantry "$PROJ_W" \
  --pantry "$PANTRY_BASE_W\pantry" \
  --pantry "$PANTRY_BASE_W\DLC\Shared\pantry" \
  --pantry "$PANTRY_BASE_W\DLC\Expansion1\pantry" \
  --pantry "$PANTRY_BASE_W\DLC\Expansion2\pantry" \
  --config Civ6.cfg --mode XLP --stewpot "$STEWPOT_W" "$XLP_W" > "$LOG" 2>&1
echo "COOK_EXIT=$?"
for pat in "missing file" "wrong extension" "is not allowed here" "Replacing asset" "error asset" "fallback" "I/O error" "ERRORS"; do
  printf '%s=%s\n' "$pat" "$(grep -ic "$pat" "$LOG")"
done
ls -l "/d/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/cook_out/leaders/"
