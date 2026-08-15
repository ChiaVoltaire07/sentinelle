# 🛡️ Sentinelle — Hub d'Intelligence, Veille & Décision Clinique

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

**Sentinelle** est une plateforme SaaS complète de **recherche ancrée sur le web scraping en temps réel**, de **veille clinique B2B pour praticiens africains** et de **simulation de marchés financiers**.

L'assistant IA (alimenté par Google Gemini) génère des synthèses strictement vérifiables, sourcées et indexées 24/7 par un réseau de scrapers autonomes.

---

## 🌟 Les Piliers du Produit

1. **🔍 Recherche Ancrée (Style Perplexity)** : Réponses sourcées en direct, citations vérifiables, score de crédibilité multi-sources.
2. **🏥 Portail Clinique & Pharmacopée B2B** : Essais cliniques PubMed & ClinicalTrials.gov géolocalisés en Afrique, fiches de synthèse exportables/imprimables, et base de pharmacologie inversée des plantes médicinales traditionnelles.
3. **📈 Marchés Financiers & Paper Trading** : Flux de cotations en direct (Binance SSE + Yahoo Finance), graphiques en chandeliers (TradingView Lightweight Charts), et simulateur de portefeuille éducatif sans risque financier.
4. **🔔 Moteur d'Alertes & Veille Personnalisée** : Surveillance continue par mots-clés avec notifications email SMTP et Web Push (Firebase Cloud Messaging).

---

## 🚀 Démarrage Rapide

### Option 1 : Développement Local (Windows / Linux / Mac)

```bash
# 1. Cloner le dépôt
git clone https://github.com/arispacco/sentinelle.git
cd sentinelle

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer l'environnement
cp .env.example .env

# 4. Lancer le serveur et le bot
python -m uvicorn web.server:app --reload --port 8000
```
Rendez-vous sur **`http://localhost:8000`**.

---

### Option 2 : Déploiement Cloud sur Render (Docker)

1. Connectez votre compte Render à votre dépôt GitHub : `https://github.com/arispacco/sentinelle.git`.
2. Créez un service via le fichier de blueprint [`render.yaml`](./render.yaml).
3. Ajoutez les variables d'environnement dans le Dashboard Render :
   - `GEMINI_API_KEY` : Clé API Google AI Studio
   - `FIREBASE_CREDENTIALS_JSON` : Clé de compte de service Firebase
   - `PYTHON_ENV` : `production`

---

## 📱 Application Mobile Flutter (`medical_app`)

L'application mobile multiplateforme (Android / iOS) permet aux professionnels de santé d'accéder aux essais cliniques et monographies hors-ligne :

```bash
cd medical_app
flutter pub get
flutter run
```

---

## 🧪 Tests Automatisés

Pour exécuter la suite de tests complète (50 tests unitaires et d'intégration) :

```bash
python -m unittest discover tests
```

---

## 🔒 Sécurité & Conformité

- **Authentification Unifiée** : Firebase Auth (Google SSO + Email/Password) + JWT propriétaire B2B.
- **Protection des Routes** : Accès libre en lecture (GET), authentification obligatoire en écriture (POST/PUT/DELETE).
- **Anti-Abus** : Rate Limiter thread-safe avec fenêtre glissante (`asyncio.Lock`).
- **Avertissement Légal** : Les informations médicales et financières fournies par Sentinelle sont délivrées à titre informatif et ne constituent ni un diagnostic médical, ni un conseil en investissement.

---

## 📄 Licence
Projet sous licence MIT — Développé par **Aris Pacco** (2026).

