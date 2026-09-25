# Quanta AI — Step 14 & Step 15 Transfer & Confirmation Architecture

## Overview

Steps 14 and 15 establish the complete transfer-preparation and confirmation lifecycle for Quanta AI.

The architecture deliberately separates:

1. **LLM reasoning** — determining the user's intent and requesting appropriate tools.
2. **Quanta domain governance** — validating transfer data, enforcing invariants, maintaining state, and managing confirmation.
3. **UI Pay authorization and execution** — handling PIN/authentication and ultimately executing the financial transaction.

The fundamental security principle is:

> **LLM proposes. Quanta validates and governs. UI Pay authorizes and executes.**

Quanta must never treat an LLM-generated transfer argument, confirmation phrase, beneficiary name, or account name as authoritative without deterministic validation.

---

## 1. Scope of Steps 14 and 15

### Step 14 — Complete Transfer Workflow

Step 14 completes the transfer preparation path up to a pending confirmation.

```text
User Request
    ↓
LLM Intent / Tool Reasoning
    ↓
Beneficiary Resolution
    ↓
Account Validation
    ↓
Amount Parsing + Validation
    ↓
TransferContext / TransferGuard
    ↓
prepare_transfer
    ↓
UI Pay Prepared Reference
    ↓
Confirmation Creation
    ↓
AWAITING_CONFIRMATION
```

Step 14 does **not** execute a transfer.

### Step 15 — Deterministic Confirmation Workflow

Step 15 handles the user's response to the pending transfer confirmation.

```text
AWAITING_CONFIRMATION
        │
        ├── CONFIRM
        │      ↓
        │   CONFIRMED
        │      ↓
        │   UI Pay Authorization / PIN
        │      ↓
        │   EXECUTING
        │      ↓
        │   SUCCESS / ERROR
        │
        ├── CANCEL
        │      ↓
        │   CANCELLED
        │
        ├── MODIFY
        │      ↓
        │   Invalidate Existing Confirmation
        │      ↓
        │   PROCESSING
        │      ↓
        │   New Preparation Required
        │
        └── EXPIRE
               ↓
            EXPIRED
```

Confirmation is therefore **not equivalent to execution**.

A user's confirmation means:

> "I approve these exact prepared transfer details."

It does not mean:

> "The transfer has been executed."

The user must still pass the UI Pay authorization/PIN boundary before execution can occur.

---

# 2. Architectural Boundaries

## 2.1 Quanta Responsibilities

Quanta may:

* interpret user intent;
* resolve beneficiaries;
* parse monetary expressions;
* validate transfer amounts;
* validate account information through UI Pay;
* prepare transfers;
* create and manage confirmation records;
* detect confirmation, cancellation, modification, and ambiguity;
* enforce transfer invariants;
* prevent stale or replayed confirmations;
* request UI Pay authorization.

Quanta must not:

* execute transfers directly;
* expose an `execute_transfer` LLM tool;
* invent account holder names;
* trust LLM-provided account names;
* treat an arbitrary confirmation phrase as authorization for a changed transfer;
* allow an expired or consumed confirmation to be reused;
* allow confirmation of a different amount or beneficiary than the prepared transfer.

## 2.2 UI Pay Responsibilities

UI Pay remains authoritative for:

* authentication;
* beneficiary ownership;
* account validation;
* authoritative account holder name;
* transaction authorization;
* PIN verification;
* final transfer execution;
* final transaction result.

The final financial execution boundary therefore remains:

```text
Quanta
    ↓
UI Pay Authorization / PIN
    ↓
UI Pay Transfer Execution
```

---

# 3. Domain Architecture

The domain layer contains deterministic business rules that should not depend on the LLM provider.

Recommended structure:

```text
app/
├── domain/
│   ├── transfer/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── amount.py
│   │   ├── context.py
│   │   └── guard.py
│   │
│   └── confirmation/
│       ├── __init__.py
│       ├── model.py
│       ├── manager.py
│       ├── store.py
│       └── resolver.py
│
├── tools/
├── providers/
├── services/
├── orchestration/
└── routers/
```

If equivalent modules already exist, reuse/refactor them rather than creating duplicate implementations.

The domain layer must not contain provider-specific LLM logic.

---

# 4. Transfer Domain

## 4.1 AccountValidator

Location:

```text
app/domain/transfer/account.py
```

`AccountValidator` is a deterministic domain/service component.

The LLM-facing operation remains the `validate_account` tool.

Responsibilities:

* validate structural account-number requirements;
* reject malformed account numbers;
* invoke UI Pay for authoritative account validation;
* receive the authoritative account name from UI Pay;
* return validated account information to the transfer workflow.

Security rule:

> The LLM must never invent, infer, or override the authoritative account holder name.

The account name displayed in a confirmation must originate from the validated UI Pay result.

Do not duplicate UI Pay's full business validation logic inside Quanta.

---

# 5. Amount Validation

Location:

```text
app/domain/transfer/amount.py
```

Amount handling must separate **parsing** from **validation**.

### Parsing

The parser may interpret expressions such as:

```text
10k
10 k
10 thousand
10 grand
10 boi
₦10,000
dubu goma
puku iri
egberun mewa
```

Examples:

```text
10k             → 10000
10 thousand     → 10000
10 boi          → 10000
₦10,000         → 10000
```

### Validation

The validator must enforce deterministic business requirements:

* amount must be an integer monetary value;
* amount must be greater than zero;
* currency must resolve to NGN for the current Quanta transfer scope;
* configured transaction limits must be respected when present;
* invalid or unsupported amounts must produce a validation result/error rather than relying on Python `assert`.

Do not use:

```python
assert amount > 0
```

for business validation.

Use explicit validation and domain errors instead.

---

# 6. TransferContext

`TransferContext` represents the application's authoritative understanding of the current transfer.

It exists to prevent stale or hallucinated LLM arguments from overriding the latest validated user intent.

Relevant fields may include:

* user ID;
* session ID;
* beneficiary ID;
* account number;
* bank identifier/name where required;
* authoritative account name;
* amount;
* currency;
* prepared reference.

Only the minimum necessary sensitive data should be retained.

The latest explicit user transfer details must replace stale values.

For example:

```text
User: Send Dad ₦10,000
    ↓
TransferContext:
    beneficiary = Dad
    amount = 10000

User: Actually send Mum instead
    ↓
TransferContext:
    beneficiary = Mum
    amount = 10000
```

The old Dad transfer must never be resurrected later.

Likewise:

```text
User: Send Mum ₦10,000
User: Actually make it ₦20,000
```

must result in:

```text
amount = 20000
```

and require a new preparation/confirmation.

---

# 7. TransferGuard

Location:

```text
app/domain/transfer/guard.py
```

`TransferGuard` enforces transfer invariants immediately before sensitive transfer operations.

It must verify, as applicable:

* authenticated user ownership;
* session consistency;
* valid beneficiary;
* validated account;
* authoritative account name;
* valid positive amount;
* correct currency;
* current transfer state;
* current TransferContext;
* prepared reference consistency;
* confirmation consistency;
* no stale transfer data;
* no execution through Quanta.

The guard must never rely on `assert`.

Failures must produce explicit domain/application errors.

---

# 8. prepare_transfer

`prepare_transfer` remains the final Quanta-side transfer preparation tool.

It must:

* validate its input through the ToolExecutor/domain layer;
* use authoritative TransferContext values;
* never blindly trust the arguments supplied by the LLM;
* call the UI Pay preparation endpoint/client;
* receive a prepared transfer reference;
* return the prepared transfer information.

The tool does **not** execute the transaction.

There is intentionally no:

```text
execute_transfer
```

tool in the LLM registry.

---

# 9. Prepared Reference Binding

The UI Pay prepared reference is an important part of confirmation integrity.

Example:

```json
{
  "prepared_reference": "prep_abc123",
  "beneficiary_id": "ben_001",
  "amount": 10000,
  "currency": "NGN"
}
```

The confirmation created from this preparation must be bound to those exact transfer details.

A confirmation must not be treated as a generic authorization for any transfer.

Conceptually:

```text
prepared_reference
        +
beneficiary_id
        +
amount
        +
currency
        ↓
confirmation fingerprint
```

The fingerprint may be generated from canonicalized transfer fields using a deterministic cryptographic hash such as SHA-256.

Do not log sensitive account information merely to create or debug the fingerprint.

If the prepared reference, beneficiary, amount, or currency no longer matches the confirmation, the confirmation must be rejected and a new transfer preparation/confirmation must be required.

---

# 10. Confirmation Domain

Location:

```text
app/domain/confirmation/
```

The confirmation domain manages the temporary authorization intent created after successful transfer preparation.

It is separate from the application's global state machine.

## 10.1 Global Application State

The global lifecycle remains:

```text
PROCESSING
    ↓
AWAITING_CONFIRMATION
    ↓
EXECUTING
    ↓
SUCCESS / ERROR
```

## 10.2 Confirmation State

The confirmation object has its own lifecycle:

```text
PENDING
    ↓
CONFIRMED
    ↓
CONSUMED

PENDING → CANCELLED
PENDING → EXPIRED
```

`INVALID` may be used as a terminal state where an existing confirmation can no longer be trusted because its required invariants have failed.

These two state systems must not be conflated.

---

# 11. Confirmation Statuses

## PENDING

A confirmation has been created after successful transfer preparation and is awaiting the user's decision.

## CONFIRMED

The user has provided a valid confirmation intent for the exact pending transfer.

`CONFIRMED` does **not** mean the transfer is executing.

It means the user's confirmation gate has been passed and the application may proceed to the UI Pay authorization/PIN boundary.

## CONSUMED

The confirmation has been used to cross the authorization boundary and cannot be replayed.

A consumed confirmation must never authorize a second attempt.

## CANCELLED

The user explicitly rejected/cancelled the pending operation.

## EXPIRED

The confirmation's TTL elapsed before it was successfully consumed.

## INVALID

The confirmation failed a required integrity or ownership check, such as:

* wrong user;
* wrong session;
* stale confirmation;
* mismatched prepared reference;
* changed amount;
* changed beneficiary;
* changed currency;
* invalid lifecycle transition.

---

# 12. Confirmation Model

The confirmation model should contain the minimum information required to securely identify the pending operation.

Conceptually:

```text
confirmation_id
request_id
user_id
session_id
operation
amount
currency
beneficiary_id
prepared_reference
fingerprint
created_at
expires_at
status
confirmed_at
consumed_at
cancelled_at
```

Do not unnecessarily store raw sensitive account information.

The confirmation is an opaque server-side record. The frontend should not be able to alter its underlying transfer details.

---

# 13. ConfirmationStore

The confirmation storage layer should be abstracted.

Example interface:

```text
create()
get()
update()
find_latest_pending()
transition()
```

An explicit atomic transition operation is preferred over unrestricted mutation:

```text
transition(
    confirmation_id,
    expected_status,
    new_status
)
```

This helps prevent accidental double-confirmation or replay.

## Prototype Implementation

Use:

```text
InMemoryConfirmationStore
```

for the current prototype.

It should be safe for concurrent access within the running application process.

This is **not equivalent to production Redis persistence**.

The in-memory store is acceptable because the current prototype does not require:

* distributed workers;
* process-restart persistence;
* cross-instance coordination.

The store abstraction allows a future implementation such as:

```text
RedisConfirmationStore
```

without changing the confirmation manager or domain rules.

---

# 14. ConfirmationManager

The manager owns confirmation lifecycle operations:

```text
create()
validate()
confirm()
cancel()
expire()
consume()
```

### create()

Creates a pending confirmation only after successful transfer preparation.

### validate()

Checks:

* ownership;
* session;
* status;
* TTL;
* prepared reference;
* fingerprint;
* transfer details.

### confirm()

Performs:

```text
PENDING → CONFIRMED
```

It must not transition the application directly to `EXECUTING`.

### cancel()

Performs:

```text
PENDING → CANCELLED
```

and prevents further use.

### expire()

Performs:

```text
PENDING → EXPIRED
```

when the TTL has elapsed.

### consume()

Performs:

```text
CONFIRMED → CONSUMED
```

and prevents replay.

Consumption must be guarded against repeated attempts.

---

# 15. Confirmation and PIN Boundary

The critical sequence is:

```text
User says "yes"
        ↓
ConfirmationResolver
        ↓
CONFIRM
        ↓
ConfirmationManager.confirm()
        ↓
TransferGuard.validate_confirmation()
        ↓
ConfirmationManager.consume()
        ↓
UI Pay authorization / PIN
        ↓
PIN accepted
        ↓
UI Pay executes transfer
```

Quanta must not interpret:

```text
"yes"
```

as:

```text
EXECUTE TRANSFER
```

It means:

```text
USER CONFIRMED THIS PREPARED TRANSFER
```

The UI Pay authorization layer remains responsible for requiring and validating the user's PIN/authentication.

---

# 16. Confirmation Intent Resolver

Location:

```text
app/domain/confirmation/resolver.py
```

The resolver converts the user's confirmation response into:

```text
CONFIRM
CANCEL
MODIFY
AMBIGUOUS
OTHER
```

It must operate only as an **intent classifier**.

It must never execute a transfer.

## Resolution Strategy

### Layer 1 — Ambiguity

Questions and uncertain statements should not authorize a transfer.

Examples:

```text
run am?
should I send it?
maybe
hmm
not sure
```

Result:

```text
AMBIGUOUS
```

The pending confirmation remains active.

### Layer 2 — Modification

Modification takes precedence over confirmation.

Examples:

```text
yes, make it 20k
sharp, but send it to Mum instead
run am, change the amount to 15k
yes but use Dad instead
```

Result:

```text
MODIFY
```

The existing confirmation must not be consumed.

The current transfer preparation must be invalidated/restarted as appropriate.

A changed transfer requires a new preparation and new confirmation.

### Layer 3 — Cancellation

Explicit cancellation must never be interpreted as confirmation.

Examples:

```text
don't send it
cancel it
stop
no send am
abeg no
leave am
```

Result:

```text
CANCEL
```

### Layer 4 — Explicit Confirmation

Examples:

```text
yes
confirm
confirmed
proceed
go ahead
okay
approved
sharp
sharp sharp
run am
run am for me
run am for me abeg
fire down
correct
correct no dulling
no wahala run am
```

Result:

```text
CONFIRM
```

### Layer 5 — Contextual / Colloquial Confirmation

Natural Nigerian expressions may be interpreted as confirmation only when a valid pending confirmation exists.

Examples include:

```text
you too much, fire down
oya send am
make you send am
abeg run am
run am sharp sharp
```

The resolver must not treat such phrases as a transfer authorization when no pending confirmation exists.

---

# 17. Multilingual Confirmation Support

The resolver should support Nigerian English, Pidgin, Yoruba, Hausa, and Igbo.

Examples:

### Yoruba

Confirmation:

```text
bẹẹni
bẹ́ẹ̀ni
tẹsiwaju
tẹ́síwájú
ṣe e
jẹ́ kó lọ
o tọ
ó dáa
ko si wahala
lọ síwájú
```

Cancellation:

```text
rárá
rara
fagilé
fagilé e
má ṣe ránṣẹ́
má ṣe rán an
dá dúró
má tẹsiwaju
mo ti yí ọkàn mi padà
```

### Hausa

Confirmation:

```text
eh
eh, ci gaba
ci gaba
ci gaba da shi
eh, aika
eh, aika shi
yi hakan
yi shi
to
to, ci gaba
da kyau
shikenan
babu matsala
mu ci gaba
```

Cancellation:

```text
a'a
aa
a'a, kar ka aika
kar a aika
kar ka aika
kar ki aika
kar a tura
daina
daina shi
bar shi
bar wannan
ka dakata
ki dakata
mu dakata
kar a ci gaba
na canza ra'ayi
```

### Igbo

Confirmation:

```text
ee
ee, gaa n'ihu
gaa n'ihu
mee ya
mee nke a
zipụ ya
ka zipụ ya
ọ dị mma
ọ dị mma, gaa n'ihu
enweghị nsogbu
ka anyị gaa
```

Cancellation:

```text
mba
mba, kagbuo ya
kagbuo
kagbuo ya
ezipụla ya
akagbula ya
kwụsị
kwụsị ya
ka anyị kwụsị
emela ya
emela nke a
achọghị m ya
```

### Nigerian Pidgin

Confirmation:

```text
yes na
yes abeg
oya go
oya do am
do am
send am
make e go
make we run am
no wahala
no wahala, run am
e correct
na correct
run am sharp sharp
fire am down
```

Cancellation:

```text
abeg no
abeg no send am
no send am
no run am
no do am
make you stop am
stop am
leave am
forget am
make we leave am
hold on
wait first
no be this one
i don change my mind
cancel am abeg
```

These phrases are examples rather than an exhaustive dictionary.

The resolver should be designed so additional phrase families can be added without modifying confirmation lifecycle logic.

---

# 18. Cancellation and Confirmation Must Be Contextual

A phrase must not be treated as a financial command merely because it appears in the phrase dictionary.

For example:

```text
"send am"
```

may be:

* a new transfer instruction when no confirmation exists;
* a confirmation response when a transfer is already pending.

Therefore:

```text
NO PENDING CONFIRMATION
    ↓
normal Quanta orchestration

PENDING CONFIRMATION
    ↓
ConfirmationResolver
```

This prevents confirmation phrases from becoming an unintended transfer execution mechanism.

---

# 19. Response Contract

When transfer preparation succeeds:

```json
{
  "request_id": "req_123",
  "status": "confirmation_required",
  "speech": {
    "text": "Confirm transfer of ten thousand naira to Amaka Okafor."
  },
  "ui": {
    "type": "transfer_confirmation"
  },
  "data": {
    "confirmation_id": "conf_abc123",
    "amount": 10000,
    "currency": "NGN",
    "beneficiary": {
      "id": "ben_001",
      "name": "Amaka Okafor",
      "bank_name": "GTBank",
      "account_number_masked": "******6789"
    }
  },
  "error": null
}
```

The `data` object exists primarily to give the UI enough information to display the confirmation.

The backend confirmation record remains authoritative.

The frontend must not be able to modify:

* amount;
* beneficiary;
* prepared reference;
* currency.

---

# 20. No Generic `navigate_to` Field Yet

Do not introduce a generic:

```json
"navigate_to": "/transfer/pin"
```

field at this stage.

That would couple the Quanta response contract to frontend route implementation.

The existing UI contract:

```text
ui.type
```

is sufficient.

For example:

```text
transfer_confirmation
```

means the frontend should render its transfer confirmation experience.

Later, if the product requires a standardized cross-platform navigation/action contract, it can be introduced deliberately rather than coupling Quanta to React Native Web routes now.

---

# 21. Modification Handling

A confirmation is bound to the exact prepared transfer.

Therefore:

```text
"yes, make it ₦20,000"
```

is not confirmation.

It is:

```text
MODIFY
```

The old confirmation must not authorize the new amount.

Likewise:

```text
"yes, send it to Mum instead"
```

must not confirm the previous beneficiary.

The correct flow is:

```text
MODIFY
    ↓
invalidate old confirmation
    ↓
update TransferContext
    ↓
PROCESSING
    ↓
validate new transfer
    ↓
prepare new transfer
    ↓
create new confirmation
    ↓
AWAITING_CONFIRMATION
```

---

# 22. Security Invariants

The implementation must enforce the following:

1. No `execute_transfer` tool exists.
2. LLM arguments are never trusted as authoritative transfer data.
3. Account names come from UI Pay validation.
4. Amounts are explicitly validated.
5. Python `assert` is not used for business/security validation.
6. Beneficiaries are scoped to the authenticated user.
7. Confirmation records are user/session bound.
8. Confirmation records are operation bound.
9. Confirmation records are bound to the prepared transfer.
10. Amount changes invalidate the previous confirmation.
11. Beneficiary changes invalidate the previous confirmation.
12. Prepared-reference mismatches invalidate confirmation.
13. Expired confirmations cannot be confirmed.
14. Cancelled confirmations cannot be confirmed.
15. Consumed confirmations cannot be replayed.
16. Confirmation does not equal execution.
17. PIN/authentication remains a UI Pay responsibility.
18. Quanta never receives or exposes the user's PIN to the LLM.
19. Ambiguous confirmation language never authorizes a transfer.
20. Colloquial confirmation phrases are interpreted only in the context of an active pending confirmation.

---

# 23. Tests

Step 14 and Step 15 should have focused unit and integration tests.

Recommended coverage:

```text
tests/
├── domain/
│   ├── transfer/
│   │   ├── test_account.py
│   │   ├── test_amount.py
│   │   ├── test_context.py
│   │   └── test_guard.py
│   │
│   └── confirmation/
│       ├── test_model.py
│       ├── test_store.py
│       ├── test_manager.py
│       └── test_resolver.py
│
├── tools/
│   └── test_transfer.py
│
└── orchestration/
    └── test_transfer_flow.py
```

At minimum test:

### Transfer

* valid beneficiary;
* unknown beneficiary;
* missing bank/account;
* invalid account number;
* authoritative account name;
* valid amount;
* zero amount;
* negative amount;
* malformed amount;
* `10k`;
* `10 thousand`;
* `10 boi`;
* Nigerian-language amount expressions already supported;
* latest amount replaces stale amount;
* latest beneficiary replaces stale beneficiary;
* stale LLM amount cannot override TransferContext;
* prepare result contains prepared reference.

### Confirmation

* creation;
* retrieval;
* expiry;
* confirmation;
* cancellation;
* consumption;
* double consumption;
* invalid ownership;
* invalid session;
* prepared-reference mismatch;
* amount mismatch;
* beneficiary mismatch;
* fingerprint mismatch;
* invalid state transition.

### Confirmation language

Test:

```text
yes
confirm
go ahead
sharp
sharp confam
run am for me abeg
you too much, fire down
correct no dulling
```

as confirmation when pending.

Test:

```text
no
cancel
don't send it
abeg no send am
leave am
stop am
```

as cancellation.

Test:

```text
run am?
maybe
should I?
hmm
```

as ambiguous.

Test:

```text
yes, make it 20k
sharp, send to Mum instead
run am but change the amount
```

as modification.

Test all supported Hausa, Yoruba, Igbo, and Pidgin phrase families.

Also test that these phrases **do not perform confirmation when there is no pending confirmation**.

---

# 24. Acceptance Criteria

Step 14 and Step 15 are complete when:

* a valid transfer can be prepared end-to-end;
* unknown beneficiaries trigger only the missing information request;
* accounts are validated through UI Pay;
* authoritative account names are preserved;
* amounts are deterministically parsed and validated;
* TransferContext prevents stale LLM arguments from overriding current values;
* prepare_transfer produces a prepared reference;
* confirmation is bound to the prepared transfer;
* a confirmation response creates `CONFIRMED`, not `EXECUTING`;
* UI Pay PIN/authorization remains the execution boundary;
* consumed confirmations cannot be replayed;
* cancelled confirmations cannot be reused;
* expired confirmations cannot be reused;
* modified transfers require new preparation and confirmation;
* colloquial and multilingual confirmation/cancellation phrases are recognized;
* ambiguous responses do not authorize or cancel accidentally;
* the response contract contains enough transfer data for the frontend confirmation UI;
* no generic frontend `navigate_to` field is required;
* no Redis or database is introduced;
* no `execute_transfer` tool exists;
* no PIN is exposed to the LLM;
* existing provider, OCR, ASR, and TTS functionality remains unaffected.

---

# 25. Out of Scope

Do not implement in Steps 14–15:

* real transfer execution;
* production Redis;
* database-backed confirmation persistence;
* frontend route implementation;
* React Native Web navigation changes;
* PIN handling inside Quanta;
* TTS changes;
* OCR changes;
* ASR changes;
* Quanta API redesign;
* Quanta Proxy integration;
* production deployment;
* transaction-history intelligence.

Those belong to later roadmap stages.

---

## Final Architecture

The completed architecture should be understood as:

```text
                         ┌─────────────────────┐
                         │       Claude        │
                         │ Intent / Tool Call  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    ToolExecutor     │
                         │ Policy / Auth /     │
                         │ Validation          │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┴──────────────────┐
                  │                                    │
                  ▼                                    ▼
        ┌───────────────────┐                ┌────────────────────┐
        │ Transfer Domain   │                │ Confirmation Domain│
        │                   │                │                    │
        │ AccountValidator  │                │ Manager            │
        │ AmountValidator   │                │ Store              │
        │ TransferContext   │                │ Resolver           │
        │ TransferGuard     │                │ Model              │
        └─────────┬─────────┘                └──────────┬─────────┘
                  │                                     │
                  ▼                                     ▼
        ┌───────────────────┐                ┌────────────────────┐
        │ prepare_transfer  │───────────────▶│ PENDING            │
        └─────────┬─────────┘                └──────────┬─────────┘
                  │                                     │
                  │                                     ▼
                  │                                CONFIRMED
                  │                                     │
                  │                                     ▼
                  │                            UI Pay Authorization
                  │                                  / PIN
                  │                                     │
                  │                                     ▼
                  │                                EXECUTING
                  │                                     │
                  │                                     ▼
                  │                              SUCCESS / ERROR
                  │
                  ▼
             UI Pay Backend
        (authoritative validation
          and preparation)
```

The core boundary remains:

> **Quanta can decide that a transfer is ready for confirmation. Quanta can verify that the user confirmed that exact transfer. Quanta cannot turn that confirmation into financial execution. UI Pay owns authorization and execution.**
