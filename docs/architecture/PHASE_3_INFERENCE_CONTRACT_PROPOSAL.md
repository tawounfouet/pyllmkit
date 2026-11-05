# Phase 3 - Proposition de contrat des primitives d'inference

> Statut : **OWNER APPROVED DESIGN / NOT IMPLEMENTED** (2026-11-05). Gate P3-G0 formel attend la preuve CI exacte sur main.
> Reference : plan docs/03_PYLLMKIT_PHASE_3_IMPLEMENTATION_PLAN.md (section 3 a 8)
> Source de verite au G0 : ADR-014..021 ACCEPTED et P3_G0_OWNER_ARCHITECTURE_APPROVAL.md.
> Ceci est une specification, **pas un exemple copiable d'API deja disponible**.

## 1. Carte du domaine

~~~text
Model Domain (M1)              Interaction Domain (M2)
  ModelId / Capability           Message / Content / Parts
            \                           /
             \                         /
              -> InferenceRequest (Value Object)
                        |
                        v
                  InferenceRun
           (Entity / Aggregate Root)
                        |
                        v
                InferenceResponse
                    (Value Object)
                        |
                 +------+------+
                 |             |
             TextOutput     FinishReason / Usage?
~~~

Aucun SDK, appel HTTP, serveur, facade agentique, executor ou registry n'est requis pour construire ces valeurs.

## 2. Signatures candidates non normatives

~~~python
# Illustration conceptuelle uniquement - ces classes ne sont pas encore implementees.
@dataclass(frozen=True, slots=True)
class GenerationConfig:
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_output_tokens: int | None = None
    seed: int | None = None
    stop_sequences: tuple[str, ...] | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None

@dataclass(frozen=True, slots=True)
class InferenceRequest:
    target: InferenceTarget
    messages: tuple[Message, ...]  # 1..* pour le chat a3
    generation_config: GenerationConfig | None = None

@dataclass(frozen=True, slots=True)
class TextOutput:
    text: str  # "" autorise, None rejete

@dataclass(frozen=True, slots=True)
class FinishReason:
    code: FinishReasonCode
    native_reason: str | None = None

@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None
    cached_input_tokens: int | None = None

@dataclass(frozen=True, slots=True)
class InferenceResponse:
    run_id: InferenceRunId
    output: TextOutput
    finish_reason: FinishReason | None = None
    usage: Usage | None = None

@dataclass(frozen=True, slots=True)
class InferenceFailure:
    code: str  # code canonique non vide, sans erreur provider native

# InferenceRun = Entity a identite RunId.
# Snapshot immuable: run_id, request, attempt, state,
# started_at, streaming_started_at, finished_at,
# response | None, failure | None, cancellation_reason_code | None.
# Deux snapshots d'une meme Entity sont egaux par identite RunId,
# mais leur state, timestamps et payload se comparent distinctement.
# Transitions pures avec datetime timezone-aware injecte.
# Aucun moteur d'execution, stockage ou emission d'evenement.
~~~

Les variantes ModelTarget, DeploymentTarget et EndpointTarget, les erreurs et le schema Run sont arbitres dans les ADR ACCEPTED; les APIs publiques restent a implementer. Les champs decimaux GenerationConfig sont adoptes en **float exact** (0.0 valide, int 0 refuse) : choix ADR-016 accepte. Les signatures ci-dessus ne specifient pas les constructeurs finaux. Les dataclasses ci-dessus ne sont pas une implementation existante; elles illustrent les contrats adoptes.

## 3. Validation a trois frontieres

| Frontiere | Responsabilite | Autorisee a3 |
|---|---|---|
| Domain | Structure, types, invariants, transitions, codec | Oui, sans reseau |
| Application future | Resolution et evaluation effective de compatibilite | Pas de resolver operationnel P0; evaluateur pur sur snapshot explicitement fourni selon ADR-021 option A adoptee |
| Adapter futur | Provider mapping, HTTP, auth, retries, SSRF, normalisation | Non |

Un ImageContent est une modalite d'entree et non une preuve de VISION effective. Un target est une reference, pas une session de connexion.

## 4. Machine a etats candidate

~~~text
CREATED -> RUNNING
RUNNING -> STREAMING | COMPLETED | FAILED | CANCELLED
STREAMING -> COMPLETED | FAILED | CANCELLED
COMPLETED, FAILED, CANCELLED -> aucun etat
~~~

STREAMING ne fournit pas de flux ni de StreamEvent en a3. L'horloge est fournie au moment de transition, timestamps aware. RunId reste stable; un retry cree un nouvel identifiant. Les etats terminaux utilisent **finished_at** : COMPLETED -> response; FAILED -> InferenceFailure; CANCELLED -> code de raison facultatif. Voir ADR-019 pour les six combinaisons legales.

## 5. Seuils qualifiants

- G0 : ADR adoptees et contrat revu, sans preuve implicite.
- G1 : Target/Config/Request, tests offline et non-regression; AC-007 obligatoire : evaluator pur sur snapshot selon option A ADR-021; jamais PASS sans test.
- G2 : Output/FinishReason/Usage/Response.
- G3 : Run, transitions, mauvais run_id et horloge.
- G4 : Codec JSON v1, tests stricts, securite, non-regression M1/M2.
- G5 : API, documentation, packaging, CI exacte sur main.
- M3 : bilan GO/NO-GO distinct du droit de publier.

## 6. Apprentissage logiciel

- DDD : Value Object et Entity/Aggregate Root sont distingues par valeur contre identite.
- SoC / SRP : Request, Run, Response et Usage ne partagent pas artificiellement leurs responsabilites.
- DIP / Hexagonal : les types du domaine ne dependent jamais des adapters.
- State Machine : interdictions de transitions rendues testables.
- Fail Fast : types invalides et schemas inconnus echouent sans coercition.
- YAGNI : ni tool runtime, ni streaming reel, ni backend d'execution dans a3.
