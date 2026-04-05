# FictionGPT (虚构集GPT)

> **AI 驱动的沉沉浸式长篇小说自动生成平台**  
> 结合 DeepSeek R1 的推理能力与 V3 的创作才华，构建你的专属故事世界。

## 项目核心：混合推理架构 (Phase 4)

在 Phase 4 中，FictionGPT 完成了从“纯本地”到“云端优先”的架构演进。通过整合 DeepSeek 系列模型，我们在保证长篇小说逻辑一致性的同时，大幅提升了文采与生成速度。

### 角色分工与模型选型

| 角色 | 模型 (默认配置) | 职责描述 |
| :--- | :--- | :--- |
| **导演 (Director)** | **DeepSeek-R1** | 核心剧情规划、长上下文伏笔编排、逻辑一致性维护。利用 R1 的推理链（CoT）确保复杂世界观不崩塌。 |
| **编剧 (Screenwriter)** | **DeepSeek-V3** | 场景大纲细化、对白设计、节奏把控。 |
| **作家 (Writer)** | **DeepSeek-V3** | 高质量正文写作，具备极强的创意发挥与文学性描写。 |
| **编辑 (Editor)** | (可选) Ollama 本地 | 质量审核与纠偏。 |

## 技术栈

- **后端**: Python 3.10+ / FastAPI / WebSocket (实时流式输出)
- **前端**: React 18 / TypeScript / TailwindCSS / Vite
- **推理后端**: 
  - **云端**: DeepSeek API (兼容 OpenAI 协议)
  - **本地**: Ollama (支持热切换，作为作家/编辑角色的降级方案)
- **存储与记忆**: 
  - **SQLite**: 结构化数据（项目信息、章节摘要、角色谱系）。
  - **ChromaDB**: 向量数据库，基于 `text2vec-base-chinese` 实现语义检索，确保长篇内容不偏离设定。

## 快速开始

### 1. 环境准备

- **API Key**: 准备有效的 `DEEPSEEK_API_KEY`。
- **(可选) Ollama**: 如需使用本地模型作为补充，请安装 [Ollama](https://ollama.com/)。

### 2. 后端部署 (Python)

1. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```
2. **环境变量**:
   复制 `.env.example` 为 `.env`，填入你的 API Key：
   ```env
   DEEPSEEK_API_KEY=sk-your-key-here
   ```
3. **配置路由**:
   检查 `config.yaml`。默认已配置为 DeepSeek 模式，你可以根据需要修改 `backend: "deepseek"` 或 `"ollama"`。
4. **启动服务器**:
   ```bash
   python main.py
   ```
   后端将运行在 `http://localhost:8000`。

### 3. 前端部署 (Node.js)

1. **进入目录**:
   ```bash
   cd frontend
   ```
2. **安装依赖**:
   ```bash
   npm install
   ```
3. **运行开发服务器**:
   ```bash
   npm run dev
   ```
4. **(可选) 生产构建**:
   ```bash
   npm run build
   ```
   构建后的文件会被后端 `main.py` 自动挂载，直接访问 `http://localhost:8000` 即可进入应用。

## 核心流程

1. **建立项目**: 定义世界观、核心冲突、叙事基调与主要人物。
2. **AI 推理**: 导演 (R1) 生成章节规划 -> 编剧 (V3) 生成场景大纲。
3. **流式生成**: 作家 (V3) 实时书写正文，通过 WebSocket 推送至前端，实现“边写边读”的沉浸式体验。
4. **长效记忆**: 系统自动摘要每个章节并存入向量库，后续创作将自动检索相关历史，解决长篇断裂问题。

## 2026-04-05 更新日志：全面多语言支持与推理优化 (Multi-Language & Reasoning Optimization)

FictionGPT 现已全面支持中英文双语创作模式，并针对 DeepSeek-R1 等推理模型在非中文环境下的表现进行了深度优化。

### 新增功能与改进：

1.  **全局多语言架构 (Global Multi-Language Support)**：
    *   **项目级语言设定**：在创建项目时可指定 `zh` (中文) 或 `en` (英文) 作为输出语言。
    *   **自动 Prompt 切换**：Agent 自动根据项目语言加载对应的 `_en.txt` 英文 Prompt 模板，确保系统指令与目标语言完全一致。
    *   **本地化上下文构建**：角色档案、项目设定、叙事解构及编剧大纲均实现了自动化翻译与标签适配（如 `Character Profiles` 代替 `角色状态`）。

2.  **推理模型“思考链”本地化 (Reasoning CoT Localization)**：
    *   针对 DeepSeek-R1 在英文模式下仍倾向于使用中文进行 CoT (思维链) 思考的问题，我们在 User Message 中加入了强制性语言约束指令。
    *   **效果**：模型在英文模式下会完全使用英文进行逻辑推理和正文创作，消除了中文残留。

3.  **精细化正文写作控制 (Refined Prose Control)**：
    *   增强了 `WriterAgent` 的指令集，严禁在正文中复述任务要求、输出列表、幻觉作文题目或解释创作决策。
    *   **英文模式优化**：专门针对英文长篇小说的叙事风格进行了 Prompt 调优。

4.  **自动标题与回退机制 (Localized Chapter Titles)**：
    *   章节标题生成与回退机制（如 `Chapter X` 与 `第X章`）现在会根据项目语言自动切换。
    *   修复了在英文模式下可能出现的中文标题残留问题。

5.  **稳定性与编码修复**：
    *   修复了 `agents/writer.py` 等核心组件在处理特殊字符时的编码问题，提升了系统的健壮性。

---

## 许可证

MIT License
