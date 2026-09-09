# tools-map — 意図から tool へ

tool の説明文と引数は **MCP server の定義が SSOT** (`apps/creo-mcp-server/src/tool-list.ts`、75 tool)。ここは「何をしたい時にどれか」の地図だけ。この表の 1 列目に出る名前の集合が server の一覧と一致することを creo-memories の CI (`plugin-contract.test.ts`) が検証する。引数は tool の説明文を読む (ここに写さない)。

## 読む — 始める前に、前提にする前に

| tool | いつ |
|---|---|
| `briefing` | 「今日の脳」(やること / 考え / 出来事 / 提案 / lock 中)。session 開始時は同じものが instructions に自動で入る。途中で読み直す時に |
| `search` | 過去の決定・経緯を前提にする前に。`kind` / `lineage` / `labelIds` / `sender` / `includeArchived` で絞れる。`atlasId` は子 atlas を含まない |
| `read` | 構造で読む (`resource: memory \| atlas \| todo`、filter は strict = 未知 key はエラー)。todo の一覧はこれ |
| `get_memory` | id / slug で 1 件。`expand: ['labels' \| 'provenance']` |
| `list_recent_memories` | 直近の N 件 |
| `get_annotations` / `get_provenance` / `get_relations` | 注釈の thread / 派生の系譜 / 関係の graph |
| `get_process` / `detect_processes` | 記憶の連鎖 (Process) を読む / 候補を見つける |
| `find_by_external` | GitHub の PR / issue から記憶を逆引き |
| `get_profile` / `project_progress` / `memory_health` | 自分の活動の分布 / atlas の進捗 / 古びた記憶の検出 |

## 書く — 次に拾う誰かのために

| tool | いつ |
|---|---|
| `remember` | 決めた / 学んだ / 壊れた / 渡す / 後で探す。`kind` を付ける (迷えば付けない = 未整理、後で提案が拾う)。`supersedes` で古い理解を置き換える |
| `annotate` / `reply_annotation` | 既存の記憶に進捗・訂正・議論を足す (`targetMemoryId`)。本文を書き換えるより先にこちら |
| `append_memory` / `patch_memory` | 本文の末尾に足す / 一部を置換 (in-place) |
| `update_memory` | 属性 (atlas / ttl / kind / metadata) や本文の全置換。lock 中は 409 |
| `attach_or_ref` | 添付 (file) を紐付ける |
| `link_external` | GitHub の PR / issue と対にする (`service` / `external_id` / `url`) |
| `record_work_log` / `search_work_logs` | agent 間・人との会話の記録と検索 (`workLogType`) |
| `generate_story` / `generate_compass` / `create_process` | atlas の物語 / 羅針盤 / 連鎖を生成 (再生成は上書き) |

## やること

| tool | いつ |
|---|---|
| `create_todo` / `update_todo` / `complete_todo` / `delete_todo` | やること の CRUD。title は無い (content の 1 行目が題)。`priority` / `dueAt` |
| `list_todos` | 未完を priority 順に。`groupBy` / `labelIds` |
| `complete_with_context` | 完了 + 結果 + 外部 link を 1 手で |

## 整える — 種類・置換・label・提案

| tool | いつ |
|---|---|
| `supersede_memory` | 古い記憶を新しい記憶で置き換えたと印を付ける (消さない) |
| `forget` | 本当に要らない時だけ (lock 中は不可)。迷えば archive や supersede |
| `label_list` / `label_create` / `label_attach` / `label_detach` | 先に `label_list` で既存を見る。合うものが無ければ文法 (`family:leaf`) の中で `label_create({ name })`。plan の上限は server が守る |
| `propose` | 分類 / label の統合 / 蒸留 / 矛盾 / 減衰 / 重複 / 剪定の提案。判断は人 (review 段)。report 段 (decay / duplicate) は agent 同士でも閉じる |
| `proposal_list` / `proposal_reject` / `proposal_revert` | 提案の一覧 / 却下 / 受け入れた提案を戻す。report 段 (decay / duplicate) の受け入れは agent もできる |

## 人だけができること (agent は頼む)

| tool | 意味 |
|---|---|
| `lock_memory` / `unlock_memory` / `label_lock` / `label_unlock` | lock = 消えない・隠れない・本文と状態が変わらない (D21)。移動 / label / 関係 / 再生成は通る |
| `proposal_accept` (review 段) | review 段 (classify / label_create / label_merge / distill / contradiction / prune) の受け入れ。agent の自己承認は server が拒否 |

## 場所 (atlas) と共有

| tool | いつ |
|---|---|
| `create_atlas` / `list_atlas` / `get_atlas_tree` / `update_atlas` / `delete_atlas` | project や `/agent/<name>` の器。slug / path で辿れる |
| `update_presence` / `get_presence` | 今何をしているか / 誰がいるか |
| `create_view` / `get_view` / `list_views` / `update_view` / `delete_view` | 記憶の見え方 (view) の定義 |

## session と運用

| tool | いつ |
|---|---|
| `get_session` / `end_session` | session の情報 / 明示的に終える (期限切れの掃除) |
| `get_status` / `get_user` / `generate_api_key` | server / 自分 / API key |
| `system_health` / `diagnose` / `search_logs` | server の健康と log (何かおかしい時) |
