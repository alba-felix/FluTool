#!/usr/bin/env python3
"""
GitHub Trending AI/ML 周榜抓取脚本（静默版）
无控制台输出，仅生成带日期的 HTML 文件，格式：github_trending_ai_YYYY_MM_DD.html
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
import os
import logging
import sys

# 添加项目根目录到路径，以便导入 core.utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.utils import get_app_data_path

# 禁用日志输出（如需调试可改为 INFO）
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ---------- 配置 ----------
GITHUB_TRENDING_URL = "https://github.com/trending?since=weekly"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
AI_KEYWORDS = [
    "ai", "machine learning", "ml", "llm", "agent", "langchain", "gpt", "claude",
    "prompt", "intelligence", "neural", "deep learning", "computer vision", "cv",
    "voice", "speech", "tts", "stt", "rag", "knowledge graph", "video generation",
    "autonomous", "mcp", "skill", "embedding", "vector", "chatbot", "copilot",
    "code generation", "multimodal", "transformer", "diffusion", "llava", "whisper"
]

def parse_stars(text: str) -> int:
    """解析带逗号或K/M后缀的star数字"""
    if not text:
        return 0
    text = text.strip().replace(",", "")
    text = text.upper()
    if "K" in text:
        return int(float(text.replace("K", "")) * 1000)
    if "M" in text:
        return int(float(text.replace("M", "")) * 1000000)
    try:
        return int(text)
    except ValueError:
        return 0

def fetch_trending_repos() -> List[Dict[str, Any]]:
    """抓取 GitHub Trending 周榜原始数据"""
    resp = requests.get(GITHUB_TRENDING_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    
    articles = soup.select("article.Box-row")
    if not articles:
        articles = soup.select(".Box-row")
    
    repos = []
    for article in articles:
        try:
            h2 = article.select_one("h2.h3.lh-condensed a, h2.h3 a")
            if not h2:
                continue
            repo_path = h2.get("href", "").strip("/")
            if not repo_path:
                continue
            repo_name = repo_path.split("/")[-1] if "/" in repo_path else repo_path
            full_name = repo_path
            
            desc_elem = article.select_one("p.col-9, p.color-fg-muted, .col-9")
            description = desc_elem.text.strip() if desc_elem else ""
            
            lang_elem = article.select_one('span[itemprop="programmingLanguage"]')
            language = lang_elem.text.strip() if lang_elem else "Unknown"
            
            total_stars = 0
            star_link = article.select_one('a[href$="/stargazers"]')
            if star_link:
                star_text = star_link.get_text(strip=True)
                total_stars = parse_stars(star_text)
            else:
                star_candidates = article.select(".f6.color-fg-muted .octicon-star ~ span")
                if star_candidates:
                    total_stars = parse_stars(star_candidates[0].text)
            
            weekly_stars = 0
            weekly_elem = article.find(string=re.compile(r"stars? this week", re.I))
            if weekly_elem:
                parent = weekly_elem.find_parent()
                if parent:
                    text = parent.get_text(strip=True)
                    match = re.search(r"(\d+(?:,\d+)*(?:\.\d+)?[KM]?)\s+stars? this week", text, re.I)
                    if match:
                        weekly_stars = parse_stars(match.group(1))
            if weekly_stars == 0:
                smalls = article.select("small, .text-small")
                for small in smalls:
                    if "star" in small.text.lower() and "this week" in small.text.lower():
                        num = re.search(r"(\d+(?:,\d+)*(?:\.\d+)?[KM]?)", small.text)
                        if num:
                            weekly_stars = parse_stars(num.group(1))
                            break
            
            repo_url = f"https://github.com/{repo_path}"
            repos.append({
                "rank": 0,
                "full_name": full_name,
                "name": repo_name,
                "url": repo_url,
                "description": description,
                "language": language,
                "total_stars": total_stars,
                "weekly_stars": weekly_stars,
            })
        except Exception:
            continue
    
    return repos

def is_ai_related(repo: Dict[str, Any]) -> bool:
    text = f"{repo['name']} {repo['description']} {repo['language']}".lower()
    for kw in AI_KEYWORDS:
        if kw in text:
            return True
    return False

def generate_highlights(description: str, name: str) -> List[str]:
    if not description:
        return [f"{name} 提供前沿 AI 能力", "支持主流 Agent 框架集成", "持续优化性能和开发者体验"]
    desc_clean = description.replace("\n", " ").strip()
    sentences = re.split(r'[.;。；]', desc_clean)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
    highlights = sentences[:3]
    if len(highlights) < 2:
        if "agent" in desc_clean.lower():
            highlights.append("专为 AI Agent 设计，提供核心能力支持")
        if "token" in desc_clean.lower():
            highlights.append("有效降低 Token 消耗，提升响应效率")
        if "local" in desc_clean.lower() or "offline" in desc_clean.lower():
            highlights.append("支持本地/离线运行，保障数据隐私")
    while len(highlights) < 2:
        highlights.append("与主流 LLM 框架无缝协作")
    return highlights[:3]

def generate_tags(repo: Dict[str, Any]) -> List[str]:
    tags = []
    text = f"{repo['name']} {repo['description']} {repo['language']}".lower()
    if any(kw in text for kw in ["code", "programming", "developer", "ide", "cursor", "claude code"]):
        tags.append("AI 编程助手")
    if any(kw in text for kw in ["security", "cybersecurity", "mitre", "vulnerability"]):
        tags.append("网络安全")
    if any(kw in text for kw in ["voice", "speech", "tts", "stt", "call"]):
        tags.append("语音 AI")
    if any(kw in text for kw in ["video", "generation", "movie", "film"]):
        tags.append("视频生成")
    if any(kw in text for kw in ["mobile", "ios", "android", "端侧"]):
        tags.append("移动端部署")
    if any(kw in text for kw in ["knowledge graph", "graph"]):
        tags.append("知识图谱")
    if any(kw in text for kw in ["memory", "持久记忆", "session"]):
        tags.append("Agent 记忆")
    if any(kw in text for kw in ["terminal", "cli", "command"]):
        tags.append("终端工具")
    if any(kw in text for kw in ["privacy", "private", "local"]):
        tags.append("隐私保护")
    if any(kw in text for kw in ["framework", "principle", "best practice"]):
        tags.append("架构设计")
    if "home assistant" in text or "wifi" in text:
        tags.append("智能家居")
    if not tags:
        tags = ["AI/ML 工具", "开源创新"]
    if repo["language"] != "Unknown":
        tags.append(repo["language"])
    else:
        tags.append("多语言支持")
    return tags[:4]

def extract_trend_keywords(repos: List[Dict[str, Any]]) -> List[str]:
    all_text = " ".join([r["description"] + " " + r["name"] for r in repos]).lower()
    candidates = ["Agent", "Skills", "知识图谱", "记忆", "语音AI", "LLM", "RAG", "MCP", "推理", "多模态", "视频生成", "安全", "终端"]
    scores = {}
    for cand in candidates:
        low = cand.lower()
        count = all_text.count(low)
        if count > 0:
            scores[cand] = count
    sorted_kw = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [kw for kw, _ in sorted_kw[:5]]

def generate_html(repos: List[Dict[str, Any]], fetch_time: str, keywords: List[str]) -> str:
    cards_html = []
    for idx, repo in enumerate(repos, 1):
        total_stars_fmt = f"{repo['total_stars']:,}"
        weekly_stars_fmt = f"+{repo['weekly_stars']:,}" if repo['weekly_stars'] > 0 else "+0"
        highlights = generate_highlights(repo["description"], repo["name"])
        highlights_li = "\n".join([f'<li>{h}</li>' for h in highlights])
        tags = generate_tags(repo)
        tags_span = "".join([f'<span class="tag">{tag}</span>' for tag in tags])
        card = f'''
    <div class="card">
      <div class="card-header">
        <span class="rank">{idx}</span>
        <a class="project-name" href="{repo["url"]}" target="_blank">{repo["full_name"]}</a>
        <span class="lang-tag">{repo["language"]}</span>
        <div class="card-stats">
          <span class="stat stat-total">{total_stars_fmt} ★</span>
          <span class="stat stat-weekly">{weekly_stars_fmt} 本周</span>
        </div>
      </div>
      <div class="card-body">
        <p class="one-liner">{repo["description"] or "暂无描述，请访问 GitHub 主页了解详情"}</p>
        <p class="section-label">核心功能</p>
        <ul>
          {highlights_li}
        </ul>
        <p class="section-label">适用场景</p>
        <div class="tags">
          {tags_span}
        </div>
      </div>
    </div>
        '''
        cards_html.append(card.strip())
    
    keywords_str = " · ".join([f"<strong>{kw}</strong>" for kw in keywords]) if keywords else "<strong>AI</strong> · <strong>Agent</strong> · <strong>开源</strong>"
    
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GitHub Trending · AI/ML 周榜 · {fetch_time[:10]}</title>
<style>
  :root {{
    --bg-start: #faf6f2;
    --bg-mid: #f3e8e0;
    --bg-end: #eedad2;
    --accent: #d4684a;
    --accent-soft: #e8a090;
    --card-bg: rgba(255,255,255,0.72);
    --card-border: rgba(212,104,74,0.12);
    --text-primary: #2c241e;
    --text-secondary: #6b5d54;
    --text-muted: #9a8c83;
    --tag-bg: rgba(212,104,74,0.08);
    --tag-text: #b8563a;
    --star-gold: #d4983a;
    --shadow-card: 0 1px 3px rgba(44,36,30,0.06), 0 4px 16px rgba(44,36,30,0.04);
    --shadow-card-hover: 0 2px 8px rgba(44,36,30,0.08), 0 8px 32px rgba(44,36,30,0.06);
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: linear-gradient(165deg, var(--bg-start) 0%, var(--bg-mid) 42%, var(--bg-end) 100%);
    min-height: 100vh;
    color: var(--text-primary);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }}

  .container {{
    max-width: 920px;
    margin: 0 auto;
    padding: 48px 24px 64px;
  }}

  /* Header */
  .header {{
    text-align: center;
    margin-bottom: 48px;
  }}

  .header h1 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    margin-bottom: 8px;
  }}

  .header .subtitle {{
    font-size: 14px;
    color: var(--text-muted);
    font-weight: 400;
  }}

  .header .fetch-time {{
    display: inline-block;
    margin-top: 12px;
    font-size: 12px;
    color: var(--text-muted);
    background: rgba(255,255,255,0.5);
    padding: 4px 14px;
    border-radius: 20px;
    letter-spacing: 0.02em;
  }}

  /* Card */
  .card-list {{
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}

  .card {{
    background: var(--card-bg);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 24px 28px;
    box-shadow: var(--shadow-card);
    transition: box-shadow 0.25s ease, transform 0.25s ease;
    position: relative;
    overflow: hidden;
  }}

  .card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px;
    height: 100%;
    background: var(--accent);
    opacity: 0.35;
    border-radius: 4px 0 0 4px;
  }}

  .card:hover {{
    box-shadow: var(--shadow-card-hover);
    transform: translateY(-1px);
  }}

  .card-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }}

  .card-header .rank {{
    font-size: 13px;
    font-weight: 600;
    color: var(--accent);
    background: var(--tag-bg);
    padding: 2px 10px;
    border-radius: 6px;
    min-width: 32px;
    text-align: center;
  }}

  .card-header .project-name {{
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    text-decoration: none;
    letter-spacing: -0.01em;
    transition: color 0.2s;
  }}

  .card-header .project-name:hover {{
    color: var(--accent);
  }}

  .card-header .lang-tag {{
    font-size: 11px;
    font-weight: 500;
    color: var(--tag-text);
    background: var(--tag-bg);
    padding: 2px 10px;
    border-radius: 6px;
    letter-spacing: 0.02em;
  }}

  .card-stats {{
    display: flex;
    gap: 16px;
    font-size: 13px;
    color: var(--text-secondary);
    margin-left: auto;
  }}

  .card-stats .stat {{
    display: flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
  }}

  .card-stats .stat-total {{
    color: var(--text-secondary);
    font-weight: 500;
  }}

  .card-stats .stat-weekly {{
    color: var(--star-gold);
    font-weight: 600;
  }}

  .card-body {{
    padding-left: 46px;
  }}

  .card-body .one-liner {{
    font-size: 14px;
    color: var(--text-primary);
    margin-bottom: 12px;
    line-height: 1.55;
  }}

  .card-body .section-label {{
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
  }}

  .card-body ul {{
    list-style: none;
    padding: 0;
    margin-bottom: 14px;
  }}

  .card-body ul li {{
    font-size: 13px;
    color: var(--text-secondary);
    padding: 3px 0;
    padding-left: 16px;
    position: relative;
    line-height: 1.55;
  }}

  .card-body ul li::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 10px;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--accent-soft);
  }}

  .tags {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }}

  .tags .tag {{
    font-size: 11px;
    font-weight: 500;
    color: var(--tag-text);
    background: var(--tag-bg);
    padding: 3px 12px;
    border-radius: 14px;
    letter-spacing: 0.01em;
    white-space: nowrap;
  }}

  /* Footer */
  .footer {{
    text-align: center;
    margin-top: 48px;
    padding-top: 24px;
    border-top: 1px solid rgba(212,104,74,0.1);
    font-size: 12px;
    color: var(--text-muted);
  }}

  .footer a {{
    color: var(--accent);
    text-decoration: none;
    font-weight: 500;
  }}

  .footer a:hover {{
    text-decoration: underline;
  }}

  .trend-keywords {{
    text-align: center;
    margin: 36px 0 12px;
    font-size: 13px;
    color: var(--text-muted);
  }}

  .trend-keywords strong {{
    color: var(--accent);
    font-weight: 600;
  }}

  @media (max-width: 640px) {{
    .container {{ padding: 28px 14px 48px; }}
    .card {{ padding: 18px 16px; }}
    .card-body {{ padding-left: 32px; }}
    .card-header .project-name {{ font-size: 15px; }}
    .card-stats {{ margin-left: 0; margin-top: 4px; width: 100%; }}
  }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>GitHub Trending · AI/ML 周榜</h1>
    <p class="subtitle">{datetime.now().strftime("%Y 年 %m 月第 %W 周")} · 人工智能与机器学习热门开源项目</p>
    <span class="fetch-time">数据抓取时间：{fetch_time}</span>
  </div>

  <p class="trend-keywords">本周关键词：{keywords_str}</p>

  <!-- Card List -->
  <div class="card-list">
    {chr(10).join(cards_html)}
  </div>

  <!-- Footer -->
  <div class="footer">
    <p>数据来源：<a href="https://github.com/trending?since=weekly" target="_blank">GitHub Trending (Weekly)</a> · 基于 AI/ML 关键词智能筛选</p>
    <p style="margin-top:4px;">页面生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} · 脚本自动抓取</p>
  </div>

</div>
</body>
</html>'''
    return html_template

def main() -> str:
    """主函数，返回生成的HTML文件路径（文件名包含日期）"""
    try:
        repos = fetch_trending_repos()
        if not repos:
            return ""
        
        ai_repos = [r for r in repos if is_ai_related(r)]
        ai_repos.sort(key=lambda x: x["weekly_stars"], reverse=True)
        top_20 = ai_repos[:20]
        if len(top_20) < 20:
            non_ai = [r for r in repos if not is_ai_related(r)]
            non_ai.sort(key=lambda x: x["weekly_stars"], reverse=True)
            needed = 20 - len(top_20)
            top_20.extend(non_ai[:needed])
        top_20 = top_20[:20]
        
        keywords = extract_trend_keywords(top_20)
        fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC+8")
        html_content = generate_html(top_20, fetch_time, keywords)
        
        # 生成带日期的文件名，格式：github_trending_ai_YYYY_MM_DD.html
        # 输出到项目 data 目录
        date_str = datetime.now().strftime("%Y_%m_%d")
        output_file = f"github_trending_ai_{date_str}.html"
        output_path = get_app_data_path(f"data/{output_file}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return str(output_path)
    except Exception:
        return ""

if __name__ == "__main__":
    # 静默执行，不输出任何信息（仅生成文件）
    _ = main()