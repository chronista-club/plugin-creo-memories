# agent-atlas — `/agent` と `/agent/<自分>`

正本は creo の `/agent` atlas の charter memory (slug `agent-charter`)。ここはホスト共通の要約。

| atlas | 誰の | 何を |
|---|---|---|
| `/agent` | 全 agent 共通 | どの agent が読んでも効く横断知識 (tool の罠、handoff の作法、agent 間の運用合意) |
| `/agent/<自分>` (`/agent/claude` / `/agent/codex` / `/agent/grok`) | その agent 専用 | 自分の癖と訂正、失敗した turn の post-mortem。**他 agent の atlas には書かない** (読むのは自由) |
| project atlas | project | 仕様・決定・todo・work log。agent 自身の都合は書かない |
| `/Personal` | mako | agent は書かない |

## どこに書くか (上から順に)

1. その project でしか意味が無い → project atlas
2. project に依らず、自分にだけ効く → `/agent/<自分>`
3. project に依らず、他の agent にも効く → `/agent`
4. mako 個人の情報・一回性の感想 → 書かない

迷ったら `/agent/<自分>` に書き、後で他 agent にも効くと分かったら `/agent` に移す (supersede)。

## local との関係 (D8 / D28)

**正本は creo。** ホストの local memory（Claude では `~/.claude/projects/<project>/memory/`） は写しで、役目は起動高速化と、creo に繋がらない時の可用性。
- 自分について学んだら **まず `/agent/<自分>` に remember**、同じ手で local も更新 (write-through)
- creo に繋がらない間に得た訂正は local に置き、復帰したら creo へ送る
- creo → local の自動生成は plugin の次版 (この版は言葉だけ揃えた)

## 読む

- project atlas の「今日の脳」は注入済みか確認する。`/agent` と `/agent/<自分>` は自動注入が無い — 作業に関係しそうな時に自分で引く: `search({ query, atlasId: '<解決した /agent の ID>', includeDescendants: true })` (親 `/agent` + read できる子 = `/agent/<自分>` も一度に。他 agent の atlas も読めれば入る)

## 書く

- 誰が書いたかは `sender` (server が ホストの認証に対応する sender を付ける)。tag は要らない
- 発見日と由来 (どの session / project で気づいたか) を本文に。古い理解は `supersedes` で置き換える
- 「次に同じ局面で助かるか」だけが基準
