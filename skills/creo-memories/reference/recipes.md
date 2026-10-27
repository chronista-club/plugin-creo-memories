# recipes — 8 つの場面

引数は tool の説明文が SSOT。ここは順番と判断だけ。

## 1. session を始める

1. instructions の「今日の脳」を読む (自動。既定の atlas の分)。hook が出す atlas の手がかりから project の Atlas ID を解決し、`briefing({ atlasId })`
2. 続きなら `read({ resource: 'todo' })` で未完を確認し、直前の handoff を `read({ resource: 'memory', filter: { kind: 'handoff', atlasId }, limit: 3 })` (新しい順。`search({ query: 'handoff' })` は意味の近い順なので、新しい handoff が出てこないことがある)
3. 自分の癖が関係しそうなら `search({ query, atlasId: '<解決した自分の Atlas ID>' })` と `search({ query, atlasId: '<解決した /agent の ID>' })`

## 2. 引き継ぐ (handoff) — context が尽きる前に (節目 / compaction の後 / 終える前)

```
remember({
  content: '# <題>\n次の一手: …\n止まっている理由: …\n見ている file: …\n決めたこと: …',
  kind: 'handoff',
  atlasId,
})
```
- 関連する todo があれば `annotate({ targetMemoryId: todoId, content: '進捗: …' })` で todo 側にも
- compaction の後に SessionStart の hook が促す (縮む前の hook の声は agent に届かないので、要約を材料に後から書く)。前の handoff があれば `supersedes: ['mem_…']` で置き換える

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
- 進捗は todo に `annotate`。完了と結果と PR を 1 手なら `complete_with_context({ memory_id, result, url, service: 'github' })` (`url` は `service` と一緒の時だけ残る。`service` が無いと黙って捨てられる)
- その作業に thread があれば、完了・待ちの解消・方針変更を本文にも反映する (7)。thread への注釈だけでは、古い `now` / `waiting` / `remaining` は変わらない
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
        今も判断に必要な前提・制約
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
- 題は `thread` の引数。スレッドの形なら、一覧・検索にもこの題が出る
- **本文は現在地を保つ。** `now` は今の結論、`waiting` は未解決の待ち、`remaining` は残る作業、`note` は今も必要な前提・制約。複数の話題は複数行で表せるが、同じ話題が進んだら既存の行を書き換える。完了報告・試行・検証ログを `now` や `note` に積み続けない
- 行の `id="mem_…"` は 1 行に 1 つ、`mem_…` の宛名だけ (slug や UUID は不可)。その記憶が仲間 (`references`) にいれば、web は種類・題・完了を**今の状態で**出す — 題や状態を本文に写さない。id を付けた記憶は `references` にも入れる。文の無い `remaining id="mem_…"` は記憶の題で描かれる。web がこの id を記憶の題に描き替えるので、「id を本文に貼らない」の例外はこの属性だけ。文の中には書かない
- 形に収まらない KDL (数・`id` 以外の属性・子を持つ欄、`id` が `mem_…` でない行、`thread` の外のノード) はスレッド全体が欄ではなく木で描かれる。KDL として読めなければ保存時に行・列が返るので、直して書き直す
- 欄を進める: 結果・根拠・判断の経緯を `annotate({ targetMemoryId: '<スレッドの id>', content: '…' })` に残し、`patch_memory({ id, before, after, note: '待ちが解けた' })` で今の状態へ。解けた `waiting` と済んだ `remaining` は畳む。id は変わらず、前の全文は版に残る。同じ結果が既に注釈されていれば重ねて作らない
- 仲間を足す・外す: `relate({ from: '<スレッドの id>', to: ['mem_…'] })` / `unrelate({ from: '<スレッドの id>', to: ['mem_…'] })` (`type` 省略 = `references`)。本文の行で指す記憶は仲間にも入れる。**過去の行を畳むだけなら線は残す。** `unrelate` は、その記憶が話の仲間でなくなった時だけ
- 別の目的を始める時は、新しいスレッドから閉じたスレッドを `references` で参照する (例: 3.3 系が終わって 3.4 系が始まった)。区切りを付けるためだけに `supersedes` は使わない。日々の更新は `patch_memory` と `relate` / `unrelate` で、同じ id のまま

積み上がった thread を畳む時は、全文・直近の注釈・関連 todo を読み、経緯の要点を注釈してから、**読んだ全文を `before`、短い現在地を `after` にして patch** する。古い予定を今の事実と混ぜない。競合して `before` が合わなければ読み直す。保存後に本文をもう一度読み、現在地・未確認点・次の作業を確認する。引き継ぎ・完了報告の前にもこの確認を行う。

版は web の「履歴」、MCP は `get_memory({ id, expand: ['versions'] })` で辿れる (MCP は版の情報と冒頭、web は前の全文)。server の現在地の更新案も、人が確認して採用すると本文へ反映される。行数・文字数で切り捨てず、今も有効な内容を残す。

### ひと区切りを閉じる・同じ目的を再開する

Web の「スレッド」は「進行中 / 閉じた / すべて」。所有者の unlocked な KDL スレッドで「終了案を作る」を押し、成果・持越し・現行手順への案内と根拠を確認する。生成だけでは本文も状態も変わらない。終了案は review 段で、人が採用する。

- 未完の関連 todo があれば一覧で示され、ボタンは「残件を残して閉じる」。閉じても todo の状態は変わらない。引き継ぐ先や残件を、完了したものとしてまとめない。
- 採用すると同じ ID・参照を保ち、前の本文は版、終了の経緯は注釈に残る。`kind: context` と `mark:thread` のまま `mark:thread-closed` が付き、通常検索でも閉じた記録と分かる。archive / supersede / todo の完了とは別。
- 終了印は専用操作で管理する。`label_create` / `label_attach` / `label_detach` で閉じたり再開したりしない。閉じたスレッドには現在地の更新案は作られず、閉じる前の古い案も適用できない。
- 同じ目的を続けるなら Web の「再開」で理由を残す。本文と ID を保って進行中へ戻り、古い案は復活しない。「終了案の採用取り消し」は採用後の本文が変わっていない時だけ旧本文も戻す。
- 終了案を人へ渡す前に、未完 todo・未確認事項・参照先を照合する。生成・採用の途中で根拠が変わった場合は案を作り直す。閉じることを関連作業すべての完了報告にしない。

## 8. 退役の提案を片づける — session の始めに、人の GO を得てから

server が「新しい考え (guide / decision …) が立ったので、同じ話題の古い考えを退役させませんか」という提案を積む (creo-memories design doc 52。保存時と夜間に、規則で候補を絞り、Haiku が「重複 / 矛盾 / 無関係」と理由を判定したもの)。種類は `duplicate` (同じ手続きの古い版) か `contradiction` (新しい方が古い方法をやめた)、`change.retire = true`、`proposed_by` は `creo`。段は report で agent が `proposal_accept` できるが、**人の明示の GO 無しに押さない**。accept すると古い記憶が新しい記憶に supersede される (検索から消える。`unsupersede` / `proposal_revert` で戻せる)

```
proposal_list({ kind: 'duplicate', open: true })        // contradiction も同じく
// 読み上げる: 新しい記憶 (change.supersede_by) の題、古い記憶 (targets) の題と日付、reason、verdicts の reason
//   「『<新の題>』が立ったので、<古い N 件> を退役させる提案です。受け入れますか？」
proposal_accept({ id })   // 人が GO と言った分だけ。まとめて GO は可
proposal_reject({ id })   // 「違う」と言われたら。理由は古い記憶への annotate で残す (却下された組は 30 日は再提案されない)
```
- 読み上げは session の始め (「今日の脳」の「提案 N 件」が合図)。GO の無い提案は次の session に持ち越す (期限 30 日)
- 期限を過ぎた未決案はinboxと件数から外れる。削除も却下もされず、`proposal_list({ open: false })` で expired として辿れる。期限切れの案はaccept/rejectできないが、期限内に採用した案は期限後も `proposal_revert` で戻せる
- `proposal_list` 末尾の `retirementStats` は、自分宛て・全Atlasの退役提案を作成順の直近20件で集計したもの。採用・却下・取り消し・未決・期限切れを分け、適用は採用の内数。kind/tierは一覧と同じ条件、open/limitは集計に影響しない。`memory_health` にも自分宛て・全Atlasの実績が出る。期限切れを却下に数えず、採用件数を精度の保証や自動適用の許可に読み替えない
- 新旧の判断は人の仕事。agent は reason (なぜ退役なのか) を示し、迷う組は古い記憶を `get_memory` で開いて見せる
- 退役の提案は agent は作れない (`change.retire` を付けた `propose` は server が拒む。積むのは server の規則 `creo` だけ)。手で見つけた古い記憶は、今までどおり新しい記憶に `supersedes` を付けるか `supersede_memory` で
