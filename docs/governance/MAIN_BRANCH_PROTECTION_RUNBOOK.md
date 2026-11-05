# Gouvernance GitHub - protection effective de main

> Date : 2026-11-05
> Repository : `tawounfouet/pyllmkit`
> Issue d'execution et preuve : [#22](https://github.com/tawounfouet/pyllmkit/issues/22).
> **STATUT OBSERVE : NON APPLIQUE.** Le GET `branches/main` indique `protected=false`; GET `rulesets` retourne `[]`; le connecteur GitHub App ne peut pas consulter `branches/main/protection` (HTTP 403).
> L'API du connecteur est **GET seulement pour les rulesets et protections** : aucun outil d'ecriture `PUT branch protection` / `POST rulesets` n'est expose. Les permissions `admin=true` de l'utilisateur ne se transmettent pas a la GitHub App.
> Ce document **n'est pas** une attestation de mise en place de protections.

## 1. Objectif

Rendre `main` effectivement gouvernee par des regles appliquees cote GitHub : contribution par PR, controles obligatoires, revues, interdiction de force-push et suppression, absence de bypass non trace, verification periodique de l'enforcement.

## 2. Matrice cible (a mettre en place dans l'interface GitHub)

| Regle | Politique proposee | Etat |
|---|---|---|
| Cible | Branche `main` | Cible connue |
| Merge via PR | PR obligatoire avant tout merge | A configurer |
| Required status checks | `validate (3.11)`, `validate (3.12)`, `validate (3.13)` du workflow `CI` | A configurer / verifier noms reels |
| Branch must be up to date | Rebasage/merge avec `main` avant merge ou merge queue avec checks requis | A configurer |
| Require approvals | Au moins **1 APPROVED independant**, hors auteur | A configurer, depend de la disponibilite d'un reviewer |
| Dismiss stale approvals | Demander une nouvelle approbation apres changement des commits | A configurer |
| Conversation resolution | Tous les threads de revue resolus | A configurer |
| Code-owner review | Activer **uniquement si CODEOWNERS et reviewer distincts sont reels** | A evaluer |
| Restrict bypass | Aucun bypass permanent d'admin/bot non justifie | A configurer |
| Force push/delete | Interdit sur `main` | A configurer |
| Ruleset enforcement | `active`, pas `evaluate` ou `disabled` | A verifier |
| Critical paths | `.github/workflows/`, `pyproject.toml`, domaines, schema, release policy | Review requise par regle ou pratiques selon plan |

Les *noms exacts* des status checks doivent etre choisis apres observation des jobs affiches sur la CI du SHA cible. Un contexte de status mal nomme ne protegera rien, ou bloquera toutes les PR.

### Attention : projet a mainteneur unique

Ne configurez pas une regle d'approbation obligatoire en supposant qu'un auteur puisse approuver sa propre PR. Pour une politique `APPROVED independant`, il faut **un reviewer distinct** et habilite. Tant que cette condition n'est pas remplie, laisser le suivi de la regle en cours, ne pas mentir dans la decision de release. Une exception de gouvernance, si adoptee, devra etre motivee et approuvee explicitement.

## 3. Procedure manuelle de configuration (GitHub web)

1. Ouvrir `https://github.com/tawounfouet/pyllmkit/settings/rules` avec le compte proprietaire ou administrateur.
2. Creer un ruleset de branche ou utiliser une protection de branche existante (eviter deux jeux de regles contradictoires).
3. Cibler `main` et activer l'application du ruleset.
4. Activer PR obligatoire, CI requise, revue d'approbation independante si possible, threads resolus et regles anti-force-push/suppression.
5. Verifier les noms reels des trois jobs `validate (3.11)`, `validate (3.12)`, `validate (3.13)`, puis sauvegarder.
6. Confirmer que les contraintes s'appliquent a l'identite qui peut fusionner : aucune exception silencieuse pour l'admin, la GitHub App ou le compte de service.
7. Utiliser une **PR de verification non destructive** et s'assurer qu'une tentative de fusion sans checks/reviews complets est **bloquee** (UI GitHub/owner, sans pousser directement ou casser `main`).
8. Archiver la preuve du ruleset et de la PR de verification dans l'issue #22.

Selon l'offre GitHub ou la visibilite du depot, certaines options peuvent ne pas etre disponibles ou leur enforcement peut varier. Ne pas confondre une regle **affichee dans l'interface** avec une regle **effectivement appliquee**.

## 4. Preuves de cloture de l'issue #22

| Preuve obligatoire | Methode de verification |
|---|---|
| Branch status | GET `/repos/tawounfouet/pyllmkit/branches/main` => `protected=true`, ou regles effectives prouvees si comportement GitHub specifique |
| Ruleset | GET `/repos/tawounfouet/pyllmkit/rulesets` indique une regle `active` ciblant `main` |
| Status checks | Capture / export de la liste exact required checks ; trois jobs Python connus |
| Review policy | Preuve d'approval independante exigee et absence de bypass |
| Enforcement | PR de verification bloquee sans check/approval puis debloquee apres satisfaction |
| Owner sign-off | Nom/identite GitHub du compte autorise et date de validation |

Un refus HTTP 403 de l'App lors de la lecture de protection **ne permet pas** de conclure que des controles absents ou presents existent; il impose une preuve alternative (owner UI et rulesets lisibles).

**Condition de fermeture : toutes les preuves obligatoires sont disponibles et rattachees a #22.** Sinon **issue #22 OPEN** et **publication NO-GO**.

## 5. Separation des qualifications

- `M3 GO technique avec reserves` est possible pour un **package de domaine hors ligne**, apres revue des no-go techniques du plan.
- `Release GO` **n'est pas possible** sans gouvernance explicitement approuvee et preuves suffisantes.
- La CI de PR ou un merge par SHA attendu ne remplace **jamais** une protection de branche imposee par GitHub.

Documentation liee : [release runbook](RELEASE_0_1_0a3_POLICY_AND_RUNBOOK.md), [M3 precheck](../quality/M3_READINESS_PRECHECK.md).
