# ADR-014 - Frontieres Request / Run / Response
> **Decision owner P3-G0 (2026-11-05)** : `ACCEPTED`, sous autorite du proprietaire dans la conversation du projet. Cette autorisation concerne les contrats et leur integration, **pas** une GitHub review externe ni la publication d'un package. 
> **Arbitrage retenu :** Request/Response = Value Objects; Run = Entity/Aggregate Root; Request chat P0 with 1..* Message, no implicit ID, SDK or I/O.


- **Statut : ACCEPTED** - adoption explicite par le proprietaire pour P3-G0 le 2026-11-05. Contrat de conception adopte, implementation Python non commencee.
- Decisionnaire requis : proprietaire du projet.
- Sources : plan Phase 3 sections 3-5, vision Domain First, DDD (05), INV-007, INF-006/013/022.
- Dependance : ADR-015, ADR-017, ADR-019.

## Contexte

Le domaine M2 sait representer les messages mais ne sait pas encore distinguer l'intention d'inference de l'execution et du resultat. Copier un modele de reponse fournisseur produirait un couplage durable.

## Decision proposee

1. **InferenceRequest** est un Value Object immuable, compare par valeur et independant du provider. Il possede une cible et des messages ordonnes; aucun identifiant auto-genere ne change sa nature en Entity.
2. **InferenceRun** est l'Aggregate Root d'une execution concrete avec un **InferenceRunId** stable, un etat, une tentative et exactement une request logique. Deux runs peuvent partager la meme request.
3. **InferenceResponse** est un Value Object immuable, associe a exactement un RunId. Elle porte un output normalise, une raison de fin optionnelle et un Usage optionnel; elle n'est pas le run lui-meme.
4. Un Message n'est pas une InferenceRequest; un ModelTarget n'est pas un modele resolu. Le domaine ne transporte aucun client HTTP, token, SDK ou gestionnaire de retry.
5. Le cas P0 de a3 est une **requete de generation conversationnelle** avec 1..* messages. Cela ne redefinit pas le domaine conceptuel plus large autorisant 0..* messages pour de futurs modes d'inference. Cette restriction est une decision de perimetre de a3.
6. Les references d'identite et de correlation ne doivent pas obliger a creer une Conversation, un Deployment concret ou un Endpoint concret.

## Alternatives et compromis

- Objet unique RequestResponseRun : rejete, melange intention, etat et resultat.
- Request avec UUID implicite : rejete, fausse identite metier et non-determinisme.
- Mode conversationnel sans messages : differe, besoin fonctionnel non etabli pour a3.

## Consequences et tests de contrat

- Valeur, immutabilite et ordre de Request; plusieurs RunIds pour la meme request.
- Equality/hash de Run fondes sur l'identite, sans confondre equivalence des snapshots et egalite du contenu.
- Response reliee au bon RunId; aucune mutation ni effet de bord.
- Les objets Python exposes restent provisoires jusqu'au gate P3-G0.

## Validation requise

Decision explicite du proprietaire et revue du contrat public, puis tests P3-AC-001, P3-AC-014, P3-AC-020 et non-regression M1/M2. La presence du fichier ne vaut pas approbation.
