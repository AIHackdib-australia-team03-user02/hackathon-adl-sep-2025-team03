# hackathon-adl-sep-2025-team03
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
.env template:
API_KEY=your_api_key_here
AZURE_ENDPOINT=your_endpoint_here
AZURE_DEPLOYMENT=your_deployment_here
```


Running docker:
```
> docker build -t hackathon-adl-sep-2025-team03 . 
> docker run --rm -it hackathon-adl-sep-2025-team03
```

See it live at https://remediationapp-team3.azurewebsites.net/ !
