# 配布とホスト対応

新しい `plugin-creo-memories` が正本。旧 `claude-plugin-*` は凍結した参照元。

| ホスト | 入口 | 確認範囲 |
|---|---|---|
| Claude Code | .claude-plugin/plugin.json | 構造検証、共通テスト。実セッション確認待ち |
| Codex | .codex-plugin/plugin.json | 共通 skills・command hooks、構造検証。実セッション確認待ち |
| Grok CLI | Claude 互換形式 | 実機確認待ち |

hooks がある場合はホストの hook 有効化が必要。SessionStart は JSON 入力の cwd を使用し、Python 3 を必要とする。無効な入力は何も出力しない。MCP がある場合、認証・実行許可・接続はホストごとに設定する。インストール済み設定はこの移植では変更しない。

開発は nightly、安定配布は main。両 manifest の version と CHANGELOG を揃え、検証後に main と vX.Y.Z を公開する。ZIP は git archive により追跡済みプラグイン資材だけから作る。

PreToolUse の local memory reminder は Claude の Write イベント用。他ホストの異なる編集ツール名には発火しないため、共有 skill の判断を使う。外部 creo MCP サーバーの plugin-contract CI は旧リポジトリを参照しており、サーバー側での切替は別途必要。

旧サーバー契約テストの version 検出を YAML `metadata.version` に変更する差分は [companion-contract.patch](companion-contract.patch)。サーバー側へは未適用。ローカルではこの差分を一時コピーへ適用し、新プラグインを指定して照合する。CI の checkout 先も `chronista-club/plugin-creo-memories` に変更する必要がある。

## 移植版の検証（2026-09-06）

共有定義・参照先・manifest 同期のテスト、Claude plugin validator、全共有 skill の quick_validate を通過。hook の cwd と JSON 出力の回帰テストを通過。GitHub の Validate workflow は nightly で成功。ホストへの実インストール・MCP 認証・実セッションの発火確認は未実施。
