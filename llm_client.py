"""
LLM Client Management Module
Handles interactions with language models and embeddings
LLM客户端， 一般模型 rerank模型 embedding模型的创建和管理
模型处理
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_compressors import DashScopeRerank
from loguru import logger

from config import ModelConfig


class LLMClientManager:
    """
    Manages LLM client instances
    Provides unified interface for different models
    """

    def __init__(self, config: ModelConfig):
        """
        Initialize LLM client manager

        Args:
            config: Model configuration
        """
        self.config = config
        self._client: Optional[ChatOpenAI] = None

    @property
    def client(self) -> ChatOpenAI:
        """
        Get or create LLM client instance
        懒加载：第一次使用时才创建
        Returns:
            ChatOpenAI client
        """
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> ChatOpenAI:
        """Create new LLM client"""
        logger.info(f"Creating LLM client for model: {self.config.model_name}")
        return ChatOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

    def update_model(self, model_name: str) -> None:
        """
        Update model and recreate client
        切换模型

        Args:
            model_name: New model name
        """
        logger.info(f"Switching model from {self.config.model_name} to {model_name}")
        self.config.model_name = model_name
        self._client = None

    def update_parameters(self, temperature: Optional[float] = None,
                          max_tokens: Optional[int] = None) -> None:
        """
        Update model parameters
        切换配置

        Args:
            temperature: New temperature value
            max_tokens: New max tokens value
        """
        if temperature is not None:
            self.config.temperature = temperature
        if max_tokens is not None:
            self.config.max_tokens = max_tokens

        if self._client is not None:
            self._client = None
            logger.info("Model parameters updated, client will be recreated")


class EmbeddingManager:
    """
    Manages embedding model instances
    """

    EMBEDDING_MODEL = "text-embedding-v3"

    def __init__(self, api_key: str):
        """
        Initialize embedding manager

        Args:
            api_key: API key for embedding service
        """
        self.api_key = api_key
        self._embeddings: Optional[DashScopeEmbeddings] = None

    @property
    def embeddings(self) -> DashScopeEmbeddings:
        """
        Get or create embeddings instance

        Returns:
            DashScopeEmbeddings instance
        """
        if self._embeddings is None:
            self._embeddings = self._create_embeddings()
        return self._embeddings

    def _create_embeddings(self) -> DashScopeEmbeddings:
        """Create embeddings instance"""
        logger.info(f"Creating embeddings with model: {self.EMBEDDING_MODEL}")
        return DashScopeEmbeddings(
            model=self.EMBEDDING_MODEL,
            dashscope_api_key=self.api_key
        )


class RerankManager:
    """
    Manages reranking model instances
    """

    RERANK_MODEL = "gte-rerank-v2"

    def __init__(self, api_key: str):
        """
        Initialize rerank manager

        Args:
            api_key: API key for rerank service
        """
        self.api_key = api_key

    def get_reranker(self, top_n: int = 3) -> DashScopeRerank:
        """
        Get reranker instance

        Args:
            top_n: Number of top results to return

        Returns:
            DashScopeRerank instance
        """
        logger.info(f"Creating reranker with top_n={top_n}")
        return DashScopeRerank(
            model=self.RERANK_MODEL,
            dashscope_api_key=self.api_key,
            top_n=top_n
        )