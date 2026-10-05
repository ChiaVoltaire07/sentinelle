# Contribuer à Sentinelle

Merci de venir. Si tu n'as jamais ouvert de pull request, tu es au bon endroit : chaque tâche simple demande **un seul fichier nouveau**. Deux personnes ne modifient donc pas la même ligne, et il n'y a pas de conflit à démêler.

Les tâches marquées **Plus tard** demandent déjà de lire le code. Laisse-les pour quand les branches et les revues seront devenues naturelles. Pendant l'atelier, prends uniquement une issue avec le label `good first issue`.

## Choisir une tâche

1. Ouvre les [issues « good first issue »](https://github.com/arispacco/sentinelle/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
2. Lis le fichier demandé. S'il est déjà créé sur `main`, ou si quelqu'un a commenté « Je la prends », choisis une autre issue.
3. Commente **Je la prends** sous l'issue. Une personne par issue.

Si toutes les issues simples sont prises, ta première pull request reste possible sans conflit : copie [`participants/EXEMPLE.md`](participants/EXEMPLE.md) vers `participants/ton-prenom-ton-nom.md`. Un fichier par personne. N'ajoute pas ton nom dans un fichier commun.

## Les sept étapes

Fais-les dans l'ordre. Attends que chacune soit finie avant la suivante.

### 1. Fork

Sur GitHub, ouvre [arispacco/sentinelle](https://github.com/arispacco/sentinelle) et clique sur **Fork**. Tu obtiens une copie sur ton compte.

### 2. Clone

Dans Git Bash (Windows) ou le terminal :

```bash
git clone https://github.com/TON-COMPTE/sentinelle.git
cd sentinelle
```

Remplace `TON-COMPTE` par ton identifiant GitHub.

### 3. Branche

Ne commite jamais sur `main`.

```bash
git switch -c docs/readme-en
```

Le nom de branche suggéré est écrit dans l'issue. `git switch -c` crée la branche et t'y place.

### 4. Le fichier

Crée **uniquement** le fichier indiqué dans l'issue. Ne modifie pas `README.md`, ni le fichier d'une autre langue, ni ce guide.

Exemple pour la traduction anglaise du README :

```bash
mkdir -p docs/i18n/en
```

Puis enregistre le texte dans `docs/i18n/en/README.md`.

### 5. Commit

Vérifie d'abord que Git te connaît. L'e-mail doit être celui de ton compte GitHub (ou l'adresse `noreply` de GitHub), sinon la contribution n'apparaît pas sur ton profil.

```bash
git config --global user.name "Ton Nom"
git config --global user.email "ton-email@exemple.com"
```

```bash
git add docs/i18n/en/README.md
git status
git commit -m "docs: traduire le README en anglais"
```

`git add` choisit ce qui entre dans l'instantané. `git commit` l'enregistre. Garde toujours l'option `-m` : sans elle, un éditeur Vim peut s'ouvrir (`Echap` puis `:q!` pour en sortir sans rien sauver).

`git status` doit montrer un seul fichier ajouté.

### 6. Push

```bash
git push -u origin docs/readme-en
```

GitHub n'accepte plus le mot de passe du compte dans le terminal. Si l'authentification échoue :

- soit `gh auth login` ;
- soit un **Personal Access Token (classic)** avec la portée `repo`, collé à la place du mot de passe (Settings → Developer settings → Personal access tokens).

### 7. Pull request

Sur ton fork, GitHub propose **Compare & pull request**. Si le bandeau a disparu : onglet **Pull requests** → **New pull request**, et choisis ta branche.

- Titre : celui proposé dans l'issue.
- Description : lien vers l'issue, par exemple `Fixes #12` (le numéro est celui de l'issue).
- Vérifie que la base est `arispacco/sentinelle`, branche `main`, et que ta branche part de ton fork.

## Règles qui évitent les conflits

- Une issue = un fichier nouveau = une branche = une pull request.
- Tu ne modifies pas un fichier qu'une autre issue demande aussi.
- Tu ne pousses pas de secret (`.env`, clé, token, cookie, session Telegram).
- Tu relis le texte. Un outil d'IA peut t'aider à comprendre, pas à envoyer une traduction que tu n'as pas lue.
- Pour une correction demandée par le mainteneur, tu commites sur **la même branche** puis tu refais `git push`. N'ouvre pas une deuxième pull request.

## Si quelque chose bloque

| Message | Quoi faire |
| --- | --- |
| `git: command not found` | Installe Git, ferme le terminal, rouvre Git Bash. |
| `Please tell me who you are` | Les deux commandes `git config --global` ci-dessus. |
| `Authentication failed` | Token ou `gh auth login`. Le mot de passe GitHub ne marche pas ici. |
| `fatal: not a git repository` | `cd sentinelle` |
| `rejected` au push | `git pull --rebase origin ta-branche` puis `git push` |
| Commit fait sur `main` par erreur | `git switch -c ma-branche` (le commit suit la nouvelle branche) |
| Pas de bandeau de pull request | Pull requests → New pull request |
| `LF will be replaced by CRLF` | Message sans gravité sous Windows |

Le plan B si l'installation de Git échoue : sur le dépôt GitHub, touche `.` pour ouvrir github.dev et faire la pull request depuis le navigateur. La règle du fichier unique reste la même.

## Après l'atelier

Les issues **sans** le label `good first issue` décrivent des corrections réelles (port du conteneur, tests manquants, prix du simulateur). Elles sont faites pour le reste du mois, une personne à la fois, après lecture du code cité dans l'issue.
