# recipes — 6 つの場面

引数は tool の説明文が SSOT。ここは順番と判断だけ。

## 1. session を始める

1. instructions の「今日の脳」を読む (自動)。hook が出す atlas の手がかりを見る
2. 続きなら `read({ resource: 'todo' })` で未完を確認し、直前の handoff を `search({ query: 'handoff', kind: 'handoff', atlasId })`
3. 自分の癖が関係しそうなら `search({ query, atlasId: '<解決した自分の Atlas ID>' })` と `search({ query, atlasId: '<解決した /agent の ID>' })`

## 2. 引き継ぐ (handoff) — context が尽きる前に (節目 / compaction の前 / 終える前)

```
remember({
  content: '# <題>\n次の一手: …\n止まっている理由: …\n見ている file: …\n決めたこと: …',
  kind: 'handoff',
  atlasId,
})
```
- 関連する todo があれば `annotate({ targetMemoryId: todoId, content: '進捗: …' })` で todo 側にも
- compaction の前 (PreCompact hook) と Stop の時に思い出す

## 3. 決めた (decision)

```
remember({
  content: '# <決定>\n結論: …\n理由: …\n捨てた案: …\n影響: …',
  kind: 'decision',
  atlasId,
  supersedes: ['mem_…'],   // 前の決定を置き換える時
})
```
- PR や issue と対にするなら `link_external({ memory_id, service: 'github', external_id, url })`

## 4. 壊れた / 直した (incident / learning)

- 起きたことは `kind: 'incident'` (出来事)、そこから得た規則は別に `kind: 'learning'` (考え) — 出来事は変わらず、学びは置き換わる
- 学びが自分の癖なら `/agent/<自分>` へ (`atlasId: '<解決した自分の Atlas ID>'`)、他 agent にも効くなら `/agent`
- 根拠の記憶へ `references` / `derivedFrom` で繋ぐ

## 5. やること (todo)

```
create_todo({ content: '# <やること>\n…', priority: 'high', atlasId })
list_todos({ atlasId })
complete_todo({ id })
```
- 進捗は todo に `annotate`。完了と結果と PR を 1 手なら `complete_with_context({ memory_id, result, url })`
- 種類が todo でない記憶に priority は付かない (server が捨てて warn)

## 6. 他 agent・人と

- 相手が拾う前提で書く: 題 / 結論 / 次の一手。相手の名前は本文に (sender は server が付ける)
- 引き継ぎは todo (相手の atlas か project atlas) + annotation。wire / chat は通知だけ
- 人に頼むこと (lock / review 段の提案の受け入れ) は todo か annotation で**頼む**。代わりにやろうとしない (server が拒否する)
- 会話の記録が要るなら `record_work_log({ content, workLogType: 'decision', sender, receiver })`
