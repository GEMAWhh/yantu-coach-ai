# 技术架构

## 1. 架构原则

- 本地优先、单用户优先；
- 确定性规则核心与 AI 能力隔离；
- 结构化数据与原始文件分离；
- 所有自动变化可追溯；
- 先模块化单体，不提前微服务；
- 先 SQLite，不提前图数据库；
- 核心功能在离线和 AI 不可用时仍可运行。

## 2. 推荐技术栈

| 层 | 技术 |
|---|---|
| Web | Vue 3、TypeScript、Vite、Vue Router、Pinia |
| 可视化 | ECharts、Cytoscape.js、PDF.js |
| API | Python、FastAPI、Pydantic |
| 数据 | SQLite、SQLAlchemy 2、Alembic、FTS5 |
| 调度 | APScheduler + 数据库任务表 |
| 测试 | Pytest、HTTPX、Playwright |
| 桌面 | Tauri 2，最后阶段封装 |

## 3. 逻辑分层

```text
Vue 页面与组件
    ↓ 仅通过 API/DTO
FastAPI 路由层
    ↓
应用服务层：用例、事务、权限、幂等
    ↓
领域层：计划、掌握、复习、错题、风险规则
    ↓
仓储层：SQLAlchemy、文件存储、任务表
    ↓
SQLite + 本地文件目录
```

AI 管线是独立适配层：

```text
原始文件 → OCR/多模态模型 → 结构化草稿 → Schema 校验
→ 业务规则校验 → 用户确认 → 应用服务 → 正式数据库
```

## 4. 模块边界

```text
apps/web/src/modules/
  today/ planning/ mastery/ review/ evidence/
  wrongbook/ resources/ graph/ analytics/ settings/

apps/api/app/
  api/ schemas/ models/ repositories/ services/
  domains/planning/ domains/mastery/ domains/review/
  domains/wrongbook/ ai/ files/ security/
```

依赖规则：

- 路由不得直接访问 ORM；
- 前端组件不得直接拼数据库字段；
- 领域规则不得依赖 FastAPI；
- AI 适配器不得直接提交正式业务事务；
- 文件删除必须通过文件服务并记录审计；
- 数据库迁移不得包含业务数据推断。

## 5. 运行目录

```text
data/
  dev/
  test/
  prod/
    database/study.db
    files/original/
    files/derived/
    files/thumbnails/
    exports/
    backups/
    logs/
    cache/
```

数据库只保存文件元数据与哈希，不存大体积 BLOB。

## 6. 任务与异步处理

首版采用：

- FastAPI 后台任务处理轻量工作；
- 数据库 `jobs` 表保存长任务状态；
- APScheduler 处理到期复习、每日生成和自动备份；
- 前端轮询任务状态，必要时使用 WebSocket；
- 不引入 Redis/Celery。

## 7. 错误模型

所有 API 错误使用统一结构：

```json
{
  "error": {
    "code": "MASTERY_TRANSITION_BLOCKED",
    "message": "缺少闭卷回忆证据",
    "details": {"required": ["closed_book_recall"]},
    "request_id": "..."
  }
}
```

用户可修正错误使用 4xx；系统错误使用 5xx；后台任务失败必须保存可读原因和重试策略。

## 8. 一致性与幂等

- 写操作使用数据库事务；
- 上传使用 SHA-256 去重；
- 任务结果、确认草稿和恢复操作支持幂等键；
- 同一 AI 草稿只能确认一次；
- 状态转换使用乐观版本号，防止重复提交覆盖。

## 9. 可观测性

记录：

- request_id、用户动作、业务对象、耗时和结果；
- AI 模型、提示词版本、重试和置信度；
- 状态转换前后、规则版本和证据；
- 备份、恢复、迁移和文件删除；
- 日志不得包含完整 API Key、原始敏感文本或图片二进制。
