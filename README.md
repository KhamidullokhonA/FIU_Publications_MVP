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
├── articles.json       # Git LFS tracked
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

### 4. Install Python Dependencies

**macOS:**

```bash
python3 -m pip install -r requirements.txt
```

**Windows PowerShell:**

```powershell
py -m pip install -r requirements.txt
```

### 5. Run the Application

**macOS:**

```bash
python3 -m streamlit run fiu_publications_app.py
```

**Windows PowerShell:**

```powershell
py -m streamlit run fiu_publications_app.py
```

Streamlit normally opens at `http://localhost:8501`.

### Troubleshooting Git LFS

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
Filter records by the selected publication years
    ↓
Group records by professor
    ↓
Calculate publication counts
    ↓
Display the individual papers behind each count
```

The current date inputs are interpreted at the **year level**. Months and days are not used because the CSRankings source records used by the app provide publication years rather than reliable exact publication dates.


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
