# P3-BOOT - Preflight et preparation de P3-G0

> Date : 2026-11-05
> Etat : **PREPARATION / PAS DE DECISION GO**
> Cible : 0.1.0a3 - Inference Primitives
> Baseline M2 : main acd6dfb76d73c260ccca523cf904be44ec249288.
> Enveloppe : documentation et decisions; aucun code d'inference execute.

## Elements prepares dans cette branche

- [x] Plan Phase 3 fourni, archive dans docs.
- [x] PIR Phase 2 fourni, archive comme trace de baseline et dette.
- [x] ADR-014..020 ecrites avec statut PROPOSED; ADR-021 optionnelle egalement redigee.
- [x] Contrat de conception propose et registre d'arbitrages.
- [ ] Revue technique contradictoire du contrat avec les choix et compromis.
- [ ] Acceptation explicite du proprietaire des ADR-014..020; decision ADR-021.
- [ ] Verifier statut des controles CI sur la branche, puis apres integration exacte sur main.
- [ ] Produire un proces-verbal P3-G0 factuel apres adoption et preuve CI main.

## Dette P2 a traiter avec preuves

| Reference | Constat de la PIR M2 | Action pre-G0 ou isolee | Etat |
|---|---|---|---|
| PIR2-01 | Certaines ADR-010..013 conservent le message historique "M2 pending" | Annotation historique indiquant la qualification M2, sans reecrire l'ADR originale | OPEN |
| PIR2-02 | README Domain example contient des litteraux \n dans un import Python | Correction ciblee du bloc et smoke test executable | OPEN |
| PIR2-03 | Signature message_from_dict annonce Mapping mais valide dict uniquement | Choix d'API explicitement arbitre, documentation et test MappingProxyType | OPEN |

Ces dettes n'ont **pas** ete corrigees par la seule production de ce rapport. Elles peuvent etre isolees sur une PR documentaire/technique separee afin de ne pas perturber la baseline M2.

## Périmètre et risques

- Exclus : providers, SDK, HTTP, tokens provider, invocation distante, streaming reel, tools, structured output, cost/pricing, registry, persistence et scheduler.
- A surveiller : main non protegee dans l'audit initial, redaction URI, absence != zero, UID Run/Request distincts, codecs M1/M2 intacts.
- Aucun build a3 n'est revendique, aucune publication PyPI n'est autorisee et aucun M3 GO n'est prononce.

## Check-list GO/NO-GO G0

| Critere | Etat actuel | Preuve a collecter |
|---|---|---|
| Contrat Request / Run / Response clair | PROPOSED | ADR-014 et contrats approuves |
| Target et Config bornes | PROPOSED | ADR-015/016 adoptees |
| Response, Usage et run lifecycle | PROPOSED | ADR-017..019 adoptees |
| Politique JSON v1 et absence de rupture M1/M2 | PROPOSED | ADR-020 adoptee + tests |
| Port/compatibilite effective | OPTIONAL | ADR-021 decidee |
| Dette PIR2-01..03 traitee ou isolee | OPEN | Issue / PR / justification |
| CI exacte sur main apres integration | PENDING | SHA + URL run + conclusion |
| Autorite de decision | PENDING | Decision explicite du proprietaire |

**Verdict de preparation : DOSSIER SOUMETTABLE A REVUE, G0 PENDING.** Ne pas fusionner G0 et M3 et ne pas qualifier sur les resultats de la seule branche.
