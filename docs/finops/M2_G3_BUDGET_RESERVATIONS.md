# M2-G3 - Reservations budgetaires durables, atomiques et hors reseau

- Date : 2026-11-08
- Statut : **G3 fondations et CLI offline candidates** sur PR #115
- Limite fondamentale : **aucun appel fournisseur, aucune preuve de plafond distant, aucun budget live**.
- Documentation anterieure : [G1](M2_G1_PRICING_CATALOG_V2.md), [G2](M2_G2_PREFLIGHT_QUOTE.md), [ADR M2](../architecture/ADR-M2-FINOPS-V2.md)

## 1. Decision d'architecture

Le budget de demonstration est conserve en **SQLite local** plutot qu'en JSON modifiable. Chaque mutation est englobee dans une transaction `BEGIN IMMEDIATE`, ce qui evite deux reservations concurrentes du meme budget sur un disque local partage.

- Domaine pur `domain/finops/reservations.py` : `BudgetLedger`, `ReservationRequest`, `BudgetReservation`, `ReservationResult`, `ReservationState`, `BudgetReservationPort`, `quote_fingerprint`.
- Adaptateur `adapters/cli/finops_reserve.py` : `SQLiteBudgetReservationStore`, transactionnel, persistant, montants `Decimal` stockes en texte.
- Commandes `pyllmkit finops budget ...`, `finops reserve`, `finops reservation ...`.
- Les reservations G3 sont des **reservations locales dans un bac a sable**, pas des garanties du cout fournisseur.
- Le tarif reste une hypothese declaree G2. L'utilisateur peut fournir un catalogue synthetique uniquement dans des tests offline.

L'invariant `spent + reserved <= limit` est verifie dans la transaction de mutation, apres verrouillage ecrivain de la base. La devise ne change jamais automatiquement et aucun calcul SQL en flottant n'est utilise.

## 2. Parcours reproductible

Depuis `feat/m2-finops-v2` :

```bash
mkdir -p .pyllmkit

pyllmkit finops budget create \
  --database .pyllmkit/finops-sandbox.db \
  --budget-id sandbox \
  --limit 10.000 \
  --currency USD

pyllmkit finops reserve \
  --database .pyllmkit/finops-sandbox.db \
  --budget-id sandbox \
  --idempotency-key image-demo-001 \
  --request examples/finops/scenario.json \
  --pricing-catalog examples/finops/synthetic-prices.json

pyllmkit finops budget inspect \
  --database .pyllmkit/finops-sandbox.db \
  --budget-id sandbox
```

Le debit hypothetique de l'exemple vaut **0.051 USD**, mais aucune execution payante n'est autorisee.

Recuperer `reservation_id` de la sortie `reserve`, puis inspecter :

```bash
pyllmkit finops reservation inspect \
  --database .pyllmkit/finops-sandbox.db \
  --reservation-id resv_...
```

Deux actions sans reseau sont disponibles :

```bash
# EXCLUSIVEMENT si aucun appel fournisseur n'a ete envoye :
pyllmkit finops reservation release \
  --database .pyllmkit/finops-sandbox.db \
  --reservation-id resv_... \
  --confirm-no-dispatch

# OU : debit fictif, distinct d'une facture :
pyllmkit finops reservation settle-simulated \
  --database .pyllmkit/finops-sandbox.db \
  --reservation-id resv_... \
  --amount 0.041
```

Une issue incertaine (timeout local, crainte d'un dispatch) se marque avec :

```bash
pyllmkit finops reservation dispute \
  --database .pyllmkit/finops-sandbox.db \
  --reservation-id resv_...
```

L'etat `disputed` **conserve** la somme reservee et interdit la liberation manuelle ordinaire.

## 3. Etats et invariants

| Etat | Sens | Montant reserve |
|---|---|---|
| `pending` | Reservation locale active | Integral |
| `disputed` | Issue incertaine, ne pas liberer | Integral |
| `released_undispatched` | Non dispatch prouve dans le cadre offline | Zero |
| `settled_simulated` | Debit synthetique applique au ledger | Zero, debit synthetique conserve en `spent` |

- `release` sur un `pending` exige `--confirm-no-dispatch`; une simple annulation fournisseur ne suffirait jamais.
- `disputed` ne peut pas etre libere via la commande normale.
- `settle-simulated` refuse tout montant superieur au reserve initial ; cela ne prejuge pas d'une facture reelle.
- Les operations terminales rejouees sont idempotentes et les changements d'etat incompatibles sont rejetes.
- Aucun TTL ne libere automatiquement une reservation. Au redemarrage, les `pending` et `disputed` demeurent charges sur le budget.
- Retries ou fallbacks payants ne sont pas branches et ne peuvent donc pas contourner le ledger.

## 4. Idempotence et concurrence

La cle `(budget_id, idempotency_key)` est unique en SQLite. Le fingerprint SHA-256 couvre le contenu canonical complet du devis G2 (`catalog_revision`, `price_id`, fournisseur, parametres, lignes, montants, etc.), le budget, la cle et le but.

- Meme cle + meme contenu = meme `reservation_id`, `replayed=true`, aucun debit additionnel.
- Meme cle + contenu modifie = `reservation_idempotency_conflict`.
- Deux processus (ou threads) sur SQLite local : les ecritures sont serialisees.
- Budget insuffisant : aucune ligne de reservation creee, aucun solde modifie.
- Le ledger n'est ni un systeme distribue ni une source facturee. Ne pas le placer sur un volume NFS / un partage reseau non qualifie.

## 5. Securite et criteres restants

**G3 offline n'est pas G3 live.** Le devis G2 a uniquement `coverage=declared_components_only`. La reservation G3 expose `atomic_budget_reserved`, mais aussi :

```json
{
  "offline_sandbox_only": true,
  "spend_bound_verified": false,
  "provider_quote_verified": false,
  "live_authorized": false
}
```

Avant tout raccordement a `generate --live`, il faut **encore** :

1. Un profil de compteurs exhaustif qualifie par fournisseur, modalite, modele et conditions contractuelles.
2. Une preuve de bornage distant applicable au request payload, une revalidation temporelle et un mecanisme de veto **avant secret**.
3. Un backend budget multi-process et multi-host adapte au deploiement cible, migration et audit durables.
4. Un protocole operationnel de dispatch idempotent, crash/restart, timeout, retry et fallback, sans double facturation supposee.
5. Des preuves G4 d'usage facture, correlation de requetes, taxes, credits et conciliations.
6. Les gates G5 de securite et la certification provider-live independante.

Tests G3 : transactions atomiques, concurrence, reouverture de base, replay idem, conflit d'empreinte, devise, solde, etats `disputed`, `release`, `settle-simulated`, CLI sans acces reseau.

**Verdict cible : GO G3 sandbox offline sous CI, NO-GO G3 live / NO-GO M2 production.**
