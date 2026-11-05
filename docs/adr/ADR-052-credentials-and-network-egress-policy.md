# ADR-052 - Secrets, endpoints et politique réseau

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0, non encore accepté par le propriétaire
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

CredentialRef est une référence opaque d'infrastructure résolue juste avant l'appel par CredentialResolverPort. ProviderConnectionConfig valide host, scheme, port, TLS, redirections, timeouts, résolution DNS et source du secret. Cloud: domaines officiels approuvés par défaut, HTTPS vérifié; endpoint alternatif seulement dans allowlist explicite, sans redirection traversant la politique. Ollama: exception loopback locale 127.0.0.1 et ::1 uniquement après choix explicite; LAN et metadata IP refusés par défaut.

## Conséquences et invariants

Protéger les rebinding DNS et les IP privées/interdites suivant la politique de destination, en validant l'adresse utilisée à la connexion, pas seulement le nom avant celle-ci. Les secrets et prompts ne sont pas journalisés, ni affichés dans repr, exceptions, traces ou artifacts. Le profil réseau est fail-closed.

## Alternatives rejetées ou reportées

URL libre fournie par un EndpointId; TLS désactivé implicitement; HTTP redirects par défaut; secrets directement dans les Value Objects.

## Vérification requise

P7-AC-012..015, 052..055; tests SSRF, metadata, redirect, DNS et canaris de fuite; vérification sans réseau réel.

## Gouvernance

Ce texte fixe une proposition de contrat, et non une preuve d'implémentation. L'acceptation requiert la décision explicite du propriétaire sur la PR documentaire P7-G0, une analyse de sécurité et la CI post-merge sur le SHA exact de main. Aucun code provider ni test réseau n'est autorisé par la seule création de l'ADR.
