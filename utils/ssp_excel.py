# utils/ssp_excel.py
import openpyxl, os, shutil, time
from datetime import datetime

EXPECTED_HEADERS = {
    "D": ["identifier", "control id", "id"],
    "O": ["description", "control description"],
    "P": ["responsible entity", "owner"],
    "Q": ["implementation status", "status"],
    "R": ["implementation comments", "comments", "rationale"],
}

def _normalize(s):
    return str(s or "").strip().lower()

def _pick_sheet(wb):
    # Prefer a sheet whose headers look like the Annex (D/O/P/Q/R)
    for ws in wb.worksheets:
        hdrs = {col: _normalize(ws[f"{col}1"].value) for col in ["D","O","P","Q","R"]}
        if (any(k in hdrs["D"] for k in EXPECTED_HEADERS["D"]) and
            any(k in hdrs["O"] for k in EXPECTED_HEADERS["O"]) and
            any(k in hdrs["P"] for k in EXPECTED_HEADERS["P"]) and
            any(k in hdrs["Q"] for k in EXPECTED_HEADERS["Q"]) and
            any(k in hdrs["R"] for k in EXPECTED_HEADERS["R"])):
            return ws
    return wb.active

def _safe_copy_for_read(path):
    """Copy the workbook to a temp sibling to avoid OneDrive/Excel locks."""
    base, ext = os.path.splitext(path)
    tmp = f"{base}.__tmpread__{int(time.time())}{ext}"
    try:
        shutil.copy2(path, tmp)
    except PermissionError:
        time.sleep(0.7)
        shutil.copy2(path, tmp)
    return tmp

def read_rows(path):
    """
    Open a temp copy for reading to avoid locks.
    Return (wb, ws, rows) where each row has:
      - row: Excel row index (int)
      - id_raw: raw string from Column D (no case transform)
      - id_upper: upper-cased identifier for matching
      - description: text from Column O
    """
    tmp = _safe_copy_for_read(path)
    try:
        wb = openpyxl.load_workbook(tmp, data_only=True)
    finally:
        try: os.remove(tmp)
        except Exception: pass

    ws = _pick_sheet(wb)
    rows = []
    for i, r in enumerate(ws.iter_rows(min_row=2), start=2):
        id_raw = str(r[3].value or "").strip()          # Column D
        desc   = str(r[14].value or "").strip()         # Column O
        rows.append({"row": i, "id_raw": id_raw, "id_upper": id_raw.upper(), "description": desc})
    return wb, ws, rows

def _timestamped_path(out_path):
    base, ext = os.path.splitext(out_path)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{base}_{ts}{ext}"

def safe_save(wb, out_path):
    """
    Save to a brand-new time-stamped file so we never collide with a locked file.
    Return the exact filename written.
    """
    target = _timestamped_path(out_path)
    wb.save(target)
    return target

def write_outcome_pqr(wb, ws, row_index: int, p_entity: str, q_status: str, r_comment: str):
    # P/Q/R are columns 16/17/18
    ws.cell(row=row_index, column=16, value=(p_entity or ""))   # P
    ws.cell(row=row_index, column=17, value=(q_status or ""))   # Q
    ws.cell(row=row_index, column=18, value=(r_comment or ""))  # R
