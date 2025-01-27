"""This Service contains the FastAPI application that will be used to serve the AI model.
It will accept a conversation and return the response from the AI model."""

import os
import logging
from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests
from dotenv import find_dotenv, load_dotenv


# service setup
load_dotenv(find_dotenv())

RETRIVAL_SERVICE_URL = (
    os.getenv("RETRIVAL_SERVICE_URL")
    if os.getenv("RETRIVAL_SERVICE_URL")
    else "http://retrieval:8000"
)
LLM_SERVICE_URL = (
    os.getenv("LLM_SERVICE_URL") if os.getenv("LLM_SERVICE_URL") else "http://llm:8000"
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def format_docs(docs) -> str:
    """Format the documents for the AI model."""
    formatted_docs = []
    for doc in docs:
        formatted_docs.append(doc["page_content"])
    return "\n".join(formatted_docs)


# Define a function to answer queries
def answer_question(question, docs) -> str:
    try:
        context = f"""You are an AI assistant with access to a collection of relevant documents. 
Use the following information to provide accurate and helpful responses to user questions:
<docs>
{docs}
</docs>
Based on the above information, please provide the most suitable and detailed response to the following user's question.
<question>
{question}
</question>
"""

        generate_payload = {"model": "gemma:2b", "prompt": context, "stream": False}
        response = requests.post(
            f"{LLM_SERVICE_URL}/api/generate", json=generate_payload
        )
        response.raise_for_status()
        output = response.json()
        # Return the response
        return output["response"]
    except Exception as e:
        logger.error(f"Error answering question: {question}")
        logger.error(e)
        return "I am sorry, There was an error processing your request"


@app.get("/")
async def root():
    """Root endpoint for the AI service."""
    return {"message": "Welcome to the AI service!"}


class ChatRequestModel(BaseModel):
    """Chat conversation model for the AI assistant."""

    conversation_id: str
    question: str


class ChatResponseModel(BaseModel):
    """Chat response model for the AI assistant."""

    conversation_id: str
    reply: str
    query: str
    context: str


@app.post("/ask/{conversation_id}")
async def chat_conversation(request: ChatRequestModel):
    """Send a conversation to the AI model and return the response."""
    try:
        conversation_id, query = request.conversation_id, request.question

        docs = requests.post(
            f"{RETRIVAL_SERVICE_URL}/retrieve_document/",
            json={"query": query, "collection_id": conversation_id},
        ).json()["documents"]

        docs = format_docs(docs=docs)

        answer = answer_question(query, docs)

        return ChatResponseModel(
            conversation_id=conversation_id, reply=answer, query=query, context=docs
        )
    except Exception as e:
        logger.error(f"Error processing conversation: {conversation_id}")
        logger.error(e)
        return {"error": str(e)}
