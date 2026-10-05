# FIU CSRankings Publication Tracker

A Streamlit application for exploring CSRankings-eligible publications associated with Florida International University (FIU) faculty.

The app uses a locally generated `articles.json` snapshot from the CSRankings data-processing pipeline and allows users to filter publications by year, view publication counts by professor, inspect the papers behind each count, and export results.

## Features

- Filter FIU publication records by start and end date
- Count qualifying publications for each FIU-affiliated professor
- View the individual papers behind each professor's count
- Display publication year, title, venue, research area, and page count
- Export professor counts as CSV
- Export paper-level results as CSV
- Export professor counts and paper lists as JSON
- Uses CSRankings-generated publication data rather than querying DBLP on every search

## Project Structure

```text
FIU_Publications_MVP/
├── fiu_publications_app.py
├── articles.json
├── requirements.txt
└── README.md
```

`articles.json` is generated from the CSRankings processing pipeline and is required to run the current version of the app.

## Requirements

- Python 3
- Streamlit
- pandas

If you are also regenerating CSRankings publication data locally, additional dependencies may be required:

- lxml
- xmltodict
- requests

Example `requirements.txt`:

```txt
streamlit
pandas
lxml
xmltodict
requests
```

## Running the Application

Clone this repository:

```bash
git clone https://github.com/YOUR_USERNAME/FIU_Publications_MVP.git
cd FIU_Publications_MVP
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Make sure `articles.json` is in the same directory as `fiu_publications_app.py`.

Run the application:

```bash
python3 -m streamlit run fiu_publications_app.py
```

Streamlit will normally open the application at:

```text
http://localhost:8501
```

## How the Data Works

The application does not parse the full DBLP XML dataset every time a user performs a search.

Instead, CSRankings processes DBLP publication data first and generates an `articles.json` file containing publication-level records.

The app then:

```text
articles.json
    ↓
Keep records associated with Florida International University
    ↓
Filter records by the selected publication years
    ↓
Group records by professor
    ↓
Calculate publication counts
    ↓
Display the individual papers behind each count
```

The current date inputs are interpreted at the **year level**. Months and days are not used because the CSRankings source records used by the app provide publication years rather than reliable exact publication dates.

## Generating a Fresh `articles.json` (Function of "Update Publication Data" Button)

If you have a local clone of the CSRankings repository, publication data can be regenerated from the CSRankings pipeline.

Example:

```bash
git clone --branch gh-pages https://github.com/emeryberger/CSrankings.git
cd CSrankings
```

Then update and process the DBLP data:

```bash
make update-dblp PYTHON=python3
make generated-author-info.csv PYTHON=python3 PYPY=python3
```

After the processing completes, verify that `articles.json` exists:

```bash
ls -lh articles.json
```

Then copy the updated file into this project:

```bash
cp articles.json /path/to/FIU_Publications_MVP/
```

The Streamlit application will use the new snapshot the next time the data is loaded.

## Important Data Notes

- The app currently treats FIU affiliation according to the institution value stored in the CSRankings snapshot.
- It does not independently verify historical FIU employment dates.
- The faculty roster is derived from FIU-tagged records present in the snapshot, so a current FIU professor with no matching record in the snapshot may not appear.
- Publication counts are author-publication records from the processed CSRankings data.
- If multiple FIU professors coauthor the same paper, that paper can appear once under each professor.
- `articles.json` is a generated CSRankings data artifact. Review the applicable CSRankings and DBLP licensing terms before redistributing or publicly hosting generated datasets.

## Current MVP Scope

The current MVP focuses on:

- publication-year filtering
- professor-level publication counts
- paper-level inspection
- CSV and JSON export

Automatic scheduled data refreshes and hosted update workflows are outside the current MVP and can be added later.

## Data Sources

- [CSRankings](https://csrankings.org/)
- [CSRankings GitHub Repository](https://github.com/emeryberger/CSrankings)
- [DBLP](https://dblp.org/)

## Author

Khamidullokhon Abdurakhmonov
Computer Science, Florida International University
