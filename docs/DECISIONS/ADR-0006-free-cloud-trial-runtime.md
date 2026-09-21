# ADR-0006：免费云端试运行的数据运行时

- 状态：已批准
- 日期：2026-09-21
- 决策：免费试运行阶段使用 Supabase 托管 PostgreSQL 保存结构化数据，Render Free Web Service 运行 FastAPI；静态 Web 继续由现有公开 Sites 托管。
- 数据库连接：生产环境必须通过 `YANTU_DATABASE_URL` 配置 TLS PostgreSQL URL，并使用 `psycopg` 驱动。生产环境禁止 SQLite，避免 Render 的临时文件系统被误用为正式数据存储。
- 保留：开发和测试继续使用隔离的本地 SQLite；所有学习规则、审计与 AI 草稿确认边界保持不变。
- 不包含：本地正式数据迁移、Supabase Storage 适配、云端备份恢复、自动部署、文件上传的云端持久化。
- 原因：免费 Render 服务会休眠且本地文件系统不持久，不能保存 SQLite 或上传文件。将数据库先迁至托管 PostgreSQL 可建立可验证的云端数据边界，同时避免一次替换数据库、文件存储和备份机制。
- 后果：本 ADR 对应 PR 合入后仍不得把当前文件上传、设置文件或备份恢复能力宣称为云端持久化；在生产 PostgreSQL 模式中，未迁移能力必须由 API 显式拒绝，而不是落入临时磁盘。这些能力必须在独立 Issue 中完成并通过迁移、备份与恢复验收后才可开放真实数据使用。
