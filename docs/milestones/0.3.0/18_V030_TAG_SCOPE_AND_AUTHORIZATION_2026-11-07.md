# PyLLMKit - v0.3.0 : périmètre du tag et décision G9

> Date : 2026-11-07
> AUTHORIZATION: GIT_TAG_v0.3.0_ONLY
> Autorité : propriétaire, développeur et mainteneur unique du dépôt.
> Décision : le propriétaire a explicitement demandé « vas-y faire le nécessaire pour tagguer à : v0.3.0 ».

## 1. Nature de cette livraison

Le tag Git `v0.3.0` est autorisé **sur le SHA exact de `main` contenant `pyproject.toml = 0.3.0`**, uniquement après la réussite des trois jobs Python de la CI du nouveau SHA.

Ce tag atteste un jalon de code source **text-only offline** et l'acceptation par le propriétaire des exceptions. Il ne revendique pas une disponibilité réelle, une homologation de sécurité des endpoints cloud ou une production provider-live prête à l'emploi.

La publication séparée d'une GitHub Release et de paquets TestPyPI/PyPI **n'est pas demandée ni autorisée** par cette décision. Aucun trafic LLM payant n'est nécessaire pour qualifier ce tag.

## 2. Gates G9 du tag

- [x] Le propriétaire approuve le tag exact `v0.3.0`.
- [x] La revue tierce et les rulesets obligatoires de `main` ont été dispensés par choix explicite du mainteneur (#105, #22 classés not_planned).
- [x] Les contrats `text_only_v1` et ADR-059 ont été approuvés par le propriétaire pour leur périmètre offline (document #17).
- [x] Le code antérieur à la release est intégré et qualifié en CI 3/3 au SHA `fb7c13df384ffebfd77931c3bf02a46ad2002e6c`, workflow [#42323610720](https://github.com/tawounfouet/pyllmkit/actions/runs/42323610720).
- [ ] Version `0.3.0`, changelog, README et contrôles de métadonnées sur une PR fusionnée.
- [ ] CI **du commit de release sur main** passée sur 3.11/3.12/3.13, incluant 752 scénarios offline, wheel/sdist, installations isolées et métadonnées.
- [ ] Tag `refs/tags/v0.3.0` réellement créé et vérifié comme pointant sur le SHA de release.
- [ ] Le SHA et les preuves CI finales sont enregistrés dans #103, sans supposer de revue externe.

## 3. Risques et exceptions explicitement acceptés

- Les scénarios de conformité sont synthétiques (`httpx.MockTransport` ou fakes), pas des canaris des fournisseurs.
- DNS, IP effective, TLS, rebinding SSRF et limites de coûts des appels fournisseurs live restent non qualifiés (#36, #81).
- Les capacités NATIVE et les refus d'opérations non supportées sont conservés strictement ; aucune conversion silencieuse n'est garantie possible.
- `Usage` incomplet et `FinishReason.UNKNOWN` ne sont jamais reconstruits comme des faits.
- Le catalogue et ses prix locaux n'apportent aucune garantie en temps réel.
- Les releases de code pré-1.0 peuvent modifier les APIs ; la migration des consommateurs doit être évaluée.
- Aucun écrasement/force-update de tag n'est autorisé. S'il existe déjà, l'opération de tagging doit confirmer son SHA ou échouer sans modification.

## 4. Exécution technique du tag

Le workflow `.github/workflows/tag-v0.3.0.yml` est limité à **ce tag précis**. Il ne doit s'activer que lorsque la CI `CI` déclenchée par `push` sur `main` se termine en SUCCESS, en vérifiant le SHA de la CI, le HEAD actuel de `main`, les trois jobs `validate (3.11/3.12/3.13)`, les artefacts de conformité, la version `0.3.0`, ce document d'autorisation et les notes du changelog. Il crée un tag Git **annoté, non forcé et non mutable** si le tag n'existe pas.

Ce workflow a temporairement besoin de `contents: write` et n'envoie aucun artefact sur PyPI. Après la vérification de la création du tag, il peut être retiré dans une PR de nettoyage distincte.

## 5. Décision distincte de distribution

- Git tag `v0.3.0` : **OWNER GO (sous réserve de CI exacte et des préconditions du workflow)**.
- GitHub Release : **NOT REQUESTED**.
- TestPyPI / PyPI : **NOT REQUESTED**.
- Provider-live / production : **NOT QUALIFIED**.
