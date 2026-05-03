import streamlit as st
import json
import pandas as pd

st.set_page_config(layout="wide", page_title="Epic Table Pathways")

@st.cache_data
def load_data():
    with open("epic_tables_parsed.json", "r", encoding='utf-8') as f:
        return json.load(f)

data = load_data()

st.title("🤖 RAG Research Model")
st.markdown("""
    Use this model to bridge the gap between **Research Questions** and **Database Schemas**. 
    The model will analyze your query and suggest the most relevant tables and join paths.
""")

# --- INPUT SECTION ---
with st.container(border=True):
    research_query = st.text_area(
        "Describe your research paper or clinical question:",
        placeholder="e.g., 'I want to study the impact of social determinants of health on readmission rates for diabetic patients...'",
        height=150
    )
    
    col1, col2 = st.columns(2)
    with col1:
        granularity = st.select_slider("Search Granularity", options=["Broad", "Balanced", "Specific"])
    with col2:
        top_k = st.number_input("Tables to retrieve", min_value=1, max_value=20, value=5)

    generate_btn = st.button("Analyze Research Path", type="primary", use_container_width=True)

# --- RESULTS SECTION ---
if generate_btn and research_query:
    st.divider()
    
    # This is a placeholder for your RAG logic
    # In a real RAG, you would embed the research_query and search against 
    # the 'description' field of your epic_tables_parsed.json.
    
    st.subheader("📋 Recommended Data Sources")
    
    # Mocking a response for now
    st.info("Analysis complete. Based on your query, here are the suggested tables:")
    
    # Example table suggestions based on keywords
    suggestions = [t for t in data if any(word in t['description'].lower() for word in research_query.lower().split())][:top_k]
    
    if suggestions:
        for table in suggestions:
            with st.expander(f"Table: {table['tableName']}"):
                st.write(f"Relevance:")
                st.write(f"**Description:** \n{table.get('description', 'No description available.')}")
                st.write("**Key Columns:**", ", ".join([c['name'] for c in table['columns'][:5]]))
                if st.button(f"Go to {table['tableName']} explorer", key=f"nav_{table['tableName']}"):
                    st.warning("To navigate back, use the sidebar menu.")
    else:
        st.warning("No direct matches found. Try broadening your research description.")

    st.subheader("🔗 Proposed Join Path")
    st.code("(under development)", language="sql")

else:
    st.info("Enter a research idea above to see the RAG model in action.")