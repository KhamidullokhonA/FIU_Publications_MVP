"""Persistent area/year dates for FIU Publications.

Local: area_dates.json (atomic file replacement).
Cloud: Supabase Postgres (selected-year updates only).
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

DATES_PATH = Path(__file__).resolve().parent / "area_dates.json"


def _secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except FileNotFoundError:
        return default


def is_cloud_storage() -> bool:
    mode = _secret("DATE_STORAGE", "local").lower()
    if mode not in {"local", "cloud"}:
        raise ValueError("DATE_STORAGE must be 'local' or 'cloud'.")
    return mode == "cloud"


def _client():
    from supabase import create_client
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise ValueError("Cloud date storage requires SUPABASE_URL and SUPABASE_SECRET_KEY.")
    return create_client(url, key)


def _validate(mapping: dict[str, str]) -> None:
    if not isinstance(mapping, dict):
        raise ValueError("Saved area dates must be a JSON object.")
    for key, value in mapping.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Area dates require string keys and ISO date values.")
        year_string, separator, area = key.partition("|")
        if not separator or not year_string.isdigit() or not area:
            raise ValueError(f"Invalid area/year key: {key!r}")
        parsed = date.fromisoformat(value)
        if parsed.year != int(year_string) or parsed.isoformat() != value:
            raise ValueError(f"Invalid date for {key!r}: {value!r}")


def load_area_dates() -> dict[str, str]:
    if is_cloud_storage():
        rows = (
            _client()
            .table("area_dates")
            .select("year,area,assigned_date")
            .order("year")
            .execute()
            .data
        )
        # This app has a small number of venues. If your table grows above
        # Supabase's query row limit, add pagination here.
        result = {
            f"{int(row['year'])}|{row['area']}": row["assigned_date"]
            for row in rows
        }
    else:
        if not DATES_PATH.exists():
            return {}
        with DATES_PATH.open(encoding="utf-8") as f:
            result = json.load(f)
    _validate(result)
    return result


def save_area_dates(data: dict[str, str], *, editing_year: int) -> None:
    _validate(data)
    if is_cloud_storage():
        client = _client()
        year_prefix = f"{editing_year}|"
        year_values = {
            key.partition("|")[2]: value
            for key, value in data.items()
            if key.startswith(year_prefix)
        }
        existing_rows = (
            client.table("area_dates")
            .select("area")
            .eq("year", editing_year)
            .execute()
            .data
        )
        existing_areas = {row["area"] for row in existing_rows}
        new_areas = set(year_values)
        if year_values:
            rows = [
                {"year": editing_year, "area": area, "assigned_date": value}
                for area, value in year_values.items()
            ]
            client.table("area_dates").upsert(rows, on_conflict="year,area").execute()
        for area in existing_areas - new_areas:
            client.table("area_dates").delete().eq("year", editing_year).eq("area", area).execute()
        return

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=DATES_PATH.parent,
            prefix=".area-dates-", suffix=".json", delete=False,
        ) as output:
            tmp_path = Path(output.name)
            json.dump(data, output, indent=2, ensure_ascii=False, sort_keys=True)
            output.write("\n")
        os.replace(tmp_path, DATES_PATH)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
