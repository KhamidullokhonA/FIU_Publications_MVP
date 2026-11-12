# FIU CSRankings Publication Tracker

A Streamlit application for exploring CSRankings-eligible publications associated with Florida International University (FIU) faculty.

The app uses a locally generated `articles.json` snapshot from the CSRankings data-processing pipeline and allows users to filter publications by date, view publication counts by professor, inspect the papers behind each count, and export results. By default, filtering uses publication years; users can optionally assign dates to specific research-area/year combinations, saved in `area_dates.json` for reuse.

## Live Demo

The FIU Publications MVP is deployed on Streamlit Community Cloud and can be accessed directly through your browser without any local installation.

🌐 **[Launch FIU Publications MVP](https://fiupublications.streamlit.app/)**

**Note:** The application may take a few moments to load after a period of inactivity due to Streamlit Community Cloud's resource management.

## Features

- Filter FIU publication records by start and end date (year-based by default)
- Optionally assign an exact date to each research-area/year combination to enable more precise filtering
- Save entered dates in `area_dates.json` so they persist across app restarts
- Count qualifying publications for each FIU-affiliated professor
- View the individual papers behind each professor's count
- Display publication year, title, research area, and page count
- Select one or more professors to compare, or leave the selection empty to see all professors
- Update the local publication snapshot using an existing CSRankings checkout
- Back up the manually assigned dates through the application
- Export professor counts as CSV
- Export paper-level results as CSV
- Export professor counts and paper lists as JSON
- Uses CSRankings-generated publication data rather than querying DBLP on every search

## Project Structure

```text
FIU_Publications_MVP/
├── fiu_publications_app.py
├── articles.json           # Generated CSRankings snapshot (Git LFS)
├── requirements.txt
├── README.md
├── area_dates.json       # Created after saving manual dates (local persistent mapping)
└── .venv/                # Optional local virtual environment (do not commit)
```

`articles.json` is generated from the CSRankings processing pipeline and is required to run the current version of the app. `area_dates.json` is a **separate** file next to the app script, created when manual dates are saved. Keep it when updating the snapshot or moving the project to another computer.

## Requirements

- Python 3 (with `venv` support)
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
## Getting Started

### 1. Get a local copy of CSRankings (for regenerating data)

If you plan to regenerate publication data, you need a local copy of the CSRankings repository. If you already have one, you can reuse it. Otherwise, clone the `gh-pages` branch with a shallow clone:

```bash
git clone --depth 1 --branch gh-pages https://github.com/emeryberger/CSrankings.git
```

This creates a separate `CSrankings` directory. The FIU tracker does **not** automatically generate a fresh `articles.json` merely because you cloned CSRankings; regenerating the snapshot requires running the CSRankings data-processing pipeline. For simply running the tracker using its existing snapshot, you can skip this step.

### 2. Install Git LFS (macOS and Windows)

The project's `articles.json` is approximately 150 MB and uses **Git Large File Storage (Git LFS)**. Install and initialize Git LFS before cloning so Git can download the actual file instead of leaving an LFS pointer.

#### macOS — Terminal

First, check whether Homebrew is already installed:

```bash
brew --version
```

If Terminal says `command not found: brew`, install Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the **Next steps** printed by the Homebrew installer to add `brew` to your shell's PATH, if instructed. Then run:

```bash
brew install git-lfs
git lfs install
git lfs version
```

#### Windows — PowerShell or Windows Terminal

Homebrew is not the standard Windows installer. Use **WinGet**, the Windows package manager, instead. First check whether it is available:

```powershell
winget --version
```

If WinGet is unavailable, install/update **App Installer** from the Microsoft Store, or see [Microsoft's WinGet documentation](https://learn.microsoft.com/en-us/windows/package-manager/winget/).

Install Git (if not already installed) and Git LFS:

```powershell
winget install --id Git.Git -e --source winget
winget install --id GitHub.GitLFS -e --source winget
```

Open a **new** PowerShell window after installation, then initialize and verify:

```powershell
git lfs install
git lfs version
```

**Alternative for either OS:** Download Git LFS from [git-lfs.com](https://git-lfs.com/) and follow its platform-specific installation instructions.

### 3. Clone the FIU Publication Tracker

```bash
git clone https://github.com/KhamidullokhonA/FIU_Publications_MVP.git
cd FIU_Publications_MVP
```

Git LFS should fetch `articles.json` automatically during a normal clone. To explicitly retrieve LFS files (or if you had already cloned the repository), run:

```bash
git lfs pull
```

Verify that the file is present and is the **actual JSON**, not a small LFS pointer:

```bash
git lfs ls-files
```

Check the file size using your operating system's terminal:

**macOS:**

```bash
ls -lh articles.json
```

**Windows PowerShell:**

```powershell
Get-Item articles.json | Select-Object Name, Length
```

`articles.json` should be roughly 150 MB. It must be in the same directory as `fiu_publications_app.py`.

### 4. Create and Activate a Virtual Environment

A Python virtual environment is **recommended**. It isolates this project's dependencies from other Python projects. Run these commands from inside `FIU_Publications_MVP`.

**macOS — Terminal:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows — PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, you can skip activation and call `.\.venv\Scripts\python.exe` directly in the commands below; changing the system-wide execution policy is not required.

When activated, the terminal prompt usually begins with `(.venv)`.

### 5. Install Python Dependencies

With the virtual environment activated, run the same command on macOS or Windows:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 6. Run the Application

With the virtual environment activated:

```bash
python -m streamlit run fiu_publications_app.py
```

Streamlit normally opens at `http://localhost:8501`.

When you finish, run `deactivate` to leave the virtual environment. On future sessions, reactivate the existing `.venv` rather than creating a new one. Do **not** commit `.venv` to Git; add `.venv/` to `.gitignore`.

## Manually Assigned Research Area Dates

The CSRankings snapshot provides publication years, but not necessarily exact calendar dates. In the app, open **Manage area/year dates (saved permanently)** to assign an exact date to an entire research-area/year combination.

1. Select a **Year to edit**.
2. Find the relevant **Area** in the table (for example, `ndss`).
3. Enter a date using `YYYY-MM-DD` (for example, `2026-05-05`). The date must be within the selected year.
4. Click **Save dates for this year**. The app writes the mapping to `area_dates.json` and reloads it.
5. To clear an assignment, empty its date field and save the year again. Use **Back up saved dates (JSON)** to download a backup.

The file is stored beside `fiu_publications_app.py` and uses keys of the form `YEAR|AREA`:

```json
{
  "2026|ndss": "2026-05-05"
}
```

**Important:** This is an *assigned area/year date*, not a verified date for each individual publication. All FIU author–paper records with `Year = 2026` and `Area = ndss` receive the same assigned date.

### Filtering rules

- **No assigned date:** A record is included whenever its publication **year** lies between the years of the selected start and end dates. Months and days are ignored for that record.
- **Assigned date:** A record is included only if the exact date falls between the selected start and end dates, **inclusive**.
- **Example:** With a filter of **April 5, 2025 – April 5, 2026**, an undated 2026 paper is included under the year-only rule, but a 2026 `ndss` paper assigned **May 5, 2026** is excluded.

Saved dates persist across app restarts and are independent of `articles.json`. They are stored on the **computer running Streamlit**, not automatically synchronized between different computers or users. Copy or back up `area_dates.json` when migrating the app. The application validates the date format and requires each assigned date's year to match its key; invalid entries are rejected.

## Updating Publication Data

The **Update publication data** expander offers a **Check and update publication data** button. It is enabled only if the app finds a local CSRankings repository containing both Git metadata and `util/regenerate_data.py`.

The app searches these locations in order:

1. `CSRANKINGS_REPO` environment variable (if configured)
2. `~/CSrankings`
3. `~/Documents/CSrankings`
4. A `CSrankings` folder beside the app's parent directory

If your checkout is somewhere else, set `CSRANKINGS_REPO` **before starting Streamlit**:

**macOS:**

```bash
export CSRANKINGS_REPO="$HOME/path/to/CSrankings"
python -m streamlit run fiu_publications_app.py
```

**Windows PowerShell:**

```powershell
$env:CSRANKINGS_REPO = "C:\path\to\CSrankings"
python -m streamlit run fiu_publications_app.py
```

When clicked, the update workflow:

1. Runs `git pull --ff-only` in the CSRankings checkout.
2. Requires the checkout to already contain `dblp.xml.xz`.
3. Runs `util/split-csv.py` and `util/regenerate_data.py` using the app's Python interpreter.
4. Validates that the generated `articles.json` contains FIU publication records.
5. Replaces the tracker's `articles.json` only after successful validation, preserving the existing snapshot on failure.

**Limitations:** This operation does **not** download a newer DBLP release; it regenerates using the DBLP snapshot already present in the checkout. The `git pull --ff-only` step fails if local tracked changes would be overwritten or if branches cannot be fast-forwarded. Resolve those changes in the CSRankings checkout before trying again. The update pipeline may require additional CSRankings dependencies beyond those required to run the tracker. The stored `area_dates.json` is not replaced by the snapshot update.

## Troubleshooting Git LFS

**`articles.json` is missing or very small:** From the tracker repository directory, try:

```bash
git lfs pull
git lfs checkout
```

Check the file size with `ls -lh articles.json` (macOS) or `Get-Item articles.json | Select-Object Name, Length` (Windows PowerShell).

**`Object does not exist on the server: [404]` or `Smudge error`:** This is not necessarily an installation problem. The repository may have an LFS pointer whose underlying object was not uploaded or is not accessible. Check:

```bash
git lfs logs last
git remote -v
git lfs ls-files
```

If the object is genuinely missing from remote LFS storage, `git lfs pull` and recloning won't fix it. A maintainer who still has the *full* `articles.json` and its LFS object locally needs to upload the missing object. From a repository with the object available, they can use `git lfs push origin --all` (which uploads locally available objects referenced by the repository's Git history). Otherwise the maintainer must restore the file from a backup and recommit/re-upload it properly.

**Avoid committing the 150 MB file as a regular Git file:** GitHub generally rejects regular files larger than 100 MB. Keep the file in Git LFS.

## How the Data Works

The application does not parse the full DBLP XML dataset every time a user performs a search.

Instead, CSRankings processes DBLP publication data first and generates an `articles.json` file containing publication-level records.

The app then:

```text
articles.json
    ↓
Keep records associated with Florida International University
    ↓
Apply year-based filtering, or assigned area/year dates where available
    ↓
Group records by professor
    ↓
Calculate publication counts
    ↓
Display the individual papers behind each count
```

Date filters use the **publication year by default**. The month and day affect matching only when an exact date has been manually saved for that area/year combination.


## Important Data Notes

- The app currently treats FIU affiliation according to the institution value stored in the CSRankings snapshot.
- It does not independently verify historical FIU employment dates.
- The faculty roster is derived from FIU-tagged records present in the snapshot, so a current FIU professor with no matching record in the snapshot may not appear.
- Publication counts are author-publication records from the processed CSRankings data.
- If multiple FIU professors coauthor the same paper, that paper can appear once under each professor.
- Manually assigned dates apply to entire area/year combinations, not individual papers; they should not be treated as independently verified publication dates.
- `articles.json` is a generated CSRankings data artifact. Review the applicable CSRankings and DBLP licensing terms before redistributing or publicly hosting generated datasets.

## Current MVP Scope

The current MVP focuses on:

- publication-year filtering with optional manually assigned area/year dates
- JSON persistence and backup of area/year date assignments
- optional professor comparison
- on-demand snapshot regeneration from a local CSRankings checkout
- professor-level publication counts
- paper-level inspection
- CSV and JSON export

An on-demand local data-regeneration workflow is included. Automatic scheduled updates, downloading new DBLP releases, and hosted multi-user synchronization are not implemented.

## Data Sources

- [CSRankings](https://csrankings.org/)
- [CSRankings GitHub Repository](https://github.com/emeryberger/CSrankings)
- [DBLP](https://dblp.org/)

## Author

Khamidullokhon Abdurakhmonov
Computer Science, Florida International University
