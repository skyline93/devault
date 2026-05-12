export function parseConfig(raw: Record<string, unknown> | undefined) {
  const c = raw ?? {};
  const paths = Array.isArray(c.paths) ? (c.paths as string[]).join('\n') : '';
  const excludes = Array.isArray(c.excludes) ? (c.excludes as string[]).join('\n') : '';
  return {
    pathsText: paths,
    excludesText: excludes,
    follow_symlinks: Boolean(c.follow_symlinks),
    preserve_uid_gid: c.preserve_uid_gid !== false,
    one_filesystem: Boolean(c.one_filesystem),
    encrypt_artifacts: Boolean(c.encrypt_artifacts),
    kms_envelope_key_id: (c.kms_envelope_key_id as string) || undefined,
    object_lock_mode: (c.object_lock_mode as string) || undefined,
    object_lock_retain_days: c.object_lock_retain_days as number | undefined,
    retention_days: c.retention_days as number | undefined,
  };
}

export function buildConfigPayloadFromValues(v: Record<string, unknown>) {
  const paths = String(v.pathsText || '')
    .split('\n')
    .map((s: string) => s.trim())
    .filter(Boolean);
  const excludes = String(v.excludesText || '')
    .split('\n')
    .map((s: string) => s.trim())
    .filter(Boolean);
  const mode = v.object_lock_mode as string | undefined;
  const days = v.object_lock_retain_days as number | undefined;
  const config: Record<string, unknown> = {
    version: 1,
    paths,
    excludes,
    follow_symlinks: Boolean(v.follow_symlinks),
    preserve_uid_gid: v.preserve_uid_gid !== false,
    one_filesystem: Boolean(v.one_filesystem),
    encrypt_artifacts: Boolean(v.encrypt_artifacts),
  };
  const kms = (v.kms_envelope_key_id as string)?.trim();
  if (kms) config.kms_envelope_key_id = kms;
  if (mode) {
    config.object_lock_mode = mode;
    config.object_lock_retain_days = days;
  }
  const rd = v.retention_days as number | undefined;
  if (rd != null && rd > 0) config.retention_days = rd;
  return config;
}

export function bindingPayloadFromValues(v: Record<string, unknown>) {
  return { bound_agent_id: v.bound_agent_id as string };
}
