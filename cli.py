"""
Command Line Interface for Document Assistant
Interactive terminal interface - Improved version based on original ragcli.py
"""
import os
import sys
from pathlib import Path
from loguru import logger

from rag_system import DocumentAssistant, MultiDocumentAssistant

# Color support
try:
    from colorama import init, Fore, Style

    init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False


def print_colored(text: str, color: str = "", end: str = "\n"):
    """Print with color support"""
    if HAS_COLOR and color:
        print(color + text + Style.RESET_ALL, end=end)
    else:
        print(text, end=end)


def print_header():
    """Print application header"""
    print("\n" + "=" * 70)
    print_colored("    RAG Document Analysis Assistant - Enhanced Edition",
                  Fore.CYAN if HAS_COLOR else "")
    print("=" * 70 + "\n")


def print_help():
    """Print help menu"""
    print("\n" + "-" * 70)
    print_colored("Command List:", Fore.YELLOW if HAS_COLOR else "")
    print("  /help      - Show this help menu")
    print("  /clear     - Clear conversation history")
    print("  /kb        - Manage knowledge base (support multiple)")
    print("  /all       - Use ALL documents in knowledge base")
    print("  /upload    - Upload document to knowledge base")
    print("  /update    - Update existing document (smart detection)")
    print("  /info      - Show document information")
    print("  /model     - Switch model")
    print("  /params    - Adjust parameters")
    print("  /quit      - Exit program")
    print("-" * 70 + "\n")


def manage_knowledge_base(assistant: MultiDocumentAssistant):
    """Knowledge base management - returns selected document(s)"""
    print_colored("\n📚 Knowledge Base Management", Fore.CYAN if HAS_COLOR else "")
    print("-" * 70)

    documents = assistant.list_documents()

    if not documents:
        print("No knowledge base available")
        return None

    print("\nAvailable knowledge bases:")
    for i, doc in enumerate(documents, 1):
        print(f"  {i}. {doc}")

    print("\nOptions:")
    print("  1. Select single knowledge base")
    print("  2. Select multiple knowledge bases (smart merge retrieval)")
    print("  3. Clear knowledge base selection")
    print("  4. Return")

    choice = input("\nPlease select [1-4]: ").strip()

    if choice == "1" and documents:
        try:
            idx = int(input(f"Select knowledge base number [1-{len(documents)}]: "))
            if 1 <= idx <= len(documents):
                selected = documents[idx - 1]
                print_colored(f"\n✅ Selected knowledge base: {selected}",
                              Fore.GREEN if HAS_COLOR else "")
                return [selected]
        except:
            print_colored("❌ Invalid selection", Fore.RED if HAS_COLOR else "")

    elif choice == "2" and documents:
        print(f"\nEnter knowledge base numbers separated by commas")
        print(f"Example: 1,2,3 or 1-3")

        try:
            input_str = input("Numbers: ").strip()
            indices = []

            for part in input_str.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    indices.extend(range(start, end + 1))
                else:
                    indices.append(int(part))

            selected_kbs = []
            for idx in indices:
                if 1 <= idx <= len(documents):
                    selected_kbs.append(documents[idx - 1])

            if selected_kbs:
                print_colored(f"\n✅ Selected {len(selected_kbs)} knowledge bases:",
                              Fore.GREEN if HAS_COLOR else "")
                for kb in selected_kbs:
                    print(f"   - {kb}")
                return selected_kbs
        except Exception as e:
            print_colored(f"❌ Invalid input: {e}", Fore.RED if HAS_COLOR else "")

    elif choice == "3":
        print_colored("\n✅ Knowledge base selection cleared",
                      Fore.GREEN if HAS_COLOR else "")
        return None

    return None


def upload_document(assistant: DocumentAssistant):
    """Upload document"""
    print_colored("\n📤 Upload Document", Fore.CYAN if HAS_COLOR else "")
    print("-" * 70)

    file_path = input("Enter file path (support txt/pdf/docx/md/csv): ").strip()
    file_path = file_path.strip('"').strip("'")

    if not Path(file_path).exists():
        print_colored(f"❌ File not found: {file_path}", Fore.RED if HAS_COLOR else "")
        return

    print("\nUploading...")
    try:
        if assistant.upload_document(file_path):
            print_colored(f"✅ Uploaded: {os.path.basename(file_path)}",
                          Fore.GREEN if HAS_COLOR else "")
        else:
            print_colored("❌ Upload failed", Fore.RED if HAS_COLOR else "")
    except Exception as e:
        print_colored(f"❌ Upload failed: {e}", Fore.RED if HAS_COLOR else "")


def update_document(assistant: DocumentAssistant):
    """Update existing document"""
    print_colored("\n🔄 Update Document", Fore.CYAN if HAS_COLOR else "")
    print("-" * 70)

    documents = assistant.list_documents()

    if not documents:
        print_colored("❌ No documents in knowledge base", Fore.RED if HAS_COLOR else "")
        return

    print("\nAvailable documents:")
    for i, doc in enumerate(documents, 1):
        print(f"  {i}. {doc}")

    try:
        idx = int(input(f"\nSelect document to update [1-{len(documents)}]: "))
        if not (1 <= idx <= len(documents)):
            print_colored("❌ Invalid selection", Fore.RED if HAS_COLOR else "")
            return

        doc_name = documents[idx - 1]

        # Show current document info
        info = assistant.get_document_info(doc_name)
        if info:
            print(f"\nCurrent document info:")
            print(f"  Size: {info['size_mb']} MB")
            print(f"  Modified: {info['modified_time']}")
            print(f"  Chunks: {info['chunk_count']}")
            print(f"  Hash: {info['file_hash'][:16]}...")

        file_path = input(f"\nEnter path to updated file: ").strip()
        file_path = file_path.strip('"').strip("'")

        if not Path(file_path).exists():
            print_colored(f"❌ File not found: {file_path}", Fore.RED if HAS_COLOR else "")
            return

        # Check if filename matches
        if Path(file_path).name != doc_name:
            print_colored(f"⚠️  Warning: Filename mismatch!", Fore.YELLOW if HAS_COLOR else "")
            print(f"   Knowledge base: {doc_name}")
            print(f"   New file: {Path(file_path).name}")
            confirm = input("   Continue anyway? (y/n): ").lower()
            if confirm != 'y':
                print_colored("❌ Update cancelled", Fore.YELLOW if HAS_COLOR else "")
                return

        force = input("\nForce update even if unchanged? (y/n, default: n): ").lower() == 'y'

        print("\n🔄 Updating...")
        try:
            if assistant.update_document(file_path, force=force):
                print_colored(f"✅ Updated: {doc_name}",
                              Fore.GREEN if HAS_COLOR else "")

                # Show new info
                new_info = assistant.get_document_info(doc_name)
                if new_info:
                    print(f"\nNew document info:")
                    print(f"  Size: {new_info['size_mb']} MB")
                    print(f"  Chunks: {new_info['chunk_count']}")
                    print(f"  Hash: {new_info['file_hash'][:16]}...")
            else:
                print_colored("❌ Update failed", Fore.RED if HAS_COLOR else "")
        except Exception as e:
            print_colored(f"❌ Update failed: {e}", Fore.RED if HAS_COLOR else "")

    except ValueError:
        print_colored("❌ Invalid input", Fore.RED if HAS_COLOR else "")
    except Exception as e:
        print_colored(f"❌ Error: {e}", Fore.RED if HAS_COLOR else "")


def show_document_info(assistant: DocumentAssistant):
    """Show detailed document information"""
    print_colored("\n📊 Document Information", Fore.CYAN if HAS_COLOR else "")
    print("-" * 70)

    documents = assistant.list_documents()

    if not documents:
        print_colored("❌ No documents in knowledge base", Fore.RED if HAS_COLOR else "")
        return

    print("\nAvailable documents:")
    for i, doc in enumerate(documents, 1):
        print(f"  {i}. {doc}")

    print(f"  {len(documents) + 1}. Show all documents info")

    try:
        idx = int(input(f"\nSelect [1-{len(documents) + 1}]: "))

        if idx == len(documents) + 1:
            # Show all
            print("\n" + "=" * 70)
            for doc in documents:
                info = assistant.get_document_info(doc)
                if info:
                    print(f"\n📄 {info['name']}")
                    print(f"   Size: {info['size_mb']} MB ({info['size_bytes']:,} bytes)")
                    print(f"   Modified: {info['modified_time']}")
                    print(f"   Chunks: {info['chunk_count']}")
                    print(f"   Hash: {info['file_hash']}")
                    print(f"   Indexed: {'✅ Yes' if info['indexed'] else '❌ No'}")
                    print("-" * 70)

        elif 1 <= idx <= len(documents):
            doc_name = documents[idx - 1]
            info = assistant.get_document_info(doc_name)

            if info:
                print("\n" + "=" * 70)
                print_colored(f"Document: {info['name']}", Fore.CYAN if HAS_COLOR else "")
                print("=" * 70)
                print(f"Path:          {info['path']}")
                print(f"Size:          {info['size_mb']} MB ({info['size_bytes']:,} bytes)")
                print(f"Last Modified: {info['modified_time']}")
                print(f"File Hash:     {info['file_hash']}")
                print(f"Chunk Count:   {info['chunk_count']}")
                print(f"Indexed:       {'✅ Yes' if info['indexed'] else '❌ No'}")
                print("=" * 70)
            else:
                print_colored(f"❌ Could not get info for: {doc_name}",
                            Fore.RED if HAS_COLOR else "")
        else:
            print_colored("❌ Invalid selection", Fore.RED if HAS_COLOR else "")

    except ValueError:
        print_colored("❌ Invalid input", Fore.RED if HAS_COLOR else "")
    except Exception as e:
        print_colored(f"❌ Error: {e}", Fore.RED if HAS_COLOR else "")


def select_model(assistant: DocumentAssistant):
    """Select model"""
    models = assistant.get_available_models()
    current = assistant.get_current_model()

    print_colored("\n🎯 Select Model", Fore.CYAN if HAS_COLOR else "")
    print("-" * 70)
    print("  1. Qwen Max (Most powerful)")
    print("  2. Qwen Plus (Balanced)")
    print("  3. Qwen Turbo (Fastest)")

    print(f"\nCurrent: {current}")
    choice = input("\nPlease select [1-3]: ").strip()

    model_map = {"1": models[0], "2": models[1], "3": models[2]}

    if choice in model_map:
        if assistant.switch_model(model_map[choice]):
            print_colored(f"✅ Switched to: {model_map[choice]}",
                          Fore.GREEN if HAS_COLOR else "")
            return model_map[choice]

    return None


def adjust_params(assistant: DocumentAssistant):
    """Adjust parameters"""
    print_colored("\n⚙️  Adjust Parameters", Fore.CYAN if HAS_COLOR else "")
    print("-" * 70)

    try:
        max_len = int(input("Max length [100-8000, current 4000]: ") or "4000")
        temp = float(input("Temperature [0.0-1.9, current 0.7]: ") or "0.7")

        max_len = max(100, min(8000, max_len))
        temp = max(0.0, min(1.9, temp))

        assistant.update_parameters(temperature=temp, max_tokens=max_len)
        print_colored(f"✅ Parameters set: max_length={max_len}, temperature={temp}",
                      Fore.GREEN if HAS_COLOR else "")
        return max_len, temp
    except:
        print_colored("❌ Invalid parameters, keeping current settings",
                      Fore.RED if HAS_COLOR else "")
        return None, None


def main():
    """Main CLI function - Enhanced version based on original ragcli.py"""
    # Check API key
    if not os.getenv("DASHSCOPE_API_KEY"):
        print_colored("❌ DASHSCOPE_API_KEY not set", Fore.RED if HAS_COLOR else "")
        input("Press Enter to exit...")
        sys.exit(1)

    print_header()
    print("✅ Initializing...")

    # Setup logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="INFO"
    )

    # Initialize multi-document assistant
    assistant = MultiDocumentAssistant()
    print_colored("✅ Initialization complete!\n", Fore.GREEN if HAS_COLOR else "")

    # Default configuration
    current_model = assistant.get_current_model()
    current_kb = None  # Can be a list of documents or None
    max_length = 4000
    temperature = 0.7

    print_help()
    print_colored("💡 Tip: Enter question directly to start, type /help for commands\n",
                  Fore.YELLOW if HAS_COLOR else "")

    while True:
        try:
            # Display status
            status_parts = [f"Model: {current_model.split('-')[0]}"]
            if current_kb:
                if current_kb == "ALL":
                    docs_count = len(assistant.list_documents())
                    status_parts.append(f"KB: 全部文档 ({docs_count}个)")
                elif isinstance(current_kb, list):
                    status_parts.append(f"KB: {len(current_kb)} doc(s)")
                else:
                    status_parts.append(f"KB: {current_kb[:20]}...")

            status_line = " | ".join(status_parts)
            user_input = input(f"\n[{status_line}]\nYou: ").strip()

            if not user_input:
                continue

            # Command handling
            if user_input.startswith('/'):
                cmd = user_input.lower()

                if cmd in ['/quit', '/exit', '/q']:
                    print_colored("\n👋 Goodbye!", Fore.CYAN if HAS_COLOR else "")
                    break

                elif cmd in ['/help', '/h', '/?']:
                    print_help()

                elif cmd in ['/clear', '/c']:
                    assistant.clear_conversation()
                    print_colored("✅ Conversation history cleared",
                                  Fore.GREEN if HAS_COLOR else "")

                elif cmd in ['/kb', '/knowledge']:
                    kb = manage_knowledge_base(assistant)
                    if kb is not None:
                        current_kb = kb
                    elif kb is None and cmd == '/kb':
                        current_kb = None

                elif cmd in ['/upload', '/up']:
                    upload_document(assistant)

                elif cmd in ['/update', '/upd']:
                    update_document(assistant)

                elif cmd in ['/info', '/i']:
                    show_document_info(assistant)

                elif cmd in ['/model', '/m']:
                    model = select_model(assistant)
                    if model:
                        current_model = model

                elif cmd in ['/params', '/p']:
                    ml, t = adjust_params(assistant)
                    if ml is not None:
                        max_length = ml
                        temperature = t

                elif cmd in ['/all', '/a']:
                    print_colored("\n✅ 已切换到全知识库模式",
                                  Fore.GREEN if HAS_COLOR else "")
                    print_colored("提示：将检索所有已上传的文档",
                                  Fore.YELLOW if HAS_COLOR else "")
                    current_kb = "ALL"  # 特殊标记

                else:
                    print_colored(f"❌ Unknown command: {user_input}",
                                  Fore.RED if HAS_COLOR else "")
                    print("  Type /help to see available commands")

                continue

            # Normal conversation
            print_colored("\nAI: ", Fore.GREEN if HAS_COLOR else "", end="")
            sys.stdout.flush()

            try:
                # 全知识库模式
                if current_kb == "ALL":
                    print_colored("🔍 正在检索全部文档...",
                                  Fore.CYAN if HAS_COLOR else "")

                    # 流式输出
                    sources = []
                    for chunk in assistant.ask_all_documents_stream(user_input):
                        if 'answer' in chunk:
                            print(chunk['answer'], end="", flush=True)
                        if 'sources' in chunk:
                            sources = chunk.get('sources', [])
                    print()  # 换行

                    # 显示引用来源
                    if sources:
                        print_colored("\n📚 引用来源:", Fore.CYAN if HAS_COLOR else "")
                        for src in sources[:5]:  # 最多显示前5个
                            doc_name = src['document']

                            # 智能显示位置信息
                            location_info = ""
                            if 'page' in src and src['page'] != '?':
                                location_info = f"第{src['page']}页"
                            elif 'source' in src.get('metadata', {}):
                                # 显示文档内位置
                                location_info = f"片段{src['index']}"
                            else:
                                # TXT等文件显示片段编号
                                location_info = f"片段{src['index']}"

                            content_preview = src['content'][:100] + "..." if len(src['content']) > 100 else src[
                                'content']
                            print(f"  [{src['index']}] {doc_name} ({location_info})")
                            print(f"      {content_preview}")
                        if len(sources) > 5:
                            print(f"  ... 还有 {len(sources) - 5} 个引用")

                # Multi-document mode
                elif isinstance(current_kb, list) and len(current_kb) > 1:
                    print_colored("🔍 正在检索多个知识库...",
                                  Fore.CYAN if HAS_COLOR else "")

                    answer = assistant.ask_multi_documents(user_input, current_kb)
                    print(f"\n{answer}")

                # Single document or no document mode
                else:
                    kb_to_use = current_kb[0] if isinstance(current_kb, list) else current_kb

                    # Stream response
                    for chunk in assistant.ask_stream(user_input, kb_to_use):
                        print(chunk, end="", flush=True)
                    print()  # New line after response

            except KeyboardInterrupt:
                print_colored("\n\n⚠️  Response interrupted",
                              Fore.YELLOW if HAS_COLOR else "")
            except Exception as e:
                print_colored(f"\n❌ Error: {e}", Fore.RED if HAS_COLOR else "")
                logger.exception("Error in conversation")

        except KeyboardInterrupt:
            print_colored("\n\n👋 Goodbye!", Fore.CYAN if HAS_COLOR else "")
            break
        except Exception as e:
            print_colored(f"\n❌ Program error: {e}", Fore.RED if HAS_COLOR else "")
            logger.exception("Error in main loop")


if __name__ == "__main__":
    main()