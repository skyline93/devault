#!/bin/sh
# Start sshd (for pgBackRest remote pg1-host) then hand off to official Postgres entrypoint.
set -e
mkdir -p /var/run/sshd
# sshd StrictModes: $HOME must not be group/world-writable or pubkey auth fails.
chmod 700 /var/lib/postgresql
chown postgres:postgres /var/lib/postgresql
/usr/sbin/sshd
exec /usr/local/bin/docker-entrypoint.sh "$@"
