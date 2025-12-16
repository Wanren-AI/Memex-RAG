"""
FastAPI Backend Server
提供RESTful API接口供前端调用
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
import tempfile
import os
import sys
from pathlib import Path
from loguru import logger
import json
import asyncio

# Add project path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_system import DocumentAssistant
from config import AvailableModels

# Initialize FastAPI app
app = FastAPI(
    title="RAG Document Assistant API",
    description="智能文档分析助手API服务",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global assistant instance
assistant: Optional[DocumentAssistant] = None


# ========== Pydantic Models ==========

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    document_name: Optional[str] = Field(None, description="文档名称")
    model: Optional[str] = Field(None, description="模型名称")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    temperature: Optional[float] = Field(None, description="温度参数")
    stream: bool = Field(True, description="是否流式输出")


class AllDocsRequest(BaseModel):
    """全文档查询请求"""
    message: str = Field(..., description="用户消息")
    search_mode: str = Field("fast", description="检索模式: fast或smart")
    top_k: int = Field(10, description="检索数量")
    fallback_ratio: float = Field(0.5, description="保底比例")
    stream: bool = Field(True, description="是否流式输出")


class ModelUpdateRequest(BaseModel):
    """模型更新请求"""
    model_name: str = Field(..., description="模型名称")


class ParametersUpdateRequest(BaseModel):
    """参数更新请求"""
    temperature: Optional[float] = Field(None, description="温度")
    max_tokens: Optional[int] = Field(None, description="最大token数")


class DocumentUpdateRequest(BaseModel):
    """文档更新请求"""
    force: bool = Field(False, description="强制更新")


class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str = Field(..., description="回答内容")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="引用来源")
    done: bool = Field(False, description="是否完成")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class DocumentInfo(BaseModel):
    """文档信息"""
    name: str
    size_mb: float
    modified_time: str
    chunk_count: int
    file_hash: str
    indexed: bool


class StatusResponse(BaseModel):
    """系统状态响应"""
    status: str
    model: str
    documents: int
    conversation_turns: int
    retrieval_config: Dict[str, Any]


class MessageResponse(BaseModel):
    """通用消息响应"""
    success: bool
    message: str
    data: Optional[Any] = None


# ========== Lifecycle Events ==========

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global assistant
    logger.info("🚀 Starting RAG API Server...")

    # Check API key
    if not os.getenv("DASHSCOPE_API_KEY"):
        logger.error("DASHSCOPE_API_KEY not set!")
        raise RuntimeError("DASHSCOPE_API_KEY environment variable is required")

    # Initialize assistant
    try:
        assistant = DocumentAssistant()
        logger.info("✅ DocumentAssistant initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DocumentAssistant: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    logger.info("👋 Shutting down RAG API Server...")


# ========== Health Check ==========

@app.get("/", tags=["System"])
async def root():
    """根路径"""
    return {
        "message": "RAG Document Assistant API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["System"])
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/status", response_model=StatusResponse, tags=["System"])
async def get_status():
    """获取系统状态"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    status_info = assistant.get_status()
    return StatusResponse(
        status="running",
        model=status_info["model"],
        documents=status_info["documents"],
        conversation_turns=status_info["conversation_turns"],
        retrieval_config=status_info["retrieval_config"]
    )


# ========== Document Management ==========

@app.get("/documents", tags=["Documents"])
async def list_documents() -> List[str]:
    """获取文档列表"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    return assistant.list_documents()


@app.get("/documents/{document_name}", response_model=DocumentInfo, tags=["Documents"])
async def get_document_info(document_name: str):
    """获取文档详细信息"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    info = assistant.get_document_info(document_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_name}")

    return DocumentInfo(**info)


@app.post("/documents/upload", response_model=MessageResponse, tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """上传文档"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    # Save uploaded file to temp location
    try:
        # 确保文件名正确编码
        original_filename = file.filename
        if isinstance(original_filename, bytes):
            original_filename = original_filename.decode('utf-8')

        logger.info(f"Uploading file: {original_filename}")

        suffix = Path(original_filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Upload to assistant (传递原始文件名)
        result = assistant.upload_document(tmp_path, original_filename=original_filename)

        # Clean up temp file
        os.unlink(tmp_path)

        if result:
            return MessageResponse(
                success=True,
                message=f"Document uploaded successfully: {original_filename}",
                data={"filename": original_filename}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to upload document")

    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/documents/{document_name}", response_model=MessageResponse, tags=["Documents"])
async def update_document(
    document_name: str,
    file: UploadFile = File(...),
    force: bool = False
):
    """更新文档"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    # Validate filename match
    if file.filename != document_name:
        raise HTTPException(
            status_code=400,
            detail=f"Filename mismatch: {file.filename} != {document_name}"
        )

    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Update document
        result = assistant.update_document(tmp_path, force=force)

        # Clean up
        os.unlink(tmp_path)

        if result:
            return MessageResponse(
                success=True,
                message=f"Document updated successfully: {document_name}",
                data={"filename": document_name}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to update document")

    except Exception as e:
        logger.error(f"Update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_name}", response_model=MessageResponse, tags=["Documents"])
async def delete_document(document_name: str):
    """删除文档"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    result = assistant.delete_document(document_name)

    if result:
        return MessageResponse(
            success=True,
            message=f"Document deleted successfully: {document_name}",
            data={"filename": document_name}
        )
    else:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_name}")


# ========== Chat / Query ==========

@app.post("/chat", tags=["Chat"])
async def chat(request: ChatRequest):
    """聊天接口（支持流式和非流式）"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    # Update model if specified
    if request.model:
        assistant.switch_model(request.model)

    # Update parameters if specified
    if request.temperature is not None or request.max_tokens is not None:
        assistant.update_parameters(
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

    # Handle document selection
    doc_name = None
    if request.document_name and request.document_name not in ["不使用知识库", "None"]:
        doc_name = request.document_name

    # Stream or non-stream response
    if request.stream:
        async def generate():
            try:
                for chunk in assistant.ask_stream(request.message, doc_name):
                    if chunk:
                        # 确保每个字符都立即发送
                        data = {"answer": chunk, "done": False}
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        # 强制刷新，确保立即发送
                        await asyncio.sleep(0)

                # Send done signal
                yield f"data: {json.dumps({'answer': '', 'done': True}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'error': str(e), 'done': True}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # Non-streaming response
        answer = assistant.ask(request.message, doc_name)
        return ChatResponse(answer=answer, sources=[], done=True)


@app.post("/chat/all-documents", tags=["Chat"])
async def chat_all_documents(request: AllDocsRequest):
    """全文档查询接口"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    if request.stream:
        async def generate():
            if request.search_mode == "smart":
                # Smart mode with LLM filtering
                # 使用同步方式调用，避免事件循环冲突
                import threading
                import queue

                result_queue = queue.Queue()
                error_queue = queue.Queue()

                def run_smart_stream():
                    try:
                        for chunk in assistant.ask_all_documents_smart_stream(
                            question=request.message,
                            top_k=request.top_k,
                            fallback_ratio=request.fallback_ratio
                        ):
                            result_queue.put(chunk)
                        result_queue.put(None)  # 结束信号
                    except Exception as e:
                        error_queue.put(e)
                        result_queue.put(None)

                # 在新线程中运行
                thread = threading.Thread(target=run_smart_stream)
                thread.start()

                while True:
                    # 检查是否有错误
                    if not error_queue.empty():
                        error = error_queue.get()
                        yield f"data: {json.dumps({'error': str(error), 'done': True}, ensure_ascii=False)}\n\n"
                        break

                    # 获取结果
                    chunk = result_queue.get()
                    if chunk is None:
                        break

                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0)  # 确保立即发送

                thread.join()
            else:
                # Fast mode - 临时禁用rerank避免SSL错误
                original_rerank = assistant.config.retrieval.use_rerank
                try:
                    # 临时禁用rerank
                    assistant.config.retrieval.use_rerank = False
                    logger.info("快速模式：已临时禁用rerank以避免SSL错误")

                    for chunk in assistant.ask_all_documents_stream(request.message):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0)
                finally:
                    # 恢复原始设置
                    assistant.config.retrieval.use_rerank = original_rerank

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # Non-streaming
        if request.search_mode == "smart":
            # Smart mode doesn't have non-streaming version
            raise HTTPException(
                status_code=400,
                detail="Smart mode only supports streaming"
            )
        else:
            result = assistant.ask_all_documents(request.message)
            return result


@app.post("/chat/clear", response_model=MessageResponse, tags=["Chat"])
async def clear_conversation():
    """清除对话历史"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    assistant.clear_conversation()
    return MessageResponse(
        success=True,
        message="Conversation history cleared"
    )


@app.get("/chat/history", tags=["Chat"])
async def get_conversation_history():
    """获取对话历史"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    history = assistant.get_conversation_history()
    return {"history": [{"role": msg.type, "content": msg.content} for msg in history]}


# ========== Model Management ==========

@app.get("/models", tags=["Models"])
async def list_models() -> List[str]:
    """获取可用模型列表"""
    return AvailableModels.all()


@app.get("/models/current", tags=["Models"])
async def get_current_model() -> Dict[str, str]:
    """获取当前使用的模型"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    return {"model": assistant.get_current_model()}


@app.put("/models/switch", response_model=MessageResponse, tags=["Models"])
async def switch_model(request: ModelUpdateRequest):
    """切换模型"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    result = assistant.switch_model(request.model_name)

    if result:
        return MessageResponse(
            success=True,
            message=f"Switched to model: {request.model_name}",
            data={"model": request.model_name}
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to switch to model: {request.model_name}"
        )


@app.put("/models/parameters", response_model=MessageResponse, tags=["Models"])
async def update_parameters(request: ParametersUpdateRequest):
    """更新模型参数"""
    if not assistant:
        raise HTTPException(status_code=500, detail="Assistant not initialized")

    assistant.update_parameters(
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )

    return MessageResponse(
        success=True,
        message="Parameters updated",
        data={
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
    )


# ========== Error Handlers ==========

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


def main():
    """启动API服务器"""
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()