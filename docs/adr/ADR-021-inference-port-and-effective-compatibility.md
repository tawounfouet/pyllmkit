# ADR-021 - Port d'inference, capacites et validation conditionnelle

- **Statut : REVISED / PROPOSED / OPTIONAL** - revue P3-G0 2026-11-05. Non adoptee.
- **Sources :** plan Phase 3 sections 2.2, 4, 5.3 et 10; UC-009, FR-017, MOD-002/004, CAP-004/009/011, INF-004.
- **Objet du gate :** decider du report ou de la portee du controle P3-AC-007, sans simuler une invocation provider.

## Contexte

La vision presente InferencePort (Protocol) et un evaluator de compatibilite effective. Mais les entites Serving et adapters operationnels ne sont pas dans a3. La seule presence d'une Request avec ImageContent ou top_p ne prouve ni support du provider ni faisabilite d'appel.

## Decision proposee

1. **Aucun InferencePort executable ou client provider en a3.** Garder un contrat conceptuel futur (invoke(Request) -> Response) dans l'architecture, mais ne pas exporter un Protocol public sans consommateur reel, sauf arbitrage contraire du proprietaire.
2. **Validation structurelle** de GenerationConfig, Target, messages dans le domaine P0. La construction d'une Request valide ne demande aucune resolution de modele, deployment ou endpoint.
3. **Validation effective** : un futur evaluator consomme un snapshot fourni explicitement par l'appelant, identifiant l'origine et les niveaux connus (SUPPORTED, PARTIAL, EMULATED, UNSUPPORTED, UNKNOWN), sans les reduire a un bool implicite. Un champ absent ou une cible non resolue donne UNKNOWN ou NOT_EVALUATED.
4. **P3-AC-007 est conditionnel** : si une evaluation pure sur snapshot explicite est introduite a3, tester qu'un parametre explicitement UNSUPPORTED est diagnostique sans drop silencieux. Si l'evaluator est differe, **marquer P3-AC-007 DEFERRED avec ADR et justification**, et ne pas compter ce cas comme passe dans M3. La matrice d'acceptation doit alors expliciter le nouveau denominateur.
5. **MVP de compatibilite optionnel** : petit evaluator pur sur snapshot statique de support de parametres fourni par le caller. Il ne fait ni discovery, ni capability intersection reelle, ni route, ni HTTP. Aucun statut de support n'est deduit d'une simple ModelId string.
6. ImageContent exprime une modalite d'entree IMAGE; il ne valide pas automatiquement la capability effective VISION.
7. Si une cible effective est connue comme UNSUPPORTED pour un parametre, report typed ou erreur explicite. Les strategies fallback/emulation sont separees et documentees.
8. Les drivers application, adapters HTTP, keys, retry, SSRF, quotas, billing et streaming reel sont hors scope. Un fake offline ne prouve que le contrat de types et le comportement de validation choisi.

## Alternatives

- Introduire un client OpenAI pour tester l'inference : refuse.
- Publier un Protocol public sans adapter ni use case reel : reporte au nom de YAGNI, sauf decision G0.
- Faire croire que des capabilities manquantes signifient NATIVE : refuse.
- Declarer 30/30 cas d'acceptation reussis avec P3-AC-007 non implemente : refuse.

## Decision requise en G0

- **Option A conseillee** : accepter la specification d'un evaluator pur minimal sur snapshot connu pour satisfaire P3-AC-007, sans InferencePort.
- **Option B** : differer l'evaluator et P3-AC-007, inscrire le report dans la matrice G0 et M3, sans invoquer un 30/30 fictif.

Aucune de ces options n'est adoptee dans ce fichier. L'autorite doit trancher avant code public.
