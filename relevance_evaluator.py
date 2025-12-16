"""
Relevance Evaluator - LLM批量评估chunk相关性
用于全文档检索的智能过滤
"""
import asyncio
from typing import List, Dict, Tuple
from loguru import logger
from langchain.schema import Document


class RelevanceEvaluator:
    """LLM相关性评估器"""

    def __init__(self, llm_client_manager):
        """
        初始化评估器

        Args:
            llm_client_manager: LLM客户端管理器
        """
        self.llm_manager = llm_client_manager
        self.evaluation_cache = {}  # 缓存评估结果

    async def batch_evaluate_relevance(
        self,
        question: str,
        chunks: List[Document],
        batch_size: int = 50
    ) -> Tuple[List[Document], Dict]:
        """
        批量评估chunks相关性

        Args:
            question: 用户问题
            chunks: 待评估的chunks列表
            batch_size: 批量大小

        Returns:
            (相关chunks, 评估统计)
        """
        if not chunks:
            return [], {"total": 0, "relevant": 0, "irrelevant": 0}

        logger.info(f"🧠 开始LLM批量评估 {len(chunks)} 个chunks的相关性")

        relevant_chunks = []
        stats = {
            "total": len(chunks),
            "relevant": 0,
            "irrelevant": 0,
            "cached": 0
        }

        # 分批评估
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            logger.info(f"  评估批次 {i//batch_size + 1}: {len(batch)} 个chunks")

            # 批量评估当前批次
            batch_results = await self._evaluate_batch(question, batch)

            # 收集相关的chunks
            for chunk, is_relevant, from_cache in batch_results:
                if is_relevant:
                    relevant_chunks.append(chunk)
                    stats["relevant"] += 1
                else:
                    stats["irrelevant"] += 1

                if from_cache:
                    stats["cached"] += 1

        logger.info(f"✅ 评估完成: {stats['relevant']}/{stats['total']} 个相关chunks")
        logger.info(f"  缓存命中: {stats['cached']}/{stats['total']}")

        return relevant_chunks, stats

    async def _evaluate_batch(
        self,
        question: str,
        batch: List[Document]
    ) -> List[Tuple[Document, bool, bool]]:
        """
        评估一批chunks

        Returns:
            [(chunk, is_relevant, from_cache), ...]
        """
        results = []

        # 并发评估每个chunk
        tasks = [
            self._evaluate_single(question, chunk)
            for chunk in batch
        ]

        evaluations = await asyncio.gather(*tasks)

        for chunk, is_relevant, from_cache in zip(batch, evaluations, [False]*len(batch)):
            results.append((chunk, is_relevant, from_cache))

        return results

    async def _evaluate_single(
        self,
        question: str,
        chunk: Document
    ) -> bool:
        """
        评估单个chunk是否相关

        Returns:
            True if relevant, False otherwise
        """
        # 检查缓存
        cache_key = self._get_cache_key(question, chunk)
        if cache_key in self.evaluation_cache:
            return self.evaluation_cache[cache_key]

        # 构建评估prompt
        prompt = self._build_evaluation_prompt(question, chunk)

        try:
            # 调用LLM
            response = await asyncio.to_thread(
                self.llm_manager.client.invoke,
                prompt
            )

            # 解析结果
            output = response.content.strip().upper()
            is_relevant = self._parse_relevance(output)

            # 缓存结果
            self.evaluation_cache[cache_key] = is_relevant

            return is_relevant

        except Exception as e:
            logger.error(f"评估chunk失败: {e}")
            # 失败时默认相关（保守策略）
            return True

    def _build_evaluation_prompt(self, question: str, chunk: Document) -> str:
        """构建评估prompt"""
        content = chunk.page_content[:500]  # 限制长度

        prompt = f"""请判断以下文本片段是否与问题相关。

**问题**: {question}

**文本片段**:
{content}

**判断标准**:
- 如果文本直接回答或部分回答了问题，回答"Y"
- 如果文本提供了相关背景或上下文信息，回答"Y"  
- 如果文本与问题完全无关，回答"N"

**请仅回答 Y (相关) 或 N (不相关)，不要有任何其他内容**:"""

        return prompt

    @staticmethod
    def _parse_relevance(output: str) -> bool:
        """解析LLM输出"""
        # 检查是否包含Y
        if output.startswith("Y") or "相关" in output:
            return True
        # 检查是否包含N
        elif output.startswith("N") or "不相关" in output:
            return False
        else:
            # 默认相关（保守策略）
            logger.warning(f"无法解析LLM输出: {output}，默认为相关")
            return True

    @staticmethod
    def _get_cache_key(question: str, chunk: Document) -> str:
        """生成缓存key"""
        # 使用问题和chunk内容的hash作为key
        content_hash = hash(chunk.page_content[:200])
        question_hash = hash(question)
        return f"{question_hash}_{content_hash}"

    def clear_cache(self):
        """清除缓存"""
        self.evaluation_cache.clear()
        logger.info("已清除评估缓存")