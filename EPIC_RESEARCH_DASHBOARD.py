import streamlit as st
import json
import pandas as pd
import os

# Set page to wide mode
st.set_page_config(layout="wide", page_title="Epic Research Schema Explorer")

STORAGE_FILE = "user_data.json"

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

def save_user_data(user_data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(user_data, f)

# Initialize data
data = load_data()
table_list = sorted([t['tableName'] for t in data])
user_data = load_user_data()

# Map table names to descriptions for quick lookup during hover
table_descriptions = {t['tableName']: t.get('description', 'No description available.') for t in data}

# --- SESSION STATE MANAGEMENT ---
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

# --- SIDEBAR ---
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

# --- FAVORITES & HISTORY ---
st.sidebar.divider()
st.sidebar.header("⭐️ Favorites")
if user_data["favorites"]:
    for fav in user_data["favorites"]:
        cols = st.sidebar.columns([0.8, 0.2])
        # Added hover description to favorite buttons
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
    recent = list(dict.fromkeys(reversed(user_data["history"])))[:5]
    for hist in recent:
        # Added hover description to history buttons
        if st.sidebar.button(f"↩️ {hist}", key=f"hist_nav_{hist}", help=table_descriptions.get(hist)):
            set_table(hist)
            st.rerun()

# --- MAIN AREA ---
table_obj = next((t for t in data if t['tableName'] == st.session_state['current_table']), None)

if table_obj:
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.title(f"Table: {table_obj['tableName']}")
    with col2:
        is_fav = table_obj['tableName'] in user_data["favorites"]
        if st.button("❤️ Unfavourite" if is_fav else "🤍 Add Favourite"):
            if is_fav:
                user_data["favorites"].remove(table_obj['tableName'])
            else:
                user_data["favorites"].append(table_obj['tableName'])
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
                        # --- THE CHANGE IS HERE ---
                        # Use the 'help' parameter to show the table description on hover
                        desc_text = table_descriptions.get(r_table, "No description available.")
                        
                        r_cols[i % 3].button(
                            r_table, 
                            key=f"rel_{col_name}_{r_table}", 
                            on_click=set_table, 
                            args=(r_table,),
                            help=desc_text  # Tooltip content
                        )
