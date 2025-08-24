from typing import List, Dict, Optional
import feedparser, time, urllib.parse

def _google_news_url(query: str, days: int = 7, lang: str = 'en-US', country: str = 'US'):
    q = urllib.parse.quote_plus(f"{query} when:{days}d")
    return f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={country}&ceid={country}:{lang}"

def fetch_news_for(ticker: str, company_name: Optional[str] = None, days: int = 7) -> List[Dict]:
    q = company_name or ticker
    query = f"{q} OR {ticker}"
    url = _google_news_url(query, days=days)
    parsed = feedparser.parse(url)
    rows = []
    fetched_at = time.strftime('%Y-%m-%d %H:%M:%S')
    for e in parsed.entries:
        link = getattr(e, 'link', '')
        title = getattr(e, 'title', '')
        published = getattr(e, 'published', '') or getattr(e, 'updated', '') or fetched_at
        summary = getattr(e, 'summary', '') or ''
        source = ''
        if hasattr(e, 'source') and getattr(e, 'source'):
            src = getattr(e, 'source')
            source = getattr(src, 'title', '') or getattr(src, 'href', '')
        rows.append({
            'ticker': ticker,
            'published': published,
            'source': source,
            'title': title,
            'url': link,
            'summary': summary,
            'fetched_at': fetched_at
        })
    return rows
