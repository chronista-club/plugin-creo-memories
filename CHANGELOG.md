# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.60.1] - 2026-09-12

- hooks: Stop hook と PreToolUse hook の stdout を JSON にする (`{"systemMessage": …}` / `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": …}}`)。**Codex は Stop hook の stdout を必ず JSON として parse する**ので、平文の `echo` は毎 turn「Hook failed — hook returned invalid stop hook JSON output」になっていた (mako 2026-09-12 報告)。Claude Code では平文も JSON も同じ「user に一言出す」挙動で、文言は変えていない

## [0.60.0] - 2026-09-10

- tools-map: `update_presence` / `get_presence` を外す。creo-memories 側で presence (agent の在席・focus の共有) を機能ごと撤去した (chronista-club/creo-memories PR、live で一度も機能していなかった — 在席を保持していた WebSocket に agentId 付きで繋ぐ client が無く、応答は常に空。mako「使ってなかったならオミット、必要になった時にまた考える」)

## [0.59.0] - 2026-09-09

- tools-map: `invite_to_atlas` (email 招待) を外す。creo-memories 側で email 招待の送る側を撤去し、招待は web の招待リンク (spec 21) に一本化した (chronista-club/creo-memories PR、相手のメールアドレスで指定する形は Apple の非公開メールで成立せず、email の存在 oracle でもあった)

## [0.58.0] - 2026-09-09

- tools-map: `create_shared_context` / `list_shared_contexts` / `get_shared_context` / `add_to_shared_context` / `join_shared_context` / `leave_shared_context` の 6 本を外す。creo-memories 側で shared context (一時の共有作業場) を機能ごと撤去した (chronista-club/creo-memories PR、live で 1 件しか使われておらず web からも到達できなかった)

## [0.57.3] - 2026-09-08

- `sync-local-cache.sh`: creo が「atlas が無い」(400) を返す atlas はその分を 0 件として写す (失敗にしない)。creo-memories 2026-09-08 から未解決の atlas は読みでもエラーになるため、repo 名から推定した atlas が無い repo で毎時間「取得に失敗 (前回の写しを残す)」にならないように
- model.md: atlas を指す引数は id / slug / 表示名、解決できなければ「atlas が無い」

## [0.57.2] - 2026-09-07

- SKILL §E / model.md: `tags` 引数は無い (spec 25 D11、creo-memories 側で MCP / REST から撤去)。旧 tag の語彙は label に写した分だけ `labelIds` で引ける、本文に語があれば `search({ query })` で当たる

## [0.57.1] - 2026-09-07

- `infer-atlas.sh`: 表に無い repo でも repo 名をそのまま atlas の手がかりとして出す (atlas が実在するかは server が解決。旧は許可表に無いと何も出さず、creo-elb のように repo と同名の atlas を作っても sync が拾わなかった)
- `sync-local-cache.sh`: creo 由来でない同名の local file は**本文が違う時だけ** `.local-only.md` に退避する (backfill 直後の元 file は同じ本文なので上書きで失うものが無い。旧は必ず退避して index の「local にしか無い」に同じ本文が並んだ)

## [0.57.0] - 2026-09-07

### Added — creo → local memory の写し (spec 25 D8 / D28、F-2)
- `scripts/sync-local-cache.sh`: この repo の atlas と `/agent/claude` `/agent` のうち label **`cache:claude`** が付いた記憶を `~/.claude/projects/<p>/memory/` に 1 記憶 = 1 file で写し、MEMORY.md (index) を作り直す。Claude Code の SessionStart から背景で (1 時間に 1 回、`CREO_SYNC_FORCE=1` で即時)。上限 `CREO_CACHE_MAX` (既定 150、更新日の新しい順)。creo に無い local file は消さず index の別節に並べる。認証は `~/.config/creo-memories/api-key` (chmod 600) → env `CREO_API_KEY` → 無ければ skip。file 名は 1 つの規則 (`derive_name`) で、共有 atlas の metadata を経路に使わない
- SKILL §C / model.md: 手元に置きたい記憶は remember + label `cache:<自分>` (Claude は `cache:claude`)。local に直接書かない
- `infer-atlas.sh`: alias を実在の atlas に (creo-ui → creoui、club-unison → unison、bikeboy → bikeboy-ladyland、chronista-hub は同名、`bokeboy` の誤字)
- 初回の backfill (local → creo、1 回もの) と REST の `atlasId` 解決 + write gate は creo-memories 側 (#863)。内容は claude-plugin-creo-memories#27 (review 3 巡 PASS) と同じ

## [0.56.1] - 2026-09-07

- MCP URL をサービス案内の `/` から実際の `/mcp` に修正。Codex の接続・OAuth メタデータ解決の失敗を解消する。
- 接続先の回帰テストを追加。

## [0.56.0] - 2026-09-06

- 新しい plugin-creo-memories リポジトリを正本とし、Claude Code / Codex の共有 skills と配布定義を追加。
- ホスト固有の前提を明記し、検証・CI・安定配布経路を整備。

## [0.55.0] - 2026-09-06

### Changed — 賢いモデルのための全面書き直し (spec 25 の世界に)
- **8,063 行 → 約 600 行**。plugin が渡すのは「事実 (creo の世界の形) と目的と判断の基準」だけ。機械的な規則 (lock / 行為者 / 提案の門 / 種類の列挙 / label の上限) は server が守るので「必ず」「mandate」を全部落とした
- **label は agent も作れる** (spec 25 D19 の改訂、2026-09-06): 文法 `family:leaf[:leaf]` (`:` 構造 / `-` 連結 / `/` は atlas 専用 / 大小無視) だけ決め、語彙は自由。`label_list` を先に見る、増えた分は減衰と統合の提案で手入れ。文法は規約 (server は長さと plan の上限だけ見る)。family の例は repo / priority / size / phase / mark / area
- SKILL.md を A 目的 / B 世界の形 / C 判断の基準 / D 他者と / E 罠 の 5 節 (≤ 120 行) に。reference は `model.md` (spec 25 の要約) / `tools-map.md` (意図 → tool、75 tool、creo の CI が検証) / `recipes.md` (6 場面) / `agent-atlas.md` の 4 本
- 2-layer「Layer 1 = Local Canon」を spec 25 D8 / D28 の言葉に: **正本は creo、local は写し** (creo → local の生成は次版)
- hooks を 4 つに: SessionStart (atlas の手がかり、server は cwd を知らない) / **PreCompact (新、context が縮む前に handoff を促す)** / Stop (1 行) / PreToolUse(Write memory/*.md) (D8 の言葉に)
- `infer-atlas.sh` を git remote 基準に (旧 branch 規則を撤去)、表は slug と repo 名が違うものだけ
- creo-memories 側に contract test (`plugin-contract.test.ts`、CI job `plugin-contract`): tool 名の集合 / 引数名 / 撤去済み語彙 / hooks / version を検証。対の PR: chronista-club/creo-memories#862

### Removed
- `api-redesign.md` / `api-redesign-rfc.md` (creo の `docs/design/archive/` へ history として移動)、improvement-loop (reference 7 本 + command + scripts 4 本 + invocation-stats)、scenes 4 本、cookbooks 9 本、templates 8 本、workflows / anti-patterns / decision-tree / mcp-tools / setup、UserPromptSubmit (keyword regex) と PostToolUse (invocation.log) の hook、`.DS_Store`
- 現存しない tool 24 種の案内 (`concept_*` ×8、`team_*` ×4、`share_atlas` 系 3、`subscribe_memories` 系 4、`add_tag` / `remove_tag` / `rename_tag`、RFC の仮想名)、旧引数名 (annotate の `memoryId` / `kind`、create_todo の `title`、record_work_log の `type`、link_external / complete_with_context の camelCase、search の `filter:{…}`)、序破離 / concept / category / stage の語彙、Linear の pair mandate

## [0.54.1] - 2026-09-03

### Fixed
- **SessionStart hook が plugin 実体を見つけられない不整合**: hook 内の
  `find … -name "claude-plugin-creo-memories*"` は plugin cache のディレクトリ名
  (`creo-memories`、marketplace.json の `name` 由来であって repo 名ではない) と一致せず
  **構造的に必ず空振り**し、常に fallback の `$HOME/repos/claude-plugin-creo-memories` が
  使われていた。repo を clone していない環境では `scripts/infer-atlas.sh` に到達できず、
  `|| echo ""` に吸われて Atlas 推論が無言で無効化される。`${CLAUDE_PLUGIN_ROOT}` 参照に変更し、
  インラインの `sh -c` を `hooks/session-start.sh` に切り出した
  (chronista-style / vantage-point と同じ形)。出力は変更前と byte 単位で一致することを確認済み。

## [0.54.0] - 2026-09-03

### Added
- **Agent Atlas の案内**: SessionStart hook に `/agent` (全 agent 共通) と `/agent/claude` (Claude 専用) の
  使い分けを 1 行出すようにした。project の記憶は project atlas、自分の癖・修正点は `/agent/claude`、
  他 agent にも効く知識は `/agent` (tag `agent:claude`)。`atlasId` 指定の search は子 atlas を含まない注意つき。
  規約の SSOT は `/agent` atlas の charter memory (slug `agent-charter`)、要約を
  `skills/creo-memories/reference/agent-atlas.md` に置き、SKILL.md / decision-tree.md の Decision Tree に Q2.5 を追加

### Changed
- **ロックステップ方針の撤回**: `0.53.0` でプロダクト (`chronista-club/creo-memories`) に版数を揃えたが、
  plugin 側の変更とプロダクトのリリースは周期が異なり、揃え続けると plugin 単独の変更を出せない
  (プロダクトは既に `0.55.0`)。今後 plugin は自身の変更内容に応じて独立に bump する。

### Fixed
- **SKILL.md frontmatter の version drift**: `0.35.0` → `0.54.0`。`0.53.0` で `plugin.json` だけを bump し
  `skills/creo-memories/SKILL.md` が取り残されていた (`0.34.2` で解消した drift の再発)。

## [0.53.0] - 2026-09-01

### Changed
- **ロックステップ復帰**: プロダクト (`chronista-club/creo-memories`) の `0.53.0` に版数を揃えた。
  `0.35.0` (2026-05-15) 以降 bump が止まり、プロダクトだけが進んでいたため 18 マイナー分の
  ズレが生じていた。`0.36.0`〜`0.52.0` は欠番。
- SKILL.md / RFC の tool 名・tool 数を現行実装 (72 tool) に同期 (#20)
- B-2 slug/display_name resolver を SKILL.md に反映 (#21)

### Fixed
- `0.35.0` 以降 `skills/` の中身が更新されていた (#20 / #21 で 5 ファイル 49 行) にもかかわらず
  `plugin.json` の version が据え置かれていた問題を解消。marketplace 側は version を持たず
  (chronista-plugins #10)、配布される版数は本 repo の `plugin.json` がそのまま使われるため、
  version を据え置くと「新しい版が出た」シグナルがどこにも立たない。

## [0.35.0] - 2026-05-14

### Added
- **atomic tag CRUD primitives**: 単独 tag を原子的に追加/削除/rename する 3 新 MCP tool ([CREO-174](https://linear.app/chronista/issue/CREO-174))
  - `add_tag(id, tag)` — 既存 tag なら no-op (idempotent)
  - `remove_tag(id, tag)` — 不在 tag なら no-op (idempotent)
  - `rename_tag(id, oldTag, newTag)` — oldTag 不在は `ValidationError` throw
  - dual storage 同時更新 (`tags` top-level + `metadata.tags` nested、 SurrealQL `array::distinct`/`array::complement`)
  - chain 伸長しない (in-place、 atomic tag CRUD は非意味的変更扱い)
  - concept service 連携 (classify / declassify を非 blocking で並走)
- HTTP endpoint も同型で追加: `POST/DELETE/PATCH /api/memories/:id/tags`
- 既存 `update_memory({tags: [...]})` (全置換) との **後方互換維持**、 並走で expose

### Documentation
- `mcp-tools.md`: 3 新 tool を articulate + `update_memory` の tag 操作節に使い分けガイド追記

## [0.34.2] - 2026-05-02

### Fixed
- `session-snapshot.md` cookbook の `search` 例が query 必須を明示していなかった (Phase 4 Confirm / Resume / List)。 dogfood で 0 件返却を観測 → `get_memory({id})` を主路線に変更 + query 必須を WARNING で明示
- SKILL.md frontmatter version drift (0.34.0 → 0.34.2、 plugin.json と整合)
- CHANGELOG `[0.34.0]` の Changed entry が実際は v0.34.1 内容 → v0.34.1 entry に移動

## [0.34.1] - 2026-05-02

### Changed
- Skill tree refactor: `creo-memories/SKILL.md` → `skills/creo-memories/SKILL.md` (公式 spec 準拠)
- Spec compliance: license/homepage fields, removed legacy skills.txt

## [0.34.0] - 2026-05-02

### Added
- Internal memory link `[label](mem_xxx)` syntax (Phase 1: server expand + client delegate)
- Session snapshot cookbook + onboarding step 0
