# Wanren AI Memex Embodied Intelligence Platform Memory System

> **Universal Embodied Robot Brain Memory System Supporting One Brain Meta Body - Dynamic Knowledge Memory Subsystem**

Memex's memory subsystem (xRAG) is a dynamic knowledge enhancement system optimized for robot business process implementation. It supports long-term and short-term professional knowledge memory and intelligent filtering for robots, mimicking human memory systems. It enables intelligent retrieval and fusion of multi-domain knowledge, dynamic expansion, updating, forgetting, and flexible management of robot memory.

---

## ✨ Core Features

### 🎯 Innovation Highlights

#### 1. **Intelligent Two-Stage Retrieval (LLM Enhanced)**
Traditional robot memory systems only support fixed knowledge memory or rely on embedding retrieval based on vector similarity, which can easily confuse semantically similar professional knowledge, with certain probability of inducing hallucinations or outputting content irrelevant to actual communication.
To make robot responses more reliable and authentic, this memory system innovatively introduces a **two-stage memory retrieval architecture**:

```
User Query → Vector Retrieval Top-K → LLM Individual Relevance Evaluation → Selected Chunks → Generate High-Quality Answer
```

- **Stage 1**: Hybrid retrieval (vector + BM25) rapidly filters Top-K candidate chunks from all documents
- **Stage 2**: Uses LLM for relevance judgment on each candidate chunk, filtering irrelevant content
- **Effectiveness Improvement**: Significantly improves answer accuracy, reduces hallucinations and irrelevant information

**Example Scenario**:
```
Query: "Xixi, what was Buffett's investment strategy in 2023?"
Traditional Memory: May recall content containing "2023" and "strategy" but discussing other topics
Memex: After LLM evaluation, only retains chunks truly discussing Buffett's 2023 investment strategy
```

#### 2. **Flexible Document Management System**
Solves pain points of traditional robot memory systems, particularly suitable for scenarios requiring frequent updates to business documents and regulations (such as bank regulations, legal provisions):

**Problems with Traditional Memory**:
- ❌ Modifying a knowledge document → Requires rebuilding/reindexing the entire vector database
- ❌ Difficult document version management
- ❌ Cannot dynamically update incrementally
- ❌ Serious waste of computational resources

**Memex Memory System Solutions**:
- ✅ **Independent Memory Indexes**: Each document stores vector index separately, hierarchical memory management, reduced coupling, no mutual interference
- ✅ **Dynamic Knowledge Update Detection**: Automatic detection of document changes based on MD5 hash
- ✅ **Hot Updates, Short Memory**: Modifying memory only rebuilds that document's index, completed in seconds
- ✅ **Forgetting Mechanism, Delayed Deletion Mechanism**: Optimized file locks, gradual forgetting, efficient use of computational and storage resources

```python
# Update single memory file - only rebuild that file's index
assistant.update_document("report_2024.pdf")

# System automatically:
# 1. Detects if memory file has physical changes (preferably MD5 comparison)
# 2. Only rebuilds vector index for changed file
# 3. Other memory file indexes completely unaffected
```

#### 3. **Full Memory Intelligent Retrieval**
- Single query, large-scale search across all robot memory systems
- Automatically aggregates relevant information from different memory units
- Intelligently annotates knowledge and memory original sources (memory filename + block)
- Supports fast mode (vector retrieval) and intelligent mode (LLM filtering)

#### 4. **Conversation History Memory**
- Short memory range: Retains last 3 rounds of conversation context
- Short memory update: Supports follow-up questions and clarifications
- Short memory forgetting: Automatically manages history length, prevents overflow, improves efficiency

#### 5. **Hybrid Retrieval Strategy**
- **Dense Retrieval**: Vector similarity (semantic understanding)
- **Sparse Retrieval**: BM25 keyword matching (exact matching)
- **Rerank**: Optional reranking module for further result optimization

---

## 🏗️ System Architecture

### Overall Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Gradio)                     │
│                    Web UI (Port: 7862)                       │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                     API Server (Port: 8000)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
┌─────────────┐  ┌──────────────┐  ┌─────────────┐
│   LLM API   │  │  Embedding   │  │   Rerank    │
│ (Alibaba    │  │    Model     │  │    Model    │
│  Bailian)   │  │              │  │             │
└─────────────┘  └──────────────┘  └─────────────┘
         │               │               │
         └───────────────┴───────────────┘
                         ↓
         ┌──────────────────────────────────────┐
         │         RAG System Core              │
         │  ┌────────────────────────────────┐  │
         │  │   Knowledge Base Manager       │  │
         │  │  - Document Upload/Delete      │  │
         │  │  - Independent Indexing        │  │
         │  │  - Smart Update Detection      │  │
         │  └────────────────────────────────┘  │
         │  ┌────────────────────────────────┐  │
         │  │   Conversation Manager         │  │
         │  │  - Chat History (3 turns)      │  │
         │  │  - Context Management          │  │
         │  │  - Smart Retrieval (2-stage)   │  │
         │  └────────────────────────────────┘  │
         │  ┌────────────────────────────────┐  │
         │  │   Relevance Evaluator          │  │
         │  │  - LLM-based Filtering         │  │
         │  │  - Batch Evaluation            │  │
         │  │  - Result Caching              │  │
         │  └────────────────────────────────┘  │
         └──────────────────────────────────────┘
                         ↓
         ┌──────────────────────────────────────┐
         │       Vector Store (Chroma)          │
         │  ┌──────────┐ ┌──────────┐          │
         │  │ Doc A    │ │ Doc B    │  ...     │
         │  │ Index    │ │ Index    │          │
         │  └──────────┘ └──────────┘          │
         └──────────────────────────────────────┘
```

### Core Module Description

#### 1. **Knowledge Base Management (knowledge_base.py)**
```python
KnowledgeBaseManager
├── upload_document()      # Upload and index document
├── update_document()      # Intelligent incremental update
├── delete_document()      # Safe deletion (delayed cleanup)
├── list_documents()       # Document list
└── get_retriever()        # Get retriever
```

**Core Innovation**:
- Independent collection_id for each document (based on filename MD5)
- Document-level cache management (document_cache, retriever_cache)
- Intelligent hash comparison, avoiding meaningless rebuilds

#### 2. **Conversation Management (conversation.py)**
```python
ConversationManager
├── chat()                              # Synchronous conversation
├── chat_stream()                       # Streaming conversation
├── smart_all_documents_retrieve()      # Intelligent full-document retrieval
└── _manage_history()                   # History management
```

**Intelligent Retrieval Process**:
```python
async def smart_all_documents_retrieve(question, all_docs, top_k=10):
    # 1. Collect candidate chunks from all documents
    all_chunks = []
    for doc in all_docs:
        chunks = retriever.get_relevant_documents(question)
        all_chunks.extend(chunks)
    
    # 2. Sort by score, take Top-K
    top_chunks = sorted(all_chunks, by_score)[:top_k]
    
    # 3. LLM batch evaluates relevance
    relevant_chunks = []
    for chunk in top_chunks:
        is_relevant = llm.evaluate(question, chunk)
        if is_relevant:
            relevant_chunks.append(chunk)
    
    # 4. Generate answer using selected chunks
    return generate_answer(question, relevant_chunks)
```

#### 3. **Relevance Evaluator (relevance_evaluator.py)**
```python
RelevanceEvaluator
├── batch_evaluate_relevance()    # Batch evaluation
├── _evaluate_single()            # Single evaluation
└── _build_evaluation_prompt()    # Build evaluation prompt
```

**Evaluation Prompt Example**:
```
Please determine whether the following text fragment is relevant to the question.

**Question**: How does Buffett view cryptocurrency?

**Text Fragment**:
I have always believed that Bitcoin is a speculative tool, not a real investment...

**Judgment Criteria**:
- If the text directly answers or partially answers the question, answer "Y"
- If the text provides relevant background or contextual information, answer "Y"  
- If the text is completely irrelevant to the question, answer "N"

**Please only answer Y (relevant) or N (irrelevant)**:
```

#### 4. **Vector Storage (vector_store.py)**
```python
VectorStoreManager
├── create_collection()      # Create vector collection
├── get_collection()         # Get existing collection
├── delete_collection()      # Delete collection
└── list_collections()       # List all collections

RetrieverFactory
├── create_hybrid_retriever()  # Hybrid retriever (vector+BM25)
└── add_reranking()           # Add reranking
```

---

## 🚀 Quick Start

### Environment Requirements

- Python 3.8+
- Alibaba Cloud Bailian API Key (supports Tongyi Qianwen series models)
- 4GB+ RAM (8GB recommended)

### 1. Install Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

### 2. Configure API Key

```bash
export DASHSCOPE_API_KEY='your_api_key_here'
```

Or configure in code:
```python
# config.py
DASHSCOPE_API_KEY = "your_api_key_here"
```

### 3. Quick Launch

```bash
Method 1: Use quick start script
# macOS/Linux users:
chmod +x quick_start.sh
./quick_start.sh
# Windows users:
1. Double-click quick_start.bat
2. Wait for service to start
3. Browser opens automatically

Method 2: Manual start
# Terminal 1: Start backend
python start_backend.py

# Terminal 2: Start frontend
python start_fronted.py
```

### 4. Access Interface

- **Web Interface**: http://localhost:7862
- **API Documentation**: http://localhost:8000/docs

---

## 📖 User Guide

### Basic Usage

#### 1. Upload Document
- Supported formats: TXT, CSV, DOC, DOCX, PDF, MD
- Automatic segmentation, vectorization, indexing
- Real-time progress display

#### 2. Select Retrieval Mode

**⚡ Fast Mode** (recommended for daily use)
- Pure vector retrieval
- Response speed: 1-3 seconds
- Suitable for: General Q&A

**🧠 Intelligent Mode** (recommended for important queries)
- Vector retrieval + LLM evaluation
- Response speed: 8-15 seconds
- Suitable for: Q&A requiring high accuracy
- Automatically filters irrelevant content

#### 3. Start Conversation

**Single Document Query**:
```
Select document: financial_report_2024.pdf
Question: What is the net profit for Q2 2024?
```

**Full Document Query**:
```
Select document: ✨ All Documents
Question: What changes are there in investment strategies comparing 2023 and 2024?
```

**Follow-up Conversation**:
```
Round 1: What is Buffett's view on tech stocks?
Round 2: Which tech companies has he specifically invested in?  # System remembers context
Round 3: What is the return rate of these investments?      # Continue follow-up
```

### Advanced Features

#### Document Management

**Update Document**:
```python
# Method 1: Directly upload file with same name via Web interface
# Method 2: API call
PUT /documents/{document_name}
```

**Delete Document**:
- Supports safe deletion, automatically cleans vector index
- Delayed deletion mechanism for Windows environment, avoiding file lock issues

#### Parameter Tuning

**Intelligent Mode Parameters**:
- `top_k`: Initial recall quantity (5-20, default 10)
- `fallback_ratio`: Fallback ratio (0.2-0.8, default 0.5)

```
top_k=10 → Recall 10 most relevant chunks from all documents
         → After LLM evaluation may retain 3-8 truly relevant ones
         → If LLM judges all irrelevant, fallback returns 5 (10*0.5)
```

**Model Parameters**:
- `temperature`: Creativity (0.0-1.0, default 0.7)
- `max_tokens`: Maximum answer length (500-8000, default 3000)

---

## 🔧 Project Structure

```
rag-document-assistant/
├── __init__.py              # Package initialization
├── config.py                # Configuration management
├── llm_client.py            # LLM client (conversation, Embedding, Rerank)
├── document_loader.py       # Document loader (multi-format support)
├── vector_store.py          # Vector storage management
├── knowledge_base.py        # Knowledge base manager ⭐
├── conversation.py          # Conversation manager ⭐
├── relevance_evaluator.py  # LLM relevance evaluator ⭐
├── rag_system.py            # RAG system core interface
├── api_server.py            # FastAPI backend service
├── api_client.py            # API client wrapper
├── web_ui_api.py            # Gradio Web interface
├── cli.py                   # Command line tool
├── logging_config.py        # Logging configuration
├── utils.py                 # Utility functions
├── start_backend.py         # Backend startup script
├── start_fronted.py         # Frontend startup script
├── quick_start.sh           # Quick start script 🆕
├── requirements.txt         # Python dependencies
└── README.md               # This document
```

---

## 🆚 Comparison with Traditional RAG

| Feature | Traditional RAG | This System |
|------|---------|--------|
| **Retrieval Method** | Single vector retrieval | Vector+BM25 hybrid retrieval |
| **Result Filtering** | Only relies on similarity | **LLM intelligent evaluation** ⭐ |
| **Document Update** | Requires rebuilding entire database | **Independent indexing, second-level updates** ⭐ |
| **Cross-document Query** | Manual specification required | Automatic full-document retrieval |
| **Conversation Memory** | None or limited | 3-round context memory |
| **Source Annotation** | Basic information | Detailed annotation with document name + page number |
| **Deployment Complexity** | High | One-click startup script |

---



### System Capacity

- **Document Quantity**: No theoretical limit (tested stable with 100+ documents)
- **Single Document Size**: Recommended <1MB (oversized documents automatically chunked)
- **Overall Database Full Document Size**: Recommended <60MB
- **Concurrent Connections**: Supports 10+ concurrent users
- **Vector Dimension**: 1536 (text-embedding-v3)

---

## 🔐 Security Features

1. **API Key Management**: Environment variable isolation, no hardcoding
2. **Data Isolation**: Each document stored independently, no interference
3. **Resource Cleanup**: Automatic management of temporary files and memory
4. **Error Handling**: Comprehensive exception catching and logging

---

## 🛠️ Technology Stack

### Core Frameworks
- **LangChain**: RAG framework
- **FastAPI**: Backend API service
- **Gradio**: Web frontend interface

### LLM Services
- **Alibaba Cloud Bailian Platform**
  - Conversation models: Tongyi Qianwen series (Qwen-Max/Plus/Turbo)
  - Embedding: text-embedding-v3
  - Rerank: gte-rerank-v2

### Vector Database
- **Chroma**: Lightweight vector database
- **BM25Retriever**: Keyword retrieval

### Others
- **Loguru**: Logging management
- **Pydantic**: Data validation
- **HTTPX**: HTTP client

---


**Major Updates**:

1. **🎯 Intelligent Two-Stage Retrieval**
   - New LLM relevance evaluation module
   - Batch evaluation optimization, improved efficiency
   - Caching mechanism reduces duplicate evaluations

2. **🔧 Flexible Document Management**
   - Independent indexing architecture, supports incremental updates
   - MD5 hash intelligent detection of document changes
   - Delayed deletion mechanism (Windows compatible)

3. **🚀 Performance Optimization**
   - Document preloading, accelerated first query
   - Multi-level caching (retriever_cache, document_cache)
   - Intelligent Top-K sorting, reduced LLM evaluation times

4. **🎨 User Experience**
   - New quick start script
   - Optimized reference source display
   - Fixed text color display issues




## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## 💡 FAQ

### Q1: Why is intelligent mode slow?
A: Intelligent mode requires calling LLM for relevance judgment on each candidate chunk. If top_k=10 is set, 10 LLM calls are needed. Recommendations:
- Use fast mode for daily use
- Use intelligent mode only for important queries
- Lower top_k value (e.g., 5-8)

### Q2: How to choose top_k value?
A: Recommendations:
- Single document query: top_k=5-8
- Full document query: top_k=10-15
- Precise query (e.g., data lookup): top_k=3-5
- Exploratory query (e.g., topic review): top_k=15-20

### Q3: Do I need to restart the service after updating documents?
A: No need! Just upload a file with the same name for hot update. The system will:
1. Automatically detect file changes (MD5 comparison)
2. Only rebuild that document's vector index
3. Other documents completely unaffected

### Q4: Which LLM models are supported?
A: Currently supports Alibaba Cloud Bailian platform models:
- qwen-max-latest (most powerful, recommended)
- qwen-plus-latest (balanced)
- qwen-turbo-latest (fast)

Can be adapted to other OpenAI-compatible APIs by modifying `config.py`.

### Q5: How to handle oversized documents?
A: System automatically chunks:
- Default chunk_size=600 characters
- chunk_overlap=150 characters
- Recommended single document<1MB
- Overall Database Full Document Size: Recommended <60MB
- Oversized documents recommended to split before uploading

---

## 📧 Contact

- Issue Reporting: Submit GitHub Issue / contact@wanrenai.com
- Feature Suggestions: Welcome to discuss
- Technical Exchange: Welcome contributions

---
