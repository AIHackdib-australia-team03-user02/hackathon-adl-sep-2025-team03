# README (Short Guide)

## Getting started (TL;DR)
**Prereqs:** Python 3.12 (or 3.11), Git. Avoid 3.13 for now.

```powershell
# 1) Create and activate a venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate

# 2) Install deps
pip install -r requirements.txt

# 3) Secrets – create .env next to main.py
#    (Do NOT commit this file)
```

**`.env` template**
```ini
AZURE_OPENAI_API_KEY=<your key>
AZURE_OPENAI_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>   # e.g., gpt-5-chat
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

**Default input & output folders**
```
knowledge/policies/vYYYY-MM/standards/   # policy & standards (e.g., ASD Blueprint)
knowledge/policies/vYYYY-MM/mappings/    # control mappings (CSV/MD/TXT)
submissions/configs/                      # app configs/IaC/state to check
submissions/docs/                         # app evidence PDFs/notes
reports/                                  # generated results (timestamped + latest/)
```

**Run & view**
```powershell
python main.py
```
Open: `reports/latest/index.md` (Markdown) or, if you installed the optional `markdown` package, `reports/latest/index.html`.

---

## What this repo does (high level)
1) **Loads secrets** from `.env` and builds an Azure OpenAI client.
2) **Discovers inputs** from the default folders (latest `knowledge/policies/vYYYY-MM` and `submissions/*`).
3) **Supervisor** orchestrates domain agents (ingestion, policy, hardening, monitoring, crypto, network).
4) **DocGen** converts structured findings into three Markdown reports.
5) **Reports** are written to `reports/<timestamp>/` and mirrored to `reports/latest/`.

---

## Agents (what each one does)
- **IngestionAgent** – Walks the input directories, reads PDF/MD/TXT/JSON/YAML/etc., and produces concise summaries for downstream use.
- **PolicyAgent** – Interprets policy/guidance (e.g., ASD/ISM/IRAP docs, mappings) and calls out coverage vs gaps with short citations.
- **HardeningAgent** – Assesses OS/App/Auth/Virtualisation baselines against ISM controls and ASD hardening guidance.
- **MonitoringAgent** – Checks logging coverage, retention, and alert rules; can run KQL via a helper if configured.
- **CryptoAgent** – Evaluates TLS/SSH/IPsec/cipher posture against policy.
- **NetworkAgent** – Reviews segmentation, NSGs, firewall exposure and hygiene.
- **DocGenAgent** – Turns structured findings into auditor‑friendly Markdown sections.

---

## Orchestration model (Supervisor)
- **Current behaviour:** sequential, "call-everyone" pass (deterministic & easy to audit).
- **Decisioning:** by default the supervisor calls each core agent on every run. You can add routing rules later (e.g., skip K8s checks if no K8s files found).
- **Parallelism:** off by default (simpler logs). You can parallelise independent checks later for speed.

---

## Report outputs
After each run you’ll get:
```
reports/<YYYY-MM-DD_HHMM>/
  index.md                      # links to the three reports
  IRAP_Company_Policy.md        # narrative policy assessment
  Compliance_Report.md          # Comply / Partial / Gap view
  Remediation_Plan.md           # prioritised actions
reports/latest/                 # mirror of the latest run
```
> The `agents/docgen.py` writer splits the payload into three clean files and creates `index.md`. If the `markdown` package is installed, it also creates `index.html` for easy sharing.

---

## Packages (one‑liners)
- **pyautogen** – multi‑agent framework (agents, tools, orchestration).
- **openai** – Azure OpenAI v1 client (we set `base_url` to the deployment path and pass API version via `default_query`).
- **python‑dotenv** – loads `.env` secrets for endpoint/key/deployment/version.
- **GitPython** – (optional) clone & scan repos as inputs.
- **pypdf** – (optional) extract text from PDFs during ingestion.
- **rank‑bm25** – (optional) simple policy KB search/RAG starter.
- **markdown** – (optional) render a single‑file `index.html` from Markdown.
- **flaml** – indirect dependency; warning is safe to ignore unless you need AutoML.

---

## Repository layout (reference)
```
autogen-irap-starter/
  agents/
    docgen.py           # DocGenAgent + write_reports (splits files + index)
    supervisor.py       # Orchestrator (sequential by default)
    *.py                # other agents: ingestion, policy, hardening, monitoring, crypto, network
  knowledge/
    policies/
      v2025-09/
        standards/      # e.g., ASD Blueprint snapshot or submodule
        mappings/       # control mappings (CSV/MD/TXT)
  submissions/
    configs/            # app configs/IaC/state
    docs/               # app evidence PDFs/notes
  reports/
    latest/             # mirror of the most recent run
  utils/
    azure_cfg.py        # Azure OpenAI v1 config (deployment‑scoped base_url)
    *.py
  main.py               # entrypoint (no args needed; uses defaults above)
  requirements.txt
  .env.example          # (optional) non‑secret template for teammates
  .gitignore
```

---

## Policy knowledge base tips
- Put **policy/guidance** under `knowledge/policies/vYYYY-MM/standards/`.
  - Example (snapshot):
    ```powershell
    git clone --depth 1 https://github.com/ASD-Blueprint/ASD-Blueprint-for-Secure-Cloud.git \
      "knowledge\policies\v2025-09\standards\asd-blueprint"
    Remove-Item -Recurse -Force "knowledge\policies\v2025-09\standards\asd-blueprint\.git"
    ```
  - Example (submodule):
    ```powershell
    git submodule add https://github.com/ASD-Blueprint/ASD-Blueprint-for-Secure-Cloud.git \
      knowledge/policies/v2025-09/standards/asd-blueprint
    ```
- Keep **app inputs** separate (under `submissions/`) to avoid comparing policy‑to‑policy.

---

## Troubleshooting (quick)
- **`OpenAI.__init__() got an unexpected keyword argument 'api_version'`** → ensure `utils/azure_cfg.py` uses `base_url = <endpoint>/openai/deployments/<deployment>` and sets `default_query = {"api-version": <version>}` (do *not* pass `api_version` as a top‑level kwarg).
- **`model is None` / Pydantic validation error** → check `.env` has `AZURE_OPENAI_DEPLOYMENT` and `.env` is being loaded before config.
- **`import autogen` fails** → use Python 3.12/3.11 and install `pyautogen` (package name), not `autogen`.
- **PowerShell activate script not signed** → `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (one‑time).
- **No content in reports** → confirm files exist under the default input folders and that extensions are allowed in `main.py`.

---

## Contributing (dev branch flow)
```powershell
# Create a feature branch and push (don’t touch main)
git switch -c dev/ashley/report-split
git add -A
git commit -m "feat: split reports + nicer index"
# If no remote yet: git remote add origin <YOUR_REPO_URL>
git push -u origin dev/ashley/report-split
```

> Keep secrets out of Git: add `.env` and `.venv/` to `.gitignore`. Use `.env.example` for non‑secret templates.
