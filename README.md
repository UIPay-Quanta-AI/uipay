# UiPay

## Overview
UiPay is a fintech web app (plus two companion websites) that lets users send and receive money through multiple payment methods, including an AI voice-command feature. It's being built as a functional prototype with a simulated banking backend (mock wallets, ledger, KYC) ahead of real BaaS/licensing integration.

## Features
- **Onboarding & KYC (mocked)** — phone/OTP verification, BVN/NIN entry, PIN creation, optional voice biometric enrollment
- **Wallet management** — simulated ledger with demo balances
- **Core transfers** — send money to saved beneficiaries with PIN/biometric confirmation
- **Quanta AI (voice payments)** — speak a command (e.g. "send mama Amaka 500 naira"); speech is transcribed, matched to a beneficiary, and pre-fills the transfer confirmation screen. Includes voice-identity verification and support for Pidgin/Nigerian-accented English
- **NFC tag payments** — tap-to-pay using merchant-registered NFC tags
- **QR code payments** — static and dynamic QR codes for merchant payments
- **Transaction history & notifications** — in-app history plus push notifications
- **Airtime/data/bills** *(optional/demo)* — simulated bill payments via sandbox aggregators

## Tech Stack

| Layer     | Technology       | Suggested Version |
|-----------|------------------|--------------------|
| Backend   | NestJS           | v11.x (latest: 11.1.28) |
| Database  | PostgreSQL       | v16.x (stable) or v18.4 (latest) |
| Runtime   | Node.js          | v20 LTS or v24+ (required for NestJS v11 ESM support) |

## Prerequisites

- Node.js (v20 LTS or v24+)
- npm or yarn
- PostgreSQL (v16+ recommended)
- Git

## Getting Started

### 1. Clone the repository
```bash
git clone <repository-url>
cd uipay
```

### 2. Install dependencies
```bash
npm install
```

### 3. Configure environment variables

NOTE: DATABASE_URL=postgresql://<user>:<password>@localhost:5432/uipay

### 4. Run the app
```bash
npm run start:dev
```

## Git Workflow

To keep `main` clean and avoid merge conflicts, follow this workflow for every task:

1. **Clone the repo locally** (if not already done).
2. **Pull the latest `main`** before starting any work:
```bash
   git checkout main
   git pull origin main
```
3. **Create a new branch** named after the feature/fix you're working on:
```bash
   git checkout -b feature/<short-description>
```
   Example: `feature/payment-gateway-integration`, `fix/login-validation`

4. **Work on your code** and commit changes regularly with clear messages.

5. **Pull `main` again before pushing**, to catch any changes made by others while you were working:
```bash
   git checkout main
   git pull origin main
   git checkout feature/<short-description>
   git merge main
```
   Resolve any conflicts locally before proceeding.

6. **Push your branch and open a pull request:**
```bash
   git push origin feature/<short-description>
```

### Branch Naming Convention
| Prefix       | Use Case                  |
|--------------|----------------------------|
| `feature/`   | New features                |
| `fix/`       | Bug fixes                   |
| `chore/`     | Maintenance/config changes  |
| `hotfix/`    | Urgent production fixes     |

## Contributing
Please follow the Git workflow above for all contributions. Ensure your branch is up to date with `main` before opening a pull request.
Create a `.env` file with your PostgreSQL connection details:
