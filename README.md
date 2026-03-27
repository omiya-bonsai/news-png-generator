# Raspberry Pi 側セットアップ手順（M5PaperS3 News Server v2）

## 概要

本ドキュメントは **M5PaperS3
ニュース表示システムのサーバ側構成（最新版）** をまとめたものです。

従来構成から次の改善が追加されています。

-   index.png + page1〜page6.png の6記事構成
-   index.version 差分検出方式
-   SDキャッシュ連携前提設計
-   systemd timer 自動更新
-   HTTP常駐サービス
-   再起動後の完全自動復旧

------------------------------------------------------------------------

# システム構成（最新版）

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

------------------------------------------------------------------------

# ディレクトリ構成

例:

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

------------------------------------------------------------------------

# Python 仮想環境の準備

作成:

    python3 -m venv ~/myenv

有効化:

    source ~/myenv/bin/activate

必要ライブラリ:

    pip install pillow feedparser

------------------------------------------------------------------------

# PNG 生成スクリプト動作確認

実行:

    cd ~/m5papers3
    python make_pages_png.py

生成確認:

    index.png
    page1.png
    page2.png
    page3.png
    page4.png
    page5.png
    page6.png
    index.version

------------------------------------------------------------------------

# index.version 差分検出方式（重要）

PNG より先に **index.version** を取得します。

例:

    20260326-1910

M5PaperS3 側では

    前回値と一致 → index.png 再取得しない

つまり:

-   通信削減
-   ePaper書換削減
-   バッテリー消費削減

を同時に実現します。

------------------------------------------------------------------------

# HTTP 配信確認

テスト起動:

    cd ~/m5papers3
    python3 -m http.server 8010

確認:

    http://<RaspberryPiのIP>:8010/index.png

------------------------------------------------------------------------

# systemd による PNG 自動生成

service 作成:

    mkdir -p ~/.config/systemd/user
    nano ~/.config/systemd/user/m5news-generate.service

内容:

    [Unit]
    Description=Generate M5PaperS3 news PNG pages

    [Service]
    Type=oneshot
    WorkingDirectory=/home/bonsai/m5papers3
    ExecStart=/home/bonsai/myenv/bin/python make_pages_png.py

------------------------------------------------------------------------

# timer 作成（5分周期）

    nano ~/.config/systemd/user/m5news-generate.timer

内容:

    [Unit]
    Description=Run news PNG generator every 5 minutes

    [Timer]
    OnBootSec=30
    OnUnitActiveSec=5min
    Persistent=true

    [Install]
    WantedBy=timers.target

有効化:

    systemctl --user daemon-reload
    systemctl --user enable m5news-generate.timer
    systemctl --user start m5news-generate.timer

確認:

    systemctl --user list-timers

------------------------------------------------------------------------

# HTTP サーバ常駐化

service 作成:

    nano ~/.config/systemd/user/m5news-http.service

内容:

    [Unit]
    Description=M5PaperS3 PNG HTTP server

    [Service]
    ExecStart=/usr/bin/python3 -m http.server 8010
    WorkingDirectory=/home/bonsai/m5papers3
    Restart=always
    RestartSec=5

有効化:

    systemctl --user daemon-reload
    systemctl --user enable m5news-http.service
    systemctl --user start m5news-http.service

確認:

    systemctl --user status m5news-http.service

------------------------------------------------------------------------

# 再起動後も自動起動させる

linger 有効化:

    loginctl enable-linger bonsai

ログイン不要で常駐します。

------------------------------------------------------------------------

# ログ確認方法

PNG生成ログ:

    journalctl --user -u m5news-generate.service

HTTPログ:

    journalctl --user -u m5news-http.service

------------------------------------------------------------------------

# 動作確認チェックリスト

確認:

-   再起動後 HTTP server 起動
-   5分周期 PNG 更新
-   index.version 更新確認
-   index.png 表示確認
-   page1〜page6.png 表示確認
-   M5PaperS3 自動追従確認

------------------------------------------------------------------------

# 推奨更新周期

    5分

理由:

-   RSS 更新頻度と整合
-   通信量削減
-   ePaper寿命延長
-   バッテリー節約

------------------------------------------------------------------------

# トラブルシューティング

PNG 未更新:

    systemctl --user status m5news-generate.timer

HTTP 接続不可:

    systemctl --user status m5news-http.service

ポート確認:

    ss -tulpn | grep 8010

index.version 未更新:

    cat index.version

------------------------------------------------------------------------

# 今後の拡張候補（優先順）

優先度 高:

-   MQTT 差分通知連携
-   nginx 置換
-   gzip 転送

優先度 中:

-   複数 RSS 統合
-   category 分離表示

優先度 低:

-   HTTPS 化
-   CDN 配信

