import streamlit as st
import json
import pandas as pd
import os
import uuid  # For unique chat session IDs

# --- 1. CONFIGURATION ---
st.set_page_config(
    layout="wide", 
    page_title="Epic Research AI Assistant",
    initial_sidebar_state="expanded" 
)

STORAGE_FILE = "user_data.json"

# --- 2. DATA LOADING ---
@st.cache_data
def load_data():
    with open("epic_tables_parsed.json", "r", encoding='utf-8') as f:
        return json.load(f)

def load_user_data():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    return {"favorites": [], "history": [], "chat_sessions": {}}

def save_user_data(data_to_save):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data_to_save, f)

data = load_data()
table_list = sorted([t['tableName'] for t in data])
user_data = load_user_data()
table_descriptions = {t['tableName']: t.get('description', 'No description available.') for t in data}

# --- 3. SESSION STATE INITIALIZATION ---
if 'active_page' not in st.session_state:
    st.session_state['active_page'] = "Table Explorer"
if 'current_chat_id' not in st.session_state:
    # Set to a default or the first existing session
    if user_data["chat_sessions"]:
        st.session_state['current_chat_id'] = list(user_data["chat_sessions"].keys())[0]
    else:
        new_id = str(uuid.uuid4())
        user_data["chat_sessions"][new_id] = {"name": "New Research Chat", "messages": []}
        st.session_state['current_chat_id'] = new_id
        save_user_data(user_data)

# --- 4. NAVIGATION & CHAT MANAGEMENT ---
st.sidebar.title("🧭 Navigation")
c_nav1, c_nav2 = st.sidebar.columns(2)

if c_nav1.button("Explorer", type="primary" if st.session_state['active_page'] == "Table Explorer" else "secondary", use_container_width=True):
    st.session_state['active_page'] = "Table Explorer"
    st.rerun()

if c_nav2.button("RAG Chat", type="primary" if st.session_state['active_page'] == "RAG Model" else "secondary", use_container_width=True):
    st.session_state['active_page'] = "RAG Model"
    st.rerun()

# Sidebar: Chat Session Management
if st.session_state['active_page'] == "RAG Model":
    st.sidebar.divider()
    st.sidebar.header("💬 Chat Sessions")
    
    if st.sidebar.button("➕ Create New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        user_data["chat_sessions"][new_id] = {"name": f"Chat {len(user_data['chat_sessions'])+1}", "messages": []}
        st.session_state['current_chat_id'] = new_id
        save_user_data(user_data)
        st.rerun()

    # List available chats
    for chat_id, info in list(user_data["chat_sessions"].items()):
        cols = st.sidebar.columns([0.8, 0.2])
        is_current = (chat_id == st.session_state['current_chat_id'])
        
        if cols[0].button(info["name"], key=f"select_{chat_id}", type="primary" if is_current else "secondary", use_container_width=True):
            st.session_state['current_chat_id'] = chat_id
            st.rerun()
            
        if cols[1].button("🗑️", key=f"del_chat_{chat_id}"):
            del user_data["chat_sessions"][chat_id]
            if not user_data["chat_sessions"]: # Ensure at least one exists
                new_id = str(uuid.uuid4())
                user_data["chat_sessions"][new_id] = {"name": "New Research Chat", "messages": []}
                st.session_state['current_chat_id'] = new_id
            elif st.session_state['current_chat_id'] == chat_id:
                st.session_state['current_chat_id'] = list(user_data["chat_sessions"].keys())[0]
            save_user_data(user_data)
            st.rerun()

# Helper for Explorer navigation
def set_table(table_name):
    st.session_state['current_table'] = table_name
    if 'sb_key_count' not in st.session_state: st.session_state['sb_key_count'] = 0
    st.session_state['sb_key_count'] += 1
    if not user_data["history"] or user_data["history"][-1] != table_name:
        user_data["history"].append(table_name)
        save_user_data(user_data)

# ==========================================
# PAGE 1: TABLE EXPLORER
# ==========================================
if st.session_state['active_page'] == "Table Explorer":
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

    # Favorites & History (Sidebar)
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
# PAGE 2: RAG MODEL (CHAT FORMAT)
# ==========================================
elif st.session_state['active_page'] == "RAG Model":
    curr_chat = user_data["chat_sessions"][st.session_state['current_chat_id']]
    
    st.title(f"🤖 Research AI: {curr_chat['name']}")
    
    # Display Chat History
    for message in curr_chat["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "tables" in message:
                cols = st.columns(len(message["tables"]))
                for idx, t_name in enumerate(message["tables"]):
                    if cols[idx].button(f"🔍 {t_name}", key=f"msg_nav_{t_name}_{uuid.uuid4()}"):
                        set_table(t_name)
                        st.session_state['active_page'] = "Table Explorer"
                        st.rerun()

    # Chat Input
    if prompt := st.chat_input("Ask about a research topic..."):
        # Add User Message
        curr_chat["messages"].append({"role": "user", "content": prompt})
        
        # RAG Logic (Simple Keyword Matcher)
        found_tables = []
        words = [w.lower() for w in prompt.split() if len(w) > 3]
        for t in data:
            if any(word in t['description'].lower() or word in t['tableName'].lower() for word in words):
                found_tables.append(t['tableName'])
        
        # Build Response
        top_tables = found_tables[:3]
        if top_tables:
            response = f"Based on your query, I found {len(found_tables)} relevant tables. Here are the top matches that might contain your variables:"
        else:
            response = "I couldn't find a direct match for those terms. Try describing the clinical event (e.g., 'medication orders' or 'vitals')."
        
        # Add AI Message
        curr_chat["messages"].append({
            "role": "assistant", 
            "content": response,
            "tables": top_tables
        })
        
        # Auto-update Chat Name if it's the first message
        if len(curr_chat["messages"]) <= 2:
            curr_chat["name"] = (prompt[:25] + '...') if len(prompt) > 25 else prompt
            
        save_user_data(user_data)
        st.rerun()
