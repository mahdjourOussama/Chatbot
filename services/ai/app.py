"""This Service contains the FastAPI application that will be used to serve the AI model.
It will accept a conversation and return the response from the AI model."""

import logging
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests
from dotenv import find_dotenv, load_dotenv


# service setup
load_dotenv(find_dotenv())

LLM_SERVICE_URL = "http://llm:11434"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="AI Service",
    description="This service is responsible for generating answers to user questions",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    question: str
    docs: str


class ChatResponseModel(BaseModel):
    """Chat response model for the AI assistant."""

    answer: str
    query: str


@app.post("/ask/{conversation_id}")
async def chat_conversation(request: ChatRequestModel):
    """Send a conversation to the AI model and return the response."""
    try:
        query, docs = request.question, request.docs
        logger.info("Sending conversation with ID  to AI model")

        answer = answer_question(query, docs)

        return ChatResponseModel(answer=answer, query=query)

    except Exception as e:
        logger.error("Error processing conversation: ")
        logger.error(e)
        return {"error": str(e)}
