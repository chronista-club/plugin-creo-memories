#!/usr/bin/env bash
#
# infer-atlas.sh — cwd (と git remote) から project atlas の slug を推定する
#
# server は cwd を知らない (atlas は認証の既定 atlas) ので、「今どの project か」の手がかりは
# plugin にしか出せない。表は atlas の slug と repo 名が違うものだけ。表に無ければ repo 名を
# そのまま出す (atlas が実在するかは server が解決する。無ければ一覧は 0 件、hook は「推定名」と断る)。
#
# Usage: ./infer-atlas.sh [/path/to/repo]

set -euo pipefail

REPO_PATH="${1:-$(pwd)}"
cd "$REPO_PATH" 2>/dev/null || exit 1

# repo 名 → atlas slug (同名は不要)
alias_of() {
  case "$1" in
    chronista-plugins|plugin-chronista-style|plugin-team-bucciarati|plugin-vantage-point|plugin-creo-memories) echo "chronista-plugins" ;;
    claude-plugin-creo-memories) echo "creo-memories" ;;
    creo-id) echo "chronista-club" ;;
    claude-plugins|claude-plugin-*) echo "chronista-plugins" ;;
    creo-ui|creoui) echo "creoui" ;;
    club-unison) echo "unison" ;;
    bikeboy|bikeboy-ladyland) echo "bikeboy-ladyland" ;;
    objectrecords|objectrecords-io) echo "objectrecords-io" ;;
    go-fast-packing) echo "Go Fast Packing" ;;
    *) return 1 ;;
  esac
}

# 1. git の toplevel の basename (worktree / lane でも repo 名で判定)
name=""
if top=$(git rev-parse --show-toplevel 2>/dev/null); then
  name=$(basename "$top")
  # worktree の dir 名は branch 名になりがち → remote の repo 名を優先
  if remote=$(git remote get-url origin 2>/dev/null); then
    r=$(basename "${remote%.git}")
    [ -n "$r" ] && name="$r"
  fi
fi
[ -z "$name" ] && name=$(basename "$REPO_PATH")

if atlas=$(alias_of "$name"); then echo "$atlas"; exit 0; fi
[ -n "$name" ] && { echo "$name"; exit 0; }
exit 1
