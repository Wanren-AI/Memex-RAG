"""
Conversation Management Module
Handles chat interactions with history management
对话管理 交互控制

"""
from typing import Iterator, Optional, Dict, Any, List
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.messages import AIMessageChunk
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import AddableDict
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from loguru import logger

from llm_client import LLMClientManager
from knowledge_base import KnowledgeBaseManager
from relevance_evaluator import RelevanceEvaluator


class ConversationManager:
    """
    Manages conversational interactions
    Supports both knowledge-based and general chat
    """

    # System prompts 有文档上下文，强调"基于文档回答"
    KB_SYSTEM_PROMPT = """You are a professional knowledge assistant.
Use the retrieved context to answer questions. If you don't know the answer, 
clearly state that you couldn't find the information.

Context:
{context}
"""
    #无文档，自由对话
    GENERAL_SYSTEM_PROMPT = """You are a helpful assistant that answers 
various questions to the best of your ability."""

    MAX_HISTORY_TURNS = 3  # 保留最近3轮对话（6条消息

    def __init__(
        self,
        llm_manager: LLMClientManager,
        kb_manager: KnowledgeBaseManager
    ):
        """
        Initialize conversation manager

        Args:
            llm_manager: LLM client manager
            kb_manager: Knowledge base manager
        """
        self.llm_manager = llm_manager
        self.kb_manager = kb_manager
        self.chat_history = ChatMessageHistory()

        # Initialize relevance evaluator for smart mode
        self.relevance_evaluator = RelevanceEvaluator(llm_manager)

        # Create prompts
        self.kb_prompt = ChatPromptTemplate.from_messages([
            ("system", self.KB_SYSTEM_PROMPT),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ])

        self.general_prompt = ChatPromptTemplate.from_messages([
            ("system", self.GENERAL_SYSTEM_PROMPT),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ])

    def _manage_history(self) -> None:
        """Manage conversation history to prevent context overflow"""
        """防止上下文过长"""
        max_messages = self.MAX_HISTORY_TURNS * 2
        if len(self.chat_history.messages) >= max_messages:
            self.chat_history.messages = self.chat_history.messages[-max_messages:]
            logger.debug(f"History trimmed to {max_messages} messages")

    def _build_chain(self, document_name: Optional[str]):
        """
        Build conversation chain based on context

        Args:
            document_name: Optional document for knowledge-based chat

        Returns:
            Runnable chain with history
        """
        self._manage_history()

        llm_client = self.llm_manager.client

        if document_name:
            # Knowledge-based chain
            retriever = self.kb_manager.get_retriever(document_name)

            if retriever is None:
                logger.warning(f"Retriever not found for: {document_name}")
                chain = self.general_prompt | llm_client | self._streaming_parser
            else:
                qa_chain = create_stuff_documents_chain(llm_client, self.kb_prompt)
                chain = create_retrieval_chain(retriever, qa_chain)
                logger.info("Knowledge-based chain created")
        else:
            # General conversation chain
            chain = self.general_prompt | llm_client | self._streaming_parser
            logger.info("General conversation chain created")

        # Wrap with history
        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: self.chat_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

        return chain_with_history

    @staticmethod
    def _streaming_parser(chunks: Iterator[AIMessageChunk]) -> Iterator[Dict]:
        """
        流式返回答案，边生成边输出
        Parse streaming chunks

        Args:
            chunks: Stream of AI message chunks

        Yields:
            Dictionaries with answer content
        """
        for chunk in chunks:
            yield AddableDict({'answer': chunk.content})#分批返回此对象

    def chat(
        self,
        question: str,
        document_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronous chat interaction

        Args:
            question: User question
            document_name: Optional document for context

        Returns:
            Response dictionary
        """
        chain = self._build_chain(document_name)

        response = chain.invoke(
            {"input": question},
            {"configurable": {"session_id": "default"}}
        )

        logger.info(f"Chat completed for question: {question[:50]}...")
        return response

    def chat_stream(
        self,
        question: str,
        document_name: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Streaming chat interaction

        Args:
            question: User question
            document_name: Optional document for context

        Yields:
            Response chunks
        """
        chain = self._build_chain(document_name)

        logger.info(f"Starting stream for: {question[:50]}...")

        for chunk in chain.stream(
            {"input": question},
            {"configurable": {"session_id": "default"}}
        ):
            yield chunk

    def clear_history(self) -> None:
        """Clear conversation history"""
        self.chat_history.clear()
        logger.info("Conversation history cleared")

    def get_history(self) -> list:
        """
        Get conversation history

        Returns:
            List of messages
        """
        return self.chat_history.messages

    def get_history_summary(self) -> Dict[str, int]:
        """
        Get history statistics

        Returns:
            Dictionary with history stats
        """
        return {
            "total_messages": len(self.chat_history.messages),
            "conversation_turns": len(self.chat_history.messages) // 2
        }

    async def smart_all_documents_retrieve(
        self,
        question: str,
        all_docs: List[str],
        top_k: int = 10,
        fallback_ratio: float = 0.5
    ) -> Dict[str, Any]:
        """
        智能模式全文档检索（带LLM相关性过滤）

        工作流程：
        1. 从所有文档向量检索Top-K chunks
        2. 用LLM批量评估每个chunk是否相关
        3. 如果没有相关chunk，则rerank后取前K*fallback_ratio个

        Args:
            question: 用户问题
            all_docs: 所有文档名列表
            top_k: 向量检索的top-k
            fallback_ratio: 保底比例

        Returns:
            {
                'relevant_chunks': List[Document],
                'sources': List[Dict],
                'stats': Dict,
                'fallback_used': bool
            }
        """
        logger.info(f"🧠 智能模式全文档检索: {len(all_docs)} 个文档, top_k={top_k}")

        # Step 1: 从所有文档收集chunks（带分数）
        all_chunks_with_scores = []  # 存储 (chunk, score, doc_name)

        for doc_name in all_docs:
            retriever = self.kb_manager.get_retriever(doc_name)
            if retriever:
                try:
                    # 获取带分数的检索结果
                    docs_with_scores = retriever.get_relevant_documents(question)

                    # 为每个chunk添加来源信息
                    for i, doc in enumerate(docs_with_scores):
                        # 使用检索排名作为分数（排名越靠前分数越高）
                        score = 1.0 / (i + 1)  # 第1个得分1.0，第2个0.5，第3个0.33...
                        all_chunks_with_scores.append((doc, score, doc_name))

                    logger.info(f"  从 {doc_name} 检索到 {len(docs_with_scores)} 个chunks")
                except Exception as e:
                    logger.error(f"  从 {doc_name} 检索失败: {e}")

        if not all_chunks_with_scores:
            return {
                'relevant_chunks': [],
                'sources': [],
                'stats': {'total': 0, 'relevant': 0, 'irrelevant': 0},
                'fallback_used': False
            }

        # Step 2: 按分数排序，只取前top_k个进行LLM评估
        all_chunks_with_scores.sort(key=lambda x: x[1], reverse=True)
        top_chunks = all_chunks_with_scores[:top_k]

        logger.info(f"  总共收集了 {len(all_chunks_with_scores)} 个chunks")
        logger.info(f"  按分数排序后取前 {len(top_chunks)} 个进行LLM评估")

        # 提取chunks和来源映射
        all_chunks = [chunk for chunk, score, doc_name in top_chunks]
        chunk_to_source = {i: doc_name for i, (chunk, score, doc_name) in enumerate(top_chunks)}

        # Step 2: LLM批量评估相关性
        relevant_chunks, eval_stats = await self.relevance_evaluator.batch_evaluate_relevance(
            question=question,
            chunks=all_chunks,
            batch_size=50
        )

        fallback_used = False

        # Step 3: 保底策略 - 如果没有相关chunk
        if not relevant_chunks:
            logger.warning("⚠️ 没有找到相关chunk，启动保底策略")
            fallback_used = True

            # Rerank所有chunks

            try:
                # 使用rerank进一步筛选
                reranker = self.kb_manager.rerank_manager.get_reranker()

                if reranker:
                    # Rerank所有chunks
                    reranked = reranker.compress_documents(all_chunks, question)

                    # 取前k*fallback_ratio个
                    fallback_count = max(1, int(top_k * fallback_ratio))
                    relevant_chunks = reranked[:fallback_count]

                    logger.info(f"  保底策略: rerank后取前 {len(relevant_chunks)} 个chunks")
                else:
                    # 如果没有reranker，直接取前k*fallback_ratio个
                    fallback_count = max(1, int(top_k * fallback_ratio))
                    relevant_chunks = all_chunks[:fallback_count]
                    logger.info(f"  保底策略: 直接取前 {len(relevant_chunks)} 个chunks")

            except Exception as e:
                logger.error(f"保底策略失败: {e}")
                # 最后的保底：直接取原始top-k的一半
                fallback_count = max(1, int(top_k * fallback_ratio))
                relevant_chunks = all_chunks[:fallback_count]

        # Format sources
        sources = []
        for i, chunk in enumerate(relevant_chunks, 1):
            # 找到chunk对应的源文档
            chunk_id = all_chunks.index(chunk) if chunk in all_chunks else -1
            source_doc = chunk_to_source.get(chunk_id, "Unknown")

            source = {
                'index': i,
                'document': source_doc,
                'content': chunk.page_content,
                'metadata': chunk.metadata
            }
            if 'page' in chunk.metadata:
                source['page'] = chunk.metadata['page']
            sources.append(source)

        return {
            'relevant_chunks': relevant_chunks,
            'sources': sources,
            'stats': eval_stats,
            'fallback_used': fallback_used
        }