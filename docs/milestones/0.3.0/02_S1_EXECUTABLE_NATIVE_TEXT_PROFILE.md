# 0.3.0 - S1 Native Text Profile: first executable conformance slice

> Statut : **IN PROGRESS - S1/G1**, base sur S0 PR #82.
> Issue : [#83](https://github.com/tawounfouet/pyllmkit/issues/83).
> Test : `tests/conformance/test_v030_s1_native_text_profile.py`.
> Les six encodeurs natifs sont invoques comme fonctions pures. **Aucune
> connexion reseau ni invocation d'adaptateur HTTP** n'est realisee ici.

## Objet

S1 cree une premiere coupe de scenarios identiques pour tous les encodeurs
OpenAI Responses, Anthropic Messages, Gemini, xAI Responses, Mistral Chat,
Ollama chat. Cette tranche ne se substitue **pas** au S2 MockTransport
testant les vrais transports et decoders. Elle vise deja une preuve
d'absence de perte silencieuse sur le profil textuel minimal.

## Matrice des scenarios implementes

| ID | Provider x6 | Oracle |
|---|---|---|
| S1-TEXT-01 | 6 codecs texte | `USER` Unicode conserve en payload natif |
| S1-GEN-01 | 6 codecs texte | `max_output_tokens=128` transmis sous son nom natif |
| S1-GEN-02 | 6 services de preparation | Absence de snapshot => refus `generation_support_snapshot_missing`, aucune invocation |
| S1-ROLE-01 | 6 codecs texte | Role `DEVELOPER` conserve chez OpenAI/xAI ; autres refus explicite, sans coercition |

`S1-TEXT-01` et `S1-GEN-01` partagent une fonction de test :
**18 tests parametres** sur six providers (6 nominal + 6 absence de
snapshot + 6 role), et ne prouvent pas la parite de tous les flux HTTP.
La preuve exacte est le resultat CI SHA de la PR.

## Points communs minimaux

- Un message `USER` avec exactement une partie `TextContent`.
- Generation `max_output_tokens` fournie et validee comme `NATIVE`
  pour chaque target.
- Aliases explicites et fakes seulement pour preparer
  `PreparedInvocation` de maniere deterministe.
- Encodage natif effectif, sans HTTP ni cle reelle.
- Parite semantique : texte, ordre et valeur numerique conserves,
  malgre formats de payload natifs differents.

## Restrictions explicitement conservees

- Le role DEVELOPER est serialise par les encoders OpenAI/xAI;
  Anthropic, Gemini, Mistral et Ollama le refusent plutot que le fusionner.
- Anthropic exige `max_output_tokens` dans le profil P7.
- Support des autres options et du multi-message historique encore a
  qualifier dans S4 ; aucun tableau de fournisseur n'est certifie a ce stade.
- Pas de decodage de reponse native ici : S2 fournira des fixtures et une
  projection de `InferenceResponse` y compris `Usage` et `FinishReason`.
- Pas de streaming natif ni de cancellation dans cette coupe : S5/S6.

## Acceptance S1-G1 (partielle)

- [x] Une matrice identique de scenarios est executee pour 6 encodeurs
  natifs, sans duplication de logique test par provider.
- [ ] CI exacte HEAD Python 3.11/3.12/3.13 a valider.
- [ ] Semantique des roles, options et support levels ratifiee.
- [ ] Exemples de rejets NATIVE/UNKNOWN/PARTIAL/UNSUPPORTED completes.
- [ ] Revue independante de ADR-059 et du contrat S1.
- [ ] Decision S1-G1 documentee.

**Gate non encore ferme**. Aucun changement de version ni autorisation
de release `0.3.0`.
