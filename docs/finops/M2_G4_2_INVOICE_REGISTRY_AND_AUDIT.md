# M2-G4.2 - Registre de factures synthétiques versionné et auditable

- Date : 2026-11-09
- Statut : implémentation candidate sur PR #115, qualification CI à vérifier sur SHA exact.
- Périmètre : **fixtures synthétiques seulement, hors réseau**. Aucune facture fournisseur authentifiée, aucun mouvement sur le budget G3, aucun envoi payant.

## 1. Contrats et stockage

- `domain/finops/invoice_registry.py` : `InvoiceImportRequest`, `ImportedInvoice`, `InvoiceImportResult`, `InvoiceAuditReport`, `InvoiceRegistryPort`, normalisation du snapshot et empreintes SHA-256.
- `adapters/cli/finops_invoice_registry.py` : `SQLiteSyntheticInvoiceRegistry` utilisant `BEGIN IMMEDIATE`, clé unique `(scope_id, import_key)`, clé primaire `(scope_id, statement_id, revision)` et journal local lié par hash.
- Chaque révision enregistre **l'intégralité du snapshot**. Les anciennes versions et les avoirs restent consultables, sans écrasement.
- L'identité du modèle, des fournisseurs API et facturant, du canal et de la devise est stable sur une chaîne de révisions du même relevé. Une correction doit conserver cette identité.
- L'import d'une nouvelle révision exige `revision = latest + 1` et `supersedes = latest`. Le premier import exige `revision = 1` et aucun parent.
- Les montants `Decimal` sont représentés en chaînes. Les montants numériquement équivalents et les lignes présentées dans un autre ordre reçoivent le même snapshot canonique.

## 2. Idempotence et sécurité

- Même `(scope_id, import_key)`, même révision et même contenu : replay, aucun événement supplémentaire.
- Même clé mais contenu, identifiant de relevé ou révision différent : `invoice_import_idempotency_conflict`.
- Révision déjà occupée avec une nouvelle clé : `invoice_revision_already_imported`.
- Correction inchangée : `invoice_revision_unchanged`. Révision omise ou mauvais parent : rejet.
- Les écritures de snapshot et d'événement sont **atomiques dans une seule transaction SQLite**. Une erreur lors de l'écriture d'audit annule l'import entier.
- Déclencheurs SQLite `BEFORE UPDATE/DELETE` bloquent les modifications ou suppressions accidentelles des snapshots et des événements.
- Chaque nouvel événement comporte un `previous_hash` et un `entry_hash` sur l'identité, la clé, la révision, l'empreinte et la date. `audit` recalcule les hashes, vérifie la continuité et les snapshots de toutes les révisions d'un espace.
- **Limite de confiance :** c'est une preuve de cohérence **locale**, pas une signature fournisseur ni un registre inviolable. Un administrateur malveillant capable de réécrire toute la base et la chaîne peut simuler une histoire cohérente. Il manque un ancrage externe et un journal indépendant.
- Le registre doit rester sur un disque SQLite local qualifié, pas sur un partage réseau ou un cluster multi-hôte non certifié.

## 3. Commandes exécutables

Dans la branche `feat/m2-finops-v2` après `git pull` :

```bash
mkdir -p .pyllmkit

pyllmkit finops invoice import-synthetic \
  --database .pyllmkit/finops-invoices.db \
  --scope-id sandbox \
  --statement examples/finops/synthetic-invoice.json \
  --revision 1 \
  --import-key invoice-demo-001

pyllmkit finops invoice inspect \
  --database .pyllmkit/finops-invoices.db \
  --scope-id sandbox \
  --statement-id demo-synthetic-2026-11

pyllmkit finops invoice history \
  --database .pyllmkit/finops-invoices.db \
  --scope-id sandbox \
  --statement-id demo-synthetic-2026-11

pyllmkit finops invoice audit \
  --database .pyllmkit/finops-invoices.db \
  --scope-id sandbox

pyllmkit finops invoice reconcile-imported \
  --database .pyllmkit/finops-invoices.db \
  --scope-id sandbox \
  --statement-id demo-synthetic-2026-11 \
  --request examples/finops/scenario.json \
  --pricing-catalog examples/finops/synthetic-prices.json \
  --provider-request-id fake-provider-call-001
```

Pour importer **une correction synthétique distincte** de ce même relevé :

```bash
pyllmkit finops invoice import-synthetic \
  --database .pyllmkit/finops-invoices.db \
  --scope-id sandbox \
  --statement path/to/modified-synthetic-invoice.json \
  --revision 2 \
  --supersedes 1 \
  --import-key invoice-demo-002
```

Le fichier de correction doit être explicitement préparé. Aucun montant réel n'est inféré, aucune correction n'est appliquée automatiquement, et **les anciennes révisions restent disponibles**.

## 4. Événements et projections

Les projections `import-synthetic`, `inspect`, `history`, `audit` et `reconcile-imported` distinguent la provenance :

```json
{
  "source_kind": "synthetic_fixture",
  "provider_invoice_verified": false,
  "ledger_mutated": false,
  "live_authorized": false
}
```

Le résultat d'audit expose également `external_trust_anchor=false`. Un rapprochement `matched_synthetic` signifie seulement une concordance arithmétique entre un devis G2 et un relevé fictif enregistré.

## 5. Conditions de qualification

- Import initial et replay idempotent, y compris après réouverture de la base.
- Correction en nouvelle révision, avoirs et taxes conservés, historique intact.
- Conflits d'identité, révision et route, blocage d'une correction identique.
- Opérations concurrentes avec la même clé ou sur une même révision.
- Injection d'erreur avant écriture du journal, transaction complètement annulée.
- Déclencheurs contre modifications/suppressions accidentelles, détection de snapshot modifié.
- Audit de tous les événements avec séquence, parent, hashes et empreintes cohérents.
- CLI complète et rapprochement en lecture seule, sans changement du ledger.

## 6. Limites et étapes restantes

Ce G4.2 **ne remplace pas** l'import de factures fournisseurs authentifiées. Restent notamment à faire : vérification cryptographique ou provenance fournisseur attestée, contrôle des doublons inter-export/compte, horodatage et ancrage externe, politiques de rétention, confidentialité, audit des corrections, rapprochement multi-lignes et conversion de devises, imputation G3 strictement sur preuves, gestion de coûts supérieurs au plafond, et validation des limites fournisseur avant live.

**Verdict prévu : GO G4.2 uniquement pour stockage local de fixtures synthétiques après CI ; NO-GO factures réelles / G3 live / production.**
