"""
Document Analysis Assistant - Personal Edition
A refactored, professional RAG system for document-based Q&A
åˆå§‹åŒ–
"""

__version__ = "1.0.0"
__author__ = "Personal Edition"
__description__ = "Intelligent document analysis with RAG technology"

# Core exports
from .rag_system import DocumentAssistant, MultiDocumentAssistant
from .config import (
    SystemConfig,
    ModelConfig,
    VectorStoreConfig,
    RetrievalConfig,
    AvailableModels
)
from .logging_config import setup_logging

# Version info
VERSION_INFO = {
    "version": __version__,
    "description": __description__,
    "features": [
        "Multi-format document support",
        "Hybrid retrieval (Vector + BM25)",
        "Optional reranking",
        "Conversational AI with history",
        "Multi-document queries",
        "Multiple LLM models",
        "CLI and Web interfaces",
        "Performance evaluation"
    ]
}

__all__ = [
    # Main classes
    "DocumentAssistant",
    "MultiDocumentAssistant",

    # Configuration
    "SystemConfig",
    "ModelConfig",
    "VectorStoreConfig",
    "RetrievalConfig",
    "AvailableModels",

    # Utilities
    "setup_logging",

    # Metadata
    "__version__",
    "VERSION_INFO"
]


def get_version_info():
    """Get formatted version information"""
    info = [
        f"Document Analysis Assistant v{__version__}",
        f"Description: {__description__}",
        "\nFeatures:"
    ]
    for feature in VERSION_INFO["features"]:
        info.append(f"  â€¢ {feature}")
    return "\n".join(info)


if __name__ == "__main__":
    print(get_version_info())