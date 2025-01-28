"""Main FastAPI application. manages the conversation between the user and the ai assistant."""

import logging
from typing import List
import json
import redis
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

r = redis.Redis(host="redis", port=6379, db=0)

app = FastAPI(
    title="Chatbot Service",
    description="This service is responsible for managing chatbot conversations",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RETRIVAL_SERVICE_URL = "http://retrival:8000"
AI_SERVICE_URL = "http://ai:8000"


class Message(BaseModel):
    """Message model for the conversation."""

    role: str
    content: str


class Conversation(BaseModel):
    """Conversation model for the chatbot."""

    conversation: List[Message]


@app.get("/collectionChat/{conversation_id}")
async def get_conversation(conversation_id: str) -> Conversation:
    """Get the conversation from the Redis store."""
    try:
        logger.info("Retrieving initial id %s", conversation_id)
        existing_conversation_json = r.get(conversation_id)
        if existing_conversation_json:
            existing_conversation = json.loads(existing_conversation_json)  # type: ignore
            return existing_conversation
        else:
            return Conversation(
                conversation=[
                    {"role": "assistant", "content": "hi how can i help you?"}
                ]
            )
    except Exception as e:
        logger.error("Error retrieving conversation %s", e)
        return {"error": e}


class postConversationModel(BaseModel):
    conversation_id: str
    question: str


@app.post("/ask/{conversation_id}")
async def post_conversation(
    request: postConversationModel,
) -> Conversation:
    """Send the conversation to the AI model and return the response."""
    conversation_id, question = request.conversation_id, request.question
    logger.info("Sending Conversation with ID %s to ", conversation_id)
    try:
        existing_conversation_json = r.get(conversation_id)
        if existing_conversation_json:
            existing_conversation = json.loads(existing_conversation_json)  # type: ignore
        else:
            existing_conversation = {
                "conversation": [
                    {"role": "system", "content": "You are a helpful assistant."}
                ]
            }

        existing_conversation["conversation"].append(
            {"role": "user", "content": question}
        )
        docs = requests.post(
            f"{RETRIVAL_SERVICE_URL}/retrieve_document/",
            json={"query": question, "collection_id": conversation_id},
        ).json()["documents"]
        docs = format_docs(docs=docs)

        response = requests.post(
            f"{AI_SERVICE_URL}/ask/{conversation_id}",
            json={
                "conversation_id": conversation_id,
                "question": question,
                "docs": docs,
            },
        )
        response.raise_for_status()
        assistant_message = response.json()["answer"]

        existing_conversation["conversation"].append(
            {"role": "assistant", "content": assistant_message}
        )

        r.set(conversation_id, json.dumps(existing_conversation))

        return existing_conversation
    except Exception as e:
        logger.error("Error processing conversation %s", e)
        return {"error": e}


def format_docs(docs) -> str:
    """Format the documents for the AI model."""
    formatted_docs = []
    for doc in docs:
        formatted_docs.append(doc["page_content"])
    return "\n".join(formatted_docs)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the chatbot service",
        "description": "This service is responsible for managing chatbot conversations",
    }


class UploadResponse(BaseModel):
    """Response model for uploading files."""

    collections: List[str]


@app.post("/upload")
def uploadFiles(files: List[UploadFile] = File(...)) -> UploadResponse:
    """Upload files to the service."""
    try:
        # Create a new collection
        collections = []
        for file in files:
            if not file.filename.endswith(".txt"):
                return {"error": "Only .txt files are allowed", collections: []}

            logger.info("Uploading file %s", file.filename)
            with file.file as file_content:
                collection_id = file.filename if file.filename else str(uuid4())
                payload = {
                    "collection_id": collection_id,
                    "document_text": file_content.read().decode("utf-8"),
                }
                response = requests.post(
                    f"{RETRIVAL_SERVICE_URL}/save_document/",
                    json=payload,
                )
                response.raise_for_status()  # Ensure the request succeeded
                collections.append(response.json().get("collection_id"))
        return UploadResponse(collections=collections)
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        return {"error": str(e), "collections": []}


@app.get("/collections")
def list_collections():
    """List all collections."""
    try:
        response = requests.get(f"{RETRIVAL_SERVICE_URL}/collections/")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        return {"error": str(e)}
