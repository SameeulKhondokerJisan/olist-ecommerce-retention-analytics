"""Download the Olist Brazilian E-Commerce Public Dataset into data/raw/.

Source: Olist's official repository https://github.com/olist/work-at-olist-data
(the same nine CSVs published at kaggle.com/datasets/olistbr/brazilian-ecommerce).
License: CC BY-NC-SA 4.0. Raw files are git-ignored and never committed.

Usage:
    python -m src.download_data
"""
from __future__ import annotations

from pathlib import Path

from src._fetch import content_length, fetch, sha256, write_manifest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPO_RAW = "https://raw.githubusercontent.com/olist/work-at-olist-data/{branch}/datasets/{name}"
FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]


def _branch() -> str:
    for branch in ("master", "main"):
        try:
            content_length(REPO_RAW.format(branch=branch, name=FILES[-1]))
            return branch
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError("Could not reach github.com/olist/work-at-olist-data")


def main() -> None:
    branch = _branch()
    entries = []
    for name in FILES:
        url = REPO_RAW.format(branch=branch, name=name)
        path = fetch(url, RAW / name)
        entries.append({"file": name, "bytes": path.stat().st_size, "sha256": sha256(path), "url": url})
        print(f"ok  {name:45s} {path.stat().st_size / 1e6:8.1f} MB")
    write_manifest(RAW, entries)


if __name__ == "__main__":
    main()
