# Traductions

La référence est le français :

- [README.md](../../README.md) à la racine
- [docs/guide.md](../guide.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md)

Chaque traduction est un **fichier nouveau**. Personne ne modifie le français de référence pour « ajouter une langue », et personne ne modifie ce fichier pour cocher une case : c'est ce qui crée les conflits quand plusieurs pull requests partent en même temps.

## Emplacements

| Langue | Code | README | Guide |
| --- | --- | --- | --- |
| Anglais | `en` | `docs/i18n/en/README.md` | `docs/i18n/en/guide.md` |
| Espagnol | `es` | `docs/i18n/es/README.md` | `docs/i18n/es/guide.md` |
| Portugais | `pt` | `docs/i18n/pt/README.md` | `docs/i18n/pt/guide.md` |
| Arabe | `ar` | `docs/i18n/ar/README.md` | — |
| Swahili | `sw` | `docs/i18n/sw/README.md` | — |

Autres fichiers prévus, toujours un par issue :

- `docs/i18n/en/CONTRIBUTING.md`
- `docs/glossaire.md`
- `docs/faq.md`
- `docs/installation/windows.md`
- `docs/installation/linux.md`
- `docs/installation/macos.md`

Une autre langue suit la même règle : un dossier `docs/i18n/<code>/`, et une issue ouverte avant d'écrire, pour que deux personnes ne visent pas le même chemin.

## Consignes de traduction

- Garder les blocs de code, les commandes, les URL et le nom **Sentinelle** tels quels.
- Garder la structure des titres.
- Pour l'arabe, ajouter en tête du fichier la ligne `<!-- dir: rtl -->` pour signaler le sens de lecture. Le texte, lui, est bien en arabe.
- Ne pas inventer de clé d'API, de statistique ou de promesse médicale.
