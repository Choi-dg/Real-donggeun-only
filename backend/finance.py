import os
import math
from typing import Dict, Optional
import yfinance as yf
import requests

def get_company_name(ticker: str):
    try:
        info = yf.Ticker(ticker).get_info(timeout=20)
        return info.get('shortName') or info.get('longName')
    except Exception:
        return None

def fetch_snapshot_yf(ticker: str) -> Dict:
    t = yf.Ticker(ticker)
    info = {}
    try:
        info = t.get_info(timeout=20)
    except Exception:
        info = {}
    try:
        fast = t.fast_info
    except Exception:
        fast = {}
    price = fast.get('last_price')
    if price is None:
        try:
            hist = t.history(period='1d')
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
        except Exception:
            price = None
    pe = info.get('trailingPE')
    pb = info.get('priceToBook')
    ev_ebitda = info.get('enterpriseToEbitda')
    market_cap = info.get('marketCap') or fast.get('market_cap')
    def clean(x):
        if x is None: return None
        if isinstance(x, float) and math.isnan(x): return None
        try: return float(x)
        except Exception: return None
    return {
        'price': clean(price),
        'pe_ttm': clean(pe),
        'pb': clean(pb),
        'ev_ebitda': clean(ev_ebitda),
        'market_cap': clean(market_cap),
        'provider': 'yfinance'
    }

def fetch_snapshot_fmp(ticker: str, api_key: Optional[str]) -> Optional[Dict]:
    if not api_key:
        return None
    try:
        base = "https://financialmodelingprep.com/api/v3"
        q = requests.get(f"{base}/quote/{ticker}?apikey={api_key}", timeout=20).json()
        if not q: return None
        quote = q[0]
        km = requests.get(f"{base}/key-metrics-ttm/{ticker}?apikey={api_key}", timeout=20).json()
        km0 = km[0] if km else {}
        return {
            'price': quote.get('price'),
            'pe_ttm': quote.get('pe'),
            'pb': km0.get('pbRatio'),
            'ev_ebitda': km0.get('enterpriseValueOverEBITDA'),
            'market_cap': quote.get('marketCap'),
            'provider': 'fmp'
        }
    except Exception:
        return None

def fetch_snapshot(ticker: str, prefer: str = 'fmp') -> Dict:
    api_key = os.getenv('FMP_API_KEY', '') or ''
    if prefer == 'fmp':
        s = fetch_snapshot_fmp(ticker, api_key)
        return s or fetch_snapshot_yf(ticker)
    else:
        s = fetch_snapshot_yf(ticker)
        return s or fetch_snapshot_fmp(ticker, api_key)

def fetch_price_history(ticker: str, period: str = '1y', interval: str = '1d'):
    t = yf.Ticker(ticker)
    return t.history(period=period, interval=interval)
