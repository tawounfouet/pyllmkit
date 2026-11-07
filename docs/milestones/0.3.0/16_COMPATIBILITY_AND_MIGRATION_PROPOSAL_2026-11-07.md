# PyLLMKit v0.3.0 - Compatibilité et préparation de migration

> Date : 2026-11-07  
> Statut : **PROPOSITION POUR REVUE S7/G7**, non validée indépendamment, pas une release note publiée.  
> Référence code : `main@b4f91e1dd05ba2e44134c0209fcc3c72f5259f8c`.  
> Package distribué dans le dépôt à cette date : `0.1.0a2`. Le jalon documentaire `0.3.0` n'est pas encore une version distribuée.

## 1. Périmètre garanti et non garanti

Le périmètre technique qualifié par la CI actuelle correspond au **chat text-only avec six adaptateurs natifs** (OpenAI, Anthropic, Google Gemini, xAI, Mistral, Ollama), en mode **offline hermétique** avec fixtures/MockTransport et leurs cas de refus. Les 752 cas PASS n'établissent pas une connectivité réelle, des coûts exacts, la sécurité live ou une couverture de tous les modèles disponibles.

Les interfaces publiques du domaine ne doivent pas être modifiées pour satisfaire seulement le CLI. La compatibilité des consommateurs existants doit être vérifiée au moyen d'une comparaison d'API avant toute release.

## 2. Évolutions CLI utiles aux utilisateurs

| Sujet | Comportement actuellement observé | Migration/attention |
|---|---|---|
| Dépendances | CLI Typer/Rich optionnel via extra `cli` | Installer avec `pip install "pyllmkit[cli]"` dans un environnement contrôlé |
| Invocation | `pyllmkit run` et `pyllmkit stream` offline par défaut | `--live` requis explicitement à chaque invocation distante ; peut entraîner des coûts |
| Config legacy | `defaults.live=True` est ignoré pour l'autorisation réseau | Ne pas compter sur la configuration pour accorder `--live` |
| Historique | Métadonnées SQLite seulement par défaut | `--record-content` distinct et nécessaire à chaque exécution pour stocker prompt/réponse |
| Export JSONL | `runs export` exige `--allow-content-export` | Consentement distinct de `--record-content` pour chaque export |
| Contenu legacy | `runs purge-content --yes` ou `--run-id` | Opération destructive logique ; sauvegardes, fichiers WAL et anciens exports non sécurisés par ce seul outil |
| Rétention | `PYLLMKIT_HISTORY_RETENTION_DAYS` optionnel, pas d'effacement surprise par défaut | Fixer une politique locale de rétention et de sauvegarde |
| FinishReason | `UNKNOWN` reste `UNKNOWN` | Ne pas traiter `run.completed` comme une preuve de `STOP` |
| Catalogue | 131 entrées, 15 catégories ; tarifs locaux indicatifs | Catalogue != déploiement exécutable ; dates/sources tarifaires non temps réel |
| Valeurs inconnues | Contexte / max tokens / prix manquants conservent `None` / N/A | Ne pas remplacer silencieusement par 128k, 8192 ou 0 USD |
| Discovery | `models sync` est une commande réseau explicite distincte des modes `run`/ `stream` | Vérifier credentials, ACL réseau et destinations avant usage |

## 3. Points de rupture potentiels à qualifier

- Passage du CLI vers un fonctionnement offline explicitement autorisé : scripts qui supposaient `defaults.live=True` peuvent maintenant nécessiter `--live`.
- Export JSONL : scripts d'export automatisé doivent ajouter `--allow-content-export` après une revue du traitement des données sensibles.
- Valeurs inconnues du catalogue : les intégrations doivent accepter `None` pour prix et limites plutôt que supposer des floats/ints non null.
- Présence de données SQLite d'anciennes versions : le nouveau défaut metadata-only n'efface pas rétroactivement les anciennes données.
- Le CLI et les modèles du catalogue ne sont pas une promesse de compatibilité avec 15 adaptateurs natifs.
- Les API publiques et contrats de sérialisation doivent faire l'objet d'un diff de signatures/types et d'un contrôle des consommateurs avant tout bump SemVer.

## 4. Qualification de la documentation S7

- [x] Proposition de compatibilité et conseils de migration documentés.
- [x] Risques de comportement CLI explicités.
- [x] Limites offline / live séparées.
- [ ] Vérifier les exemples depuis **wheel installée** au SHA candidat.
- [ ] Ajouter une comparaison d'API publiquement exposée entre `0.1.0a2` et la candidate.
- [ ] Effectuer une revue par un consommateur SDK indépendant.
- [ ] Faire ratifier les breaking changes autorisés et consigner la décision G7.

**Verdict :** documentation de migration prête pour revue, **G7 non ratifié**. Aucune création de tag ou distribution autorisée par ce document.
