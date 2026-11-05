# ADR-022 - Tool definition and execution boundary

- Date : 2026-11-05
- Statut : ACCEPTED (owner, 2026-11-05; P4-G0 qualifié main@b66e94e3, CI #42079191595 SUCCESS)
- Phase : P4-BOOT, L4.1 et L4.2
- Sources : docs/04_PYLLMKIT_PHASE_4_IMPLEMENTATION_PLAN.md, domaine 00-09, principe TOOL-003.

> Approbation du proprietaire : [P4_G0_OWNER_ARCHITECTURE_APPROVAL.md](../quality/P4_G0_OWNER_ARCHITECTURE_APPROVAL.md). Aucune revue tierce revendiquee.

## Contexte

PyLLMKit represente des outils proposes a un LLM. Le fait qu'un modele demande l'utilisation d'un outil ne constitue ni un droit d'execution ni une instruction que le noyau doit executer. Le framework doit rester domain-first et independant de tout provider.

## Decision adoptee

1. Tool et ToolSchema sont des Value Objects descriptifs, immuables en profondeur. Tool contient un nom, une description optionnelle et un schema d'arguments. Aucun callback, fonction Python, callable, commande, endpoint, credential ni objet executable n'est admis dans ces objets.
2. ToolCall represente une demande d'appel observee ou construite, jamais une invocation effective. ToolResult represente uniquement une observation fournie explicitement par le consommateur.
3. La validation de schema, de catalogue local et de correlation est pure, synchrone, deterministe et hors ligne. Elle n'effectue aucun I/O, chargement de secrets, execution, subprocess ou HTTP.
4. Si un executant est necessaire dans un projet consommateur, il appartient a une application ou a un moteur externe, derriere une frontiere explicite. Aucun ExecutorPort n'est requis en M4.
5. Les fonctions de domaine ne produisent ni ToolResult artificiel ni execution reelle. Elles peuvent retourner un rapport de validation ou un nouveau contexte immutable.

## Alternatives ecartees

- Tool avec handler Python : derive agentique et surface d'execution.
- ToolCall auto-executable : confusion entre intention, observation et effet de bord.
- Registry dynamique avec auto-discovery : hors P4, ajoute du couplage infrastructure.

## Consequences et preuves exigees

- L4.1 rejette schemas et definitions incluant des valeurs Python non JSON.
- L4.2 conserve ToolCall distinct de ToolResult et n'invente jamais de resultat.
- Tests d'architecture : aucun import de SDK provider, executor, reseau ou secrets dans domain/tooling.
- Couverture P4-AC-001, 033, 034, 035.
- Integrations agents, permissions et executeurs sont hors scope de M4.

## Risques residuels

Un consommateur pourrait executer lui-meme un appel apres lecture du domaine. Cette decision ne pretend pas securiser cet executant externe. L'autorisation, l'isolation, la traçabilite d'execution et le sandboxing sont des responsabilites distinctes.
