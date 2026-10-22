#!/usr/bin/env bash
set -euo pipefail
PLUGIN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# SessionStart の stdout は agent の context に入る (PreCompact / Stop の出力は agent に届かない)。
# Hosts may launch hooks outside the project. Resolve the event cwd first.
EVENT=$(cat)
EVENT_CWD=$(printf '%s' "$EVENT" | python3 -c 'import json,sys; d=json.load(sys.stdin); p=d.get("cwd"); assert isinstance(p,str) and p; print(p)' 2>/dev/null) || exit 0
SOURCE=$(printf '%s' "$EVENT" | python3 -c 'import json,sys; s=json.load(sys.stdin).get("source"); print(s if isinstance(s,str) else "")' 2>/dev/null || true)
cd "$EVENT_CWD" 2>/dev/null || exit 0

atlas=$(bash "$PLUGIN_DIR/scripts/infer-atlas.sh" "$EVENT_CWD" 2>/dev/null || true)
if [ -n "$atlas" ]; then
  printf '%s\n' "creo: project Atlas 候補 = ${atlas}。read({ resource: 'atlas' }) で実在する Atlas ID を解決してから使う。推定名を atlasId に渡さない。"
else
  printf '%s\n' "creo: project Atlas は read({ resource: 'atlas' }) から選ぶ。"
fi
printf '%s\n' "creo: instructions の「今日の脳」は既定の atlas の分。project の続きは briefing({ atlasId }) と read({ resource: 'todo' })。未接続なら作業を続け、取得・保存未実施と報告する。"

# compaction の後 = 縮む前の続きを creo に置く番 (要約が材料。PreCompact の時点では agent に声が届かない)
if [ "$SOURCE" = compact ]; then
  printf '%s\n' "creo: context が縮みました。縮む前の続き (次の一手 / 止まっている理由 / 見ている file / 決めたこと) を、要約を材料に handoff (kind: 'handoff') として remember する。前の handoff があれば supersedes で置き換える。"
fi
