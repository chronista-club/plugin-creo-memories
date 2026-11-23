#!/usr/bin/env bash
set -euo pipefail
PLUGIN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# SessionStart の stdout は agent の context に入る (PreCompact / Stop の出力は agent に届かない)。
# Hosts may launch hooks outside the project. Resolve the event cwd first (Antigravity passes cwd or workspacePaths[0]).
EVENT=$(cat)
IS_AGY=$(printf '%s' "$EVENT" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert isinstance(d,dict); print("1" if any(k in d for k in ("hookEventName","conversationId","workspacePaths")) else "0")' 2>/dev/null) || exit 0
EVENT_CWD=$(printf '%s' "$EVENT" | python3 -c 'import json,sys; d=json.load(sys.stdin); p=d.get("cwd"); wp=d.get("workspacePaths"); p=p if isinstance(p,str) and p else (wp[0] if isinstance(wp,list) and wp and isinstance(wp[0],str) else ""); assert p; print(p)' 2>/dev/null) || exit 0
SOURCE=$(printf '%s' "$EVENT" | python3 -c 'import json,sys; s=json.load(sys.stdin).get("source"); print(s if isinstance(s,str) else "")' 2>/dev/null || true)
cd "$EVENT_CWD" 2>/dev/null || exit 0

atlas=$(bash "$PLUGIN_DIR/scripts/infer-atlas.sh" "$EVENT_CWD" 2>/dev/null || true)
LINES=()
if [ -n "$atlas" ]; then
  LINES+=("creo: project Atlas 候補 = ${atlas}。read({ resource: 'atlas' }) で実在する Atlas ID を解決してから使う。推定名を atlasId に渡さない。")
else
  LINES+=("creo: project Atlas は read({ resource: 'atlas' }) から選ぶ。")
fi
LINES+=("creo: instructions の「今日の脳」は既定の atlas の分。project の続きは briefing({ atlasId }) と read({ resource: 'todo' })。未接続なら作業を続け、取得・保存未実施と報告する。")

# compaction の後 = 縮む前の続きを creo に置く番 (要約が材料。PreCompact の時点では agent に声が届かない)
if [ "$SOURCE" = compact ]; then
  LINES+=("creo: context が縮みました。縮む前の続き (次の一手 / 止まっている理由 / 見ている file / 決めたこと) を、要約を材料に handoff (kind: 'handoff') として remember する。前の handoff があれば supersedes で置き換える。")
fi

MESSAGE=$(printf '%s\n' "${LINES[@]}")
if [ "$IS_AGY" = "1" ]; then
  printf '%s' "$MESSAGE" | python3 -c 'import json,sys; print(json.dumps({"injectSteps":[{"systemMessage":{"systemMessage":sys.stdin.read().rstrip("\n")}}]}, ensure_ascii=False))'
else
  printf '%s\n' "$MESSAGE"
fi

