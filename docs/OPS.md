# Exploitation

Ce document s'adresse à la personne qui fait tourner Sentinelle, pas à une première pull request. Les secrets se configurent dans l'environnement, jamais dans Git. Voir [SECURITY.md](../SECURITY.md).

## Secrets

- Ne jamais committer `.env`, un dump, ni un fichier `*.session`.
- `POSTGRES_PASSWORD` et `MEDICAL_AUTH_SECRET` doivent être longs et aléatoires en production.
- `MEDICAL_AUTH_OPTIONAL=0` en production : la lecture médicale anonyme reste un réglage local.

Le modèle des variables est [`.env.example`](../.env.example).

## Santé du service

- `GET /health` : processus web, utilisé par le contrôle de [`render.yaml`](../render.yaml).
- `GET /api/health` : backend médical et compteurs du store.

## Sauvegardes

- Windows : `.\scripts\backup.ps1`
- Linux : `./scripts/backup.sh`
- Postgres : `pg_dump "$DATABASE_URL" > backups/medical_$(date +%F).sql`

Le dossier `backups/` est ignoré par Git. Le disque d'un hébergeur gratuit est éphémère : une sauvegarde locale ou un dump vers une base managée survit à un redémarrage, un fichier écrit dans le conteneur non.

## Ingestion planifiée

Exemple pour le planificateur de tâches ou cron :

```bash
python -m bot.ingest_medical --delay 0.5
python -m bot.cheat_sheet_queue --limit 100
```

## Observabilité minimale

- `data/ingestion_runs.jsonl` : historique des runs d'ingestion (dossier local, non versionné).
- table `access_logs` (auth.db) : accès API médicaux.
- journaux du processus web et du bot.
