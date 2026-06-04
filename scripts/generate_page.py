#!/usr/bin/env python3
"""Stock Market Daily - HTML Page Generator"""

import argparse, json, os, sys
from datetime import datetime

SIGNAL_CONFIG = {
    "买入关注": {"color": "#10b981", "bg": "#10b98115", "icon": "📈"},
    "风险警示": {"color": "#ef4444", "bg": "#ef444415", "icon": "⚠️"},
    "宏观观察": {"color": "#f59e0b", "bg": "#f59e0b15", "icon": "🔭"},
}

SECTOR_COLORS = {
    "科技": "#3b82f6", "金融": "#8b5cf6", "能源": "#f59e0b",
    "医疗": "#10b981", "消费": "#ec4899", "工业": "#06b6d4",
    "宏观": "#6b7280", "房地产": "#f97316", "材料": "#84cc16",
}

def render_tickers(tickers):
    if not tickers:
        return ""
    return "".join(
        f'<span class="ticker">${t}</span>' for t in tickers
    )

def render_card(item):
    signal = item.get("signal", "宏观观察")
    cfg = SIGNAL_CONFIG.get(signal, SIGNAL_CONFIG["宏观观察"])
    sector = item.get("sector", "")
    sector_color = SECTOR_COLORS.get(sector, "#6b7280")
    tickers_html = render_tickers(item.get("tickers", []))
    title = item.get("title_zh", "")
    analyst_take = item.get("analyst_take", "")
    why = item.get("why_recommended", "")
    source = item.get("source", "")
    pub_time = item.get("pub_time", "")
    url = item.get("url", "#")
    translate_url = f"https://translate.google.com/translate?sl=auto&tl=zh-CN&u={url}"

    sector_badge = f'<span class="sector-badge" style="background:{sector_color}20;color:{sector_color}">{sector}</span>' if sector else ""
    ticker_row = f'<div class="ticker-row">{tickers_html}</div>' if tickers_html else ""

    return f"""
    <article class="card">
      <div class="card-signal-bar" style="background:{cfg['color']}"></div>
      <div class="card-body">
        <div class="card-top">
          <span class="signal-badge" style="background:{cfg['bg']};color:{cfg['color']}">{cfg['icon']} {signal}</span>
          {sector_badge}
        </div>
        {ticker_row}
        <h2 class="card-title">{title}</h2>
        <div class="why-box">💡 {why}</div>
        <p class="analyst-take">{analyst_take}</p>
        <div class="card-footer">
          <span class="pub-meta">{source} · {pub_time}</span>
          <div class="card-links">
            <a class="btn-zh" href="{translate_url}" target="_blank">🌐 中文阅读</a>
            <a class="btn-src" href="{url}" target="_blank">原文</a>
          </div>
        </div>
      </div>
    </article>"""


def generate_html(items, date_str, generated_at):
    count = len(items)
    cards = "\n".join(render_card(item) for item in items)
    buy_count = sum(1 for i in items if i.get("signal") == "买入关注")
    risk_count = sum(1 for i in items if i.get("signal") == "风险警示")
    macro_count = sum(1 for i in items if i.get("signal") == "宏观观察")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0">
<title>股市分析日报 · {date_str}</title>
<style>
  :root {{
    --bg:#f8fafc; --surface:#fff; --text:#1e293b; --text2:#64748b;
    --border:#e2e8f0; --radius:16px; --shadow:0 2px 12px rgba(0,0,0,0.06);
    --max:480px;
  }}
  @media(prefers-color-scheme:dark) {{
    :root {{ --bg:#0f172a; --surface:#1e293b; --text:#f1f5f9; --text2:#94a3b8; --border:#334155; --shadow:0 2px 12px rgba(0,0,0,0.3); }}
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);min-height:100vh;padding-bottom:48px}}

  .header{{background:var(--surface);border-bottom:1px solid var(--border);padding:18px 16px 14px;position:sticky;top:0;z-index:100;backdrop-filter:blur(12px)}}
  .header-inner{{max-width:var(--max);margin:0 auto;display:flex;justify-content:space-between;align-items:center}}
  .logo{{font-size:19px;font-weight:800;letter-spacing:-.3px}}
  .logo span{{background:linear-gradient(135deg,#10b981,#3b82f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
  .header-right{{text-align:right;font-size:12px;color:var(--text2);line-height:1.6}}
  .header-date{{font-weight:700;font-size:13px;color:var(--text)}}

  .summary-bar{{max-width:var(--max);margin:0 auto;padding:10px 16px 0;display:flex;gap:8px;font-size:12px}}
  .sum-chip{{padding:3px 10px;border-radius:20px;font-weight:600}}

  main{{max-width:var(--max);margin:0 auto;padding:14px 12px;display:flex;flex-direction:column;gap:12px}}

  .card{{background:var(--surface);border-radius:var(--radius);border:1px solid var(--border);box-shadow:var(--shadow);overflow:hidden}}
  .card-signal-bar{{height:3px}}
  .card-body{{padding:13px 15px 15px}}
  .card-top{{display:flex;gap:6px;align-items:center;margin-bottom:8px;flex-wrap:wrap}}
  .signal-badge{{font-size:11px;font-weight:700;padding:3px 9px;border-radius:10px;white-space:nowrap}}
  .sector-badge{{font-size:10px;font-weight:600;padding:2px 8px;border-radius:8px}}
  .ticker-row{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px}}
  .ticker{{font-size:12px;font-weight:800;color:#3b82f6;background:#3b82f610;border:1px solid #3b82f630;padding:2px 8px;border-radius:6px;font-family:monospace}}
  .card-title{{font-size:15px;font-weight:700;line-height:1.45;margin-bottom:9px;letter-spacing:-.2px}}
  .why-box{{font-size:12px;color:var(--text2);background:var(--bg);border-left:3px solid #f59e0b;padding:6px 10px;border-radius:0 8px 8px 0;margin-bottom:10px;line-height:1.5}}
  .analyst-take{{font-size:13px;color:var(--text2);line-height:1.7;margin-bottom:12px}}
  .card-footer{{display:flex;justify-content:space-between;align-items:center;gap:8px}}
  .pub-meta{{font-size:11px;color:var(--text2);flex-shrink:0}}
  .card-links{{display:flex;gap:6px;flex-shrink:0}}
  .btn-zh{{font-size:12px;font-weight:600;color:#fff;background:#3b82f6;padding:4px 10px;border-radius:8px;text-decoration:none;white-space:nowrap}}
  .btn-zh:hover{{background:#2563eb}}
  .btn-src{{font-size:11px;color:var(--text2);text-decoration:none;padding:4px 7px;border-radius:6px;border:1px solid var(--border);white-space:nowrap}}
  .btn-src:hover{{color:var(--text)}}

  .disclaimer{{max-width:var(--max);margin:20px auto 0;padding:12px 16px;font-size:11px;color:var(--text2);text-align:center;border-top:1px solid var(--border);line-height:1.7}}
</style>
</head>
<body>
<header class="header">
  <div class="header-inner">
    <div class="logo">📈 <span>股市分析日报</span></div>
    <div class="header-right">
      <div class="header-date">{date_str}</div>
      <div>今日精选 {count} 篇</div>
    </div>
  </div>
  <div class="summary-bar">
    <span class="sum-chip" style="background:#10b98115;color:#10b981">📈 买入关注 {buy_count}</span>
    <span class="sum-chip" style="background:#ef444415;color:#ef4444">⚠️ 风险警示 {risk_count}</span>
    <span class="sum-chip" style="background:#f59e0b15;color:#f59e0b">🔭 宏观观察 {macro_count}</span>
  </div>
</header>

<main>
{cards}
</main>

<div class="disclaimer">
  ⚠️ 本站内容由 AI 自动生成，仅供参考，不构成任何投资建议。<br>
  股市有风险，投资需谨慎，请结合自身判断做出决策。<br>
  更新于 {generated_at} · 每天 06:00 自动更新
</div>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=False)
    parser.add_argument("--data", required=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8-sig") as f:
            items = json.load(f)
    elif args.data:
        items = json.loads(args.data)
    else:
        print("Error: --file or --data required", file=sys.stderr); sys.exit(1)

    generated_at = datetime.now().strftime("%H:%M")
    html = generate_html(items, args.date, generated_at)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated: {args.output} ({len(items)} articles)")

if __name__ == "__main__":
    main()
