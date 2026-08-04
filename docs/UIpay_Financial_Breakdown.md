# UIpay / Quanta AI — Financial Breakdown

**Currency note:** all figures in NGN, converted at the Aug 4, 2026 mid-market rate of ≈ ₦1,360/$1. USD-denominated services will drift with FX — treat conversions as estimates, not invoiced amounts.

---

## 1. Already paid

| Item | Amount | Notes |
|---|---|---|
| OTP/SMS verification & resend gateway + domain hosting for the two Chateck Holdings websites + other setup costs | **₦140,000** | Paid as a combined total — an itemized per-service split wasn't available at the time of writing; worth pulling the actual receipts/invoices if this needs to break out line-by-line later |

---

## 2. Costs still required

| Item | Provider (feasible example) | Pricing model | Est. cost | Notes |
|---|---|---|---|---|
| Voice SDK (Eagle + Leopard) | Picovoice | Free tier, then custom paid plan | **$0** through the free tier (100–250 min/month per engine — enough for the Sept 21 demo); paid "Growth" tier referenced around **$6,000/year (~$500/mo ≈ ₦680,000/mo)** once past demo scale | Paid tier is quote-based — get an exact number from Picovoice sales before budgeting it in permanently |
| LLM API hosting (text/image/voice intent parsing, Pidgin handling) | Anthropic Claude API (Haiku 4.5) | Usage-based, $1/$5 per million input/output tokens | **~$10–$30/mo (₦13,600–₦40,800/mo)** at dev + demo-scale usage | No fixed hosting fee — this rises with real transaction volume after launch |
| NFC | Native OS APIs (Android HCE / iOS Core NFC) | Free | **₦0** | Current scope is simulated tap-to-pay, which the OS handles natively — no third-party SDK needed. *If UIpay later moves to real contactless card acceptance (EMV), certified SDKs like Stripe Terminal or Square run $25,000–$60,000 in dev cost plus ~$15,000–$50,000/yr in PCI compliance — flagged for awareness only, not in current scope* |
| QR | Self-hosted open-source library (e.g. `qrcode`) | Free | **₦0** | No external API required for basic generation. If a hosted service with dynamic tracking/analytics is preferred instead, entry-level plans run ~$10/mo (₦13,600/mo) |

---

## 3. Estimated totals

| | Low | High |
|---|---|---|
| Already paid (sunk cost) | ₦140,000 | ₦140,000 |
| Additional spend to reach the Sept 21 demo (LLM API testing usage — everything else is $0 at demo scale) | ₦13,600 | ₦40,800 |
| **Total through demo day** | **₦153,600** | **₦180,800** |
| Estimated recurring monthly cost *after* launch, at modest scale (Voice paid tier + LLM + optional hosted QR) | ₦693,600 | ₦734,400 |

The big swing factor post-launch is the Picovoice paid tier — get their actual quote before locking in the monthly recurring number above.
