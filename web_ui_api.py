"""
Enhanced Web UI with API Client
完全参照原始web_ui.py的样式和功能
前后端分离版本
"""
import gradio as gr
from typing import List, Optional, Dict, Any
import sys
import os
from loguru import logger
from pathlib import Path
import time

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_client import create_client

# Initialize API client
api_client = create_client("http://localhost:8000")


def format_sources_html(sources: List[Dict[str, Any]]) -> str:
    """Format sources as HTML for display - 使用强制样式确保可见"""
    if not sources:
        return ""

    # 使用Markdown格式，更容易被Gradio正确渲染
    result = "\n\n---\n\n### 📚 引用来源\n\n"

    for src in sources[:5]:
        doc_name = src['document']
        index = src['index']
        content = src['content']

        if 'page' in src and src['page'] != '?':
            location = f"第{src['page']}页"
        else:
            location = f"片段{index}"

        # 截断内容
        if len(content) > 150:
            content_display = content[:150] + "..."
        else:
            content_display = content

        # 使用Markdown格式
        result += f"**[{index}] {doc_name} ({location})**\n\n"
        result += f"> {content_display}\n\n"

    if len(sources) > 5:
        result += f"\n*... 还有 {len(sources) - 5} 个引用*\n"

    return result


def upload_document(file):
    """Upload document"""
    if file is None:
        return "❌ 请选择文件", gr.update(), gr.update()

    try:
        result = api_client.upload_document(file.name)
        if result.get("success"):
            updated_docs = load_documents()
            doc_info = get_document_list_html()
            return (
                f"✅ 上传成功: {os.path.basename(file.name)}",
                gr.update(choices=updated_docs, value=updated_docs[-1] if len(updated_docs) > 2 else "不使用知识库"),
                doc_info
            )
        return f"❌ 上传失败", gr.update(), gr.update()
    except Exception as e:
        return f"❌ {str(e)}", gr.update(), gr.update()


def update_document(file, selected_doc_name, force_update):
    """Update document"""
    if file is None or not selected_doc_name or selected_doc_name == "请选择要更新的文档":
        return "❌ 请选择文件和文档", gr.update()

    try:
        file_basename = os.path.basename(file.name)
        if file_basename != selected_doc_name:
            return f"⚠️ 文件名不匹配\n❌ 更新取消", gr.update()

        result = api_client.update_document(selected_doc_name, file.name, force=force_update)
        if result.get("success"):
            return f"✅ 更新成功: {selected_doc_name}", get_document_list_html()
        return f"❌ 更新失败", gr.update()
    except Exception as e:
        return f"❌ {str(e)}", gr.update()


def delete_document(selected_doc_name):
    """Delete document"""
    if not selected_doc_name or selected_doc_name == "请选择要删除的文档":
        return "❌ 请先选择文档", gr.update(), gr.update()

    try:
        result = api_client.delete_document(selected_doc_name)
        if result.get("success"):
            updated_docs = load_documents()
            return (
                f"✅ 删除成功: {selected_doc_name}",
                gr.update(choices=updated_docs, value="不使用知识库"),
                get_document_list_html()
            )
        return "❌ 删除失败", gr.update(), gr.update()
    except Exception as e:
        return f"❌ {str(e)}", gr.update(), gr.update()


def get_document_list_html():
    """Get document list HTML"""
    try:
        docs = api_client.list_documents()
    except:
        return "<div style='padding: 20px; text-align: center; color: #ef4444;'>❌ 无法连接API</div>"

    if not docs:
        return "<div style='padding: 20px; text-align: center; color: #6b7280;'>📁 知识库为空</div>"

    html = f"<div style='padding: 10px;'><h4 style='color: #2563eb !important;'>📚 知识库文档 ({len(docs)}个)</h4>"

    for doc in docs:
        try:
            info = api_client.get_document_info(doc)
            if info:
                html += f"""
                <div style='margin: 10px 0; padding: 12px; background: #f3f4f6 !important; border-radius: 8px; border-left: 4px solid #2563eb;'>
                    <div style='font-weight: bold; color: #1e40af !important;'>📄 {info['name']}</div>
                    <div style='font-size: 0.85em; color: #374151 !important;'>
                        <div style='color: #4b5563 !important;'>📊 {info['size_mb']} MB | ✂️ {info['chunk_count']} 块</div>
                        <div style='color: #4b5563 !important;'>🕒 {info['modified_time']}</div>
                    </div>
                </div>
                """
        except:
            pass

    html += "</div>"
    return html


def get_chat_history_html():
    """Get formatted chat history - 简洁版，只显示关键信息"""
    try:
        response = api_client.get_conversation_history()
        history = response.get('history', [])

        if not history:
            return "<div style='padding: 15px; text-align: center; color: #9ca3af; font-size: 0.9em;'>💭 暂无对话历史</div>"

        # 统计轮数
        rounds = len(history) // 2

        html = f"<div style='padding: 8px;'>"
        html += f"<div style='color: #6b7280; font-size: 0.85em; margin-bottom: 8px;'>共 {rounds} 轮对话</div>"

        # 显示所有消息
        for i, msg in enumerate(history):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '').strip()

            if role == 'human':
                # 人类消息：智能提取query
                # 可能的格式：
                # 1. "基于以下...问题：实际问题" (智能模式)
                # 2. 直接是问题

                # 尝试提取"问题："后的内容
                if '问题：' in content:
                    parts = content.split('问题：')
                    query = parts[-1].strip()
                    # 如果还有多行，取第一个非空行
                    lines = [line.strip() for line in query.split('\n') if line.strip()]
                    query = lines[0] if lines else query
                elif '\n\n' in content:
                    # 如果有空行分隔，取最后一段
                    parts = content.split('\n\n')
                    query = parts[-1].strip()
                else:
                    # 直接使用整个内容
                    query = content

                # 进一步清理：如果包含"检索到的相关内容"等字样，说明是prompt，需要提取真正的问题
                if '检索到的相关内容' in query or '基于检索到的' in query:
                    # 这种情况下，问题在最前面
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('基于') and not line.startswith('检索') and '问题：' not in line:
                            query = line
                            break

                # 截断显示（限制40个字符，因为是侧边栏）
                if len(query) > 40:
                    display_content = query[:40] + "..."
                else:
                    display_content = query

                icon = "👤"
                color = "#3b82f6"
                bg_color = "#eff6ff"
            else:  # ai
                # AI消息：简单截断
                if len(content) > 50:
                    display_content = content[:50] + "..."
                else:
                    display_content = content

                icon = "🤖"
                color = "#10b981"
                bg_color = "#f0fdf4"

            html += f"""
            <div style='margin: 6px 0; padding: 8px; background: {bg_color}; border-radius: 6px; border-left: 3px solid {color};'>
                <div style='display: flex; align-items: center; gap: 6px;'>
                    <span style='font-size: 1.1em;'>{icon}</span>
                    <span style='font-size: 0.85em; color: #6b7280; font-weight: 500;'>
                        {role.upper()}
                    </span>
                </div>
                <div style='margin-top: 4px; color: #374151; font-size: 0.85em; line-height: 1.4; word-wrap: break-word;'>
                    {display_content}
                </div>
            </div>
            """

        html += "</div>"
        return html

    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        import traceback
        traceback.print_exc()
        return "<div style='padding: 15px; text-align: center; color: #ef4444; font-size: 0.9em;'>❌ 无法获取历史</div>"


def refresh_document_list():
    """Refresh list"""
    return get_document_list_html(), gr.update(choices=load_documents())


def load_documents():
    """Load documents"""
    try:
        docs = api_client.list_documents()
        return ["不使用知识库", "✨ 全部文档"] + docs
    except:
        return ["不使用知识库", "✨ 全部文档"]


def chat_response_wrapper(message, history, selected_doc, model, max_length, temperature, search_mode, smart_top_k, fallback_ratio):
    """Wrapper"""
    if history is None:
        history = []

    new_history = history + [[message, "⏳ 正在处理..."]]
    yield "", new_history

    for updated_history in chat_response(message, history, selected_doc, model, max_length, temperature, search_mode, smart_top_k, fallback_ratio):
        yield "", updated_history


def chat_response(message, history, selected_doc, model, max_length, temperature, search_mode, smart_top_k, fallback_ratio):
    """Main chat logic - 完全参照原始，确保逐字符显示"""
    if not message.strip():
        return history

    if history is None:
        history = []

    start_time = time.time()
    history = history + [[message, "⏳ 正在处理..."]]
    yield history

    try:
        if selected_doc == "✨ 全部文档":
            # All documents
            response_text = ""
            sources = []
            chunk_count = 0
            first_chunk = True

            mode = "smart" if search_mode == "🧠 智能模式" else "fast"

            for chunk in api_client.chat_all_documents(message, mode, smart_top_k, fallback_ratio, True):
                # 逐chunk处理answer字段
                if 'answer' in chunk and chunk['answer']:
                    if first_chunk:
                        processing_time = time.time() - start_time
                        logger.info(f"Processing: {processing_time:.2f}s")
                        first_chunk = False

                    # 累积文本
                    response_text += chunk['answer']
                    chunk_count += 1

                    # 每次都更新界面
                    history[-1][1] = response_text
                    yield history

                if 'sources' in chunk:
                    sources = chunk.get('sources', [])

                if 'error' in chunk:
                    raise Exception(chunk['error'])

            logger.info(f"Chunks: {chunk_count}")

            # 添加引用来源和时间
            if sources:
                sources_html = format_sources_html(sources)
                total_time = time.time() - start_time
                time_info = f'<div style="margin-top: 10px; color: #9ca3af; font-size: 0.85em; text-align: right;">⏱️ {total_time:.2f}秒 | {search_mode}</div>'
                final_response = response_text + "\n\n" + sources_html + time_info
            else:
                total_time = time.time() - start_time
                time_info = f'\n\n<div style="color: #9ca3af; font-size: 0.85em; text-align: right;">⏱️ {total_time:.2f}秒 | {search_mode}</div>'
                final_response = response_text + time_info

            history[-1][1] = final_response
            yield history

        elif selected_doc != "不使用知识库":
            # Single document - 逐字符累积
            response_text = ""
            chunk_count = 0
            first_chunk = True
            char_count = 0  # 统计字符数

            for chunk in api_client.chat(message, selected_doc, model, max_length, temperature, True):
                if first_chunk:
                    processing_time = time.time() - start_time
                    logger.info(f"Processing: {processing_time:.2f}s")
                    first_chunk = False

                # chunk是文本块，逐字符累积
                response_text += chunk
                chunk_count += 1
                char_count += len(chunk)

                # 每接收到新文本就更新界面
                history[-1][1] = response_text
                yield history

            logger.info(f"Chunks: {chunk_count}, Chars: {char_count}")

            # 添加总处理时间
            total_time = time.time() - start_time
            time_info = f'\n\n<div style="color: #9ca3af; font-size: 0.85em; text-align: right;">⏱️ {total_time:.2f}秒</div>'
            history[-1][1] = response_text + time_info
            yield history

        else:
            # General chat - 逐字符累积
            response_text = ""
            chunk_count = 0
            first_chunk = True
            char_count = 0

            for chunk in api_client.chat(message, None, model, max_length, temperature, True):
                if first_chunk:
                    processing_time = time.time() - start_time
                    logger.info(f"Processing: {processing_time:.2f}s")
                    first_chunk = False

                # 逐字符累积
                response_text += chunk
                chunk_count += 1
                char_count += len(chunk)

                # 每次都更新
                history[-1][1] = response_text
                yield history

            logger.info(f"Chunks: {chunk_count}, Chars: {char_count}")

            # 添加总处理时间
            total_time = time.time() - start_time
            time_info = f'\n\n<div style="color: #9ca3af; font-size: 0.85em; text-align: right;">⏱️ {total_time:.2f}秒</div>'
            history[-1][1] = response_text + time_info
            yield history

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        total_time = time.time() - start_time
        error_msg = f"❌ 错误: {str(e)}\n\n<div style='color: #9ca3af; font-size: 0.85em;'>⏱️ {total_time:.2f}秒</div>"
        history[-1][1] = error_msg
        yield history


def clear_conversation():
    """Clear"""
    try:
        api_client.clear_conversation()
    except:
        pass
    return []


def create_interface():
    """Create interface - 参照原始样式，添加历史记录显示"""

    if not api_client.health_check():
        print("❌ 无法连接API服务器")
        print("请先启动: python start_backend.py")

    custom_css = """
    .gradio-container { max-width: 1400px !important; }
    .source-citation { background: #f8f9fa; border-left: 4px solid #2563eb; padding: 15px; margin: 10px 0; border-radius: 8px; }
    .history-box { background: #f0f9ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 10px; margin: 10px 0; }
    """

    with gr.Blocks(theme=gr.themes.Soft(), css=custom_css, title="RAG 文档分析助手") as interface:
        gr.HTML("""
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #2563eb; margin-bottom: 10px;">📚 RAG 文档分析助手</h1>
                <p style="color: #6b7280; font-size: 1.1em;">支持全知识库检索 · 智能引用来源 · 多文档分析 · 对话历史记忆</p>
            </div>
        """)

        with gr.Tabs():
            with gr.Tab("💬 对话"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(label="对话", height=500, show_label=True, avatar_images=None)
                        with gr.Row():
                            msg = gr.Textbox(label="", placeholder="输入你的问题... (支持跨文档综合查询和上下文记忆)", lines=2, scale=4, show_label=False)
                            submit_btn = gr.Button("发送", variant="primary", scale=1)
                        with gr.Row():
                            clear_btn = gr.Button("清除对话", size="sm")

                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ 设置")

                        try:
                            available_models = api_client.list_models()
                            current_model = api_client.get_current_model()
                        except:
                            available_models = ["qwen-max-latest"]
                            current_model = "qwen-max-latest"

                        model_dropdown = gr.Dropdown(choices=available_models, value=current_model, label="选择模型")
                        doc_dropdown = gr.Dropdown(choices=load_documents(), value="不使用知识库", label="选择文档")

                        gr.Markdown("**💡 提示**：\n- 支持上下文对话记忆（最近3轮）\n- 选择\"✨ 全部文档\"检索所有知识库\n- 自动显示引用来源")

                        # 对话历史显示区域 - 可折叠
                        with gr.Accordion("💭 对话历史", open=False):
                            history_display = gr.HTML(
                                value=get_chat_history_html(),
                                label=""
                            )
                            gr.Markdown("*点击刷新按钮查看最新历史*", elem_classes="text-sm")

                        gr.Markdown("### 🎯 全文档检索模式")
                        search_mode = gr.Radio(choices=["⚡ 快速模式", "🧠 智能模式"], value="⚡ 快速模式", label="检索策略")

                        with gr.Accordion("模式说明", open=False):
                            gr.Markdown("**⚡ 快速模式**（推荐）\n- 纯向量检索\n- 响应速度：1-3秒\n\n**🧠 智能模式**（精准）\n- 向量+LLM评估\n- 响应速度：8-15秒\n- 自动过滤不相关")

                        with gr.Accordion("智能模式参数", open=False):
                            smart_top_k = gr.Slider(5, 20, 10, step=1, label="Top-K")
                            fallback_ratio = gr.Slider(0.2, 0.8, 0.5, step=0.1, label="保底比例")

                        max_length_slider = gr.Slider(500, 8000, 3000, step=100, label="最大回答长度")
                        temperature_slider = gr.Slider(0.0, 1.0, 0.7, step=0.1, label="温度")

            with gr.Tab("📁 文档管理"):
                gr.Markdown("## 文档管理中心")
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("### 📚 当前文档")
                        doc_list_display = gr.HTML(value=get_document_list_html())
                        refresh_btn = gr.Button("🔄 刷新列表", size="sm")

                    with gr.Column(scale=1):
                        with gr.Group():
                            gr.Markdown("### 📤 上传文档")
                            upload_file = gr.File(file_types=[".txt", ".pdf", ".docx", ".md", ".csv"])
                            upload_btn_mgmt = gr.Button("上传", variant="primary")
                            upload_status_mgmt = gr.Textbox(interactive=False, show_label=False, placeholder="等待操作...")

                        gr.Markdown("---")

                        with gr.Group():
                            gr.Markdown("### 🔄 更新文档")
                            try:
                                doc_list = api_client.list_documents()
                            except:
                                doc_list = []
                            update_doc_select = gr.Dropdown(choices=["请选择要更新的文档"] + doc_list, value="请选择要更新的文档", label="选择文档")
                            update_file = gr.File(file_types=[".txt", ".pdf", ".docx", ".md", ".csv"])
                            force_update_check = gr.Checkbox(label="强制更新", value=False)
                            update_btn = gr.Button("更新", variant="secondary")
                            update_status = gr.Textbox(interactive=False, show_label=False, placeholder="等待操作...")

                        gr.Markdown("---")

                        with gr.Group():
                            gr.Markdown("### 🗑️ 删除文档")
                            delete_doc_select = gr.Dropdown(choices=["请选择要删除的文档"] + doc_list, value="请选择要删除的文档", label="选择文档")
                            delete_btn = gr.Button("删除", variant="stop")
                            delete_status = gr.Textbox(interactive=False, show_label=False, placeholder="等待操作...")

                gr.Markdown("---\n### 💡 使用提示\n支持格式：TXT, PDF, DOCX, MD, CSV")

        # Event handlers
        msg.submit(chat_response_wrapper, [msg, chatbot, doc_dropdown, model_dropdown, max_length_slider, temperature_slider, search_mode, smart_top_k, fallback_ratio], [msg, chatbot]).then(
            # 更新历史显示
            lambda: get_chat_history_html(),
            None,
            history_display
        )

        submit_btn.click(chat_response_wrapper, [msg, chatbot, doc_dropdown, model_dropdown, max_length_slider, temperature_slider, search_mode, smart_top_k, fallback_ratio], [msg, chatbot]).then(
            # 更新历史显示
            lambda: get_chat_history_html(),
            None,
            history_display
        )

        clear_btn.click(clear_conversation, None, chatbot, queue=False).then(
            # 清除后刷新历史显示
            lambda: get_chat_history_html(),
            None,
            history_display
        )

        upload_btn_mgmt.click(upload_document, upload_file, [upload_status_mgmt, doc_dropdown, doc_list_display]).then(
            lambda: (gr.update(choices=["请选择要更新的文档"] + api_client.list_documents()), gr.update(choices=["请选择要删除的文档"] + api_client.list_documents())),
            None, [update_doc_select, delete_doc_select]
        )

        update_btn.click(update_document, [update_file, update_doc_select, force_update_check], [update_status, doc_list_display])
        delete_btn.click(delete_document, delete_doc_select, [delete_status, doc_dropdown, doc_list_display]).then(
            lambda: (gr.update(choices=["请选择要更新的文档"] + api_client.list_documents()), gr.update(choices=["请选择要删除的文档"] + api_client.list_documents())),
            None, [update_doc_select, delete_doc_select]
        )

        refresh_btn.click(refresh_document_list, None, [doc_list_display, doc_dropdown], queue=False).then(
            lambda: (gr.update(choices=["请选择要更新的文档"] + api_client.list_documents()), gr.update(choices=["请选择要删除的文档"] + api_client.list_documents())),
            None, [update_doc_select, delete_doc_select]
        )

        gr.HTML("""
            <div style="text-align: center; margin-top: 30px; padding: 20px; color: #6b7280;">
                <p>💡 <strong>使用提示</strong>：系统会自动记住最近3轮对话，支持上下文理解</p>
            </div>
        """)

    return interface


def main():
    """Launch"""
    logger.info("Starting Web UI...")

    if not api_client.health_check():
        print("❌ 无法连接API")
        print("请先启动: python start_backend.py")
        return

    print("✅ API连接成功")
    interface = create_interface()
    interface.queue()
    interface.launch(server_name="127.0.0.1", server_port=7862, share=False, inbrowser=True, show_error=True)


if __name__ == "__main__":
    main()