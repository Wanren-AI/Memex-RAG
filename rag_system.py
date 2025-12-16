"""
RAG System Core
Main interface for the document analysis assistant
整个系统的核心
"""
from typing import Optional, Iterator, Dict, Any, List
from loguru import logger

from config import SystemConfig, AvailableModels
from llm_client import LLMClientManager, EmbeddingManager, RerankManager
from knowledge_base import KnowledgeBaseManager
from conversation import ConversationManager


class DocumentAssistant:
    """
    Unified RAG System Interface
    Provides high-level API for document-based question answering
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Initialize Document Assistant

        Args:
            config: System configuration (uses default if None)
        """
        self.config = config or SystemConfig.default()
        logger.info("Initializing Document Assistant...")

        # Initialize managers
        self.llm_manager = LLMClientManager(self.config.model)
        self.embedding_manager = EmbeddingManager(self.config.model.api_key)
        self.rerank_manager = RerankManager(self.config.model.api_key)

        # Initialize knowledge base
        self.kb_manager = KnowledgeBaseManager(
            self.embedding_manager,
            self.rerank_manager,
            self.config.vector_store,
            self.config.retrieval
        )

        # Initialize conversation
        self.conversation_manager = ConversationManager(
            self.llm_manager,
            self.kb_manager
        )

        logger.info("Document Assistant initialized successfully")

        # 预加载所有文档到cache（重要优化）
        self._preload_documents()

    # ========== Document Management ==========

    def upload_document(self, file_path: str, original_filename: str = None) -> bool:
        """
        Upload and index a document

        Args:
            file_path: Path to document
            original_filename: Original filename (for proper encoding)

        Returns:
            True if successful
        """
        result = self.kb_manager.upload_document(file_path, original_filename=original_filename)
        return result is not None

    def list_documents(self) -> List[str]:
        """
        List all indexed documents

        Returns:
            List of document names
        """
        return self.kb_manager.list_documents()

    def delete_document(self, document_name: str) -> bool:
        """
        Delete a document

        Args:
            document_name: Document to delete

        Returns:
            True if successful
        """
        return self.kb_manager.delete_document(document_name)

    def update_document(self, file_path: str, force: bool = False) -> bool:
        """
        Update an existing document

        Args:
            file_path: Path to the updated document
            force: Force update even if content hasn't changed

        Returns:
            True if successful
        """
        result = self.kb_manager.update_document(file_path, force)
        return result is not None

    def get_document_info(self, document_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a document

        Args:
            document_name: Name of the document

        Returns:
            Dictionary with document information
        """
        return self.kb_manager.get_document_info(document_name)

    # ========== Conversation ==========

    def ask(
            self,
            question: str,
            document_name: Optional[str] = None
    ) -> str:
        """
        Ask a question (synchronous)

        Args:
            question: User question
            document_name: Optional document for context

        Returns:
            Answer text
        """
        response = self.conversation_manager.chat(question, document_name)
        return response.get('answer', '')

    def ask_stream(
            self,
            question: str,
            document_name: Optional[str] = None
    ) -> Iterator[str]:
        """
        Ask a question with streaming response

        Args:
            question: User question
            document_name: Optional document for context

        Yields:
            Answer chunks
        """
        for chunk in self.conversation_manager.chat_stream(question, document_name):
            if 'answer' in chunk and chunk['answer']:
                yield chunk['answer']

    def clear_conversation(self) -> None:
        """Clear conversation history"""
        self.conversation_manager.clear_history()

    def get_conversation_history(self) -> list:
        """Get conversation history"""
        return self.conversation_manager.get_history()

    # ========== Model Management ==========

    def switch_model(self, model_name: str) -> bool:
        """
        Switch to a different model

        Args:
            model_name: New model name

        Returns:
            True if successful
        """
        try:
            if model_name not in AvailableModels.all():
                logger.error(f"Unknown model: {model_name}")
                return False

            self.llm_manager.update_model(model_name)
            logger.info(f"Switched to model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch model: {e}")
            return False

    def update_parameters(
            self,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None
    ) -> None:
        """
        Update model parameters

        Args:
            temperature: Temperature value
            max_tokens: Maximum tokens
        """
        self.llm_manager.update_parameters(temperature, max_tokens)

    def get_current_model(self) -> str:
        """Get current model name"""
        return self.config.model.model_name

    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return AvailableModels.all()

    def ask_all_documents(
            self,
            question: str
    ) -> Dict[str, Any]:
        """
        Ask question across ALL documents in knowledge base

        Args:
            question: User question

        Returns:
            Dictionary with answer and sources from all documents
        """
        logger.info("Querying all documents in knowledge base")

        # Get all documents
        all_docs = self.list_documents()

        if not all_docs:
            return {
                'answer': "知识库中没有任何文档。请先上传文档。",
                'sources': [],
                'num_sources': 0
            }

        logger.info(f"Found {len(all_docs)} documents to search")

        # Collect contexts from all documents
        all_contexts = []

        for doc_name in all_docs:
            retriever = self.kb_manager.get_retriever(doc_name)
            if retriever:
                try:
                    docs = retriever.get_relevant_documents(question)
                    for doc in docs:
                        all_contexts.append({
                            'source': doc_name,
                            'content': doc.page_content,
                            'metadata': doc.metadata
                        })
                    logger.info(f"Retrieved {len(docs)} chunks from {doc_name}")
                except Exception as e:
                    logger.error(f"Failed to retrieve from {doc_name}: {e}")

        if not all_contexts:
            return {
                'answer': "未在任何文档中找到相关信息。",
                'sources': [],
                'num_sources': 0
            }

        logger.info(f"Total retrieved chunks: {len(all_contexts)}")

        # Build enhanced prompt with all contexts
        context_parts = []
        for i, ctx in enumerate(all_contexts, 1):
            page_info = f" (第{ctx['metadata'].get('page', '?')}页)" if 'page' in ctx['metadata'] else ""
            context_parts.append(
                f"[来源 {i}：{ctx['source']}{page_info}]\n{ctx['content']}"
            )

        context_text = "\n\n---\n\n".join(context_parts)

        enhanced_question = f"""基于以下从知识库所有文档中检索到的信息回答问题。

问题：{question}

检索到的相关内容：

{context_text}

---

请基于上述检索到的内容回答问题：
1. 仅使用上述文档中的事实信息
2. 明确标注信息来自哪个文档
3. 如果信息跨越多个文档，请综合分析
4. 不要推测文档中没有的内容
5. 按时间顺序或逻辑顺序组织信息（如果适用）"""

        # 保留对话历史，支持上下文记忆
        # self.clear_conversation()  # ❌ 移除清空历史

        # Query without specific document (direct LLM call)
        response = self.conversation_manager.chat(enhanced_question, document_name=None)

        # Format sources
        sources = []
        for i, ctx in enumerate(all_contexts, 1):
            source = {
                'index': i,
                'document': ctx['source'],
                'content': ctx['content'],
                'metadata': ctx['metadata']
            }
            if 'page' in ctx['metadata']:
                source['page'] = ctx['metadata']['page']
            sources.append(source)

        return {
            'answer': response.get('answer', ''),
            'sources': sources,
            'num_sources': len(sources),
            'documents_searched': len(all_docs)
        }

    def ask_all_documents_stream(
            self,
            question: str
    ) -> Iterator[Dict[str, Any]]:
        """
        智能任务分类的全局检索

        根据问题类型自动选择最佳检索策略：
        1. 统计型（提了几次）→ 高召回top20
        2. 演变型（观点变化）→ 分阶段检索
        3. 一般型（直接问答）→ 精确检索top5
        """
        logger.info("启动智能检索模式")

        # 获取所有文档
        all_docs = self.list_documents()

        if not all_docs:
            yield {
                'answer': "知识库中没有任何文档。请先上传文档。",
                'sources': [],
                'done': True
            }
            return

        # Step 1: 任务分类
        task_type = self._classify_task(question)
        logger.info(f"任务类型识别为: {task_type}")

        # Step 2: 根据任务类型调用不同策略
        if task_type == "STATISTICAL":
            yield from self._statistical_query(question, all_docs)
        elif task_type == "EVOLUTION":
            yield from self._evolution_query(question, all_docs)
        else:
            yield from self._general_query(question, all_docs)

    def _classify_task(self, question: str) -> str:
        """
        识别任务类型

        Returns:
            STATISTICAL: 统计型（计数、频率）
            EVOLUTION: 演变型（观点变化）
            GENERAL: 一般型（直接问答）
        """
        q_lower = question.lower()

        # 统计型关键词
        statistical_keywords = [
            '多少次', '频率', '出现', '提及', '次数', '提了', '说了',
            '几次', '统计', '计数', '列举', '所有'
        ]

        # 演变型关键词
        evolution_keywords = [
            '变化', '从', '到', '转变', '演变', '发展', '趋势',
            '为什么', '原因', '态度', '看法变', '观点变'
        ]

        # 检测统计型
        if any(kw in q_lower for kw in statistical_keywords):
            return "STATISTICAL"

        # 检测演变型（同时包含对比词）
        if any(kw in q_lower for kw in evolution_keywords):
            # 进一步检测是否有对比结构
            if ('从' in q_lower and '到' in q_lower) or '变化' in q_lower:
                return "EVOLUTION"

        return "GENERAL"

    def _statistical_query(
            self,
            question: str,
            all_docs: List[str]
    ) -> Iterator[Dict[str, Any]]:
        """
        统计型查询：高召回率策略
        目标：尽可能找到所有相关mentions
        """
        logger.info("📊 统计型查询：使用高召回模式（top20）")

        # 收集所有chunks（预加载已完成，直接从cache获取）
        all_chunks = []
        for doc_name in all_docs:
            from vector_store import generate_collection_id
            collection_id = generate_collection_id(doc_name)

            # 从cache获取（如果没有则跳过并警告）
            if collection_id in self.kb_manager.document_cache:
                chunks = self.kb_manager.document_cache[collection_id]
                for chunk in chunks:
                    chunk.metadata['source_document'] = doc_name
                    all_chunks.append(chunk)
            else:
                logger.warning(f"文档 {doc_name} 不在cache中（预加载可能失败）")

        if not all_chunks:
            yield {'answer': "无法加载文档内容。请确保文档已正确上传。", 'sources': [], 'done': True}
            return

        logger.info(f"收集到 {len(all_chunks)} 个chunks")

        # 使用BM25检索，避免SSL错误
        from langchain_community.retrievers import BM25Retriever

        try:
            # 高召回：使用BM25检索top20（不依赖embedding）
            bm25_retriever = BM25Retriever.from_documents(all_chunks, k=20)
            retrieved = bm25_retriever.invoke(question)
            logger.info(f"✅ BM25召回 {len(retrieved)} 个相关chunks")

        except Exception as e:
            logger.error(f"检索失败: {e}")
            yield {'answer': f"❌ 检索失败: {str(e)}", 'sources': [], 'done': True}
            return

        # 按文档分组并排序
        contexts_by_doc = {}
        for chunk in retrieved:
            doc = chunk.metadata.get('source_document', 'unknown')
            if doc not in contexts_by_doc:
                contexts_by_doc[doc] = []
            contexts_by_doc[doc].append(chunk)

        # 构建结构化上下文
        context_parts = []
        for doc_name in sorted(contexts_by_doc.keys()):
            context_parts.append(f"\n{'=' * 60}\n文档：{doc_name}\n{'=' * 60}")
            for i, chunk in enumerate(contexts_by_doc[doc_name], 1):
                page = chunk.metadata.get('page', '?')
                context_parts.append(f"\n[片段{i}，第{page}页]\n{chunk.page_content}")

        context_text = "\n".join(context_parts)

        # 统计型prompt
        prompt = f"""你是专业的报告研究分析师。基于检索到的原文片段回答统计类问题。

问题：{question}

检索结果（已按文档分组，共{len(contexts_by_doc)}个文档，{len(retrieved)}个相关片段）：

{context_text}

---

【回答要求】
1. **统计准确**：仔细阅读每个片段，逐一计数，不要遗漏任何提及
2. **标注出处**：每次提及都必须标注 [文档名-第X页]。如果文档中没有标注页数，仅标注[文档名]即可
3. **时间排序**：按年份顺序列举（如果文档名包含年份）
4. **原文引用**：关键观点要引用原文片段
5. **总结统计**：最后给出明确的统计结果

【回答格式示例】
根据检索到的{len(retrieved)}个相关片段，统计结果如下：

1. [1957年信-第2页] 首次提及，观点：...
   原文："..."

2. [1958年信] 再次讨论，观点：...
   原文："..."

...

【统计总结】
- 时间范围：XXXX年-XXXX年
- 提及次数：X次
- 涉及文档：X个
"""

        # 流式生成（保留对话历史）
        # self.clear_conversation()  # ❌ 移除清空历史
        for chunk in self.conversation_manager.chat_stream(prompt, document_name=None):
            if 'answer' in chunk and chunk['answer']:
                yield {'answer': chunk['answer']}

        # 返回所有sources
        sources = []
        for i, chunk in enumerate(retrieved, 1):
            source = {
                'index': i,
                'document': chunk.metadata.get('source_document', 'unknown'),
                'content': chunk.page_content,
                'metadata': chunk.metadata
            }
            if 'page' in chunk.metadata:
                source['page'] = chunk.metadata['page']
            sources.append(source)

        yield {
            'sources': sources,
            'num_sources': len(sources),
            'task_type': 'STATISTICAL',
            'recall_mode': 'high',
            'done': True
        }

    def _evolution_query(
            self,
            question: str,
            all_docs: List[str]
    ) -> Iterator[Dict[str, Any]]:
        """
        演变型查询：时间序列分析
        目标：展示观点随时间的变化
        """
        logger.info(" 演变型查询：使用时间序列分析模式")
        logger.info(" 演变型查询：使用时间序列分析模式")

        # 收集所有chunks（预加载已完成）
        all_chunks = []
        for doc_name in all_docs:
            from vector_store import generate_collection_id
            collection_id = generate_collection_id(doc_name)

            # 从cache获取
            if collection_id in self.kb_manager.document_cache:
                chunks = self.kb_manager.document_cache[collection_id]
                for chunk in chunks:
                    chunk.metadata['source_document'] = doc_name
                    chunk.metadata['year'] = self._extract_year(doc_name)
                    all_chunks.append(chunk)
            else:
                logger.warning(f"文档 {doc_name} 不在cache中")

        logger.info(f"✅ 演变型查询：成功收集 {len(all_chunks)} 个chunks")

        if not all_chunks:
            yield {'answer': "无法加载文档内容。请确保文档已正确上传。", 'sources': [], 'done': True}
            return

        # 使用BM25检索，避免SSL错误
        from langchain_community.retrievers import BM25Retriever

        try:
            # 检索top15（不依赖embedding）
            bm25_retriever = BM25Retriever.from_documents(all_chunks, k=15)
            retrieved = bm25_retriever.invoke(question)
            logger.info(f"✅ BM25检索到 {len(retrieved)} 个相关chunks")

        except Exception as e:
            logger.error(f"检索失败: {e}")
            yield {'answer': f"❌ 检索失败: {str(e)}", 'sources': [], 'done': True}
            return

        # 按时间排序
        sorted_chunks = sorted(
            retrieved,
            key=lambda x: (x.metadata.get('year', '9999'), x.metadata.get('source_document', ''))
        )

        # 构建时间线上下文
        context_parts = []
        current_year = None

        for i, chunk in enumerate(sorted_chunks, 1):
            doc = chunk.metadata.get('source_document', 'unknown')
            year = chunk.metadata.get('year', '?')
            page = chunk.metadata.get('page', '?')

            # 年份分隔
            if year != current_year:
                current_year = year
                context_parts.append(f"\n{'=' * 60}\n【{year}年】\n{'=' * 60}")

            context_parts.append(f"\n[{doc}-第{page}页]\n{chunk.page_content}")

        context_text = "\n".join(context_parts)

        # 演变型prompt
        prompt = f"""你是专业的文档分析师。基于检索到的按时间排序的原文片段，分析观点演变过程。

问题：{question}

检索结果（已按时间排序，共{len(sorted_chunks)}个片段）：

{context_text}

---

【回答要求】
1. **时间线索**：清晰展示观点随时间的演变轨迹
2. **阶段划分**：识别关键转折点，划分不同阶段
3. **原因分析**：分析每次转变的可能原因或背景
4. **精确引用**：每个观点都要标注 [文档名-第X页] 并引用原文。如果文档中没有标注页数，仅标注[文档名]即可
5. **对比分析**：明确指出前后观点的异同

【回答格式示例】
观点演变分析：

一、早期阶段（XXXX年-XXXX年）：[概括性描述]
   [XXXX年信-第X页] 观点1：...
   原文引用："..."

   [XXXX年信-第X页] 观点2：...
   原文引用："..."

二、转折点（XXXX年）：
   [XXXX年信-第X页] 关键变化：...
   可能原因：...

三、新阶段（XXXX年-XXXX年）：[概括性描述]
   [XXXX年信-第X页] 新观点：...
   与早期对比：...

【演变总结】
- 主要变化：...
- 关键转折：...
- 深层原因：...
"""

        # 流式生成（保留对话历史）
        # self.clear_conversation()  # ❌ 移除清空历史
        for chunk in self.conversation_manager.chat_stream(prompt, document_name=None):
            if 'answer' in chunk and chunk['answer']:
                yield {'answer': chunk['answer']}

        # 返回sources
        sources = []
        for i, chunk in enumerate(sorted_chunks, 1):
            source = {
                'index': i,
                'document': chunk.metadata.get('source_document', 'unknown'),
                'year': chunk.metadata.get('year', '?'),
                'content': chunk.page_content,
                'metadata': chunk.metadata
            }
            if 'page' in chunk.metadata:
                source['page'] = chunk.metadata['page']
            sources.append(source)

        yield {
            'sources': sources,
            'num_sources': len(sources),
            'task_type': 'EVOLUTION',
            'done': True
        }

    def _general_query(
            self,
            question: str,
            all_docs: List[str]
    ) -> Iterator[Dict[str, Any]]:
        """
        一般型查询：精确检索
        目标：直接回答具体问题
        """
        logger.info("🎯 一般型查询：使用精确检索模式（top5）")

        # 收集所有chunks（预加载已完成）
        all_chunks = []
        for doc_name in all_docs:
            from vector_store import generate_collection_id
            collection_id = generate_collection_id(doc_name)

            # 从cache获取
            if collection_id in self.kb_manager.document_cache:
                chunks = self.kb_manager.document_cache[collection_id]
                for chunk in chunks:
                    chunk.metadata['source_document'] = doc_name
                    all_chunks.append(chunk)
            else:
                logger.warning(f"文档 {doc_name} 不在cache中")

        if not all_chunks:
            yield {'answer': "无法加载文档内容", 'sources': [], 'done': True}
            return

        logger.info(f"收集到 {len(all_chunks)} 个chunks")

        # 使用预加载的检索器，而不是创建临时向量库（避免SSL错误）
        from langchain.retrievers import EnsembleRetriever
        from langchain_community.retrievers import BM25Retriever
        from langchain.schema import Document

        try:
            # 方案：使用BM25 + 简单排序，不依赖embedding
            # 创建BM25检索器
            bm25_retriever = BM25Retriever.from_documents(all_chunks, k=15)

            # 直接使用BM25检索（不使用向量检索，避免SSL）
            retrieved = bm25_retriever.invoke(question)
            logger.info(f"✅ BM25检索返回 {len(retrieved)} 个最相关chunks")

            # 简单截断到top10
            retrieved = retrieved[:10] if len(retrieved) > 10 else retrieved

        except Exception as e:
            logger.error(f"检索失败: {e}")
            yield {'answer': f"❌ 检索失败: {str(e)}", 'sources': [], 'done': True}
            return

        # 构建上下文
        context_parts = []
        for i, chunk in enumerate(retrieved, 1):
            doc = chunk.metadata.get('source_document', 'unknown')
            page = chunk.metadata.get('page', '?')
            context_parts.append(f"[来源{i}：{doc}-第{page}页]\n{chunk.page_content}")

        context_text = "\n\n---\n\n".join(context_parts)

        # 一般型prompt
        prompt = f"""基于检索到的最相关文档片段回答问题。

问题：{question}

检索到的相关内容（已按相关度排序）：

{context_text}

---

请基于上述检索到的内容回答问题：
1. 仅使用上述文档中的事实信息
2. 明确标注信息来源 [文档名-第X页]，如果文档中没有标注页数，仅标注[文档名]即可
3. 关键观点要引用原文
4. 不要推测文档中没有的内容
"""

        # 流式生成（保留对话历史，支持上下文记忆）
        # self.clear_conversation()  # ❌ 移除清空历史，保留短期记忆
        for chunk in self.conversation_manager.chat_stream(prompt, document_name=None):
            if 'answer' in chunk and chunk['answer']:
                yield {'answer': chunk['answer']}

        # 返回sources
        sources = []
        for i, chunk in enumerate(retrieved, 1):
            source = {
                'index': i,
                'document': chunk.metadata.get('source_document', 'unknown'),
                'content': chunk.page_content,
                'metadata': chunk.metadata
            }
            if 'page' in chunk.metadata:
                source['page'] = chunk.metadata['page']
            sources.append(source)

        yield {
            'sources': sources,
            'num_sources': len(sources),
            'task_type': 'GENERAL',
            'done': True
        }

    def _extract_year(self, filename: str) -> str:
        """从文件名提取年份"""
        import re
        match = re.search(r'(19\d{2}|20\d{2})', filename)
        return match.group(1) if match else '9999'

    def _preload_documents(self) -> None:
        """
        预加载所有文档到cache
        优化首次查询性能
        """
        all_docs = self.list_documents()
        if not all_docs:
            logger.info("知识库为空，无需预加载")
            return

        logger.info(f"🚀 预加载 {len(all_docs)} 个文档到cache...")
        loaded_count = 0

        for doc_name in all_docs:
            from vector_store import generate_collection_id
            collection_id = generate_collection_id(doc_name)

            # 只加载不在cache中的
            if collection_id not in self.kb_manager.document_cache:
                retriever = self.kb_manager.get_retriever(doc_name)
                if retriever and collection_id in self.kb_manager.document_cache:
                    chunks = len(self.kb_manager.document_cache[collection_id])
                    logger.info(f"  ✅ {doc_name}: {chunks} chunks")
                    loaded_count += 1
                else:
                    logger.warning(f"  ⚠️ {doc_name}: 加载失败")

        logger.info(f"✅ 预加载完成: {loaded_count}/{len(all_docs)} 个文档")

    def ask_all_documents_smart_stream(
        self,
        question: str,
        top_k: int = 10,
        fallback_ratio: float = 0.5
    ) -> Iterator[Dict[str, Any]]:
        """
        智能模式全文档检索（流式输出）
        带LLM相关性过滤的全文档检索

        Args:
            question: 用户问题
            top_k: 向量检索的top-k
            fallback_ratio: 保底比例（0-1）

        Yields:
            流式输出字典
        """
        logger.info(f"🧠 启动智能模式全文档检索 (top_k={top_k}, fallback_ratio={fallback_ratio})")

        # 获取所有文档
        all_docs = self.list_documents()

        if not all_docs:
            yield {
                'answer': "知识库中没有任何文档。请先上传文档。",
                'sources': [],
                'done': True
            }
            return

        # 提示开始检索
        yield {'answer': '🔍 正在从所有文档中检索相关内容...\n\n', 'sources': []}

        # 使用asyncio运行异步检索
        import asyncio

        try:
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 执行智能检索
            result = loop.run_until_complete(
                self.conversation_manager.smart_all_documents_retrieve(
                    question=question,
                    all_docs=all_docs,
                    top_k=top_k,
                    fallback_ratio=fallback_ratio
                )
            )

            loop.close()

        except Exception as e:
            logger.error(f"智能检索失败: {e}")
            yield {
                'answer': f"检索失败: {str(e)}",
                'sources': [],
                'done': True
            }
            return

        relevant_chunks = result['relevant_chunks']
        sources = result['sources']
        stats = result['stats']
        fallback_used = result['fallback_used']

        # 输出统计信息
        if fallback_used:
            status_msg = f"⚠️ LLM评估未找到相关内容，使用保底策略获得 {len(relevant_chunks)} 个chunks\n\n"
        else:
            status_msg = f"✅ LLM评估完成: {stats['relevant']}/{stats['total']} 个相关chunks\n\n"

        yield {'answer': status_msg, 'sources': []}

        if not relevant_chunks:
            yield {
                'answer': "未找到相关内容。",
                'sources': [],
                'done': True
            }
            return

        # 构建增强prompt
        context_parts = []
        for i, source in enumerate(sources, 1):
            page_info = f" (第{source.get('page', '?')}页)" if 'page' in source else ""
            context_parts.append(
                f"[来源 {i}：{source['document']}{page_info}]\n{source['content']}"
            )

        context_text = "\n\n---\n\n".join(context_parts)

        enhanced_question = f"""基于以下经过LLM相关性评估后的高质量内容回答问题。

问题：{question}

经过智能筛选的相关内容：

{context_text}

---

请基于上述内容回答问题：
1. 仅使用上述文档中的事实信息
2. 明确标注信息来自哪个文档
3. 如果信息跨越多个文档，请综合分析
4. 不要推测文档中没有的内容"""

        # 保留对话历史，支持上下文记忆
        # self.clear_conversation()  # ❌ 移除清空历史，保留短期记忆

        # 流式生成答案
        for chunk in self.conversation_manager.chat_stream(enhanced_question, document_name=None):
            if 'answer' in chunk and chunk['answer']:
                yield {'answer': chunk['answer'], 'sources': []}

        # 最后返回sources
        yield {
            'answer': '',
            'sources': sources,
            'done': True,
            'metadata': {
                'total_chunks': stats['total'],
                'relevant_chunks': stats['relevant'],
                'irrelevant_chunks': stats['irrelevant'],
                'fallback_used': fallback_used,
                'documents_searched': len(all_docs)
            }
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get system status information

        Returns:
            Dictionary with status info
        """
        return {
            "model": self.get_current_model(),
            "documents": len(self.list_documents()),
            "conversation_turns": len(self.conversation_manager.get_history()) // 2,
            "retrieval_config": {
                "use_rerank": self.config.retrieval.use_rerank,
                "top_k": self.config.retrieval.top_k,
            }
        }


class MultiDocumentAssistant(DocumentAssistant):
    """
    Extended assistant with multi-document query support
    """

    def ask_multi_documents(
            self,
            question: str,
            document_names: List[str]
    ) -> str:
        """
        Ask question across multiple documents

        Args:
            question: User question
            document_names: List of documents to query

        Returns:
            Synthesized answer
        """
        logger.info(f"Querying {len(document_names)} documents")

        all_contexts = []

        # Retrieve from all documents
        for doc_name in document_names:
            retriever = self.kb_manager.get_retriever(doc_name)
            if retriever:
                try:
                    docs = retriever.get_relevant_documents(question)
                    for doc in docs:
                        all_contexts.append({
                            'source': doc_name,
                            'content': doc.page_content
                        })
                    logger.info(f"Retrieved {len(docs)} chunks from {doc_name}")
                except Exception as e:
                    logger.error(f"Failed to retrieve from {doc_name}: {e}")

        if not all_contexts:
            return "No relevant information found in the specified documents."

        # Build enhanced prompt
        context_text = "\n\n---\n\n".join([
            f"[Source: {ctx['source']}]\n{ctx['content']}"
            for ctx in all_contexts
        ])

        enhanced_question = f"""Based on the following information retrieved from multiple documents, answer the question.

Question: {question}

Retrieved Information:
{context_text}

---

Please answer based only on the information provided above. Clearly distinguish between different sources and do not speculate beyond what's in the documents."""

        # 保留对话历史，支持上下文记忆
        # self.clear_conversation()  # ❌ 移除清空历史

        # Query without retrieval (we already have the context)
        return self.ask(enhanced_question, document_name=None)