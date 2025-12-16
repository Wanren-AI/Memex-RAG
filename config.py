"""
Configuration Management Module
Handles all configuration settings for the RAG system
配置管理
"""
import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class ModelConfig:
    """LLM Model Configuration"""
    api_key: str
    base_url: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 8000
    
    @classmethod
    def from_env(cls, model_name: str = "qwen-max-latest"):
        """Create config from environment variables"""
        return cls(
            api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model_name=model_name,
        )


@dataclass
class VectorStoreConfig:
    """Vector Store Configuration"""
    persist_directory: str# 数据库存储目录
    collection_prefix: str = "doc_kb"# 集合名前缀
    chunk_size: int = 600
    chunk_overlap: int = 150
    
    @classmethod
    def default(cls):
        """Create default configuration"""
        base_dir = Path("./vector_store")
        base_dir.mkdir(exist_ok=True)
        return cls(persist_directory=str(base_dir))


@dataclass
class RetrievalConfig:
    """Retrieval Configuration"""
    top_k: int = 8# 检索返回前8个结果
    use_rerank: bool = True
    use_llm_filter: bool = False
    rerank_top_n: int = 4 # 重排后取前4个
    hybrid_weights: tuple = (0.5, 0.5)


@dataclass
class SystemConfig:
    """Complete System Configuration
    包含模模型 向量空间 检索器三个config 可以理解为是config的config
    """
    model: ModelConfig
    vector_store: VectorStoreConfig
    retrieval: RetrievalConfig
    
    @classmethod
    def default(cls):
        """Create default system configuration"""
        return cls(
            model=ModelConfig.from_env(),
            vector_store=VectorStoreConfig.default(),
            retrieval=RetrievalConfig()
        )


# Available models
class AvailableModels:
    """Available LLM models - 阿里百炼平台支持的模型"""
    QWEN_MAX = "qwen-max-latest"
    QWEN_PLUS = "qwen-plus-latest"
    QWEN_TURBO = "qwen-turbo-latest"

    @classmethod
    def all(cls):
        """Get all available models"""
        return [cls.QWEN_MAX, cls.QWEN_PLUS, cls.QWEN_TURBO]


# File type support
SUPPORTED_FILE_TYPES = {
    '.txt', '.csv', '.doc', '.docx', '.pdf', '.md'
}