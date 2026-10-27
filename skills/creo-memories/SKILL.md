---
name: creo-memories
description: creo-memories = 外部脳。context が尽きても、session / machine / model / 人をまたいで続きができる場所。書くのは「次に拾う誰かのため」、読むのは「自分が始めた気になる前」。
metadata:
  version: 0.68.1
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
- **読む**のは「自分が始めた気になる前」。session 開始の「今日の脳」は既定の atlas の分。project の続きは `briefing({ atlasId })`。過去の決定を前提にする前に `search`
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
- **context が尽きる前に handoff を 1 本** (`kind: 'handoff'`): 次の一手 / 止まっている理由 / 見ている file / 決めたこと。きっかけは場面で違う — 長い作業の節目、compaction の後 (SessionStart の hook が促す。要約を材料に書く)、終える前。「まだ書いていない」と気づいた時が書く時
- Atlas をまたぐ 1 つの話は **スレッド**に束ねる: `kind: 'context'` + label `mark:thread`、本文は KDL の `thread "<題>" { now / waiting / remaining / note }`、仲間は `references`。詳細: [recipes.md](reference/recipes.md) の 7
- **スレッドの本文は現在地。** 作業が進んだら既存の行を書き換え、解けた待ち・済んだ作業を畳む。経緯は注釈、前の全文は版に残る。完了報告を `now` に追記し続けない。引き継ぎ・完了報告の前に本文も読み直す
- 既存の記憶への補足は `annotate({ targetMemoryId, content })`。スレッドの現在地は上記の手順で更新する。それ以外の本文を書き換えるのは、自分が書いた記憶の訂正だけ
- 古い理解を新しい理解で置き換えたら `remember({ content, supersedes: ['mem_…'] })` か `supersede_memory({ id, supersededBy })`。消さない

#### 新しい記録を保存する前に

これから作る記憶・注釈・要約・引き継ぎの原稿に適用する。保存済みの記憶を推敲のために一括更新しない。

- 結論を先に置き、確認したこと・未確認点・次の作業を必要に応じて分ける。短い記録に空の見出しや固定のひな形を足さない。
- 誰が何を決めたか、何を確認したか、どの条件で次へ進めるかを読み取れるか確かめ、追いにくい箇所だけ直す。担当・原因・次の作業が不明なら推測で埋めない。
- 保存前に原稿と根拠を照合する。数値・対象・条件・否定・確かさを保ち、「実装済み」「検証済み」「公開済み」を混同しない。「未確認」を「問題なし」に変えず、予定を完了として書かない。
- ユーザーの発言や裁定の引用、コードはそのまま保つ。意味が明確な専門用語や箇条書きは残す。読みやすさのために必要な根拠を削らない。

例: 「修正済み、実機未確認」を「修正は完了した。実機ではまだ確認していない」と分けても、「修正が完了し、正常に動作している」とは書かない。

### どこへ
- project のことは **project の atlas** (session 開始の hook が手がかりを出す。無ければ `read({ resource: 'atlas' })`)
- 自分の癖・訂正・失敗の post-mortem は **`/agent/<自分>`**、他 agent にも効く知識は `/agent`、project の文脈の学びは project atlas。**ホストの local memory は creo の写し** (Claude の例: `~/.claude/projects/<p>/memory/`)。次の session でも手元に置きたい記憶には label **`cache:<自分>`** (Claude は `cache:claude`) を付ける — Claude Code では hook が creo → local を生成する。local に直接書いた事実は次の同期で「creo に未登録」として index の別節に出る。詳細: [agent-atlas.md](reference/agent-atlas.md)
- mako 個人の情報や一回性の感想は書かない

### 読む
- 「今日の脳」(やること / 考え / 出来事 / 提案 / lock 中) は instructions に届く既定の atlas の分。project の分は `briefing({ atlasId })`
- 前提にする前に `search({ query, atlasId })`。`atlasId` は既定でその atlas だけ。子 atlas も一緒に引くなら `search({ query, atlasId, includeDescendants: true })` (親 + read できる子孫。`/agent` を親にすれば `/agent/<自分>` も入る)
- todo を始める前に `read({ resource: 'todo' })`。終えたら `complete_todo({ id })`

### 整える (提案する)
- 種類が違う / label を足したい / 2 つが同じ / 矛盾している → `propose({ kind, target, change, reason })`。判断は人
- **退役の提案** (server が積む `duplicate` / `contradiction`、`change.retire` 付き。新しい考えが立った時に同じ話題の古い考えを見つけたもの) は session の始めに読み上げ、**人の GO があった分だけ** `proposal_accept`。段は report で agent が押せるが、押すのは人が決めてから (recipes 8)
- label は先に `label_list()` で既存を見て、合うものを `label_attach({ memoryId, labelIds })` (`labelIds` は id でも名前でも)。無ければ文法の中で `label_create({ name })` (既存の family に寄せる。family の例: `repo:` / `priority:` / `size:` / `phase:` / `mark:` / `area:`)。似た label が並んだら人に頼む (`propose({ kind: 'label_merge' })` は受け入れても今は記録だけで、統合は適用されない)
- 要らない記憶は `forget` より supersede (archive の書き口はまだ無い)。lock 中は 409 — unlock は人に頼む

### 人だけができること
lock と unlock / review 段の提案の受け入れ / 退役の提案 (report 段) を「押す」判断。agent は頼む・提案する・読み上げる。

## D. 他者と

- 記憶は **一緒に働く人が web / iOS で読み、連動する他の agent (codex / grok / 他の LLM / 別 session の claude) も同じ atlas を読む**。題を 1 行目に、結論を先に、前提と根拠を短く
- 他 agent への引き継ぎは **todo + annotation** (creo が SSOT。wire や chat は通知)。相手の `/agent/<name>` には書かない (読むのは自由)
- 規約の正本は `/agent` の charter (agent 共通)。この skill はホスト共通の写し + command hook
- 「今日も上手くできました」の日記は書かない。**次に同じ局面で助かるか**だけが基準

## E. 罠 (tool の説明文が SSOT。ここは非自明なものだけ)

- `annotate` は `targetMemoryId`、`get_annotations` は `memoryId`。注釈・返信・`remember({ annotates })` は対象の Atlas を継承し、明示した `atlasId` が優先。通常の `remember` で `atlasId` を省略すると Personal へ保存され、警告が返る。プロジェクトの記憶では保存先を明示する
- `create_todo` に title は無い (content の 1 行目)。`priority` は `low | medium | high`
- `read` の filter は strict (未知 key はエラー)。`resource` は `memory | atlas | todo`
- `category` は deprecated (対応表で `kind` に写る、対応の無い値は未整理)。**`tags` 引数は無い** (spec 25 D11、2026-09-07 に撤去)。旧 tag の語彙は label に写した分だけ引ける (`labelIds`)。本文に語があれば `search({ query })` で当たる
- `remember` の `labelIds` に無い label を渡すとエラー (先に `label_create`)。label 名の `/` は atlas 専用で使わない、大小は同じ扱い (`Area:MCP` = `area:mcp`)
- `update_memory` / `forget` / `supersede` は lock 中に 409。`generate_story` / `generate_compass` の再生成は lock を見ずに上書き
- `search({ atlasId })` は既定で子 atlas を含まない。含めるなら `includeDescendants: true` (読めない子は黙って落ちる。`scope: 'all'` では無意味)
- `search({ query })` の並びは `rankScore` (類似度 + 系統の段)。同じくらい近いなら、いま有効な考え (guide / decision) が出来事 (handoff / log / 注釈) より上に来る。**完了した todo は既定で出ない** — 「前にやった作業」を探すなら `includeCompleted: true` か `lineage: "event"`。`score` は類似度のままなので、閾値の感覚は変わらない
- 通常検索で根拠に届かない時は、必要に応じて `search({ query, atlasId, depth: "deep" })`（「深く探す」）。本文をAIで照合するため追加数秒と費用がかかる。常時・自動反復にはしない。`deepSearch.applied` を確認し、falseなら通常結果へのfallback。query必須、`useAtlasContext`との併用不可。`read`にはdepthを渡さない

recipes: [recipes.md](reference/recipes.md) / 地図: [tools-map.md](reference/tools-map.md)

Atlas のパス・slug は ID ではない。`read({ resource: "atlas" })` で実際の ID を解決する。自分の軸は利用中のホスト（claude / codex / grok）に合わせ、他 agent の軸に書かない。未接続なら作業を続け、記憶の取得・保存が未実施であることを伝える。
