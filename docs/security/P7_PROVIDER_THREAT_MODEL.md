# PyLLMKit - P7 Provider Threat Model

- Date : 2026-11-06
- Statut : PROPOSED - validation de sécurité P7-G0 requise
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Périmètre : invocations HTTP/SDK, secrets, mapping, streaming, logs, qualité et dépenses.

## Actifs et frontières de confiance

Actifs: credential API, prompts et réponses, messages multi-rôles, identité modèle/deployment, coût cloud, RunId et AttemptId, métriques et logs. Frontières: application -> adapter; adapter -> credential resolver; adapter -> réseau; SDK -> DTO natif -> domaine. Provider et contenu de réponse sont non fiables par défaut.

## Menaces prioritaires et contrôles obligatoires

| ID | Scénario | Impact | Contrôle | Test exigé |
|---|---|---|---|---|
| T01 | Clé dans repr, exception, trace ou CI | Critique | CredentialRef opaque, log redaction, zero body | canary token + prompt |
| T02 | SSRF vers metadata IP ou LAN | Critique | allowlist URL/IP, loopback Ollama limité, DNS final validé | metadata, private IP, IPv6, DNS |
| T03 | Redirect externe ou HTTPS downgradé | Critique | redirects interdits par défaut, TLS verify obligatoire en cloud | 30x cross-host, http redirect |
| T04 | Fausse capacité UNKNOWN devenue NATIVE | Haute | fail-closed P6, refus paramètre non supporté | tests unsupported/unknown |
| T05 | Injection de rôle ou tool_call par mapping | Haute | mapping text-only strict, reject on unknown | fixtures rôle/tool/multimodal |
| T06 | Double facturation par retries superposés | Haute | SDK retries=0, politique unique max attempts/deadline | compteur d'essais 429/timeout |
| T07 | Rejouer un stream après premier delta | Haute | no retry post-delta, fail terminal exact | interruption SSE/JSONL |
| T08 | Faux succès après cancellation | Haute | cleanup, terminalité observée, pas de remote cancel claim | early close sync/async |
| T09 | Appel live en CI/pull request | Critique | double opt-in + secrets absents, branche non-fiable isolée | CI sans réseau |
| T10 | Dépense cloud incontrôlée | Haute | tokens, budget, nombre d'appels et timeout bornés | refus sans plafond |
| T11 | Informations sensibles dans la télémétrie | Haute | métriques agrégées et ids opaques uniquement | canary logs/artefacts |
| T12 | SDK compromis/dérive protocole | Haute | extras séparés, versions revues, fixtures et scans | install clean + contrat |
| T13 | Data retention non maîtrisée | Haute | privacy policy explicite, OpenAI store=false lorsque applicable | payload contract + fail closed |
| T14 | Une cible EndpointTarget transformée en URL | Critique | binding approuvé, jamais URL depuis identifiant | EndpointTarget adversarial |

## Matrice d'autorisation réseau

- OpenAI / Anthropic: uniquement API officielle par défaut, host/scheme explicitement approuvé; TLS vérifié et aucune redirection hors contrat.
- Ollama: seulement loopback configuré explicitement; ports et hôtes distants uniquement via dérogation documentée, revue distincte et allowlist.
- Il est interdit d'effectuer un appel réseau lors de l'import, de la construction d'une Value Object ou de la résolution pure M6.
- Interdiction de deviner ou de construire une URL à partir de ModelId, ProviderId ou EndpointId.
- Le contrôle DNS/IP doit couvrir les adresses effectivement connectées pour éviter le TOCTOU; un simple contrôle regex/hostname ne suffit pas.

## Confidentialité et rétention

Ne pas journaliser prompt, output complet, headers Authorization, raw SDK exception, body HTTP ni fichiers media. Conserver uniquement codes erreurs sûrs, durée, identifiants opaques et compteurs de tokens connus. Un test live ne stocke ni clé ni réponse textuelle. Si la demande de non-rétention chez un provider n'est pas applicable ou ne peut être garantie, déclarer la limite et obtenir un arbitrage explicite.

## Risques résiduels et décision de gate

Le contrôle local de deadline ne peut garantir ni l'annulation distante ni l'absence de facturation d'un appel expiré. Les API et leurs garanties évoluent; vérification officielle à refaire au lot provider. Risques de gouvernance ouverts: main non protégée (#22), release indépendante (#35), frontière provider (#36), revue tierce non constatée. G0 ne peut être GO tant que ses ADR et ce threat model ne sont pas approuvés; même GO G0 n'autorise ni production ni tests cloud payants.
