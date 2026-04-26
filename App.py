import streamlit as st
import pandas as pd
import re
from datetime import datetime

import streamlit as st
import pandas as pd
import re
from datetime import datetime

import streamlit as st
import pd as pd
import pandas as pd
import re
from datetime import datetime

import streamlit as st
import pandas as pd
import re
from datetime import datetime
import streamlit as st
import pandas as pd
import re
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(page_title="GenieLink DNA Portal", page_icon="🧬", layout="wide")

# 2. STATE MANAGEMENT
if "access_type" not in st.session_state: st.session_state["access_type"] = None
if "user_name" not in st.session_state: st.session_state["user_name"] = ""
if 'all_kits' not in st.session_state: st.session_state.all_kits = {}
if 'match_notes' not in st.session_state: st.session_state.match_notes = {}

# 3. TEXT DATA PARSER
def parse_dna_data(raw_text):
    if not raw_text: return {}
    matches = {}
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    skip = ["cousin", "removed", "half", "paternal", "maternal", "shared dna", "tree"]
    for i, line in enumerate(lines):
        cm_m = re.search(r"(\d+)\s*cM", line)
        if cm_m:
            val = int(cm_m.group(1))
            for j in range(i - 1, -1, -1):
                pot = lines[j]
                if not any(k in pot.lower() for k in skip) and re.search('[a-zA-Z]', pot):
                    matches[pot.strip().lower()] = val
                    break
    return matches

# 4. LOGIN SYSTEM
if st.session_state.access_type is None:
    st.title("🧬 GenieLink DNA Portal")
    n_in = st.text_input("Name:")
    k_in = st.text_input("Key:", type="password").strip()
    if st.button("Unlock Portal"):
        t_codes = st.secrets.get("temporary_codes", [])
        if k_in == "Genie20":
            st.session_state.access_type, st.session_state.user_name = "Founder", n_in
            st.rerun()
        elif k_in in t_codes:
            d_m = re.search(r"(\d{4}-\d{2}-\d{2})$", k_in)
            if d_m:
                exp = datetime.strptime(d_m.group(1), "%Y-%m-%d").date()
                if datetime.now().date() <= exp:
                    st.session_state.access_type, st.session_state.user_name = "Temp", n_in
                    st.rerun()
                else: st.error("Key Expired")
            else:
                st.session_state.access_type, st.session_state.user_name = "Guest", n_in
                st.rerun()
        else: st.error("Invalid Key")
    st.stop()

# 5. MAIN APP HEADER
st.title(f"🧬 Welcome, {st.session_state.user_name}!")
t1, t2 = st.tabs(["📄 Paste Text", "📊 Upload CSV"])

with t1:
    num = st.number_input("How many kits?", 1, 10, 1)
    with st.form("text_form"):
        inps = []
        for i in range(int(num)):
            c1, c2 = st.columns([1, 2])
            inps.append((c1.text_input(f"Kit {i+1} Name", key=f"n{i}"), c2.text_area(f"Data {i+1}", key=f"d{i}")))
        if st.form_submit_button("Process Text Kits"):
            for n, d in inps:
                if n and d: st.session_state.all_kits[n] = parse_dna_data(d)
            st.rerun()

with t2:
    up = st.file_uploader("Upload CSV files", accept_multiple_files=True)
    if st.button("Process CSVs"):
        for f in up:
            try:
                df = pd.read_csv(f)
                df.columns = [str(c).lower().strip() for c in df.columns]
                nc = next((c for c in df.columns if c in ['name','match','person']), None)
                cc = next((c for c in df.columns if c in ['cm','total','shared']), None)
                if nc and cc:
                    df = df.dropna(subset=[nc, cc])
                    df[cc] = pd.to_numeric(df[cc].astype(str).str.replace(' cM', ''), errors='coerce')
                    st.session_state.all_kits[f.name] = dict(zip(df[nc].astype(str).str.lower(), df[cc].dropna()))
                    st.success(f"Loaded {f.name}")
            except: st.error(f"Failed to read {f.name}")
        st.rerun()

# 6. RESULTS & FILTERS (Visible when 2+ kits added)
if len(st.session_state.all_kits) >= 2:
    st.divider()
    st.header("🔍 Triangulated Match Results")
    col_s, col_c = st.columns([2, 1])
    q = col_s.text_input("🔍 Social Search (Filter by Name):").lower()
    m_cm = col_c.slider("📏 Min cM Filter:", 0, 100, 7)

    # Calculate Intersection
    kl = list(st.session_state.all_kits.values())
    shared = set(kl[0].keys())
    for d in kl[1:]: shared.intersection_update(d.keys())

    res = []
    for name in shared:
        if all(st.session_state.all_kits[k].get(name, 0) >= m_cm for k in st.session_state.all_kits) and q in name:
            row = {"Match Name": name.title()}
            for k in st.session_state.all_kits: row[k] = st.session_state.all_kits[k][name]
            row["Research"] = f"https://www.google.com/search?q=\"{name.replace(' ', '+')}\"+genealogy"
            row["Notes"] = st.session_state.match_notes.get(name, "")
            res.append(row)

    if res:
        df_f = pd.DataFrame(res)
        cfg = {
            "Research": st.column_config.LinkColumn("🔍"), 
            "Notes": st.column_config.TextColumn("Notes", width="large"),
            **{k: st.column_config.NumberColumn(format="%d cM") for k in st.session_state.all_kits.keys()}
        }
        edt = st.data_editor(df_f, column_config=cfg, disabled=[c for c in df_f.columns if c != "Notes"], hide_index=True, key="dt_edit")
        
        # Save Notes
        for _, r in edt.iterrows():
            st.session_state.match_notes[r["Match Name"].lower()] = r["Notes"]
        
        st.download_button("📥 Export Report", edt.to_csv(index=False).encode('utf-8'), "GenieLink_Report.csv")
    else:
        st.info("No shared matches found for these kits at the selected cM threshold.")

# 7. SIDEBAR ACTIONS
if st.sidebar.button("Reset Everything"):
    st.session_state.all_kits, st.session_state.match_notes = {}, {}
    st.rerun()
