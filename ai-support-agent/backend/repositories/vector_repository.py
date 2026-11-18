"""
repositories/vector_repository.py — ChromaDB Vector Store Access Object
=========================================================================

VectorRepository is the single source of truth for all interactions with
the ChromaDB persistent vector database. Services and RAG pipeline functions
call this class; they never import chromadb directly.

Why a class here:
    VectorRepository holds two pieces of instance state: the ChromaDB client
    and the cached collection reference. Managing lazy-loading and singleton
    caching of the collection inside a class is far cleaner than module-level
    globals. It also makes swapping the vector store (e.g., to Pinecone or
    Weaviate) a matter of creating an alternative class with the same interface.
"""

from typing import Any, Dict, List, Optional

import chromadb

from core.logger import get_logger

logger = get_logger(__name__)


class VectorRepository:
    """
    Data access layer for the ChromaDB vector database.

    Manages client creation, collection caching, and all CRUD operations
    against the vector index.

    Attributes:
        chroma_db_path   (str): File-system path for ChromaDB persistent storage.
        collection_name  (str): Name of the ChromaDB collection to use.
    """

    def __init__(self, chroma_db_path: str, collection_name: str) -> None:
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    # ------------------------------------------------------------------
    # Collection access (lazy + cached)
    # ------------------------------------------------------------------

    def _get_client(self) -> chromadb.PersistentClient:
        """Return the shared ChromaDB client, creating it on first call."""
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self.chroma_db_path)
        return self._client

    def get_collection(self):
        """
        Return the cached ChromaDB collection, loading it on first access.

        Returns:
            chromadb.Collection: The active collection for similarity search.

        Raises:
            Exception: If the collection has not been populated yet.
        """
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_collection(name=self.collection_name)
            logger.info(
                "ChromaDB collection '%s' loaded (%d documents).",
                self.collection_name,
                self._collection.count(),
            )
        return self._collection

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def clear_and_create(self):
        """
        Drop the existing collection (if present) and create a fresh one.

        Used by the RAG indexing pipeline when rebuilding the knowledge base.

        Returns:
            chromadb.Collection: A new, empty collection ready for ingestion.
        """
        client = self._get_client()

        try:
            client.delete_collection(name=self.collection_name)
            logger.info("Cleared existing ChromaDB collection: %s", self.collection_name)
        except Exception:
            logger.debug("Collection '%s' did not exist; creating fresh.", self.collection_name)

        self._collection = client.create_collection(name=self.collection_name)
        return self._collection

    def store(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """
        Batch-insert documents, embeddings, and metadata into the collection.

        Args:
            ids        (List[str])              : Unique string ID for each document chunk.
            documents  (List[str])              : Raw text for each chunk.
            embeddings (List[List[float]])      : Pre-computed embedding vectors.
            metadatas  (List[Dict[str, Any]])   : Metadata dicts (source, page, etc.).

        Raises:
            Exception: If the ChromaDB write fails.
        """
        collection = self.get_collection()
        logger.info("Writing %d vectors to ChromaDB collection '%s'.", len(ids), self.collection_name)

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(
            "Vector store populated. Total indexed records: %d", collection.count()
        )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector: List[float],
        n_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Run an approximate nearest-neighbour similarity search.

        Args:
            query_vector (List[float]) : The embedding of the search query.
            n_results    (int)         : Number of top matches to return.

        Returns:
            List[Dict[str, Any]]: Matched chunks, each with:
                - ``id``       (str)  : Chunk identifier.
                - ``text``     (str)  : Raw chunk text.
                - ``metadata`` (dict) : Source metadata.
                - ``distance`` (float): Similarity distance (lower = closer).
        """
        collection = self.get_collection()

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=n_results,
        )

        records: List[Dict[str, Any]] = []
        if results and results.get("documents"):
            for i in range(len(results["ids"][0])):
                records.append({
                    "id":       results["ids"][0][i],
                    "text":     results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0.0,
                })

        logger.info("Vector search returned %d result(s).", len(records))
        return records
