"""
datapack.json + narrative.json → 填入 templates/report_template.html → docs/YYYY-MM-DD/index.html

script 負責:溫度計定位、價位卡、名單、vol 編號、日期格式(全部從 datapack 算,零 AI token)
narrative.json 負責:標題/內文/下週劇本/投票(這一份先由人工或 AI 一次性寫好,之後可換成呼叫 Anthropic API)
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(ROOT, "templates", "report_template.html")
CHARTS_DIR = os.path.join(ROOT, "charts")
DOCS_DIR = os.path.join(ROOT, "docs")


def load_json(name):
    path = os.path.join(ROOT, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_history():
    path = os.path.join(ROOT, config.HISTORY_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_history(history):
    path = os.path.join(ROOT, config.HISTORY_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def fmt_price(v):
    return f"{v:,.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def build_us_levels(spy):
    lv = spy["levels"]
    return (
        f'    <div class="level up"><span class="dir">▲ 大格局壓力</span><span class="px">{fmt_price(lv["hi52"])}</span>(52週高)</div>\n'
        f'    <div class="level down"><span class="dir">▼ 大格局支撐</span><span class="px">{fmt_price(lv["lo52"])}</span>(52週低)</div>\n'
        f'    <div class="level up"><span class="dir">◎ 下週先盯這裡</span><span class="px">{fmt_price(lv["ma50"])}</span>(50日線)</div>'
    )


def build_btc_levels(btc, override=None):
    if override:
        return (
            f'    <div class="level up"><span class="dir">▲ {override["up_label"]}</span><span class="px">{override["up_value"]}</span></div>\n'
            f'    <div class="level down"><span class="dir">▼ {override["down_label"]}</span><span class="px">{override["down_value"]}</span></div>'
        )
    lv = btc["levels"]
    return (
        f'    <div class="level up"><span class="dir">▲ 本週高點</span><span class="px">{fmt_price(lv["wk_hi"])}</span></div>\n'
        f'    <div class="level down"><span class="dir">▼ 本週低點</span><span class="px">{fmt_price(lv["wk_lo"])}</span></div>'
    )


def build_roster(stocks):
    lines = []
    for s in stocks:
        name = s["t"]
        lines.append(f'        <li><span class="tk">{name}</span> 本週 {s["w"]:+.1f}%</li>')
    return "\n".join(lines)


def build_tldr(items):
    lines = []
    for i, text in enumerate(items, 1):
        lines.append(f'    <li data-i="{i:02d}">{text}</li>')
    return "\n".join(lines)


def build_watchlist(items):
    return "\n".join(f"    <li>{t}</li>" for t in items)


def build_poll_options(options):
    lines = []
    for o in options:
        lines.append(f'  <button class="opt"><span class="key">{o["key"]}</span>{o["text"]}</button>')
    return "\n".join(lines)


def build_body(paragraphs):
    return "\n".join(paragraphs)


def strip_block(html, start_marker, end_marker):
    start = html.find(start_marker)
    end = html.find(end_marker)
    if start == -1 or end == -1:
        return html
    return html[:start] + html[end + len(end_marker):]


def fill_chart_block(html, tag, chart_filename, narrative, root_key):
    start_marker = f"<!--CHART_{tag}_START-->"
    end_marker = f"<!--CHART_{tag}_END-->"
    chart_path = os.path.join(CHARTS_DIR, chart_filename)
    if not os.path.exists(chart_path):
        return strip_block(html, start_marker, end_marker)
    html = html.replace(start_marker, "").replace(end_marker, "")
    html = html.replace(f"{{{{chart_{root_key}_file}}}}", chart_filename)
    html = html.replace(f"{{{{chart_{root_key}_alt}}}}", narrative.get(f"chart_{root_key}_alt", ""))
    html = html.replace(f"{{{{chart_{root_key}_tag}}}}", narrative.get(f"chart_{root_key}_tag", ""))
    html = html.replace(f"{{{{caption_{root_key}}}}}", narrative.get(f"caption_{root_key}", ""))
    return html


def main():
    datapack = load_json(config.DATAPACK_FILE)
    narrative = load_json("narrative.json")
    history = load_history()

    spy = next(i for i in datapack["indices"] if i["symbol"] == "SPY")
    btc = next(i for i in datapack["indices"] if i["symbol"] == "BTC")

    start_str, end_str = datapack["week"].split("/")

    # vol 編號綁定「這一週」,同一週重新 build(改稿)不會往上加
    vol_by_week = history.setdefault("vol_by_week", {})
    if end_str not in vol_by_week:
        vol_by_week[end_str] = history.get("vol", 0) + 1
        history["vol"] = vol_by_week[end_str]
    vol_num = vol_by_week[end_str]
    save_history(history)

    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_str, "%Y-%m-%d")
    date_range = f"{start_dt:%Y.%m.%d} – {end_dt:%m.%d}"
    date_range_short = f"{start_dt:%m/%d}–{end_dt:%m/%d}"

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    html = fill_chart_block(html, "US", "spy_chart.png", narrative, "us")
    html = fill_chart_block(html, "BTC", "btc_chart.png", narrative, "btc")

    slots = {
        "vol": f"VOL.{vol_num:02d}",
        "date_range": date_range,
        "date_range_short": date_range_short,
        "headline": narrative["headline"],
        "dek": narrative["dek"],
        "tldr_items": build_tldr(narrative["tldr_items"]),
        "us_tag_class": narrative["us_tag_class"],
        "us_tag_label": narrative["us_tag_label"],
        "us_title": narrative["us_title"],
        "us_body": build_body(narrative["us_body"]),
        "us_levels": build_us_levels(spy),
        "btc_tag_class": narrative["btc_tag_class"],
        "btc_tag_label": narrative["btc_tag_label"],
        "btc_title": narrative["btc_title"],
        "btc_body": build_body(narrative["btc_body"]),
        "btc_levels": build_btc_levels(btc, narrative.get("btc_levels_override")),
        "rotation_body": build_body(narrative["rotation_body"]),
        "roster_hot_title": f'{config.SECTOR_NAMES[datapack["leaders"]["sector"]]}|走得穩的',
        "roster_hot": build_roster(datapack["leaders"]["stocks"]),
        "roster_cold_title": f'{config.SECTOR_NAMES[datapack["laggards"]["sector"]]}|正在被倒貨的',
        "roster_cold": build_roster(datapack["laggards"]["stocks"]),
        "watchlist": build_watchlist(narrative["watchlist"]),
        "poll_question": narrative["poll_question"],
        "poll_options": build_poll_options(narrative["poll_options"]),
        "footer_note": narrative["footer_note"],
    }

    for key, val in slots.items():
        html = html.replace(f"{{{{{key}}}}}", val)

    out_dir = os.path.join(DOCS_DIR, end_str)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"完成 → {out_path}")


if __name__ == "__main__":
    main()
