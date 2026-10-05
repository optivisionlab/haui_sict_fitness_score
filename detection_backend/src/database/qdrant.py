import os
import uuid
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from dotenv import load_dotenv
from typing import List, Union, Literal, Callable
from loguru import logger
from tqdm import tqdm
from PIL import Image
from pathlib import Path

# from src.app.embedding.facenet_embedding import get_embedding
from src.app.embedding.insightface_embedding import get_embedding
from src.config.configs import *
load_dotenv()

class QdrantVectorStore:
    def __init__(
        self,
        url: str = QDRANT_URL,
        collection_name: str = 'face',
        vector_size: int = VECTOR_SIZE,
        api_key: str = QDRANT_API_KEY
    ):
        """
        Initialize Qdrant vector store manager.
        
        Args:
            collection_name (str): Name of the collection
            vector_size (int): Size of the embedding vectors
            qdrant_url (str): URL of the Qdrant server
        """
        self.collection_name = collection_name
        self.vector_size = vector_size
        # Initialize Qdrant client
        logger.debug("Qdrant URL: {}", url)
        self.client = QdrantClient(url=url, 
                                   api_key=api_key)

    def create_collection(self, collection_name:str) -> bool:
        """
        Create a new collection if it doesn't exist.
        
        Returns:
            bool: True if collection was created or already exists
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {collection_name}")
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
    
    def add_vector(self, images: List[Image.Image], collection_name:str = "",get_embedding: Callable = get_embedding, metadata : List[Dict] = None) -> bool:
        """
        Add documents to the collection.
        
        Args:
            documents (List[Dict]): List of documents with text and metadata
            
        Returns:
            bool: True if documents were added successfully
        """
        if not collection_name:
            collection_name = self.collection_name
        try:
            # Create collection if it doesn't exist
            if not self.create_collection(collection_name=collection_name):
                pass
            # Prepare documents for insertion
            points = []
            embeddings,_,b64_faces = get_embedding(images, verbose = False, return_b64=True)

            for data, emb_list, b64_list in zip(metadata, embeddings, b64_faces):
                if emb_list is None:
                    continue

                points = []

                for emb, b64 in zip(emb_list, b64_list):
                    payload = data.copy() 
                    payload['b64'] = b64

                    points.append(
                        models.PointStruct(
                            id=str(uuid.uuid4()),
                            vector=emb,
                            payload=payload
                        )
                    )

                if points:
                    self.client.upsert(
                        collection_name=collection_name,
                        points=points
                    )
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            return False
        
    def search(self, query: Union[Image.Image, List[Image.Image]], collection_name : str = "", k: int = 5, get_embedding: Callable = get_embedding, threshold = None):

        
        query_embeddings, boxes = get_embedding(query)
        query_embeddings = [
            emb.detach().cpu().numpy()[0] if emb is not None else None
            for emb in query_embeddings
        ]

        all_results = []

        for emb, box in zip(query_embeddings, boxes):
            if emb is not None:
                results = self.client.query_points(
                    collection_name=collection_name,
                    query=emb,
                    limit=k,
                    score_threshold=threshold,
                    with_payload=models.PayloadSelectorExclude(exclude=["b64"])
                )
                logger.debug(results)
                all_results.append([results.points, box])
            else:
                all_results.append([])
        return all_results
    
    def get_relevant_faces(self, query: Union[Image.Image, List[Image.Image]], collection_name : str = "", k: int = 5, threshold = 0.65) -> List[Dict]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            
        Returns:
            List[Dict]: List of similar documents with scores
            
        """

        if not collection_name:
            collection_name = self.collection_name
        try:
            # Search for similar vectors
            results = self.search(query, collection_name = collection_name, k = k, threshold = threshold)
            processed_results = []
            for scored_point, box in results:
                if scored_point:
                    for point in scored_point:
                        processed_results.append({
                            "metadata": point.payload,
                            "score": point.score,
                            "bbox" : box[0].tolist()
                        })
                else:
                    processed_results.append({
                            "metadata": {},
                            "score": 0.0
                        })
            
            return processed_results
            
        except Exception as e:
            logger.exception(f"Error searching documents: {str(e)}")
            return [{} for _ in range(len(query))]
    
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
    vector_store = QdrantVectorStore()    
    # input_img = [Image.open(img_path) for img_path in Path("tmp").glob("*")]

    # vector_store.add_vector(input_img, metadata = [{} for _ in range(len(input_img))])

    logger.info(vector_store.get_relevant_faces(
        [Image.open("tmp/ce4f9595-07ab-4956-bce6-f106b8129feb-17360026626361641762035.webp")], 
        k = 1))

if __name__ == "__main__":
    main()