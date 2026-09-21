# ADR-0007：私有 Supabase Storage 保存云端原始文件

- 状态：已批准
- 日期：2026-09-21
- 决策：生产 PostgreSQL 模式使用私有 Supabase Storage bucket 保存图片和 PDF 原件；FastAPI 以服务端 Secret Key 调用 Storage API，浏览器只访问研途教练 API。
- 对象命名：沿用 `files/original/<sha256前两位>/<sha256>.<扩展名>`，路径完全由服务端根据已校验内容生成。数据库继续保存 SHA-256、相对对象路径、MIME、大小、状态和引用计数。
- 去重与一致性：相同 SHA-256 复用同一资产并增加引用计数；远端上传失败时不提交新资产元数据。内容寻址对象允许幂等重试，避免数据库事务回滚后无法恢复上传。
- 安全：项目 URL 必须是 HTTPS Supabase Origin；URL、Secret Key 和 bucket 必须完整配置。Secret Key 不进入前端、日志、错误响应、测试夹具真实值或提交历史。
- 保留：开发和测试继续使用隔离的本地 SQLite 与本地文件目录；现有文件类型、文件头、路径穿越和引用删除规则不变。
- 不包含：既有本地文件迁移、云端备份恢复、个人设置持久化、公开对象 URL、多用户 Storage RLS。
- 后果：部署前必须建立私有 bucket 并配置三个服务端环境变量。配置缺失时上传和读取继续失败关闭；Storage 故障返回稳定 503，云端备份和设置仍保持关闭。
