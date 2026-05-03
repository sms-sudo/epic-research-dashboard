import streamlit as st
import uuid
import os
import json
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- 1. PATH CONFIGURATION ---
PARENT_DIR = os.path.dirname(os.path.dirname(__file__))
STORAGE_FILE = os.path.join(PARENT_DIR, "user_data.json")
INDEX_PATH = os.path.join(PARENT_DIR, "faiss_index_local")
DATA_FILE = os.path.join(PARENT_DIR, "epic_tables_parsed.json")

# --- 2. DATA UTILITIES ---
def load_user_data():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    return {"favorites": [], "history": [], "chat_sessions": {}}

def save_user_data(user_data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(user_data, f)

@st.cache_data
def load_epic_schema():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    return []

# --- 3. OPTIMIZED RAG BACKEND ---
@st.cache_resource
def load_rag_backend():
    embeddings = OllamaEmbeddings(
        model="mxbai-embed-large",
        num_ctx=4096
    )

    if os.path.exists(INDEX_PATH):
        vectorstore = FAISS.load_local(
            INDEX_PATH, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
    else:
        st.error(f"FAISS index not found at {INDEX_PATH}.")
        st.stop()

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    prompt = ChatPromptTemplate.from_template("""
    You are an Epic Database expert. Use the following context to answer.
    Context: {context}
    Question: {question}
    Answer:""")

    # Use llama3:8b or a faster model like phi3 if hardware is limited
    llm = ChatOllama(model="llama3:8b", temperature=0)

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt | llm | StrOutputParser()
    )
    return rag_chain, vectorstore

# --- 4. INITIALIZE ---
user_data = load_user_data()
schema_data = load_epic_schema()
table_descriptions = {t['tableName']: t.get('description', 'No description') for t in schema_data}

if 'current_chat_id' not in st.session_state:
    if user_data["chat_sessions"]:
        st.session_state['current_chat_id'] = list(user_data["chat_sessions"].keys())[0]
    else:
        new_id = str(uuid.uuid4())
        user_data["chat_sessions"][new_id] = {"name": "New Chat", "messages": []}
        st.session_state['current_chat_id'] = new_id

# --- 5. UI: SIDEBAR ---
st.sidebar.header("💬 Chat Sessions")
if st.sidebar.button("➕ New Research Chat", use_container_width=True):
    new_id = str(uuid.uuid4())
    user_data["chat_sessions"][new_id] = {"name": "New Chat", "messages": []}
    st.session_state['current_chat_id'] = new_id
    save_user_data(user_data)
    st.rerun()

for chat_id, info in list(user_data["chat_sessions"].items()):
    cols = st.sidebar.columns([0.8, 0.2])
    if cols[0].button(info["name"], key=f"sel_{chat_id}", 
                      type="primary" if chat_id == st.session_state['current_chat_id'] else "secondary", 
                      use_container_width=True):
        st.session_state['current_chat_id'] = chat_id
        st.rerun()
    if cols[1].button("🗑️", key=f"del_{chat_id}"):
        del user_data["chat_sessions"][chat_id]
        save_user_data(user_data)
        st.rerun()

# --- 6. UI: MAIN CHAT ---
rag_chain, vectorstore = load_rag_backend()
curr_chat = user_data["chat_sessions"][st.session_state['current_chat_id']]

st.title(f"🤖 Research AI: {curr_chat['name']}")

# Display chat history
for message in curr_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "tables" in message and message["tables"]:
            st.write("**Related Tables:**")
            t_cols = st.columns(len(message["tables"]))
            for idx, t_name in enumerate(message["tables"]):
                if t_cols[idx].button(f"🔍 {t_name}", key=f"hist_{t_name}_{idx}", help=table_descriptions.get(t_name)):
                    st.info(f"Navigate to 'Table Explorer' for {t_name}")

# Chat Input & Optimized Generation
if prompt_text := st.chat_input("What clinical data are you looking for?"):
    curr_chat["messages"].append({"role": "user", "content": prompt_text})
    with st.chat_message("user"):
        st.markdown(prompt_text)

    with st.chat_message("assistant"):
        # 1. Faster retrieval step (run separately to get table names immediately)
        related_docs = vectorstore.similarity_search(prompt_text, k=3)
        top_matches = [doc.metadata['name'] for doc in related_docs]
        
        # 2. Optimized Streaming Response
        response_placeholder = st.empty()
        full_response = ""
        
        # Using .stream() instead of .invoke() for immediate visual feedback
        for chunk in rag_chain.stream(prompt_text):
            full_response += chunk
            response_placeholder.markdown(full_response + "▌")
        
        response_placeholder.markdown(full_response)
        
        # 3. Display table buttons after text generation starts
        if top_matches:
            st.write("**Suggested Tables:**")
            btn_cols = st.columns(len(top_matches))
            for i, t_name in enumerate(top_matches):
                btn_cols[i].button(f"🔍 {t_name}", key=f"res_{t_name}_{uuid.uuid4()}", help=table_descriptions.get(t_name))

    # Save to session and file
    curr_chat["messages"].append({"role": "assistant", "content": full_response, "tables": top_matches})
    if len(curr_chat["messages"]) <= 2:
        curr_chat["name"] = prompt_text[:30] + "..." if len(prompt_text) > 30 else prompt_text
        
    save_user_data(user_data)
    st.rerun()