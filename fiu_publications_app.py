"""Explore a local CSRankings articles.json snapshot for FIU-affiliated authors.

Run: streamlit run fiu_publications_app.py
"""

from __future__ import annotations

import json
from datetime import date
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


st.title("FIU CSRankings publication explorer")
st.caption("Based on your local CSRankings articles.json snapshot — not live DBLP data.")

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
