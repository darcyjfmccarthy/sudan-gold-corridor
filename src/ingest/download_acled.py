import os
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("ACLED_EMAIL")
PASSWORD = os.getenv("ACLED_PASSWORD")

login_url = "https://acleddata.com/user/login?_format=json"
api_url = "https://acleddata.com/api/acled/read"

# Sudan chunks
DATE_WINDOWS = [
    ("2018-01-01", "2019-12-31"),
    ("2020-01-01", "2021-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2024-01-01", "2025-12-31"),
]

session = requests.Session()
resp = session.post(login_url, json={"name": EMAIL, "pass": PASSWORD})
resp.raise_for_status()

if "current_user" not in resp.json():
    raise RuntimeError("Login failed — check credentials")

print(f"[✓] Logged in as {resp.json()['current_user']['name']}")

r = session.get("https://acleddata.com/api/acled/read?limit=1")
print(r.status_code, r.text[:200])

frames = []
for start, end in DATE_WINDOWS:
    params = {
        "country": "Sudan",
        "event_date": f"{start}|{end}",
        "event_date_where": "BETWEEN",
        "_format": "json",
        "limit": "5000"
    }

    print(f"Fetching {start} → {end}")
    r = session.get(api_url, params=params)
    r.raise_for_status()

    data = r.json().get("data", [])
    if not data:
        print(f"No results returned for {start}-{end}")
        continue

    frames.append(pd.DataFrame(data))

df_all = pd.concat(frames, ignore_index=True)
Path("data/raw").mkdir(parents=True, exist_ok=True)
df_all.to_csv("data/raw/acled_sudan.csv", index=False)

print(f"Saved {len(df_all)} events to data/raw/acled_sudan.csv")