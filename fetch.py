import pandas as pd, requests, datetime as dt
from pytrends.request import TrendReq

today = dt.date.today().isoformat()

# ---------- 1. FRED (no key needed) ----------
def fred(series):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
    return float(pd.read_csv(url).iloc[-1, 1])

cape   = fred('CAPE')
tobinq = fred('TOBINQ')
hhld   = fred('MEFBTAA158N') / 100          # household equity %
mag7   = 0.36                                # hard-code until you scrape
nvda_ps= 38                                  # hard-code (or scrape Yahoo)

# ---------- 2. Google Trends ----------
pytrend = TrendReq(hl='en-US', tz=360)
kw = ['AI stock', 'NVDA stock', 'ChatGPT stock']
pytrend.build_payload(kw, timeframe='today 3-m')
gt = pytrend.interest_over_time().mean().mean()

# ---------- 3. GPU lead-time placeholder ----------
gpu_weeks = 20

# ---------- 4. Insider selling ----------
try:
    url = ('http://openinsider.com/screener?s=nvda&o=&pl=1&ph=&ll=1&lh='
           '&fd=730&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl=1'
           '&vh=&cl=1&ch=&scl=1&sch=&oc=1&sortcol=0&cnt=100&page=1')
    ins = pd.read_csv(url)
    insider = float(ins['Value ($)'].sum()) / 1e6   # $ million
except:
    insider = 150                                   # fallback

# ---------- 5. z-score ----------
z = ( (cape - 30) / 10 +
      (tobinq - 1.5) / 0.5 +
      (nvda_ps - 30) / 5 +
      (gt - 50) / 20 +
      (gpu_weeks - 16) / 4 +
      (insider - 100) / 50 )
z = round(z, 2)

# ---------- 6. Push row to Google Sheet ----------
GAS_URL = 'https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec'  # <-- replace only this line
params = {
  'date': today, 'cape': cape, 'tobinq': tobinq, 'mag7': mag7,
  'nvda_ps': nvda_ps, 'hhld': hhld, 'gt_ai': gt, 'gpu': gpu_weeks,
  'insider': insider, 'dc': 0, 'z': z
}
requests.get(GAS_URL, params=params, timeout=30)

# ---------- 7. Mirror CSV for GitHub Pages ----------
out = pd.DataFrame([params])
out.to_csv('docs/data.csv', index=False)