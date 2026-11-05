# PyLLMKit - P7-G0 Architecture Precheck

- Date: 2026-11-06
- Statut: PRECHECK TECHNIQUE SATISFAIT sur PR HEAD; GO de poursuite demandé le 2026-11-06, sous réserve de CI post-merge et revue humaine indépendante
- Base main: 08a1cd5fc3d7a786e340727b446049c15c000ba7
- Nature: examen des décisions; pas une attestation de CI ni un PV post-merge.

## Artefacts soumis à revue

- ADR-049..ADR-058: dix décisions de frontière, invocation, binding, sécurité, erreurs, mapping, streaming, extras, live et gouvernance.
- docs/architecture/PHASE_7_PROVIDER_ADAPTERS_ARCHITECTURE.md.
- docs/security/P7_PROVIDER_THREAT_MODEL.md.
- Le plan utilisateur P7_PROVIDER_ADAPTERS_IMPLEMENTATION_PLAN.md, statut PROPOSED: 8 lots et P7-AC-001..064 (64 exigences, non exécutées).

## Décisions proposées pour le propriétaire

1. Conserver P7/M7 comme identifiant technique malgré le titre fondateur « 6. Provider Adapters ».
2. Implémenter Ollama en premier, puis OpenAI Responses API, puis Anthropic Messages API; streaming des trois en dernier.
3. Préparer un objet immuable PreparedInvocation et un RunId applicatif, sans changer InferenceRequest ou le JSON v1.
4. AdapterRegistry distinct de ProviderCatalog; aucune connexion ni sélection implicite.
5. Politique egress fail-closed, secrets opaques et SDK optionnels; retries SDK neutralisés si orchestrés par PyLLMKit.
6. Profil initial text-only: unsupported/unknown et sorties natives non reconnues refusés sans perte silencieuse.
7. Exécuter tests live seulement sur opt-in et budget séparé; ne pas traiter une fixture comme preuve live.
8. Version actuelle 0.1.0a2 inchangée, 0.2.0a1..a3 cibles non publiées; release gouvernée séparément.

## Matrice de qualification proposée

| Gate | Lots / livrables | AC proposés | Statut à l'ouverture |
|---|---|---|---|
| G0 | ADR-049..058, architecture, threat model, owner approval | précondition | À examiner |
| G1 | L7.1 ports/lifecycle | 001-008 | Non commencé |
| G2 | L7.2 registry/connexion sécurisée | 009-016 | Non commencé |
| G3 | L7.3 Ollama | 017-024 | Non commencé |
| G4 | L7.4 OpenAI | 025-032 | Non commencé |
| G5 | L7.5 Anthropic | 033-040 | Non commencé |
| G6 | L7.6 streaming trois providers | 041-048 | Non commencé |
| G7 | L7.7 fiabilité, sécurité, observabilité | 049-056 | Non commencé |
| G8 | L7.8 integration, packaging, revue | 057-064 | Non commencé |

## NO-GO si

- ADR manquante/non approuvée, sécurité non signée, extension de domaine/JSON v1 non autorisée.
- Risque d'accès réseau arbitraire ou de fuite secrets non traité.
- Cible ambiguë, alias sans preuve, capability UNKNOWN supposée supportée.
- Aucun plan de tests négatifs, coûts live ou qualification SHA exacte.

## Preuves attendues avant GO G0

- Décision explicite du propriétaire sur la PR, avec arbitrages éventuels enregistrés.
- CI sur HEAD de la PR puis merge autorisé et CI push/main sur le SHA exact.
- PV docs/quality/P7_G0_GATE_REVIEW.md créé sur la base du résultat réel; aucune donnée de CI ni reviewer inventé.
- Aucun SDK ou code d'adapter, aucun appel live dans cette PR.

## Réserves M6 conservées

- #22: protection main non attestée.
- #35: release et version non autorisées.
- #36: frontière provider à consolider.
- Revue humaine indépendante des changements de réseau/sécurité encore requise pour M7; une autorisation du propriétaire ne vaut pas revue indépendante.
