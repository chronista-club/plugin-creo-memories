# plugin-creo-memories

Shared Claude Code / Codex plugin for **creo-memories** — the external brain. Your context is finite and the session ends; creo is where the continuation lives, shared with the next you, the other agents working alongside (codex / grok / other LLMs / another claude session), and the people you work with.

## What it provides

- **MCP server** `https://mcp.creo-memories.in/mcp` (tool descriptions are the source of truth)
- **Skill** `creo-memories` — purpose, the shape of the world (3 lineages × 16 kinds, marks, labels, lock, proposals, briefing, sender), the judgment for *what to write / where / when to read*, how to work with others, and the non-obvious traps. ≤ 120 lines. No mandates: the mechanical rules are enforced by the server
- **Hooks** (2 events)
  - `SessionStart` — the atlas hint for this repo (the server does not know your cwd), and the project's own briefing is `briefing({ atlasId })`. After a compaction (`source: compact`) it asks the agent to write the handoff from the summary
  - `PreToolUse(Write */memory/*.md)` — local memory is a cache; the canonical copy is `/agent/<self>`
  - No `PreCompact` / `Stop` hooks: their output never reaches the agent (PreCompact stdout goes to the debug log, Stop's `systemMessage` is shown only to the person)

## Layout

```
skills/creo-memories/
  SKILL.md                 A purpose / B world / C judgment / D with others / E traps
  reference/model.md       spec 25 summary (lineages, kinds, marks, label, lock, proposals, briefing, self & cache)
  reference/tools-map.md   intent → tool (all of them; the set is checked against the server by creo-memories CI)
  reference/recipes.md     7 scenes: start / handoff / decision / incident / todo / with others / thread
  reference/agent-atlas.md /agent and /agent/<self>, local as cache
hooks/                     hooks.json, session-start.sh
scripts/infer-atlas.sh     cwd / git remote → atlas slug
scripts/sync-local-cache.sh creo → ~/.claude/projects/<p>/memory/ (label cache:claude; Claude Code の SessionStart から背景で)
```

## Install

```
/plugin marketplace add chronista-club/chronista-plugins
/plugin install creo-memories@chronista-plugins
```

Authentication: the MCP server uses OAuth (Creo ID). On first use Claude Code opens the login.

## Companion

The plugin mirrors the MCP server's tool list, argument names and atlas names. The mirror is verified by `apps/creo-mcp-server/src/plugin-contract.test.ts` in the (private) `creo-memories` repo (CI job `plugin-contract` currently clones the frozen `claude-plugin-creo-memories` repo; switching its target and host-specific assertions is companion work). Changes to tools on the server side come paired with a PR here; PR numbers reference each other. Spec: creo-memories `docs/spec/25-memory-classification.md`, design doc 39.

## Changelog

See [CHANGELOG.md](CHANGELOG.md). 0.55.0 is the rewrite for the spec-25 world (2026-09-06).

## License

MIT

## 共通配布

Claude Code / Codex は同じ `skills/` を使います。[ホスト対応と検証範囲](docs/host-support.md)を参照してください。カタログは [chronista-plugins](https://github.com/chronista-club/chronista-plugins)。

Codex はカタログ追加後 `codex plugin add creo-memories@chronista-plugins` で登録する。共有 skills はホストのスキル一覧から呼び出す。
