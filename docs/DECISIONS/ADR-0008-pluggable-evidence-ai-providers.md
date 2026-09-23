# ADR-0008：可插拔证据 AI Provider

- 状态：Accepted
- 日期：2026-09-23

## 决策

证据分析通过服务端 Provider 接口调用模型。保留 Fake Provider 作为默认降级与自动化测试实现；DeepSeek 作为首个真实图片配置；其他供应商通过 OpenAI-compatible Base URL、模型名和 API Key 接入。Provider 只能由服务端环境变量选择。

真实 Provider 当前只接收 PNG/JPEG，并把图片以内联 data URL 发往已配置供应商。PDF 在建立独立且受测的转换/OCR 管线前失败关闭。所有模型输出先经过 `evidence-analysis-v1` 校验并写入草稿，仍须用户确认才能进入正式业务字段。

## 原因

统一兼容层可以在不改前端和业务确认边界的情况下测试 DeepSeek，并为百炼、硅基流动等兼容服务保留替换能力。服务端选择和脱敏作业记录避免把供应商密钥或原件内容暴露给浏览器、数据库和日志。

## 后果

- 切换供应商只修改 Render 的 `YANTU_EVIDENCE_AI_*` 环境变量并重新部署。
- 供应商差异若超出 OpenAI Chat Completions 图像协议，应新增独立适配器和契约测试，不得在业务服务中写供应商分支。
- Provider 不可用、鉴权失败、限流、响应非法或输入类型不支持时，保存脱敏失败作业和待修正草稿；确定性核心继续工作。
- 真实模型上线前仍需使用脱敏样本完成黄金集评测和人工验收。
