# PyLLMKit v0.3.0 - Dossier de revue des contrats et de ratification S0-S8

> Date : 2026-11-07  
> Statut : **DOSSIER DE PRÉ-REVUE TECHNIQUE, RATIFICATION INDÉPENDANTE EN ATTENTE**  
> SHA exact examiné : `b4f91e1dd05ba2e44134c0209fcc3c72f5259f8c`  
> Objet : qualification du socle **text-only offline**, pas validation de trafic provider live, production, version bump, tag ou distribution.  
> Auteur / préparation : assistant technique contributeur aux PR antérieures. **Pas une revue humaine indépendante.**

## 1. Décision de périmètre et exception owner

Le propriétaire a explicitement décidé le 2026-11-07 de **ne pas rendre obligatoire la protection GitHub de `main`** pour PyLLMKit. L'issue [#22](https://github.com/tawounfouet/pyllmkit/issues/22) est clôturée **not_planned** en conséquence.

- Cette exception est une **acceptation du risque résiduel**, pas une preuve que le risque est supprimé : pushes directs, force-pushes, merge sans review ou contrôles CI non imposés peuvent rester possibles.
- Le contrôle manuel d'un **SHA exact**, les résultats réels de CI et la traçabilité des PR restent requis dans la procédure choisie.
- L'exception ne vaut **ni ratification de ADR-059**, ni revue API/sécurité indépendante, ni autorisation live, ni GO release.
- Elle ne modifie pas rétroactivement l'audit historique 00-14, qui décrit les exigences alors en vigueur.

## 2. Preuves CI reproductibles, source exacte

- [CI main #42321595995](https://github.com/tawounfouet/pyllmkit/actions/runs/42321595995) : **SUCCESS** sur Python 3.11, 3.12, 3.13 au SHA exact indiqué en en-tête.
- **2 825 tests pytest réussis par version Python**, lint Ruff et mypy strict réussis.
- **752 cas de conformité offline PASS par version** ; le validateur S8 distinct accepte la même matrice.
- Trois artefacts `v030-conformance-3.11`, `v030-conformance-3.12`, `v030-conformance-3.13`, issus de la CI exacte.
- Wheel/sdist et smoketests clean-environment exécutés dans la CI.
- [PR #99](https://github.com/tawounfouet/pyllmkit/pull/99) et [PR #102](https://github.com/tawounfouet/pyllmkit/pull/102) fusionnées. PR #102 couvre valeurs inconnues du catalogue, consentement supplémentaire `--allow-content-export` et purge logique des contenus SQLite.
- Les 752 cas sont **des scénarios de fixtures synthétiques**, non des probes live. **2 825 n'est pas un nombre de provider-live tests.**
- Sources des assertions : [reporter S2-S7](https://github.com/tawounfouet/pyllmkit/blob/main/tools/v030_conformance_report.py) et [validateur S8](https://github.com/tawounfouet/pyllmkit/blob/main/tools/v030_s8_integrated_evidence.py).

## 3. Lecture de ADR-059, recommandation de ratification

[ADR-059](https://github.com/tawounfouet/pyllmkit/blob/main/docs/adr/ADR-059-multi-provider-conformance-boundary.md) est **PROPOSED**. [Contract Profile v1](https://github.com/tawounfouet/pyllmkit/blob/main/docs/milestones/0.3.0/01_MULTI_PROVIDER_CONTRACT_V1.md) demeure **DRAFT**.

| Décision proposée ADR-059 | Lecture au vu des preuves | Attestation restant à obtenir |
|---|---|---|
| Contrats dans les Protocols / tests, pas de nouveau VO ProviderContract | Cohérent avec séparation domaine/adapter | Décision API owner/reviewer |
| Scope `text_only_v1`, pas d'aplatissement du multimodal/tools | Cohérent avec fixtures S1-S4 | Ratifier limites et refus |
| Capabilities NATIVE seulement, UNKNOWN/PARTIAL/EMULATED/UNSUPPORTED fail-closed | Tests S1/S4 explicitement présents | Versionner matrice effective par provider/modèle |
| Erreurs code-only et redaction | Fixtures S2/S3 adversariales | Audit transversal de logs/chaînes d'erreurs indépendant |
| RunId / attempt_id, terminal unique, pas de retries implicites | S2-S5 ont des tests dédiés | Traçabilité exhaustive d'alias et attempt |
| Parité canonique sync/async, sans promettre égalité du temps d'exécution | Tests multi-provider exécutés | Ratifier exceptions par mode |
| Résultats PASS/FAIL/N/A/UNSUPPORTED/BLOCKED et provenance | 752 PASS avec SHA, Python, fixture | Ajouter le registre des scénarios **non exécutables** et justifications N/A |
| G0-G9 autonomes ; pas de release implicite | Dossier de gates en place | Signatures de décision par gate |

**Avis technique préparatoire :** ADR-059 peut être proposé pour acceptation sur le périmètre **offline text-only** avec des exceptions explicites, mais ce document **ne l'approuve pas**, ne change pas son statut et ne clôt pas G0/G1.

## 4. Oracle des 27 familles de conformance

Les deux validateurs ont des listes de minima **égales** et la somme des minima est exactement **752**. Ils attestent l'exécution réussie des familles attendues sur le SHA audité, mais cela **ne prouve pas** une matrice exhaustive des possibilités API des six fournisseurs.

| Famille | Cas attendus (minimum) | Statut |
|---|---:|---|
| **S1: profil et préconditions** - `test_six_native_encoders_preserve_text_and_explicit_token_limit` | 6 | PASS offline (CI exacte) |
| `test_generation_snapshot_missing_fails_before_adapter` | 6 | PASS offline (CI exacte) |
| `test_developer_role_is_not_silently_coerced` | 6 | PASS offline (CI exacte) |
| **S2/S3: erreurs, sorties et sécurité de transport simulé** - `test_status_failure_has_one_safe_code_and_one_transport_attempt` | 108 | PASS offline (CI exacte) |
| `test_explicit_live_opt_in_gate_prevents_even_mock_transport_contact` | 12 | PASS offline (CI exacte) |
| `test_native_response_projection_is_consistent_and_lossless` | 24 | PASS offline (CI exacte) |
| `test_ollama_json_content_type_is_explicitly_supported` | 2 | PASS offline (CI exacte) |
| `test_native_transport_error_is_sanitized_and_nonretryable` | 48 | PASS offline (CI exacte) |
| `test_native_response_failure_is_strict_and_nonleaking` | 72 | PASS offline (CI exacte) |
| **S4: génération, rôles, usage et raisons de fin** - `test_explicit_native_parameter_is_mapped_or_rejected` | 48 | PASS offline (CI exacte) |
| `test_adapter_rejects_non_native_assessment_even_when_prepared` | 72 | PASS offline (CI exacte) |
| `test_adapter_rejects_missing_assessment_without_silent_acceptance` | 18 | PASS offline (CI exacte) |
| `test_application_refuses_non_native_support_before_adapter` | 24 | PASS offline (CI exacte) |
| `test_supported_multiturn_text_history_is_lossless` | 6 | PASS offline (CI exacte) |
| `test_history_role_restrictions_are_explicit_not_coerced` | 30 | PASS offline (CI exacte) |
| `test_native_response_usage_and_finish_semantics` | 60 | PASS offline (CI exacte) |
| **S5: flux et lifecycle** - `test_native_stream_conformance` | 84 | PASS offline (CI exacte) |
| `test_pre_cancelled_native_session_never_contacts_transport` | 12 | PASS offline (CI exacte) |
| `test_cancel_after_first_delta_closes_native_mock_transport` | 12 | PASS offline (CI exacte) |
| `test_single_use_stream_session_rejects_replay_without_second_call` | 12 | PASS offline (CI exacte) |
| `test_external_async_task_cancel_propagates_and_closes_native_mock_socket` | 6 | PASS offline (CI exacte) |
| `test_cancel_after_completed_stream_has_no_second_terminal` | 12 | PASS offline (CI exacte) |
| **S6: egress et deadlines de préflight** - `test_cloud_rejects_any_unapproved_endpoint_before_secret_and_transport` | 40 | PASS offline (CI exacte) |
| `test_cloud_valid_endpoint_still_works_with_synthetic_credential` | 10 | PASS offline (CI exacte) |
| `test_openai_config_mutated_after_construction_is_rejected_at_call` | 2 | PASS offline (CI exacte) |
| `test_ollama_mutated_destination_is_rejected_as_noncanonical` | 8 | PASS offline (CI exacte) |
| `test_expired_invocation_deadline_prevents_native_egress` | 12 | PASS offline (CI exacte) |

**Vocabulaire cible :** `PASS`, `FAIL`, `NOT_APPLICABLE`, `UNSUPPORTED`, `BLOCKED`. Les résultats exécutés sont PASS. Il manque encore un **inventaire des cases non exécutées**, justifié individuellement, plutôt qu'une extrapolation depuis les cas PASS.

Les six fournisseurs natifs couverts sont **OpenAI, Anthropic, Google Gemini, xAI, Mistral, Ollama**. Le catalogue CLI couvre 15 catégories de fournisseurs, ce qui n'étend pas automatiquement la qualification native à 15.

## 5. Matrice des invariants C-01 à C-15

| Invariant | Objectif | Qualification actuelle | Preuve ou action résiduelle |
|---|---|---|---|
| C-01 | Identité provider/deployment/alias | **PARTIAL** | Lier les cas de résolution et incohérences d'alias aux 6 providers. |
| C-02 | RunId et attempt_id | **PARTIAL** | Prouver les combinaisons de corrélation sur sync/async et streaming. |
| C-03 | Aucun paramètre ignoré silencieusement | **OK-OFFLINE** | S4 génération et refus des statuts non natifs. |
| C-04 | Réponse / run terminaux valides | **OK-OFFLINE** | Tests P7, S2 et S4. |
| C-05 | FinishReason UNKNOWN préservé | **OK-OFFLINE** | S4 usage/finish et correctif CLI #101. |
| C-06 | Usage incomplet non inventé | **OK-OFFLINE** | S2 et S4. |
| C-07 | Erreurs sûres et non-divulgation | **PARTIAL** | Code-only offline ; audit logs/traces/chaînes d'exceptions encore à signer. |
| C-08 | Événements ordonnés et terminal unique | **OK-OFFLINE** | S2 stream et S5 lifecycle. |
| C-09 | EOF / sortie non représentable fail-closed | **OK-OFFLINE** | S2/S4/S5. |
| C-10 | Annulation locale et cleanup | **OK-OFFLINE** | S5 ; arrêt distant ou facturation non certifiés. |
| C-11 | Pas de retry/fallback/redirect implicites | **OK-OFFLINE** | S2/S3/S6 sur transport simulé. |
| C-12 | Import provider-free sans HTTPX | **OK-OFFLINE** | Smoke clean wheel S7. |
| C-13 | Parité sync/async | **PARTIAL** | Vérifier la totalité des oracles et préconditions P0. |
| C-14 | Destinations approuvées | **PARTIAL / BLOCKED-LIVE** | Préflight simulé OK ; DNS peer-IP TLS non attestés. |
| C-15 | Limites de durée et taille | **PARTIAL / BLOCKED-LIVE** | Deadline mock contrôlée ; streaming sync réel volontairement fail-closed. |

`OK-OFFLINE` signifie propriété démontrée sur tests synthétiques ciblés, **pas** certification live ni signature formelle. Le classement conserve les réserves de l'audit historique #99.

## 6. Décisions par gate

| Gate | Verdict préparatoire | Décision/validation encore nécessaire |
|---|---|---|
| G0 | PRET POUR REVUE, non ratifié | Approuver ADR-059 et baseline post-merge |
| G1 | PRET POUR REVUE, non ratifié | Approuver `text_only_v1`, champs NATIVE et refus |
| G2 | PARTIAL | Registre exhaustif des axes/scénarios, exceptions N/A et provenance |
| G3 | PARTIAL | Vérification indépendante redaction, erreurs et logs |
| G4 | PARTIAL | Contrôle alias, RunId, attempt_id, parité complète |
| G5 | GO TECHNIQUE OFFLINE / GLOBAL PARTIAL | Signer les limites de streaming ; garder sync live fail-closed |
| G6 | GO PRE-FLIGHT OFFLINE / NO-GO LIVE | Tests DNS/peer-IP/TLS, SSRF, budgets, canary, sécurité opérationnelle distincts |
| G7 | PARTIAL | Note de compatibilité et revue développeur SDK |
| G8 | GO CI EXACTE OFFLINE / SIGNOFF PENDING | Revue humaine indépendante et PV daté sur le SHA final |
| G9 | NO-GO RELEASE | Candidat de version, release notes, provenance, autorisation explicite |

## 7. Cahier de revue API et sécurité à faire exécuter

Le reviewer humain **différent de l'auteur des changements** doit cocher les preuves et produire une décision explicite :

- [ ] Confirmer les préconditions, signatures InferencePort/AsyncInferencePort et types publics sur 6 providers.
- [ ] Confirmer les refus de capabilities `UNKNOWN`, `PARTIAL`, `UNSUPPORTED` et `EMULATED` sans perte silencieuse.
- [ ] Vérifier le mapping natif des 8 paramètres S4, y compris statut absent et valeurs limites.
- [ ] Vérifier que `FinishReason.UNKNOWN` et `Usage` partiel ne sont pas normalisés abusivement.
- [ ] Vérifier les identités `provider_id`, `deployment_id`, `model_alias`, `run_id`, `attempt_id`.
- [ ] Analyser la surface d'exception, le masquage d'erreurs, les logs et l'absence de fuite de credentials/prompts.
- [ ] Confirmer le comportement `--mock/--live`, `--record-content`, `--allow-content-export` et les contraintes de purge.
- [ ] Vérifier les limites de sync/async streaming, l'ordre des événements et la fermeture des ressources.
- [ ] Contrôler les risques live distincts (DNS, IP connectée, TLS, SSRF/rebinding, budgets), ou signer un **NO-GO live** explicite.
- [ ] Vérifier le diff par rapport au SHA `b4f91e1...`, citer CI/artefacts et enregistrer les exceptions.

**Formulaire de décision :** reviewer = `PENDING`; date = `PENDING`; SHA examiné = `PENDING`; décision G0/G1/G2/G3/G4/G5/G6/G7/G8 = `PENDING`; anomalies = `PENDING`.

L'auteur assistant **ne peut ni remplir une signature humaine**, ni transformer une validation automatique en review indépendante, ni déclarer G0-G8 fermés sans décision enregistrée.

## 8. Suites minimales

1. Obtenir la revue distincte sur ce dossier et le code courant : noter constats, correctifs et exceptions.
2. Fermer les gaps C-01/C-02/C-07/C-13 et documenter la matrice P0 des cases exclues.
3. Signer les gates offline limités `G0-G5/G7/G8` suivant les résultats de revue.
4. Maintenir un NO-GO live (G6) jusqu'à qualification dédiée, sans préjuger de la stratégie de tag 0.3.0.
5. Ajouter une note de migration/compatibilité, préparer une candidate et qualifier G9 séparément (issue #103).

**Cette publication documentaire n'est pas un GO de tag, de release ou de PyPI.**
