import os
import shutil
from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import openpyxl
import asyncio
from main import planning_agent, blueprint_search_agent, data_analyst_agent, remediation_agent, model_client, termination, selector_prompt, selector_func
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from datetime import datetime

templates = Jinja2Templates(directory="templates")
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
def upload(request: Request, file: UploadFile = File(...)):
    # Save uploaded file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Extract criteria from column O
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    criteria = []
    count = 0
    for row in ws.iter_rows(min_row=2):
        if count > 5:
            break
        count += 1
        val = row[14].value
        if val and str(val).strip():
            criteria.append(str(val).strip())
    # Run team for each criterion
    results = asyncio.run(run_team(criteria))
    # Write HTML report
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(UPLOAD_DIR, f"output_guideline_results_{now_str}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(render_html_report(results))
    return templates.TemplateResponse("results.html", {"request": request, "results": results, "report_path": output_path})

def render_html_report(results):
    # html = '''<html><head><title>Guideline Results</title><style>body {font-family: 'Segoe UI', Arial, sans-serif; background: #f8f9fa; margin: 0; padding: 2em;} h1 {color: #2c3e50; margin-bottom: 1em;} ul {list-style: none; padding: 0;} li {background: #fff; margin-bottom: 1em; padding: 1em; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.07);} strong {color: #2980b9; font-size: 1.1em;} .summary {display: block; margin-top: 0.5em; color: #444; white-space: pre-line;}</style></head><body><h1>Guideline Results</h1><ul>'''
    # for line in results:
    #     green = "GREEN" in line
    #     guideline, summary = line.split(":", 1) if ":" in line else (line, "")
    # html += "</ul></body></html>"
    # return html
        import markdown2
        html = '''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Guideline Results</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(120deg, #f8f9fa 0%, #e3e6ea 100%);
                margin: 0;
                padding: 2em;
            }
            h1 {
                color: #1a2636;
                margin-bottom: 2em;
                font-weight: 600;
                font-size: 2.2em;
            }
            ul {
                list-style: none;
                padding: 0;
                max-width: 900px;
                margin: 0 auto;
            }
            li {
                background: #fff;
                margin-bottom: 2em;
                padding: 2em 2em 1em 2em;
                border-radius: 16px;
                box-shadow: 0 4px 24px rgba(30,40,60,0.08);
                border-left: 8px solid #4fd18b;
                transition: box-shadow 0.2s;
            }
            li.red {
                border-left: 8px solid #e74c3c;
            }
            .guideline {
                color: #2980b9;
                font-size: 1.2em;
                font-weight: 600;
                margin-bottom: 1em;
                display: block;
            }
            .summary {
                margin-top: 0.5em;
                color: #222;
                font-size: 1em;
            }
            @media (max-width: 600px) {
                body { padding: 0.5em; }
                ul { padding: 0; }
                li { padding: 1em; }
            }
            pre, code {
                background: #f4f6fa;
                border-radius: 6px;
                padding: 0.2em 0.5em;
                font-size: 0.95em;
            }
            blockquote {
                border-left: 4px solid #4fd18b;
                margin: 1em 0;
                padding-left: 1em;
                color: #555;
                background: #f8f9fa;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }
            th, td {
                border: 1px solid #e3e6ea;
                padding: 0.5em 1em;
            }
            th {
                background: #f4f6fa;
            }
        </style>
    </head>
    <body>
        <h1>Guideline Results</h1>
        <ul>
    '''
        for line in results:
            green = "GREEN" in line
            guideline, summary = line.split(":", 1) if ":" in line else (line, "")
            summary_html = markdown2.markdown(summary.strip())
            li_class = "" if green else "red"
            html += f'<li class="{li_class}"><span class="guideline">{guideline.strip()}</span><div class="summary">{summary_html}</div></li>'
        html += "</ul></body></html>"
        return html

async def run_team(criteria):
    results = []
    for guideline_description in criteria:
        task = f"As part of an Australian Government IRAP assessment, review the provided Powershell scripts and determine if they satisfy the following compliance criterion from the ASD System Security Plan annex:\n---\n{guideline_description}\n---\n"
        team = SelectorGroupChat(
            [planning_agent, blueprint_search_agent, data_analyst_agent, remediation_agent],
            model_client=model_client,
            termination_condition=termination,
            selector_prompt=selector_prompt,
            selector_func=selector_func,
            allow_repeated_speaker=True,
            max_turns=7,
        )
        result = await Console(team.run_stream(task=task))
        #team.reset()
        if hasattr(result, "messages") and result.messages:
            final_message = result.messages[-2].content
            final_message += "\n\n" + result.messages[-1].content
            results.append(f"{guideline_description}: {final_message}")
        else:
            results.append(f"{guideline_description}: [No summary found]")
    return results

@app.get("/report/{filename}")
def get_report(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    return FileResponse(file_path, media_type="text/html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
