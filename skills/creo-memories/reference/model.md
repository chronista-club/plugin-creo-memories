# model — creo の世界の形 (spec 25 の要約)

正本は creo-memories の `docs/spec/25-memory-classification.md` (D1〜D30) と `docs/design/39-memory-classification-structure.md`。ここは agent が推論に使う分だけ。

## 記憶は 3 系統 — 終わり方で決まる

| 系統 (`lineage`) | 何か | 終わり方 = 印 |
|---|---|---|
| **出来事** (event) | 起きたこと。変わらない | 終わらない (archive はできる) |
| **考え** (thought) | 理解・判断・設計。より良い考えに置き換わる | `superseded_by` (置換) |
| **やること** (action) | 行動の予定。片付く | `completed_at` (完了) |

系統は **種類 (`kind`) から導出**され、保存されない。`status` 列は無い (状態は系統ごとに 1 つの印)。

## 種類は 16 (`kind`)

| 系統 | 種類 |
|---|---|
| 出来事 (6) | `annotation` (注釈) / `log` (作業の記録) / `milestone` (節目) / `reference` (資料) / `handoff` (引き継ぎ) / `incident` (壊れた) |
| 考え (9) | `decision` (決めた) / `context` (背景) / `design` (設計) / `learning` (学び) / `spec` (仕様) / `idea` (思いつき) / `guide` (手順) / `plan` (計画) / `story` (物語、生成物) |
| やること (1) | `todo` |

**未整理 (kind 無し) は一級の状態** (D9)。急ぐ時は kind 無しで速記し、後で `propose({ kind: 'classify' })` か人が付ける。`category` は deprecated — 旧 → 新の対応表で `kind` に写される (対応の無い値だけ未整理)。**`tags` 引数は無い** (D11、2026-09-07 に MCP / REST から撤去。旧 tag の語彙は `metadata.legacy_tags` に残るが検索の面には出ない。本文に語があれば embedding で当たる、残す価値のある語は label に)。新しく書くなら `kind` と `labelIds`。

## 語彙は label (文法だけ決まっている)

- 自由 tag は無い (D11)。語彙は **種類 + label**
- label は **ユーザー単位**。**文法は `family:leaf[:leaf]`** — `:` は構造 (左が広く右が狭い、`phase:2:waiting`)、`-` は語の中の連結 (`cross-project`)、`/` は atlas の path 専用で label には使わない、大小は無視 (key は小文字)。決まっているのは記号の使い方だけで、family も葉も自由
- **agent も作れる** (D19 は 2026-09-06 に改訂。旧「人が作る」は撤回)。作る前に `label_list` で既存を見て、合う family に寄せる。増えた葉は `propose({ kind: 'label_merge' | 'decay' })` で手入れする。**server が見るのは長さ (≤64) と plan の上限 (slate 20 / desk 1,000) だけ**で、文法は弾かない (規約)
- label は user 単位なので一覧は人ごとに違う (新しい user は 0 件)。family の例: `repo:<git remote の basename>` (他 atlas の code base を指す時だけ) / `priority:high|medium|low` / `size:s|m|l` / `phase:<n>[:<状態>]` / `mark:<人の印>` (dogfood、roadmap、backlog …) / `area:<技術や領域>` (surrealdb、mcp、deploy …)
- 旧 tag は `metadata.legacy_tags` に残るだけ (検索の面には出ない。label に写したものだけ `labelIds` で引ける)

## 印と属性

| 列 | 意味 |
|---|---|
| `completed_at` / `superseded_by` / `archived_at` | 印 (上の表)。archive = 隠す (消さない) |
| `locked_at` | **lock** = 消えない・隠れない・本文と状態が変わらない (D21)。atlas の移動、label の付け外し、関係、story / compass の再生成は**通る**。lock / unlock は人だけ。lock は TTL に勝つ |
| `hot_until` | 今ホットな記憶 (期限つき) |
| `priority` (1〜3) / `due_at` | やること の属性 |
| `sender` / `channel` | **誰が書いたか / どこから** (D17)。server が MCP client の名乗り (`clientInfo.name`) から決める。agent が自分で名乗る必要は無い。ホストの認証に対応する sender / `users:<id>` |
| `ttl` | 一時の記憶 (期限で消える)。`update_memory({ ttl: null })` で永続に |
| `place` | 物理の場所 (器だけ、iOS の速記から) |

## 固定化 — 提案と受け入れ (D4 / D20)

- 記憶の分類・統合・蒸留・矛盾・減衰・重複・剪定は **agent が `propose` で提案し、人が受け入れる**。提案は一つの入れ物 (`proposals`)、受け入れは 3 段 (報告のみ / 受け入れ・却下 / 提案しない)
- review 段の `proposal_accept` は人だけ (agent の自己承認は server が拒否)
- **briefing** (D14) = session 開始に自動で入る「今日の脳」: やること (priority 順) / 考え (有効なもの) / 出来事 (直近) / 提案 (open) / lock 中。`briefing` tool で読み直せる

## 自己と cache (D7 / D8 / D28)

- 自己は actor 軸の atlas: 人は `/Personal`、agent は `/agent/<name>` (`/agent/<自分>`)。agent 共通の知識は `/agent`
- **atlas を指す引数 (`atlasId` / `atlas_id`) は id / slug / 表示名のどれでも**。解決できない値は「atlas が無い」のエラー (2026-09-08 から読みも書きも。それまで読みは黙って 0 件だった)。推定名を渡す前に `read({ resource: "atlas" })` で実在を確かめる
- **外部脳は一つ (creo)。local (`~/.claude/projects/<p>/memory/`) は写し** — 起動高速化と、creo に繋がらない時の可用性のため。同期は creo → local の一方向 (0.57.0、`scripts/sync-local-cache.sh`。Claude Code の SessionStart から背景で 1 時間に 1 回)。写すのは **label `cache:claude` が付いた記憶 ∩ (この repo の atlas ∪ `/agent/claude` ∪ `/agent`)**、上限 150 件 (更新日の新しい順、超えた分は index に件数だけ)。1 記憶 = 1 file (`metadata.cache.name` か題から file 名)、MEMORY.md は index。creo に無い local file は消さず index の別節に並ぶ (= local にしか無い事実の検出器)。認証は `~/.config/creo-memories/api-key` (chmod 600) か env `CREO_API_KEY`、無ければ黙って skip。local に直接書かない: remember + label `cache:<自分>`。Codex / Grok の local への写しは未実装 (label は同じ器)

## つながり (D29)

- 関係は edge (`derived_from` / `references` / `extends` / `annotates`)。**確からしさ (`confidence`) と行為者 (`created_by`) は edge の側**にある (記憶の列ではない)
- `remember` の `derivedFrom` / `references` / `supersedes` / `extends` / `derives` と `confidence` / `relationReason` で張る
