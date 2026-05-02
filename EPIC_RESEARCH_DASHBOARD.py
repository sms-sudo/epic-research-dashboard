import streamlit as st
import json
import pandas as pd
import os

# --- 1. CONFIGURATION (Must be the very first Streamlit command) ---
st.set_page_config(
    layout="wide", 
    page_title="Epic Research Schema Explorer",
    initial_sidebar_state="expanded" 
)

STORAGE_FILE = "user_data.json"

# --- 2. SHARED DATA LOADING ---
@st.cache_data
def load_data():
    with open("epic_tables_parsed.json", "r", encoding='utf-8') as f:
        data = json.load(f)
    return data

def load_user_data():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    return {"favorites": [], "history": []}

def save_user_data(user_data_in):
    with open(STORAGE_FILE, "w") as f:
        json.dump(user_data_in, f)

# Initialize data
data = load_data()
table_list = sorted([t['tableName'] for t in data])
user_data = load_user_data()
table_descriptions = {t['tableName']: t.get('description', 'No description available.') for t in data}

# --- 3. NAVIGATION ---
st.sidebar.title("🧭 Navigation")
app_mode = st.sidebar.radio("Go to:", ["Table Explorer", "RAG Model"])

# --- 4. SESSION STATE & HELPERS ---
if 'current_table' not in st.session_state:
    st.session_state['current_table'] = table_list[0]

if 'sb_key_count' not in st.session_state:
    st.session_state['sb_key_count'] = 0

def set_table(table_name):
    st.session_state['current_table'] = table_name
    st.session_state['sb_key_count'] += 1
    if not user_data["history"] or user_data["history"][-1] != table_name:
        user_data["history"].append(table_name)
        user_data["history"] = user_data["history"][-50:]
        save_user_data(user_data)

# ==========================================
# PAGE 1: TABLE EXPLORER
# ==========================================
if app_mode == "Table Explorer":
    st.sidebar.divider()
    st.sidebar.header("📂 Table Selection")

    try:
        current_index = table_list.index(st.session_state['current_table'])
    except ValueError:
        current_index = 0

    selected_table_name = st.sidebar.selectbox(
        "Select a table to explore:", 
        table_list, 
        index=current_index,
        key=f"sb_version_{st.session_state['sb_key_count']}"
    )

    if selected_table_name != st.session_state['current_table']:
        set_table(selected_table_name)

    # Favorites & History
    st.sidebar.divider()
    st.sidebar.header("⭐️ Favorites")
    if user_data["favorites"]:
        for fav in user_data["favorites"]:
            cols = st.sidebar.columns([0.8, 0.2])
            if cols[0].button(f"📍 {fav}", key=f"fav_nav_{fav}", help=table_descriptions.get(fav)):
                set_table(fav)
                st.rerun()
            if cols[1].button("❌", key=f"fav_del_{fav}"):
                user_data["favorites"].remove(fav)
                save_user_data(user_data)
                st.rerun()
                
    st.sidebar.divider()
    st.sidebar.header("🕒 History")
    if user_data["history"]:
        recent = list(dict.fromkeys(reversed(user_data["history"])))[:10]
        for hist in recent:
            desc = table_descriptions.get(hist, "No description available.")
            if st.sidebar.button(f"↩️ {hist}", key=f"hist_nav_{hist}", help=desc):
                set_table(hist)
                st.rerun()
        if st.sidebar.button("🗑️ Clear History", use_container_width=True):
            user_data["history"] = []
            save_user_data(user_data)
            st.rerun()

    # Main Area Content
    table_obj = next((t for t in data if t['tableName'] == st.session_state['current_table']), None)
    if table_obj:
        c1, c2 = st.columns([0.8, 0.2])
        with c1:
            st.title(f"Table: {table_obj['tableName']}")
        with c2:
            is_fav = table_obj['tableName'] in user_data["favorites"]
            if st.button("❤️ Unfavourite" if is_fav else "🤍 Add Favourite"):
                if is_fav: user_data["favorites"].remove(table_obj['tableName'])
                else: user_data["favorites"].append(table_obj['tableName'])
                save_user_data(user_data)
                st.rerun()

        if table_obj.get('description'):
            st.info(f"**Description:** {table_obj['description']}")

        tab1, tab2 = st.tabs(["📋 Columns & Keys", "🔗 Relationship Explorer"])
        with tab1:
            if table_obj.get('primaryKey'):
                st.subheader("Primary Keys")
                st.table(pd.DataFrame(table_obj['primaryKey']))
            col_df = pd.DataFrame(table_obj['columns'])
            if not col_df.empty:
                st.subheader("All Columns")
                display_cols = ['name', 'type', 'description', 'isDiscontinued']
                actual_cols = [c for c in display_cols if c in col_df.columns]
                st.dataframe(col_df[actual_cols], use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Tie-back Finder")
            def find_related(col_name):
                return sorted(list(set(t['tableName'] for t in data if t['tableName'] != st.session_state['current_table'] and any(c['name'].upper() == col_name.upper() for c in t['columns']))))
            
            cols_to_check = sorted([c['name'] for c in table_obj['columns']], key=lambda x: ("ID" not in x, x))
            for col_name in cols_to_check:
                related_tables = find_related(col_name)
                if related_tables:
                    with st.expander(f"{col_name} ({len(related_tables)} tables)"):
                        r_cols = st.columns(3)
                        for i, r_table in enumerate(related_tables):
                            r_cols[i % 3].button(r_table, key=f"rel_{col_name}_{r_table}", on_click=set_table, args=(r_table,), help=table_descriptions.get(r_table))

# ==========================================
# PAGE 2: RAG MODEL
# ==========================================
elif app_mode == "RAG Model":
    st.title("🤖 RAG Research Model")
    st.markdown("Analyze your research question to find the best data paths.")
    
    with st.container(border=True):
        query = st.text_area("Enter your research idea:", height=150, placeholder="e.g. Impact of SDOH on Readmission rates...")
        if st.button("Generate Data Recommendations", type="primary"):
            st.divider()
            st.subheader("Top Recommended Tables")
            # Simple semantic mock-up logic
            matches = [t for t in data if any(word.lower() in t['description'].lower() for word in query.split() if len(word) > 3)]
            if matches:
                for m in matches[:5]:
                    with st.expander(f"Table: {m['tableName']}"):
                        st.write(m['description'])
                        if st.button(f"View {m['tableName']}", key=f"rag_nav_{m['tableName']}"):
                            st.session_state['current_table'] = m['tableName']
                            # Note: To fully switch pages, user would manually select 'Table Explorer'
                            st.success(f"Selected {m['tableName']}. Switch to 'Table Explorer' to view details.")
            else:
                st.warning("No high-confidence matches found.")
