# UIpay / Quanta AI — Product Roadmap

**Status:** Draft for team review · **Owner:** Charles (Project Monitoring & Supervision) · **Last updated:** August 4, 2026
**Hard deadline:** September 21, 2026 — no workstream below extends past this date.

---

## 1. Summary

**Auth & identity is complete.** It closed out ahead of its original Aug 3–7 target, which frees that week's capacity rather than leaving it idle.

**Quanta AI's scope has grown.** Alongside the existing voice pipeline, it now includes an **image-to-text feature**: snapping a photo or screenshot of bank account details (a transfer receipt, a bank app screenshot, a physical card, a printed account details paper) and having Quanta AI extract the account number, bank name, and account name into the same beneficiary/confirmation flow that typed and spoken commands already feed. Because this is genuine added scope, Quanta AI now gets **three dedicated phases — text, image, voice, extending its total footprint to three-plus weeks.

**The plan is now two overlapping tracks, not one straight line.** A *Core Platform* track (wallet/KYC → transfer + admin dashboard → NFC/QR → security → regression) and a *Quanta AI* track (text → image → voice) run concurrently wherever their dependencies allow, rather than each phase waiting for the previous one to fully close out. Auth finishing early is what makes that overlap possible without moving the deadline.This is to ensure everyone finishes as swiftly as possible.

**Already complete, before this roadmap starts:** the MySQL database schema (16 tables), FastAPI/SQLAlchemy models, and Alembic migrations are built and verified against a live database. The full PRD is written and the team's role assignments are mapped to it. The Figma board's Admin/Merchant/User capability breakdown, Auth pages, and tiered-KYC merchant application requirements are folded into the plan below. Spitch has been dropped from the Quanta AI pipeline in favor of direct LLM-based Pidgin handling, which removes an entire cloud-integration workstream that would otherwise have needed its own week.

**Read this roadmap as ambitious, not comfortable.** Taking Auth (done), KYC, wallets, the core transfer flow, a three-phase multimodal Quanta AI (text, image, voice), NFC, QR, and an admin dashboard from "schema exists" to "demo-ready" by Sept 21 is a genuinely tight fit for a five-person team with overlapping roles, even with the extra room this revision creates. Section 5 names the highest-risk phase and what to cut first if time runs short — decide that trade-off now, not in the final weeks.

---

## 2. Timeline at a glance

| # | Phase | Track | Dates | Duration | Owner(s) | Status |
|---|---|---|---|---|---|---|
| 0 | Foundations — DB schema, PRD, role alignment | — | Completed prior to Aug 3 | — | Tonye, Johnny | ✅ Complete |
| 1 | Auth & identity | Core Platform | Completed prior to Aug 3 | - | Johnny, Rufina | ✅ Complete |
| 2 | Wallet, profile, KYC / merchant application | Core Platform | Aug 3 – Aug 14 | 2 wks | Johnny, Rufina, Tonye, Delight | Planned |
| 3 | Core transfer flow + admin dashboard v1 | Core Platform | Aug 12 – Aug 25 | 2 wks  | Johnny, Rufina, Charles | Planned |
| 4A | Quanta AI — text-only intent pipeline (incl. Pidgin) | Quanta AI | Aug 26 – Aug 31 | 1 wk | Ikede Divine, Johnny, Tonye | Planned |
| 4B | Quanta AI — image-to-text bank detail capture | Quanta AI | Aug 31 – Sep 4 | 4 days | Ikede Divine, Tonye | Planned |
| 4C | Quanta AI — voice (Eagle + Leopard) + Pidgin/accent voice validation | Quanta AI | Sep 5 – Sep 16 | 1.5 wks | Ikede Divine, Tonye | ⚠ Highest risk |
| 5 | NFC + QR | Core Platform | Aug 21 – Aug 27 | 6 days | Johnny, Tonye, Delight | Planned |
| 6 | Full security pass | Core Platform | Sep 7 – Sep 11 | 1 wk | Charles | Planned |
| 7 | Regression testing + demo prep | Core Platform | Sep 14 – Sep 18 | 1 wk | Tonye (lead), full team | Planned |
| — | Buffer + demo day | Both | Sep 19 – **Sep 21** | 3 days | Full team | Hard deadline |

---

## 3. Phase-by-phase detail

### Track A — Core Platform

#### Phase 2 (Aug 3–14): Wallet, profile, KYC / merchant application — extended to 2 weeks
**Goal:** a signed-up user has a wallet, a profile, can apply for merchant status, and has an entry point for adding a beneficiary by photo (wired up fully once Phase 4B lands).

- **Backend (Johnny, Tonye):** wallet creation on signup (simulated NUBAN + seeded demo balance), profile update endpoint, transaction-PIN-set endpoint, merchant application endpoint with the individual-vs-organization branching from the board (Name/BVN/Address/Utility Bill/Tier ≤2 vs CAC/BVN/Address/Utility Bill/Tier open), KYC tier assignment, and an endpoint to accept Quanta AI's extracted bank-detail JSON from Phase 4B and stage it for confirm-before-save review.
- **Frontend (Rufina, Delight):** BVN/NIN entry, profile setup, transaction PIN creation, "Application for Merchant" forms for both applicant types, account-created screen, plus a camera-capture / photo-library entry point on the add-beneficiary screen (UI shell here; extraction logic lands in Phase 4B).
- **Testing (Tonye):** starts here — moved up from Phase 3 — running alongside development instead of after it.
- **Why extended:** wallet + KYC alone fit a single week; folding in the new image-intake surface and giving testing room to run concurrently pushes this to two weeks.
- **Milestone:** a user has a live simulated wallet and can submit a merchant application that lands in `merchant_profiles` with `status = pending`.

#### Phase 3 (Aug 12–25): Core transfer flow + admin dashboard v1 — extended to 2 weeks, overlaps Phase 2's final days
**Goal:** the single transfer endpoint every payment method will eventually feed into is working manually, and an admin can act on merchant applications and image-submitted bank details.

- **Backend (Johnny):** the core transfer endpoint (pick beneficiary → amount → confirm → PIN → ledger update → success), beneficiary CRUD, transaction history endpoint.
- **Backend/Frontend (Johnny, Rufina):** admin dashboard v1 — manage users, approve/reject merchant applications, view revenue, transaction counts, ongoing transactions, **plus a review queue for image-submitted bank details flagged by Phase 4B**, using the same approve/edit/reject pattern as merchant applications.
- **Testing (Tonye):** continues — testing the transfer endpoint and admin dashboard as they land, same cadence as Phase 2.
- **Why extended:** the review-queue work needs the same solidity requirement as everything else here. Quanta AI (text, image, voice), NFC, and QR are all just different ways of reaching this same endpoint, so it has to be rock-solid before they build on top of it — that's worth the extra week.
- **Milestone:** manual transfers work end to end, and an admin can approve a merchant application and watch `is_merchant` flip to true. This remains the single most important gate in the whole roadmap.

#### Phase 5 (Aug 21 – Aug 27): NFC + QR
**Goal:** NFC and QR usable end to end, reaching the same confirmation screen as everything else.

- **Backend endpoints (Johnny, Jeffrey):** NFC tag registration and QR code generation were started back in the Aug 10–14 window, in parallel with Phase 4A, since they don't depend on Quanta AI at all — that head start is what buys this phase room to run 1.5 weeks on its own instead of being crammed alongside voice integration.
- **Frontend (Rufina, jeffrey):** NFC tap screen, QR scan screen, merchant inventory management screens.Not just the screens but the endpoints.
- **Milestone:** NFC tap and QR scan both reach the same confirmation screen as manual entry, voice, and image-to-text.

#### Phase 6 (Sep 7–11): Full security pass
**Goal:** the whole app gets a dedicated security review.

- **Charles:** confirm PIN/PIN hashing and BVN/CAC encryption are implemented correctly; confirm there is no path where Quanta AI (text, image, or voice), NFC, or QR can bypass the PIN/biometric confirmation screen; review the on-device/LLM data flow — **now explicitly including image data handling**, since bank-detail photos and screenshots should not be retained any longer than needed to extract and confirm the data.
- **Jeffrey (if time allows, lower priority):** statement generation, push notifications.
- **Milestone:** Charles signs off that no feature — including image-to-text — can move money without PIN/biometric confirmation.

#### Phase 7 (Sep 14–18): Regression testing + demo prep
**Goal:** feature-complete, tested, demo-ready build.

- **Tonye (lead):** full regression pass across every flow built since Phase 1, bug log, edge-case documentation.
- **Full team:** bug-fixing sprint against Tonye's findings.
- **Charles:** final go/no-go sign-off.
- **Demo prep:** seed realistic demo users/beneficiaries/merchants, script the walkthrough (onboarding → beneficiary via text/image/voice/NFC/QR → confirmation → admin review), test on the actual accents and devices used in the live demo.
- **Milestone:** feature-complete build, tested, demo script rehearsed.

#### Buffer (Sep 19–21): Contingency + demo day
Three days held back deliberately, not assigned new feature work. Use it to absorb whatever slipped from Phase 4C or elsewhere. Demo/final delivery happens on or before **September 21**.

---

### Track B — Quanta AI (three dedicated phases)

#### Phase 4A (Aug 26 – 31): Text-only intent pipeline — overlaps Phase 2
**Goal:** reliable intent extraction from typed text, Pidgin included, before any audio or image work starts.

- **Ikede Divine:** LLM-based intent parser (function-calling / structured output) against the `{intent, recipient_nickname, amount, currency}` schema; test harness; 50–100 phrase test set covering standard English, Nigerian-accented phrasing, and Pidgin — tested directly against the LLM, no Spitch translation step.
- **Ikede Divine + Tonye + Johnny:** wire the parser's output to beneficiary fuzzy-matching and auto-navigation to the confirmation screen, still text-only.
- **Dependency:** only needs the beneficiary schema (already in Foundations), not the finished transfer endpoint — that's what lets it start Aug 26.
- **Milestone:** typing a Pidgin phrase like "abeg send my mama Amaka 500 naira" reliably produces the correct structured JSON and pre-fills the confirmation screen.

#### Phase 4B (Aug 31 - Sep 4): Image-to-text bank detail capture — NEW, overlaps Phase 3
**Goal:** snapping a photo or screenshot of bank account details reliably produces the same structured beneficiary data that 4A and voice produce.

- **Ikede Divine:** vision-capable LLM call (image input) against the same beneficiary schema as 4A (`bank_name`, `account_number`, `account_name`); confidence scoring so low-confidence extractions route to mandatory manual review instead of silently auto-filling; a test set of sample screenshots and photos spanning a few Nigerian banks' apps, transfer receipts, and physical cards.
- **Ikede Divine + Tonye + Rufina:** wire extracted output into the same confirmation screen as 4A and voice, with an editable review step before save — OCR/vision extraction on receipts and screenshots won't always be perfect.
- **Rufina:** "scan/upload bank details" entry point on the add-beneficiary screen (camera capture + photo library picker), building on the UI shell from Phase 2.
- **Dependency:** shares the beneficiary schema with 4A; both feed the same downstream confirmation screen owned by Phase 3.
- **Milestone:** snapping a screenshot of a transfer receipt or a photo of a card reliably extracts the correct account number and bank name into the confirmation screen, with anything below the confidence threshold routed to manual edit.

#### Phase 4C (Sep 5 – Sep 16): Voice (Eagle + Leopard) + Pidgin/accent voice validation — ⚠ highest risk, extended to 2 weeks
**Goal:** Eagle and Leopard integrated into the app, and validated against real Pidgin speech, not just typed text.

- **Ikede Divine:** Picovoice Eagle enrollment and verification, Leopard on-device transcription, wired into Phase 4A's pipeline.
- **Ikede Divine + Tonye:** validate Leopard's raw transcription accuracy against real Pidgin recordings, lean on the LLM's own robustness (established in 4A) to recover intent from imperfect transcripts, log every voice attempt to `voice_transaction_logs` for admin review.
- **Why extended:** A big risk part of the project.
- **Milestone:** a voice command completes a transfer for a standard-accented English speaker, and a genuine Pidgin voice command also completes a transfer, within this same phase.

---

## 4. Cross-cutting workstreams (run every phase, not just their "named" phase)

- **Testing & documentation (Tonye):** starts Phase 2 (Aug 3), continues through every phase after — not batched alone.
- **Security (Charles):** the Phase 6 pass is a dedicated deep review, not the only security work — PIN hashing and encryption choices from Phase 2 onward should already follow the bcrypt-for-secrets / encrypt-for-BVN-CAC pattern established in the schema, checked as they're built. Phase 6 now explicitly covers image data handling too.
- **Project monitoring (Charles, Tonye):** weekly check-in against this roadmap. Because Core Platform and Quanta AI now run as parallel tracks, a slip in one shouldn't automatically delay the other — decide track-by-track, that week, what gets cut per Section 5.

---

## 5. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Phase 4C (Eagle/Leopard voice + real Pidgin validation) still slips despite the extra week | Medium | Eagle/Leopard core integration stays non-negotiable; NFC/QR frontend polish (Phase 5) absorbs slippage first — manual transfer (Phase 3) and image-to-text (Phase 4B) both already give the demo working fallback paths into the same confirmation screen |
| Image-to-text (4B) misreads account details from low-quality photos or screenshots (glare, blur, handwriting) | Medium | Confidence-scored extraction: anything below threshold routes to a mandatory manual-edit step before save; a transfer can never be created straight from an image without the standard confirm + PIN step |
| Team capacity assumes near-full-time effort across 5 people | Medium | If this is part-time/alongside coursework, Phases 6–7 are the first place to compress scope, not Phases 1–3 |
| LLM-based Pidgin handling (post-Spitch) underperforms on real speech | Medium | Phase 4C explicitly tests against real Pidgin recordings, not assumed to work from 4A's text-only results alone |
| Merchant application review (Phase 3 admin dashboard) becomes a bottleneck if built late | Low–Medium | Scheduled early and now overlapping Phase 2, so it isn't competing with Quanta AI's voice crunch (4C) later on |
| Running two tracks concurrently strains the 7-person team more than a strictly sequential plan would | Medium | Track ownership is gets disjointed — Ikede Divine owns Quanta AI; Johnny/Rufina/Tonye/Charles own Core Platform — so overlap mostly adds coordination overhead, not double-booked individuals. Flag at the weekly check-in if that stops being true |

---

## 6. Explicitly out of scope for this deadline

Cutting these from the Sept 21 timeline is a deliberate choice, not an oversight — worth stating plainly so nobody assumes they're silently included:

- Real CBN license or BaaS partnership — all transfers remain simulated against the internal ledger.
- Handwriting recognition or non-standard document formats for image-to-text — Phase 4B targets clean digital screenshots and photographed bank cards/printed slips; handwritten notes are not scoped for Sept 21, not yet at least.
- Any integration with card-network agentic-commerce standards (Visa Trusted Agent Protocol, Mastercard Agent Pay) — relevant only once a real BaaS/card partnership exists; logged as a future consideration, not a Sept 21 deliverable.

---

## 7. Milestone checklist

- [x] Auth working end to end, admin login separate from public login — **complete**
- [ ] Wallet + profile + merchant application submission working
- [ ] Manual transfer flow complete; admin can approve/reject merchants and review image-submitted bank details
- [ ] Text-only Quanta AI reliably extracts intent, Pidgin included
- [ ] Image-to-text Quanta AI reliably extracts bank details from photos/screenshots, with manual-edit fallback for low-confidence reads
- [ ] Voice transfer works for standard-accented English and genuine Pidgin; NFC + QR functional
- [ ] Security sign-off complete, including image data handling
- [ ] Full regression pass clean; demo script rehearsed
- [ ] **Sep 21 — Final demo / delivery**
