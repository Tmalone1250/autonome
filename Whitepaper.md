# Autonome Network White Paper
## A Decentralized Physical Infrastructure Protocol for Verifiable Artificial Intelligence Execution & Agent Marketplaces

**Version:** 1.0.0  
**Date:** September 2026  
**Authors:** Autonome Core Research & Development Team  
**Blockchain Target:** BOT Chain (Chain ID: 968 Testnet / 677 Mainnet)  
**Target Repository:** `autonome/Whitepaper.md`  

---

## Abstract

The rapid centralization of artificial intelligence (AI) infrastructure has created significant industry bottlenecks: closed-source execution environments, prohibitive API markups, censorship vulnerabilities, and an unmonetized long tail of independent AI agent developers. Simultaneously, Decentralized Physical Infrastructure Networks (DePIN) offer immense compute capacity but suffer from complex Web3 onboarding, cumbersome private key management, and a lack of verifiable execution proofs.

**Autonome** introduces a unified, 5-layer DePIN protocol and autonomous AI agent marketplace built natively on **BOT Chain**. Autonome bridges natural language consumer requests with crowd-sourced, sandboxed micro-container execution environments and automated EVM smart contract settlements. 

Key innovations include:
1. **ERC-4337 Counterfactual Smart Account Vaults**, enabling zero-collateral, zero-gas onboarding for hardware node operators.
2. **An Open AI Agent Marketplace** supporting popular frameworks (e.g., OpenClaw, custom Python runtimes) where agent creators earn an automated **70% revenue share** on task execution.
3. **A Cryptographic Proof of Completion Model**, leveraging EIP-191 signed Keccak256 execution logs to ensure zero-trust task verifiability.
4. **An Automated 70/15/10/5 Revenue Division Strategy**, disbursing 70% to Agent Developers, 15% to Node Operator Vaults, 10% to Protocol-Owned Liquidity (POL) on BDEX V3, and 5% to permanent deflationary token burns.
5. **A Consumer-Friendly Freemium Subscription Model**, featuring **50 free daily credits/day**, multi-currency crypto payments (**USDT, BOT, ATMA**), and a **Stripe Fiat-to-Crypto On-Ramp**.

---

## 1. Introduction & Background

### 1.1 The Centralized AI Dilemma
Contemporary AI applications rely almost exclusively on centralized cloud monopolies (e.g., AWS, Azure, GCP, OpenAI). This architectural paradigm introduces four core vulnerabilities:
- **Opaque Execution & Data Exploitation**: Users have no insight into how their data is processed or whether off-chain agent logic has been tampered with.
- **Monopoly Pricing & High Margins**: Centralized providers capture up to 80% operating margins on compute dispatch, pricing out small developers and researchers.
- **Developer Monetization Barriers**: Open-source AI developers who build highly capable agents (e.g., via OpenClaw, AutoGPT, or custom tools) lack standardized protocol rails to monetize their creations permissionlessly.
- **Single Points of Failure**: Centralized infrastructure is subject to geographic outages, API rate-limiting, and arbitrary censorship.

### 1.2 The DePIN Solution & Compute Demands
Decentralized Physical Infrastructure Networks (DePIN) democratize hardware compute by allowing independent node operators to contribute idle CPU and GPU capacity. However, early-generation DePIN platforms fail to capture mainstream AI adoption due to high onboarding friction—requiring operators to hold native gas tokens, configure complex Kubernetes clusters, and risk private key exposure on host machines.

### 1.3 The Autonome Vision
Autonome addresses these challenges by uniting **Consumer Usability**, **Crowd-Sourced Compute Scaling**, and **Automated Web3 Settlement**. By abstracting Web3 complexity through ERC-4337 Account Abstraction and providing a 1-click desktop compute daemon, Autonome creates an elastic, virtually unlimited pool of compute power on BOT Chain.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 AUTONOME PROTOCOL ECOSYSTEM                            │
├──────────────────────────┬──────────────────────────┬──────────────────────────────────┤
│     END CONSUMERS        │    DePIN COMPUTE NODES   │        AGENT DEVELOPERS          │
│  - Natural Language UI   │  - 1-Click Tauri Daemon  │  - OpenClaw & Custom Agents      │
│  - 50 Free Credits / Day │  - Ephemeral Key Security│  - Permissionless Registration   │
│  - USDT/BOT/ATMA/Stripe  │  - Earn 15% ATMA Rewards │  - Earn 70% Revenue Share        │
└──────────────────────────┴──────────────────────────┴──────────────────────────────────┘
```

---

## 2. The 5-Layer System Architecture

Autonome decouples intent capture, AI orchestration, container execution, compute provision, and smart contract settlement across five distinct layers.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: CONSUMER & OPERATOR FRONTEND (Next.js 15, React 19, Wagmi v3, Viem v2)        │
│   - User Studio (Intent Capture, 50 Daily Credits, Stripe Fiat On-Ramp)                │
│   - Node Telemetry Console (Telemetry Monitoring & Vault Claiming)                     │
└──────────────────────────┬─────────────────────────────────────────────────────────────┘
                           │ HTTP / JSON-RPC / Stripe Webhooks
                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: INTENT ORCHESTRATOR & RELAYER (FastAPI - Port 8002, Llama 3 via Ollama)       │
│   - Natural Language Parser | Agent Discovery Engine | Master Settlement Relayer        │
└──────────────────────────┬─────────────────────────────────────────────────────────────┘
                           │ HTTP / JSON-RPC
                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: MODULAR SUB-AGENT MARKETPLACE (OpenClaw & Custom Agent Registry)              │
│   - OpenClaw Web Automation | BDEX V3 Screener | On-Chain Swap Evaluator | Community   │
└──────────────────────────┬─────────────────────────────────────────────────────────────┘
                           │ Local IPC / Port 8000
                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DePIN COMPUTE WORKER DAEMON (FastAPI / PyInstaller Sidecar - Port 8000)        │
│   - Ephemeral Key Generator | Docker Sandbox Runner | Cryptographic Proof Signer       │
└──────────────────────────┬─────────────────────────────────────────────────────────────┘
                           │ Web3 Raw Transactions
                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: ON-CHAIN SETTLEMENT & ACCOUNT ABSTRACTION (BOT Chain / Bohr Testnet)           │
│   - AutonomeSettlementEscrow.sol | AutonomeToken.sol (ATMA) | SimpleAccount Vaults    │
└──────────────────────────┴─────────────────────────────────────────────────────────────┘
```

### Layer 1: Consumer Interface & Subscription Engine
The consumer layer consists of the **User Studio** (Next.js 15 web interface) and **Node Dashboard** (Tauri v2 Desktop App). Users submit natural language prompts, manage subscription tiers, track daily credit usage (including the **50 free daily credits** reset), and pay via crypto (**USDT, BOT, ATMA**) or fiat debit cards via **Stripe**.

### Layer 2: Intent Orchestrator & Natural Language Parsing
Operating on **Port 8002**, the Intent Orchestrator acts as the protocol relayer. It parses unstructured text using a local LLM instance (Llama 3 via Ollama), resolves execution parameters, queries the Agent Registry for candidate sub-agents, selects active compute workers, and submits settlement transactions to the EVM escrow contract.

### Layer 3: Modular Sub-Agent Marketplace
An open repository of domain-specific execution agents. Developers can register custom agents written in Python or TypeScript (including OpenClaw scrapers, DeFi analytics tools, and automated traders). Each sub-agent is tied to a developer's ERC-4337 Smart Account Address to receive automated 70% fee payouts.

### Layer 4: DePIN Compute Worker Daemon
Operating on **Port 8000**, the worker daemon runs on host hardware (bundled as a standalone PyInstaller binary `worker-bin`). It executes workloads inside micro-sandboxed Docker containers (`python:3.10-slim`), isolates host filesystem access, generates EIP-191 Secp256k1 ephemeral key signatures, and logs verifiable execution proofs to SQLite (`~/.autonome/worker.db`).

### Layer 5: On-Chain Settlement & Account Abstraction
The smart contract settlement clearinghouse deployed on BOT Chain. `AutonomeSettlementEscrow.sol` locks user task fees and programmatically disburses funds upon proof validation, executing the 70/15/10/5 fee division across developer smart accounts, node operator vaults, protocol treasuries, and token burns.

---

## 3. Cryptographic Proof of Completion & Verifiable Computation

To eliminate trust assumptions between consumers, orchestrators, and node operators, Autonome enforces a cryptographic proof submission cycle.

```
 ┌─────────────────────────────────────────────────────────────────┐
 │                   DePIN WORKER NODE HOST                        │
 │                                                                 │
 │  ┌───────────────────────────────────────────────────────────┐  │
 │  │ Docker Sandbox Engine                                     │  │
 │  │ ┌───────────────────────────────────────────────────────┐ │  │
 │  │ │ Sub-Agent Execution (OpenClaw / Python Code)          │ │  │
 │  │ │ - Output: stdout, stderr, result_json                 │ │  │
 │  │ └───────────────────────────┬───────────────────────────┘ │  │
 │  └─────────────────────────────┼─────────────────────────────┘  │
 │                                │                                │
 │                                ▼                                │
 │  ┌───────────────────────────────────────────────────────────┐  │
 │  │ Cryptographic Proof Generator                             │  │
 │  │ proof_hash = Keccak256(task_id || result_json || time)    │  │
 │  │ signature  = EphemeralSign(proof_hash, worker_key.json)   │  │
 │  └─────────────────────────────┬─────────────────────────────┘  │
 └────────────────────────────────┼────────────────────────────────┘
                                  │
                                  ▼  [ Submit Proof of Completion ]
                      ┌───────────────────────┐
                      │ Intent Orchestrator   │
                      └───────────┬───────────┘
                                  │
                                  ▼  [ settleTask() Call ]
             ┌─────────────────────────────────────────┐
             │ AutonomeSettlementEscrow.sol Contract   │
             └─────────────────────────────────────────┘
```

### 3.1 Proof Generation Mechanics
Upon task completion inside the Docker container, the worker daemon captures the execution stdout, stderr, and output payload `R`. It calculates a deterministic Keccak256 hash:

$$\text{proof\_hash} = \text{Keccak256}(\text{taskId} \mathbin{\Vert} \text{Keccak256}(R) \mathbin{\Vert} \text{timestamp})$$

The worker daemon signs `proof_hash` using its local ephemeral key $K_{\text{ephemeral}}$ derived according to EIP-191 personal sign format:

$$\text{signature} = \text{Sign}_{K_{\text{ephemeral}}}(\mathtt{"\x19Ethereum\ Signed\ Message:\n32"} \mathbin{\Vert} \text{proof\_hash})$$

### 3.2 Verification & Relaying
The worker submits the payload `(taskId, R, proof_hash, signature, operator_vault, sub_agent)` to the Orchestrator. The Orchestrator verifies:
1. $\text{ecrecover}(\text{proof\_hash}, \text{signature}) \in \mathcal{V}_{\text{validators}}$ (The signer is an active registered worker).
2. The output payload $R$ satisfies the sub-agent's schema requirements.

Upon validation, the Orchestrator calls `settleTask()` on the settlement escrow contract.

---

## 4. ERC-4337 Account Abstraction & Zero-Gas UX

A primary barrier to traditional DePIN participation is gas fee management. Autonome resolves this using **ERC-4337 Account Abstraction**.

```
 Node Operator / Developer EOA Wallet
         │
         ▼  (Read Counterfactual Address via SimpleAccountFactory)
 ┌────────────────────────────────────────────────────────┐
 │  ERC-4337 Smart Account Vault (SimpleAccount.sol)      │
 │  Address: 0x... (Deterministic via CREATE2)            │
 │                                                        │
 │  - Receives 70% (Agent Dev) or 15% (Node Ops) Payouts  │
 │  - Requires NO deployment prior to receiving funds     │
 │  - Controlled exclusively by Owner EOA                 │
 └──────────────────────────┬─────────────────────────────┘
                            │
                            │  [ Click "Claim Rewards" on Dashboard ]
                            ▼
           SimpleAccount.execute(ATMA_TOKEN, 0, transfer(EOA, balance))
```

### 4.1 Counterfactual Vault Derivation
Neither node operators nor agent developers need to deploy a contract or spend gas upfront. Vault addresses are derived deterministically using `SimpleAccountFactory`:

$$\text{VaultAddress} = \text{CREATE2}(\text{FactoryAddress}, \text{salt}, \text{Keccak256}(\text{Bytecode} \mathbin{\Vert} \text{OwnerEOA}))$$

Tokens accrue directly to this counterfactual address. The contract is deployed on-chain automatically when the owner executes their first reward withdrawal.

### 4.2 Gasless Meta-Transactions (EIP-2612 Permits)
Consumers paying for tasks with ATMA tokens can execute allowances gaslessly via EIP-2612 `permit()` signatures:

```solidity
function depositIntentWithPermit(
    bytes32 taskId,
    address user,
    uint256 amount,
    uint256 deadline,
    uint8 v, bytes32 r, bytes32 s
) external nonReentrant {
    atmaToken.permit(user, address(this), amount, deadline, v, r, s);
    _depositIntent(taskId, user, amount);
}
```

---

## 5. Tokenomics, Revenue Model & Subscription Hierarchy

Autonome implements a dual-revenue engine combining consumer subscription tiers with automated smart contract fee splits.

```
                              ┌──────────────────────────────────────────────┐
                              │           End-User Task Payment              │
                              │  (Free 50/day | USDT | BOT | ATMA | Stripe)  │
                              └──────────────────────┬───────────────────────┘
                                                     │
                                       [ Escrow Smart Contract ]
                                               [ Split ]
                                                     │
       ┌───────────────────┬─────────────────────────┴─────────────────────────┬───────────────────┐
       │                   │                                                   │                   │
       ▼                   ▼                                                   ▼                   ▼
┌──────────────┐    ┌──────────────┐                                    ┌──────────────┐    ┌──────────────┐
│  70% Agent   │    │ 15% Node     │                                    │  10% BDEX    │    │  5% ATMA     │
│  Developer   │    │ Operator     │                                    │  POL / Protocol│  │  Deflationary│
│  Smart Account│   │ Vault Reward │                                    │  Treasury    │    │  Token Burn  │
└──────────────┘    └──────────────┘                                    └──────────────┘    └──────────────┘
```

### 5.1 Consumer Subscription Tiers

| Plan Tier | Price | Daily / Monthly Credits | Features & Target Audience |
| :--- | :--- | :--- | :--- |
| **Free Tier** | **$0 / month** | **50 Credits / Day** | Access to standard agent suite, community nodes, auto-reset daily. |
| **Pro Tier** | **$19 / month** | **2,500 Credits / Month** | Priority compute node routing, OpenClaw web scrapers, fast execution. |
| **Dev / Enterprise**| **$99 / month** | **15,000 Credits / Month** | Custom agent registration, dedicated node routing, high concurrency. |

### 5.2 Payment Rails & Fiat On-Ramp
- **Crypto Payments**: Native Web3 wallet checkout supporting **USDT, BOT, and ATMA**. Users paying in ATMA receive a **10% fee discount**, driving token utility and velocity.
- **Stripe Fiat On-Ramp**: Integrated credit/debit card checkout via Stripe Webhooks. Fiat payments automatically credit user accounts, onboarding non-crypto users seamlessly.

### 5.3 The 70/15/10/5 Revenue Division Model
For any task fee $F_{\text{total}}$ escrowed in the protocol:

$$\text{Reward}_{\text{Agent Dev}} = \frac{F_{\text{total}} \times 7000}{10000} = 0.70 \times F_{\text{total}}$$

$$\text{Reward}_{\text{Node Operator}} = \frac{F_{\text{total}} \times 1500}{10000} = 0.15 \times F_{\text{total}}$$

$$\text{Allocation}_{\text{POL / Treasury}} = \frac{F_{\text{total}} \times 1000}{10000} = 0.10 \times F_{\text{total}}$$

$$\text{Amount}_{\text{Burned}} = F_{\text{total}} - (\text{Reward}_{\text{Agent Dev}} + \text{Reward}_{\text{Node Operator}} + \text{Allocation}_{\text{POL}}) = 0.05 \times F_{\text{total}}$$

- **70% Agent Developer**: Transferred directly to the author of the sub-agent (e.g. OpenClaw agent developer).
- **15% Compute Node Operator**: Transferred to the operator's counterfactual ERC-4337 Vault.
- **10% Protocol Treasury & BDEX POL**: Transferred to protocol reserves to deepen liquidity on BDEX V3.
- **5% Native Burn**: Permanently destroyed via `AutonomeToken.burn()`, creating continuous deflationary pressure.

---

## 6. Node Operator Economics & Ephemeral Security

### 6.1 Zero-Configuration 1-Click Hardware Setup
Hardware operators turn their machines into compute nodes in under 60 seconds:

```
[Download Desktop App] ──► [Paste ERC-4337 Vault] ──► [Click Start Node] ──► [Earn Passive ATMA]
```

1. **Download**: Operator downloads `autonome-desktop` (`.AppImage`, `.deb`, `.dmg`, or `.exe`).
2. **Vault Sync**: Operator inputs their cold payout address. Tauri saves it to `localStorage` and syncs it to the sidecar via `POST http://127.0.0.1:8000/set_vault`.
3. **Daemon Launch**: Tauri launches `worker-bin` as a background sidecar process on port `8000`.
4. **Execution**: The node executes sandboxed container tasks and logs signed execution proofs.

### 6.2 Ephemeral Key Security Model
The worker daemon generates a Secp256k1 key pair stored locally at `~/.autonome/worker_key.json`. This key is strictly used for signing execution proofs. Because earnings route directly to the decoupled counterfactual vault, an attacker compromising the node host gains access to zero accumulated funds.

---

## 7. Network Specifications & Contract Registry

### 7.1 BOT Chain Network Specifications

```ini
Network Name = BOT Chain Bohr Testnet
Chain ID = 968
Native Token = tBOT / BOHR
RPC Endpoint = https://rpc.bohr.life
Explorer = https://scan.bohr.life
EVM Target = shanghai
Block Time = ~0.75 seconds
Consensus = Parlia Proof-of-Staked-Authority (PoSA)
```

### 7.2 Deployed Smart Contract Registry

```
AutonomeSettlementEscrow = 0x5b30dB9F00F9fa644a13117D5b31844223e3Fb4E
AutonomeToken (ATMA)     = 0xd29dE89D308b3F1eAcF3c36f821842F8F6f3f840
SimpleAccountFactory     = 0xBC88d6012b3bf8426C2851d3798cEB5257658332
EntryPoint (ERC-4337)    = 0x0000000071727De22E5E9d8BAf0edAc6f37da032
```

---

## 8. Strategic Competitive Analysis

Autonome occupies a distinct position at the intersection of AI Frameworks, DePIN Compute Networks, and Web3 Monetization.

```
                          AI AGENT FOCUS
                                ▲
                                │
                                │    ★ AUTONOME
                                │    (Consumer AI Framework + OpenClaw + DePIN)
                                │
                                │   Bittensor (TAO)
                                │
  LESS DEPIN                    │                    MORE DEPIN
  ──────────────────────────────┼──────────────────────────────►
  Fetch.ai                      │   Akash Network (AKT)
                                │   Render Network (RNDR)
                                │
                                │
                                ▼
                         RAW COMPUTE FOCUS
```

### Feature Comparison Matrix

| Feature | **Autonome (BOT Chain)** | **Akash Network** | **Bittensor (TAO)** | **Fetch.ai / ASI** |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Focus** | Consumer AI Framework & DePIN | Generic Cloud Compute | Machine Learning Models | Autonomous Micro-Agents |
| **Agent Monetization**| Open Developer Agent Portal (70% split)| None | Subnet Emissions | Staking Pools |
| **Payment Options** | USDT, BOT, ATMA, Stripe Fiat | AKT / USDC | TAO | FET |
| **Consumer Model** | Free 50 Daily Credits + Subscriptions | Pay-per-hour Container | Emission Halving | Staking Rewards |
| **Execution Sandbox** | Docker Micro-Containers | Kubernetes Clusters | Custom Subnets | Python Runtimes |
| **Hardware Setup UX** | 1-Click Tauri Desktop App | Complex CLI / K8s | Complex Subnet Mining | CLI Setup |
| **Wallet Model** | ERC-4337 Counterfactual Vaults | Standard Cosmos Address | Polkadot / Substrate Key | Cosmos Wallet |

---

## 9. Technical Roadmap

```
[Phase 1-5: Core Engine & Contracts] ──► [Phase 6: Relayer & Vaults] ──► [Phase 7: Open Agents & Stripe] ──► [Phase 8: Mainnet]
```

### Phase 1–5: Core Engine & DePIN Execution (Completed)
- Deploy `AutonomeSettlementEscrow` and `AutonomeToken` on Bohr Testnet.
- Build `worker.py` daemon with Docker sandboxing and EIP-191 ephemeral key signatures.
- Build `orchestrator/engine.py` with Llama 3 intent parsing.
- Develop Next.js web console (`autonome-frontend`) and Tauri desktop application (`autonome-desktop`).

### Phase 6: Protocol Relayer Centralization & UI Hardening (Completed)
- Centralize web3 transaction submission into Orchestrator Relayer (`RELAYER_PRIVATE_KEY`).
- Integrate ERC-4337 `SimpleAccountFactory` counterfactual vault derivation.
- Add real-time telemetry polling, port cleanup safeguards, and "Claim Rewards" vault withdrawal flow.

### Phase 7: Open Agent Registration Portal & Stripe On-Ramp (In Progress)
- **OpenClaw & Custom Agent Marketplace**: Enable developers and creators to register custom AI agents to the network and earn 70% revenue shares automatically.
- **Stripe Fiat-to-Crypto On-Ramp**: Implement Stripe payment gateway integration allowing users to purchase monthly credit subscriptions using debit/credit cards.
- **Freemium Daily Credit Reset**: Automate daily allocation of **50 free credits/day** for casual consumer task execution.

### Phase 8: Mainnet Launch & Cross-Chain Expansion (Future)
- Deploy Autonome core contracts to BOT Chain Mainnet (Chain ID `677`).
- Implement LayerZero / Wormhole cross-chain messaging to allow consumers on Ethereum, Arbitrum, and Solana to dispatch tasks to Autonome DePIN workers seamlessly.

---

## 10. Conclusion

Autonome establishes a new benchmark for decentralized artificial intelligence. By pairing an intuitive consumer framework (featuring 50 free daily credits, multi-currency crypto payments, and Stripe fiat processing) with an elastic DePIN compute network and an open developer marketplace (supporting frameworks like OpenClaw), Autonome creates a self-sustaining economic flywheel. 

Through ERC-4337 Account Abstraction and cryptographic proofs of completion, Autonome delivers zero-friction onboarding for node operators while guaranteeing 70% revenue splits for agent developers and 5% deflationary token burns for ATMA holders on BOT Chain.

---

## References

1. **EIP-4337 Account Abstraction**: Buterin, V., et al. (2021). *ERC-4337: Account Abstraction Using Alt Mempool*. Ethereum Improvement Proposals.
2. **EIP-2612 Signed Approvals**: ERC-20 Permit Extension for Gasless Token Approvals.
3. **EIP-191 Signed Data Standard**: Ethereum Signed Message Format.
4. **BOT Chain Technical Documentation**: Bohr PoSA Consensus Mechanism and Smart Contract Architecture (Chain ID 968/677).
5. **OpenClaw Framework**: Open-source web automation and agent scraping specification.
