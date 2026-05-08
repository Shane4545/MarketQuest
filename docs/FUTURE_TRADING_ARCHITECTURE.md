# Future trading architecture (intended progression)

This document describes a **possible** future path if research and paper results justify additional product depth. It is **not** a commitment to build every stage, and **not** an offer of brokerage or advisory services.

## Intended progression (high level)

1. **Research scanner** — Rule-based candidate identification from acquired features (current Phase 1 direction).
2. **Paper basket** — Frozen allocation artifact for review (historical / simulated context).
3. **Paper trading ledger** — Internal simulated ledger for hypothetical fills and P&L tracking (future).
4. **Broker paper account integration** — Connectivity to a broker’s **paper/sandbox** environment for simulated orders (future).
5. **Human-approved live trade intents** — Explicit approval gates before any message leaves the system toward a live broker (future).
6. **Live broker execution** — Only after risk controls, structured logging, kill switches, and compliance review are in place (future).

## Concept separation (design vocabulary)

| Concept | Meaning |
|--------|---------|
| **Research candidate** | Symbol that passed configured scan rules. |
| **Frozen paper basket** | Historical or simulated allocation artifact produced for analysis/review. |
| **Trade intent** | Proposed action (e.g. BUY/SELL/HOLD/DO_NOT_TRADE) — **future**; not execution. |
| **Paper order** | Simulated order against a paper ledger or broker paper account — **not in current phase**. |
| **Live order** | Real brokerage order — **not in current phase**. |

**Allowed in the current phase:** research candidates and frozen paper baskets only.  
**Not allowed in the current phase:** live orders, broker execution, or production trade tickets.

## Current system boundaries (explicit)

- The current system **does not** place trades.
- The current system **does not** provide personalized financial, legal, or tax advice.
- The current system **is not** production trading software.
- **Real-money execution must only be enabled for an authorized brokerage account owner, after explicit human approval, broker compliance checks, account permissions, risk controls, kill switches, and audit logging are in place.**

## Governance and safety (future)

Future phases that touch orders or brokers should include, at minimum:

- Human approval workflow for trade intents.
- Risk limits, position limits, and loss limits (configurable and logged).
- Kill switches and audit logs for every order decision and state change.
- Clear separation between research outputs, paper simulation, and live execution.

## Launcher and data model (current phase)

The governed run launcher records **safe-by-default** flags in `launcher_request.json` and `launcher_status.json` (e.g. `trading_enabled: false`, `live_orders_enabled: false`) so that **future** trading and compliance layers can attach without rewriting core run metadata. These flags are **not** an offer to enable trading in the current build.

---

*This file is informational architecture only; it does not change product terms of use or regulatory status by itself.*
