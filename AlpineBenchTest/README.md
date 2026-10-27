# Alpine Assembly Bench Test

Portable Python desktop wizard for J&J Alpine Assembly bench testing.

## Current scope

Implemented: job/serial/date identification; confirmed re-tests; preparation;
CDA 1, CDA 2, CDA 3; separate ER1 pre-calibration and decay screens; CV3;
Vac 1 and voltage walkup; timers; calculated acceptance results; zero confirmations;
failure stop/retry/yellow-tag; saved progress and resume; final review and notes.

Analytics export is implemented: one verified `.xlsx` workbook per job.
Five-page reports are not implemented yet. The original reference files are unchanged.

## Copy to a new computer

1. Copy `AlpineBenchTest` from the USB drive to a permanent, writable folder on
   the computer. Keep the application files and subfolders together.
2. Exclude `.venv` and `__pycache__` folders when transferring. The Python
   environment must be created on each computer, including when moving between
   Mac and Windows. Exclude demo job folders from `results/` unless needed.
3. Follow the setup steps for that computer below. Internet access is needed
   during installation; the application does not need internet during a test.
   A server destination does require access to the company network.

The application currently requires Python 3.10 or newer, Tk 8.6 or newer, and
openpyxl. Excel is useful for opening the output but is not needed to write it.
A standalone executable is not included yet.

## Windows: first-time setup

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/windows/).
   Include Tcl/Tk and the Python launcher (`py`) when available.
2. Open **Command Prompt** and change into the copied folder. Replace the example
   path with your actual folder:

   ```bat
   cd /d "C:\Users\YourName\Documents\AlpineBenchTest"
   ```

3. Create the local environment and install the required package:

   ```bat
   py -3 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   If `py` is unavailable, use `python -m venv .venv` after confirming
   `python --version` is 3.10 or newer.

4. Check Tk and the Excel-writing dependency:

   ```bat
   .venv\Scripts\python.exe -c "import tkinter, openpyxl; print('Tk:', tkinter.TkVersion, 'openpyxl:', openpyxl.__version__)"
   ```

   Tk must be 8.6 or newer. If Tcl/Tk is missing, modify or reinstall Python with
   that component before proceeding.
5. Set the results destination using the section below, then run a practice test.

## Windows: normal startup

Double-click `Launch-Windows.bat`. For desktop access, create a shortcut to that
file; keep the launcher itself inside `AlpineBenchTest`.

Alternatively, from Command Prompt in the application folder:

```bat
.venv\Scripts\python.exe -m app.main
```

Repeat setup only when configuring another computer or recreating its environment.

## Mac: first-time setup

1. Use Python 3.10 or newer with Tk 8.6 or newer. On the development Mac, Homebrew
   Python 3.14 is used. With Homebrew installed, its setup commands are:

   ```sh
   brew install python@3.14 python-tk@3.14
   ```

   Alternatively, install Python with Tcl/Tk support from
   [python.org](https://www.python.org/downloads/macos/).
   Do not use `/usr/bin/python3`; its deprecated Tk can produce a blank window.

2. Open **Terminal** and change into the copied folder. Replace the example path
   if your folder is elsewhere:

   ```sh
   cd "$HOME/Documents/BayAt/AlpineBenchTest"
   ```

3. Create the environment with your compatible Python. On the development Mac:

   ```sh
   /opt/homebrew/bin/python3.14 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

   On another Mac, use `python3 -m venv .venv` if `python3` selects the compatible
   installation. The `/opt/homebrew` path is specific to this development setup.

4. Check the dependencies and make the launcher executable:

   ```sh
   .venv/bin/python -c "import tkinter, openpyxl; print('Tk:', tkinter.TkVersion, 'openpyxl:', openpyxl.__version__)"
   chmod +x Launch-Mac.command
   ```

5. Set the results destination using the section below, then run a practice test.

The local environment is already configured on the development Mac; it does not
need to be recreated for normal startup.

## Mac: normal startup

Double-click `Launch-Mac.command`, or run this from Terminal in the application
folder:

```sh
./Launch-Mac.command
```

Alternatively:

```sh
.venv/bin/python -m app.main
```

Both platform launchers use the local `.venv` when present. No environment
activation is required.

## Check a new installation

1. Start a dummy job and unit, such as `SETUPTEST` and `TEST001`.
2. Check scrolling, the measurement timer, Save / Quit, and resuming the run.
3. Confirm `records.json` and `Analysis/SETUPTEST_analysis.xlsx` appear under the
   selected results destination. Open the workbook to inspect the entries, then
   close it before continuing tests.
4. Check saving and resuming on the actual server destination before bench use.

## Set the server destination

Edit **`config/settings.json` → `results_directory`**.
The development default `results` resolves relative to this application folder.
Use an absolute path to the server location when available. Windows UNC example:

```json
{"results_directory": "\\\\server\\share\\AlpineResults", "report_rows_per_file": 20}
```

On Mac, use the mounted share's path, such as `/Volumes/Share/AlpineResults`.
Only one tester may use the shared destination at a time. There is no concurrent
writer coordination. A JSON save failure is displayed and progression is rolled back.
An Excel export failure leaves JSON saved and displays a warning; retry export
after closing the workbook in Excel.
The configured report capacity is provisional until print-layout verification.

## Records and workflow

Each job has a `records.json` file. It contains unique run IDs, serials, selected
session dates, test numbers, timestamped measurement attempts, zero confirmations,
notes, and final decisions. Failed attempts are retained, even after a successful
retry. Retry repeats the failed stage within the same run. A confirmed new run
for a previously tested serial gets a new ID and a re-test note.

Progress is saved after each completed screen. An unfinished run must be resumed
and completed or yellow-tagged before another unit starts under that job.
Save / Quit preserves unsubmitted fields as a draft and asks whether to exit.
Choosing No leaves the current screen open. On resume, an interrupted decay
interval restarts; initial readings are restored, but final decay readings must
be taken again. Yellow-tag is available on every test screen and closes the run
as Fail, then asks whether to exit. Choosing No returns to identification.
Closing the window directly still discards unsubmitted fields.
Pausing after successful measurements retains the pending zero confirmation.

Each decay screen has one user-started 60-second measurement timer. Complete
fill and settling first, then start the timer and enter initial readings.
Initial fields remain editable throughout. Final fields and evaluation unlock
when the timer finishes. Record final measurements at that point; decay uses the
60-second measurement interval, not time spent typing or submitting the form.
Vacuum loss is movement
toward zero. Negative decay (pressure increasing or vacuum strengthening) is
flagged as failure requiring troubleshooting rather than silently passing.
ER1 CV5 initial and final readings must both be within 2.5–3.75 psi, inclusive.
Strict less-than decay limits and strict CV3 bounds follow the test reference.
Zero, airflow and stability checks are tester confirmations.

## Analytics workbook

Output: `results/<job>/Analysis/<job>_analysis.xlsx` (or the configured server root).
The `Test runs` worksheet has one row per run, including incomplete runs with a
blank final decision. Columns include identifiers, dates, status, decision,
notes, failure counts, stage attempt counts, latest submitted readings and results.
Unsubmitted drafts stay in JSON only. The latest attempt supplies each stage's
measurement columns; previous failed attempts remain in JSON and summary notes.
Decimals are stored as numbers, confirmations as booleans, dates as Excel dates,
and identifiers as text so leading zeros and long serials are preserved.
Pressure is in psi, QDM5/QDF22/QDF3 and Vac 2 readings are in mmHg; decay is per minute.
UTC timestamp columns are labeled explicitly.

Each save regenerates the workbook from JSON and verifies every cell by reopening
it before replacing the previous workbook. Dates have Excel millisecond precision;
numeric comparison allows relative rounding of 1e-15 from numeric serialization.
An export mismatch fails export and leaves the prior workbook intact. JSON is the
source of truth. Excel edits are overwritten on the next export: use a separate
copy for analysis, charts, and manual edits. Keep the live workbook closed while testing.

Regenerate all existing jobs on Mac:
```sh
.venv/bin/python -m app.outputs
```
Or one job: `.venv/bin/python -m app.outputs Demo00`.
Windows equivalent: `.venv\Scripts\python.exe -m app.outputs Demo00`.

Five-page reports and their rollover remain for a later phase.

## Bypass the timer for workflow testing

At the top of `app/wizard.py`, set
`LOCK_FINAL_READINGS_UNTIL_TIMER_FINISHES = False` and restart the application.
Final entry fields and evaluation are immediately available, including via Enter.
Calculations still assume a 60-second interval. The screen identifies the bypass,
and decay attempts record `timer_bypassed: true` in JSON.
Use a dummy job for this mode. Restore the toggle to `True` and restart before
actual bench testing. Its default is `True`.

## Verify logic

From this folder: `.venv/bin/python -m unittest discover -s tests -v`
(Windows: `.venv\Scripts\python.exe -m unittest discover -s tests -v`).
Platform launcher and full bench workflow checks are required on both Mac and
Windows before operational use.
