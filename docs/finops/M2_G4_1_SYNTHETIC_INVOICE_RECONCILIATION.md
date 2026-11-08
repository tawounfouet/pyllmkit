# M2-G4.1 - Rapprochement de facture synthetique, hors reseau

- Date : 2026-11-08
- Statut : implementation G4.1 et tests dans la PR #115 ; qualification CI a confirmer.
- **Aucune facture fournisseur reelle n'est verifiee**. Ce gate couvre uniquement la comparaison arithmetique d'une fixture de facture locale, explicitement synthetique.
- Aucun appel API, aucune identification fournisseur, aucun acces secret, aucun mouvement sur le ledger G3 et aucune permission live.

## 1. Perimetre

Le devis pre-generation G2 chiffre les seules composantes declarees et peut omettre des compteurs facturables.

G4.1 compare les **lignes d'usage** d'un fichier de facture synthetique au montant de ce devis. Les **taxes** et **credits** sont comptabilises et presentes separement ; ils ne sont pas fusionnes au sous-total d'usage a comparer.

Contrats du domaine :

- `SyntheticInvoiceLine` (`line_id`, `provider_request_id`, `kind`, `amount`).
- `SyntheticInvoiceStatement` (`statement_id`, identite complete de la route facturante, devise, lignes et origine `synthetic_fixture`).
- `SyntheticReconciliation` : resultat de rapprochement, ecart sur usage, taxes, credits et net.
- `reconcile_synthetic_statement` : fonction pure, immuable, sans effets de bord.
- `parse_synthetic_invoice_statement_json` : parseur strict, doublons de cles JSON rejetes, valeurs `Decimal` transmises exclusivement comme chaines non negatives, maximum 1 Mo et 2 000 lignes.

Aucun faux document externe ne peut se presenter comme `provider_verified` : le seul `source_kind` admissible est `synthetic_fixture`.

## 2. Exemple CLI reproductible

Depuis la branche `feat/m2-finops-v2`, executer apres `git pull` :

```bash
pyllmkit finops reconcile \
  --request examples/finops/scenario.json \
  --pricing-catalog examples/finops/synthetic-prices.json \
  --statement examples/finops/synthetic-invoice.json \
  --provider-request-id fake-provider-call-001
```

Montants attendus dans la fixture (en USD, valeurs **fictives**) :

| Concept | Montant |
|---|---:|
| Devis G2 (usage declare) | 0.051 |
| Facture synthetique - usage | 0.051 |
| Facture synthetique - taxes | 0.010 |
| Facture synthetique - credits | 0.005 |
| Net synthetique | 0.056 |
| Ecart sur usage declare | 0.000 |

Le resultat nominal renvoie `status=matched_synthetic` et `reason=declared_usage_agrees_only`, avec :

```json
{
  "provider_invoice_verified": false,
  "provider_request_correlation": "caller_declared_not_verified",
  "comparison_basis": "declared_usage_subtotal_excluding_taxes_and_credits",
  "budget_ledger_mutated": false,
  "live_authorized": false
}
```

La correspondance de `provider_request_id` dans un fichier local ne constitue **pas une preuve** que le fournisseur a emis une facture ni execute l'appel distant.

## 3. Semantique des verdicts

- `matched_synthetic` : sous-total d'usage synthetique et devis G2 concordants a la tolerance pres. **Uniquement une egalite arithmetique** ; une ligne facture absente ailleurs reste possible.
- `variance_synthetic` : difference explicite entre usage synthetique et devis ; l'ecart est signe.
- `unmatched` : aucune ligne n'a l'identifiant de requete fourni ; montant d'usage `null`, et non `0`.
- `indeterminate` / `quote_not_priced` : absence de tarif G2, comparaison impossible.
- `indeterminate` / `billing_route_mismatch` : divergence du modele, provider API, provider facturant, canal ou devise.
- `indeterminate` / `usage_lines_missing` : lignes liees a la requete, mais aucune ligne d'usage ; ne pas supposer un usage nul.
- Montants de lignes toujours non negatifs. Les credits sont des valeurs positives deduites dans le calcul du **net**, qui peut devenir negatif.

Codes de retour CLI :
- `0` pour `matched_synthetic`, sans autorisation live.
- `3` pour `variance_synthetic`, `unmatched`, `indeterminate` et les refus de validation domaine.
- `2` pour les erreurs I/O.

La tolerance facultative `--tolerance 0.001` utilise un `Decimal` explicite et ne peut etre negative ou non finie.

## 4. Tests et refus

- Exactitude decimale (taxes, credits, ecarts positifs et negatifs, total net negatif possible).
- Echec en cas de route, devise ou identifiant de requete non concordants.
- Distinction du zero declare et de l'absence d'une ligne d'usage.
- Aggregation de plusieurs lignes d'usage d'une meme requete, sans confusion avec une autre requete.
- Unicite de `line_id`, refus d'un champ inconnu, doublon JSON, nombres flottants, NaN, Infinity, tailles excessives.
- CLI complet et idempotence en lecture ; aucun fichier SQLite cree ou modifie.

## 5. Gates manquants avant production

**G4.1 n'est pas un moteur d'import de factures reelles.** Pour aller vers G4.2 et G5, il faudra :

1. Des adaptateurs d'import fournisseur ou exports signes verifiables, provenance et authenticite (pas seulement un `source_kind` declare).
2. Registre append-only des factures et revisions, deduplication inter-imports, conservation des avoirs et historiques.
3. Identifiants de correlation attestes par le fournisseur et application du rapprochement G3 sans double imputation.
4. Gestion explicite des taxes, credits, arrondis, taux de change, frais et compteurs complementaires.
5. Revue des depenses non rapprochees, alertes et resolution manuelle des litiges.
6. Validation de profil de cout exhaustif, hard caps distants et garde avant secrets pour de futures operations payantes.

**GO cible : G4.1 comparaison synthetique offline. NO-GO : facture fournisseur verifiee, debit automatique, live ou production.**
