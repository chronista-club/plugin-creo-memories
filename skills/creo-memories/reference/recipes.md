# recipes — 7 つの場面

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
- 根拠の記憶へ `references` / `derivedFrom` で繋ぐ。書いた後に気づいたら `relate({ from, to: ['mem_…'], type: 'derived_from' })`

## 5. やること (todo)

```
create_todo({ content: '# <やること>\n…', priority: 'high', atlasId })
list_todos({ atlasId })
complete_todo({ id })
```
- 進捗は todo に `annotate`。完了と結果と PR を 1 手なら `complete_with_context({ memory_id, result, url })`
- 種類が todo でない記憶に priority は付かない (作る時は server が捨てて warn、`update_todo` では ValidationError)
- 優先度・期限を外す: `update_todo({ id, priority: null, dueAt: null })`。完了を外す: `update_todo({ id, status: 'pending' })`

## 6. 他 agent・人と

- 相手が拾う前提で書く: 題 / 結論 / 次の一手。相手の名前は本文に (sender は server が付ける)
- 引き継ぎは todo (相手の atlas か project atlas) + annotation。wire / chat は通知だけ
- 人に頼むこと (lock / review 段の提案の受け入れ) は todo か annotation で**頼む**。代わりにやろうとしない (server が拒否する)
- 会話の記録が要るなら `record_work_log({ content, workLogType: 'decision', sender, receiver })`

## 7. スレッドを編む — Atlas をまたいで 1 つの話を束ねる

スレッド = `kind: 'context'` + label `mark:thread` の記憶。仲間 = スレッドから `references` で指した記憶 (1 段)。web の `/threads` が、仲間を やること / 考え / 出来事 に分けて束ねて見せる。web は見るだけで、編むのは会話の中の agent

```
label_list()   // mark:thread が無ければ label_create({ name: 'mark:thread' })
remember({
  content: `thread "<題>" {
    now "<今どこ (自由文、markdown)>" id="mem_…"
    waiting "<何を・誰を待っているか>" id="mem_…"
    remaining "<残り>"
    remaining id="mem_…"
    note """
        欄に収まらない話 (理由・ためらい・経緯)
        """
}`,
  contentType: 'application/vnd.kdl',
  kind: 'context',
  labelIds: ['mark:thread'],   // label は名前でも渡せる
  references: ['mem_…'],
  supersedes: [],   // 新しいスレッド。省くと似た記憶の検出で保存が止まりやすい (スレッドは仲間の要約なので当たりやすい)
  atlasId,
})
```
- 題は `thread` の引数 (KDL の記憶は一覧の題が「KDL (n B)」になるので、スレッドの題は本文に書く)
- 欄は `now` (今どこ) / `waiting` (待ち) / `remaining` (残り) / `note` (メモ) の骨だけ。値は自由文。同じ欄は何行書いてもよい。知らない欄も名前のまま描かれる
- 行の `id="mem_…"` は 1 行に 1 つ、`mem_…` の宛名だけ (slug や UUID は不可)。その記憶が仲間 (`references`) にいれば、web は種類・題・完了を**今の状態で**出す — 題や状態を本文に写さない。id を付けた記憶は `references` にも入れる。文の無い `remaining id="mem_…"` は記憶の題で描かれる。web がこの id を記憶の題に描き替えるので、「id を本文に貼らない」の例外はこの属性だけ。文の中には書かない
- 形に収まらない KDL (数・`id` 以外の属性・子を持つ欄、`id` が `mem_…` でない行、`thread` の外のノード) はスレッド全体が欄ではなく木で描かれる。KDL として読めなければ保存時に行・列が返るので、直して書き直す
- 欄を進める: `patch_memory({ id, before, after })` (スレッドの id は変わらない)
- 仲間を足す・外す: `relate({ from: '<スレッドの id>', to: ['mem_…'] })` / `unrelate({ from: '<スレッドの id>', to: ['mem_…'] })` (`type` 省略 = `references`)。スレッドの id は変わらない。足した仲間は本文の行にも `id="mem_…"` で書く (逆も同じ: 行から消したら `unrelate`)
- スレッドを作り直す (`supersedes`) のは、話そのものが別の話になった時だけ (例: 3.3 系が終わって 3.4 系が始まった)。日々の更新は `patch_memory` と `relate` / `unrelate` で、同じ id のまま
