"""
API Client for Frontend
前端调用后端API的客户端封装
"""
import requests
import json
from typing import Iterator, Optional, List, Dict, Any
from loguru import logger


class RAGAPIClient:
    """
    RAG系统API客户端
    封装所有后端API调用
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化API客户端

        Args:
            base_url: API服务器地址
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = 30

    # ========== System APIs ==========

    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        response = requests.get(f"{self.base_url}/status", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    # ========== Document Management APIs ==========

    def list_documents(self) -> List[str]:
        """获取文档列表"""
        response = requests.get(f"{self.base_url}/documents", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_document_info(self, document_name: str) -> Dict[str, Any]:
        """获取文档信息"""
        response = requests.get(
            f"{self.base_url}/documents/{document_name}",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def upload_document(self, file_path: str) -> Dict[str, Any]:
        """
        上传文档

        Args:
            file_path: 文件路径

        Returns:
            响应数据
        """
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.split('/')[-1], f)}
            response = requests.post(
                f"{self.base_url}/documents/upload",
                files=files,
                timeout=60  # 上传可能需要更长时间
            )
        response.raise_for_status()
        return response.json()

    def update_document(
        self,
        document_name: str,
        file_path: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        更新文档

        Args:
            document_name: 文档名称
            file_path: 新文件路径
            force: 强制更新

        Returns:
            响应数据
        """
        with open(file_path, 'rb') as f:
            files = {'file': (document_name, f)}
            response = requests.put(
                f"{self.base_url}/documents/{document_name}",
                files=files,
                params={'force': force},
                timeout=60
            )
        response.raise_for_status()
        return response.json()

    def delete_document(self, document_name: str) -> Dict[str, Any]:
        """删除文档"""
        response = requests.delete(
            f"{self.base_url}/documents/{document_name}",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    # ========== Chat APIs ==========

    def chat(
        self,
        message: str,
        document_name: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = True
    ) -> Iterator[str]:
        """
        发送聊天消息（流式）

        Args:
            message: 用户消息
            document_name: 文档名称
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度
            stream: 是否流式

        Yields:
            响应文本块（逐字符）
        """
        payload = {
            "message": message,
            "document_name": document_name,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }

        if stream:
            response = requests.post(
                f"{self.base_url}/chat",
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            if data.get('answer'):
                                # 返回答案文本
                                yield data['answer']
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse: {data_str}")
        else:
            response = requests.post(
                f"{self.base_url}/chat",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            yield result.get('answer', '')

    def chat_all_documents(
        self,
        message: str,
        search_mode: str = "fast",
        top_k: int = 10,
        fallback_ratio: float = 0.5,
        stream: bool = True
    ) -> Iterator[Dict[str, Any]]:
        """
        全文档查询（返回完整数据结构）

        Args:
            message: 用户消息
            search_mode: 检索模式 (fast/smart)
            top_k: 检索数量
            fallback_ratio: 保底比例
            stream: 是否流式

        Yields:
            响应数据块 {'answer': str, 'sources': list, 'done': bool, ...}
        """
        payload = {
            "message": message,
            "search_mode": search_mode,
            "top_k": top_k,
            "fallback_ratio": fallback_ratio,
            "stream": stream
        }

        if stream:
            response = requests.post(
                f"{self.base_url}/chat/all-documents",
                json=payload,
                stream=True,
                timeout=180  # 智能模式可能需要更长时间
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            yield data
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse: {data_str}")
        else:
            response = requests.post(
                f"{self.base_url}/chat/all-documents",
                json=payload,
                timeout=180
            )
            response.raise_for_status()
            yield response.json()

    def clear_conversation(self) -> Dict[str, Any]:
        """清除对话历史"""
        response = requests.post(
            f"{self.base_url}/chat/clear",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_conversation_history(self) -> Dict[str, Any]:
        """获取对话历史"""
        response = requests.get(
            f"{self.base_url}/chat/history",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()  # 返回完整的响应，包含history字段

    # ========== Model Management APIs ==========

    def list_models(self) -> List[str]:
        """获取可用模型列表"""
        response = requests.get(f"{self.base_url}/models", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_current_model(self) -> str:
        """获取当前模型"""
        response = requests.get(
            f"{self.base_url}/models/current",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()["model"]

    def switch_model(self, model_name: str) -> Dict[str, Any]:
        """切换模型"""
        response = requests.put(
            f"{self.base_url}/models/switch",
            json={"model_name": model_name},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def update_parameters(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """更新模型参数"""
        response = requests.put(
            f"{self.base_url}/models/parameters",
            json={
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


# ========== Convenience Functions ==========

def create_client(base_url: str = "http://localhost:8000") -> RAGAPIClient:
    """创建API客户端实例"""
    return RAGAPIClient(base_url)


# ========== Example Usage ==========

if __name__ == "__main__":
    # 示例用法
    client = create_client()

    # 健康检查
    if client.health_check():
        print("✅ API服务器正常")
    else:
        print("❌ API服务器无法连接")
        exit(1)

    # 获取文档列表
    docs = client.list_documents()
    print(f"📚 文档列表: {docs}")

    # 获取模型列表
    models = client.list_models()
    print(f"🤖 可用模型: {models}")

    # 发送消息（流式）
    print("\n💬 开始对话:")
    for chunk in client.chat("你好", stream=True):
        if chunk.get('answer'):
            print(chunk['answer'], end='', flush=True)
    print()