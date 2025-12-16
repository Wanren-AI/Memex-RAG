"""
Knowledge Base Manager
Core module for managing document knowledge bases
知识库管理
高层抽象
"""
import shutil
import hashlib
import json
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime
from langchain_core.retrievers import BaseRetriever
from loguru import logger

from config import VectorStoreConfig, RetrievalConfig
from document_loader import DocumentProcessor
from vector_store import VectorStoreManager, RetrieverFactory, generate_collection_id
from llm_client import EmbeddingManager, RerankManager


class KnowledgeBaseManager:
    """
    Manages document knowledge bases
    Handles upload, indexing, and retrieval operations
    """

    def __init__(
            self,
            embedding_manager: EmbeddingManager,
            rerank_manager: RerankManager,
            vector_config: VectorStoreConfig,
            retrieval_config: RetrievalConfig
    ):
        """
        Initialize knowledge base manager

        Args:
            embedding_manager: Embedding model manager
            rerank_manager: Rerank model manager
            vector_config: Vector store configuration
            retrieval_config: Retrieval configuration
        """
        # 1. 保存依赖
        self.embedding_manager = embedding_manager
        self.rerank_manager = rerank_manager
        self.vector_config = vector_config
        self.retrieval_config = retrieval_config

        # Initialize components
        # 2. 初始化组件
        self.document_processor = DocumentProcessor(
            chunk_size=vector_config.chunk_size,
            chunk_overlap=vector_config.chunk_overlap
        )
        self.vector_store_manager = VectorStoreManager(
            vector_config,
            embedding_manager.embeddings
        )
        self.retriever_factory = RetrieverFactory(retrieval_config)

        # Storage for documents and retrievers
        # 3. 缓存（提高性能）
        self.document_cache: Dict[str, List] = {}
        self.retriever_cache: Dict[str, BaseRetriever] = {}

        # Knowledge base storage path
        # 4. 存储目录
        self.kb_storage = Path("./knowledge_base")
        self.kb_storage.mkdir(exist_ok=True)

        # Config directory for metadata (separate from documents)
        # 配置目录（存储元数据，与文档分离）
        self.config_dir = Path("./.rag_config")
        self.config_dir.mkdir(exist_ok=True)

        # File hash tracking for change detection
        # 文件hash追踪（用于检测文档变化）
        self.file_hashes: Dict[str, str] = {}
        self.hash_file = self.config_dir / "file_hashes.json"

        # Deferred deletion for Windows file lock issues
        # 延迟删除（解决Windows文件锁定问题）
        self.pending_deletions_file = self.config_dir / "pending_deletions.json"
        self.pending_deletions = set()

        # Load existing file hashes
        self._load_file_hashes()

        # Load and cleanup pending deletions
        # 加载并清理待删除的数据
        self._load_pending_deletions()
        self._cleanup_pending_deletions()

    def upload_document(self, file_path: str, original_filename: str = None) -> Optional[str]:
        """
        Upload and index a document

        Args:
            file_path: Path to document file
            original_filename: Original filename (优先使用,避免编码问题)

        Returns:
            Document identifier or None if failed
        """
        try:
            # Validate file
            if not self.document_processor.validate_file(file_path):
                return None

            # Copy file to storage
            # 优先使用传入的原始文件名,确保中文正常显示
            file_name = original_filename if original_filename else Path(file_path).name
            stored_path = self.kb_storage / file_name

            if not stored_path.exists():
                shutil.copy(file_path, stored_path)
                logger.info(f"Document copied to: {stored_path}")

            # Generate collection ID
            collection_id = generate_collection_id(file_name)

            # Check if already indexed检查是否已索引
            if collection_id in self.retriever_cache:
                logger.info(f"Document already indexed: {file_name}")
                return file_name

            # Load and split document 加载并切分文档
            documents = self.document_processor.load_document(str(stored_path))

            # Create vector store collection创建向量存储
            vector_store = self.vector_store_manager.create_collection(
                collection_id,
                documents
            )

            # Cache documents
            self.document_cache[collection_id] = documents

            # Create retriever
            retriever = self._create_retriever(collection_id, vector_store, documents)
            self.retriever_cache[collection_id] = retriever

            # Calculate and save file hash
            file_hash = self._calculate_file_hash(str(stored_path))
            self.file_hashes[file_name] = file_hash
            self._save_file_hashes()

            logger.info(f"Document successfully indexed: {file_name}")
            return file_name

        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            return None

    def _create_retriever(self, collection_id: str, vector_store, documents) -> BaseRetriever:
        """
        Create retriever with optional enhancements

        Args:
            collection_id: Collection identifier
            vector_store: Vector store instance
            documents: Source documents

        Returns:
            Enhanced retriever
        """
        # Start with hybrid retriever
        retriever = self.retriever_factory.create_hybrid_retriever(
            vector_store,
            documents
        )

        # Add reranking if enabled
        if self.retrieval_config.use_rerank:
            try:
                reranker = self.rerank_manager.get_reranker(
                    top_n=self.retrieval_config.rerank_top_n
                )
                retriever = self.retriever_factory.add_reranking(retriever, reranker)
                logger.info(f"Reranking enabled for collection: {collection_id}")
            except Exception as e:
                logger.warning(f"Failed to enable reranking: {e}")

        return retriever

    def get_retriever(self, document_name: str) -> Optional[BaseRetriever]:
        """
        Get retriever for a document

        Args:
            document_name: Document name

        Returns:
            Retriever instance or None
        """
        collection_id = generate_collection_id(document_name)

        # 先检查retriever cache
        if collection_id in self.retriever_cache:
            return self.retriever_cache[collection_id]

        # Try to load from disk
        vector_store = self.vector_store_manager.get_collection(collection_id)
        if vector_store is None:
            return None

        # 检查document_cache，避免重复加载文件
        if collection_id in self.document_cache:
            documents = self.document_cache[collection_id]
            logger.debug(f"从cache获取文档: {document_name}")
        else:
            # 只在cache中没有时才重新加载文件
            stored_path = self.kb_storage / document_name
            if not stored_path.exists():
                return None

            logger.debug(f"重新加载文档: {document_name}")
            documents = self.document_processor.load_document(str(stored_path))
            self.document_cache[collection_id] = documents

        retriever = self._create_retriever(collection_id, vector_store, documents)
        self.retriever_cache[collection_id] = retriever

        return retriever

    def list_documents(self) -> List[str]:
        """
        List all available documents
        Excludes hidden files and configuration files

        Returns:
            List of document names
        """
        if not self.kb_storage.exists():
            return []

        # 确保文件名正确编码
        files = [
            f.name for f in self.kb_storage.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]

        # 对文件名进行排序并返回
        return sorted(files)

    def delete_document(self, document_name: str) -> bool:
        """
        Delete a document and its vector index (with deferred deletion for Windows)
        删除文档及其向量索引（Windows使用延迟删除机制）

        Args:
            document_name: Document to delete

        Returns:
            True if deleted successfully
        """
        import gc
        import time

        try:
            collection_id = generate_collection_id(document_name)
            logger.info(f"🗑️ Deleting document: {document_name}")
            logger.debug(f"   Collection ID: {collection_id}")

            # Step 1: Remove from all caches (immediate - user won't see the document)
            # 从所有缓存中移除（立即生效 - 用户立即看不到文档）
            if collection_id in self.retriever_cache:
                del self.retriever_cache[collection_id]
                logger.info(f"  ✓ Removed from retriever cache")

            if collection_id in self.document_cache:
                del self.document_cache[collection_id]
                logger.info(f"  ✓ Removed from document cache")

            # Step 2: Release vector store connection
            # 释放向量存储连接
            if collection_id in self.vector_store_manager.stores:
                del self.vector_store_manager.stores[collection_id]
                logger.info(f"  ✓ Released vector store connection")

            # Step 3: Force garbage collection
            # 强制垃圾回收
            gc.collect()
            logger.debug(f"  ✓ Forced garbage collection")

            # Step 4: Remove from file hashes
            # 从文件哈希记录中移除
            if document_name in self.file_hashes:
                del self.file_hashes[document_name]
                self._save_file_hashes()
                logger.info(f"  ✓ Removed from file hashes")

            # Step 5: Delete physical file (immediate)
            # 删除物理文件（立即）
            stored_path = self.kb_storage / document_name
            if stored_path.exists():
                stored_path.unlink()
                logger.info(f"  ✓ Physical file deleted")

            # Step 6: Try immediate vector deletion
            # 尝试立即删除向量数据
            vector_path = Path(self.vector_config.persist_directory) / collection_id

            if not vector_path.exists():
                logger.info(f"  ✓ Vector data already removed")
                logger.info(f"✅ Document deleted successfully: {document_name}")
                return True

            # Wait briefly for Windows to release locks
            time.sleep(0.5)

            # Try to delete
            try:
                shutil.rmtree(vector_path)
                logger.info(f"  ✓ Vector data deleted immediately")
                logger.info(f"✅ Document deleted successfully: {document_name}")
                return True
            except (PermissionError, OSError) as e:
                # File locked - use deferred deletion
                logger.info(f"  📌 Vector data locked, using deferred deletion")
                logger.debug(f"     Reason: {e}")

                # Mark for deferred deletion
                self.pending_deletions.add(collection_id)
                self._save_pending_deletions()

                logger.info(f"  ✓ Marked for cleanup on next restart")
                logger.info(f"✅ Document deleted successfully: {document_name}")
                logger.info(f"   💡 Vector data will be cleaned up on next program start")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def update_document(self, file_path: str, force: bool = False) -> Optional[str]:
        """
        Update an existing document with intelligent change detection
        智能文档更新：检测变化后才更新

        Args:
            file_path: Path to the new/updated document file
            force: Force update even if file hasn't changed

        Returns:
            Document name if successful, None if failed

        Example:
            >>> kb_manager.update_document("updated_report.pdf")
            >>> kb_manager.update_document("report.pdf", force=True)  # 强制更新
        """
        try:
            file_name = Path(file_path).name
            stored_path = self.kb_storage / file_name

            # Check if document exists
            if not stored_path.exists():
                logger.warning(f"Document not found in knowledge base: {file_name}")
                logger.info(f"Uploading as new document instead...")
                return self.upload_document(file_path)

            # Calculate new file hash
            new_hash = self._calculate_file_hash(file_path)
            old_hash = self.file_hashes.get(file_name)

            # Check if file has actually changed
            if not force and old_hash == new_hash:
                logger.info(f"📄 Document content unchanged: {file_name}")
                logger.info(f"   Hash: {new_hash[:16]}...")
                return file_name

            # File has changed or force update
            logger.info(f"🔄 Updating document: {file_name}")
            if force:
                logger.info(f"   (Force update)")
            else:
                logger.info(f"   Old hash: {old_hash[:16] if old_hash else 'None'}...")
                logger.info(f"   New hash: {new_hash[:16]}...")

            # Step 1: Release old resources and connections
            # 释放旧资源和连接
            collection_id = generate_collection_id(file_name)

            logger.info(f"   Releasing old resources...")
            self.retriever_cache.pop(collection_id, None)
            self.document_cache.pop(collection_id, None)
            self.vector_store_manager.stores.pop(collection_id, None)

            # Force garbage collection to release connections
            import gc
            gc.collect()

            # Try to delete old vector data (may fail on Windows, will be cleaned up later)
            # 尝试删除旧向量数据（Windows可能失败，稍后会清理）
            vector_path = Path(self.vector_config.persist_directory) / collection_id
            if vector_path.exists():
                import time
                time.sleep(0.3)  # Brief wait
                try:
                    shutil.rmtree(vector_path)
                    logger.debug(f"   ✓ Old vector data deleted")
                except (PermissionError, OSError):
                    # Mark for deferred deletion
                    self.pending_deletions.add(collection_id)
                    self._save_pending_deletions()
                    logger.debug(f"   📌 Old vector data marked for cleanup")

            # Step 2: Copy new file to storage (overwrite)
            logger.info(f"   Copying new file...")
            shutil.copy(file_path, stored_path)

            # Step 3: Re-index with new content
            logger.info(f"   Re-indexing document...")
            documents = self.document_processor.load_document(str(stored_path))

            # Create new vector store collection
            vector_store = self.vector_store_manager.create_collection(
                collection_id,
                documents
            )

            # Update caches
            self.document_cache[collection_id] = documents

            # Create new retriever
            retriever = self._create_retriever(collection_id, vector_store, documents)
            self.retriever_cache[collection_id] = retriever

            # Update file hash
            self.file_hashes[file_name] = new_hash
            self._save_file_hashes()

            logger.info(f"✅ Document updated successfully: {file_name}")
            logger.info(f"   Chunks: {len(documents)}")

            return file_name

        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return None

    def get_document_info(self, document_name: str) -> Optional[Dict]:
        """
        Get information about a document
        获取文档信息

        Args:
            document_name: Name of the document

        Returns:
            Dictionary with document info or None
        """
        stored_path = self.kb_storage / document_name

        if not stored_path.exists():
            return None

        collection_id = generate_collection_id(document_name)

        # Get file stats
        file_stats = stored_path.stat()
        file_size = file_stats.st_size
        modified_time = datetime.fromtimestamp(file_stats.st_mtime)

        # Get chunk count from cache or load
        chunk_count = 0
        if collection_id in self.document_cache:
            chunk_count = len(self.document_cache[collection_id])
        else:
            vector_store = self.vector_store_manager.get_collection(collection_id)
            if vector_store:
                try:
                    # Try to get count from vector store
                    chunk_count = vector_store._collection.count()
                except:
                    chunk_count = "Unknown"

        return {
            "name": document_name,
            "path": str(stored_path),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "modified_time": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
            "file_hash": self.file_hashes.get(document_name, "Unknown"),
            "chunk_count": chunk_count,
            "indexed": collection_id in self.retriever_cache
        }

    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate MD5 hash of a file
        计算文件的MD5哈希值

        Args:
            file_path: Path to file

        Returns:
            MD5 hash string
        """
        hash_md5 = hashlib.md5()

        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)

        return hash_md5.hexdigest()

    def _load_file_hashes(self) -> None:
        """
        Load file hashes from disk
        从磁盘加载文件哈希记录
        """
        if self.hash_file.exists():
            try:
                with open(self.hash_file, 'r', encoding='utf-8') as f:
                    self.file_hashes = json.load(f)
                logger.debug(f"Loaded {len(self.file_hashes)} file hashes")
            except Exception as e:
                logger.warning(f"Failed to load file hashes: {e}")
                self.file_hashes = {}
        else:
            self.file_hashes = {}

    def _save_file_hashes(self) -> None:
        """
        Save file hashes to disk
        保存文件哈希记录到磁盘
        """
        try:
            with open(self.hash_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_hashes, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.file_hashes)} file hashes")
        except Exception as e:
            logger.warning(f"Failed to save file hashes: {e}")

    def _load_pending_deletions(self) -> None:
        """
        Load pending deletions from disk
        从磁盘加载待删除列表
        """
        if self.pending_deletions_file.exists():
            try:
                with open(self.pending_deletions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.pending_deletions = set(data.get('collections', []))
                if self.pending_deletions:
                    logger.info(f"📌 Loaded {len(self.pending_deletions)} pending deletions")
            except Exception as e:
                logger.warning(f"Failed to load pending deletions: {e}")
                self.pending_deletions = set()
        else:
            self.pending_deletions = set()

    def _save_pending_deletions(self) -> None:
        """
        Save pending deletions to disk
        保存待删除列表到磁盘
        """
        try:
            with open(self.pending_deletions_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'collections': list(self.pending_deletions)
                }, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.pending_deletions)} pending deletions")
        except Exception as e:
            logger.warning(f"Failed to save pending deletions: {e}")

    def _cleanup_pending_deletions(self) -> None:
        """
        Cleanup pending deletions on startup
        启动时清理待删除的数据
        """
        if not self.pending_deletions:
            return

        logger.info(f"🧹 Cleaning up {len(self.pending_deletions)} pending deletions...")

        cleaned = 0
        still_locked = []

        for collection_id in list(self.pending_deletions):
            vector_path = Path(self.vector_config.persist_directory) / collection_id

            if not vector_path.exists():
                # Already deleted
                self.pending_deletions.remove(collection_id)
                cleaned += 1
                logger.debug(f"  ✓ Already cleaned: {collection_id[:16]}...")
                continue

            try:
                shutil.rmtree(vector_path)
                self.pending_deletions.remove(collection_id)
                cleaned += 1
                logger.info(f"  ✓ Cleaned up: {collection_id[:16]}...")
            except Exception as e:
                logger.debug(f"  ⚠️ Still locked: {collection_id[:16]}... ({e})")
                still_locked.append(collection_id)

        # Save updated pending list
        self._save_pending_deletions()

        if cleaned > 0:
            logger.info(f"✅ Cleanup complete: {cleaned} cleaned")
        if still_locked:
            logger.warning(f"⚠️ {len(still_locked)} collections still locked, will retry next time")