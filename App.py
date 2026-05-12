  import streamlit as st
import pandas as pd
import re
from datetime import datetime

# =========================================================
# 1. PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="GenieLink DNA Portal",
    page_icon="🧬",
    layout="wide"
)

# =========================================================
# 2. SESSION STATE
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
# 3. DNA TEXT PARSER
# =========================================================
def parse_dna_data(raw_text):
    """
    Extract names + cM values from pasted DNA match text.
    """
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

            # Search upward for possible name
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
# 4. LOGIN SYSTEM
# =========================================================
if st.session_state.access_type is None:

    st.title("🧬 GenieLink DNA Portal")

    name_input = st.text_input("Name")
    key_input = st.text_input("Access Key", type="password").strip()

    if st.button("Unlock Portal"):

        temp_codes = st.secrets.get("temporary_codes", [])

        # Founder Access
        if key_input == "Genie20":
            st.session_state.access_type = "Founder"
            st.session_state.user_name = name_input
            st.rerun()

        # Temporary / Guest Access
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
# 5. MAIN HEADER
# =========================================================
st.title(f"🧬 Welcome, {st.session_state.user_name}!")

tab1, tab2 = st.tabs([
    "📄 Paste Text",
    "📊 Upload CSV"
])

# =========================================================
# 6. TEXT INPUT TAB
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

                    parsed = parse_dna_data(kit_data)

                    if parsed:
                        st.session_state.all_kits[kit_name] = parsed
                        added_count += 1

            if added_count > 0:
                st.success(f"✅ Loaded {added_count} text kit(s).")
                st.rerun()
            else:
                st.warning("No valid kits were added.")

# =========================================================
# 7. CSV UPLOAD TAB
# =========================================================
with tab2:

    uploaded_files = st.file_uploader(
        "Upload CSV files",
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

                    # Normalize columns
                    df.columns = [
                        str(col).lower().strip()
                        for col in df.columns
                    ]

                    # Find likely name column
                    name_col = next(
                        (
                            c for c in df.columns
                            if c in ["name", "match", "person"]
                        ),
                        None
                    )

                    # Find likely cM column
                    cm_col = next(
                        (
                            c for c in df.columns
                            if c in ["cm", "shared", "total"]
                        ),
                        None
                    )

                    if not name_col or not cm_col:
                        st.error(
                            f"❌ {file.name}: Could not detect required columns."
                        )
                        continue

                    # Clean rows
                    clean_df = df.dropna(subset=[name_col, cm_col]).copy()

                    # Convert cM values
                    clean_df[cm_col] = pd.to_numeric(
                        clean_df[cm_col]
                        .astype(str)
                        .str.replace(" cM", "", regex=False)
                        .str.replace(",", "", regex=False),
                        errors="coerce"
                    )

                    clean_df = clean_df.dropna(subset=[cm_col])

                    # Save to session
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
                    st.error(f"❌ Failed to read {file.name}: {e}")

            if success_count > 0:
                st.rerun()

# =========================================================
# 8. TRIANGULATION RESULTS
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

    # -----------------------------------------------------
    # Find Shared Matches
    # -----------------------------------------------------
    kit_values = list(st.session_state.all_kits.values())

    shared_matches = set(kit_values[0].keys())

    for kit in kit_values[1:]:
        shared_matches.intersection_update(kit.keys())

    results = []

    for match_name in shared_matches:

        # Apply filters
        valid = all(
            st.session_state.all_kits[k].get(match_name, 0) >= min_cm
            for k in st.session_state.all_kits
        )

        if valid and search_query in match_name:

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

            # Add kit cM values
            for kit_name in st.session_state.all_kits:
                row[kit_name] = (
                    st.session_state.all_kits[kit_name][match_name]
                )

            results.append(row)

    # -----------------------------------------------------
    # Display Results
    # -----------------------------------------------------
    if results:

        results_df = pd.DataFrame(results)

        column_config = {
            "Research": st.column_config.LinkColumn("🔍 Research"),
            "Notes": st.column_config.TextColumn(
                "Notes",
                width="large"
            )
        }

        # Add dynamic number columns
        for kit_name in st.session_state.all_kits.keys():
            column_config[kit_name] = st.column_config.NumberColumn(
                kit_name,
                format="%d cM"
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

        # Save Notes
        for _, row in edited_df.iterrows():

            st.session_state.match_notes[
                row["Match Name"].lower()
            ] = row["Notes"]

        # Export CSV
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
# 9. SIDEBAR ACTIONS
# =========================================================
st.sidebar.header("⚙️ Actions")

if st.sidebar.button("Reset Everything"):

    st.session_state.all_kits = {}
    st.session_state.match_notes = {}

    st.rerun()
