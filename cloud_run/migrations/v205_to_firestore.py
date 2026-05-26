"""v205 (Apps Script) → Firestore migration.

Reads CSV exports produced by the v205 endpoints:
    exportBrandMappingToCSV   → brand_mappings_<date>.csv
    exportCategoryMappingToCSV → category_mappings_<date>.csv
    exportMonthlySnapshotsToCSV → monthly_snapshots_<date>.csv

Writes into Firestore at users/{target_user_id}/...

Usage:
    python v205_to_firestore.py --user-id <uid> --dir /path/to/csvs [--dry-run]
"""
from __future__ import annotations
import argparse
import csv
import glob
import os
import sys
import time
from pathlib import Path


def _load_csv(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", required=True)
    ap.add_argument("--dir", required=True, help="directory containing v205 CSV exports")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.services.firestore_client import user_col, init_firestore
    init_firestore()

    summary = {"brand_mappings": 0, "category_mappings": 0, "monthly_snapshots": 0}

    # category_mappings
    for path in glob.glob(os.path.join(args.dir, "category_mapping*.csv")):
        for row in _load_csv(path):
            doc = {
                "tier": int(row.get("tier") or 1),
                "category": row.get("category", ""),
                "item_type_filter": row.get("item_type_filter", ""),
                "include_keywords": row.get("포함_키워드") or row.get("include_keywords", ""),
                "exclude_keywords": row.get("제외_키워드") or row.get("exclude_keywords", ""),
                "accuracy_basis": row.get("정확도_기준") or row.get("accuracy_basis", "80%+"),
                "migrated_at": time.time(),
            }
            if not args.dry_run:
                user_col(args.user_id, "category_mappings").document().set(doc)
            summary["category_mappings"] += 1

    # brand_mappings
    for path in glob.glob(os.path.join(args.dir, "brand_mapping*.csv")):
        for row in _load_csv(path):
            doc = {
                "category": row.get("category", ""),
                "brand": row.get("brand", ""),
                "display_name": row.get("display_name", ""),
                "seller_keywords": row.get("영업자_keywords") or row.get("seller_keywords", ""),
                "brand_keywords": row.get("brand_keywords", ""),
                "type": row.get("type", ""),
                "DART_revenue_eok": float(row["DART_매출_억"]) if row.get("DART_매출_억") else None,
                "confidence": row.get("신뢰등급") or row.get("confidence", "M"),
                "migrated_at": time.time(),
            }
            if not args.dry_run:
                user_col(args.user_id, "brand_mappings").document().set(doc)
            summary["brand_mappings"] += 1

    # monthly_snapshots
    for path in glob.glob(os.path.join(args.dir, "monthly_snapshots*.csv")):
        for row in _load_csv(path):
            doc = {
                "month": row.get("month", ""),
                "category": row.get("category", ""),
                "brand": row.get("brand", ""),
                "production_kg": float(row.get("production_kg") or 0),
                "mapping_coverage": float(row.get("mapping_coverage") or 0),
                "total_rows": int(row.get("total_rows") or 0),
                "migrated_at": time.time(),
            }
            if not args.dry_run:
                user_col(args.user_id, "monthly_snapshots").document().set(doc)
            summary["monthly_snapshots"] += 1

    print(f"Migration {'(dry-run) ' if args.dry_run else ''}complete: {summary}")


if __name__ == "__main__":
    main()
