# ADR-059 - Frontiere de conformite multi-provider v0.3.0

- Date : 2026-11-06
- Statut : **ACCEPTED BY OWNER - S0/G0, contrat text-only offline seulement (2026-11-07)**
- Base : `main@8dd97d5e33108c350e11b3a976926f2138f4e936`
- Jalon : `0.3.0` Multi-provider Contract Stabilization
- References : ADR-021, ADR-030..038, ADR-049..058 ; PyLLMKit docs 01/02/03/07/08/09.

## Contexte

La Phase 7 a implemente six adaptateurs texte sync/async et un adaptateur
de streaming natif SSE/NDJSON. Les tests de chaque lot et le smoke test
`test_p7_six_provider_registry.py` prouvent des proprietes locales
mais **pas** une conformite native transversale : le smoke test de registre
utilise les FakeInferenceAdapter.

La garantie recherchee n'est ni une generation identique ni un support
uniforme de toutes les fonctionnalites proprietaires. Elle est une
equivalence des **decisions de contrat** : preconditions, conservation des
champs, sorties, identites, terminaux, erreurs et echec explicite.

## Decision adoptee par le proprietaire pour le profil offline

1. **Ne pas introduire de nouveau Value Object ProviderContract dans le domaine.**
   Reutiliser les Protocols existants et une suite de conformite situee
   dans `tests/conformance/`; les divergences natives restent en adapters.
2. **Profil v1 = chat texte strict**, inference sync/async et streams M5
   quand la semantique est representable. Multi-part, multimodal, outils,
   reasoning prive, schema structuré et etats de sortie natifs non
   representables ne sont jamais aplatis silencieusement.
3. **Parametres et capabilities** : un champ fourni n'est emisse que si
   sa compatibilite effective est prouvee NATIVE; les niveaux UNKNOWN,
   PARTIAL, EMULATED ou UNSUPPORTED ne deviennent jamais NATIVE par defaut.
   Les codecs ont un dernier devoir de verification des noms nativement
   encodables, meme si le snapshot de resolution est positif.
4. **Erreurs publiques** : maintenir `InvocationPortError(code)` et
   `InvocationPreconditionError(code)` ; pas de hierarchy d'exceptions
   additionnelle sans ADR. Ne jamais exposer corps HTTP, headers secrets,
   prompts, tokens d'acces ni repr natif.
5. **Identite et cycle de vie** : conserver un RunId par invocation logique,
   un attempt_id par tentative (une seule tentative dans la baseline) et
   un terminal M5 unique. Aucun retry implicite, failover ou replay.
6. **Parite sync/async** : comparaison des projections canoniques et des
   categories d'erreur, non du timing ni des primitives de cancellation.
   La limite du streaming sync reseau reel demeure un refus explicite.
7. **Provenance et verdict** : matrices par scenario/provider/mode avec
   statut PASS, FAIL, NOT_APPLICABLE, UNSUPPORTED ou BLOCKED, provenance des
   fixtures, SHA, version Python et conditions d'execution. Aucun SKIP opaque.
8. **Gates distincts** : S0-G0 confirme une baseline de travail,
   S1-G1 ratifie le Contract Profile v1, S2-G2 qualifie les fixtures,
   S8-G8 statue sur le code et S9-G9 sur la candidate. Aucun gate
   n'autorise une publication ou un canary payant implicitement.

## Consequences

- Les signatures `InferencePort.invoke`, `AsyncInferencePort.ainvoke`,
  `PreparedStreamingPort.stream_prepared` et
  `AsyncPreparedStreamingPort.astream_prepared` restent inchangees.
- Le contrat M5 (`stream(request)`, `astream(request)`) reste independant
  du transport natif P7 et des objets `PreparedInvocation`.
- Les tests S0 figent les signatures, l'inventaire des fournisseurs et les
  mappings sans ouvrir de reseau.
- S1 formalise les invariants par scenarios; S2 produit les fixtures
  `httpx.MockTransport` pour chaque fournisseur natif.
- Une difference legitime de structure de roles ou d'exigence de tokens
  doit etre indiquee comme condition de support, jamais masquee.

## Alternatives rejetees

- Ajouter un septieme provider avant la qualification des six existants.
- Ecrire un client universel qui transforme silencieusement les roles.
- Considerer une CI verte comme un audit independant ou une preuve TLS live.
- Aligner artificiellement les sorties generees entre modeles.
- Passer automatiquement `pyproject.toml` a `0.3.0` avant G8/G9.

## Qualification de cette decision

S0-G0 : le proprietaire, developpeur et mainteneur unique, a explicitement
accepte la decision de conception pour la baseline text-only offline
le 2026-11-07. La revue par un tiers n'est pas exigee pour ce projet,
sans qu'une telle revue soit presentee comme realisee. Les tests locaux
sont declares par le proprietaire ; la CI GitHub au SHA exact reste la
preuve reproductible du scope hermetique.

Le registre de decision et des exceptions figure dans
[17_OWNER_SELF_ACCEPTANCE_AND_SCOPED_GATES_2026-11-07.md](../milestones/0.3.0/17_OWNER_SELF_ACCEPTANCE_AND_SCOPED_GATES_2026-11-07.md).
Cette acceptation ne certifie pas le reseau live, la production, la
securite egress reelle ni une release 0.3.0. Issue #22 not_planned ;
#36 et #81 conservent les chantiers operationnels distincts.
