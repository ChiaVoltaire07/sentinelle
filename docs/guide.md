# Guide de Sentinelle

Ce document explique ce que fait le projet, comment le lancer, et où poser une contribution. C'est la version française de référence : les traductions vont dans `docs/i18n/<code>/guide.md`, pas dans ce fichier.

## À quoi sert Sentinelle

Sentinelle rassemble trois usages derrière une même application web.

1. **Recherche sourcée.** Une question reçoit une synthèse appuyée sur des pages collectées, avec les liens d'origine. Le modèle de langage (Google Gemini, ou Ollama en local) ne remplace pas les sources : il les résume.
2. **Portail clinique.** Essais et fiches à destination de professionnels de santé, avec une authentification pour les écritures. Ce n'est pas un dispositif de diagnostic.
3. **Simulateur de marchés.** Cours et paris de prédiction en papier : le portefeuille est virtuel. Ce n'est pas un conseil en investissement.

## Ce que le projet n'est pas

- Un service médical d'urgence.
- Un courtier ou un portefeuille avec de l'argent réel.
- Un endroit où déposer des clés d'API. Le modèle vide est `.env.example`. Le vrai fichier `.env` reste sur ta machine.

## Carte du code

| Chemin | Contenu |
| --- | --- |
| `web/server.py` | Application FastAPI, fichiers statiques, santé du service (`GET /health`) |
| `web/api.py` | Routes HTTP (chat, alertes, médical, marchés, prédictions) |
| `web/static/` | Interface web (HTML, CSS, JavaScript) |
| `bot/` | Orchestration de la veille, stockage, profil, simulateur |
| `scrapers/` | Collectes par thème |
| `models.py` | Offre telle que renvoyée par un scraper |
| `bot/models.py` | Offre enrichie (score, provenance, expiration) |
| `tests/` | Tests automatiques, lancés sans réseau autant que possible |
| `medical_app/` | Client mobile Flutter |
| `docs/OPS.md` | Sauvegardes et exploitation, pas une première contribution |

## Lancer le serveur

Prérequis : Python 3.11 ou 3.12, et Git.

```bash
git clone https://github.com/arispacco/sentinelle.git
cd sentinelle
python -m venv .venv
```

Windows :

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn web.server:app --reload --port 8000
```

macOS et Linux :

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn web.server:app --reload --port 8000
```

Ensuite ouvre `http://localhost:8000`.

Sans `GEMINI_API_KEY`, les synthèses IA restent indisponibles. La page et une partie des collectes peuvent tout de même démarrer. Ne colle aucune clé dans un fichier suivi par Git.

## Vérifier que ça répond

- `GET /health` : le processus web est vivant (c'est le contrôle utilisé au déploiement).
- `GET /api/health` : état du stockage médical et du store principal.

## Lancer les tests

Depuis la racine du dépôt, environnement virtuel activé :

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Les tests fixent `MEDICAL_AUTH_OPTIONAL=1` quand ils montent l'API. Ils ne doivent pas dépendre d'une clé secrète réelle.

## Contribuer sans se marcher dessus

Lis [CONTRIBUTING.md](../CONTRIBUTING.md). Pendant un atelier, chaque personne crée un fichier différent :

- une traduction de ce guide ou du README ;
- un glossaire, une FAQ, ou un guide d'installation pour un seul système.

Les corrections de code (conteneur, tests, simulateur) sont décrites dans des issues à part. Elles ne se prennent pas le jour où l'on découvre GitHub.

## Licence

Le projet est sous licence [MIT](../LICENSE). Tu peux t'en servir, le modifier et le redistribuer, à condition de garder l'avis de copyright.
