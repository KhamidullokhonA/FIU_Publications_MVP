"""Explore a local CSRankings articles.json snapshot for FIU-affiliated authors.

Run: streamlit run fiu_publications_app.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import hmac

from area_date_storage import (
    is_cloud_storage,
    load_area_dates,
    save_area_dates,
)

os.environ["PYTHONUTF8"] = "1"
INSTITUTION = "Florida International University"
DEFAULT_PATH = Path(__file__).resolve().parent / "articles.json"
DATES_PATH = DEFAULT_PATH.parent / "area_dates.json"

st.set_page_config(page_title="FIU CSRankings Publications", page_icon="📚", layout="wide")


@st.cache_data(show_spinner="Loading CSRankings publication snapshot...")
def load_fiu_articles(path: str, mtime_ns: int) -> pd.DataFrame:
    """Cache parsing, invalidating when the local snapshot changes."""
    del mtime_ns  # cache-key only
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        raise ValueError("Expected articles.json to contain a JSON list.")

    fiu = [
        {
            "Professor": item["name"],
            "Year": int(item["year"]),
            "Title": item["title"],
            "Area": item.get("area", ""),
            "Number of authors": item.get("numauthors"),
            "Page count": item.get("pageCount"),
        }
        for item in records
        if isinstance(item, dict)
        and item.get("institution") == INSTITUTION
        and item.get("name")
        and item.get("year") is not None
        and item.get("title")
    ]
    if not fiu:
        raise ValueError(f"No records found with institution={INSTITUTION!r}.")
    df = pd.DataFrame.from_records(fiu)
    # One row is one author-publication credit in the generated snapshot.
    # Do not deduplicate by title: this would change CSRankings source counts.
    return df


def area_year_key(year: int, area: str) -> str:
    return f"{year}|{area}"


def locate_csrankings_repo() -> Path | None:
    """Find an existing checkout; do not clone or run commands from user input."""
    choices = [
        os.environ.get("CSRANKINGS_REPO"),
        Path.home() / "CSrankings",
        Path.home() / "Documents" / "CSrankings",
        Path(__file__).resolve().parent.parent / "CSrankings",
    ]
    for choice in choices:
        if choice:
            candidate = Path(choice).expanduser().resolve()
            if (candidate / ".git").exists() and (candidate / "util" / "regenerate_data.py").is_file():
                return candidate
    return None


@st.cache_resource
def refresh_mutex() -> threading.Lock:
    """One refresh at a time, shared across Streamlit browser sessions."""
    return threading.Lock()


def run_checked(command: list[str], repo: Path, timeout: int) -> str:
    result = subprocess.run(
        command, cwd=str(repo), capture_output=True, text=True,
        timeout=timeout, check=False,
    )
    if result.returncode:
        details = (result.stderr or result.stdout).strip()[-1800:]
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{details}")
    return result.stdout.strip()


def validate_snapshot(path: Path) -> tuple[int, int]:
    with path.open(encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        raise ValueError("New articles.json is not a JSON list.")
    count = sum(
        1 for record in records
        if isinstance(record, dict)
        and record.get("institution") == INSTITUTION
        and record.get("name")
        and record.get("title")
        and isinstance(record.get("year"), int)
    )
    if count == 0:
        raise ValueError("The refreshed snapshot contains no FIU publications.")
    return len(records), count


def update_from_csrankings(repo: Path) -> tuple[str, int, int]:
    """Pull official repository inputs, regenerate details, then atomically publish."""
    git_output = run_checked(["git", "pull", "--ff-only"], repo, timeout=180)
    if not (repo / "dblp.xml.xz").is_file():
        raise FileNotFoundError(
            "CSRankings checkout has no dblp.xml.xz. "
            "A Git pull alone cannot produce paper details without a DBLP input."
        )
    run_checked([sys.executable, "util/split-csv.py"], repo, timeout=180)
    run_checked([sys.executable, "util/regenerate_data.py"], repo, timeout=1500)
    new_source = repo / "articles.json"
    if not new_source.is_file():
        raise FileNotFoundError("CSRankings did not generate articles.json.")
    total, fiu_count = validate_snapshot(new_source)
    # Preserve the working snapshot until the new one has passed validation.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=DEFAULT_PATH.parent, prefix=".articles-", suffix=".json", delete=False
        ) as output:
            tmp_path = Path(output.name)
            with new_source.open("rb") as source:
                shutil.copyfileobj(source, output)
        os.replace(tmp_path, DEFAULT_PATH)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
    load_fiu_articles.clear()
    return git_output, total, fiu_count


st.title("FIU CSRankings publication explorer")
st.caption("Uses the latest successfully loaded local CSRankings snapshot, not live DBLP results.")

with st.expander("Update publication data", expanded=False):
    st.write(
        "Anyone can request an update. This pulls the latest tracked files from the "
        "official CSRankings checkout and regenerates articles.json using its existing "
        "filtered DBLP snapshot. It does not download a newer DBLP release."
    )
    repo = locate_csrankings_repo()
    if repo is None:
        st.info(
        "Publication updates are managed through GitHub Actions."
        )
        st.link_button(
            "Update Publications on GitHub",
            "https://github.com/KhamidullokhonA/"
            "FIU_Publications_MVP/actions/workflows/update-publications.yml",
        )
    else:
        st.caption(f"Data source: {repo}")
    
    if repo is not None:
        if st.button("Check and update publication data", disabled=repo is None):
            mutex = refresh_mutex()
        if not mutex.acquire(blocking=False):
            st.warning("An update is already running. Please try again later.")
        else:
            try:
                with st.spinner("Pulling and regenerating data. This may take several minutes..."):
                    git_output, total, fiu_count = update_from_csrankings(repo)
                st.success(
                    f"Snapshot updated: {total:,} author–paper records "
                    f"({fiu_count:,} FIU records)."
                )
                st.caption(f"Git: {git_output.splitlines()[-1] if git_output else 'Success'}")
                st.rerun()
            except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
                st.error(f"Update failed; previous working dataset kept. Details: {exc}")
            finally:
                mutex.release()

if DEFAULT_PATH.is_file():
    st.caption(
        "Active articles.json file modified: "
        + datetime.fromtimestamp(DEFAULT_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        + " (server local time; not necessarily DBLP publication date)."
    )

if not DEFAULT_PATH.is_file():
    st.error("Missing articles.json. Put this script next to your CSRankings articles.json file.")
    st.stop()

try:
    articles = load_fiu_articles(str(DEFAULT_PATH), DEFAULT_PATH.stat().st_mtime_ns)
except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
    st.error(f"Could not load the publication snapshot: {exc}")
    st.stop()

min_year = int(articles["Year"].min())
max_year = int(articles["Year"].max())

try:
    area_dates = load_area_dates()
except (OSError, ValueError, json.JSONDecodeError) as exc:
    st.error(f"Cannot read saved area dates: {exc}. Fix or back up area_dates.json before continuing.")
    st.stop()

# A single assigned date is shared by all papers in the same area and publication year.
# This is NOT an independently verified publication date for each paper.
cloud_dates = is_cloud_storage()

if cloud_dates:
    if "date_editor_authenticated" not in st.session_state:
        st.session_state.date_editor_authenticated = False

    if not st.session_state.date_editor_authenticated:
        with st.expander("Date editor login"):
            with st.form("date_editor_login"):
                password = st.text_input(
                    "Owner password", type="password"
                )
                submitted = st.form_submit_button("Unlock editing")

                if submitted:
                    expected = st.secrets["OWNER_PASSWORD"]

                    if hmac.compare_digest(password, expected):
                        st.session_state.date_editor_authenticated = True
                        st.rerun()
                    else:
                        st.error("Incorrect password.")

    else:
        if st.button("Lock date editor"):
            st.session_state.date_editor_authenticated = False
            st.rerun()

can_edit_dates = (
    not cloud_dates
    or st.session_state.get("date_editor_authenticated", False)
)
with st.expander("Manage area/year dates (saved permanently)", expanded=not bool(area_dates)):
    st.caption(
        "Enter a YYYY-MM-DD date for each area and year (for example, ndss / 2026). "
        "Dates apply to every paper with that exact area and year. "
        "Save them to area_dates.json. Without an assigned date, papers use publication-year filtering."
    )
    available_years = sorted(articles["Year"].unique().tolist(), reverse=True)
    editing_year = st.selectbox("Year to edit", available_years, key="area_date_edit_year")
    combos = (
        articles.loc[articles["Year"] == editing_year]
        .groupby("Area", dropna=False)
        .size()
        .rename("Papers")
        .reset_index()
        .sort_values("Area")
        .reset_index(drop=True)
    )
    combos["Date (YYYY-MM-DD)"] = [
        area_dates.get(area_year_key(editing_year, str(area)), "")
        for area in combos["Area"]
    ]
    editor = st.data_editor(
        combos[["Area", "Papers", "Date (YYYY-MM-DD)"]],
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        disabled= (
            ["Area", "Papers"]
            if can_edit_dates
            else ["Area", "Papers", "Date (YYYY-MM-DD)"]),
        column_config={
            "Date (YYYY-MM-DD)": st.column_config.TextColumn(
                "Date (YYYY-MM-DD)",
                help="Use YYYY-MM-DD (e.g. 2026-05-05). Empty = unknown."
            ),
            "Papers": st.column_config.NumberColumn("Author–paper records"),
        },
        key=f"area_date_editor_{editing_year}",
    )
    if can_edit_dates and st.button("Save dates for this year", key="save_area_dates"):
        updated = area_dates.copy()
        invalid = []
        for row in editor.itertuples(index=False, name=None):
            area, _paper_count, raw_value = row
            value = "" if pd.isna(raw_value) else str(raw_value).strip()
            key = area_year_key(editing_year, str(area))
            if not value:
                updated.pop(key, None)
                continue
            try:
                parsed = date.fromisoformat(value)
                if parsed.year != editing_year or parsed.isoformat() != value:
                    raise ValueError("Date must be YYYY-MM-DD in the selected year")
            except ValueError:
                invalid.append(f"{area}: {value}")
                continue
            updated[key] = value
        if invalid:
            st.error("Dates must be valid YYYY-MM-DD values in the selected year: " + "; ".join(invalid))
        else:
            try:
                save_area_dates(updated, editing_year=editing_year)
            except Exception as exc:
                st.error(f"Could not save dates: {exc}")
            else:
                st.success("Dates saved successfully.")
                st.rerun()
    st.download_button(
        "Back up saved dates (JSON)",
        data=json.dumps(area_dates, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name="area_dates_backup.json", mime="application/json",
    )

# Map the user-assigned area/year dates onto every paper.
keys = [area_year_key(int(y), str(a)) for y, a in zip(articles["Year"], articles["Area"])]
articles["Assigned date"] = pd.to_datetime(
    [area_dates.get(key) for key in keys], errors="coerce"
)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "Start date (inclusive)",
        value=date(max(min_year, max_year - 5), 1, 1),
        min_value=date(min_year, 1, 1),
        max_value=date(max_year, 12, 31),
    )
with col2:
    end_date = st.date_input(
        "End date (inclusive)",
        value=date(max_year, 12, 31),
        min_value=date(min_year, 1, 1),
        max_value=date(max_year, 12, 31),
    )

if start_date > end_date:
    st.error("Start date must be on or before end date.")
    st.stop()

start_year, end_year = start_date.year, end_date.year
st.info(
    f"Filtering from **{start_date.isoformat()} through {end_date.isoformat()}** (inclusive). "
    "Papers with saved area/year dates use exact-date filtering; other papers use publication-year filtering."
)

# The roster includes every FIU-tagged author in the snapshot, even if they
# have no papers in the currently selected year range.
roster = articles["Professor"].drop_duplicates().sort_values().tolist()
chosen_professors = st.multiselect(
    "Filter professors (optional)",
    options=roster,
    default=[],
    placeholder="Select professors to compare...",
    help="Leave empty to show all professors. Choose multiple names to compare a subset.",
)
active_roster = chosen_professors if chosen_professors else roster

# Saved date takes priority. Missing dates preserve the original year-only behavior.
assigned = articles["Assigned date"]
within_range = (
    (assigned.notna() & assigned.between(pd.Timestamp(start_date), pd.Timestamp(end_date)))
    | (assigned.isna() & articles["Year"].between(start_year, end_year))
)
selected = articles.loc[
    within_range & articles["Professor"].isin(active_roster)
].copy()
selected["Assigned date"] = selected["Assigned date"].dt.strftime("%Y-%m-%d")
counts = selected.groupby("Professor").size()
summary = pd.DataFrame({
    "Professor": active_roster,
    "Paper count": [int(counts.get(person, 0)) for person in active_roster],
}).sort_values(["Paper count", "Professor"], ascending=[False, True], ignore_index=True)

m1, m2, m3 = st.columns(3)
m1.metric("Professors shown", len(active_roster))
m2.metric("Professors with papers in range", int((summary["Paper count"] > 0).sum()))
m3.metric("Professor–paper records", len(selected))

st.subheader("Professor publication counts")
st.dataframe(summary, use_container_width=True, hide_index=True)
st.download_button(
    "Download professor counts (CSV)",
    data=summary.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"fiu_counts_{start_year}_{end_year}.csv",
    mime="text/csv",
)

st.subheader("Papers for selected professors")
if selected.empty:
    st.write("No qualifying papers in the selected date range.")
else:
    st.dataframe(
        selected[["Professor", "Year", "Title", "Area", "Number of authors", "Assigned date", "Page count"]]
        .sort_values(["Professor", "Year", "Title"], ascending=[True, False, True]),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download selected professors' papers (CSV)",
        data=selected[["Professor", "Year", "Title", "Area", "Number of authors", "Assigned date", "Page count"]]
        .sort_values(["Professor", "Year", "Title"], ascending=[True, False, True])
        .to_csv(index=False).encode("utf-8-sig"),
        file_name=f"fiu_selected_professors_papers_{start_year}_{end_year}.csv",
        mime="text/csv",
    )

st.subheader("Individual professor details")
professor = st.selectbox("Choose a professor", summary["Professor"].tolist())
professor_papers = (
    selected.loc[selected["Professor"] == professor]
    .sort_values(["Year", "Title"], ascending=[False, True])
    .reset_index(drop=True)
)
st.write(f"**{professor} — {len(professor_papers)} qualifying paper records**")
if professor_papers.empty:
    st.write("No qualifying papers in the selected date range.")
else:
    st.dataframe(
        professor_papers[["Year", "Title", "Area", "Number of authors", "Assigned date", "Page count"]],
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download this professor's papers (CSV)",
        data=professor_papers[["Year", "Title", "Area", "Number of authors", "Assigned date", "Page count"]].to_csv(index=False).encode("utf-8-sig"),
        file_name=f"fiu_professor_papers_{start_year}_{end_year}.csv",
        mime="text/csv",
    )

st.divider()
# Nested output with all filtered roster members, including zero-paper professors.
papers_by_professor = {
    name: group[["Year", "Title", "Area", "Number of authors", "Assigned date", "Page count"]]
    .rename(columns={"Year": "year", "Title": "title", "Area": "area", "Number of authors": "numauthors","Assigned date": "assignedDate", "Page count": "pageCount"})
    .to_dict(orient="records")
    for name, group in selected.groupby("Professor")
}
export = [
    {"professor": row["Professor"], "count": int(row["Paper count"]),
     "papers": papers_by_professor.get(row["Professor"], [])}
    for row in summary.to_dict(orient="records")
]
st.download_button(
    "Download professor counts + paper lists (JSON)",
    data=json.dumps(export, ensure_ascii=False, indent=2).encode("utf-8"),
    file_name=f"fiu_publications_{start_year}_{end_year}.json",
    mime="application/json",
)

st.caption(
    "Faculty membership and paper eligibility come from this CSRankings snapshot. "
    "Authors not represented by FIU-tagged records in the snapshot cannot be listed; "
    "this is not a verified current FIU faculty roster. Multiple FIU authors on one "
    "paper each receive their own author-publication record."
)
