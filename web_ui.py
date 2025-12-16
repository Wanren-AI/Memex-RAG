"""
Enhanced Web UI with All Documents Search and Source Citations
增强版Web UI：支持全知识库检索和引用来源显示
"""
import gradio as gr
from typing import List, Dict, Any
import sys
import os
from loguru import logger

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_system import DocumentAssistant

# Initialize assistant
assistant = DocumentAssistant()


def format_sources_html(sources: List[Dict[str, Any]]) -> str:
    """
    Format sources as HTML for display

    Args:
        sources: List of source dictionaries

    Returns:
        HTML string
    """
    if not sources:
        return ""

    html = '<div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #2563eb;">'
    html += '<h3 style="color: #2563eb; margin-top: 0;">📚 引用来源</h3>'

    # Show up to 5 sources
    for src in sources[:5]:
        doc_name = src['document']
        index = src['index']
        content = src['content']

        # Smart location display
        if 'page' in src and src['page'] != '?':
            location = f"第{src['page']}页"
        else:
            location = f"片段{index}"

        # Truncate content
        if len(content) > 150:
            content_display = content[:150] + "..."
        else:
            content_display = content

        html += f'''
        <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 5px;">
            <div style="font-weight: bold; color: #1e40af;">
                [{index}] {doc_name} ({location})
            </div>
            <div style="margin-top: 5px; color: #4b5563; font-size: 0.9em; line-height: 1.5;">
                {content_display}
            </div>
        </div>
        '''

    if len(sources) > 5:
        html += f'<div style="margin-top: 10px; color: #6b7280; font-style: italic;">... 还有 {len(sources) - 5} 个引用</div>'

    html += '</div>'
    return html


def upload_document(file):
    """Upload document to knowledge base"""
    if file is None:
        return "❌ 请选择文件", gr.update(), gr.update()

    try:
        logger.info(f"Uploading file: {file.name}")
        result = assistant.upload_document(file.name)

        if result:
            # 更新文档列表
            updated_docs = load_documents()
            doc_info = get_document_list_html()
            return (
                f"✅ 上传成功: {os.path.basename(file.name)}",
                gr.update(choices=updated_docs, value=updated_docs[-1] if len(updated_docs) > 2 else "不使用知识库"),
                doc_info
            )
        else:
            return "❌ 上传失败", gr.update(), gr.update()
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return f"❌ 上传失败: {str(e)}", gr.update(), gr.update()


def update_document(file, selected_doc_name, force_update):
    """Update existing document"""
    if file is None:
        return "❌ 请选择要更新的文件", gr.update()

    if not selected_doc_name or selected_doc_name == "请选择要更新的文档":
        return "❌ 请先选择要更新的文档", gr.update()

    try:
        logger.info(f"Updating document: {selected_doc_name} with {file.name}")

        # Check filename match
        import os
        file_basename = os.path.basename(file.name)
        if file_basename != selected_doc_name:
            warning_msg = f"⚠️ 文件名不匹配！\n知识库: {selected_doc_name}\n新文件: {file_basename}\n"
            return warning_msg + "❌ 更新取消（文件名必须匹配）", gr.update()

        # Perform update
        result = assistant.update_document(file.name, force=force_update)

        if result:
            doc_info = get_document_list_html()
            return f"✅ 更新成功: {selected_doc_name}", doc_info
        else:
            return "❌ 更新失败", gr.update()

    except Exception as e:
        logger.error(f"Update error: {e}")
        return f"❌ 更新失败: {str(e)}", gr.update()


def delete_document(selected_doc_name):
    """Delete document from knowledge base"""
    if not selected_doc_name or selected_doc_name == "请选择要删除的文档":
        return "❌ 请先选择要删除的文档", gr.update(), gr.update()

    try:
        logger.info(f"Deleting document: {selected_doc_name}")
        result = assistant.delete_document(selected_doc_name)

        if result:
            updated_docs = load_documents()
            doc_info = get_document_list_html()
            return (
                f"✅ 删除成功: {selected_doc_name}",
                gr.update(choices=updated_docs, value="不使用知识库"),
                doc_info
            )
        else:
            return "❌ 删除失败", gr.update(), gr.update()

    except Exception as e:
        logger.error(f"Delete error: {e}")
        return f"❌ 删除失败: {str(e)}", gr.update(), gr.update()


def get_document_list_html():
    """Get formatted HTML list of documents with info"""
    docs = assistant.list_documents()

    if not docs:
        return "<div style='padding: 20px; text-align: center; color: #6b7280;'>📁 知识库为空</div>"

    html = "<div style='padding: 10px;'>"
    html += f"<h4 style='color: #2563eb; margin-bottom: 15px;'>📚 知识库文档 ({len(docs)}个)</h4>"

    for doc in docs:
        info = assistant.get_document_info(doc)
        if info:
            html += f"""
            <div style='margin: 10px 0; padding: 12px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #2563eb;'>
                <div style='font-weight: bold; color: #1e40af; margin-bottom: 5px;'>📄 {info['name']}</div>
                <div style='font-size: 0.85em; color: #6b7280;'>
                    <div>📊 大小: {info['size_mb']} MB</div>
                    <div>🕒 修改: {info['modified_time']}</div>
                    <div>✂️ 分块: {info['chunk_count']}</div>
                    <div>🔑 哈希: {info['file_hash'][:16]}...</div>
                </div>
            </div>
            """

    html += "</div>"
    return html


def refresh_document_list():
    """Refresh document list display"""
    return get_document_list_html(), gr.update(choices=load_documents())


def load_documents():
    """Load available documents"""
    docs = assistant.list_documents()
    return ["不使用知识库", "✨ 全部文档"] + docs


def chat_response_wrapper(
        message: str,
        history: List,
        selected_doc: str,
        model: str,
        max_length: int,
        temperature: float,
        search_mode: str = "⚡ 快速模式",
        smart_top_k: int = 10,
        fallback_ratio: float = 0.5
):
    """
    Wrapper to immediately clear input and show processing
    """
    # 立即返回清空的输入框和带处理提示的对话
    if history is None:
        history = []

    # 立即显示问题和处理状态
    new_history = history + [[message, "⏳ 正在处理..."]]

    # 同时返回空字符串（清空输入）和更新的历史
    yield "", new_history

    # 然后调用实际的处理函数
    for updated_history in chat_response(
        message, history, selected_doc, model, max_length, temperature,
        search_mode, smart_top_k, fallback_ratio
    ):
        yield "", updated_history


def chat_response(
        message: str,
        history: List,
        selected_doc: str,
        model: str,
        max_length: int,
        temperature: float,
        search_mode: str = "⚡ 快速模式",
        smart_top_k: int = 10,
        fallback_ratio: float = 0.5
):
    """
    Generate chat response with source citations
    支持快速模式和智能模式

    Args:
        message: User message
        history: Chat history
        selected_doc: Selected document
        model: Model name
        max_length: Max tokens
        temperature: Temperature
        search_mode: 检索模式（快速/智能）
        smart_top_k: 智能模式的top-k
        fallback_ratio: 保底比例

    Returns:
        Updated history
    """
    import time

    if not message.strip():
        return history

    # Initialize history if None
    if history is None:
        history = []

    # 记录开始时间
    start_time = time.time()

    # 立即显示用户问题
    history = history + [[message, "⏳ 正在处理..."]]
    yield history

    try:
        # Update model parameters
        assistant.switch_model(model)
        assistant.update_parameters(temperature, max_length)

        # Determine query mode
        if selected_doc == "✨ 全部文档":
            # All documents mode
            logger.info(f"使用全文档检索 - 模式: {search_mode}")

            # Stream response
            response_text = ""
            sources = []
            chunk_count = 0
            first_chunk = True

            # 根据模式选择不同的检索方法
            if search_mode == "🧠 智能模式":
                logger.info(f"智能模式参数: top_k={smart_top_k}, fallback_ratio={fallback_ratio}")
                stream_generator = assistant.ask_all_documents_smart_stream(
                    message,
                    top_k=smart_top_k,
                    fallback_ratio=fallback_ratio
                )
            else:
                # 快速模式（原始方法）
                stream_generator = assistant.ask_all_documents_stream(message)

            for chunk in stream_generator:
                if 'answer' in chunk:
                    if first_chunk:
                        # 计算处理时间（从提交到第一个token）
                        processing_time = time.time() - start_time
                        logger.info(f"Processing time: {processing_time:.2f}s")
                        first_chunk = False

                    response_text += chunk['answer']
                    chunk_count += 1
                    # Yield updated history for every chunk
                    history[-1][1] = response_text
                    yield history

                if 'sources' in chunk:
                    sources = chunk.get('sources', [])

                # 智能模式的元数据
                if 'metadata' in chunk:
                    metadata = chunk['metadata']
                    logger.info(f"智能模式统计: {metadata}")

            logger.info(f"Received {chunk_count} chunks")

            # Add sources to response
            if sources:
                sources_html = format_sources_html(sources)
                # 添加处理时间信息
                total_time = time.time() - start_time
                time_info = f'<div style="margin-top: 10px; color: #9ca3af; font-size: 0.85em; text-align: right;">⏱️ 处理时间: {total_time:.2f}秒 | 模式: {search_mode}</div>'
                final_response = response_text + "\n\n" + sources_html + time_info
            else:
                total_time = time.time() - start_time
                time_info = f'\n\n<div style="color: #9ca3af; font-size: 0.85em; text-align: right;">⏱️ 处理时间: {total_time:.2f}秒 | 模式: {search_mode}</div>'
                final_response = response_text + time_info

            history[-1][1] = final_response
            yield history

        elif selected_doc != "不使用知识库":
            # Single document mode
            logger.info(f"Using single document: {selected_doc}")

            response_text = ""
            chunk_count = 0
            first_chunk = True

            for chunk in assistant.ask_stream(message, selected_doc):
                if first_chunk:
                    # 计算处理时间
                    processing_time = time.time() - start_time
                    logger.info(f"Processing time: {processing_time:.2f}s")
                    first_chunk = False

                response_text += chunk
                chunk_count += 1
                history[-1][1] = response_text
                yield history

            logger.info(f"Received {chunk_count} chunks")

            # 添加总处理时间
            total_time = time.time() - start_time
            time_info = f'\n\n<div style="color: #9ca3af; font-size: 0.85em; text-align: right;">⏱️ 处理时间: {total_time:.2f}秒</div>'
            history[-1][1] = response_text + time_info
            yield history

        else:
            # General chat mode
            logger.info("Using general chat mode")

            response_text = ""
            chunk_count = 0
            first_chunk = True

            for chunk in assistant.ask_stream(message, None):
                if first_chunk:
                    # 计算处理时间
                    processing_time = time.time() - start_time
                    logger.info(f"Processing time: {processing_time:.2f}s")
                    first_chunk = False

                response_text += chunk
                chunk_count += 1
                history[-1][1] = response_text
                yield history

            logger.info(f"Received {chunk_count} chunks")

            # 添加总处理时间
            total_time = time.time() - start_time
            time_info = f'\n\n<div style="color: #9ca3af; font-size: 0.85em; text-align: right;">⏱️ 处理时间: {total_time:.2f}秒</div>'
            history[-1][1] = response_text + time_info
            yield history

    except Exception as e:
        logger.error(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        total_time = time.time() - start_time
        error_msg = f"❌ 错误: {str(e)}\n\n<div style='color: #9ca3af; font-size: 0.85em;'>⏱️ 失败时间: {total_time:.2f}秒</div>"
        history[-1][1] = error_msg
        yield history


def clear_conversation():
    """Clear conversation history"""
    assistant.clear_conversation()
    return []


def create_interface():
    """Create Gradio interface"""

    # Custom CSS
    custom_css = """
    .gradio-container {
        max-width: 1400px !important;
    }
    .source-citation {
        background: #f8f9fa;
        border-left: 4px solid #2563eb;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
    }
    """

    with gr.Blocks(
            theme=gr.themes.Soft(),
            css=custom_css,
            title="RAG 文档分析助手"
    ) as interface:
        # Header
        gr.HTML("""
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #2563eb; margin-bottom: 10px;">
                    📚 RAG 文档分析助手
                </h1>
                <p style="color: #6b7280; font-size: 1.1em;">
                    支持全知识库检索 · 智能引用来源 · 多文档分析 · 文档更新管理
                </p>
            </div>
        """)

        # Main Tabs
        with gr.Tabs() as tabs:
            # Tab 1: Chat Interface
            with gr.Tab("💬 对话", id="chat_tab"):
                with gr.Row():
                    # Left panel: Chat
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            label="对话",
                            height=500,
                            show_label=True,
                            avatar_images=None
                        )

                        with gr.Row():
                            msg = gr.Textbox(
                                label="",
                                placeholder="输入你的问题... (支持跨文档综合查询)",
                                lines=2,
                                scale=4,
                                show_label=False
                            )
                            submit_btn = gr.Button("发送", variant="primary", scale=1)

                        with gr.Row():
                            clear_btn = gr.Button("清除对话", size="sm")

                    # Right panel: Settings
                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ 设置")

                        # Model selection
                        model_dropdown = gr.Dropdown(
                            choices=assistant.get_available_models(),
                            value=assistant.get_current_model(),
                            label="选择模型",
                            info="选择AI模型"
                        )

                        # Document selection
                        doc_dropdown = gr.Dropdown(
                            choices=load_documents(),
                            value="不使用知识库",
                            label="选择文档",
                            info="选择知识库来源",
                            interactive=True
                        )

                        gr.Markdown("""
                        **💡 提示**：
                        - 选择"✨ 全部文档"可检索所有知识库
                        - 支持跨文档综合分析
                        - 自动显示引用来源
                        """)

                        # 全文档检索模式选择
                        gr.Markdown("### 🎯 全文档检索模式")

                        search_mode = gr.Radio(
                            choices=["⚡ 快速模式", "🧠 智能模式"],
                            value="⚡ 快速模式",
                            label="检索策略",
                            info="仅在选择'全部文档'时生效"
                        )

                        with gr.Accordion("模式说明", open=False):
                            gr.Markdown("""
                            **⚡ 快速模式**（推荐）
                            - 纯向量检索
                            - 响应速度：1-3秒
                            - 适合：常规查询
                            
                            **🧠 智能模式**（精准）
                            - 向量检索 + LLM相关性评估
                            - 响应速度：8-15秒
                            - 适合：需要高精度的复杂查询
                            - 自动过滤不相关内容
                            - 保底策略：确保有结果返回
                            """)

                        # 智能模式参数
                        with gr.Accordion("智能模式参数", open=False):
                            smart_top_k = gr.Slider(
                                minimum=5,
                                maximum=20,
                                value=10,
                                step=1,
                                label="Top-K",
                                info="向量检索返回的chunks数量"
                            )

                            fallback_ratio = gr.Slider(
                                minimum=0.2,
                                maximum=0.8,
                                value=0.5,
                                step=0.1,
                                label="保底比例",
                                info="无相关结果时保留的比例"
                            )

                        # Parameters
                        max_length_slider = gr.Slider(
                            minimum=500,
                            maximum=8000,
                            value=3000,
                            step=100,
                            label="最大回答长度",
                            info="控制回答的最大字数"
                        )

                        temperature_slider = gr.Slider(
                            minimum=0.0,
                            maximum=1.0,
                            value=0.7,
                            step=0.1,
                            label="温度",
                            info="控制回答的创造性"
                        )

            # Tab 2: Document Management
            with gr.Tab("📁 文档管理", id="doc_mgmt_tab"):
                gr.Markdown("## 文档管理中心")

                with gr.Row():
                    # Left: Document list
                    with gr.Column(scale=2):
                        gr.Markdown("### 📚 当前文档")
                        doc_list_display = gr.HTML(
                            value=get_document_list_html(),
                            label="文档列表"
                        )
                        refresh_btn = gr.Button("🔄 刷新列表", size="sm")

                    # Right: Operations
                    with gr.Column(scale=1):
                        # Upload section
                        with gr.Group():
                            gr.Markdown("### 📤 上传文档")
                            upload_file = gr.File(
                                label="选择文件",
                                file_types=[".txt", ".pdf", ".docx", ".md", ".csv"]
                            )
                            upload_btn_mgmt = gr.Button("上传", variant="primary")
                            upload_status_mgmt = gr.Textbox(
                                label="上传状态",
                                interactive=False,
                                show_label=False,
                                placeholder="等待操作..."
                            )

                        gr.Markdown("---")

                        # Update section
                        with gr.Group():
                            gr.Markdown("### 🔄 更新文档")
                            update_doc_select = gr.Dropdown(
                                choices=["请选择要更新的文档"] + assistant.list_documents(),
                                value="请选择要更新的文档",
                                label="选择文档",
                                info="选择要更新的文档"
                            )
                            update_file = gr.File(
                                label="选择新文件（文件名必须相同）",
                                file_types=[".txt", ".pdf", ".docx", ".md", ".csv"]
                            )
                            force_update_check = gr.Checkbox(
                                label="强制更新（即使未变化）",
                                value=False,
                                info="勾选后会跳过变化检测"
                            )
                            update_btn = gr.Button("更新", variant="secondary")
                            update_status = gr.Textbox(
                                label="更新状态",
                                interactive=False,
                                show_label=False,
                                placeholder="等待操作..."
                            )

                        gr.Markdown("---")

                        # Delete section
                        with gr.Group():
                            gr.Markdown("### 🗑️ 删除文档")
                            delete_doc_select = gr.Dropdown(
                                choices=["请选择要删除的文档"] + assistant.list_documents(),
                                value="请选择要删除的文档",
                                label="选择文档",
                                info="⚠️ 删除后无法恢复"
                            )
                            delete_btn = gr.Button("删除", variant="stop")
                            delete_status = gr.Textbox(
                                label="删除状态",
                                interactive=False,
                                show_label=False,
                                placeholder="等待操作..."
                            )

                # Tips
                gr.Markdown("""
                ---
                ### 💡 使用提示

                **上传文档**：
                - 支持格式：TXT, PDF, DOCX, MD, CSV
                - 上传后自动索引和向量化
                - 可在对话中直接使用

                **更新文档**：
                - 智能检测文件变化（基于MD5哈希）
                - 文件未变化时自动跳过更新
                - 文件名必须与知识库中的文件名完全一致
                - 强制更新适用于重新索引场景

                **删除文档**：
                - 删除操作不可恢复
                - 会同时删除文件和向量索引
                - 删除后需刷新文档列表
                """)

        # Event handlers - Chat Tab
        msg.submit(
            chat_response_wrapper,
            [msg, chatbot, doc_dropdown, model_dropdown, max_length_slider, temperature_slider,
             search_mode, smart_top_k, fallback_ratio],
            [msg, chatbot]
        )

        submit_btn.click(
            chat_response_wrapper,
            [msg, chatbot, doc_dropdown, model_dropdown, max_length_slider, temperature_slider,
             search_mode, smart_top_k, fallback_ratio],
            [msg, chatbot]
        )

        clear_btn.click(
            clear_conversation,
            None,
            chatbot,
            queue=False
        )

        # Event handlers - Document Management Tab
        # Upload
        upload_btn_mgmt.click(
            upload_document,
            upload_file,
            [upload_status_mgmt, doc_dropdown, doc_list_display]
        ).then(
            # Update management dropdowns after upload
            lambda: (
                gr.update(choices=["请选择要更新的文档"] + assistant.list_documents()),
                gr.update(choices=["请选择要删除的文档"] + assistant.list_documents())
            ),
            None,
            [update_doc_select, delete_doc_select]
        )

        # Update
        update_btn.click(
            update_document,
            [update_file, update_doc_select, force_update_check],
            [update_status, doc_list_display]
        )

        # Delete
        delete_btn.click(
            delete_document,
            delete_doc_select,
            [delete_status, doc_dropdown, doc_list_display]
        ).then(
            # Update management dropdowns after delete
            lambda: (
                gr.update(choices=["请选择要更新的文档"] + assistant.list_documents()),
                gr.update(choices=["请选择要删除的文档"] + assistant.list_documents())
            ),
            None,
            [update_doc_select, delete_doc_select]
        )

        # Refresh
        refresh_btn.click(
            refresh_document_list,
            None,
            [doc_list_display, doc_dropdown],
            queue=False
        ).then(
            # Update management dropdowns after refresh
            lambda: (
                gr.update(choices=["请选择要更新的文档"] + assistant.list_documents()),
                gr.update(choices=["请选择要删除的文档"] + assistant.list_documents())
            ),
            None,
            [update_doc_select, delete_doc_select]
        )

        # Footer
        gr.HTML("""
            <div style="text-align: center; margin-top: 30px; padding: 20px; color: #6b7280;">
                <p>💡 <strong>使用提示</strong>：</p>
                <p>
                    • 选择"✨ 全部文档"进行全知识库检索<br>
                    • 系统会自动显示引用来源和页码<br>
                    • 适合跨文档分析和长期趋势研究
                </p>
            </div>
        """)

    return interface


def main():
    """Launch the application"""
    logger.info("Starting Enhanced Web UI...")

    # Check API key
    if not os.getenv("DASHSCOPE_API_KEY"):
        logger.error("DASHSCOPE_API_KEY not set!")
        print("❌ 错误: 未设置 DASHSCOPE_API_KEY")
        print("请设置环境变量:")
        print("  export DASHSCOPE_API_KEY=your_key")
        return

    # Create and launch interface
    interface = create_interface()

    interface.queue()  # 启用队列支持流式输出
    interface.launch(
        server_name="127.0.0.1",
        server_port=7861,          # 改为7861避免冲突
        share=False,
        inbrowser=True,
        show_error=True
    )


if __name__ == "__main__":
    main()