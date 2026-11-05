# Future Provider Boundary - Contrat d'integration sans fuite dans le domaine

> Date : 2026-11-05
> Statut : **SPECIFICATION FUTURE, NON IMPLEMENTEE**. Aucune connexion LLM effective n'est ajoutee par cette documentation.
> Autorite : ADR-014..021, JSON Inference v1, invariants M1/M2/M3.
> Regle centrale : **les Value Objects sont purs**. Transport, secrets, parsing de texte, retries et adaptation provider vivent a l'exterieur.

## 1. Architecture de frontiere envisagee

```text
Consumer -> Application Use Case
           |      |
           |      +-> request validation / explicit compatibility policy
           v
       InferencePort (future, explicite)
           |
     ProviderAdapter
        |       |       |        |
      Secret  JSON    Network  Retry/timeout
      Store   parser  Client   Policy
           |
     Native Response Mapping
           |
    InferenceResponse / InferenceRun
           |
     Inference JSON v1
```

Le domaine a3 actuel **ne possede pas d'InferencePort operationnel**. Tout port propose doit recevoir une ADR, une API minimale et des tests de contrat, plutot qu'etre introduit indirectement via `InferenceRequest`.

## 2. Responsabilites par couche

| Sujet | Couche proprietaire future | Contrat attendu |
|---|---|---|
| Parsing JSON **texte** | Boundary API/transport | Accepter seulement JSON RFC-compatible; refuser cles dupliquees et constantes non standards |
| Limites payload | Ingress/API | Taille max du corps (bytes), profondeur, nombre de messages, media refs et temps de parsing; rejeter avant allocs couteuses |
| Validation des schemas Inference v1 | Domaine | `request_from_dict`, `response_from_dict`, `run_from_dict`; aucune coercition |
| Secrets et identite provider | Adapter + secret manager | Reference opaque; pas de token dans VO, logs, `repr`, erreur retour |
| Compatibilite parametres | Application + snapshot capability | Utiliser `GenerationSupportSnapshot` explicite; ne pas ignorer `UNSUPPORTED`; UNKNOWN ne devient pas NATIVE |
| Mapping provider -> domain | Adapter | Raison d'arret native conservee; Usage nullable, aucun total ou cout invente |
| Transport, TLS, timeout | Adapter HTTP | Deadlines explicites, TLS verify, proxy controle, connection pool bornes |
| Erreurs, codes, traces | Adapter/Application | Erreur technique sanitizee -> `InferenceFailure(code)` ; logs a acces restreint et identifiants de correlation non sensibles |
| Retry, backoff, idempotence | Application/Adapter | Retry seulement sur erreurs transitoires autorisees; budget borne; distinguer les **Runs** des tentatives reseau |
| Streaming | Future application + adapter | Type d'evenements versionne, timeouts, cancellation cooperative, backpressure et ordre; ne pas confondre Run STREAMING et vrai flux |
| Observabilite | Adapter/Application | Metrics sans prompt brut, traces redactees, comptage cost explicite si donnees suffisantes |
| Persistance et retention | Infrastructure | Chiffrement, TTL, RBAC, audit de lecture, suppression des contenus |
| URL / endpoints | Adapter et policy security | Allowlist ou politique explicite de destination; defense SSRF, blocage loopback/metadata IP; ne pas ouvrir arbitrary URLs |

## 3. Politique d'entree JSON texte (future)

Le mapping Inference v1 **n'a pas l'obligation de detecter** deux cles dupliquees quand le parser les a deja ecrasees. L'API de transport devra :

1. Verifier content-type accepte et taille maximale du corps **avant** chargement en memoire.
2. Parser en refusant les **cles dupliquees a chaque niveau**, y compris `messages`, `target`, `response`, `usage`.
3. Interdire `NaN`, `Infinity`, `-Infinity` et nombre JSON hors limites applicatives.
4. Refuser un JSON dont l'objet racine n'est pas un dictionnaire, puis confier la validation des champs au codec Inference v1.
5. Garder des erreurs **code-only** (sans coller le contenu de la requete). Contrôler nombre de champs/longueur des chaines avant diagnostic.
6. Fixer dans une ADR future les limites quantitatives et le traitement du streaming; aucune valeur de taille/temps n'est inventee comme contrat actuel.

Exemple d'implementation *possible au boundary, non ajoutee au domaine* :

```python
import json

def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result

def parse_external_json(raw: str) -> object:
    return json.loads(
        raw,
        object_pairs_hook=_no_duplicate_keys,
        parse_constant=lambda _value: (_ for _ in ()).throw(
            ValueError("non-standard JSON constant")
        ),
    )
```

Ce code ne traite **pas** a lui seul les limites de taille/profondeur/precision, qui restent a l'infrastructure; ne pas le presenter comme parser de production complet. L'algorithme est explicite sur l'absence de fuite de valeur dans les exceptions.

## 4. Normalisation des erreurs

Table de mapping **a definir concretement pour chaque provider** :

| Cas | Comportement applicatif | Ne pas faire |
|---|---|---|
| Timeout | Code `timeout` ou `provider_timeout` ; conserver correlation | Retourner stacktrace provider dans `InferenceFailure` |
| 429 / quotas | Retry borne si adapte, sinon code normalise | Boucle infinie, cout imprevisible |
| 5xx transitoire | Backoff avec jitter, budget de tentative et deadline | Replay non trace du meme RunId |
| 4xx non-retryable | Refus sans retry ou mapping explicite | Reessayer un mauvais parametre indefiniment |
| Reponse partielle | Explicit UNKNOWN / None et evenement d'echec selon ADR future | Inventer Usage, STOP ou paiement |
| Annulation | Signal a l'adapter, resultat terminal dans Run si coherent | Affirmer qu'un `cancel()` pur annule un appel distant |

Un retry de **transport** a sa propre identite de tentative et doit etre correlate au Run; un replay d'inference logique cree un nouveau `InferenceRunId` suivant le contrat L3.3. Les politiques de idempotence et de facturation sont a documenter avant livraison.

## 5. Securite et confidentialite

- Refs media : aucune lecture de fichier, URI ou fetch implicite par `MediaSourceRef`.
- Pas de journalisation des prompts, des corps HTTP ou des `Authorization` headers par defaut.
- Secrets via coffre et injection a la couche adaptateur, rotation et revocation verifiables, pas de `.env` commits.
- Egress controle, SSRF defense, destinations et DNS verifiables selon le modele de menace.
- Filtres de donnees et controle d'acces app/tenant avant usage des tools ou du provider.
- Eviter dans les messages d'erreurs les valeurs inconnues fournies par le fournisseur ou l'utilisateur.

## 6. Tests d'acceptation a creer avant le premier provider

| Scenario | Preuve attendue |
|---|---|
| JSON duplicate keys, NaN/Infinity, payload enorme | Rejet avant domaine, code sanitize |
| Parametre UNSUPPORTED ou UNKNOWN | Pas de parametre perdu ni support invente |
| Usage partiel / FinishReason inconnu | Observations fideles, aucune conversion ZERO/STOP |
| Provider timeout, 429, 5xx, 4xx | Matrice d'erreurs, retries bornes, idempotence |
| Secret/URL sensibles | Aucun token dans exception, repr, logs, artefacts CI |
| Endpoint prive / metadata IP | SSRF bloque avant connexion |
| Cancel / streaming | Aucun faux claim de cancellation distante; backpressure |
| Tests contractuels | Fakes deterministes + tests sandbox provider hors suite offline |
| Regression schema | Model v1, Interaction v1, Inference v1 invariants intacts |

## 7. Sortie de cette specification

Au lancement d'un lot provider, creer **une nouvelle ADR de boundary** et des use cases explicites, puis definir les budgets, limites, erreurs, retries et types de streams. La spec ne vaut pas implementation ni autorisation de connecteur.

Voir [API Inference](../api/inference.md), [runbook release](../governance/RELEASE_0_1_0a3_POLICY_AND_RUNBOOK.md), [ADR-020](../adr/ADR-020-inference-json-v1-codec.md).
