# pgBackRest 演示栈 SSH 材料（**仅限本地 compose**）

`id_ed25519` / `id_ed25519.pub` 为 **预生成的演示密钥**，仅用于 `postgres-pgbr-demo` 容器内 **sshd** 与 DeVault **Agent** 之间的 `ssh postgres@postgres-pgbr-demo`（pgBackRest 访问远程 `PGDATA` 的默认方式）。

**请勿**用于任何公网或共享环境；若仓库对外公开，请改为本地 `ssh-keygen` + `.gitignore` 私钥，并在 `docker-compose` 中改为 bind-mount 你本机生成的密钥路径。
