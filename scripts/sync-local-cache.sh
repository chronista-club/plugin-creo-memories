#!/usr/bin/env bash
#
# sync-local-cache.sh — creo → local memory の写しを作る (spec 25 D8 / D28、F-2)
#
# 正本は creo。local (`~/.claude/projects/<dir>/memory/`) は起動高速化と可用性のための写し。
# この repo の atlas と `/agent/claude` `/agent` のうち、label `cache:claude` が付いた記憶を
# 1 記憶 = 1 file で書き、MEMORY.md (index) を作り直す。creo に無い local file は**消さない**
# (index の別節に並べる = 「local にしか無い事実」の検出器)。
#
# 認証: ~/.config/creo-memories/api-key (chmod 600) → env CREO_API_KEY。どちらも無ければ黙って skip
# (creo に繋がらない時は前回の写しが残る)。key は出力しない。
#
# 上限: CREO_CACHE_MAX (既定 150 件、更新日の新しい順)。超えた分は index に件数だけ出す
#
# Usage:
#   sync-local-cache.sh [--cwd <dir>]        # 今すぐ同期 (stdout に要約)
#   sync-local-cache.sh --background         # hook 用: stdin の JSON から cwd を取り、背景で同期
#   CREO_SYNC_FORCE=1 で 1 時間の間隔を無視

set -uo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
BASE="${CREO_API_BASE:-https://app.creo-memories.in}"
LABEL="cache:claude"
STATE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/creo-memories"
JQ=$(command -v jaq 2>/dev/null || command -v jq 2>/dev/null || true)

api_key() {
  local f="${XDG_CONFIG_HOME:-$HOME/.config}/creo-memories/api-key"
  if [ -r "$f" ]; then tr -d '[:space:]' < "$f"; return 0; fi
  if [ -n "${CREO_API_KEY:-}" ]; then printf '%s' "$CREO_API_KEY"; return 0; fi
  return 1
}

cwd=""
mode="run"
while [ $# -gt 0 ]; do
  case "$1" in
    --background) mode="background" ;;
    --cwd) cwd="${2:-}"; shift ;;
    *) ;;
  esac
  shift
done

if [ "$mode" = "background" ]; then
  # hook の stdin (JSON) から cwd。読めなければ $PWD
  if [ -n "$JQ" ]; then
    input=$(cat 2>/dev/null || true)
    cwd=$(printf '%s' "$input" | $JQ -r '.cwd // empty' 2>/dev/null || true)
  fi
  [ -z "$cwd" ] && cwd="$PWD"
  mkdir -p "$STATE_DIR"
  nohup bash "$0" --cwd "$cwd" > "$STATE_DIR/sync.log" 2>&1 < /dev/null &
  exit 0
fi

[ -z "$cwd" ] && cwd="$PWD"
[ -z "$JQ" ] && { echo "creo-sync: jq が無い"; exit 0; }
command -v curl > /dev/null 2>&1 || { echo "creo-sync: curl が無い"; exit 0; }
key=$(api_key) || exit 0

# Claude Code の project dir 名 = cwd の英数字以外を全部 `-` に (`.vp/lanes/ios` → `--vp-lanes-ios`、実測 2026-09-07)
dir_key=$(printf '%s' "$cwd" | sed 's/[^A-Za-z0-9]/-/g')
mem_dir="$HOME/.claude/projects/$dir_key/memory"
stamp="$STATE_DIR/$dir_key.stamp"
lock="$STATE_DIR/$dir_key.lock"

# 1 時間に 1 回 (背景で走るので、session を開くたびに叩かない)
if [ -z "${CREO_SYNC_FORCE:-}" ] && [ -f "$stamp" ] && [ -n "$(find "$stamp" -mmin -60 2>/dev/null)" ]; then
  echo "creo-sync: 1 時間以内に同期済 ($dir_key)"; exit 0
fi
mkdir -p "$STATE_DIR"
# 1 時間より古い lock は死骸 (SIGKILL / 再起動で trap が走らない) とみなして壊す
if [ -d "$lock" ] && [ -z "$(find "$lock" -maxdepth 0 -mmin -60 2>/dev/null)" ]; then rmdir "$lock" 2>/dev/null; fi
if ! mkdir "$lock" 2>/dev/null; then echo "creo-sync: 別の同期が走っている"; exit 0; fi
trap 'rmdir "$lock" 2>/dev/null' EXIT

atlas=$("$PLUGIN_ROOT/scripts/infer-atlas.sh" "$cwd" 2>/dev/null || true)

# label 名 → id (REST の一覧 filter は id しか受けない。無ければ「写すものが無い」= 何もしない)
label_id=$(curl -sS -m 30 "$BASE/api/labels" -H "X-API-Key: $key" 2>/dev/null \
  | $JQ -r --arg n "$LABEL" '.labels[]? | select((.name | ascii_downcase) == $n) | .id' 2>/dev/null | head -1)
[ -z "$label_id" ] && { echo "creo-sync: label $LABEL が無い (label_create してから)"; exit 0; }

fetch_atlas() {
  # $1 = atlas (id / slug / 表示名)。label 付きの記憶を page で全部取る (1 page 100 件)
  local a="$1" page=1 got
  while :; do
    got=$(curl -sS -m 30 -G "$BASE/api/memories" -H "X-API-Key: $key" \
      --data-urlencode "atlasId=$a" --data-urlencode "labelIds=$label_id" \
      --data-urlencode "limit=100" --data-urlencode "page=$page") || return 1
    printf '%s' "$got" | $JQ -e '.memories' > /dev/null 2>&1 || return 1
    printf '%s\n' "$got" | $JQ -c '.memories[]'
    [ "$(printf '%s' "$got" | $JQ '.memories | length')" -lt 100 ] && break
    page=$((page + 1))
    [ "$page" -gt 20 ] && break
  done
}

tmp=$(mktemp)
trap 'rm -f "$tmp" "$tmp.top"; rmdir "$lock" 2>/dev/null' EXIT
ok=1
for a in ${atlas:+"$atlas"} claude agent; do
  fetch_atlas "$a" >> "$tmp" || { echo "creo-sync: $a の取得に失敗 (前回の写しを残す)"; ok=0; }
done
[ "$ok" = 1 ] || exit 0

# 上限 (既定 150 件、更新日の新しい順)。超えた分は index に件数を出す = 手入れ (label を外す / 減衰の提案) の合図
MAX="${CREO_CACHE_MAX:-150}"
case "$MAX" in ''|*[!0-9]*) MAX=150 ;; esac
total=$($JQ -s 'length' "$tmp")
$JQ -s -c 'sort_by(.updated_at // .updatedAt // "") | reverse | .[]' "$tmp" > "$tmp.top" && mv -f "$tmp.top" "$tmp"
omitted=$((total > MAX ? total - MAX : 0))
omitted_names=()

mkdir -p "$mem_dir"
index="$mem_dir/MEMORY.md"
written=()
count=0
seen=()   # 書いた名前と省いた名前の両方 (衝突の判定は 1 つの規則で)

slugify() { tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' | cut -c1-63; }

# 1 記憶 → file 名。metadata.cache.name → 無ければ題 → それも空なら id。英数字と `-` だけ (creo の metadata は
# 共有 atlas なら他の書き手の入力。`/` `..` を通さない)。同じ名前が 2 度出たら id の末尾を添える。
# 書く側と (上限で) 省く側の両方がこの 1 つの関数を通る = index の「local にしか無い」判定が同じ名前で行える
derive_name() {
  local line="$1" n
  n=$(printf '%s' "$line" | $JQ -r '.metadata.cache.name // empty' | slugify)
  [ -z "$n" ] && n=$(printf '%s' "$line" | $JQ -r '(.content | split("\n")[0]) | sub("^#+ *"; "")' | slugify)
  [ -z "$n" ] && n=$(printf '%s' "$line" | $JQ -r '.id' | slugify)
  case " ${seen[*]:-} " in *" $n "*) n="$n-$(printf '%s' "$line" | $JQ -r '.id' | tail -c 7 | slugify)" ;; esac
  printf '%s' "$n"
}

i=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  name=$(derive_name "$line")
  seen+=("$name")
  if [ "$i" -ge "$MAX" ]; then omitted_names+=("$name"); i=$((i + 1)); continue; fi
  i=$((i + 1))
  title=$(printf '%s' "$line" | $JQ -r '(.content | split("\n")[0]) | sub("^#+ *"; "")')
  # YAML で素のまま置けない題 (": " や " #" や引用符を含む、特殊文字で始まる) は double-quoted (JSON の escape と互換)
  ytitle=$(printf '%s' "$title" | $JQ -R -r 'if test(": | #|[\"\\\\]|^[\\[\\]{}&*!|>%@`'"'"'-?,]|:$") then tojson else . end')
  # creo 由来でない同名の local file は、本文が違う時だけ退避する (消さない、の約束。同じ本文 = backfill 済の元 file なら
  # 上書きで失うものは無い)
  stash=""
  if [ -f "$mem_dir/$name.md" ] && ! grep -q '^  creo_id: ' "$mem_dir/$name.md"; then stash="$mem_dir/$name.md"; fi
  typ=$(printf '%s' "$line" | $JQ -r '.metadata.cache.type // (if .kind == "learning" then "feedback" elif .kind == "reference" then "reference" else "project" end)')
  {
    printf -- '---\nname: %s\ndescription: %s\nmetadata:\n  type: %s\n  creo_id: %s\n  kind: %s\n  updated_at: %s\n---\n\n' \
      "$name" "$ytitle" "$typ" "$(printf '%s' "$line" | $JQ -r '.id')" \
      "$(printf '%s' "$line" | $JQ -r '.kind // "未整理"')" "$(printf '%s' "$line" | $JQ -r '.updated_at // .updatedAt // ""')"
    printf '%s' "$line" | $JQ -r '.content | split("\n") | .[1:] | (if .[0] == "" then .[1:] else . end) | join("\n")'
  } > "$mem_dir/.$name.md.tmp" || { echo "creo-sync: 書けなかった: $name"; rm -f "$mem_dir/.$name.md.tmp"; continue; }
  if [ -n "$stash" ]; then
    # frontmatter を除いた本文 (空行と末尾の空白を落として) が同じなら退避しない
    body_of() { awk 'BEGIN{n=0} /^---$/{n++; next} n>=2 && !/^[[:space:]]*$/ {sub(/[[:space:]]+$/, ""); print}' "$1"; }
    if [ "$(body_of "$stash" | shasum)" != "$(body_of "$mem_dir/.$name.md.tmp" | shasum)" ]; then
      mv -f "$stash" "$mem_dir/$name.local-only.md"
    fi
  fi
  mv -f "$mem_dir/.$name.md.tmp" "$mem_dir/$name.md" || { echo "creo-sync: 書けなかった: $name"; continue; }
  written+=("$name")
  count=$((count + 1))
done < "$tmp"

# index を作り直す。creo 由来 → 本節、creo に無い local file → 別節 (消さない)
{
  printf '# Memory Index\n\n'
  printf '<!-- creo の写し (label cache:claude、atlas: %s + /agent/claude + /agent)。正本は creo。生成: sync-local-cache.sh %s -->\n\n' "${atlas:-?}" "$(date -u +%Y-%m-%dT%H:%MZ)"
  [ "$omitted" -gt 0 ] && printf '> ⚠️ label cache:claude が %s 件あり、上限 %s を超えた %s 件を省いた (古い順。file は残るが index には載せない)。creo 側で label を外すか減衰を提案して減らす\n\n' "$total" "$MAX" "$omitted"
  for n in "${written[@]:-}"; do
    [ -z "$n" ] && continue
    d=$(sed -n 's/^description: //p' "$mem_dir/$n.md" | head -1 | $JQ -R -r 'if startswith("\"") then (fromjson? // .) else . end')
    printf -- '- [%s](%s.md) — %s\n' "$n" "$n" "$d"
  done
  local_only=()
  for f in "$mem_dir"/*.md; do
    [ -e "$f" ] || continue
    b=$(basename "$f" .md)
    [ "$b" = "MEMORY" ] && continue
    skip=0
    for w in "${written[@]:-}" "${omitted_names[@]:-}"; do [ "$w" = "$b" ] && { skip=1; break; }; done
    [ "$skip" = 1 ] || local_only+=("$b")
  done
  if [ ${#local_only[@]} -gt 0 ]; then
    printf '\n## local にしか無い (creo に未登録。正本は creo — remember して label cache:claude を)\n\n'
    for b in "${local_only[@]}"; do
      d=$(sed -n 's/^description: //p' "$mem_dir/$b.md" | head -1 | $JQ -R -r 'if startswith("\"") then (fromjson? // .) else . end')
      printf -- '- [%s](%s.md) — %s\n' "$b" "$b" "$d"
    done
  fi
} > "$mem_dir/.MEMORY.md.tmp" && mv -f "$mem_dir/.MEMORY.md.tmp" "$index"

touch "$stamp"
echo "creo-sync: $count 件を写した (${mem_dir}、atlas ${atlas:-?} + claude + agent、local だけ ${#local_only[@]} 件)"
