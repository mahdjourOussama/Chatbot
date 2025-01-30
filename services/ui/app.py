import streamlit as st
from typing import List
import requests
import time

CHATBOT_URL = "http://app:8000"
# CHATBOT_URL = "http://localhost:9000/"


class Collection:
    def __init__(self, name: str, id: str):
        self.name = name
        self.id = id


def list_collections() -> List[Collection]:
    try:
        response = requests.get(f"{CHATBOT_URL}/collections")
        if response.status_code == 200:
            collections = [
                Collection(name=collection["name"], id=collection["id"])
                for collection in response.json()
            ]
        else:
            collections = []
        return collections
    except Exception as e:
        st.error(f"Error listing collections: {e}")
        return []


# Main page
def main():
    st.title("Chatbot Collections")

    st.session_state.collections = list_collections()
    upload_files()
    if st.session_state.collections:
        st.subheader("Existing Collections")
        cols = st.columns(4)
        for index, collection in enumerate(st.session_state.collections):
            col = cols[index % 4]
            with col:
                st.button(
                    f"{collection.name}",
                    key=collection.id,
                    on_click=lambda c=collection: st.session_state.update(
                        {"collection": c}
                    ),
                )

    else:
        st.subheader("No collections found")


def upload_files():
    uploaded_files = st.file_uploader(
        "Upload txt files", type="txt", accept_multiple_files=False
    )
    if uploaded_files:
        files = [
            ("files", (uploaded_files.name, uploaded_files.getvalue(), "text/plain"))
        ]
        try:
            response = requests.post(f"{CHATBOT_URL}/upload/", files=files)
            if response.status_code == 200:
                st.session_state.collections = list_collections()
                st.success("Collections created successfully")
            else:
                st.error("Failed to create collections")
        except Exception as e:
            st.error(f"Error uploading files: {e}")


# Chat page
def chat_page():
    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
    with col1:
        st.title(f"Chat with {st.session_state.collection.name}")
    with col2:
        st.button(
            "Back to collections", on_click=lambda: st.session_state.pop("collection")
        )
    response = requests.get(
        f"{CHATBOT_URL}/collectionChat/{st.session_state.collection.name}"
    )
    conversation = [
        message
        for message in response.json()["conversation"]
        if message["role"] != "system"
    ]
    st.session_state.conversation = conversation
    if st.session_state.conversation:
        chat_container = st.container(border=True, height=450)
        with chat_container:
            for idx, message in enumerate(st.session_state.conversation):
                with st.chat_message(message["role"]):
                    if idx == len(st.session_state.conversation) - 1:
                        st.write_stream(stream_response(message["content"]))
                    else:
                        st.markdown(message["content"])
    st.text_input("Ask a question:", key="user_input", on_change=ask)


def ask():
    with st.spinner("Analyzing... Please wait..."):
        qst = st.session_state.user_input
        response = requests.post(
            f"{CHATBOT_URL}/ask/{st.session_state.collection.name}",
            json={"question": qst, "conversation_id": st.session_state.collection.name},
        )
        if response.status_code == 200:
            bot_response = response.json()
            st.session_state.conversation.append(bot_response)
            st.session_state.user_input = ""
        else:
            st.error("Failed to get response")


def stream_response(response):
    for word in response.split():
        yield word + " "
        time.sleep(0.05)


# Routing
if "collection" in st.session_state:
    chat_page()
else:
    main()
