import streamlit as st
import pandas as pd
import re
from datetime import datetime

# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="GenieLink DNA Portal",
    page_icon="🧬",
    layout="wide"
)

# =========================================================
# SESSION STATE
# =========================================================
if "access_type" not in st.session_state:
    st.session_state.access_type = None

if "user_name" not in st.session_state:
    st.session_state.user_name = ""

if "all_kits" not in st.session_state:
    st.session_state.all_kits = {}

if "match_notes" not in st.session_state:
    st.session_state.match_notes = {}

# =========================================================
# DNA TEXT PARSER
# =========================================================
def parse_dna_data(raw_text):
    if not raw_text:
        return {}

    matches = {}

    lines = [
        line.strip()
        for line in raw_text.split("\n")
        if line.strip()
    ]

    skip_words = [
        "cousin",
        "removed",
        "half",
        "paternal",
        "maternal",
        "shared dna",
        "tree"
    ]

    for i, line in enumerate(lines):

        cm_match = re.search(r"(\d+)\s*cM", line, re.IGNORECASE)

        if cm_match:

            cm_value = int(cm_match.group(1))

            # Search upward for the name
            for j in range(i - 1, -1, -1):

                possible_name = lines[j]

                if (
                    not any(word in possible_name.lower() for word in skip_words)
                    and re.search(r"[a-zA-Z]", possible_name)
                ):
                    matches[possible_name.strip().lower()] = cm_value
                    break

    return matches

# =========================================================
# LOGIN SYSTEM
# =========================================================
if st.session_state.access_type is None:

    st.title("🧬 GenieLink DNA Portal")

    name_input = st.text_input("Name")
    key_input = st.text_input("Access Key", type="password").strip()

    if st.button("Unlock Portal"):

        temp_codes = st.secrets.get("temporary_codes", [])

        # Founder access
        if key_input == "Genie20":

            st.session_state.access_type = "Founder"
            st.session_state.user_name = name_input
            st.rerun()

        # Temporary access
        elif key_input in temp_codes:

            date_match = re.search(r"(\d{4}-\d{2}-\d{2})$", key_input)

            if date_match:

                expiry_date = datetime.strptime(
                    date_match.group(1),
                    "%Y-%m-%d"
                ).date()

                if datetime.now().date() <= expiry_date:

                    st.session_state.access_type = "Temp"
                    st.session_state.user_name = name_input
                    st.rerun()

                else:
                    st.error("❌ Access key expired.")

            else:

                st.session_state.access_type = "Guest"
                st.session_state.user_name = name_input
                st.rerun()

        else:
            st.error("❌ Invalid access key.")

    st.stop()

# =========================================================
# MAIN APP
# =========================================================
st.title(f"🧬 Welcome, {st.session_state.user_name}!")

tab1, tab2 = st.tabs([
    "📄 Paste Text",
    "📊 Upload CSV"
])

# =========================================================
# TEXT INPUT TAB
# =========================================================
with tab1:

    num_kits = st.number_input(
        "How many kits?",
        min_value=1,
        max_value=10,
        value=1
    )

    with st.form("text_form"):

        kit_inputs = []

        for i in range(int(num_kits)):

            col1, col2 = st.columns([1, 2])

            kit_name = col1.text_input(
                f"Kit {i+1} Name",
                key=f"name_{i}"
            )

            kit_data = col2.text_area(
                f"DNA Data {i+1}",
                key=f"data_{i}"
            )

            kit_inputs.append((kit_name, kit_data))

        submit_text = st.form_submit_button("Process Text Kits")

        if submit_text:

            added_count = 0

            for kit_name, kit_data in kit_inputs:

                if kit_name and kit_data:

                    parsed_data = parse_dna_data(kit_data)

                    if parsed_data:

                        st.session_state.all_kits[kit_name] = parsed_data
                        added_count += 1

            if added_count > 0:

                st.success(f"✅ Loaded {added_count} kit(s).")
                st.rerun()

            else:
                st.warning("No valid kits were added.")

# =========================================================
# CSV UPLOAD TAB
# =========================================================
with tab2:

    uploaded_files = st.file_uploader(
        "Upload CSV Files",
        type=["csv"],
        accept_multiple_files=True
    )

    if st.button("Process CSV Files"):

        if not uploaded_files:

            st.warning("Please upload at least one CSV file.")

        else:

            success_count = 0

            for file in uploaded_files:

                try:

                    df = pd.read_csv(file)

                    # Normalize column names
                    df.columns = [
                        str(col).lower().strip()
                        for col in df.columns
                    ]

                    # Detect columns
                    name_col = next(
                        (
                            c for c in df.columns
                            if c in ["name", "match", "person"]
                        ),
                        None
                    )

                    cm_col = next(
                        (
                            c for c in df.columns
                            if c in ["cm", "shared", "total"]
                        ),
                        None
                    )

                    if not name_col or not cm_col:

                        st.error(
                            f"❌ {file.name}: Missing required columns."
                        )
                        continue

                    # Clean dataframe
                    clean_df = df.dropna(
                        subset=[name_col, cm_col]
                    ).copy()

                    # Convert cM values
                    clean_df[cm_col] = pd.to_numeric(
                        clean_df[cm_col]
                        .astype(str)
                        .str.replace(" cM", "", regex=False)
                        .str.replace(",", "", regex=False),
                        errors="coerce"
                    )

                    clean_df = clean_df.dropna(subset=[cm_col])

                    # Store data
                    st.session_state.all_kits[file.name] = dict(
                        zip(
                            clean_df[name_col]
                            .astype(str)
                            .str.lower(),

                            clean_df[cm_col]
                        )
                    )

                    success_count += 1

                    st.success(f"✅ Loaded {file.name}")

                except Exception as e:

                    st.error(
                        f"❌ Failed to read {file.name}: {e}"
                    )

            if success_count > 0:
                st.rerun()

# =========================================================
# TRIANGULATED MATCH RESULTS
# =========================================================
if len(st.session_state.all_kits) >= 2:

    st.divider()

    st.header("🔍 Triangulated Match Results")

    col_search, col_filter = st.columns([2, 1])

    search_query = col_search.text_input(
        "🔍 Filter by Name"
    ).lower()

    min_cm = col_filter.slider(
        "📏 Minimum cM",
        min_value=0,
        max_value=100,
        value=7
    )

    # Find shared matches
    kit_values = list(st.session_state.all_kits.values())

    shared_matches = set(kit_values[0].keys())

    for kit in kit_values[1:]:
        shared_matches.intersection_update(kit.keys())

    results = []

    for match_name in shared_matches:

        valid_match = all(
            st.session_state.all_kits[kit_name].get(match_name, 0) >= min_cm
            for kit_name in st.session_state.all_kits
        )

        if valid_match and search_query in match_name:

            row = {
                "Match Name": match_name.title(),
                "Research": (
                    f'https://www.google.com/search?q='
                    f'"{match_name.replace(" ", "+")}"'
                    f'+genealogy'
                ),
                "Notes": st.session_state.match_notes.get(
                    match_name,
                    ""
                )
            }

            # Add cM values
            for kit_name in st.session_state.all_kits:

                row[kit_name] = (
                    st.session_state.all_kits[kit_name][match_name]
                )

            results.append(row)

    # Display results
    if results:

        results_df = pd.DataFrame(results)

        column_config = {
            "Research": st.column_config.LinkColumn(
                "🔍 Research"
            ),
            "Notes": st.column_config.TextColumn(
                "Notes",
                width="large"
            )
        }

        # Dynamic cM columns
        for kit_name in st.session_state.all_kits.keys():

            column_config[kit_name] = (
                st.column_config.NumberColumn(
                    kit_name,
                    format="%d cM"
                )
            )

        edited_df = st.data_editor(
            results_df,
            column_config=column_config,
            disabled=[
                col
                for col in results_df.columns
                if col != "Notes"
            ],
            hide_index=True,
            key="results_editor"
        )

        # Save notes
        for _, row in edited_df.iterrows():

            st.session_state.match_notes[
                row["Match Name"].lower()
            ] = row["Notes"]

        # Download button
        st.download_button(
            label="📥 Export Report",
            data=edited_df.to_csv(index=False).encode("utf-8"),
            file_name="GenieLink_Report.csv",
            mime="text/csv"
        )

    else:

        st.info(
            "No shared matches found at the selected cM threshold."
        )

# =========================================================
# SIDEBAR ACTIONS
# =========================================================
st.sidebar.header("⚙️ Actions")

if st.sidebar.button("Reset Everything"):

    st.session_state.all_kits = {}
    st.session_state.match_notes = {}

    st.rerun()
