# PyLLMKit v0.3.0 - Bilan post-implémentation

> **Date :** 7 novembre 2026  
> **Projet :** PyLLMKit  
> **Type :** Post-Implementation Review (PIR), rétrospective technique et produit  
> **Périmètre :** jalon `v0.3.0`, de la stabilisation multi-provider à la création du tag Git, avec suivi documentaire post-tag  
> **Statut :** **GO pour le code source et les contrats textuels qualifiés hors ligne ; NO-GO pour les garanties provider-live / production ; distribution PyPI non réalisée**  
> **Gouvernance :** approbation par le développeur et mainteneur unique ; ce document n'est pas une revue indépendante ni une attestation de tests live.

## 1. Synthèse exécutive

Le jalon `v0.3.0` a concrétisé la vision d'une bibliothèque Python agnostique des fournisseurs de LLM : un domaine typé indépendant du réseau, six adaptateurs natifs textuels, une interface CLI optionnelle, des contrats de streaming, des mécanismes de découverte, ainsi qu'un premier suivi local de l'usage et des coûts.

**Résultat vérifié :** le tag Git annoté [`v0.3.0`](https://github.com/tawounfouet/pyllmkit/tree/v0.3.0) existe et pointe vers le commit de release `1e98d1a8184303c2a18caa14a819099a9be169cf`. Sur ce SHA, [la CI #42324863963](https://github.com/tawounfouet/pyllmkit/actions/runs/42324863963) a conclu **SUCCESS** sur Python 3.11, 3.12 et 3.13 : **2 827 tests pytest PASS par version**, **752 scénarios de conformité hors ligne PASS par version**, et contrôleur S8 indépendant des minima lui aussi PASS. Ruff, mypy, wheel/sdist et contrôles d'installation propre figurent dans la même chaîne CI.

**Ce que cette réussite ne prouve pas :** compatibilité réelle garantie avec tous les endpoints distants, sécurité egress DNS/peer-IP/TLS/SSRF en conditions de production, budgets de facturation effectivement appliqués aux fournisseurs, interruption distante des inférences, ou qualification universelle du multimodal et du tool calling natif.

Le choix du mainteneur unique de dispenser les protections obligatoires de `main` et la revue par un tiers a été enregistré : ces contrôles sont **non requis pour ce projet**, et non artificiellement déclarés réalisés.

### Tableau de décision

| Dimension | Verdict au 07/11/2026 | Motif |
|---|---|---|
| Architecture domaine / ports / adaptateurs | **GO offline** | Contrats implémentés, frontières inspectées et tests exécutés |
| Six adaptateurs textuels et parité sur scénarios connus | **GO offline avec réserves** | Conformité synthétique ; incompatibilités non représentables refusées |
| Streaming, cycle de vie et annulation locale | **GO offline avec réserves** | Limites réseau et hard deadline sync préservées |
| CLI, catalogue, SQLite, FinOps | **GO source avec limites** | Parcours local intégré, consentement et inconnues documentés |
| Version `0.3.0` et tag Git | **GO - réalisé et vérifié** | SHA, CI exacte et objet tag annoté contrôlés |
| GitHub Release / TestPyPI / PyPI | **Non exécuté** | Canaux distincts, non demandés |
| Egress live, canaris et production | **NO-GO** | Preuves opérationnelles manquantes (#36, #81) |

## 2. Références exactes et état du dépôt

| Référence | Valeur / preuve |
|---|---|
| Dépôt | [`tawounfouet/pyllmkit`](https://github.com/tawounfouet/pyllmkit) |
| Tag officiel | [`refs/tags/v0.3.0`](https://github.com/tawounfouet/pyllmkit/tree/v0.3.0) |
| Objet Git annoté | `949a096e450b2106183b7ffe8bb4421d4822f1d4` |
| Commit **tagué** | `1e98d1a8184303c2a18caa14a819099a9be169cf` |
| CI du commit tagué | [#42324863963 - SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42324863963) |
| Workflow de création du tag | [#42324994012 - SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42324994012) |
| PR de release | [#107 - fusionnée](https://github.com/tawounfouet/pyllmkit/pull/107) |
| PR de nettoyage du workflow temporaire | [#108 - fusionnée](https://github.com/tawounfouet/pyllmkit/pull/108) |
| README simplifié après le tag | [#109 - fusionnée](https://github.com/tawounfouet/pyllmkit/pull/109) |
| `main` au moment du PIR | `fd2f5b19de3a837f417f3f17235871dba6bc8d86` |
| CI du `main` post-README | [#42325835613 - SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42325835613) |
| Version de `pyproject.toml` sur `main` | `0.3.0` |
| PR ouvertes à la vérification | **0** |

**Distinction importante :** le tag `v0.3.0` fige le code au SHA `1e98d1a...`. Les modifications ultérieures sur `main`, notamment le README raccourci à **74 lignes** contre **306**, n'appartiennent pas rétroactivement au contenu du tag. Aucun déplacement du tag n'a été effectué.

## 3. Objectif initial et périmètre réellement livré

### 3.1 Objectif du jalon

Le jalon de la roadmap initiale, `0.3.0 - Multi-provider Contract Stabilization`, vise à stabiliser les contrats partagés entre fournisseurs hétérogènes, les modèles et leurs déploiements, les capacités et limites effectives, les API sync/async/streaming, la taxonomie d'erreurs et une compatibilité observable et testable.

Le produit n'a pas vocation à absorber le runtime agentique, l'exécution métier des tools, le moteur RAG complet, le routage automatique global ou un proxy LLM d'entreprise. Les responsabilités de ces systèmes restent séparées du cœur PyLLMKit.

### 3.2 Capacités implémentées et périmètre démontré

| Domaine | Réalisations observables | Qualification / limite |
|---|---|---|
| **Model Domain** | Modèles, identités, artefacts, modalités, capacités, contraintes, limites, codecs JSON | Cœur sans dépendances HTTP imposées |
| **Interactions** | `Role`, `Message`, `Content`, éléments textuels et références multimédias descriptives | La présence d'objets multimédias n'implique pas un support d'inférence multimodale provider |
| **Inference** | `InferenceRequest`, `InferenceResponse`, `InferenceRun`, états de run, `Usage`, `FinishReason` | Données inconnues / partielles conservées, pas de total de tokens inventé |
| **Tooling & Structured Output** | Définition d'outils, appels/résultats descriptifs, validation, sérialisation | Pas d'exécution automatique des fonctions métier |
| **Streaming** | Événements typés, ordre, terminaux, EOF, annulation locale, projection | Transport simulé et refus explicites pour les garanties sync live impossibles à tenir |
| **Registry & Discovery** | Providers/deployments descriptifs, recherche, résolution déterministe, provenance et conflits | La présence au catalogue ne vaut pas disponibilité distante |
| **Provider adapters** | Encodeurs/décodeurs et adaptateurs natifs textuels sync/async pour six fournisseurs | Scénarios de fixtures et HTTP mock, pas de certification live |
| **CLI** | Typer/Rich, `models`, `run`, `stream`, inspection, gestion d'historique | Mode mock par défaut ; `--live` explicitement requis pour le réseau |
| **SQLite & FinOps** | Historique local, métadonnées par défaut, estimation de coûts, export et purge logique | Prix indicatifs ; pas de garantie d'effacement forensique SQLite ni de facturation exacte |

### 3.3 Six fournisseurs natifs

| Fournisseur | API / protocole testé dans les fixtures | Particularité |
|---|---|---|
| OpenAI | Responses API / SSE | Mappage de paramètres natifs et rôles stricts |
| Anthropic | Messages API / SSE | Contraintes d'alternance des rôles et de tokens de sortie |
| Google Gemini | `generateContent` / SSE | Mappage spécifique des paramètres et contenus |
| xAI | Responses API / SSE | Contrats et erreurs natifs dédiés |
| Mistral | Chat Completions / SSE | Conversion contrôlée des paramètres et rôles |
| Ollama | `/api/chat` / NDJSON | Runtime local, avec autorisation réseau explicite |

Les **131 entrées du catalogue réparties en 15 catégories** signalées dans le changelog ne sont **pas 131 modèles testés live**, ni 15 adaptateurs exécutables. Le périmètre natif qualifié est limité aux six fournisseurs cités et aux scénarios `text_only_v1` effectivement couverts.

## 4. Architecture finale et décisions de conception

```text
Applications Python / CLI / futurs consommateurs Py*Kit
                       |
                Facade et services
                       |
         Ports / Protocols d'inférence
                       |
    +------------------+------------------+
    |                                     |
Domain Core                     Adaptateurs / anti-corruption
(provider-agnostic)             |-- Six providers natifs
    |                           |-- HTTP et streaming SSE/NDJSON
    |                           |-- Registry / Discovery
    +-- Model / Capability      |-- SQLite / History / CLI
    +-- Request / Run / Response
    +-- Tools / Structured Output
    +-- StreamEvent / Usage
```

Les principes qui ont tenu le jalon sont :

1. **Domain First / DDD :** les identités et invariants (`Model`, `Deployment`, `InferenceRun`, `ToolCall`, `Usage`) sont explicites.
2. **Ports & Adapters / DIP :** `domain` ne dépend ni des clés de fournisseur, ni de HTTPX, ni des SDK d'inférence.
3. **Anti-Corruption Layer :** chaque fournisseur conserve son mapping propre sans imposer sa forme native au domaine.
4. **Capability-driven :** support `NATIVE`, `PARTIAL`, `EMULATED`, `UNSUPPORTED`, `UNKNOWN` non aplati ; les incompatibilités connues ou non justifiées échouent explicitement.
5. **CQRS limité et traçabilité :** distinguer commandes d'inférence, consultation catalogue/historique, identité de run et tentative de transport ; aucun retry ou fallback implicite n'est revendiqué.
6. **Sûreté par défaut :** aucun appel live sans accord explicite, aucun prix inconnu transformé en coût nul et aucun `FinishReason.UNKNOWN` transformé en `STOP`.

La [décision ADR-059](../../adr/ADR-059-multi-provider-conformance-boundary.md) et le [profil `text_only_v1`](01_MULTI_PROVIDER_CONTRACT_V1.md) ont été **ratifiés par le mainteneur pour le périmètre offline**, selon le [registre propriétaire #17](17_OWNER_SELF_ACCEPTANCE_AND_SCOPED_GATES_2026-11-07.md).

## 5. Rétrospective de livraison S0 à S9

| Lot | Résultat post-implémentation | Statut / réserve |
|---|---|---|
| **S0 - Audit et baseline** | Cartographie du noyau, 6 adaptateurs, invariants C-01..C-15, ADR-059 | Accepté owner offline |
| **S1 - Contrat natif textuel** | `text_only_v1`, contraintes de rôles/paramètres, refus des capacités non natives | Accepté owner offline |
| **S2 - Harness multi-provider** | Tests cross-provider, sync/async, HTTP et streaming simulés | 752 scénarios cumulés, non exhaustifs des plateformes réelles |
| **S3 - Erreurs et JSON strict** | Taxonomie courte, sanitization, parsing strict, absence de payload fournisseur brut dans le domaine | Audit transversal de toutes les traces/logs encore à renforcer |
| **S4 - Paramètres et sorties** | Config de génération, `Usage`, `FinishReason`, alias et historique de messages | Couverture exhaustive RunId/attempt/alias non démontrée |
| **S5 - Streaming** | SSE/NDJSON, terminaux et fermeture locale, comportements fail-closed | Hard deadline sync live non établi |
| **S6 - Egress et resilience** | Préflight offline, destinations configurées, no-live par défaut, échecs sûrs | **NO-GO** DNS/IP/TLS/SSRF et budgets en conditions live |
| **S7 - API et exemples** | API publique, démonstrations provider-free, installation propre, migration proposée | Comparaison complète d'API consommateur à finaliser |
| **S8 - Intégration / preuves** | Matrice 27 familles / 752 scénarios, validateur S8, CI multi-Python, artefacts | **GO offline**, pas un test fournisseur réel |
| **S9 - Version / tagging** | `0.3.0`, changelog, tests de packaging, CI sur SHA versionné, tag annoté et nettoyage | **GO pour tag Git seulement** ; aucune distribution PyPI |

### Séquence notable des PR

- **#82, #88 à #98 :** construction et intégration du jalon de conformité S0-S8.
- **#99, #100, #101, #102 :** clôture documentaire, CLI et durcissement des valeurs inconnues, historique et confidentialité.
- **#104, #106 :** dossier de contrats, acceptation explicite du mainteneur unique et registre des exceptions.
- **#107 :** version `0.3.0`, notes et création du tag conditionnée à la CI exacte.
- **#108 :** retrait du workflow temporaire doté de `contents: write` après la création vérifiée du tag.
- **#109 :** simplification du README et maintien des tests via des exemples autonomes, sur `main` après le tag.

Pour la granularité des lots et preuves initiales : [S8](11_S8_INTEGRATED_QUALIFICATION_GO_NO_GO.md), [intégration sur main](12_S8_SOURCE_INTEGRATION_AND_MAIN_QUALIFICATION.md), [audit S0-S9](14_S0_S9_FUNCTIONAL_CLOSURE_AUDIT_2026-11-06.md) et [dossier de contrats](15_CONTRACT_CONFORMANCE_AND_INDEPENDENT_REVIEW_DOSSIER_2026-11-07.md).

## 6. Qualification : chiffres, méthodes et limites

### 6.1 Résultats vérifiés sur le commit tagué

| Contrôle | Python 3.11 | Python 3.12 | Python 3.13 |
|---|---:|---:|---:|
| CI `validate` | **SUCCESS** | **SUCCESS** | **SUCCESS** |
| Suite pytest principale | **2 827 PASS** | **2 827 PASS** | **2 827 PASS** |
| Conformité six fournisseurs offline | **752 PASS** | **752 PASS** | **752 PASS** |
| Validateur d'intégrité S8 | **PASS (752)** | **PASS (752)** | **PASS (752)** |
| Ruff / mypy | **PASS** | **PASS** | **PASS** |
| Build et smokes wheel/sdist | **PASS** | **PASS** | **PASS** |

**Source exacte :** [workflow #42324863963](https://github.com/tawounfouet/pyllmkit/actions/runs/42324863963), commit `1e98d1a8184303c2a18caa14a819099a9be169cf`, journaux des trois jobs. Les chiffres de pytest sont **par version Python** : on ne les additionne pas pour annoncer 8 481 tests distincts. Les 752 cas sont des scénarios de conformité exécutés séparément, mais peuvent partager certaines assertions et chemins de code avec les tests pytest.

**Qualification post-tag :** le README a été raccourci dans [PR #109](https://github.com/tawounfouet/pyllmkit/pull/109) ; la [CI post-merge #42325835613](https://github.com/tawounfouet/pyllmkit/actions/runs/42325835613) est également **SUCCESS 3/3**, avec 2 827 pytest et 752 scénarios par version sur `main@fd2f5b19...`.

### 6.2 Écart de métrologie observé dans la CI

Les journaux du **sous-test ciblé Gemini + cloud HTTP** sur le commit tagué et sur le `main` post-README indiquent :

- commande visant `--cov-fail-under=95` ;
- `72 passed` ;
- **couverture combinée exacte `94.97%`** ;
- sortie pytest-cov : `FAIL Required test coverage of 95% not reached` ;
- pourtant, le **step GitHub Actions correspondant porte `conclusion=success`**, et le job global est vert.

**Interprétation :** les tests fonctionnels du sous-ensemble réussissent, mais un signal de couverture ne respecte pas le seuil annoncé. La cause de la discordance entre la sortie textuelle et la conclusion du step n'a pas été établie dans ce PIR. Il serait incorrect de conclure que **tous** les seuils ciblés atteignent 95 % au seul motif de la CI verte.

**Action PIR-01 (P1) :** reproduire isolément cette commande, inspecter le code de sortie du processus et la politique CI, combler les branches manquantes de `cloud_http.py` / `google_gemini_mapping.py` ou ajuster explicitement, avec justification, le seuil concerné. Ajouter un test de non-régression qui vérifie la propagation de l'échec de couverture. **Ne pas réécrire a posteriori le statut CI historique.**

### 6.3 Ce que la qualification ne couvre pas

- Aucun canari fournisseur live n'a été observé dans les preuves du jalon ; aucune connexion réelle, latence, facturation ni changement d'API provider n'est certifié.
- La provenance d'une fixture ne prouve pas que le comportement fournisseur réel est identique au moment de l'exécution.
- Les campagnes adversariales DNS/peer-IP/TLS, SSRF/rebinding et proxy/redirect restent distinctes des tests MockTransport.
- L'effacement logique SQLite ne garantit pas la purge des WAL, pages libérées, copies et exports préexistants.
- L'acceptation du mainteneur unique vaut décision de gouvernance et acceptation des risques, **pas preuve d'une revue externe**.

## 7. Qualité de la livraison, problèmes résolus et difficultés

### Points réussis

1. **Chaîne de preuves reproductibles.** Chaque évolution est liée à une PR, un SHA et une CI ; le tag a été créé uniquement après contrôle du SHA versionné.
2. **Tests synthétiques de grande ampleur.** Un référentiel de 27 familles et 752 scénarios, contrôlé par un second validateur, réduit les divergences silencieuses entre six APIs hétérogènes.
3. **Refus plutôt que falsification des données.** Les prix, capacités et champs partiels absents restent inconnus au lieu de valeurs inventées.
4. **Séparation domain/adapters.** Le noyau reste indépendant du protocole, utile pour réutilisation dans une CLI, une application web ou un runtime agentique.
5. **Hygiène post-release.** Le workflow temporaire de tag a été retiré ; le tag annoté n'a pas été déplacé ; le README a été réduit de 306 à 74 lignes.

### Frictions constatées

1. **Métadonnées figées dans des tests anciens.** Le bump `0.1.0a2` -> `0.3.0` a d'abord échoué sur des assertions historiques et une commande de smoke wheel ; elles ont été corrigées avant le tag.
2. **Documentation stratifiée.** Le `ROADMAP.md` historique et plusieurs dossiers anciens décrivent encore la version `0.1.0a2`, des étapes dépassées et des statuts NO-GO qui avaient du sens à leur date. Le README présentait le même problème avant #109.
3. **Nombreux contrôles formels pour un mainteneur unique.** Le propriétaire a volontairement levé deux règles de procédure (protection de main et reviewer tiers) tout en conservant CI et traçabilité ; les risques procéduraux doivent rester connus.
4. **Écart entre sécurité simulée et exploitation réelle.** Le jalon qualifie une interface de développement, pas encore un service réseau sécurisé de production.
5. **Signal de couverture ambigu.** Un sous-test affiche `94.97%` sous un seuil de `95%` alors que le step est déclaré réussi : voir PIR-01.

## 8. Registre des décisions et des écarts résiduels

| ID | Sujet | Gravité / priorité | Situation et décision |
|---|---|---|---|
| **PIR-01** | Sous-test Gemini/cloud HTTP : couverture `94.97%` / seuil `95%`, step vert | **P1 - qualité** | Reproduire et corriger l'incohérence de seuil/exit code |
| **PIR-02** | Egress DNS, IP connectée, TLS, SSRF/rebinding, redirects/proxies | **P0 avant live** | Continuer [#36](https://github.com/tawounfouet/pyllmkit/issues/36) et [#81](https://github.com/tawounfouet/pyllmkit/issues/81) ; aucun GO provider-live |
| **PIR-03** | Token/cost/rate budgets et canaris opt-in | **P0 avant live** | Politique de dépenses, allowlist, limites et procédures de canari à prouver |
| **PIR-04** | Streaming synchrone réel, deadline hard-stop | **P0 pour ce mode** | Conserver fail-closed jusqu'à garantie vérifiable ; ne pas promettre arrêt côté provider |
| **PIR-05** | Matrice exhaustive non exécutés et exceptions N/A/UNSUPPORTED/BLOCKED | **P1** | Compléter le registre, ne pas extrapoler depuis les 752 cas PASS |
| **PIR-06** | Révision API, contrat de migration, clients consommateurs | **P1 avant distribution large** | Comparer les signatures et essayer une application réelle |
| **PIR-07** | `ROADMAP.md` et issues historiques datées | **P1 - pilotage** | Actualiser le statut `v0.3.0` ; distinguer archives et roadmap future |
| **PIR-08** | Publication wheel/sdist sur TestPyPI/PyPI, provenance et installation externe | **P2 - décision séparée** | Aucun upload ; préparer un protocole de publication si demandé |
| **PIR-09** | Confidentialité du stockage SQLite et purge forensique | **P2 / sécurité données** | Politique de rétention, WAL/backups/exports et limites de purge explicites |
| **PIR-10** | Protection `main` et revue tierce | **Risque accepté par owner** | Issues #22 et #105 fermées `not_planned` ; ne pas les présenter comme contrôles actifs |

**Issues ouvertes à la vérification :** [#36](https://github.com/tawounfouet/pyllmkit/issues/36), [#81](https://github.com/tawounfouet/pyllmkit/issues/81), [#103](https://github.com/tawounfouet/pyllmkit/issues/103) et [#35](https://github.com/tawounfouet/pyllmkit/issues/35). L'issue #103 contient des en-têtes historiques encore au statut G9 pending, mais ses commentaires postérieurs attestent la création du tag. L'issue #35 concerne un ancien candidat `0.1.0a3` et doit être reclassée ou clôturée sans confondre l'autorisation de PyPI avec le tag Git livré.

## 9. Feuille de route recommandée après v0.3.0

### 9.1 Prochain incrément : stabilisation opérationnelle P7-L7.8

**Objectif :** passer de « six adaptateurs conformes sur fixtures » à « chemins réseau autorisables sous conditions contrôlées ».

- [ ] Spécifier la frontière de sécurité réseau (DNS résolu, pair réellement connecté, IP privée/loopback, TLS, redirections et proxies).
- [ ] Définir un budget explicite par appel et par provider : tokens, coût maximum estimé, requêtes, temps et autorisation.
- [ ] Tester cancellation, fermeture de sockets, deadline totale, limites de payload et erreurs natives sans fuite de données.
- [ ] Démarrer par un **canari Ollama local**, puis un cloud à faible budget, **uniquement après validation de sécurité et autorisation spécifique**.
- [ ] Produire des preuves indépendantes pour tests hermétiques, tests intégration réseau local et tests provider cloud réel.

### 9.2 Prochain incrément produit : consumer-driven validation

Construire **une petite application Python consommatrice** qui effectue réellement les opérations `DISCOVER -> RESOLVE -> INVOKE -> OBSERVE`, en utilisant l'API publique plutôt que des chemins internes. Mesurer les irritants d'import, la configuration, les capacités et paramètres, la gestion d'erreurs, la persistance, les coûts et la testabilité.

Les extensions `0.4.x+` du [ROADMAP.md](../../../ROADMAP.md) doivent être **rebaselinées** : registry/discovery, streaming et FinOps ont déjà une partie des fonctionnalités historiquement planifiées. La décision d'ajouter un `TokenizerPort`, davantage de multimodal, de nouveaux providers ou des intégrations PyAgentsKit/PyRuntimeKit doit reposer sur les gaps du consommateur et non sur la seule numérotation initiale.

### 9.3 Distribution et documentation

- [ ] Réécrire l'en-tête de `ROADMAP.md` en état courant après le tag, avec backlog unique et liens vers les issues actives.
- [ ] Séparer le `CHANGELOG.md` publié en tête de ses archives historiques, sans falsifier les jalons antérieurs.
- [ ] Synchroniser l'issue #103 avec **G9 Git tag = DONE**, et réserver une issue séparée pour TestPyPI/PyPI si la distribution est décidée.
- [ ] Formaliser matrice de compatibilité et notes de migration pour les consommateurs.
- [ ] Garder le README concis ; placer les preuves, contrats et matrices dans `docs/`.

## 10. Actions proposées, responsables et critères de sortie

| Ordre | Action | Responsable | Critère de sortie vérifiable |
|---|---|---|---|
| 1 | Qualifier l'écart de couverture Gemini/HTTP (PIR-01) | Mainteneur / tests CI | Résultat du seuil cohérent avec le statut du step ; preuve sur SHA exact |
| 2 | Actualiser la roadmap post-`v0.3.0` | Mainteneur | `ROADMAP.md` courant, anciens jalons archivés, priorités explicites |
| 3 | Concevoir/implémenter P7-L7.8 (PIR-02..04) | Mainteneur | Tests adversariaux réseau, budgets et hard-deadlines séparés des mocks |
| 4 | Tester une app consommatrice PyLLMKit | Mainteneur | Parcours `DISCOVER -> RESOLVE -> INVOKE -> OBSERVE` démontré sans imports privés |
| 5 | Décider de la prochaine version et du canal de distribution | Mainteneur | Autorisation distincte et preuves d'artefact, sans publication tacite |

## 11. Décision post-implémentation

**GO - JALON SOURCE `v0.3.0` CLOTURÉ.** Le code source a été intégré, les contrats offline ont été acceptés par le propriétaire, les tests et artefacts d'intégration ont passé la CI, et le tag annoté a été créé sur le bon commit. Le suivi documentaire du README a également été validé après le tag.

**NO-GO - GARANTIES LIVE / PRODUCTION.** La qualification des scénarios MockTransport ne remplace ni des tests egress réels ni une politique opérationnelle de coûts et de sécurité. Le streaming sync réel sans garantie de deadline reste explicitement limité.

**NON REALISÉ - PUBLICATION PyPI / GitHub Release.** Le tag Git constitue le seul canal de livraison demandé et exécuté pour le jalon.

**Recommandation de continuation :** ne pas empiler de nouvelles couches de framework avant d'avoir corrigé l'écart de métrologie PIR-01, mis à jour le pilotage et exercé l'API dans une application réelle. Construire le chantier opérationnel P7-L7.8 en parallèle de cet essai consommateur.

---

## 12. Sources de référence et traçabilité

- [ROADMAP.md](../../../ROADMAP.md) et [CHANGELOG.md](../../../CHANGELOG.md) - trajectoire historique et notes de version.
- [ADR-059](../../adr/ADR-059-multi-provider-conformance-boundary.md) et [01 - Contrat text_only_v1](01_MULTI_PROVIDER_CONTRACT_V1.md) - contrat principal.
- [11 - S8 Integrated Qualification](11_S8_INTEGRATED_QUALIFICATION_GO_NO_GO.md), [12 - Source Integration](12_S8_SOURCE_INTEGRATION_AND_MAIN_QUALIFICATION.md) et [14 - Audit S0-S9](14_S0_S9_FUNCTIONAL_CLOSURE_AUDIT_2026-11-06.md) - preuves et écarts historiques.
- [15 - Dossier conformité](15_CONTRACT_CONFORMANCE_AND_INDEPENDENT_REVIEW_DOSSIER_2026-11-07.md), [16 - Migration](16_COMPATIBILITY_AND_MIGRATION_PROPOSAL_2026-11-07.md), [17 - Acceptation propriétaire](17_OWNER_SELF_ACCEPTANCE_AND_SCOPED_GATES_2026-11-07.md), [18 - Tag](18_V030_TAG_SCOPE_AND_AUTHORIZATION_2026-11-07.md).
- [PR #107](https://github.com/tawounfouet/pyllmkit/pull/107), [#108](https://github.com/tawounfouet/pyllmkit/pull/108), [#109](https://github.com/tawounfouet/pyllmkit/pull/109) - version, tagging, nettoyage et README.
- [CI tag #42324863963](https://github.com/tawounfouet/pyllmkit/actions/runs/42324863963), [tag workflow #42324994012](https://github.com/tawounfouet/pyllmkit/actions/runs/42324994012), [CI main post-README #42325835613](https://github.com/tawounfouet/pyllmkit/actions/runs/42325835613).
- [Issues #36](https://github.com/tawounfouet/pyllmkit/issues/36), [#81](https://github.com/tawounfouet/pyllmkit/issues/81), [#103](https://github.com/tawounfouet/pyllmkit/issues/103), [#35](https://github.com/tawounfouet/pyllmkit/issues/35) - reliquats en suivi.

> **Portée de l'analyse :** les éléments décrits comme « vérifiés » correspondent aux fichiers, aux références Git et aux journaux GitHub consultés. Les analyses de causes, recommandations et priorisations sont des conclusions du présent PIR et ne sont pas des faits attestés par des essais live.