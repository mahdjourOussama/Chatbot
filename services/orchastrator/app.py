"""Main FastAPI application. manages the conversation between the user and the ai assistant."""

import logging
from typing import List
import json
import redis
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

r = redis.Redis(host="redis", port=6379, db=0)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RETRIVAL_SERVICE_URL = "http://retrieval:8000"
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
            return {"error": "Conversation not found"}
    except Exception as e:
        logger.error("Error retrieving conversation %s", e)
        return {"error": e}


class postConversationModel(BaseModel):
    conversation_id: str
    questoin: str


class postConversationResponseModel(BaseModel):
    conversation_id: str
    answer: str


@app.post("/ask/{conversation_id}")
async def post_conversation(
    request: postConversationModel,
) -> postConversationResponseModel:
    """Send the conversation to the AI model and return the response."""
    conversation_id, question = request.conversation_id, request.questoin
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

        response = requests.post(
            f"{AI_SERVICE_URL}/ask/{conversation_id}",
            json={
                "conversation_id": conversation_id,
                "question": question,
            },
            timeout=10,
        )
        response.raise_for_status()
        assistant_message = response.json()["answer"]

        existing_conversation["conversation"].append(
            {"role": "assistant", "content": assistant_message}
        )

        r.set(conversation_id, json.dumps(existing_conversation))

        return postConversationResponseModel(
            conversation_id=conversation_id,
            response=assistant_message,
        )
    except Exception as e:
        logger.error("Error processing conversation %s", e)
        return {"error": e}


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the chatbot service",
        "description": "This service is responsible for managing chatbot conversations",
    }


class UploadRequest(BaseModel):
    """Request model for uploading files."""

    files: List[UploadFile]


class UploadResponse(BaseModel):
    """Response model for uploading files."""

    collections: List[str]


@app.post("/upload")
def uploadFiles(request: UploadRequest):
    """Upload files to the service."""
    try:
        # Create a new collection
        collections = []
        for file in request.files:
            response = requests.post(
                f"{RETRIVAL_SERVICE_URL}/upload_document/", json={"file": file}
            )
            collections._SERVICEappend(response.json().get("collection_id"))
        return
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        return {"error": str(e)}
