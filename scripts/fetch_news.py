"""
Stock Market Daily - Fetch & Generate
从权威财经媒体 RSS 抓取新闻，以资深分析师视角筛选10篇投资参考文章，生成HTML页面
依赖：groq, feedparser, requests
"""

import json, os, sys, subprocess, time, re
from datetime import datetime, timezone, timedelta
from groq import Groq
import feedparser, requests

TODAY = datetime.now().strftime("%Y-%m-%d")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
OUTPUT_HTML = os.path.join(OUTPUT_DIR, f"stock-{TODAY}.html")
GENERATE_SCRIPT = os.path.join(os.path.dirname(__file__), "generate_page.py")

RSS_FEEDS = [
    ("Reuters Business",    "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Finance",     "https://feeds.reuters.com/news/wealth"),
    ("MarketWatch",         "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("CNBC Markets",        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"),
    ("CNBC Earnings",       "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135"),
    ("Seeking Alpha",       "https://seekingalpha.com/feed.xml"),
    ("Yahoo Finance",       "https://finance.yahoo.com/rss/topfinstories"),
    ("Barron's",            "https://www.barrons.com/xml/rss/3_7558.xml"),
    ("Financial Times",     "https://www.ft.com/rss/home/us"),
    ("Bloomberg Markets",   "https://feeds.bloomberg.com/markets/news.rss"),
]

ANALYST_PROMPT = """你是一名拥有20年经验的资深股票市场分析师，专注于北美股市（NYSE/NASDAQ）。
你的风格：数据驱动、逻辑清晰、敢于给出明确观点，从不模棱两可。

读者：个人投资者，希望通过阅读你的分析做出更明智的买入/持有/观望决策。

下面是今天从财经媒体收集的新闻候选列表。

**任务：从中精选10篇最值得投资者关注的文章**

筛选标准：
- 直接影响具体公司股价的重大事件（财报、并购、CEO变动、监管处罚、产品发布）
- 影响整个板块或大盘的宏观信号（利率、通胀、就业数据、地缘政治）
- 隐藏的买入机会或风险预警（市场低估/高估信号、内部人交易、机构动向）

**去重规则**：同一事件只保留信息最完整的一条，不同来源报道同一新闻算重复。

**输出格式**：直接输出JSON数组（不加```标记），共10条，每条字段：

- title_zh: 中文标题（25字以内，直接点明核心事件）
- tickers: 涉及的股票代码数组，如["AAPL","MSFT"]，若为宏观新闻填[]
- sector: 所属板块，如"科技"/"金融"/"能源"/"医疗"/"消费"/"工业"/"宏观"
- signal: 投资信号，只能是以下三个之一："买入关注" / "风险警示" / "宏观观察"
- analyst_take: 分析师点评（150-200字）：说清楚——这条新闻意味着什么？对股价有何影响？为什么值得投资者关注？给出明确的行动建议（应该买入/减仓/持有观望？理由是什么？）
- why_recommended: 推荐理由（30字以内，一句话说清楚为什么推荐这篇）
- source: 来源媒体名称
- pub_time: 发布日期 YYYY-MM-DD
- url: 原文链接

候选新闻列表：
{candidates}

只输出JSON数组，不要任何解释。"""


def fetch_rss_news():
    results, seen_urls = [], set()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StockNews-Bot/1.0)"}

    for source_name, feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, headers=headers, timeout=15)
            feed = feedparser.parse(resp.content)
            count = 0
            for entry in feed.entries:
                url = entry.get("link", "")
                if not url or url in seen_urls:
                    continue
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                if pub_date and pub_date < cutoff:
                    continue
                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                summary = re.sub(r"<[^>]+>", " ", summary).strip()[:300]
                seen_urls.add(url)
                results.append({
                    "title": title, "body": summary, "source": source_name,
                    "date": pub_date.strftime("%Y-%m-%d") if pub_date else TODAY,
                    "url": url,
                })
                count += 1
                if count >= 10:
                    break
            print(f"  {source_name}: {count} 条")
        except Exception as e:
            print(f"  {source_name} 失败: {e}", file=sys.stderr)
        time.sleep(0.5)

    print(f"共抓取 {len(results)} 条候选新闻")
    return results


def format_candidates(raw_news):
    lines = []
    for i, n in enumerate(raw_news, 1):
        lines.append(
            f"{i}. [{n['source']}] {n['date']}\n"
            f"   标题: {n['title']}\n"
            f"   摘要: {n['body'][:250]}\n"
            f"   链接: {n['url']}"
        )
    return "\n\n".join(lines)


def clean_json(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw[raw.index("\n")+1:] if "\n" in raw else raw[3:]
    if raw.rstrip().endswith("```"):
        raw = raw.rstrip()[:-3].rstrip()
    return raw.strip()


def process_with_groq(raw_news, retry=3):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    prompt = ANALYST_PROMPT.format(candidates=format_candidates(raw_news))

    for attempt in range(1, retry + 1):
        try:
            print(f"调用 Groq API（第{attempt}次）...")
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=4096,
            )
            raw = clean_json(resp.choices[0].message.content)
            print(f"输出前200字: {raw[:200]}")
            items = json.loads(raw)
            print(f"分析师选出 {len(items)} 篇文章")
            return items
        except json.JSONDecodeError as e:
            print(f"JSON解析失败（{attempt}次）: {e}", file=sys.stderr)
            if attempt == retry: raise
            time.sleep(5)
        except Exception as e:
            print(f"API失败（{attempt}次）: {e}", file=sys.stderr)
            if attempt == retry: raise
            time.sleep(10)


def generate_html(items):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp = os.path.join(OUTPUT_DIR, f"_tmp_{TODAY}.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    result = subprocess.run(
        [sys.executable, GENERATE_SCRIPT, "--file", tmp, "--output", OUTPUT_HTML, "--date", TODAY],
        capture_output=True, text=True, env={**os.environ, "PYTHONUTF8": "1"}
    )
    os.remove(tmp)
    if result.returncode != 0:
        print(f"generate_page.py 错误: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout.strip())


def update_index():
    import glob
    index_path = os.path.join(OUTPUT_DIR, "index.html")
    pages = sorted(glob.glob(os.path.join(OUTPUT_DIR, "stock-????-??-??.html")), reverse=True)
    archive = "".join(
        f'<li><a href="stock-{os.path.basename(p).replace("stock-","").replace(".html","")}.html">'
        f'{"✦ " if os.path.basename(p).replace("stock-","").replace(".html","") == TODAY else ""}'
        f'{os.path.basename(p).replace("stock-","").replace(".html","")}</a></li>\n'
        for p in pages[:30]
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>股市分析日报</title>
<meta http-equiv="refresh" content="0;url=stock-{TODAY}.html">
<style>body{{font-family:-apple-system,"PingFang SC",sans-serif;max-width:480px;margin:60px auto;padding:0 20px;color:#1e293b}}
h1{{font-size:24px}}p{{color:#64748b}}ul{{list-style:none;padding:0}}li{{margin:8px 0}}
a{{color:#3b82f6;text-decoration:none}}a:hover{{text-decoration:underline}}</style>
</head><body>
<h1>📈 股市分析日报</h1>
<p>资深分析师每日精选，正在跳转今日报告…</p>
<p style="font-size:13px;color:#94a3b8">如未跳转，<a href="stock-{TODAY}.html">点击这里</a></p>
<h2 style="font-size:16px;margin-top:32px">历史归档</h2>
<ul>{archive}</ul>
<p style="font-size:11px;color:#94a3b8;margin-top:32px">⚠️ 本站内容仅供参考，不构成投资建议。投资有风险，决策需谨慎。</p>
</body></html>"""
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html 已更新")


def main():
    print(f"=== Stock Market Daily {TODAY} ===")
    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: 未设置 GROQ_API_KEY", file=sys.stderr); sys.exit(1)
    raw = fetch_rss_news()
    if not raw:
        print("ERROR: 未抓取到新闻", file=sys.stderr); sys.exit(1)
    items = process_with_groq(raw)
    generate_html(items)
    update_index()
    print(f"完成！{OUTPUT_HTML}")

if __name__ == "__main__":
    main()
