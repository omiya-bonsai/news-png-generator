# M5PaperS3 News Server for Raspberry Pi

Japanese: [README.ja.md](README.ja.md)

This repository contains the Raspberry Pi side of the system: RSS fetching, PNG generation, `index.version` generation, HTTP serving, and `systemd`-based operation.

For the full project overview, see the integration hub [m5papers3-news-system](https://github.com/omiya-bonsai/m5papers3-news-system). For the device-side implementation, see [M5PaperS3_NewsDashboard](https://github.com/omiya-bonsai/M5PaperS3_NewsDashboard).

## Quick Links

- Integration hub:
  - [omiya-bonsai/m5papers3-news-system](https://github.com/omiya-bonsai/m5papers3-news-system)
- M5PaperS3 device:
  - [omiya-bonsai/M5PaperS3_NewsDashboard](https://github.com/omiya-bonsai/M5PaperS3_NewsDashboard)

![M5PaperS3 device photo](img/01.jpeg)

## What This Repository Does

- build `index.png` and `page1.png` to `page6.png`
- generate `index.version`
- serve files over HTTP
- keep generation and serving alive with `systemd --user`

## Current Features

- six-page news layout (`index` + six detail pages)
- `index.version` diff-based update detection
- SD-cache-friendly output design
- automated generation with `systemd` timer
- persistent HTTP service
- reboot-friendly recovery

## System Flow

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

## Directory Layout

Example runtime layout:

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

## Font Requirement

Font files are intentionally not included in this repository.

The current script expects at least:

- `NotoSansCJK-Regular.ttc`
- `NotoSansCJK-Bold.ttc`

Expected path:

```text
/home/bonsai/m5papers3/fonts/
```

If you change the font location, also update `FONT_REGULAR` and `FONT_BOLD` inside `make_pages_png.py`.

## Python Environment

Create a virtual environment:

```bash
python3 -m venv ~/myenv
```

Activate it:

```bash
source ~/myenv/bin/activate
```

Install dependencies:

```bash
pip install pillow feedparser
```

## Test the PNG Generator

```bash
cd ~/m5papers3
python make_pages_png.py
```

Expected generated files:

- `index.png`
- `page1.png`
- `page2.png`
- `page3.png`
- `page4.png`
- `page5.png`
- `page6.png`
- `index.version`

## How `index.version` Is Used

The device checks `index.version` before re-downloading `index.png`.

```text
same as previous value -> skip index.png download
```

This reduces:

- network usage
- e-paper redraw frequency
- battery drain

The current version string is built from article order, title, timestamp, and summary so that detail-page changes are also reflected.

## HTTP Serving Check

Manual test:

```bash
cd ~/m5papers3
python3 -m http.server 8010
```

Then check:

```text
http://<RaspberryPi-IP>:8010/index.png
```

## `systemd` Setup

The repository includes distributable unit files under [`systemd/`](systemd).

### Generate PNG pages

Example service:

```ini
[Unit]
Description=Generate M5PaperS3 news PNG pages

[Service]
Type=oneshot
WorkingDirectory=/home/bonsai/m5papers3
ExecStart=/home/bonsai/myenv/bin/python make_pages_png.py
```

### Run every 5 minutes

Example timer:

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

Enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable m5news-generate.timer
systemctl --user start m5news-generate.timer
```

### Persistent HTTP server

Example HTTP service:

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

The `[Install]` section matters. Without it, the service may work with manual `start`, but it will not be a proper `enable` target for automatic startup after reboot.

Enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable m5news-http.service
systemctl --user start m5news-http.service
```

## Auto-start After Reboot

If you want user services to stay available without interactive login:

```bash
loginctl enable-linger bonsai
```

## Logs

PNG generation:

```bash
journalctl --user -u m5news-generate.service
```

HTTP service:

```bash
journalctl --user -u m5news-http.service
```

## Basic Verification Checklist

- HTTP server starts after reboot
- PNG generation runs every 5 minutes
- `index.version` updates as expected
- `index.png` is reachable
- `page1.png` through `page6.png` are reachable
- the M5PaperS3 device follows updates correctly

## Troubleshooting

Generation not running:

```bash
systemctl --user status m5news-generate.timer
```

HTTP unreachable:

```bash
systemctl --user status m5news-http.service
ss -tulpn | grep 8010
```

Version not updating:

```bash
cat index.version
```

Font load failure:

- confirm required `.ttc` files exist under `fonts/`
- confirm the `FONT_REGULAR` and `FONT_BOLD` paths match your environment

## Notes

- The detailed documents are currently written in Japanese.
- Real NHK-generated PNG files and real-news images should stay out of this repository.

## License

This repository is licensed under the [MIT License](LICENSE).
