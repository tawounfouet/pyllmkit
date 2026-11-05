## Contexte et exigences

- Besoin / issue / exigence :
- ADR ou invariants concernes :
- Perimetre et exclusions explicites :
- Base `main` SHA :

## Changement livre

- [ ] Classes, fonctions et contrats nommes dans la documentation
- [ ] Aucun comportement provider/HTTP/outil invente ou laisse implicite
- [ ] Compatibilite des versions de schema verifiee
- [ ] Aucune cle API, token ou donnees sensibles dans le diff

## Tests, qualite et apprentissage

- [ ] Cas positifs et **cas negatifs** pour les invariants
- [ ] Ruff, mypy strict et suite pytest sur Python 3.11, 3.12, 3.13
- [ ] Couverture branches inspectee, pas seulement le pourcentage global
- [ ] Scripts offline et exemples README reellement executables
- [ ] Wheel/sdist clean installs lorsque API, packaging ou docs changent
- [ ] Section enseignements : pattern/DDD/SoC/DIP retenu et alternative rejetee

**URL de CI PR** :

**HEAD SHA de PR** :

## Revue et integration

- [ ] Revue independante si elle est imposee et disponible
- [ ] Verifier le SHA attendu au moment du merge
- [ ] CI push/main SUCCESS sur le commit de fusion exact
- [ ] Liens vers les preuves de logs et jobs mis a jour
- [ ] PV GO/NO-GO separe du commit qui implemente les nouvelles fonctions
- [ ] Pas de publication sans decision explicite

**SHA final de main** :

**URL CI de main** :

**Risques residuels et reservations** :

**Statut reel** : PROPOSE / IMPLEMENTE / TESTE PR / INTEGRE / QUALIFIE / PUBLIE (selectionner seulement le statut etabli).
