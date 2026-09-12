---
name: creo-memories
description: creo-memories = 外部脳。context が尽きても、session / machine / model / 人をまたいで続きができる場所。書くのは「次に拾う誰かのため」、読むのは「自分が始めた気になる前」。
metadata:
  version: 0.61.0
  tags: memory, external-brain, collaboration, chronista
---

## ホスト共通の読み方

このディレクトリが共有定義の正本。Claude Code は `.claude-plugin`、Codex は `.codex-plugin` から同じ skills を読む。Grok CLI は Claude 互換形式を対象とするが実機確認待ち。
本文中の `Agent`、`Bash`、`Read` や MCP の名前は Claude 表記の例。利用中のホストで提供された同等のツールを発見して使う。存在しないツール・モデル・実行結果を仮定しない。`${CLAUDE_PLUGIN_ROOT}` の資料パスは、この skill から辿れるプラグインルートに読み替える。

# creo-memories — 外部脳

## A. 目的

あなたの context は有限で、session は終わる。続きを拾うのは、次の自分、連動して動く他の agent (codex / grok / 他の LLM、そして別 session の claude)、そして一緒に働く人。
**creo はその全員が同じものを読む外部脳**であり、記録 (todo / spec / 決定 / 引き継ぎ) の SSOT でもある。

- **書く**のは「次に拾う誰かのため」。決めた / 学んだ / 壊れた / 渡す / 後で自分が探す、のどれかなら書く。会話の写しは書かない
- **読む**のは「自分が始めた気になる前」。session 開始の「今日の脳」が実際に届いていれば利用する。過去の決定を前提にする前に `search`
- 機械的な規則 (lock、行為者、提案の門、種類の列挙、label の上限) は **server が守る**。ここに「必ず」は無い。判断はあなたがする

## B. 世界の形 (詳細: [model.md](reference/model.md))

- 記憶は **出来事 / 考え / やること** の 3 系統。終わり方で決まる (出来事は終わらない、考えは置き換わる、やることは片付く)。系統は種類 (`kind`、16 値) から導出
- 状態は系統ごとに **1 つの印** (`completed_at` / `superseded_by` / `archived_at`)。`status` 列は無い
- 語彙は **種類 + label**。自由 tag は無い。label は `family:leaf[:leaf]` の文法 (`:` は左が広く右が狭い、`-` は語の連結、`/` は atlas 専用、大小無視) で **agent も人も作れる**。語彙は自由。**文法は規約で server は弾かない** (見るのは長さと plan の上限だけ)。増えた分は減衰と統合の提案で手入れする
- **未整理 (kind 無し) は一級の状態**。急ぐ時は kind 無しで速記してよい。後で `propose` か人が付ける
- **lock** = 消えない・隠れない・本文と状態が変わらない。移動 / label / 関係 / 再生成は通る。lock も unlock も人だけ
- **誰が書いたか (`sender`) は server が決める**。名乗らなくてよい。あなたが書いた記憶は ホストの認証に対応する sender として人にも他 agent にも見える
- **提案 (`propose`)** が agent の「整える」手段。受け入れは人

## C. 判断の基準

### 書く
- `remember({ content, kind, atlasId })`。1 行目は題。結論が先。id や生 SQL や長い log は本文に貼らない (人が web / iOS で読む)
- **context が尽きる前に handoff を 1 本** (`kind: 'handoff'`): 次の一手 / 止まっている理由 / 見ている file / 決めたこと。きっかけは場面で違う — 長い作業の節目、compaction の前 (hook が思い出させる)、終える前。「まだ書いていない」と気づいた時が書く時
- 既存の記憶に足すなら `annotate({ targetMemoryId, content })`。本文を書き換えるのは自分が書いた記憶の訂正だけ
- 古い理解を新しい理解で置き換えたら `remember({ content, supersedes: ['mem_…'] })` か `supersede_memory({ id, supersededBy })`。消さない

### どこへ
- project のことは **project の atlas** (session 開始の hook が手がかりを出す。無ければ `read({ resource: 'atlas' })`)
- 自分の癖・訂正・失敗の post-mortem は **`/agent/<自分>`**、他 agent にも効く知識は `/agent`、project の文脈の学びは project atlas。**ホストの local memory は creo の写し** (Claude の例: `~/.claude/projects/<p>/memory/`)。次の session でも手元に置きたい記憶には label **`cache:<自分>`** (Claude は `cache:claude`) を付ける — Claude Code では hook が creo → local を生成する。local に直接書いた事実は次の同期で「creo に未登録」として index の別節に出る。詳細: [agent-atlas.md](reference/agent-atlas.md)
- mako 個人の情報や一回性の感想は書かない

### 読む
- 「今日の脳」(やること / 考え / 出来事 / 提案 / lock 中) が instructions に届いていれば利用する。途中で `briefing({ atlasId })`
- 前提にする前に `search({ query, atlasId })`。`atlasId` は既定でその atlas だけ。子 atlas も一緒に引くなら `search({ query, atlasId, includeDescendants: true })` (親 + read できる子孫。`/agent` を親にすれば `/agent/<自分>` も入る)
- todo を始める前に `read({ resource: 'todo' })`。終えたら `complete_todo({ id })`

### 整える (提案する)
- 種類が違う / label を足したい / 2 つが同じ / 矛盾している → `propose({ kind, target, change, reason })`。判断は人
- label は先に `label_list()` で既存を見て、合うものを `label_attach({ memoryId, labelIds })`。無ければ文法の中で `label_create({ name })` (既存の family に寄せる。family の例: `repo:` / `priority:` / `size:` / `phase:` / `mark:` / `area:`)。似た label が並んだら `propose({ kind: 'label_merge' })`
- 要らない記憶は `forget` より archive や supersede。lock 中は 409 — unlock は人に頼む

### 人だけができること
lock と unlock / review 段の提案の受け入れ。agent は頼む・提案する。

## D. 他者と

- 記憶は **一緒に働く人が web / iOS で読み、連動する他の agent (codex / grok / 他の LLM / 別 session の claude) も同じ atlas を読む**。題を 1 行目に、結論を先に、前提と根拠を短く
- 他 agent への引き継ぎは **todo + annotation** (creo が SSOT。wire や chat は通知)。相手の `/agent/<name>` には書かない (読むのは自由)
- 規約の正本は `/agent` の charter (agent 共通)。この skill はホスト共通の写し + command hook
- 「今日も上手くできました」の日記は書かない。**次に同じ局面で助かるか**だけが基準

## E. 罠 (tool の説明文が SSOT。ここは非自明なものだけ)

- `annotate` は `targetMemoryId`、`get_annotations` は `memoryId`
- `create_todo` に title は無い (content の 1 行目)。`priority` は `low | medium | high`
- `read` の filter は strict (未知 key はエラー)。`resource` は `memory | atlas | todo`
- `category` は deprecated (対応表で `kind` に写る、対応の無い値は未整理)。**`tags` 引数は無い** (spec 25 D11、2026-09-07 に撤去)。旧 tag の語彙は label に写した分だけ引ける (`labelIds`)。本文に語があれば `search({ query })` で当たる
- `remember` の `labelIds` に無い label を渡すとエラー (先に `label_create`)。label 名の `/` は atlas 専用で使わない、大小は同じ扱い (`Area:MCP` = `area:mcp`)
- `update_memory` / `forget` / `supersede` は lock 中に 409。`generate_story` / `generate_compass` の再生成は lock を見ずに上書き
- `search({ atlasId })` は既定で子 atlas を含まない。含めるなら `includeDescendants: true` (読めない子は黙って落ちる。`scope: 'all'` では無意味)

recipes: [recipes.md](reference/recipes.md) / 地図: [tools-map.md](reference/tools-map.md)

Atlas のパス・slug は ID ではない。`read({ resource: "atlas" })` で実際の ID を解決する。自分の軸は利用中のホスト（claude / codex / grok）に合わせ、他 agent の軸に書かない。未接続なら作業を続け、記憶の取得・保存が未実施であることを伝える。
