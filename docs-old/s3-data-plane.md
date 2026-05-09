# S3 数据面：Multipart、流式与配置

本文对应 [`enterprise-backlog.md`](./enterprise-backlog.md) **M1 · 二、数据面可靠性** 中与对象存储相关的实现说明（**0.4.0** 起含跨重启 Multipart 续传）。

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

## 3. 重试与 Multipart 断点续传

- **同进程重试**：每个分片 PUT 失败时 **指数退避重试**（同一 Agent 进程、同一租约与预签名有效期内）。
- **跨重启 / 跨进程续传（0.4.0+）**：
  - **控制面**：`jobs.bundle_wip_multipart_upload_id`（及 `bundle_wip_content_length`、`bundle_wip_part_size_bytes`）记录进行中的 MPU；`RequestStorageGrant` 可带 **`resume_bundle_multipart_upload_id`**（须与 WIP 一致），服务端 **`ListParts`** 后仅为缺失分片签发预签名；若 S3 上已齐片，则返回 **`bundle_multipart_completed_parts_json`**，Agent 直接 `CompleteJob`。
  - **Agent**：`~/.cache/devault-agent/multipart/<job_id>/` 下保留 **`bundle.tar.gz`** 与 **`checkpoint.json`**（含 manifest、校验和、已完成 `PartNumber`+`ETag`）；同一作业在租约回收为 **PENDING** 后再次被拉取时，可继续上传。目录根可通过 **`DEVAULT_AGENT_MULTIPART_STATE_DIR`** 配置。
  - **孤儿 MPU**：同一作业 **发起新的** Multipart（不带 resume）前，控制面对旧 WIP 调用 **`AbortMultipartUpload`**；作业 **`CompleteJob` 失败**（终态 FAILED）时亦会 Abort 并清空 WIP 列。
- **Artifact 加密（`encrypt_artifacts`）与续传**：Agent 在 **加密后** 才将 bundle 移入 WIP 路径并写入 **`checkpoint.json`**（manifest 已含 **`encryption`** 块，且 `checksum_sha256` / `content_length` 为 **密文** 维度）。续传前执行 **`validate_multipart_resume_checkpoint`**（`src/devault/plugins/file/multipart_resume.py`）：**策略 `encrypt_artifacts` 必须与 manifest 是否含 `encryption` 一致**；**WIP 文件大小** 须与 checkpoint 的 `content_length` 一致，否则 **清空本地 multipart 状态** 并重新打 tarball + 加密，避免半写入或策略切换后的静默错传。checkpoint JSON 另含 **`encrypt_artifacts`** 布尔字段便于排障。成功且为 Multipart + 加密的 **`CompleteJob`** 递增指标 **`devault_multipart_encrypted_mpu_completes_total`**（控制面）。
- **STS / AssumeRole（控制面 → S3）**：可通过 `DEVAULT_S3_ASSUME_ROLE_ARN` 等变量使用 **短时**会话密钥；与静态 `DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY` 或默认凭证链（IRSA 等）组合方式见 **`website/docs/storage/sts-assume-role.md`** 与 `src/devault/storage/s3_client.py`。

---

## 4. 恢复（GET）流式与校验

预签名恢复路径使用 **`httpx` stream** 写入临时文件，并 **分块更新 SHA-256**，与 `development-design.md` 中「禁止一次性读入 artifact」一致；校验通过后再解压。

---

## 5. 云厂商差异（简要）

- **MinIO** 与 **AWS S3** 在预签名 URL、ETag 引号、`complete_multipart_upload` 行为上基本一致；若遇兼容问题，优先核对 **endpoint / path-style / region** 与 **时钟偏差**（预签名过期）。
- **STS 临时凭证**：控制面支持 **`AssumeRole`** 返回的会话密钥（可缓存至临近过期），亦支持仅静态密钥或仅默认凭证链；详见 **`website/docs/storage/sts-assume-role.md`**。

---

## 6. 协议字段（`proto/agent.proto`）

- **`RequestStorageGrantRequest.bundle_content_length`**：备份 WRITE 必填（由当前 Agent 实现保证），用于 Multipart 决策。
- **`RequestStorageGrantRequest.resume_bundle_multipart_upload_id`**：续传时填写控制面此前返回的 **`bundle_multipart_upload_id`**（须与 DB WIP 一致）。
- **`RequestStorageGrantReply`**：`bundle_multipart_*`、`bundle_multipart_part_size_bytes`、可选 **`bundle_multipart_completed_parts_json`**（已齐片时由服务端填好，供 `CompleteJob`）。
- **`CompleteJobRequest`**：`bundle_multipart_upload_id`、`bundle_multipart_parts_json`。

修改 `.proto` 后执行：`bash scripts/gen_proto.sh`。
