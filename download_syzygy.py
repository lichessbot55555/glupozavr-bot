import os
import re
import urllib.request
from urllib.parse import urljoin, unquote

BASE = "https://tablebase.lichess.ovh/tables/standard/"

JOBS = [
    ("3-4-5-wdl/", r"C:\Syzygy\3-4-5-wdl"),
    ("3-4-5-dtz/", r"C:\Syzygy\3-4-5-dtz"),
]

def get_links(url):
    with urllib.request.urlopen(url) as r:
        html = r.read().decode("utf-8", errors="ignore")

    links = re.findall(r'href="([^"]+)"', html)
    return links

def download_file(url, out_path):
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"[SKIP] {out_path}")
        return

    print(f"[GET]  {url}")
    print(f"[SAVE] {out_path}")

    tmp_path = out_path + ".part"

    with urllib.request.urlopen(url) as r, open(tmp_path, "wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    os.replace(tmp_path, out_path)
    print("[OK]")

def main():
    for folder, target_dir in JOBS:
        os.makedirs(target_dir, exist_ok=True)

        page_url = urljoin(BASE, folder)
        print(f"\n=== {page_url} ===")

        links = get_links(page_url)

        for link in links:
            name = unquote(link)

            if name.startswith("../"):
                continue

            if not (name.endswith(".rtbw") or name.endswith(".rtbz")):
                continue

            file_url = urljoin(page_url, name)
            out_path = os.path.join(target_dir, os.path.basename(name))

            download_file(file_url, out_path)

if __name__ == "__main__":
    main()