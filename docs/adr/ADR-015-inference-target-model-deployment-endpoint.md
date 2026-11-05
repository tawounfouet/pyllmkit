# ADR-015 - Cibles d'inference explicites
> **Decision owner P3-G0 (2026-11-05)** : `ACCEPTED`, sous autorite du proprietaire dans la conversation du projet. Cette autorisation concerne les contrats et leur integration, **pas** une GitHub review externe ni la publication d'un package. 
> **Arbitrage retenu :** Three discriminated Target variants (Model, Deployment, Endpoint); distinct typed IDs; no resolution or provider inferred.


- **Statut : ACCEPTED** - adoption explicite par le proprietaire pour P3-G0 le 2026-11-05. Contrat de conception adopte, implementation Python non commencee.
- Sources : plan Phase 3 section 5.1; INF-007/008/011/012, INV-001/002/003, architecture Serving.
- Depends on : ADR-014.

## Contexte

Le corpus distingue Model, Deployment et Endpoint. M2 n'implemente pas de Deployment ni Endpoint operables. Une cible doit pouvoir etre decrite sans promettre la resolution ou la disponibilite effective.

## Decision adoptee

1. Introduire **InferenceTarget** et trois variantes fermees au schema a3 : **ModelTarget**, **DeploymentTarget**, **EndpointTarget**.
2. ModelTarget reference un **ModelId** du domaine M1. DeploymentTarget et EndpointTarget referencent des identifiants opaques et distinctement types, non vides, sans construire d'Entity Serving.
3. Chaque variante est un Value Object immuable; le discriminant fait partie de la valeur et de la representation JSON.
4. Aucun target ne contient par defaut une URL a dereferencer, un credential ou un nom de provider infere d'un identifiant.
5. La presence d'une cible n'affirme ni existence, ni capacites effectives, ni readiness d'invocation. La resolution reste une responsabilite applicative future.
6. ModelTarget peut etre resolu plus tard en Deployment/Endpoint, seulement selon une policy explicite, jamais implicitement dans le constructeur.
7. Pas de fallback ou de routing automatique dans le Domain Core.

## Alternatives examinees

- ModelTarget uniquement : plus petit MVP, mais ignore INF-008 et complique la future evolution de l'API.
- Une simple string cible : rejete, perd les distinctions metier et rend les erreurs silencieuses probables.
- URL brute comme EndpointTarget : rejete, confusion identite, connectivite et risques de securite.

## Critere G0 et tests attendus

- Trois variantes disjointes, IDs exacts et non vides, type strict, equality/hash et serialization deterministes.
- Cross-type substitution refusee.
- Construction offline sans registry ni SDK.
- Une source contenant ImageContent reste une intention; support VISION effectif non invente.
- Tests P3-AC-001..003 et controle des imports.
