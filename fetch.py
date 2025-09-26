# fetch.py  –  historical Fed data + live daily proxies  (zero-maintenance)
import pandas as pd
import requests
import datetime as dt
import os
import time
from pytrends.request import TrendReq

today       = dt.date.today()
GAS_URL     = 'https://script.google.com/macros/s/AKfycby3ohuCJJywDanfdrAN3fas527MM5lxsWz4MrAKUN4RxsHKffmW_lzQlodmMMe4g2awXw/exec'  # ← Apps-Script url
FED_CSV     = 'fed_history.csv'          # local cache
PROXY_CSV   = 'docs/data.csv'            # live dashboard file

hdr = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ---------- 1.  download Fed history once ----------
def fed_history() -> pd.DataFrame:
    """monthly CAPE + quarterly Tobin-Q + quarterly HH-equity  (Fed Z.1)"""
    # CAPE (monthly)
    cape = pd.read_csv('https://www.multpl.com/shiller-pe/table/by-month', header=0,
                       names=['date','cape'], thousands=',')
    cape['date'] = pd.to_datetime(cape['date'])

    # Tobin-Q (quarterly from Fed Z.1 HTML table)
    tq = pd.read_html(requests.get('https://www.federalreserve.gov/releases/z1/current/',
                                   headers=hdr, timeout=30).text, match='Tobin')[0]
    tq = tq.rename(columns={'Period':'date','Value':'tobinq'})
    tq['date'] = pd.to_datetime(tq['date'])

    # Household equity % (quarterly CSV link inside B.101.e)
    hh = pd.read_csv('https://www.federalreserve.gov/releases/z1/current/csv/b101e.csv',
                     skiprows=5, usecols=['Year','Q1','Q2','Q3','Q4']).melt(
                     id_vars='Year', var_name='q', value_name='hhld')
    hh['date'] = pd.to_datetime(hh['Year'].astype(str) + hh['q'].str[1], format='%Y%q')
    hh = hh[['date','hhld']].dropna()

    # merge on date (forward-fill quarterly into monthly)
    fed = (cape
           .merge(tq,  on='date', how='left')
           .merge(hh,  on='date', how='left'))
    fed[['tobinq','hhld']] = fed[['tobinq','hhld']].ffill()
    fed = fed.dropna(subset=['cape'])          # keep only months we have CAPE
    return fed

# ---------- 2.  live daily proxies ----------
def proxy_today() -> pd.Series:
    """today’s values from multpl + Google Trends"""
    tbl = lambda slug: float(pd.read_html(requests.get(f'https://www.multpl.com/{slug}/table/by-month',
                                                       headers=hdr, timeout=20).text, match='Date')[0].iloc[0,1])
    cape  = tbl('shiller-pe')
    pe    = tbl('s-p-500-pe-ratio')
    ps    = tbl('price-to-sales')

    pytrend = TrendReq(hl='en-US', tz=360)
    kw = ['AI stock','NVDA stock','ChatGPT stock']
    pytrend.build_payload(kw, timeframe='today 3-m')
    gt_ai = pytrend.interest_over_time().mean().mean()

    mag7=0.36; gpu=20; insider=150; dc=0; hhld_proxy=0.31
    z = ( (cape - 30)/10 + (pe - 20)/5 + (ps - 30)/5 +
          (gt_ai - 50)/20 + (gpu - 16)/4 + (insider - 100)/50 ).round(2)
    return pd.Series({'date':today,'cape':cape,'pe':pe,'tobinq':ps,'mag7':mag7,
                      'nvda_ps':ps,'hhld':hhld_proxy,'gt_ai':gt_ai,'gpu':gpu,
                      'insider':insider,'dc':dc,'z':z})

# ---------- 3.  main logic ----------
if os.path.exists(FED_CSV):                      # already have history
    fed = pd.read_csv(FED_CSV, parse_dates=['date'])
    last_fed = fed['date'].max().date()
    if today <= last_fed:                        # still inside Fed history → proxy
        row = proxy_today()
    else:                                        # new Fed quarter dropped → re-download
        fed = fed_history()
        fed.to_csv(FED_CSV, index=False)
        row = proxy_today()
else:                                            # first run → build history
    fed = fed_history()
    fed.to_csv(FED_CSV, index=False)
    row = proxy_today()

# append today’s proxy row
live = pd.read_csv(PROXY_CSV) if os.path.exists(PROXY_CSV) else pd.DataFrame()
live = pd.concat([live, row.to_frame().T], ignore_index=True).drop_duplicates(subset=['date'])
live.to_csv(PROXY_CSV, index=False)

# push to Google Sheet
requests.get(GAS_URL, params=row.to_dict(), timeout=30)
print('done', today, 'z=', row.z)
