import streamlit as st
import json
import pandas as pd

# Set page to wide mode
st.set_page_config(layout="wide", page_title="Epic Research Schema Explorer")

@st.cache_data
def load_data():
    with open("epic_tables_parsed.json", "r", encoding='utf-8') as f:
        data = json.load(f)
    return data

data = load_data()
table_list = sorted([t['tableName'] for t in data])

# --- SESSION STATE MANAGEMENT ---
if 'current_table' not in st.session_state:
    st.session_state['current_table'] = table_list[0]

# This counter acts as a 'version' for the selectbox to force a refresh
if 'sb_key_count' not in st.session_state:
    st.session_state['sb_key_count'] = 0

def set_table(table_name):
    """Updates the state and increments the key count to force widget refresh"""
    st.session_state['current_table'] = table_name
    st.session_state['sb_key_count'] += 1

# --- SIDEBAR ---
st.sidebar.header("📂 Table Selection")

# Calculate the index for the dropdown based on our state
try:
    current_index = table_list.index(st.session_state['current_table'])
except ValueError:
    current_index = 0

# We use a unique key every time a button is clicked to force the dropdown to update
selected_table_name = st.sidebar.selectbox(
    "Select a table to explore:", 
    table_list, 
    index=current_index,
    key=f"sb_version_{st.session_state['sb_key_count']}"
)

# Update state if the user manually changes the dropdown
if selected_table_name != st.session_state['current_table']:
    st.session_state['current_table'] = selected_table_name

st.sidebar.divider()

st.sidebar.header("🔍 Research Assistant")
research_query = st.sidebar.text_input("Enter your research idea:", placeholder="e.g. Diabetes adherence")

if research_query:
    st.sidebar.subheader("Suggested Tables")
    matches = [t for t in data if research_query.lower() in t['description'].lower() or research_query.lower() in t['tableName'].lower()]
    
    if matches:
        for m in matches[:10]:
            # Using on_click to trigger our refresh logic
            st.sidebar.button(
                f"📄 {m['tableName']}", 
                key=f"search_{m['tableName']}", 
                on_click=set_table, 
                args=(m['tableName'],)
            )
    else:
        st.sidebar.write("No matches found.")

# --- MAIN AREA ---
st.title("Epic Data Schema Explorer")

# Always use the session_state value for the actual display
table_obj = next((t for t in data if t['tableName'] == st.session_state['current_table']), None)

if table_obj:
    st.header(f"Table: {table_obj['tableName']}")
    if table_obj.get('description'):
        st.info(f"**Description:** {table_obj['description']}")

    tab1, tab2 = st.tabs(["📋 Columns & Keys", "🔗 Relationship Explorer"])

    with tab1:
        if table_obj.get('primaryKey'):
            st.subheader("Primary Keys")
            st.table(pd.DataFrame(table_obj['primaryKey']))

        st.subheader("All Columns")
        col_df = pd.DataFrame(table_obj['columns'])
        if not col_df.empty:
            display_cols = ['name', 'type', 'description', 'isDiscontinued']
            actual_cols = [c for c in display_cols if c in col_df.columns]
            st.dataframe(col_df[actual_cols], use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Tie-back Finder")
        st.write(f"Find tables linked to **{table_obj['tableName']}**")
        
        # Function to find related tables (defined inside main to access data)
        def find_related(col_name):
            related = []
            for t in data:
                if t['tableName'] == st.session_state['current_table']: continue
                if any(c['name'].upper() == col_name.upper() for c in t['columns']):
                    related.append(t['tableName'])
            return sorted(list(set(related)))

        cols_to_check = [c['name'] for c in table_obj['columns']]
        cols_to_check.sort(key=lambda x: ("ID" not in x, x))

        for col_name in cols_to_check:
            related_tables = find_related(col_name)
            if related_tables:
                with st.expander(f"{col_name} (found in {len(related_tables)} other tables)"):
                    r_cols = st.columns(3)
                    for i, r_table in enumerate(related_tables):
                        r_cols[i % 3].button(
                            r_table, 
                            key=f"rel_{col_name}_{r_table}",
                            on_click=set_table,
                            args=(r_table,)
                        )