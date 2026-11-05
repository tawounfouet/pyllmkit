# P3-BOOT - Preflight et preparation de P3-G0

**Post-integration evidence (2026-11-05): P3-G0 = GO ARCHITECTURE AVEC RESERVES.** Owner-accepted ADR-014..021 merged via [PR #19](https://github.com/tawounfouet/pyllmkit/pull/19) into `main` SHA [`965311db`](https://github.com/tawounfouet/pyllmkit/commit/965311dbef527ad59222b7586f9c801bb713bead), [CI #42029448967 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42029448967) 3/3 Python jobs. See [P3_G0_GATE_REVIEW.md](P3_G0_GATE_REVIEW.md) for formal gate decision and reservations. The checklist below preserves pre-integration tracking/history; G1/M3 and publication are not authorized by G0.


> Date : 2026-11-05
> Etat : **OWNER ADR ACCEPTED / INTEGRATION AND FINAL G0 CI PENDING**
> Cible : 0.1.0a3 - Inference Primitives
> Baseline M2 : main acd6dfb76d73c260ccca523cf904be44ec249288.
> Enveloppe : documentation et decisions; aucun code d'inference execute.

## Elements prepares dans cette branche

- [x] Plan Phase 3 fourni, archive dans docs.
- [x] PIR Phase 2 fourni, archive comme trace de baseline et dette.
- [x] ADR-014..020 ecrites avec statut PROPOSED; ADR-021 optionnelle egalement redigee.
- [x] Contrat de conception propose et registre d'arbitrages.
- [x] Revue technique contradictoire : recommandations et arbitrages dans P3_G0_ARCHITECTURE_REVIEW.md; validation du proprietaire encore requise.
- [x] Adoption explicite ADR-014..021 par le proprietaire, avec ADR-021 option A et float exact (voir P3_G0_OWNER_ARCHITECTURE_APPROVAL.md).
- [x] CI initiale de PR #19 : run [#42024327072](https://github.com/tawounfouet/pyllmkit/actions/runs/42024327072), SUCCESS sur SHA 4ca6d76584499e59a9f94f5f000e935458381fb6.
- [ ] Requalifier les nouveaux commits de revue et collecter la CI exacte de PR #19 sur sa tete finale.
- [ ] Apres integration eventuelle, qualifier la CI sur le SHA exact de main (pas de merge autorise dans la revue).
- [ ] Produire un proces-verbal P3-G0 factuel apres verification de la CI sur main, avec SHA exact.

## Dette P2 a traiter avec preuves

| Reference | Constat de la PIR M2 | Action pre-G0 ou isolee | Etat |
|---|---|---|---|
| PIR2-01 | Certaines ADR-010..013 conservent le message historique "M2 pending" | Annotation historique indiquant la qualification M2, sans reecrire l'ADR originale | OPEN |
| PIR2-02 | README Domain example contient des litteraux \n dans un import Python | Correction ciblee du bloc et smoke test executable | OPEN |
| PIR2-03 | Signature message_from_dict annonce Mapping mais valide dict uniquement | Choix d'API explicitement arbitre, documentation et test MappingProxyType | OPEN |

Ces dettes n'ont **pas** ete corrigees par la seule production de ce rapport. Leur suivi explicite est materialise par l'[issue #20](https://github.com/tawounfouet/pyllmkit/issues/20). Elles peuvent etre isolees sur une PR documentaire/technique separee afin de ne pas perturber la baseline M2.

## Périmètre et risques

- Exclus : providers, SDK, HTTP, tokens provider, invocation distante, streaming reel, tools, structured output, cost/pricing, registry, persistence et scheduler.
- A surveiller : main non protegee dans l'audit initial, redaction URI, absence != zero, UID Run/Request distincts, codecs M1/M2 intacts.
- Aucun build a3 n'est revendique, aucune publication PyPI n'est autorisee et aucun M3 GO n'est prononce.

## Check-list GO/NO-GO G0

| Critere | Etat actuel | Preuve a collecter |
|---|---|---|
| Contrat Request / Run / Response clair | ACCEPTED DESIGN | ADR-014 et owner decision |
| Target et Config bornes | ACCEPTED DESIGN | ADR-015/016, float exact choisi |
| Response, Usage et run lifecycle | ACCEPTED DESIGN | ADR-017..019 adoptees |
| Politique JSON v1 et absence de rupture M1/M2 | ACCEPTED DESIGN | ADR-020 adoptee, tests de futur lot L3.4 |
| Port/compatibilite effective | OPTION A ACCEPTED | Evaluateur pur AC-007 requis; port public non executable |
| Dette PIR2-01..03 traitee ou isolee | ISOLATED / OPEN | Issue #20; correctifs non appliques |
| CI exacte sur main apres integration | PENDING | SHA + URL run + conclusion |
| Autorite de decision | OWNER ACCEPTED | Decision P3_G0_OWNER_ARCHITECTURE_APPROVAL.md, sans GitHub APPROVED review independante |

**Verdict : adoption de conception acquise, G0 PENDING jusqu'a integration, CI du main SHA exact et PV.** Ne pas fusionner G0 et M3 et ne pas qualifier sur les resultats de la seule branche.
