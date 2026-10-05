# Signaler un problème de sécurité

N'ouvre pas d'issue publique pour une faille, une clé d'API, un token ou un mot de passe.

1. Révoque tout de suite la clé ou le token concerné, puis génères-en un nouveau. Effacer un commit ne suffit pas : l'historique reste lisible.
2. Écris en privé au mainteneur : [https://github.com/arispacco](https://github.com/arispacco).
3. Si les alertes de sécurité GitHub sont disponibles sur le dépôt, utilise aussi [une alerte privée](https://github.com/arispacco/sentinelle/security/advisories/new).

## Ce qu'il ne faut jamais committer

- le fichier `.env`
- `FIREBASE_CREDENTIALS_JSON`, `GEMINI_API_KEY`, `MEDICAL_AUTH_SECRET`
- cookies LinkedIn, X ou sessions Telegram (`*.session`)
- dumps de base, sauvegardes (`backups/`) et données locales (`data/`)

Le modèle sans secrets est `.env.example`.
