# 二次开发说明

本仓库是基于 [chatchat-space/Langchain-Chatchat](https://github.com/chatchat-space/Langchain-Chatchat) 的个人二次开发 fork，用于大模型应用方向的学习与面试项目实践。改动保持原项目结构，默认不改变原有行为。

## 改动概览

| 方向 | 涉及文件 | 说明 |
|---|---|---|
| RAG 检索降级路由 | `libs/chatchat-server/chatchat/server/chat/kb_chat.py` | 新增 `fallback_to_search` 参数；知识库召回为空时降级调用搜索引擎补充上下文，搜索失败不影响主流程 |
| 检索评测 | `libs/chatchat-server/eval_rag.py` | 控制变量对比 `top_k`、`score_threshold`、降级开关，输出命中率、平均延迟、p95 延迟、平均召回数，结果写入 CSV |
| Agent 工具 | `libs/chatchat-server/chatchat/server/agent/tools_factory/system_time.py` 与 `__init__.py` | 新增 `system_time` 工具并注册到工具注册表 |
| API 可观测性 | `libs/chatchat-server/chatchat/server/api_server/observability.py` 与 `server_app.py` | 纯 ASGI 请求日志中间件与统一异常处理，不破坏 SSE 流式响应 |

## 本地运行

- 推荐 Docker：镜像 `chatimage/chatchat:0.3.1.3-93e2c87-20240829`，用 `docker compose` 启动。
- 将本仓库修改后的源文件复制进容器后重启即可生效，无需重新构建镜像。
- 也可按上游 README 使用 Python 3.11 + Poetry 源码安装。

## 评测复现

1. 启动服务，确认 API 地址为 `http://127.0.0.1:7861`。
2. 准备评测集：
   ```bash
   cp libs/chatchat-server/eval_samples.example.json libs/chatchat-server/eval_samples.json
   ```
   把 `question` 改成知识库中的事实性问题，`expected_tokens` 填答案必然出现的关键词。
3. 运行评测：
   ```bash
   cd libs/chatchat-server
   python eval_rag.py --kb-name samples --tests eval_samples.json --top-k 3,5,10 --out eval_report.csv
   ```
4. 需要对比降级开关时追加 `--fallback`；需要评测 LLM 回答质量时追加 `--answer`（要求模型已配置可用）。

## 说明

- 改动仅用于个人学习与面试项目，未修改上游许可证与原作者署名。
- `eval_samples.example.json` 为模板，正式评测请替换为自己的知识库问题。