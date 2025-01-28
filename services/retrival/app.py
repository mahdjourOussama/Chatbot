"""
this service is responsible for managing documents
this service contain two main functions:
1- save_document: this function is responsible for uploading and update the document into the database
3- retrieve_document: this function is responsible for retrieving the document from the database
"""

import os
from typing import List, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document

from fastapi import FastAPI, UploadFile, File
from sqlalchemy import create_engine, Column, String, JSON, Uuid
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware
from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel
from uuid import uuid4
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)
# Load environment variables
load_dotenv(find_dotenv())
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = "database"
POSTGRES_PORT = POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")


CONNECTION_STRING = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# setup the FastAPI app
app = FastAPI(
    title="Document Management Service",
    description="This service is responsible for managing documents",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the path to the pre-trained model
modelPath = "BAAI/bge-small-en-v1.5"

# Create a dictionary with model configuration options, specifying to use the CPU for computations
model_kwargs = {"device": "cpu"}
# Create a dictionary with encoding options, specifically setting 'normalize_embeddings' to False
encode_kwargs = {"normalize_embeddings": True}

# Initialize an instance of HuggingFaceEmbeddings with the specified parameters
embeddings = HuggingFaceEmbeddings(
    model_name=modelPath,  # Provide the pre-trained model's path
    model_kwargs=model_kwargs,  # Pass the model configuration options
    encode_kwargs=encode_kwargs,  # Pass the encoding options
)


class UpdateCollectionRequest(BaseModel):
    """Request model for updating a collection."""

    collection_id: Optional[str]
    document_text: str


class UpdateCollectionResponse(BaseModel):
    """Response model for updating a collection."""

    document_ids: List[str]
    collection_id: str


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the document management service",
        "description": "This service is responsible for managing documents",
    }


@app.post("/save_document")
def save_document(request: UpdateCollectionRequest):
    """Update a document in the database."""
    collection_id = request.collection_id or str(uuid4())
    documents = text_to_documents(request.document_text, {"file": collection_id})
    try:
        logger.info("Updating collection %s", collection_id)
        store = PGVector(
            embeddings=embeddings,
            collection_name=collection_id,
            connection=CONNECTION_STRING,
            use_jsonb=True,
        )
        retriever = store.as_retriever()
        documents_id = retriever.add_documents(documents)
        return UpdateCollectionResponse(
            document_ids=documents_id, collection_id=collection_id
        )

    except Exception as e:
        logger.error(f"Error updating collection: {collection_id}")
        logger.debug(f"connection string: {CONNECTION_STRING}")
        logger.error(e)
        return {
            "error": str(e),
        }


class RetriveDocumentRequest(BaseModel):
    """Request model for retrieving a document."""

    collection_id: str
    query: str


class RetriveDocumentResponse(BaseModel):
    """Response model for retrieving a document."""

    documents: List[Document]


@app.post("/retrieve_document")
def retrieve_document(request: RetriveDocumentRequest) -> RetriveDocumentResponse:
    """Retrieve a document from the database."""
    try:
        logger.info("Retrieving document %s", request.collection_id)
        store = PGVector(
            embeddings=embeddings,
            collection_name=request.collection_id,
            connection=CONNECTION_STRING,
            use_jsonb=True,
        )
        retriever = store.as_retriever()
        return RetriveDocumentResponse(documents=retriever.invoke(input=request.query))
    except Exception as e:
        logger.error(f"Error retrieving document: {request.collection_id}")
        logger.debug(f"connection string: {CONNECTION_STRING}")
        logger.error(e)
        return {
            "error": str(e),
        }


def text_to_documents(text: str, metadata: dict) -> List[Document]:
    """Convert text into a list of Document objects."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_text(text)
    return [
        Document(
            page_content=t,
            metadata={"chunk_id": idx, "total_chunks": len(texts), **metadata},
        )
        for idx, t in enumerate(texts)
    ]


def parseUploadFile(file_content: bytes) -> List[Document]:
    """Parse the content of an uploaded file into a list of Document objects."""
    logger.info("Parsing uploaded file")
    text = file_content.decode("utf-8")
    return text_to_documents(text, {})


@app.post("/upload_document")
async def upload_document(file: UploadFile = File(...)):
    """Upload a text file and save its content as documents in the database."""
    try:
        content = await file.read()
        documents = parseUploadFile(content)
        collection_id = file.filename or str(uuid4())
        logger.info("Uploading document %s", collection_id)
        store = PGVector(
            embeddings=embeddings,
            collection_name=collection_id,
            connection=CONNECTION_STRING,
            use_jsonb=True,
        )
        retriever = store.as_retriever()
        documents_id = retriever.add_documents(documents)
        return UpdateCollectionResponse(
            document_ids=documents_id, collection_id=collection_id
        )
    except Exception as e:
        logger.error("Error uploading document")
        logger.debug(f"connection string: {CONNECTION_STRING}")
        logger.error(e)
        return {
            "error": str(e),
        }


# Setup SQLAlchemy
Base = declarative_base()


class langchain_pg_collection(Base):
    __tablename__ = "langchain_pg_collection"
    uuid = Column(Uuid, primary_key=True, index=True)
    name = Column(String, index=True)
    cmetadata = Column(JSON)

    def __repr__(self):
        return f"<Collection {self.name}>"


try:
    engine = create_engine(CONNECTION_STRING)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error("Error creating tables")
    logger.debug(f"connection string: {CONNECTION_STRING}")
    logger.error(e)


class Collection(BaseModel):
    id: str
    name: str


@app.get("/collections")
def get_collections() -> List[Collection]:
    try:
        logger.info("Retrieving collections")
        db = SessionLocal()
        collections = db.query(langchain_pg_collection).all()
        return [
            Collection(
                id=str(collection.uuid),
                name=collection.name,
            )
            for collection in collections
        ]
    except Exception as e:
        logger.error("Error retrieving collections")
        logger.debug(f"connection string: {CONNECTION_STRING}")
        logger.error(e)
        return {
            "error": str(e),
        }
    finally:
        db.close()
