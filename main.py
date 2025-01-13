import os
import json
import gc

import streamlit as st
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_chroma import Chroma

from vectorize_documents import embeddings, get_pdf_text, get_text_chunks, get_vector_store

working_dir = os.path.dirname(os.path.abspath(__file__))
config_data = json.load(open(f"{working_dir}/config.json"))
GROQ_API_KEY = config_data["GROQ_API_KEY"]
os.environ["GROQ_API_KEY"] = GROQ_API_KEY


def setup_vectorstore():
    persist_directory = f"{working_dir}/vector_db_dir"
    vectorstore = Chroma(persist_directory=persist_directory,
                         embedding_function=embeddings)
    return vectorstore


def chat_chain(vectorstore):
    llm = ChatGroq(model="llama3-70b-8192",
                   temperature=0.4)
    retriever = vectorstore.as_retriever()
    memory = ConversationBufferMemory(
        llm=llm,
        output_key="answer",
        memory_key="chat_history",
        return_messages=True
    )
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        memory=memory,
        verbose=True,
        return_source_documents=True
    )

    return chain

# Fallback function using GROQ API
def fallback_response(user_input):
    # Initialize the GROQ API Chat model
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.4)
    
    # Generate response using GROQ API
    response = llm({"question": user_input})
    
    return response["answer"]

def reset_chat():
    st.session_state.messages = []
    gc.collect()

st.set_page_config(
    page_title="Multi Doc Chat",
    page_icon = "📚",
    layout="centered"
)

st.title("📚 Multi Documents Chatbot")
with st.sidebar:        
    st.title("📁 PDF File's Section")
    pdf_docs = st.file_uploader("Upload your PDF Files & \n Click on the Submit & Process Button ", accept_multiple_files=True)
    if st.button("Submit & Process"):
        with st.spinner("Processing..."): # user friendly message.
            raw_text = get_pdf_text(pdf_docs) # get the pdf text
            text_chunks = get_text_chunks(raw_text) # get the text chunks
            get_vector_store(text_chunks) # create vector store
            st.success("Done")

    st.button("Clear Chat", on_click=reset_chat)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = setup_vectorstore()

if "conversationsal_chain" not in st.session_state:
    st.session_state.conversationsal_chain = chat_chain(st.session_state.vectorstore)
def reset_chat():
    st.session_state.messages = []
    gc.collect()


for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("Ask AI...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
      
    
    with st.chat_message("user"):
        st.markdown(user_input)


    with st.chat_message("assistant"):
        response = st.session_state.conversationsal_chain({"question": user_input})
        assistant_response = response["answer"]
        if not assistant_response or assistant_response.strip() == "":
            # Fallback to GROQ API response
            assistant_response = fallback_response(user_input)

        st.markdown(assistant_response)
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})

