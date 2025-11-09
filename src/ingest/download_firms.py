import requests
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

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

    new_df = pd.read_csv(pd.compat.StringIO(r.text))

    # Load old dataset if exists
    if os.path.exists(output_path):
        old_df = pd.read_csv(output_path)
        combined = pd.concat([old_df, new_df]).drop_duplicates()
    else:
        combined = new_df

    combined.to_csv(output_path, index=False)
    print(f"FIRMS appended to {output_path} (rows: {len(combined)})")


if __name__ == "__main__":
    download_firms()