import streamlit as st
import json
import pandas as pd
import os
import uuid

# --- 1. CONFIGURATION (Must be the first Streamlit command) ---
st.set_page_config(
    layout="wide", 
    page_title="Epic Research AI Assistant",
    initial_sidebar_state="expanded" 
)

STORAGE_FILE = "user_data.json"

# --- 2. DATA LOADING & STORAGE REPAIR ---
@st.cache_data
def load_data():
    try:
        with open("epic_tables_parsed.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Data file 'epic_tables_parsed.json' not found.")
        return []

def load_user_data():
    defaults = {"favorites": [], "history": [], "chat_sessions": {}}
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            try:
                data = json.load(f)
                # Repair missing keys if migrating from older versions
                for key in defaults:
                    if key not in data:
                        data[key] = defaults[key]
                return data
            except json.JSONDecodeError:
                return defaults
    return defaults

def save_user_data(data_to_save):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data_to_save, f)

# Initialize Data
data = load_data()
table_list = sorted([t['tableName'] for t in data])
user_data = load_user_data()
table_descriptions = {t['tableName']: t.get('description', 'No description available.') for t in data}

# --- 3. CRITICAL SESSION STATE INITIALIZATION (Prevents KeyErrors) ---
if 'active_page' not in st.session_state:
    st.session_state['active_page'] = "Table Explorer"

if 'current_table' not in st.session_state:
    st.session_state['current_table'] = table_list[0] if table_list else None

if 'sb_key_count' not in st.session_state:
    st.session_state['sb_key_count'] = 0

if 'current_chat_id' not in st.session_state:
    if user_data["chat_sessions"]:
        st.session_state['current_chat_id'] = list(user_data["chat_sessions"].keys())[0]
    else:
        new_id = str(uuid.uuid4())
        user_data["chat_sessions"][new_id] = {"name": "New Research Chat", "messages": []}
        st.session_state['current_chat_id'] = new_id
        save_user_data(user_data)

# --- 4. NAVIGATION HELPERS ---
def set_table(table_name):
    """Updates table selection and logs to history."""
    st.session_state['current_table'] = table_name
    st.session_state['sb_key_count'] += 1
    if not user_data["history"] or user_data["history"][-1] != table_name:
        user_data["history"].append(table_name)
        user_data["history"] = user_data["history"][-50:] # Limit history size
        save_user_data(user_data)

# --- 5. SIDEBAR NAVIGATION BUTTONS ---
st.sidebar.title("🧭 Navigation")
col_nav1, col_nav2 = st.sidebar.columns(2)

if col_nav1.button("Explorer", 
                   type="primary" if st.session_state['active_page'] == "Table Explorer" else "secondary",
                   use_container_width=True):
    st.session_state['active_page'] = "Table Explorer"
    st.rerun()

if col_nav2.button("RAG Chat", 
                   type="primary" if st.session_state['active_page'] == "RAG Model" else "secondary",
                   use_container_width=True):
    st.session_state['active_page'] = "RAG Model"
    st.rerun()

# ==========================================
# PAGE: TABLE EXPLORER
# ==========================================
if st.session_state['active_page'] == "Table Explorer":
    st.sidebar.divider()
    st.sidebar.header("📂 Table Selection")

    # Safety lookup for index
    try:
        current_idx = table_list.index(st.session_state['current_table'])
    except (ValueError, KeyError):
        current_idx = 0

    selected_table_name = st.sidebar.selectbox(
        "Select a table to explore:", 
        table_list, 
        index=current_idx,
        key=f"sb_version_{st.session_state['sb_key_count']}"
    )

    if selected_table_name != st.session_state['current_table']:
        set_table(selected_table_name)

    # Sidebar: Favorites
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
                
    # Sidebar: History
    st.sidebar.divider()
    st.sidebar.header("🕒 History")
    if user_data["history"]:
        recent = list(dict.fromkeys(reversed(user_data["history"])))[:10]
        for hist in recent:
            if st.sidebar.button(f"↩️ {hist}", key=f"hist_nav_{hist}", help=table_descriptions.get(hist)):
                set_table(hist)
                st.rerun()
        if st.sidebar.button("🗑️ Clear History", use_container_width=True):
            user_data["history"] = []
            save_user_data(user_data)
            st.rerun()

    # --- MAIN CONTENT ---
    table_obj = next((t for t in data if t['tableName'] == st.session_state['current_table']), None)
    
    if table_obj:
        c1, c2 = st.columns([0.8, 0.2])
        with c1:
            st.title(f"Table: {table_obj['tableName']}")
        with c2:
            is_fav = table_obj['tableName'] in user_data["favorites"]
            if st.button("❤️ Unfavourite" if is_fav else "🤍 Add Favourite", use_container_width=True):
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
# PAGE: RAG MODEL (CHAT)
# ==========================================
elif st.session_state['active_page'] == "RAG Model":
    # Sidebar: Chat Sessions
    st.sidebar.divider()
    st.sidebar.header("💬 Chat Sessions")
    
    if st.sidebar.button("➕ New Research Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        user_data["chat_sessions"][new_id] = {"name": "New Chat", "messages": []}
        st.session_state['current_chat_id'] = new_id
        save_user_data(user_data)
        st.rerun()

    for chat_id, info in list(user_data["chat_sessions"].items()):
        cols = st.sidebar.columns([0.8, 0.2])
        if cols[0].button(info["name"], key=f"sel_{chat_id}", type="primary" if chat_id == st.session_state['current_chat_id'] else "secondary", use_container_width=True):
            st.session_state['current_chat_id'] = chat_id
            st.rerun()
        if cols[1].button("🗑️", key=f"del_{chat_id}"):
            del user_data["chat_sessions"][chat_id]
            if not user_data["chat_sessions"]:
                new_id = str(uuid.uuid4())
                user_data["chat_sessions"][new_id] = {"name": "New Chat", "messages": []}
                st.session_state['current_chat_id'] = new_id
            elif st.session_state['current_chat_id'] == chat_id:
                st.session_state['current_chat_id'] = list(user_data["chat_sessions"].keys())[0]
            save_user_data(user_data)
            st.rerun()

    # --- CHAT INTERFACE ---
    curr_chat = user_data["chat_sessions"][st.session_state['current_chat_id']]
    st.title(f"🤖 Research AI: {curr_chat['name']}")

    # Display History
# --- Find this section inside the RAG Model loop ---
    for message in curr_chat["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Check if this message has table suggestions attached
            if "tables" in message and message["tables"]:
                st.write("**Related Tables:**")
                
                # Create columns for the suggestion buttons
                t_cols = st.columns(len(message["tables"]))
                
                for idx, t_name in enumerate(message["tables"]):
                    # 1. Look up the description for the hover tooltip
                    # Using .get() ensures it won't crash if a name is missing
                    hover_text = table_descriptions.get(t_name, "No description available.")
                    
                    # 2. Apply the 'help' parameter to show the description on hover
                    if t_cols[idx].button(
                        f"🔍 {t_name}", 
                        key=f"chat_nav_{t_name}_{uuid.uuid4()}",
                        help=hover_text  # This creates the hover tooltip
                    ):
                        set_table(t_name)
                        st.session_state['active_page'] = "Table Explorer"
                        st.rerun()

    # Chat Input
    if prompt := st.chat_input("What clinical data are you looking for?"):
        curr_chat["messages"].append({"role": "user", "content": prompt})
        
        # Keyword-based RAG matching
        words = [w.lower() for w in prompt.split() if len(w) > 3]
        matches = []
        for t in data:
            if any(word in t['description'].lower() or word in t['tableName'].lower() for word in words):
                matches.append(t['tableName'])
        
        top_matches = matches[:3]
        if top_matches:
            ai_response = f"I found {len(matches)} tables related to your request. Here are the most relevant ones to explore:"
        else:
            ai_response = "I couldn't find a direct table match. Could you try describing the data differently (e.g., 'vitals', 'lab results', or 'patient demographics')?"

        curr_chat["messages"].append({
            "role": "assistant", 
            "content": ai_response,
            "tables": top_matches
        })

        if len(curr_chat["messages"]) <= 2:
            curr_chat["name"] = (prompt[:30] + "...") if len(prompt) > 30 else prompt
            
        save_user_data(user_data)
        st.rerun()
