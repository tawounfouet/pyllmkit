# PyLLMKit P5 - Streaming API

> Domaine hors reseau, provider-agnostic, Python 3.11+. Version du paquet 0.1.0a2; cible indicative 0.1.0b1 sans release.

## Imports canoniques

from pyllmkit.domain.streaming import ResponseStarted, TextDelta, ToolCallStarted, ToolCallDelta, ToolCallCompleted, UsageUpdated, ResponseCompleted, ResponseFailed, ResponseCancelled, StreamState, StreamStatus, MemoryInferenceStream, MemoryAsyncInferenceStream, consume_stream, consume_async_stream, event_to_dict, event_from_dict, stream_to_dict, stream_from_dict

## Event Model (L5.1)

Tous les evenements sont des objets-valeur immuables. run_id est un InferenceRunId M3 explicite, sequence est un entier exact (pas bool) a partir de 0. TextDelta et ToolCallDelta portent des fragments raw opaques. Les events ne constituent pas des DomainEvent persistants ni des frames SSE.

## Ordre, lifecycle et reconstruction (L5.2 et L5.3)

StreamState est la vue derivee immutable. consume_stream et consume_async_stream valident un debut unique, des positions strictement contigues, la correlation de run, la terminalite. EOF sans terminal donne INCOMPLETE. Un tool call peut recevoir des fragments interleaves par ToolCallId; completed_tool_calls retourne des ToolCall M4 avec ToolArguments.raw, sans parsed. partial_tool_calls reste une observation non finale. Aucun ToolResult ni JSON parse ne sont inventes.

## Sync/async (L5.4)

InferenceStream et AsyncInferenceStream sont des Protocols distincts. StreamingPort.stream(request) retourne Iterator[StreamEvent]; AsyncStreamingPort.astream(request) retourne AsyncIterator[StreamEvent], sans await initial. MemoryInferenceStream et MemoryAsyncInferenceStream sont des fixtures hors ligne. Un consommateur peut limiter max_events et recevra INCOMPLETE tant qu'aucun evenement terminal explicite n'a ete lu. Le caller ferme explicitement les generateurs a ressources si interrompus.

## JSON v1 (L5.5)

event_to_dict/event_from_dict et stream_to_dict/stream_from_dict serialisent des donnees JSON compatibles. Enveloppes et payloads exacts, schema_version entier exact, object_type et kind stricts. Une trace est rejouee avant acceptation pour verifier observed_status, run_id et ordre. Ceci ne parse pas de texte JSON et ne modifie pas les codecs historiques M1-M4.

## Limites

100000 evenements, 8 MiB de texte UTF-8 cumule, 128 tool calls et 1 MiB de raw UTF-8 par appel. Les messages d'erreurs et repr n'affichent pas les fragments. Les proprietes de performance sont testees hors reseau.

## Exemple

Voir examples/18_stream_text_events.py a examples/22_full_streaming_walkthrough.py et tests/acceptance/test_p5_l51_events.py a test_p5_l56_integration.py. Dossier de qualite : docs/quality/PHASE_5_TRACEABILITY.md.

## Hors perimetre

OpenAI, Anthropic, Google, HTTP/SSE, WebSocket, executions tools, auth provider, agents, retries, persistence durable, replay distribue, publication PyPI. Ces capacites necessitent des frontieres explicites et de futures ADR.
