← [Documentation](index.md)

# Paramètres

Cette page couvre les champs propres à chaque onglet, appliqués immédiatement à la requête suivante (aucun n'est sauvegardé entre deux sessions, sauf indication contraire). Pour l'écran **⚙️ Paramètres** de l'application (réglages généraux, indépendants d'un onglet), accessible tout en bas du menu hamburger, voir [Guide → ⚙️ Paramètres](guide.md#-paramètres).

## Onglet 🔍 Recherche

| Paramètre | Type | Défaut | Valeurs | Effet |
|---|---|---|---|---|
| Mot-clé | texte | `Gemma` | libre | Filtre les résultats par mot-clé. |
| Domaine | liste | `Tous les domaines` | 🧠 LLM, 👁️ Vision, 🖼️ Image, 🎙️ Audio, 🗣️ Speech, 🔤 Embeddings, 🌐 Multimodal, 🧩 Reranking | Restreint les tâches précises proposées ; ne filtre pas seul. |
| Tâche précise | liste | `Toutes les tâches` | dépend du domaine | Seul ce champ filtre réellement par `pipeline_tag` côté Hub. |
| Langue | liste | `Toutes les langues` | langues déclarées par les dépôts | Filtre par langue. |
| Licence | liste | `Toutes les licences` | licences déclarées | Filtre par licence. |
| Trier par | liste | `Téléchargements` | téléchargements, likes, date de création, pertinence | Ordre des résultats. |
| Minimum (milliards) | slider | `0` | 0–200 | 0 = pas de borne minimale de paramètres. |
| Maximum (milliards) | slider | `0` | 0–200 | 0 = pas de borne maximale de paramètres. |
| Nombre de résultats | slider | `20` | 5–100 | Borne obligatoire, imposée côté client et serveur. |

**Application** : immédiate, à l'appui sur Entrée ou clic sur « 🔍 Rechercher ». **Réinitialisation** : bouton « Réinitialiser » (remet tous les champs ci-dessus à leur valeur par défaut).

## Onglet 🎯 Mon usage

| Paramètre | Type | Défaut | Valeurs | Effet |
|---|---|---|---|---|
| Usages | sélection multiple | aucun coché | Chatbot, Coding, RAG, Embeddings, Traduction, Vision, Speech, Génération d'images | Détermine les tâches Hub interrogées. |
| RAM (Go) | nombre | `16` | 0–4096 | Utilisée pour le verdict de compatibilité, jamais transmise au Hub. |
| VRAM (Go) | nombre | `0` | 0–1024 | Idem. Au moins RAM ou VRAM doit être non nulle pour lancer une recherche. |

## Onglet 💻 Hardware

| Paramètre | Type | Défaut | Valeurs | Effet |
|---|---|---|---|---|
| RAM (Go) | nombre | `16` | 0–4096 | Base du calcul des précisions supportées. |
| VRAM (Go) | nombre | `0` | 0–1024 | Idem. |

## Onglet ⭐ Favoris (par favori)

| Paramètre | Type | Défaut | Valeurs | Stockage |
|---|---|---|---|---|
| Collection | texte ou liste | vide | libre (saisie personnalisée acceptée) | `data/favorites.json` |
| Statut | liste | vide | `à tester`, `testé`, `recommandé`, `à écarter` | idem |
| Note personnelle | slider | `0` | 0–5 (0 = aucune note) | idem |
| Tags | texte | vide | libres, séparés par des virgules | idem |
| Dernier test | texte | vide | date au format JJ/MM/AAAA | idem |
| Commentaire | texte libre | vide | libre | idem |

**Application** : immédiate à l'enregistrement du formulaire d'édition. **Stockage** : voir [Données](data.md).

Voir la [table de référence complète](reference.md#table-des-paramètres) pour une vue consolidée.
