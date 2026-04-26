import streamlit as st
import pandas as pd
import re
from datetime import datetime

import streamlit as st
import pandas as pd
import re
from datetime import datetime

# 1. PAGE CONFIG
st.set_page_config(page_title="GenieLink DNA Portal", page_icon="🧬", layout="wide")

# 2. SESSION STATE
if "access_type" not in st.session_state: st.session_state["access_type"] = None
if "user_name" not in st.session_state: st.session_state["user_name"] = ""
if 'all_kits' not in st.session_state: st.session_state.all_kits = {}
if 'match_notes' not in st.session_state: st.session_state.match_notes = {}

# 3. DNA TEXT PARSER
def parse_dna_data(raw_text):
    if not raw_text: return {}
    matches = {}
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    skip = ["cousin", "removed", "half", "paternal", "maternal", "shared dna", "tree"]
    for i, line in enumerate(lines):
        cm_match = re.search(r"(\d+)\s*cM", line)
        if cm_match:
            val = int(cm_match.group(1))
            for j in range(i - 1, -1, -1):
                pot = lines[j]
                is_garbage = any(k in pot.lower() for k in skip)
                if not is_garbage and re.search('[a-zA-Z]', pot):
                    matches[pot.strip().lower()] = val
                    break
    return matches

# 4. LOGIN SYSTEM
if st.session_state.access_type is None:
    st.title("🧬 GenieLink DNA Portal")
    n_in = st.text_input("Name:")
    k_in = st.text_input("Key:", type="password").strip()
    if st.button("Unlock"):
        t_codes = st.secrets.get("temporary_codes", [])
        if k_in == "Genie20":
            st.session_state.access_type, st.session_state.user_name = "Founder", n_in
            st.rerun()
        elif k_in in t_codes:
            d_match = re.search(r"(\d{4}-\d{2}-\d{2})$", k_in)
            if d_match:
                exp = datetime.strptime(d_match.group(1), "%Y-%m-%d").date()
                if datetime.now().date() <= exp:
                    st.session_state.access_type, st.session_state.user_name = "Temp", n_in
                    st.rerun()
                else: st.error("Key Expired")
            else:
                st.session_state.access_type, st.session_state.user_name = "Guest", n_in
                st.rerun()
        else: st.error("Invalid Key")
else:
    # 5. MAIN INTERFACE
    st.title(f"🧬 Welcome, {st.session_state.user_name}!")
    t1, t2 = st.tabs(["📄 Paste Text", "📊 Upload CSV"])

    with t1:
        num = st.number_input("Number of kits:", 1, 10, 1)
        with st.form("text_form"):
            inputs = []
            for i in range(int(num)):
                c1, c2 = st.columns([1, 2])
                inputs.append((c1.text_input(f"Kit {i+1} Name", key=f"n{i}"), c2.text_area(f"Data {i+1}", key=f"d{i}")))
            if st.form_submit_button("Process Text Kits"):
                for n, d in inputs:
                    if n and d: st.session_state.all_kits[n] = parse_dna_data(d)
                st.rerun()

    with t2:
        up = st.file_uploader("Upload CSVs", accept_multiple_files=True)
        if st.button("Process CSVs"):
            for f in up:
                try:
                    df = pd.read_csv(f)
                    df.columns = [str(c).lower().strip() for c in df.columns]
                    nc = next((c for c in df.columns if c in ['name','match name','full name','person','display name','match']), None)
                    cc = next((c for c in df.columns if c in ['
