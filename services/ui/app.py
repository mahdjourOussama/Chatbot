import streamlit as st
import os
from typing import List
import requests

CHATBOT_URL = "http://localhost:8000"


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
    collections: List[Collection] = [
        Collection(name=f"collection{i}", id=f"id_{i}") for i in range(1, 8)
    ]
    return collections


# Main page
def main():
    st.title("Chatbot Collections")

    collections = list_collections()
    upload_files()
    if collections:
        st.subheader("Existing Collections")
        cols = st.columns(4)
        for index, collection in enumerate(collections):
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
        "Upload txt files", type="txt", accept_multiple_files=True
    )
    if uploaded_files:
        os.makedirs("collections", exist_ok=True)
        for uploaded_file in uploaded_files:
            with open(os.path.join("collections", uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())
        st.success("Files uploaded successfully")

        # Send files to backend
        files = [
            ("files", (file.name, file.getvalue(), "text/plain"))
            for file in uploaded_files
        ]
        response = requests.post(f"{CHATBOT_URL}/upload/", files=files)

        if response.status_code == 200:
            st.session_state.collections = response.json().get("collections", [])
            st.success("Collections created successfully")
        else:
            st.error("Failed to create collections")


# Chat page
def chat_page():
    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
    with col1:
        st.title(f"Chat with {st.session_state.collection.name}")
    with col2:
        st.button(
            "Back to collections", on_click=lambda: st.session_state.pop("collection")
        )
    conversation = [
        Message("Hello, how can I help you?", bot=True),
    ]
    user_input = st.text_input("Ask a question:")
    if user_input:
        conversation.append(Message(user_input, bot=False))
        response = ask(user_input)
        conversation.append(response)
    for message in conversation:
        display_message(message)


def display_message(message: Message):
    if message.bot:
        st.markdown(
            f"""
            <div style='text-align: left;  padding: 10px; border-radius: 10px; margin: 10px 0;'>
                <strong>Bot:</strong> {message.message}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style='text-align: right; padding: 10px; border-radius: 10px; margin: 10px 0;'>
                {message.message}
            </div>
            """,
            unsafe_allow_html=True,
        )


def ask(qst: str) -> Message:
    response = requests.post(
        f"{CHATBOT_URL}/ask/{st.session_state.collection.id}",
        json={"question": qst, "collection_id": st.session_state.collection.id},
    )
    if response.status_code == 200:
        bot_response = Message(
            response.json().get("answer", "I'm sorry, I don't understand"), bot=True
        )
    else:
        bot_response = Message("Failed to get response from backend", bot=True)
    return bot_response


# Routing
if "collection" in st.session_state:
    chat_page()
else:
    main()
