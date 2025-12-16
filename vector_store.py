"""
Vector Store Management Module
Handles document indexing and retrieval
embedding后向量存储 检索的基础

检索器的创建
"""
import hashlib
from typing import List, Optional
from pathlib import Path
from langchain.indexes import SQLRecordManager
from langchain.retrievers import (
    ContextualCompressionRetriever, 
    EnsembleRetriever
)
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.indexing import index
from langchain_core.embeddings import Embeddings
from loguru import logger

from config import VectorStoreConfig, RetrievalConfig


class VectorStoreManager:
    """
    Manages vector stores for document collections
    Handles indexing, retrieval, and search operations
    """
    
    def __init__(self, config: VectorStoreConfig, embeddings: Embeddings):
        """
        Initialize vector store manager
        
        Args:
            config: Vector store configuration
            embeddings: Embedding model instance
        """
        self.config = config
        self.embeddings = embeddings
        self.stores = {}
        
    def create_collection(self, collection_id: str, documents: List[Document]) -> Chroma:
        """
        Create or update a vector store collection
        向量存储集合
        Args:
            collection_id: Unique collection identifier
            documents: Documents to index
            
        Returns:
            Chroma vector store instance
        """
        logger.info(f"Creating collection: {collection_id}")
        
        # Initialize vector store
        # 1. 创建存储目录
        persist_dir = Path(self.config.persist_directory) / collection_id
        persist_dir.mkdir(parents=True, exist_ok=True)

        # 2. 初始化Chroma向量数据库，创建一个空的向量数据库实例
        vector_store = Chroma(
            collection_name=collection_id,
            embedding_function=self.embeddings,
            persist_directory=str(persist_dir)
        )
        
        # Setup record manager for deduplication
        # 3. 设置记录管理器（去重）
        record_manager = SQLRecordManager(
            f"chroma/{collection_id}",
            db_url="sqlite:///./record_manager.db"
        )
        record_manager.create_schema()
        
        # Index documents
        # 4. 索引文档，把文档 先embedding →再 存入数据库
        # 此处为实际的embedding处
        result = index(
            documents, # 要索引的文档
            record_manager,  #记录管理器，追踪已索引的文档避免重复索引支持增量更新
            vector_store, # 向量存储
            cleanup="full", # 清理策略：完全替换
            source_id_key="source"
        )
        
        logger.info(f"Indexing result: {result}")
        
        self.stores[collection_id] = vector_store
        return vector_store
    
    def get_collection(self, collection_id: str) -> Optional[Chroma]:
        """
        Get existing collection
        
        Args:
            collection_id: Collection identifier
            
        Returns:
            Chroma instance or None
        """
        if collection_id in self.stores:
            return self.stores[collection_id]
        
        persist_dir = Path(self.config.persist_directory) / collection_id
        if not persist_dir.exists():
            logger.warning(f"Collection {collection_id} does not exist")
            return None
        
        vector_store = Chroma(
            collection_name=collection_id,
            embedding_function=self.embeddings,
            persist_directory=str(persist_dir)
        )
        
        self.stores[collection_id] = vector_store
        return vector_store
    
    def delete_collection(self, collection_id: str) -> bool:
        """
        Delete a collection
        
        Args:
            collection_id: Collection to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            if collection_id in self.stores:
                del self.stores[collection_id]
            
            persist_dir = Path(self.config.persist_directory) / collection_id
            if persist_dir.exists():
                import shutil
                shutil.rmtree(persist_dir)
            
            logger.info(f"Collection {collection_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """
        List all available collections
        
        Returns:
            List of collection IDs
        """
        base_dir = Path(self.config.persist_directory)
        if not base_dir.exists():
            return []
        
        return [d.name for d in base_dir.iterdir() if d.is_dir()]


class RetrieverFactory:
    """
    Factory for creating different types of retrievers
    """
    
    def __init__(self, config: RetrievalConfig):
        """
        Initialize retriever factory
        
        Args:
            config: Retrieval configuration
        """
        self.config = config
    
    def create_hybrid_retriever(#混合检索
        self, 
        vector_store: Chroma, 
        documents: List[Document]
    ) -> EnsembleRetriever:
        """
        Create hybrid retriever combining dense and sparse search
        
        Args:
            vector_store: Vector store for dense retrieval
            documents: Documents for BM25 retrieval
            
        Returns:
            EnsembleRetriever instance
        """
        logger.info("Creating hybrid retriever (Vector + BM25)")
        
        # Dense retriever (vector similarity)
        # 1. 密集检索器（向量相似度）
        dense_retriever = vector_store.as_retriever(
            search_kwargs={"k": self.config.top_k}
        )
        
        # Sparse retriever (keyword-based)
        # 2. 稀疏检索器（关键词匹配）
        sparse_retriever = BM25Retriever.from_documents(
            documents, 
            k=self.config.top_k
        )
        
        # Combine retrievers
        # 3. 组合检索器
        ensemble_retriever = EnsembleRetriever(
            retrievers=[dense_retriever, sparse_retriever],
            weights=list(self.config.hybrid_weights)# [0.5, 0.5]
        )
        
        return ensemble_retriever
    
    def add_reranking(
        self, 
        base_retriever, 
        reranker
    ) -> ContextualCompressionRetriever:
        """
        Add reranking to a retriever
        在基础检索器上加rerank层
        Args:
            base_retriever: Base retriever
            reranker: Reranker instance
            
        Returns:
            Retriever with reranking
        """
        logger.info("Adding reranking layer")
        return ContextualCompressionRetriever(
            base_compressor=reranker,#重排序模型
            base_retriever=base_retriever#基础检索器
        )


def generate_collection_id(source_name: str) -> str:
    """
    用MD5生成唯一ID
    Generate unique collection ID from source name
    
    Args:
        source_name: Source identifier
        
    Returns:
        MD5 hash of source name
    """
    return hashlib.md5(source_name.encode('utf-8')).hexdigest()
