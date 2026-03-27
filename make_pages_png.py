from PIL import Image, ImageDraw, ImageFont
import feedparser
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import html
import re
import hashlib
from pathlib import Path

RSS_URL = "https://www.nhk.or.jp/rss/news/cat0.xml"

FONT_REGULAR = "/home/bonsai/m5papers3/fonts/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/home/bonsai/m5papers3/fonts/NotoSansCJK-Bold.ttc"

WIDTH = 540
HEIGHT = 960

TITLE_FONT_SIZE = 42
SECTION_FONT_SIZE = 24
BODY_FONT_SIZE = 28
META_FONT_SIZE = 20
DETAIL_TITLE_FONT_SIZE = 34
FOOTER_FONT_SIZE = 20

LEFT_MARGIN = 32
RIGHT_MARGIN = 32
TOP_MARGIN = 28
BOTTOM_MARGIN = 20

LINE_HEIGHT = 40
META_LINE_HEIGHT = 28
ITEM_GAP = 18
SECTION_GAP = 20

FOOTER_HEIGHT = 56
FOOTER_TOP_GAP = 10

MAX_HEADLINES = 6
MAX_DETAIL_ARTICLES = 6
MAX_LINES_PER_HEADLINE = 2
MAX_LINES_DETAIL_TITLE = 3

OUTPUT_INDEX = "index.png"
OUTPUT_VERSION = "index.version"

JST = timezone(timedelta(hours=9))


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def wrap_text(draw, text, font, max_width):
    lines = []
    line = ""

    for char in text:
        if char == "\n":
            lines.append(line)
            line = ""
            continue

        test_line = line + char
        width = draw.textlength(test_line, font=font)

        if width <= max_width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = char

    if line:
        lines.append(line)

    return lines


def limit_lines(lines, max_lines):
    if len(lines) <= max_lines:
        return lines

    lines = lines[:max_lines]
    if lines[-1]:
        lines[-1] = lines[-1][:-1] + "…"
    else:
        lines[-1] = "…"
    return lines


def draw_lines(draw, lines, font, x, y, line_height, fill=0):
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def draw_separator(draw, y):
    draw.line(
        (LEFT_MARGIN, y, WIDTH - RIGHT_MARGIN, y),
        fill=180,
        width=1
    )


def parse_entry_datetime_to_jst(entry):
    raw = None

    for key in ("published", "updated", "pubDate"):
        value = getattr(entry, key, None)
        if value:
            raw = value
            break

    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=JST)
            return dt.astimezone(JST)
        except Exception:
            pass

    t = None
    if getattr(entry, "published_parsed", None):
        t = entry.published_parsed
    elif getattr(entry, "updated_parsed", None):
        t = entry.updated_parsed

    if t is not None:
        return datetime(*t[:6], tzinfo=timezone.utc).astimezone(JST)

    return None


def get_entry_datetime(entry):
    dt = parse_entry_datetime_to_jst(entry)
    if dt is None:
        return "日時不明"
    return dt.strftime("%Y-%m-%d %H:%M")


def get_entry_summary(entry):
    summary = ""
    if getattr(entry, "summary", None):
        summary = entry.summary
    elif getattr(entry, "description", None):
        summary = entry.description

    summary = strip_html(summary)

    if not summary:
        return "要約情報はありません。"

    return summary


def make_canvas():
    image = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(image)
    return image, draw


def load_fonts():
    return {
        "title": ImageFont.truetype(FONT_BOLD, TITLE_FONT_SIZE),
        "section": ImageFont.truetype(FONT_BOLD, SECTION_FONT_SIZE),
        "body": ImageFont.truetype(FONT_REGULAR, BODY_FONT_SIZE),
        "meta": ImageFont.truetype(FONT_REGULAR, META_FONT_SIZE),
        "detail_title": ImageFont.truetype(FONT_BOLD, DETAIL_TITLE_FONT_SIZE),
        "footer": ImageFont.truetype(FONT_REGULAR, FOOTER_FONT_SIZE),
    }


def draw_header(draw, fonts, title_text, page_label=None):
    y = TOP_MARGIN
    draw.text((LEFT_MARGIN, y), title_text, font=fonts["title"], fill=0)

    if page_label:
        page_width = draw.textlength(page_label, font=fonts["meta"])
        draw.text(
            (WIDTH - RIGHT_MARGIN - page_width, y + 12),
            page_label,
            font=fonts["meta"],
            fill=90
        )

    y += 56
    draw_separator(draw, y)
    y += 16
    return y


def draw_footer(draw, fonts, left_text, center_text, right_text):
    footer_top = HEIGHT - BOTTOM_MARGIN - FOOTER_HEIGHT

    draw_separator(draw, footer_top)

    y = footer_top + 16

    if left_text:
        draw.text((LEFT_MARGIN, y), left_text, font=fonts["footer"], fill=110)

    if center_text:
        center_width = draw.textlength(center_text, font=fonts["footer"])
        draw.text(
            ((WIDTH - center_width) / 2, y),
            center_text,
            font=fonts["footer"],
            fill=110
        )

    if right_text:
        right_width = draw.textlength(right_text, font=fonts["footer"])
        draw.text(
            (WIDTH - RIGHT_MARGIN - right_width, y),
            right_text,
            font=fonts["footer"],
            fill=110
        )


def content_bottom_limit():
    return HEIGHT - BOTTOM_MARGIN - FOOTER_HEIGHT - FOOTER_TOP_GAP


def render_headlines_page(feed, fonts, output_path):
    image, draw = make_canvas()

    y = draw_header(
        draw,
        fonts,
        getattr(feed.feed, "title", "NHKニュース"),
        "index"
    )

    max_width = WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    bottom_limit = content_bottom_limit()

    entries = feed.entries[:MAX_HEADLINES]

    if not entries:
        draw.text(
            (LEFT_MARGIN, y),
            "記事がありません。",
            font=fonts["body"],
            fill=0
        )
        draw_footer(draw, fonts, "", "index", "詳細 →")
        image.save(output_path)
        print(f"saved: {output_path}")
        return

    for i, entry in enumerate(entries):
        title_text = "・" + entry.title
        title_lines = wrap_text(draw, title_text, fonts["body"], max_width)
        title_lines = limit_lines(title_lines, MAX_LINES_PER_HEADLINE)

        estimated_height = (
            len(title_lines) * LINE_HEIGHT
            + META_LINE_HEIGHT
            + ITEM_GAP
        )

        if y + estimated_height > bottom_limit:
            break

        y = draw_lines(
            draw,
            title_lines,
            fonts["body"],
            LEFT_MARGIN,
            y,
            LINE_HEIGHT
        )

        meta_text = get_entry_datetime(entry)
        draw.text(
            (LEFT_MARGIN + 18, y - 2),
            meta_text,
            font=fonts["meta"],
            fill=90
        )

        y += META_LINE_HEIGHT
        y += ITEM_GAP

        if i < len(entries) - 1 and y < bottom_limit:
            draw_separator(draw, y - 8)

    draw_footer(draw, fonts, "", "index", "詳細 →")
    image.save(output_path)
    print(f"saved: {output_path}")


def render_detail_page(feed, fonts, entry_index, output_path, page_label):
    image, draw = make_canvas()

    feed_title = getattr(feed.feed, "title", "NHKニュース")
    y = draw_header(draw, fonts, feed_title, page_label)
    bottom_limit = content_bottom_limit()

    if len(feed.entries) <= entry_index:
        draw.text(
            (LEFT_MARGIN, y),
            "対象記事がありません。",
            font=fonts["body"],
            fill=0
        )
        draw_footer(draw, fonts, "← 前の記事", page_label, "次の記事 →")
        image.save(output_path)
        print(f"saved: {output_path}")
        return

    entry = feed.entries[entry_index]
    max_width = WIDTH - LEFT_MARGIN - RIGHT_MARGIN

    rank_label = f"記事 {entry_index + 1}"
    draw.text(
        (LEFT_MARGIN, y),
        rank_label,
        font=fonts["section"],
        fill=0
    )

    y += 42

    title_lines = wrap_text(draw, entry.title, fonts["detail_title"], max_width)
    title_lines = limit_lines(title_lines, MAX_LINES_DETAIL_TITLE)

    y = draw_lines(
        draw,
        title_lines,
        fonts["detail_title"],
        LEFT_MARGIN,
        y,
        44
    )

    y += 4

    meta_text = get_entry_datetime(entry)
    draw.text(
        (LEFT_MARGIN, y),
        meta_text,
        font=fonts["meta"],
        fill=90
    )

    y += 34
    draw_separator(draw, y)
    y += SECTION_GAP

    draw.text(
        (LEFT_MARGIN, y),
        "要約",
        font=fonts["section"],
        fill=0
    )

    y += 38

    summary = get_entry_summary(entry)
    summary_lines = wrap_text(draw, summary, fonts["body"], max_width)

    available_height = bottom_limit - y
    max_summary_lines = max(1, available_height // LINE_HEIGHT)
    summary_lines = limit_lines(summary_lines, max_summary_lines)

    draw_lines(
        draw,
        summary_lines,
        fonts["body"],
        LEFT_MARGIN,
        y,
        LINE_HEIGHT
    )

    draw_footer(draw, fonts, "← 前の記事", page_label, "次の記事 →")
    image.save(output_path)
    print(f"saved: {output_path}")


def build_index_version(feed) -> str:
    """
    一覧表示に影響する要素だけで version を作る。
    ここが前回と同じなら PNG 再生成をスキップする。
    """
    entries = feed.entries[:MAX_HEADLINES]
    parts = []

    for entry in entries:
        title = getattr(entry, "title", "").strip()
        dt = get_entry_datetime(entry)
        parts.append(f"{title}|{dt}")

    source = "\n".join(parts)
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
    return digest


def read_existing_version(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").strip()


def write_index_version(version_text: str, output_path: str):
    Path(output_path).write_text(version_text + "\n", encoding="utf-8")
    print(f"saved: {output_path} -> {version_text}")


def main():
    feed = feedparser.parse(RSS_URL)

    if getattr(feed, "bozo", 0):
        print(f"bozo_exception: {feed.bozo_exception}")

    new_version = build_index_version(feed)
    old_version = read_existing_version(OUTPUT_VERSION)

    print(f"old version: {old_version if old_version else '(none)'}")
    print(f"new version: {new_version}")

    if old_version == new_version:
        print("No change detected. Skip PNG regeneration.")
        return

    fonts = load_fonts()

    render_headlines_page(feed, fonts, OUTPUT_INDEX)

    for i in range(MAX_DETAIL_ARTICLES):
        output_path = f"page{i + 1}.png"
        page_label = f"page{i + 1}"
        render_detail_page(feed, fonts, i, output_path, page_label)

    write_index_version(new_version, OUTPUT_VERSION)
    print("PNG regeneration completed.")


if __name__ == "__main__":
    main()
