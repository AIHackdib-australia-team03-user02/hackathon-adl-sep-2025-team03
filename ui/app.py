# ui/app.py
import io, os, sys, zipfile, shutil, subprocess, time, base64
from datetime import datetime
from pathlib import Path
import streamlit as st

# ---------- Bootstrap ----------
st.set_page_config(page_title="Defence ISM Compliance – AutoGen", layout="wide")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUNS_ROOT = (REPO_ROOT / "runs").absolute()
RUNS_ROOT.mkdir(exist_ok=True, parents=True)

ASSETS = REPO_ROOT / "ui" / "assets"
HERO = ASSETS / "hero.png"
LOGO = ASSETS / "logo.png"
RUN_GIF = ASSETS / "running.gif"   # optional fun animation

def _img_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

hero_b64 = _img_b64(HERO) if HERO.exists() else None
logo_b64 = _img_b64(LOGO) if LOGO.exists() else None
run_gif_b64 = _img_b64(RUN_GIF) if RUN_GIF.exists() else None

# ---------- Styles (taller header using reclaimed top space) ----------
# Header height knobs (tweak if you want even taller)
HEADER_MIN = 260   # px
HEADER_MAX = 360   # px

hero_bg = ""
if hero_b64:
    hero_bg = "background-image:linear-gradient(rgba(8,12,24,.45), rgba(8,12,24,.45)), url('data:image/png;base64," + hero_b64 + "');"

css_template = f"""
<style>
/* Reclaim Streamlit's top padding so the hero can use that space */
div.block-container {{ padding-top: .35rem; }}
section.main > div.block-container {{ padding-top: .35rem; }}

/* Taller hero header with background image */
.hero {{
  display:flex; align-items:flex-end; justify-content:space-between; gap:1rem;
  padding:1.4rem 1.6rem; border-radius:16px;
  border:1px solid rgba(255,255,255,.06);
  min-height: {HEADER_MIN}px;
  max-height: {HEADER_MAX}px;
  overflow: hidden;
  %HERO_BG%
  background-size: cover;
  background-position: center top;   /* show more of the image upper area */
}}
.hero h1 {{ margin:.1rem 0; font-size:2.1rem; line-height:1.15; text-shadow:0 2px 8px rgba(0,0,0,.35); }}
.hero p  {{ margin:.25rem 0 .6rem 0; opacity:.95; text-shadow:0 1px 4px rgba(0,0,0,.35); }}

.badges {{ display:flex; gap:.5rem; flex-wrap:wrap; }}
.badge {{
  font-size:.78rem; padding:.25rem .55rem; border-radius:999px;
  border:1px solid rgba(255,255,255,.18);
  background:rgba(0,0,0,.28);
  backdrop-filter: blur(4px);
}}
.badge.ok {{ border-color:rgba(16,185,129,.5); background:rgba(16,185,129,.18) }}

.logbox code {{ white-space:pre-wrap !important; }}
hr {{ border: none; border-top: 1px solid rgba(255,255,255,.1); margin: 1.0rem 0; }}

/* --- Fun "radar" animation (used if running.gif not present) --- */
.radar-wrap {{
  display:flex; gap:1rem; align-items:center;
  padding:.6rem .8rem; border-radius:12px;
  border:1px solid rgba(255,255,255,.12);
  background:rgba(0,0,0,.20);
  backdrop-filter: blur(6px);
  width: fit-content;
}}
.radar {{
  width: 120px; height: 120px; border-radius:50%;
  position: relative; overflow:hidden;
  background: radial-gradient(circle at center,
    rgba(80,200,180,.25) 0%, rgba(80,200,180,.10) 40%,
    rgba(0,0,0,.12) 41%, rgba(0,0,0,.20) 100%);
  box-shadow: inset 0 0 20px rgba(0,0,0,.5);
  border: 2px solid rgba(120,220,200,.8);
}}
.ring {{ position:absolute; border:1px solid rgba(120,220,200,.25); border-radius:50%; }}
.r1 {{ width:90px; height:90px; top:15px; left:15px; }}
.r2 {{ width:60px; height:60px; top:30px; left:30px; }}
.r3 {{ width:30px; height:30px; top:45px; left:45px; }}
.beam {{
  content:""; position:absolute; top:50%; left:50%; width:60px; height:2px;
  background: linear-gradient(90deg, rgba(120,220,200,1), rgba(120,220,200,0));
  transform-origin: left center;
  animation: sweep 2s linear infinite;
}}
@keyframes sweep {{
  from {{ transform: rotate(0deg);   }}
  to   {{ transform: rotate(360deg); }}
}}
.status-text {{ font-size:.95rem; opacity:.9 }}
</style>
"""
st.markdown(css_template.replace("%HERO_BG%", hero_bg), unsafe_allow_html=True)

# ---------- Header (no logo here to save vertical space) ----------
st.markdown("""
<div class="hero">
  <div class="left">
    <h1>Defence ISM Compliance Assistant</h1>
    <p>Multi-agent AutoGen • Azure OpenAI • Reproducible runs</p>
    <div class="badges">
      <span class="badge">Local & Docker</span>
      <span class="badge">ZIP & Folder</span>
      <span class="badge ok">Ready</span>
    </div>
  </div>
  <div class="right"></div>
</div>
""", unsafe_allow_html=True)

st.write("")

# ---------- Sidebar ----------
st.sidebar.header("Run Configuration")
input_mode = st.sidebar.radio("Input mode", ["Use existing folder path", "Upload .zip"], key="input_mode")
run_adapter = st.sidebar.selectbox("Execution mode", ["Subprocess (python -m main)", "Direct Python import"], key="exec_mode")

# Optional limiter: toggle + slider
limit_rows = st.sidebar.toggle("Limit rows?", value=False, key="limit_rows_toggle")
rows_to_process = None
if limit_rows:
    rows_to_process = st.sidebar.slider("Rows to process", min_value=1, max_value=1000, value=5, step=1, key="rows_slider")

extra_args = st.sidebar.text_input("Extra CLI args (subprocess)", value="", key="extra_cli")
st.sidebar.caption("Tip: switch to dark theme for projectors. Keep logs visible during the demo.")

# ---------- Tabs ----------
tab_run, tab_history, tab_settings, tab_about = st.tabs(["▶️ Run", "📜 History", "⚙️ Settings", "ℹ️ About"])

# Helper to show the fun running animation
def show_running_animation():
    if run_gif_b64:
        return st.markdown(
            f"<img src='data:image/gif;base64,{run_gif_b64}' height='120' alt='running'/>",
            unsafe_allow_html=True
        )
    else:
        return st.markdown("""
        <div class="radar-wrap">
          <div class="radar">
            <div class="ring r1"></div>
            <div class="ring r2"></div>
            <div class="ring r3"></div>
            <div class="beam"></div>
          </div>
          <div class="status-text">Scanning…</div>
        </div>
        """, unsafe_allow_html=True)

# ---------- Run tab ----------
with tab_run:
    st.subheader("Run Assessment")

    workdir = None
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    outdir = RUNS_ROOT / run_id

    if input_mode == "Use existing folder path":
        default_path = str(REPO_ROOT / "systems" / "test-system")
        folder = st.text_input("Absolute (or project-relative) folder", value=default_path, key="folder_path")
        if st.button("Validate folder", key="btn_validate_folder"):
            if folder and os.path.isdir(folder):
                st.success(f"Found folder: {os.path.abspath(folder)}")
            else:
                st.error("Path does not exist or is not a directory.")
        workdir = folder
    else:
        up = st.file_uploader("Upload blueprint .zip (contains the two folders)", type=["zip"], key="zip_upload")
        if up:
            outdir.mkdir(exist_ok=True, parents=True)
            unzip_dir = outdir / "unzipped"
            unzip_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(up.read())) as z:
                z.extractall(unzip_dir)
            st.success(f"Unzipped to: {unzip_dir}")
            workdir = str(unzip_dir)

    st.markdown("—")
    c1, c2 = st.columns([1, 3], vertical_alignment="center")
    with c1:
        clicked = st.button("Run assessment", type="primary", disabled=not workdir, key="btn_run")
    with c2:
        st.caption("Each run is saved under **/runs** with downloadable artifacts.")

    if clicked:
        if not workdir or not os.path.isdir(workdir):
            st.error("Invalid folder path.")
            st.stop()

        outdir.mkdir(exist_ok=True, parents=True)

        # status + logs + indeterminate progress
        status = st.empty()
        with status.container():
            st.write("**Status:**")
            anim_slot = st.empty()
            anim_slot.empty()
            show_running_animation()
        prog = st.progress(0)
        log_area = st.empty()

        try:
            if run_adapter.startswith("Subprocess"):
                cmd = [sys.executable, "-u", "-m", "main", "--input", workdir, "--out", str(outdir)]
                if rows_to_process is not None:
                    cmd += ["--max-rows", str(rows_to_process)]
                if extra_args.strip():
                    cmd += extra_args.split()

                st.write("Command:")
                st.code(" ".join(cmd))

                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"

                proc = subprocess.Popen(
                    cmd, cwd=str(REPO_ROOT), env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", bufsize=1,
                )

                i = 0
                lines = []
                for line in proc.stdout:
                    line = line.rstrip()
                    lines.append(line)
                    log_area.code(line)
                    i = (i + 3) % 101
                    prog.progress(i)
                rc = proc.wait()
                if rc != 0:
                    tail = "\n".join(lines[-80:])
                    prog.empty()
                    anim_slot.empty()
                    status.info("❌ Failed")
                    st.error(f"Process exited with {rc}\n\n{tail}")
                    st.stop()

            else:
                try:
                    import main as project_main
                except Exception as e:
                    prog.empty()
                    anim_slot.empty()
                    status.info("❌ Import failed")
                    st.exception(e)
                    st.stop()

                fn = getattr(project_main, "run_blueprint_assessment", None)
                if not callable(fn):
                    prog.empty()
                    anim_slot.empty()
                    status.info("⚠️ No callable")
                    st.warning("main.py lacks run_blueprint_assessment(workdir, outdir, max_rows). Use subprocess mode or add the wrapper.")
                    st.stop()

                i = 0
                for line in fn(workdir=workdir, outdir=str(outdir), max_rows=rows_to_process):
                    log_area.code(str(line))
                    i = (i + 3) % 101
                    prog.progress(i)
                    time.sleep(0.01)

            # completed
            prog.empty()
            anim_slot.empty()
            status.success("✅ Completed")

            zpath = RUNS_ROOT / f"{outdir.name}.zip"
            shutil.make_archive(str(zpath)[:-4], "zip", str(outdir))
            with open(zpath, "rb") as f:
                st.download_button("Download results (.zip)", f, file_name=zpath.name, key="btn_download_zip")

            st.success(f"Results saved to: {outdir}")
            try:
                st.toast("Run complete", icon="✅")
            except Exception:
                pass

        except Exception as e:
            prog.empty()
            anim_slot.empty()
            status.info("❌ Failed")
            st.exception(e)

# ---------- History tab ----------
with tab_history:
    st.subheader("Previous runs")

    def folder_size_bytes(p: Path) -> int:
        if not p.exists(): return 0
        if p.is_file(): return p.stat().st_size
        total = 0
        for root, _, files in os.walk(p):
            for f in files:
                try: total += (Path(root) / f).stat().st_size
                except Exception: pass
        return total

    rows = []
    for d in sorted(os.listdir(RUNS_ROOT)):
        if d.startswith("run_"):
            p = RUNS_ROOT / d
            rows.append({
                "Run ID": d,
                "Path": str(p),
                "Size (KB)": round(folder_size_bytes(p) / 1024, 1),
                "Modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption("No runs yet.")

# ---------- Settings tab ----------
with tab_settings:
    st.subheader("Display & behaviour")
    st.caption("Theme can be controlled by `.streamlit/config.toml` (dark mode recommended for projectors).")
    st.code("""[theme]
base="dark"
primaryColor="#3B82F6"
backgroundColor="#0B1220"
secondaryBackgroundColor="#111827"
textColor="#E5E7EB"
font="sans serif"
""", language="toml")

# ---------- About tab (logo lives here now) ----------
with tab_about:
    st.subheader("About this demo")
    st.markdown("""
This UI wraps a multi-agent AutoGen pipeline that validates a system against **Australian ISM** controls,
fills a **System Security Plan** annex, and produces auditor-friendly output. It supports:
- Two input modes: **Existing folder** or **ZIP upload**
- Two execution modes: **Subprocess (CLI)** or **Direct import**
- Reproducible runs: each run stores inputs, logs, and artifacts under `/runs`
""")
    if HERO.exists():
        st.image(str(HERO), caption="Hero visual (header background)", use_container_width=True)
    if LOGO.exists():
        st.image(str(LOGO), caption="Event logo", use_container_width=False, width=360)
