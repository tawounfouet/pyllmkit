# ADR-021 - Port d'invocation et compatibilite effective

- Statut : **PROPOSED / OPTIONNEL** (P3-BOOT, 2026-11-05).
- Sources : plan Phase 3 sections 2.2, 3.4 et 4.1; UC-009, FR-017, MOD-002/004, CAP-004/009/011, INF-004.
- G0 : peut etre **DEFERRED** avec justification explicite, sans bloquer les ADR-014..020.

## Contexte

La vision comporte un InferencePort (Protocol), une resolution des capacites et des adapters. Aucune cible concrete ni SDK provider n'est integre au jalon M2. Un faux invoker ne demontre pas l'aptitude a appeler un vrai modele.

## Decision proposee

1. **Ne pas publier d'InferencePort executable dans le P0 de a3.** Documenter seulement son interface structurelle cible afin de ne pas anticiper des choix de transport ni d'erreur native.
2. Contrat futur envisage : invoke(request: InferenceRequest) -> InferenceResponse, implementable par adapter independant. Les adapters ne residant jamais dans domain.inference.
3. La construction d'une Request valide structurellement n'implique **aucune garantie de compatibilite effective**.
4. Une evaluation de compatibilite future s'appuie sur des **snapshots explicites** de capabilities et de limites Model/Deployment/Provider/Endpoint. Sans donnees, resultat NOT_EVALUATED/UNKNOWN, jamais NATIVE implicite.
5. Parametre explicitement non supporte par une cible connue : rejet ou diagnostic explicite; aucun drop silencieux. Les strategies d'emulation ou fallback exigent une policy distincte.
6. ImageContent porte une modalite d'entree, non une preuve de capacite VISION effective.
7. SSRF, secrets, HTTP, retries, quotas, event bus et observabilite fournisseur appartiennent aux futures couches application/adapters.
8. Un fake offline eventuel prouvera uniquement le contrat de typage, pas une invocation reelle.

## Alternatives

- Introduire des maintenant un client LLM ou un adapter OpenAI : rejete, viole la frontiere de a3.
- Publier immediatement un Protocol sans consommateur reel : differe au nom de YAGNI.
- Considerer UNKNOWN comme supported : rejete.

## Critere de decision

Le proprietaire doit choisir ACCEPTED (contrat documente, port reporte) ou REVISED (port structurel optionnel dans a3). Dans les deux cas, toute execution reseau reste hors scope.
