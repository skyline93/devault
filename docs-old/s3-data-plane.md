# S3 数据面：Multipart、流式与配置

本文对应 [`enterprise-backlog.md`](./enterprise-backlog.md) **阶段 B** 中与对象存储相关的实现说明（**0.3.0**）。

---

## 1. 何时使用 Multipart 上传（备份 bundle）

- Agent 在本地打好 `bundle.tar.gz` 后，在 **`RequestStorageGrant`** 中上报 **`bundle_content_length`**。
- 当长度 **≥ `DEVAULT_S3_MULTIPART_THRESHOLD_BYTES`**（默认 32MiB）时，控制面：
  1. 对 bundle key 调用 **`CreateMultipartUpload`**；
  2. 为每个分片生成 **`upload_part` 预签名 PUT**（`BundlePartPresign`）；
  3. 在回复中带上 **`bundle_multipart_upload_id`** 与 **`bundle_multipart_part_size_bytes`**（与分片规划一致）。
- **manifest.json** 体积通常很小，仍使用 **单次 `put_object` 预签名**。

完成后 Agent 在 **`CompleteJob`** 中提交 **`bundle_multipart_upload_id`** 与 **`bundle_multipart_parts_json`**（`[{"PartNumber":1,"ETag":"..."}, ...]`），控制面用平台凭证调用 **`complete_multipart_upload`**，再写入 `Artifact` 记录。

小于阈值时仍走 **单对象 PUT**（但 Agent 侧对大文件使用 **文件句柄流式 PUT**，避免整包读入内存）。

---

## 2. 分片大小与上限

| 变量 | 默认 | 说明 |
|------|------|------|
| `DEVAULT_S3_MULTIPART_THRESHOLD_BYTES` | `33554432` (32MiB) | 达到或超过则走 Multipart。 |
| `DEVAULT_S3_MULTIPART_PART_SIZE_BYTES` | `16777216` (16MiB) | 目标分片大小；**不小于 5MiB**（S3 除最后一片外的限制）。 |

若 `ceil(对象大小 / 分片大小) > 10000`，控制面会自动 **增大有效分片大小**，以满足 S3 **最多 10000 片** 的约束（见 `devault.storage.multipart`）。

---

## 3. 重试与「断点续传」范围

- **已实现**：每个分片 PUT 失败时 **指数退避重试**（同一 Agent 进程、同一租约与预签名有效期内）。
- **待办（见 [`enterprise-backlog.md`](./enterprise-backlog.md) 阶段 B 表）**：
  - **Multipart 跨重启 / 跨进程断点续传**（持久化 `UploadId` 与已完成 Part，重启后续传；与租约、Abort 策略协同）。
  - **STS / AssumeRole 临时凭证**（控制面访问 S3 使用短时会话密钥，替代长期静态 AK/SK）。

---

## 4. 恢复（GET）流式与校验

预签名恢复路径使用 **`httpx` stream** 写入临时文件，并 **分块更新 SHA-256**，与 `development-design.md` 中「禁止一次性读入 artifact」一致；校验通过后再解压。

---

## 5. 云厂商差异（简要）

- **MinIO** 与 **AWS S3** 在预签名 URL、ETag 引号、`complete_multipart_upload` 行为上基本一致；若遇兼容问题，优先核对 **endpoint / path-style / region** 与 **时钟偏差**（预签名过期）。
- **STS 临时凭证**：仍为 backlog **P2**，当前控制面仍使用配置的 AK/SK 或等价环境变量。

---

## 6. 协议字段（`proto/agent.proto`）

- **`RequestStorageGrantRequest.bundle_content_length`**：备份 WRITE 必填（由当前 Agent 实现保证），用于 Multipart 决策。
- **`RequestStorageGrantReply`**：`bundle_multipart_*` 与 `bundle_multipart_part_size_bytes`。
- **`CompleteJobRequest`**：`bundle_multipart_upload_id`、`bundle_multipart_parts_json`。

修改 `.proto` 后执行：`bash scripts/gen_proto.sh`。
