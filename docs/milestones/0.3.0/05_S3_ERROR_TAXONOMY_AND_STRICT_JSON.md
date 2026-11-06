# PyLLMKit v0.3.0 - S3 Error Taxonomy and Strict Native JSON

> Date : 2026-11-06
> Statut : **S3/G3 EN COURS**, premiere tranche technique.
> Base : S2 streaming [PR #90](https://github.com/tawounfouet/pyllmkit/pull/90)
> Issue : [#85](https://github.com/tawounfouet/pyllmkit/issues/85)
> ADRs : ADR-053 (taxonomie, retries, deadlines), ADR-059 (parite multi-provider)
> Aucune operation live, publication ou changement de version.

## 1. Ecarts detectes par les tests adversariaux

Avant correctif, la nouvelle batterie S3 a revele **14 cas
reproductibles** sur Python 3.11 :

- Deux cas `duplicate_key` (Ollama sync et async) :
  `ollama_mapping.decode_ollama_response` employait `json.loads(raw)`
  sans prevention des cles dupliquees. Un payload synthetique avec deux
  champs `model` identiques etait accepte.
- Douze cas `nonfinite_constant` (6 providers x sync/async) :
  `json.loads` de Python autorise par defaut `NaN`, `Infinity` et
  `-Infinity`, y compris dans des champs natifs non exploites.

Il s'agit d'un ecart d'acceptation du JSON **avant conversion domaine**,
et non d'une decision de representation des six API.

## 2. Correctif de frontiere

Ajout de `adapters/inference/strict_json.py` :

- `decode_provider_json_object(raw: bytes | str)` rejette les racines
  non objet, les cles dupliquees a tous les niveaux, les constantes
  numeriques hors norme et les encodages invalides.
- Le code d'erreur est toujours `provider_protocol_error`, sans
  corps natif dans l'exception publique ni chainage sensible.
- Les six decoders de reponses natifs et
  `native_stream_mapping.decode_native_json` utilisent la meme
  frontiere au lieu de configurations `json.loads` divergentes.
- Les mappers provider-specific conservent leurs regles propres apres
  parsing. Le domaine, les Protocols, M5 et les signatures publiques ne
  changent pas.

La fonction commune est un composant purement **adapter/anti-corruption**,
pas un Value Object de domaine, ni un decoder universel de toutes les
modalites.

## 3. Matrice de tests S3

| Famille | Providers | Modes | Cas | Attendu |
|---|---:|---:|---:|---|
| `ConnectError` | 6 | 2 | 12 | `connection_failure` |
| `ReadTimeout` | 6 | 2 | 12 | `provider_timeout` |
| `ReadError` | 6 | 2 | 12 | `provider_protocol_error` |
| `RemoteProtocolError` | 6 | 2 | 12 | `provider_protocol_error` |
| MIME inattendu | 6 | 2 | 12 | `provider_protocol_error` |
| JSON malforme | 6 | 2 | 12 | `provider_protocol_error` |
| Taille de reponse > 2 MiB | 6 | 2 | 12 | `response_too_large` |
| HTTP 302 | 6 | 2 | 12 | `provider_protocol_error`, aucune redirection |
| Cles JSON dupliquees | 6 | 2 | 12 | `provider_protocol_error` |
| `NaN` natif | 6 | 2 | 12 | `provider_protocol_error` |
| **Total croise** | | | **120** | Une seule tentative, erreur sure |
| Unitaires parser | - | - | **20** | Invalides/imbriques + validite |

La campagne commune est executee contre les vrais adapteurs HTTP
avec `httpx.MockTransport`. Tous les identifiants et secrets sont
synthetiques. Chaque cas d'echec compte les requetes : exactement une,
aucun retry/failover.

## 4. Resultats attendus et preuve

- [x] Nouveaux tests adversariaux en rouge avant correctif.
- [x] Correctif partage de parsing strict dans les sept decodeurs.
- [x] Tests unitaires de rejet et de validite du parser.
- [ ] CI exacte sur SHA final, Python 3.11, 3.12, 3.13.
- [ ] Artefacts conformance JSON/Markdown complets, matrice S3 incluse.
- [ ] Aucun echec des anciens tests P7 ni baisse des seuils coverage.
- [ ] Revue independante du traitement d'erreurs, des limites et de la
  non-divulgation de donnees.
- [ ] Arbitrage G3 explicite, non deduit d'une CI verte.

## 5. Limites et suite

Le parser strict s'applique aux reponses textuelles des six codecs et
aux trames de streaming de la Phase 7. Il n'est pas une assurance de
protection contre tout payload volumineux ou profond ; les limites
HTTP/wire, les timeouts et les controles de securite des connexions
restent des gates distincts. Cette tranche ne modifie pas la politique
de retries `max_attempts=1`, ne corrige pas les protections main
(#22) ni la verification DNS/peer-IP/TLS live (#36 et #81).

**Decision S3-G3 : PENDING** tant que preuves et revue ne sont pas
archivees. **Version `0.3.0` : jalon cible, pas une release.**
