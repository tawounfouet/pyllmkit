# Phase 3 - Proposition de contrat des primitives d'inference

> Statut : **DRAFT / NOT IMPLEMENTED / NOT APPROVED**
> Reference : plan docs/03_PYLLMKIT_PHASE_3_IMPLEMENTATION_PLAN.md (section 3 a 8)
> Source de verite au G0 : ADR-014..021 apres arbitrage.
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

# InferenceRun = Entity a identite RunId,
# transitions controllees produisant de nouveaux snapshots immuables.
~~~

Les variantes ModelTarget, DeploymentTarget et EndpointTarget, la forme exacte des erreurs et le schema Run sont a faire valider par ADR avant tout code public. Les dataclasses ci-dessus ne specifient pas les constructeurs finaux.

## 3. Validation a trois frontieres

| Frontiere | Responsabilite | Autorisee a3 |
|---|---|---|
| Domain | Structure, types, invariants, transitions, codec | Oui, sans reseau |
| Application future | Resolution et evaluation effective de compatibilite | Pas de resolver operationnel P0 |
| Adapter futur | Provider mapping, HTTP, auth, retries, SSRF, normalisation | Non |

Un ImageContent est une modalite d'entree et non une preuve de VISION effective. Un target est une reference, pas une session de connexion.

## 4. Machine a etats candidate

~~~text
CREATED -> RUNNING
RUNNING -> STREAMING | COMPLETED | FAILED | CANCELLED
STREAMING -> COMPLETED | FAILED | CANCELLED
COMPLETED, FAILED, CANCELLED -> aucun etat
~~~

STREAMING ne fournit pas de flux ni de StreamEvent en a3. L'horloge est fournie au moment de transition, timestamps aware. RunId reste stable; un retry cree un nouvel identifiant.

## 5. Seuils qualifiants

- G0 : ADR adoptees et contrat revu, sans preuve implicite.
- G1 : Target/Config/Request, tests offline et non-regression.
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
