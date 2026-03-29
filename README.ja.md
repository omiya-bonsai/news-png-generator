# Raspberry Pi 側セットアップ手順（M5PaperS3 News Server v2）

English: [README.md](README.md)

このリポジトリは Raspberry Pi 側の生成・配信ロジックです。全体像は統合ハブ [m5papers3-news-system](https://github.com/omiya-bonsai/m5papers3-news-system)、M5PaperS3 側は [M5PaperS3_NewsDashboard](https://github.com/omiya-bonsai/M5PaperS3_NewsDashboard) を参照してください。

## ジャンプリンク

- 統合ハブ:
  - [omiya-bonsai/m5papers3-news-system](https://github.com/omiya-bonsai/m5papers3-news-system)
- M5PaperS3 側:
  - [omiya-bonsai/M5PaperS3_NewsDashboard](https://github.com/omiya-bonsai/M5PaperS3_NewsDashboard)

![M5PaperS3 device photo](img/01.jpeg)

## 概要

本ドキュメントは **M5PaperS3 ニュース表示システムのサーバ側構成（最新版）** をまとめたものです。

従来構成から次の改善が追加されています。

- index.png + page1〜page6.png の6記事構成
- index.version 差分検出方式
- SDキャッシュ連携前提設計
- systemd timer 自動更新
- HTTP常駐サービス
- 再起動後の完全自動復旧

---

## システム構成（最新版）

```text
NHK RSS
   ↓
make_pages_png.py
   ↓
index.png
page1.png
page2.png
page3.png
page4.png
page5.png
page6.png
index.version
   ↓
python http.server (port 8010)
   ↓
M5PaperS3
```

---

## 関連リポジトリ

- 統合ハブ:
  - [omiya-bonsai/m5papers3-news-system](https://github.com/omiya-bonsai/m5papers3-news-system)
- M5PaperS3 側:
  - [omiya-bonsai/M5PaperS3_NewsDashboard](https://github.com/omiya-bonsai/M5PaperS3_NewsDashboard)

このリポジトリは、Raspberry Pi 側の次を担当します。

- RSS 取得
- PNG 生成
- `index.version` 生成
- HTTP 配信
- `systemd` 運用

---

## ディレクトリ構成

例:

```text
~/m5papers3
├── make_pages_png.py
├── index.png
├── page1.png
├── page2.png
├── page3.png
├── page4.png
├── page5.png
├── page6.png
├── index.version
└── fonts/
    ├── NotoSansCJK-Regular.ttc
    └── NotoSansCJK-Bold.ttc
```

---

## フォント要件（重要）

このリポジトリには `fonts/` 配下のフォントファイルを含めていません。  
ファイルサイズが大きいため、各環境で別途配置する前提です。

現在の `make_pages_png.py` は、少なくとも次のフォントを前提にしています。

- NotoSansCJK-Regular.ttc
- NotoSansCJK-Bold.ttc

配置先:

```text
/home/bonsai/m5papers3/fonts/
```

つまり、実際には次のパスに置かれている必要があります。

```text
/home/bonsai/m5papers3/fonts/NotoSansCJK-Regular.ttc
/home/bonsai/m5papers3/fonts/NotoSansCJK-Bold.ttc
```

フォント配置先を変更する場合は、`make_pages_png.py` 内の次の定数も合わせて修正してください。

- `FONT_REGULAR`
- `FONT_BOLD`

フォントが存在しない場合、`ImageFont.truetype(...)` の初期化でスクリプトは失敗します。

補足:

- このフォント要件は Raspberry Pi 側の PNG 生成に必要です
- M5PaperS3 本体側スケッチには不要です

---

## Python 仮想環境の準備

作成:

```bash
python3 -m venv ~/myenv
```

有効化:

```bash
source ~/myenv/bin/activate
```

必要ライブラリ:

```bash
pip install pillow feedparser
```

---

## PNG 生成スクリプト動作確認

実行:

```bash
cd ~/m5papers3
python make_pages_png.py
```

生成確認:

- index.png
- page1.png
- page2.png
- page3.png
- page4.png
- page5.png
- page6.png
- index.version

---

## index.version 差分検出方式（重要）

PNG より先に `index.version` を取得します。

例:

```text
20260326-1910
```

M5PaperS3 側では次のように判定します。

```text
前回値と一致 → index.png 再取得しない
```

つまり、次を同時に実現します。

- 通信削減
- ePaper書換削減
- バッテリー消費削減

現在の `index.version` は、一覧だけでなく詳細ページの変更も反映できるよう、記事タイトル・日時・要約をもとに生成する前提です。

---

## HTTP 配信確認

テスト起動:

```bash
cd ~/m5papers3
python3 -m http.server 8010
```

確認:

```text
http://<RaspberryPiのIP>:8010/index.png
```

---

## systemd による PNG 自動生成

service 作成:

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/m5news-generate.service
```

内容:

```ini
[Unit]
Description=Generate M5PaperS3 news PNG pages

[Service]
Type=oneshot
WorkingDirectory=/home/bonsai/m5papers3
ExecStart=/home/bonsai/myenv/bin/python make_pages_png.py
```

---

## timer 作成（5分周期）

```bash
nano ~/.config/systemd/user/m5news-generate.timer
```

内容:

```ini
[Unit]
Description=Run news PNG generator every 5 minutes

[Timer]
OnBootSec=30
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
```

有効化:

```bash
systemctl --user daemon-reload
systemctl --user enable m5news-generate.timer
systemctl --user start m5news-generate.timer
```

確認:

```bash
systemctl --user list-timers
```

---

## HTTP サーバ常駐化

service 作成:

```bash
nano ~/.config/systemd/user/m5news-http.service
```

内容:

```ini
[Unit]
Description=M5PaperS3 PNG HTTP server
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m http.server 8010
WorkingDirectory=/home/bonsai/m5papers3
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

`[Install]` が無いと、手動で `start` すれば動いても、`enable` した時の自動起動対象になりません。  
再起動後も確実に HTTP サーバを立ち上げたい場合は、この `WantedBy=default.target` が重要です。

有効化:

```bash
systemctl --user daemon-reload
systemctl --user enable m5news-http.service
systemctl --user start m5news-http.service
```

確認:

```bash
systemctl --user status m5news-http.service
```

---

## 再起動後も自動起動させる

linger 有効化:

```bash
loginctl enable-linger bonsai
```

ログイン不要で常駐します。

---

## ログ確認方法

PNG生成ログ:

```bash
journalctl --user -u m5news-generate.service
```

HTTPログ:

```bash
journalctl --user -u m5news-http.service
```

---

## 動作確認チェックリスト

確認:

- 再起動後 HTTP server 起動
- 5分周期 PNG 更新
- index.version 更新確認
- index.png 表示確認
- page1〜page6.png 表示確認
- M5PaperS3 自動追従確認

---

## 推奨更新周期

```text
5分
```

理由:

- RSS 更新頻度と整合
- 通信量削減
- ePaper寿命延長
- バッテリー節約

---

## トラブルシューティング

PNG 未更新:

```bash
systemctl --user status m5news-generate.timer
```

HTTP 接続不可:

```bash
systemctl --user status m5news-http.service
```

ポート確認:

```bash
ss -tulpn | grep 8010
```

index.version 未更新:

```bash
cat index.version
```

フォント読み込み失敗:

- `fonts/` 配下に必要な `.ttc` があるか確認
- `make_pages_png.py` の `FONT_REGULAR` / `FONT_BOLD` のパスが実環境と一致しているか確認

---

## 今後の拡張候補（優先順）

優先度 高:

- MQTT 差分通知連携
- nginx 置換
- gzip 転送

優先度 中:

- 複数 RSS 統合
- category 分離表示

優先度 低:

- HTTPS 化
- CDN 配信

## License

このリポジトリは [MIT License](LICENSE) です。
