#!/usr/bin/env bash
set -euo pipefail
PLUGIN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# Hosts may launch hooks outside the project. Resolve the event cwd first.
EVENT_CWD=$(python3 -c 'import json,sys; d=json.load(sys.stdin); p=d.get("cwd"); assert isinstance(p,str) and p; print(p)' 2>/dev/null) || exit 0
cd "$EVENT_CWD" 2>/dev/null || exit 0

atlas=$(bash "$PLUGIN_DIR/scripts/infer-atlas.sh" "$EVENT_CWD" 2>/dev/null || true)
if [ -n "$atlas" ]; then
  printf '%s\n' "creo: project Atlas 候補 = ${atlas}。read({ resource: 'atlas' }) で実在する Atlas ID を解決してから使う。推定名を atlasId に渡さない。"
else
  printf '%s\n' "creo: project Atlas は read({ resource: 'atlas' }) から選ぶ。"
fi
printf '%s\n' 'creo: 記憶コンテキストが既に届いていれば重複検索は不要。未注入なら必要な記憶だけ search。未接続なら作業を続け、取得・保存未実施と報告する。'
