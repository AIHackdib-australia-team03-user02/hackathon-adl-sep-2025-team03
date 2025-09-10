# README (Short Guide) — updated

## Getting started (TL;DR)
**Prereqs:** Python 3.12 (or 3.11), Git. Avoid 3.13 for now.

```powershell
# 1) Create and activate a venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install deps
python -m pip install --upgrade pip
pip install autogen-agentchat openpyxl python-dotenv markdown

# 3) Secrets – create .env next to main.py
#    (Do NOT commit this file)
```

**`.env` template**
```ini
# Use Azure OpenAI (preferred)
AZURE_OPENAI_API_KEY=<your key>
AZURE_OPENAI_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>   # e.g., gpt-4o-mini or gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Or fallback to OpenAI (if you don’t set Azure env vars)
OPENAI_API_KEY=<your openai key>
```

---

## Input/Output locations (current)
We run directly against your **standards** and **systems** folders (no zips needed).

```
.\standards\
  Information security manual (March 2025).pdf
  static\content\files\configscripts\  # ASD/blueprint sample configs/scripts
  static\content\files\text\           # text-based evidence/notes
  ... (any other guidance folders you keep here)

.\systems\
  test-system\                          # YOUR test evidence (folder, not zip)
    static\content\files\configscripts\
    static\content\files\text\
  SSP_filled_YYYYMMDD-HHMMSS.xlsx       # output written here (timestamped)
```

> Put the **System security plan annex template (March 2025).xlsx** in `.\standards\`.  
> We always save the **filled** workbook to `.\systems\SSP_filled_*.xlsx`.

---

## Run it
```powershell
python .\main.py
```

- To **limit** the run to the first 5 rows (handy for testing), in `main.py` use:
  ```python
  res = supervisor.execute_tool(
      "run_ssp",
      ism_pdf=ism_pdf,
      ssp_xlsx_in=ssp_xlsx_in,
      ssp_xlsx_out=ssp_xlsx_out,
      gold_blueprint=gold_blueprint,
      test_system_path=test_system_path,
      max_rows=5,  # process only first 5 lines
  )
  ```
- To process **all rows**, remove `max_rows` (or set `None`).

---

## What this repo does (now)
1) **Loads LLM config** from `.env` (Azure OpenAI first, OpenAI fallback; offline stubs if neither).
2) **Reads SSP Excel** (March 2025 sheet):  
   - **Column D** = *Identifier* (e.g., `ISM-1955`)  
   - **Column O** = *Description* (used as keywords)  
   - **Column I** = *Applicability to P (Protected)* → drives whether we evaluate.
3) **Supervisor → run_ssp**: for each P-relevant row, it:
   - Finds **test evidence** in `.\systems\test-system\...` (folders, not zips).
   - Decides **Implementation Status (Q)** from **test evidence only**.
   - Chooses the **Responsible Entity (P)** via a selector agent.
   - Writes **Implementation Comments (R)** based on the decision policy (below).
4) **Writes results** back to the same SSP sheet (only columns P/Q/R).  
   Output is saved as `.\systems\SSP_filled_YYYYMMDD-HHMMSS.xlsx`.

---

## Architecture & routing (brief)
- **SupervisorAgent** (orchestrator)
  - Tool: `run_ssp(ism_pdf, ssp_xlsx_in, ssp_xlsx_out, gold_blueprint, test_system_path, max_rows)`
  - Reads SSP rows, calls evidence discovery/validation, and writes results.
- **Selector Agent** (lightweight)
  - Given `Identifier + Description`, chooses the **owner**:
    - `Policy Owner`, `Platform/Ops`, `SecOps`, `Security Architecture`, `Network Ops`.
  - The selector’s text **does not** affect Q/R; it only sets **P (owner)**.
- **Tech “group chat” tool** (stubbed for now)
  - Bundles Hardening/Monitoring/Crypto/Network agents for future multi-agent workflows.
  - Today, evidence decides status; the group is ready for deeper, iterative checks later.

**Decision of Q/R is evidence-first and test-only.** Gold (blueprint) is used for internal hints only and does **not** change outcomes.

---

## Evidence discovery & validation (important)
- The scanner prefers **real config files over markdown**.  
  Extension priority: configs/scripts (`.ps1/.json/.yaml/.ini/.cfg/...`) » text (`.txt`) » docs (`.md`).
- Preferred search paths (if present) are scanned first:
  - `static/content/files/configscripts/`
  - `static/content/files/text/`
  - `config/`, `configs/`, `policies/`
- We rank candidates using filename/content keyword hits (from **Control ID** and **Description**) and the extension priority above.

### Control-specific rules (example)
- **ISM-1955** (Password age must be ≤ 30 days):  
  The validator extracts **MaximumPasswordAge** from config/text (e.g., `.ps1`, `.txt`, `.md`) and returns:
  - **Comply** if value ≤ 30 (Column Q = `Comply`)  
  - **Gap** if value > 30 (Column Q = `Gap`)  
  - If no numeric value is found in test evidence, we treat it as **Gap** (needs explicit evidence).

> Example: If your test file contains  
> `New-ItemProperty … -Name MaximumPasswordAge -Value 50 ...`  
> you’ll get **Q = Gap**, **R =** `Password age 50 days > 30 (file: MaximumPasswordAge.txt) Set MaximumPasswordAge ≤ 30 days and rotate any compromised/suspected credentials.`

---

## What we write to the SSP (columns)
For every processed row:

- If **Column I ≠ “Yes”** →  
  **Q:** `N/A (not P)`  
  **R:** `Not applicable to Protected per Column I.`

- If **Column I = “Yes”** →  
  **Q** is decided from **test evidence only**:
  - **Comply** → we put **what we found** (e.g., extracted value + filename) in **R**.
  - **Gap** (or **Fail**, if you later add that category) → we include a short **remediation** in **R**.  
    (For ISM-1955: “Set MaximumPasswordAge ≤ 30 days …”)
  - **No evidence** → **Q = Gap**, **R left blank** (so it’s obvious what’s missing).

> Only P/Q/R are updated. We **do not** create extra debug columns.

---

## Testing quickly
- Put a config file under:  
  `.\systems\test-system\static\content\files\text\MaximumPasswordAge.txt`
- Set a value to force non-compliance:
  ```
  New-ItemProperty -Path HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters `
    -Name MaximumPasswordAge -Value 50 -PropertyType DWORD -Force
  ```
- `python .\main.py` → check the first P-relevant row in the timestamped output under `.\systems\`.

---

## Troubleshooting (quick)
- **`ModuleNotFoundError: No module named 'autogen'`**  
  You’re missing the package. Install into your active venv:
  ```powershell
  pip install autogen-agentchat
  ```
  Make sure VS Code uses the same interpreter (Command Palette → *Python: Select Interpreter* → pick `.venv`).

- **Permission denied opening the SSP Excel**  
  Excel/OneDrive lock the file. We read via a **temp copy** and always **write a new timestamped file**. Close the workbook while running.

- **“Comply” referencing a generic file (e.g., DisablePasswordChange.txt)**  
  We now force **Gap** when a validator exists but can’t find a numeric value (e.g., ISM-1955). If you still see this, ensure your test file lives under `.\systems\test-system\...` and contains `MaximumPasswordAge`.

- **Paths wrong / scanner finds nothing**  
  Flip your `test_system_path` to a **folder** (not a zip) and make sure the file extensions are among:  
  `.ps1 .psm1 .bat .cmd .sh .reg .json .yaml .yml .ini .cfg .conf .xml .toml .txt .md`.

- **Caches**  
  After code changes:  
  ```powershell
  Remove-Item -Recurse -Force .\utils\__pycache__\
  Remove-Item -Recurse -Force .\agents\__pycache__\
  ```

---

## Repository layout (reference)
```
autogen-irap-starter/
  agents/
    supervisor.py          # run_ssp: orchestrates reading SSP and writing P/Q/R
    policy.py, hardening.py, monitoring.py, crypto.py, network.py, docgen.py
  systems/
    test-system/           # your test evidence (folders/files)
    SSP_filled_*.xlsx      # outputs (timestamped)
  standards/
    Information security manual (March 2025).pdf
    System security plan annex template (March 2025).xlsx
    static/content/files/configscripts/
    static/content/files/text/
  utils/
    blueprint_io.py        # evidence discovery + validators (config > markdown)
    ssp_excel.py           # Excel read/write helpers (forced columns D/I/O)
    ...                    # other utils
  main.py
  .env
  requirements.txt (optional if you prefer one file)
```

---

## Contributing / Git (quick flow)
```powershell
git switch -c dev/<yourname>/<short-topic>
git add -A
git commit -m "feat: evidence-first SSP fill; config>markdown; selector owner"
git push -u origin dev/<yourname>/<short-topic>
```

> Keep secrets out of Git. Use `.gitignore` to exclude `.env` and `.venv/`.

---

## Roadmap (next steps)
- Add more **control-specific validators** (e.g., crypto/network/monitoring controls).
- Expand the group-chat loop for **multi-agent** technical checks.
- Optional “**Fail**” severity for egregious misconfigs (e.g., value over 90 days).
- Export a **control-by-control** Markdown/HTML report alongside the SSP fill.
