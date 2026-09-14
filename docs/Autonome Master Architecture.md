# **Autonome: Master Architecture & Protocol Specification**

## **1\. Executive Summary & The Architectural Pivot**

Autonome is a decentralized compute marketplace and AI agent orchestration network built on **BOT Chain**. It connects consumers needing AI-driven automated tasks with independent DePIN node operators supplying idle hardware compute.

**The Paradigm Shift: The Brain vs. The Muscle**

To achieve mass adoption and true hardware scalability, Autonome enforces a strict decoupling of intent parsing from workload execution:

* **The Orchestrator (The Brain):** A centralized (or VPS-hosted) service running heavy LLMs (e.g., Llama 3 via Ollama). It parses user prompts, formats JSON execution manifests, estimates compute costs, and routes tasks to Sub-Agents.  
* **The Compute Node (The Muscle):** A hardware-agnostic, decentralized worker running on consumer devices. **Nodes do NOT run AI models.** They act as Akash-style ephemeral container runners. They execute lightweight, sandboxed task payloads, returning cryptographic proofs while utilizing true 0% idle RAM when inactive.

## **2\. Current System Architecture (The 5 Layers)**

The protocol currently possesses a fully functional vertical slice, executing an end-to-end flow from the Next.js UI down to immutable settlement on the Bohr Testnet.

1. **Consumer & Operator Gateways (Frontend):** Next.js App Router, Tailwind, Wagmi. Features the User Studio and the Node Operator Dashboard.  
2. **The Intent Orchestrator (Backend :8001):** FastAPI microservice. Uses Ollama to parse raw text into actionable JSON manifests.  
3. **Modular Sub-Agents:** Python domain logic (e.g., bdex\_screener.py) that receives parsed intents, injects live on-chain context, and formats the final execution payload.  
4. **The Compute Worker Daemon (Backend :8000):** FastAPI execution service. It runs the workload, computes Keccak256 proofs, settles on-chain, and maintains persistence via a local execution\_logs.db SQLite database.  
5. **On-Chain Settlement (BOT Chain):** The AutonomeSettlementEscrow contract trustlessly splits tokens: 70% to Sub-Agent developers, 15% to Node Operators, and 15% Protocol/Burn.

## **3\. The Unofficial BOT Chain Python SDK (botchain-sdk-py)**

Autonome relies heavily on the botchain-sdk-py package to abstract away BOT Chain's unique EVM architecture. This SDK is fully deployed and integrated, providing:

* **Parlia Consensus Support:** Automatically injects ExtraDataToPOAMiddleware to prevent block header parsing crashes.  
* **Zero-Gas Settlement (MegaFuel):** Intercepts transactions and queries pm\_isSponsorable, allowing the Compute Worker to sign zero-gas settlement proofs (gasPrice \= 0x0).  
* **DeFi Automation:** Natively interacts with the BDEX V3 QuoterV2 and SwapRouter for automated token conversions and liquidity queries.

## **4\. Master Kanban Roadmap (Path to Prototype)**

This roadmap tracks our immediate steps to deliver a frictionless, consumer-ready prototype.

### **✅ DONE (Phases 1 \- 5\)**

* **\[Core\]** Next.js User Studio & Node Dashboard (Wagmi \+ Tailwind).  
* **\[Core\]** Central FastAPI Orchestrator (Llama 3 Intent Parsing).  
* **\[Core\]** Modular Sub-Agent Pipeline (BDEX Screener integration).  
* **\[Core\]** Worker Daemon with Persistent SQLite Execution Logs.  
* **\[Core\]** botchain-sdk-py Integration (Zero-Gas EOA Paymaster).

### **🚀 UP NEXT (Phase 6: Infrastructure & Frictionless Onboarding)**

* **\[DePIN\] Akash-Style Ephemeral Compute Runner:** Refactor worker.py to use docker-py. Remove the local LLM requirement so nodes become generic, agnostic container runners.  
* **\[DePIN\] Autonome Desktop Client (Tauri):** Build a 1-click .exe / .dmg installer bundling worker.py. Implements **Autonomous Ephemeral Provisioning** (auto-generating a hidden, zero-balance EOA key on boot) so users never touch a .env file or terminal.  
* **\[Security\] ERC-4337 Smart Account Vaults:** Integrate SimpleAccountFactory for counterfactual vault deployment. The Tauri App takes the Vault Address as its only input, safely routing operator earnings to cold storage.  
* **\[Payments\] Fiat-to-Crypto On-Ramp (CreditModal.tsx):** Integrate a Web2 checkout flow (Stripe/Transak) allowing users to purchase Studio credits with USD, auto-routed to USDT on BOT Chain.

### **📅 BACKLOG (The Complete Marketplace)**

* **\[Marketplace\] The Agent Hub (Developer Portal):** UI for developers to register Sub-Agents and track their 70% royalty earnings.  
* **\[Marketplace\] DCM Engine (Compute Router):** Upgrade the Orchestrator to maintain a dynamic registry of active worker nodes and route tasks based on real-time availability and ping.  
* **\[Marketplace\] Mainnet Smart Contracts:** Deploy the final 70/15/15 Settlement Escrow to BOT Chain Mainnet.