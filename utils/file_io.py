from pathlib import Path

TEXT_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".ps1", ".bicep", ".tf", ".csv", ".xml", ".cfg", ".ini"}

def load_local_texts(paths):
    results = []
    for p in paths or []:
        p = Path(p)
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in TEXT_EXT:
                    try:
                        results.append((str(f), f.read_text(encoding="utf-8", errors="ignore")))
                    except Exception as e:
                        results.append((str(f), f"<read_error: {e}>"))
        elif p.is_file() and p.suffix.lower() in TEXT_EXT:
            try:
                results.append((str(p), p.read_text(encoding="utf-8", errors="ignore")))
            except Exception as e:
                results.append((str(p), f"<read_error: {e}>"))
    return results
