# Raspberry Pi 側セットアップ手順（M5PaperS3 News Server）

## 概要

本ドキュメントは、M5PaperS3 にニュース画像（PNG）を配信するための
Raspberry Pi 側の構築手順をまとめたものです。

役割は以下の通りです。

- RSS 取得
- PNG 生成（page1.png ～ page4.png）
- HTTP 配信
- 自動更新（systemd timer）
- 再起動後の自動復旧

---

# システム構成

```
NHK RSS
  ↓
make_pages_png.py
  ↓
page1.png ～ page4.png
  ↓
python http.server (port 8010)
  ↓
M5PaperS3
```

---

# ディレクトリ構成

例:

```
~/m5papers3
 ├── make_pages_png.py
 ├── fonts/
 │    └── NotoSansCJK-Regular.ttc
 ├── page1.png
 ├── page2.png
 ├── page3.png
 └── page4.png
```

---

# Python 仮想環境の準備

仮想環境作成:

```
python3 -m venv ~/myenv
```

有効化:

```
source ~/myenv/bin/activate
```

必要ライブラリ:

```
pip install pillow feedparser
```

---

# PNG 生成スクリプト動作確認

実行:

```
cd ~/m5papers3
python make_pages_png.py
```

以下が生成されれば成功:

```
page1.png
page2.png
page3.png
page4.png
```

---

# HTTP 配信確認

テスト起動:

```
cd ~/m5papers3
python3 -m http.server 8010
```

ブラウザ確認:

```
http://<RaspberryPiのIP>:8010/page1.png
```

---

# systemd による PNG 自動生成

service 作成:

```
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/m5news-generate.service
```

内容:

```
[Unit]
Description=Generate M5PaperS3 news PNG pages

[Service]
Type=oneshot
WorkingDirectory=/home/bonsai/m5papers3
ExecStart=/home/bonsai/myenv/bin/python make_pages_png.py
```

---

# timer 作成（5分周期）

```
nano ~/.config/systemd/user/m5news-generate.timer
```

内容:

```
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

```
systemctl --user daemon-reload
systemctl --user enable m5news-generate.timer
systemctl --user start m5news-generate.timer
```

確認:

```
systemctl --user list-timers
```

---

# HTTP サーバ常駐化

service 作成:

```
nano ~/.config/systemd/user/m5news-http.service
```

内容:

```
[Unit]
Description=M5PaperS3 PNG HTTP server

[Service]
ExecStart=/usr/bin/python3 -m http.server 8010
WorkingDirectory=/home/bonsai/m5papers3
Restart=always
RestartSec=5
```

有効化:

```
systemctl --user daemon-reload
systemctl --user enable m5news-http.service
systemctl --user start m5news-http.service
```

状態確認:

```
systemctl --user status m5news-http.service
```

---

# 再起動後も自動起動させる

linger 有効化:

```
loginctl enable-linger bonsai
```

これによりログインしていなくても service が動作します。

---

# ログ確認方法

PNG生成ログ:

```
journalctl --user -u m5news-generate.service
```

HTTP サーバログ:

```
journalctl --user -u m5news-http.service
```

---

# 動作確認チェックリスト

確認項目:

- Raspberry Pi 再起動後も HTTP サーバが起動する
- 5分ごとに PNG が更新される
- page1.png がブラウザから取得できる
- M5PaperS3 が自動更新に追従する

---

# 推奨運用設定

推奨更新周期:

```
5分
```

理由:

- RSS 更新頻度と整合
- ePaper 書き換え回数抑制
- ネットワーク負荷低減

---

# トラブルシューティング

PNG が更新されない:

```
systemctl --user status m5news-generate.timer
```

HTTP 接続できない:

```
systemctl --user status m5news-http.service
```

ポート確認:

```
ss -tulpn | grep 8010
```

---

# 将来の拡張候補

- RSS 差分検出更新
- キャッシュ制御（ETag対応）
- nginx 化
- HTTPS 化
- 複数 RSS ソース統合

