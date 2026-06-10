# Qdrant volume backup and restore

Compose project name defaults to `deploy` → volume `deploy_qdrant_data`.

## Backup

```bash
# From repo root
bash scripts/qdrant_backup.sh backup
# or explicit output path
bash scripts/qdrant_backup.sh backup ./backups/qdrant-$(date +%Y%m%d).tar.gz
```

Creates a tarball of the Docker volume without stopping Qdrant (best-effort; for production prefer brief maintenance window).

## Restore

```bash
docker compose -f deploy/docker-compose.yml stop qdrant api
bash scripts/qdrant_backup.sh restore ./backups/qdrant-YYYYMMDD.tar.gz
docker compose -f deploy/docker-compose.yml up -d qdrant api
curl -sf http://localhost:6333/readyz
```

## Verify after restore

```bash
curl -sf http://localhost:8000/health
curl -s -X POST http://localhost:8000/v1/workspace/index \
  -H "X-API-Key: dev" -H "Content-Type: application/json" \
  -d '{"workspace_id":"local","paths":["guide/"]}' | jq
```

## RPO / ops notes

- **RPO:** Depends on backup schedule (manual or cron). No continuous replication in MVP.
- **Reindex fallback:** If restore fails, run `aicery workspace index` on critical paths.
- Volume name: `docker volume ls | grep qdrant` if project prefix differs.

See [https://aicery.dev/docs](https://aicery.dev/docs) for operations guides.
