import pandas as pd
import requests
import datetime as dt
from pytrends.request import TrendReq

today = dt.date.today().isoformat()
# ---------- 1. FRED (JSON API – no key needed for < 50 calls/day) ----------
def fred(series: str) -> float:
    API_KEY = "c63f4de89b61c8ee0b910235aebbadc1"
    url = (
        f'https://api.stlouisfed.org/fred/series/observations'
           f'?series_id={series}&api_key={API_KEY}&file_type=json&limit=1&sort_order=desc'
    )
    return float(requests.get(url, timeout=20).json()["observations"][0]["value"])

cape    = fred("CAPE")
tobinq  = fred("TOBINQ")
hhld    = fred("MEFBTAA158N") / 100          # household equity %

# ---------- 2. Hard-coded placeholders (replace with live scrapes later) ----------
mag7    = 0.36
nvda_ps = 38

# ---------- 3. Google Trends ----------
pytrend = TrendReq(hl="en-US", tz=360)
kw = ["AI stock", "NVDA stock", "ChatGPT stock"]
pytrend.build_payload(kw, timeframe="today 3-m")
gt = pytrend.interest_over_time().mean().mean()

# ---------- 4. GPU lead-time placeholder ----------
gpu_weeks = 20

# ---------- 5. Insider selling ----------
try:
    url = (
        "http://openinsider.com/screener?s=nvda&o=&pl=1&ph=&ll=1&lh=&fd=730&fdr=&td=0"
        "&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl=1&vh=&cl=1&ch=&scl=1&sch=&oc=1"
        "&sortcol=0&cnt=100&page=1"
    )
    insider = float(pd.read_csv(url)["Value ($)"].sum()) / 1e6
except Exception:
    insider = 150  # fallback

# ---------- 6. z-score composite ----------
z = (
    (cape - 30) / 10
    + (tobinq - 1.5) / 0.5
    + (nvda_ps - 30) / 5
    + (gt - 50) / 20
    + (gpu_weeks - 16) / 4
    + (insider - 100) / 50
)
z = round(z, 2)

# ---------- 7. Push row to Google Sheet ----------
GAS_URL = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"  # <-- replace only this
params = {
    "date": today, "cape": cape, "tobinq": tobinq, "mag7": mag7,
    "nvda_ps": nvda_ps, "hhld": hhld, "gt_ai": gt, "gpu": gpu_weeks,
    "insider": insider, "dc": 0, "z": z,
}
requests.get(GAS_URL, params=params, timeout=30)

# ---------- 8. Mirror CSV for GitHub Pages ----------
pd.DataFrame([params]).to_csv("docs/data.csv", index=False)
