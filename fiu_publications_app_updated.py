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

INSTITUTION = "Florida International University"
DEFAULT_PATH = Path(__file__).resolve().parent / "articles.json"

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
            "Venue": item.get("conf", ""),
            "Area": item.get("area", ""),
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
        st.warning(
            "No local CSRankings checkout found. Set CSRANKINGS_REPO to its path "
            "on the computer running Streamlit. Updates are unavailable until it is configured."
        )
    else:
        st.caption(f"Data source: {repo}")
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

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "Start date (year is used)",
        value=date(max(min_year, max_year - 5), 1, 1),
        min_value=date(min_year, 1, 1),
        max_value=date(max_year, 12, 31),
    )
with col2:
    end_date = st.date_input(
        "End date (year is used)",
        value=date(max_year, 12, 31),
        min_value=date(min_year, 1, 1),
        max_value=date(max_year, 12, 31),
    )

if start_date > end_date:
    st.error("Start date must be on or before end date.")
    st.stop()

start_year, end_year = start_date.year, end_date.year
st.info(
    f"Including full publication years **{start_year}–{end_year}**. "
    "Months and days are not used because the source only supplies a publication year."
)

selected = articles.loc[articles["Year"].between(start_year, end_year)].copy()

# Snapshot roster is all professors listed with FIU as institution ANYWHERE
# in the input file. This is not an independently verified current FIU roster.
roster = articles["Professor"].drop_duplicates().sort_values().tolist()
counts = selected.groupby("Professor").size()
summary = pd.DataFrame({
    "Professor": roster,
    "Paper count": [int(counts.get(person, 0)) for person in roster],
}).sort_values(["Paper count", "Professor"], ascending=[False, True], ignore_index=True)

m1, m2, m3 = st.columns(3)
m1.metric("Professors in snapshot", len(roster))
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

st.subheader("Papers by professor")
professor = st.selectbox("Choose a professor", summary["Professor"].tolist())
professor_papers = (
    selected.loc[selected["Professor"] == professor]
    .sort_values(["Year", "Title"], ascending=[False, True])
    .reset_index(drop=True)
)
st.write(f"**{professor} — {len(professor_papers)} qualifying paper records**")
if professor_papers.empty:
    st.write("No qualifying papers in the selected years.")
else:
    st.dataframe(
        professor_papers[["Year", "Title", "Venue", "Area", "Page count"]],
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download this professor's papers (CSV)",
        data=professor_papers.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"fiu_professor_papers_{start_year}_{end_year}.csv",
        mime="text/csv",
    )

st.divider()
st.download_button(
    "Download all matching paper records (CSV)",
    data=selected.sort_values(["Professor", "Year"], ascending=[True, False])
    .to_csv(index=False).encode("utf-8-sig"),
    file_name=f"fiu_all_papers_{start_year}_{end_year}.csv",
    mime="text/csv",
)

# Nested output with ALL roster members including zero-paper professors.
papers_by_professor = {
    name: group[["Year", "Title", "Venue", "Area", "Page count"]]
    .rename(columns={"Year": "year", "Title": "title", "Venue": "venue", "Area": "area", "Page count": "pageCount"})
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
