# 免费云端试运行部署

## 1. 当前边界

本部署用于个人免费试运行：公开 Sites 托管 Web，Render Free 托管 FastAPI，Supabase 托管 PostgreSQL 和私有 Storage。它不是正式发布，也不改变本地优先架构。

Render Free 空闲约 15 分钟后会休眠，首次唤醒可能需要约一分钟；其本地文件系统会在休眠、重启或重新部署后丢失。结构化数据必须进入 Supabase PostgreSQL，图片和 PDF 原件必须进入私有 `yantu-assets` bucket。云端备份、恢复和个人设置仍保持关闭。

## 2. Blueprint

根目录 `render.yaml` 创建一个 `yantu-coach-api` 免费 Python Web Service：

- 分支：`develop`；
- 自动部署：GitHub CI 全部通过后；
- Python：`3.12.14`；
- 构建：`pip install -e apps/api`；
- 启动：Uvicorn 监听 `0.0.0.0:$PORT`；
- 健康检查：`GET /health`。

免费服务不支持独立 pre-deploy command。当前单实例在 FastAPI 启动阶段运行现有 Alembic 初始化/升级；数据库连接或迁移失败会阻止健康检查通过。

## 3. 初次创建时填写

Render Blueprint 初次创建会要求填写以下 `sync: false` 变量。所有值只粘贴到 Render 的私密输入框，不得提交到仓库、Issue、PR、聊天或截图。

### `YANTU_DATABASE_URL`

1. 在 Supabase 项目顶部点 `Connect`。
2. 选择 `Session pooler`，复制 URI。免费项目的 Direct connection 通常只支持 IPv6；Session pooler 使用 IPv4，更适合外部长期运行后端。
3. 把 URI 中 `[YOUR-PASSWORD]` 替换为数据库密码。密码中的 `&`、`#`、`?`、空格等保留字符必须进行 URL 编码。
4. 确保连接串末尾包含 `?sslmode=require`；已有查询参数时追加 `&sslmode=require`。

### `YANTU_AUTH_TOKEN_SHA256`

在本机仓库运行：

```powershell
python scripts/hash_auth_token.py
```

输入并确认至少 32 个字符的个人访问密钥。原始密钥保存在密码管理器中，Render 只填写脚本输出的 64 位摘要；Web 登录时填写原始密钥。

### `YANTU_SUPABASE_URL`

填写 Supabase Project URL，格式为 `https://<project-ref>.supabase.co`。这是项目地址，不包含 `/storage` 路径。

### `YANTU_SUPABASE_SECRET_KEY`

在 Supabase `Project Settings` → `API Keys` 中创建或复制服务端 Secret Key。该密钥绕过 Storage RLS，只允许保存在 Render 后端环境变量中。

### 证据 AI Provider

Blueprint 默认设置 `YANTU_EVIDENCE_AI_PROVIDER=fake`，因此没有模型密钥时仍可部署和使用确定性核心。测试 DeepSeek 时，在 Render Environment 中设置：

```text
YANTU_EVIDENCE_AI_PROVIDER=deepseek
YANTU_EVIDENCE_AI_API_KEY=<DeepSeek 服务端 API Key>
```

DeepSeek 自动使用 `https://api.deepseek.com` 和 `deepseek-flash`。不要把 Key 填到研途网页、个人访问密钥输入框、GitHub 或 Sites 环境变量中。

百炼、硅基流动等 OpenAI 兼容服务使用：

```text
YANTU_EVIDENCE_AI_PROVIDER=openai_compatible
YANTU_EVIDENCE_AI_API_KEY=<服务端 API Key>
YANTU_EVIDENCE_AI_BASE_URL=<供应商文档给出的 HTTPS OpenAI-compatible API 根地址>
YANTU_EVIDENCE_AI_MODEL=<支持图片输入的模型名>
```

代码会在 Base URL 后追加 `/chat/completions`。切换 Provider 后需要保存环境变量并重新部署 Render。真实 Provider 当前只分析 PNG/JPEG；PDF 仍可保存和查看，但分析会明确失败关闭。

## 4. 自动配置

Blueprint 自动设置：

- `YANTU_APP_ENV=prod`；
- `YANTU_CORS_ALLOWED_ORIGINS=https://yantu-coach-ai-demo-20260715.h1660930192.chatgpt.site`；
- `YANTU_SUPABASE_STORAGE_BUCKET=yantu-assets`。
- `YANTU_EVIDENCE_AI_PROVIDER=fake`（配置真实 Provider 前保持降级模式）。

不要把 bucket 改为 Public。Web 只通过带个人访问密钥的研途教练 API 读取原件。

## 5. 部署后验收

1. Render 部署状态必须为 `Live`，健康检查通过。
2. 打开 `https://<render-host>/health`，响应中 `environment` 必须为 `prod`。
3. 未带个人访问密钥请求 `/api/v1/meta` 必须返回 `401 AUTH_REQUIRED`。
4. 带正确密钥请求 `/api/v1/meta` 必须成功。
5. 运行一轮图片上传和读取，Render 重启后再次读取仍必须成功。
6. Supabase Table Editor 应出现迁移后的业务表，Storage 的 `yantu-assets` 中应出现内容哈希对象。
7. 完成以上项目后，使用 `apps/web/.env.production` 关闭 Demo API、启用个人访问密钥入口，并由 Sites Worker 将同源 `/health` 和 `/api/*` 固定转发到 Render URL。

## 6. 失败与回滚

- 构建失败：检查 Python 版本和依赖安装日志，不修改 Supabase 数据。
- 启动失败：优先检查 Session pooler URI、密码 URL 编码和 `sslmode=require`。
- Storage 返回 503：检查 Project URL、Secret Key 和私有 bucket 名称；禁止回退到 Render 本地磁盘。
- AI 分析显示鉴权失败：只检查 Render 中的 `YANTU_EVIDENCE_AI_*`，不要修改网页登录用的个人访问密钥。
- 需要停止试运行时，在 Render 暂停服务；不要删除 Supabase 数据库或 bucket。
- 回滚代码时使用 Render 最近的成功部署或回滚对应 Git 提交，不执行数据库降级或数据删除。
