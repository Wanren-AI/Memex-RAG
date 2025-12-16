"""
Document Loader Module
Handles loading and splitting of various document formats
文档加载与切分
"""
from typing import List
from pathlib import Path
from langchain_community.document_loaders import (
    CSVLoader, TextLoader, UnstructuredWordDocumentLoader,
    PyPDFLoader, UnstructuredMarkdownLoader
)
from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.file_utils.filetype import FileType, detect_filetype
from loguru import logger


class DocumentProcessor:
    """
    Unified document processor for multiple file formats
    Supports: TXT, CSV, DOC, DOCX, PDF, MD
    """

    # Mapping of file types to their loaders
    LOADER_MAPPING = {
        FileType.CSV: (CSVLoader, {'autodetect_encoding': True}),
        FileType.TXT: (TextLoader, {'autodetect_encoding': True}),
        FileType.DOC: (Docx2txtLoader, {}),
        FileType.DOCX: (Docx2txtLoader, {}),
        FileType.PDF: (PyPDFLoader, {}),
        FileType.MD: (TextLoader, {'encoding': 'utf-8'})
    }

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        """
        Initialize document processor

        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", " ", ""],# 按优先级切分，实在没办法的话按字符数强行切
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def load_document(self, file_path: str) -> List[Document]:
        """
        Load and split document into chunks

        Args:
            file_path: Path to the document

        Returns:
            List of document chunks
        """
        try:
            # 1. 检测文件类型
            file_type = detect_filetype(file_path)

            # 2. 查找对应加载器
            if file_type not in self.LOADER_MAPPING:
                raise ValueError(f"Unsupported file type: {file_type}")

            loader_class, params = self.LOADER_MAPPING[file_type]
            logger.info(f"Loading document [{file_path}] using {loader_class.__name__}")
            # 3. 创建加载器实例
            loader = loader_class(file_path, **params)
            # 4. 加载并切分
            documents = loader.load_and_split(self.text_splitter)

            logger.info(f"Document split into {len(documents)} chunks")
            return documents

        except Exception as e:
            logger.error(f"Failed to load document {file_path}: {e}")
            raise

    def validate_file(self, file_path: str) -> bool:
        """
        文件是否有效
        Validate if file exists and is supported

        Args:
            file_path: Path to validate

        Returns:
            True if valid, False otherwise
        """
        path = Path(file_path)

        if not path.exists():
            logger.error(f"File does not exist: {file_path}")
            return False

        try:
            file_type = detect_filetype(file_path)
            if file_type not in self.LOADER_MAPPING:
                logger.error(f"Unsupported file type: {file_type}")
                return False
            return True
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            return False