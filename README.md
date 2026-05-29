# Scout — Hub de recherche ancré (style Perplexity)

PWA de **recherche ancrée sur le scraping** : l'assistant répond à partir des sources collectées (actu, crypto, géopolitique, santé, Polymarket), avec espaces thématiques, opportunités ciblées, suivis et Learn Trading (papier).

## Démarrage (Windows)

```powershell
cd D:\scrapper
python -m pip install -r requirements.txt
.\run_all.ps1
```

Ouvre http://127.0.0.1:8000

## Fonctionnalités

- **Chat hub** : question → scrape live → synthèse **uniquement** à partir des sources
- **Profil local** : compétences, ville/pays, intérêts → matching opportunités
- **Opportunités** : emplois, bourses, voyages, events + digest de bienvenue personnalisé
- **Mes suivis** : dashboards (Yahoo Finance historique + actus), auto-refresh ~10 min
- **Learn Trading** : simulation éducative (cash virtuel), niveaux beginner → pro
- **Espaces** : Actualité, Sport, Finance, Crypto, Santé, Géopolitique, Prédictions
- **Thèmes** clair / sombre (ambre / pierre)

## API utiles

- `GET/PUT /api/profile`
- `GET /api/opportunities` / `feed` / `digest`
- `POST /api/chat` `{ "message", "session_id" }`
- `GET /api/spaces` / `GET /api/spaces/{slug}`
- `GET/POST /api/watches*`
- `GET /api/learn/portfolio` · `POST /api/learn/orders` · `POST /api/learn/explain` · `POST /api/learn/sweep`
- `GET /api/crypto/markets` · `GET /api/predictions`
- `GET /api/medical/*` (santé B2B)

## Marché / cours (pile quasi gratuite)

| Actif | Provider | Latence | Clé |
|-------|----------|---------|-----|
| Actions | Yahoo Finance | ~15 min | Non |
| Actions (backup) | Stooq | EOD / delayed | Non |
| Actions (option) | Finnhub / Alpha Vantage | near-realtime | `MARKET_API_KEY` |
| Crypto | **Binance REST** (+ SSE poll) | ~1–3 s | Non |
| Crypto (fallback) | CoinGecko | delayed | Non |

- Graphiques : **TradingView Lightweight Charts** (chandeliers + SMA20)
- `GET /api/market/quote` · `/chart` · `/crypto/tickers` · `/stream/{symbol}` (SSE)
- `GET /api/market/providers` — état des providers
- Tick-by-tick actions US : **pas gratuit** (licences NYSE/NASDAQ). Crypto oui via Binance.

```env
MARKET_PROVIDER=auto          # auto | finnhub | alphavantage
MARKET_API_KEY=               # optionnel free tier
```

## Scrapers

| Module | Source |
|--------|--------|
| `scrapers/news.py` | Google News RSS |
| `scrapers/jobs.py` | RemoteOK, Arbeitnow, Google News jobs |
| `scrapers/scholarships.py` / `travel_opps.py` / `events.py` | Bourses, voyages, events (RSS) |
| `scrapers/crypto.py` | CoinGecko + RSS |
| `scrapers/geopolitics.py` | RSS conflits |
| `scrapers/predictions.py` | Polymarket Gamma API |
| `scrapers/medical.py` | ClinicalTrials + PubMed |

## Tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## Recherche sémantique & fiches IA (médical)

- **Recherche sémantique sans Postgres** : les embeddings (`gemini-embedding-001`, 768 dims) sont stockés en colonne `embedding` de `medical.db` (blob float32, ~3 Ko/dossier) et la similarité cosinus est calculée en Python. Repli automatique sur la recherche textuelle si aucun embedding. PostgreSQL + PostGIS + pgvector reste supporté en option via `DATABASE_URL` (docker-compose).
- **Backfill embeddings** des dossiers existants :
  ```powershell
  python -m bot.embed_medical --limit 400
  ```
- **Batch fiches IA** (cheat sheets) :
  ```powershell
  python -m bot.cheat_sheet_queue --limit 400
  ```
  La file gère les pauses automatiques en cas de quota (429) et reprend là où elle s'était arrêtée.

## Notes

- Prédictions / crypto / Learn Trading : **pas de conseil financier** ; trading = papier uniquement.
- Santé : usage professionnel.
- Le `.venv` Linux (WSL) n'est pas utilisable tel quel sous Windows : utiliser le Python système ou créer `python -m venv .venv` sous Windows.
