import requests
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
from io import StringIO

load_dotenv()

API_KEY = os.getenv('FIRMS_MAP_KEY')

PRODUCT = "VIIRS_SNPP_NRT"

# Sudan + Darfur + Kordofan bounding box (approx)
BBOX = "21,8,33,18"

def download_firms(output_path="data/raw/firms_sudan_area.csv"):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{API_KEY}/{PRODUCT}/{BBOX}/10"
    print(f"Requesting FIRMS from: {url}")

    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"Error {r.status_code}: {r.text}")

    new_df = pd.read_csv(StringIO(r.text))
    new_df.columns = [c.strip().lower() for c in new_df.columns]

    if "acq_date" in new_df.columns:
        try:
            new_df["acq_date"] = pd.to_datetime(new_df["acq_date"])
        except Exception:
            pass

    if os.path.exists(output_path):
        old_df = pd.read_csv(output_path)
        old_df.columns = [c.strip().lower() for c in old_df.columns]
        combined = pd.concat([old_df, new_df], ignore_index=True)

        dedupe_cols = [c for c in ["latitude","longitude","acq_date","satellite","instrument","frp","confidence","version"] if c in combined.columns]
        if dedupe_cols:
            combined = combined.drop_duplicates(subset=dedupe_cols)
        else:
            combined = combined.drop_duplicates()
    else:
        combined = new_df

    combined.to_csv(output_path, index=False)
    print(f"FIRMS appended to {output_path} (rows: {len(combined)})")

if __name__ == "__main__":
    download_firms()