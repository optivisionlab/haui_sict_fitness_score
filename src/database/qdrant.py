import os
import uuid
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
from typing import List, Union, Literal
from sentence_transformers import SentenceTransformer
from loguru import logger
import requests
from src.config.configs import *
from tqdm import tqdm
load_dotenv()

class QdrantVectorStore:
    def __init__(
        self,
        collection_name: str,
    ):
        """
        Initialize Qdrant vector store manager.
        
        Args:
            collection_name (str): Name of the collection
            vector_size (int): Size of the embedding vectors
            qdrant_url (str): URL of the Qdrant server
        """
        self.collection_name = collection_name
        self.vector_size = os.getenv("vector_size", 768)
        # Initialize Qdrant client
        self.client = QdrantClient(url=QDRANT_URL)

    def create_collection(self) -> bool:
        """
        Create a new collection if it doesn't exist.
        
        Returns:
            bool: True if collection was created or already exists
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            return False
    
    def delete_collection(self) -> bool:
        """
        Delete the collection if it exists.
        
        Returns:
            bool: True if collection was deleted or didn't exist
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if self.collection_name in collection_names:
                self.client.delete_collection(collection_name=self.collection_name)
                logger.info(f"Deleted collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} does not exist")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            return False
    
    def add_documents(self, documents: List[Document], get_embedding: function) -> bool:
        """
        Add documents to the collection.
        
        Args:
            documents (List[Dict]): List of documents with text and metadata
            
        Returns:
            bool: True if documents were added successfully
        """
        try:
            # Create collection if it doesn't exist
            if not self.create_collection():
                pass
            # Prepare documents for insertion
            points = []
            embeddings = get_embedding([doc.page_content for doc in documents])
            for doc, emb in zip(documents, embeddings):
                # Generate embedding for the document text
                # Create point with embedding and metadata
                point = models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb,
                    payload={
                        "text": doc.page_content,
                        "metadata": doc.metadata
                    }
                )
                points.append(point)
            
            # Upload points to collection
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            return False
        
    def search(self, query: str, k: int = 5, get_embedding: function = None):
        query_embedding = get_embedding([query], 'local')[0]

        # Search for similar vectors
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=k
        )
        return results
    
    def get_relevant_documents(self, query: str, k: int = 5) -> List[Dict]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            
        Returns:
            List[Dict]: List of similar documents with scores
        """
        try:
            # Search for similar vectors
            results = self.search(query, k)
            processed_results = []
            for scored_point in results:
                processed_results.append({
                    "text": scored_point.payload["text"],
                    "metadata": scored_point.payload.get("metadata", {}),
                    "score": scored_point.score
                })
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
    
    def get_collection_info(self) -> Dict:
        """
        Get information about the collection.
        
        Returns:
            Dict: Collection information
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": collection_info.name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {}

    def insert_points(self, text:str, metadata:dict ,emb:list):
        point = models.PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload={
                    "text": text,
                    "metadata": metadata
                }
                )
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

def main():
    # Example usage
    embeddings = GoogleGenerativeAIEmbeddings(
            model=os.getenv("embedding_model", "models/embedding-001"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            task_type = "RETRIEVAL_QUERY"
        )
    vector_store = QdrantVectorStore(collection_name="thue", embeddings=embeddings)    

    # Search for similar documents
    query = "Thông tin các khoản chịu thuế"
    results = vector_store.get_relevant_documents(query, k=10)
    
    logger.info("\nSearch Results:")
    for i, result in enumerate(results, 1):
        logger.info(f"\n{i}. Score: {result['score']:.4f}")
        logger.info(f"Text: {result['text']}")
        logger.info(f"Metadata: {result['metadata']}")

if __name__ == "__main__":
    main()