# Wanren AI Memex 具身智能平台记忆系统 

> **支持One Brain Meta Body的通用具身机器人大脑记忆系统 - 动态知识记忆子系统**

Memex的记忆子系统（xRAG），专为机器人落地业务流程优化的动态知识强化系统，以仿人类记忆系统支持机器人的长短期专业知识记忆与智能过滤，支持多领域知识智能检索融合、动态扩展、更新、遗忘、及机器人记忆的灵活管理。

---

## ✨ 核心特性

### 🎯 创新亮点

#### 1. **智能两阶段检索（LLM增强）**
传统的机器人记忆系统仅支持固定知识记忆或依赖向量相似度的Embedding检索，对语义相似的专业知识容易混淆，有一定的概率引出幻觉或输出与实际沟通不相关的内容。
为使机器人的回答更加可靠，真实，本记忆系统创新性地引入**两阶段记忆检索架构**：

```
用户查询 → 向量检索Top-K → LLM逐一评估相关性 → 精选Chunks → 生成高质量答案
```

- **第一阶段**：混合检索（向量 + BM25）从所有文档快速筛选Top-K候选chunks
- **第二阶段**：对每个候选chunk使用LLM进行相关性判断，过滤无关内容
- **效果提升**：显著提高答案准确性，减少幻觉和无关信息

**示例场景**：
```
查询：”悉悉，巴菲特2023年的投资策略是什么呀？”
传统记忆：可能召回包含"2023"和"策略"但谈论其他主题的内容
Memex：LLM评估后仅保留真正讨论巴菲特2023年投资策略的chunks
```

#### 2. **灵活的文档管理系统**
解决传统机器人记忆系统的痛点，特别适合需要频繁更新业务文档与规范的场景（如银行规章、法律条文）：

**传统记忆的问题**：
- ❌ 修改一个知识文档 → 需要重建/重索引整个向量数据库
- ❌ 文档版本管理困难
- ❌ 无法动态增量更新
- ❌ 计算资源浪费严重

**Memex记忆系统的解决方案**：
- ✅ **独立的记忆索引**：每个文档单独存储向量索引，分层管理记忆，减少耦合，互不干扰
- ✅ **动态知识更新检测**：基于MD5哈希自动检测文档变化
- ✅ **热更新，短记忆**：修改记忆仅重建该文档的索引，秒级完成
- ✅ **遗忘机制，延迟删除机制**：优化文件锁，渐进遗忘，高效利用运算与存储资源

```python
# 更新单个记忆文件 - 仅重建该文件索引
assistant.update_document("report_2024.pdf")

# 系统自动：
# 1. 检测记忆文件是否产生物理变化（优选MD5对比）
# 2. 仅重建变化文件的向量索引
# 3. 其他记忆文件索引完全不受影响
```

#### 3. **全记忆智能检索**
- 一次查询，跨所有机器人记忆系统大面积搜索
- 自动汇总不同记忆单元内的相关信息
- 智能标注知识与记忆原始来源（记忆文件名+区块）
- 支持快速模式（向量检索）和智能模式（LLM过滤）

#### 4. **对话历史记忆**
- 短记忆范围：保留最近3轮对话上下文
- 短记忆更新：支持追问和澄清
- 短记忆遗忘：自动管理历史长度，防止溢出，提高效率

#### 5. **混合检索策略**
- **Dense Retrieval**：向量相似度（语义理解）
- **Sparse Retrieval**：BM25关键词匹配（精确匹配）
- **Rerank**：可选的重排序模块，进一步优化结果

---

## 🏗️ 系统架构

### 整体架构图

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
│ (阿里百炼)  │  │    Model     │  │    Model    │
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

### 核心模块说明

#### 1. **知识库管理 (knowledge_base.py)**
```python
KnowledgeBaseManager
├── upload_document()      # 上传并索引文档
├── update_document()      # 智能增量更新
├── delete_document()      # 安全删除（延迟清理）
├── list_documents()       # 文档列表
└── get_retriever()        # 获取检索器
```

**核心创新**：
- 每个文档独立的collection_id（基于文件名MD5）
- 文档级别的缓存管理（document_cache, retriever_cache）
- 智能哈希对比，避免无意义的重建

#### 2. **对话管理 (conversation.py)**
```python
ConversationManager
├── chat()                              # 同步对话
├── chat_stream()                       # 流式对话
├── smart_all_documents_retrieve()      # 智能全文档检索
└── _manage_history()                   # 历史管理
```

**智能检索流程**：
```python
async def smart_all_documents_retrieve(question, all_docs, top_k=10):
    # 1. 从所有文档收集候选chunks
    all_chunks = []
    for doc in all_docs:
        chunks = retriever.get_relevant_documents(question)
        all_chunks.extend(chunks)
    
    # 2. 按分数排序，取Top-K
    top_chunks = sorted(all_chunks, by_score)[:top_k]
    
    # 3. LLM批量评估相关性
    relevant_chunks = []
    for chunk in top_chunks:
        is_relevant = llm.evaluate(question, chunk)
        if is_relevant:
            relevant_chunks.append(chunk)
    
    # 4. 使用精选chunks生成答案
    return generate_answer(question, relevant_chunks)
```

#### 3. **相关性评估器 (relevance_evaluator.py)**
```python
RelevanceEvaluator
├── batch_evaluate_relevance()    # 批量评估
├── _evaluate_single()            # 单次评估
└── _build_evaluation_prompt()    # 构建评估prompt
```

**评估Prompt示例**：
```
请判断以下文本片段是否与问题相关。

**问题**: 巴菲特如何看待加密货币？

**文本片段**:
我一直认为比特币是一种投机工具，而不是真正的投资...

**判断标准**:
- 如果文本直接回答或部分回答了问题，回答"Y"
- 如果文本提供了相关背景或上下文信息，回答"Y"  
- 如果文本与问题完全无关，回答"N"

**请仅回答 Y (相关) 或 N (不相关)**:
```

#### 4. **向量存储 (vector_store.py)**
```python
VectorStoreManager
├── create_collection()      # 创建向量集合
├── get_collection()         # 获取现有集合
├── delete_collection()      # 删除集合
└── list_collections()       # 列出所有集合

RetrieverFactory
├── create_hybrid_retriever()  # 混合检索器（向量+BM25）
└── add_reranking()           # 添加重排序
```

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 阿里云百炼API密钥（支持通义千问系列模型）
- 4GB+ RAM（推荐8GB）

### 1. 安装依赖

```bash
pip install -r requirements.txt --break-system-packages
```

### 2. 配置API密钥

```bash
export DASHSCOPE_API_KEY='your_api_key_here'
```

或在代码中配置：
```python
# config.py
DASHSCOPE_API_KEY = "your_api_key_here"
```

### 3. 快速启动

```bash
方式1:使用快速启动脚本
# macOS/Linux用户：
chmod +x quick_start.sh
./quick_start.sh
#Windows用户：
1. 双击 quick_start.bat
2. 等待服务启动
3. 浏览器自动打开

方式2: 手动启动
# 终端1: 启动后端
python start_backend.py

# 终端2: 启动前端
python start_fronted.py
```

### 4. 访问界面

- **Web界面**: http://localhost:7862
- **API文档**: http://localhost:8000/docs

---

## 📖 使用指南

### 基本使用

#### 1. 上传文档
- 支持格式：TXT, CSV, DOC, DOCX, PDF, MD
- 自动切分、向量化、索引
- 进度实时显示

#### 2. 选择检索模式

**⚡ 快速模式**（推荐日常使用）
- 纯向量检索
- 响应速度：1-3秒
- 适合：一般性问答

**🧠 智能模式**（推荐重要查询）
- 向量检索 + LLM评估
- 响应速度：8-15秒
- 适合：需要高准确度的问答
- 自动过滤不相关内容

#### 3. 开始对话

**单文档查询**：
```
选择文档：financial_report_2024.pdf
问题：2024年第二季度的净利润是多少？
```

**全文档查询**：
```
选择文档：✨ 全部文档
问题：对比2023和2024年的投资策略有什么变化？
```

**追问对话**：
```
第一轮：巴菲特对科技股的看法是什么？
第二轮：他具体投资了哪些科技公司？  # 系统记住上下文
第三轮：这些投资的回报率如何？      # 继续追问
```

### 高级功能

#### 文档管理

**更新文档**：
```python
# 方法1: Web界面直接上传同名文件
# 方法2: API调用
PUT /documents/{document_name}
```

**删除文档**：
- 支持安全删除，自动清理向量索引
- Windows环境延迟删除机制，避免文件锁问题

#### 参数调优

**智能模式参数**：
- `top_k`: 初始召回数量（5-20，默认10）
- `fallback_ratio`: 保底比例（0.2-0.8，默认0.5）

```
top_k=10 → 从所有文档召回10个最相关chunks
         → LLM评估后可能保留3-8个真正相关的
         → 如果LLM全部判定不相关，保底返回5个（10*0.5）
```

**模型参数**：
- `temperature`: 创造性（0.0-1.0，默认0.7）
- `max_tokens`: 最大回答长度（500-8000，默认3000）

---

## 🔧 项目结构

```
rag-document-assistant/
├── __init__.py              # 包初始化
├── config.py                # 配置管理
├── llm_client.py            # LLM客户端（对话、Embedding、Rerank）
├── document_loader.py       # 文档加载器（多格式支持）
├── vector_store.py          # 向量存储管理
├── knowledge_base.py        # 知识库管理器 ⭐
├── conversation.py          # 对话管理器 ⭐
├── relevance_evaluator.py  # LLM相关性评估器 ⭐
├── rag_system.py            # RAG系统核心接口
├── api_server.py            # FastAPI后端服务
├── api_client.py            # API客户端封装
├── web_ui_api.py            # Gradio Web界面
├── cli.py                   # 命令行工具
├── logging_config.py        # 日志配置
├── utils.py                 # 工具函数
├── start_backend.py         # 后端启动脚本
├── start_fronted.py         # 前端启动脚本
├── quick_start.sh           # 快速启动脚本 🆕
├── requirements.txt         # Python依赖
└── README.md               # 本文档
```

---

## 🆚 与传统RAG的对比

| 特性 | 传统RAG | 本系统 |
|------|---------|--------|
| **检索方式** | 单一向量检索 | 向量+BM25混合检索 |
| **结果过滤** | 仅依赖相似度 | **LLM智能评估** ⭐ |
| **文档更新** | 需重建全库 | **独立索引，秒级更新** ⭐ |
| **跨文档查询** | 需手动指定 | 自动全文档检索 |
| **对话记忆** | 无或有限 | 3轮上下文记忆 |
| **来源标注** | 基础信息 | 文档名+页码详细标注 |
| **部署复杂度** | 较高 | 一键启动脚本 |

---



### 系统容量

- **文档数量**：无理论上限（实测100+文档稳定）
- **单文档大小**：建议<1MB（超大文档自动分块）
- **整体数据库全文档大小**：建议<60MB
- **并发连接**：支持10+并发用户
- **向量维度**：1536（text-embedding-v3）

---

## 🔐 安全特性

1. **API密钥管理**：环境变量隔离，不硬编码
2. **数据隔离**：每个文档独立存储，互不干扰
3. **资源清理**：自动管理临时文件和内存
4. **错误处理**：完善的异常捕获和日志记录

---

## 🛠️ 技术栈

### 核心框架
- **LangChain**: RAG框架
- **FastAPI**: 后端API服务
- **Gradio**: Web前端界面

### LLM服务
- **阿里云百炼平台**
  - 对话模型：通义千问系列（Qwen-Max/Plus/Turbo）
  - Embedding：text-embedding-v3
  - Rerank：gte-rerank-v2

### 向量数据库
- **Chroma**: 轻量级向量数据库
- **BM25Retriever**: 关键词检索

### 其他
- **Loguru**: 日志管理
- **Pydantic**: 数据验证
- **HTTPX**: HTTP客户端

---


**重大更新**：

1. **🎯 智能两阶段检索**
   - 新增LLM相关性评估模块
   - 批量评估优化，提升效率
   - 缓存机制减少重复评估

2. **🔧 灵活文档管理**
   - 独立索引架构，支持增量更新
   - MD5哈希智能检测文档变化
   - 延迟删除机制（Windows兼容）

3. **🚀 性能优化**
   - 文档预加载，首次查询加速
   - 多级缓存（retriever_cache, document_cache）
   - 智能Top-K排序，减少LLM评估次数

4. **🎨 用户体验**
   - 新增快速启动脚本
   - 优化引用来源显示
   - 修复文字颜色显示问题




## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 💡 常见问题

### Q1: 智能模式为什么慢？
A: 智能模式需要对每个候选chunk调用LLM进行相关性判断。如果设置top_k=10，就需要10次LLM调用。建议：
- 日常使用选择快速模式
- 重要查询才使用智能模式
- 降低top_k值（如5-8）

### Q2: 如何选择top_k值？
A: 建议：
- 单文档查询：top_k=5-8
- 全文档查询：top_k=10-15
- 精确查询（如数据查找）：top_k=3-5
- 探索性查询（如主题综述）：top_k=15-20

### Q3: 更新文档后需要重启服务吗？
A: 不需要！直接上传同名文件即可热更新。系统会：
1. 自动检测文件变化（MD5对比）
2. 仅重建该文档的向量索引
3. 其他文档完全不受影响

### Q4: 支持哪些LLM模型？
A: 当前支持阿里云百炼平台的模型：
- qwen-max-latest（最强，推荐）
- qwen-plus-latest（平衡）
- qwen-turbo-latest（快速）

可通过修改`config.py`适配其他OpenAI兼容API。

### Q5: 如何处理超大文档？
A: 系统自动分块处理：
- 默认chunk_size=600字符
- chunk_overlap=150字符
- 建议单文档<1MB
- 建议数据库全文档<60MB
- 超大文档建议拆分后上传

---

## 📧 联系方式

- 问题反馈：提交 GitHub Issue / contact@wanrenai.com
- 功能建议：欢迎讨论
- 技术交流：欢迎贡献

---
