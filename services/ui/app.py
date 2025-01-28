import streamlit as st
from typing import List
import requests

CHATBOT_URL = "http://app:8000"
# CHATBOT_URL = "http://localhost:9000/"


class Collection:
    def __init__(self, name: str, id: str):
        self.name = name
        self.id = id


class Message:
    def __init__(self, message: str, bot: bool):
        self.message = message
        self.bot = bot


# Function to list all collections
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
                    f"{collection.name} (ID: {collection.id})",
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
    print(response.json())
    conversation = [
        Message(
            message=message["content"],
            bot=True if message["role"] == "assistant" else False,
        )
        for message in response.json()["conversation"]
        if message["role"] != "system"
    ]
    st.session_state.conversation = conversation
    user_input = st.text_input("Ask a question:")
    if user_input:
        response = ask(user_input)
    if st.session_state.conversation:
        for message in st.session_state.conversation:
            display_message(message)


def display_message(message: Message):
    if message.bot:
        st.markdown(
            f"""
            <div style='text-align: left;  padding: 10px; border-radius: 10px; margin: 10px 0; background-color: #f6f6f6;  width: 50%;'>
                <strong>Bot:</strong> {message.message}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style='text-align: left; padding: 10px; border-radius: 10px; margin: 10px 0; background-color: #f0f0f0; width: 50%; float: right;'>
                <strong>User:</strong> {message.message}
            </div>
            """,
            unsafe_allow_html=True,
        )


def ask(qst: str) -> list:
    response = requests.post(
        f"{CHATBOT_URL}/ask/{st.session_state.collection.name}",
        json={"question": qst, "conversation_id": st.session_state.collection.name},
    )
    print(response.json())
    if response.status_code == 200:
        conversation = [
            Message(
                message=message["content"],
                bot=True if message["role"] == "assistant" else False,
            )
            for message in response.json()["conversation"]
            if message["role"] != "system"
        ]
        st.session_state.conversation = conversation
    else:
        st.error("Failed to get response")


# Routing
if "collection" in st.session_state:
    chat_page()
else:
    main()
