import yaml
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from .data_store import init_db, upsert_quote, insert_news_batch
from .finance import fetch_snapshot, get_company_name
from .news import fetch_news_for

def refresh_all(config_path: str = 'config.yaml'):
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    db_path = cfg.get('database_path', 'stocks.db')
    watchlist = cfg.get('watchlist', [])
    company_names = cfg.get('company_names', {})

    init_db(db_path)
    now = datetime.utcnow().strftime('%Y-%m-%d')
    updated_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    for t in watchlist:
        snap = fetch_snapshot(t)
        row = {
            'ticker': t,
            'asof': now,
            'price': snap.get('price'),
            'pe_ttm': snap.get('pe_ttm'),
            'pb': snap.get('pb'),
            'ev_ebitda': snap.get('ev_ebitda'),
            'market_cap': snap.get('market_cap'),
            'updated_at': updated_at
        }
        upsert_quote(db_path, row)

        cname = company_names.get(t) or get_company_name(t) or t
        news_rows = fetch_news_for(t, cname, days=7)
        insert_news_batch(db_path, news_rows)

    print(f"[refresh_all] {updated_at} - refreshed: {', '.join(watchlist)}")

def main():
    sched = BlockingScheduler(timezone='Asia/Seoul')
    sched.add_job(lambda: refresh_all('config.yaml'),
                  'cron', hour=7, minute=0)
    print('[scheduler] started. Ctrl+C to stop.')
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print('[scheduler] stopped.')

if __name__ == '__main__':
    main()
