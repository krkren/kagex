# KAGEX Sample — web 版 起動手順

このフォルダ (`site/`) は自己完結です。フォルダごとコピー / 別ホストへアップロードしても動きます。

## 起動 (ローカル確認)

```
python serve.py            # → http://localhost:8100/
```

ブラウザ (**Chrome / Edge**、JSPI を標準搭載する新しめの版) で
**http://localhost:8100/** を開くと、引数なしで案件が起動します。
別ポートで開くなら `python serve.py 8200` のように引数指定。

> Windows では一部のポート (例 8123) が予約されていて `WinError 10013` になることがあります。
> その場合は 8080 / 8100 / 8200 など別のポートを使ってください。

## 構成

| ファイル | 役割 |
|---|---|
| index.html / krkrz.js / krkrz.wasm / krkrz.data | 共有エンジンバイナリ (案件非依存) |
| webconfig.js | 起動時構成 (webbase / 起動引数) |
| resource/ + resource.list | config.cf(文字コード) / messages / フォント |
| gamedata/ | 案件データ (web:// でオンデマンド取得) |
| gamedata.krkrz_files.json | autopath 用ファイル一覧マニフェスト |
| krkrz_prefetch.json | 起動後バックグラウンド先読みリスト (delivery:"prefetch" 指定時のみ) |

## 配信 (COOP/COEP 必須)

SharedArrayBuffer/pthread のため、配信サーバは以下ヘッダが必須:
`Cross-Origin-Opener-Policy: same-origin` / `Cross-Origin-Embedder-Policy: require-corp`
(同梱 `serve.py` は付与済み)。itch.io は「SharedArrayBuffer support」を有効にすれば配信可。

リクエスト URL は小文字に正規化されるため、case-sensitive なサーバに置く場合は
小文字→実ファイル名の解決が必要 (同梱 `serve.py` は対応済)。

## トラブル時: キャッシュのクリア

アセット更新後に古いデータが出る等の場合、URL に `?opfsclear=1` を付けて一度開くと
web:// の永続キャッシュ (OPFS) を全消しして起動する (セーブデータは消えない)。

## 再生成 (krkrz_web 側)

このサイトは krkrz_web の共有バイナリ + この案件の `web-config.json` から生成されています。
案件データや設定を更新したら、krkrz_web フォルダで再ステージング:

```
make PROJECT_DIR=/home/jake/kagex run     # ステージング + ローカル起動
make PROJECT_DIR=/home/jake/kagex web     # ステージングのみ (site を再生成)
```
