# Ops notes — Portail Clinique

## Secrets
- Ne jamais committer `.env`
- `POSTGRES_PASSWORD` et `MEDICAL_AUTH_SECRET` doivent être forts en production
- `MEDICAL_AUTH_OPTIONAL=0` en production

## Health
`GET /api/health` → status, backend médical, compteurs

## Backups
- Windows: `.\scripts\backup.ps1`
- Linux: `./scripts/backup.sh`
- Postgres: `pg_dump $DATABASE_URL > backups/medical_$(date +%F).sql`

## Ingestion planifiée (exemple Task Scheduler / cron)
```
python -m bot.ingest_medical --delay 0.5
python -m bot.cheat_sheet_queue --limit 100
```

## Observabilité minimale
- `data/ingestion_runs.jsonl` : historique des runs d'ingestion
- table `access_logs` (auth.db) : accès API médicaux
- logs uvicorn / bot stdout
