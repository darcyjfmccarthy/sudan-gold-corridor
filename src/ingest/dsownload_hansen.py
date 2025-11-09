import subprocess
import os
from pathlib import Path

OUT = Path("data/raw/hansen_loss.tif")
OUT.parent.mkdir(parents=True, exist_ok=True)

def download_hansen():
    cmd = [
        "aws", "s3", "cp",
        "s3://gfw-data-lake/hansen/tiles/hansen_treecover_loss.tif",
        str(OUT),
        "--no-sign-request"
    ]
    subprocess.run(cmd, check=True)
    print(f"Hansen forest loss raster saved to {OUT}")

if __name__ == "__main__":
    download_hansen()
