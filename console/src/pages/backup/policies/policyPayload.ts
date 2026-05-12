export type PolicyPluginKind = 'file' | 'postgres_pgbackrest';

export function parseConfig(raw: Record<string, unknown> | undefined, plugin: PolicyPluginKind) {
  if (plugin === 'postgres_pgbackrest') {
    const c = raw ?? {};
    return {
      stanza: String(c.stanza || ''),
      pg_host: String(c.pg_host || ''),
      pg_port: typeof c.pg_port === 'number' ? c.pg_port : 5432,
      pg_data_path: String(c.pg_data_path || ''),
      pgbackrest_operation: (c.pgbackrest_operation as string) || 'backup',
      backup_type: (c.backup_type as string) || 'full',
      repo_s3_bucket: String(c.repo_s3_bucket ?? ''),
      repo_s3_prefix: String(c.repo_s3_prefix ?? ''),
      repo_s3_region: String(c.repo_s3_region ?? ''),
      repo_s3_endpoint: String(c.repo_s3_endpoint ?? ''),
      repo_path: String(c.repo_path ?? ''),
    };
  }
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

export function buildConfigPayloadFromValues(v: Record<string, unknown>, plugin: PolicyPluginKind) {
  if (plugin === 'postgres_pgbackrest') {
    const op = String(v.pgbackrest_operation || 'backup').toLowerCase() === 'expire' ? 'expire' : 'backup';
    const cfg: Record<string, unknown> = {
      version: 1,
      stanza: String(v.stanza || '').trim(),
      pg_host: String(v.pg_host || '').trim(),
      pg_port: Number(v.pg_port) > 0 ? Number(v.pg_port) : 5432,
      pg_data_path: String(v.pg_data_path || '').trim(),
      pgbackrest_operation: op,
    };
    if (op === 'backup') {
      cfg.backup_type = String(v.backup_type || 'full').toLowerCase() === 'incr' ? 'incr' : 'full';
    }
    const bucket = String(v.repo_s3_bucket || '').trim();
    const prefix = String(v.repo_s3_prefix || '').trim();
    if (bucket && prefix) {
      cfg.repo_s3_bucket = bucket;
      cfg.repo_s3_prefix = prefix;
      const region = String(v.repo_s3_region || '').trim();
      if (region) cfg.repo_s3_region = region;
      const endpoint = String(v.repo_s3_endpoint || '').trim();
      if (endpoint) cfg.repo_s3_endpoint = endpoint;
    } else {
      const rp = String(v.repo_path || '').trim();
      if (rp) cfg.repo_path = rp;
    }
    return cfg;
  }
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
