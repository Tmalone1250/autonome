# Autonome: Decentralized AI Agent DePIN Network
## Master Architecture & Technical Specification
### A Unified Source Specification for NotebookLM, Pitch Decks, Executive Overviews & Technical Audits

---

## 1. Executive Summary & Core Value Proposition

**Autonome** is a next-generation Decentralized Physical Infrastructure Network (DePIN) and autonomous agent orchestration protocol built on **BOT Chain**. Autonome bridges the critical gap between complex, natural-language consumer requests and verified, decentralized artificial intelligence execution.

The core mission of Autonome is to deliver a **top-quality, production-grade AI framework** for end-users, powered by an **unlimited pool of compute supply** provided by crowd-sourced DePIN Node Operators, and fueled by a flourishing **AI Agent Marketplace** where developers and individuals (e.g., utilizing OpenClaw and custom agent frameworks) can monetize specialized AI agents.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 AUTONOME ECOSYSTEM MATRIX                               │
├──────────────────────────┬──────────────────────────┬──────────────────────────────────┤
│    CONSUMER LAYER        │      DEPIN NETWORK       │         ON-CHAIN LAYER           │
│  - Monthly Subscriptions │  - Crowd-Sourced Hardware│  - ERC-4337 Account Abstraction  │
│  - Free Tier (50 cr/day) │  - Sandboxed Micro-Docker│  - 70/15/10/5 Revenue Settlement   │
│  - USDT/BOT/ATMA/Stripe  │  - Ephemeral Key Signing │  - ATMA Deflationary Token Burn  │
│  - Natural Language UI   │  - Unlimited Compute     │  - Sub-Agent Smart Accounts      │
└──────────────────────────┴──────────────────────────┴──────────────────────────────────┘
```

### Key Business Metrics & Strategic Highlights
- **Target Blockchain**: BOT Chain / Bohr Testnet (Chain ID `968`) & BOT Chain Mainnet (Chain ID `677`).
- **Consumer Payment Flexibility**: Supports multi-currency payments in **USDT, BOT, or ATMA**, alongside a planned **Stripe Fiat-to-Crypto On-Ramp** for credit/debit card subscriptions.
- **Freemium Tier Model**: Includes a Free Tier granting **50 daily credits/day** for casual tasks, scaling into tiered monthly subscriptions for power users and enterprise workloads.
- **Open AI Agent Marketplace**: Anyone can register a custom AI agent (built via OpenClaw, custom Python runtimes, or LangChain) into the protocol registry to earn passive income whenever Orchestrators call their agent.
- **70/15/10/5 Automated Settlement**: 70% to Sub-Agent Developer Smart Account, 15% to DePIN Node Operator Vault, 10% to Protocol Treasury / BDEX POL, and 5% permanently burned in ATMA tokens for native protocol deflation.
- **Node Operator Security**: 100% ephemeral key derivation — node operators never handle private keys, eliminating cold storage liability and slash risk.

---

## 2. Market Problem & The Autonome Solution

### The Current Market Bottlenecks
1. **Centralized AI Monopolies & Opaque Subscriptions**: Proprietary AI agent platforms impose strict usage caps, high API markups, closed-source execution environments, and censorship risks.
2. **DePIN Usability Friction**: Conventional decentralized compute networks force hardware operators to manage complex private keys, perform manual web3 transactions, and configure complex networking.
3. **The Agent Monetization Gap**: Independent developers and hobbyists who build high-utility AI agents (e.g., using OpenClaw, AutoGPT, or custom tools) lack standardized protocol rails to monetize their agents without deploying custom smart contract infrastructures.
4. **Lack of Verifiable Execution**: Web3 users requesting off-chain AI tasks have no cryptographic guarantee that an agent executed the requested code faithfully without data manipulation.

### The Autonome Paradigm Shift
Autonome solves these industry bottlenecks through a fully integrated hardware, agent, and smart contract ecosystem:
- **Unlimited Scalable DePIN Compute**: Crowd-sourced node operators install a 1-click desktop app, providing an elastic, virtually unlimited pool of compute power for the BOT Chain ecosystem.
- **Permissionless AI Agent Registration**: Developers and everyday creators register agents (e.g., OpenClaw web scrapers, DeFi screeners, social media bots) into the protocol's central registry. Whenever an Orchestrator routes a consumer task to their agent, 70% of the execution fee settles directly into the developer's Smart Account.
- **Flexible Consumer Pricing & On-Ramping**: Users can access the platform via a **Free Tier (50 credits/day)** or subscribe monthly using **USDT, BOT, ATMA**, or traditional debit cards via **Stripe**.
- **Verifiable Execution Proofs**: Sub-agents and compute nodes return cryptographic proofs of completion to the Orchestrator before smart contract funds are unlocked.

---

## 3. The 5-Layer System Architecture

Autonome is built on a modular 5-layer stack that separates consumer intent, AI orchestrations, containerized workloads, hardware operation, and settlement logistics.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: CONSUMER & OPERATOR FRONTEND (Next.js 15, Wagmi v3, Viem, React 19)           │
│   - User Studio (Intent Entry, Subscriptions, Stripe On-Ramp, 50 Free Daily Credits)    │
│   - Node Dashboard (Telemetry & ERC-4337 Vault Claiming)                               │
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
│   - OpenClaw Web Automation | BDEX V3 Screener | On-Chain Swap Evaluator | User Agents │
└──────────────────────────┬─────────────────────────────────────────────────────────────┘
                           │ Local IPC / Port 8000
                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DePIN COMPUTE WORKER DAEMON (FastAPI / PyInstaller Sidecar - Port 8000)        │
│   - Ephemeral Wallet Manager | Docker Sandbox Runner | Cryptographic Proof Signer       │
└──────────────────────────┬─────────────────────────────────────────────────────────────┘
                           │ Web3 Raw Transactions
                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: ON-CHAIN SETTLEMENT & ACCOUNT ABSTRACTION (BOT Chain / Bohr Testnet)           │
│   - AutonomeSettlementEscrow.sol | AutonomeToken.sol (ATMA) | SimpleAccount Vaults    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Layer Descriptions

#### Layer 1: Consumer Studio & Operator Telemetry (`autonome-frontend` & `autonome-desktop`)
- **Consumer Studio**: Enables end-users to manage subscription tiers, track daily credits (including the 50 free daily credits reset), pay via USDT/BOT/ATMA or Stripe fiat on-ramp, and submit natural language prompts (`http://localhost:8002/prompt`).
- **Node Dashboard & Tauri Desktop Control Panel**: Serves as the operator interface. Displays system hardware metrics (CPU/RAM load), active worker status, listening ports, execution logs, and an interactive **Claim Rewards** module interfacing with ERC-4337 smart account vaults.

#### Layer 2: Intent Orchestrator (`autonome/orchestrator/engine.py`)
- Acts as the system brain and protocol relayer running on **Port 8002**.
- Integrates local LLM inference (Llama 3 hosted on Ollama at `http://localhost:11434`) to extract structured parameters (e.g., token symbols, scraper targets, execution rules) from unstructured prompt text.
- Queries the **Agent Registry** to dynamically discover registered community sub-agents (including OpenClaw agents).
- Relays execution tasks to Layer 4 workers, receives signed cryptographic proofs of completion, and constructs web3 settlement transactions on Layer 5.

#### Layer 3: Modular Sub-Agent Marketplace (`autonome/agents/` & OpenClaw Registry)
- Open ecosystem of specialized AI agent logic. Supports out-of-the-box financial screeners (e.g., `bdex_screener.py`), web automation agents (OpenClaw integration), and custom user-registered Python/TypeScript micro-agents.
- Each registered agent has an associated **Sub-Agent Smart Account Address** to receive automated 70% settlement payouts.

#### Layer 4: DePIN Compute Worker Daemon (`autonome/worker.py` & `worker-bin`)
- Runs as an independent daemon or Tauri sidecar on **Port 8000**, scaling horizontally across thousands of crowd-sourced node operators to provide virtually unlimited compute power.
- Manages host Docker containers (`python:3.10-slim`), isolating execution from the host filesystem.
- Key Management: Automatically generates an EIP-191 Secp256k1 ephemeral key pair stored locally at `~/.autonome/worker_key.json`.
- Proof Generation: Computes Keccak256 hashes of execution stdout, stderr, and output artifacts, returning a signed proof of completion (`proof_hash` + `signature`).

#### Layer 5: On-Chain Settlement & Account Abstraction (`autonome-contracts/`)
- EVM smart contracts deployed on Bohr Testnet (Chain ID `968`) & BOT Chain Mainnet (Chain ID `677`).
- Governs task fee escrows, subscription credit balances, validator verification, automated 70/15/10/5 fee splits, and ERC-4337 smart vault rewards.

---

## 4. End-to-End Task Lifecycle: A Step-by-Step Narrative

To understand how Autonome functions in practice, consider the execution of a complete task from user prompt entry to on-chain token settlement:

```
[User Prompt / Subscription] ──► [Orchestrator Agent Discovery] ──► [DePIN Worker Sandbox Exec] ──► [Proof of Completion Submitted] ──► [Escrow 70/15/10/5 Payout]
```

### Phase A: Intent Capture, Credit Verification & Parameter Extraction
1. A user visits the **User Studio** web UI. The UI verifies their active subscription or daily credit balance (e.g., using 1 of their **50 free daily credits**).
2. The user enters a natural language prompt: *"Use OpenClaw to scrape top DEX liquidity pairs and screen BDEX V3 for arbitrage opportunities."*
3. The UI packages the request and posts a JSON payload to `http://localhost:8002/prompt`.
4. The **Intent Orchestrator** sends the prompt to the local Ollama instance running `llama3`.
5. Llama 3 parses the text, identifies required capabilities, and queries the Agent Registry to match the request with registered community agents (e.g., an OpenClaw scraper + `bdex_screener`).

### Phase B: Worker Dispatch & Sandboxed Docker Execution
6. The Orchestrator selects an available DePIN Compute Worker Node from the active node registry.
7. The task payload is forwarded to the selected worker node at `http://localhost:8000/execute`.
8. The worker node receives the task, spins up an isolated ephemeral Docker container (`python:3.10-slim`), and executes the script securely.

### Phase C: Proof of Completion Generation & Signing
9. Post-execution, the sub-agent and worker generate a structured output payload and calculate a cryptographic `proof_hash`:
    $$\text{proof\_hash} = \text{Keccak256}(\text{task\_id} \mathbin{\Vert} \text{result\_json} \mathbin{\Vert} \text{timestamp})$$
10. The worker signs `proof_hash` using its local ephemeral key (`worker_key.json`) and appends the node operator's registered vault address (`operator_vault`) and the sub-agent's developer wallet (`sub_agent`).
11. The worker returns this **Proof of Completion** payload back to the Orchestrator.

### Phase D: Centralized On-Chain Settlement & Revenue Division
12. The Orchestrator validates the proof of completion. Using its `RELAYER_PRIVATE_KEY` (funded with BOHR gas), it calls `settleTask()` on the `AutonomeSettlementEscrow` contract:
    ```solidity
    AutonomeSettlementEscrow.settleTask(taskId, subAgentSmartAccount, operatorVaultAddress);
    ```
13. The escrow contract verifies that `msg.sender` is an authorized validator, locks the task status to `Settled`, and disburses funds according to the **70/15/10/5 rule**:
    - **70% ATMA / Crypto** transferred to `subAgentSmartAccount` (Agent Developer / Creator).
    - **15% ATMA / Crypto** transferred to `operatorVaultAddress` (Node Operator ERC-4337 Vault).
    - **10% ATMA / Crypto** transferred to `polTreasury` (BDEX Protocol-Owned Liquidity & Protocol Treasury).
    - **5% ATMA** permanently burned via `atmaToken.burn()` for native token deflation.

### Phase E: Real-Time Telemetry & Log Synchronization
14. Upon receiving the transaction receipt, the Orchestrator sends a `PATCH` request to the worker daemon (`http://localhost:8000/logs/{task_id}`) with the settlement `tx_hash`.
15. The worker records the transaction hash into its local SQLite database (`~/.autonome/worker.db`).
16. The frontend polling loops update the **Node Dashboard** and **User Studio**, displaying a clickable Bohr Scan explorer link (`https://scan.bohr.life/tx/0x...`) for instant verification.

---

## 5. Consumer Subscription Model, Fiat On-Ramp & Tokenomics

Autonome introduces a commercial subscription hierarchy tailored for consumer accessibility, combined with a sustainable economic split for protocol participants.

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

### Consumer Subscription & Pricing Hierarchy

| Plan Tier | Pricing | Daily / Monthly Credits | Target Audience | Primary Features |
| :--- | :--- | :--- | :--- | :--- |
| **Free Tier** | **$0 / month** | **50 Credits / Day** | Casual Users & Testers | Access to standard agent suite, community compute nodes, daily reset. |
| **Pro Tier** | **$19 / month** | **2,500 Credits / Month** | Power Users & Traders | High-priority compute node allocation, OpenClaw scrapers, fast execution. |
| **Dev / Enterprise**| **$99 / month** | **15,000 Credits / Month** | Developers & Businesses | Custom agent registration, dedicated node routing, high concurrency API access. |

### Payment Rail Options
1. **Native Crypto (USDT, BOT, ATMA)**: Direct Web3 wallet payments via Wagmi/Viem. Users paying in **ATMA** receive a **10% credit discount**, driving organic token velocity.
2. **Fiat-to-Crypto On-Ramp (Stripe)**: Integrated credit card / debit card checkout via Stripe Webhooks. Fiat payments automatically mint/assign credit balances to user accounts, bridging Web2 users seamlessly into Web3 AI execution.

### The 70/15/10/5 Revenue Division Breakdown

| Beneficiary Role | Percentage Split | Basis Points (bps) | Economic Purpose |
| :--- | :--- | :--- | :--- |
| **Sub-Agent Developer / Owner** | **70.0%** | `7000 bps` | Paid directly to the developer's Smart Account. Creates a compelling cash-generation incentive for agent creators (e.g., OpenClaw agent developers). |
| **Compute Node Operator** | **15.0%** | `1500 bps` | Paid directly into the operator's counterfactual ERC-4337 Smart Account Vault for hardware compute provision. |
| **BDEX POL & Treasury** | **10.0%** | `1000 bps` | Automatically deepens Protocol-Owned Liquidity on BDEX V3 and funds ongoing network development. |
| **Deflationary Token Burn** | **5.0%** | `500 bps` | Permanently destroyed from circulating supply, creating net-deflationary pressure proportional to network usage. |

---

## 6. ERC-4337 Account Abstraction & Zero-Gas UX Architecture

Autonome eliminates Web3 onboarding friction for both node operators and agent developers.

```
 Node Operator / Dev EOA Wallet
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

### Counterfactual Vault Architecture
- Node operators and agent developers do **not** need to deploy a contract or spend gas upfront to start earning.
- The system derives a deterministic counterfactual address using the canonical `SimpleAccountFactory`:
  $$\text{VaultAddress} = \text{CREATE2}(\text{FactoryAddress}, \text{salt}, \text{Keccak256}(\text{Bytecode} \mathbin{\Vert} \text{OwnerEOA}))$$
- Rewards accrue directly to this smart account address. The contract is deployed on-chain automatically when the owner executes their first withdrawal command.

### The "Claim Rewards" Execution Mechanics
When an operator or developer clicks **Claim Rewards** in the Dashboard:
1. The dashboard queries token balances in the vault address.
2. Wagmi constructs an ERC-4337 execution transaction targeting the `SimpleAccount`:
   ```typescript
   const calldata = encodeFunctionData({
     abi: SimpleAccountABI,
     functionName: 'execute',
     args: [ATMA_TOKEN_ADDRESS, 0n, transferCalldata]
   });
   ```
3. The owner signs the transaction with their connected wallet. Tokens transfer instantly from the vault contract to their primary wallet.

---

## 7. Sub-Agent Proof of Completion & Ephemeral Security

Autonome introduces a zero-trust hardware architecture designed to isolate compute execution, verify task completion, and protect host machines.

```
 ┌─────────────────────────────────────────────────────────────────┐
 │                     HOST COMPUTER (DePIN Node)                  │
 │                                                                 │
 │  ┌───────────────────────────────────────────────────────────┐  │
 │  │ worker.py / worker-bin Daemon                             │  │
 │  │ - Generates ~/.autonome/worker_key.json (Ephemeral EOA)   │  │
 │  │ - Listens on 127.0.0.1:8000                               │  │
 │  └─────────────────────────────┬─────────────────────────────┘  │
 │                                │                                │
 │                                ▼                                │
 │  ┌───────────────────────────────────────────────────────────┐  │
 │  │ Docker Sandbox Engine                                     │  │
 │  │ ┌───────────────────────────────────────────────────────┐ │  │
 │  │ │ Isolated Container (python:3.10-slim)                     │ │  │
 │  │ │ - Executes Sub-Agent (e.g. OpenClaw / BDEX Screener)    │ │  │
 │  │ │ - Generates Signed Proof of Completion                 │ │  │
 │  │ └───────────────────────────────────────────────────────┘ │  │
 │  └───────────────────────────────────────────────────────────┘  │
 └─────────────────────────────────────────────────────────────────┘
```

### Key Security Properties
1. **Self-Generating Ephemeral Keys**:
   - On first boot, `worker.py` creates an Ethereum private key at `~/.autonome/worker_key.json`.
   - The key is used exclusively to sign `proof_hash` strings via EIP-191 personal signing.
   - Node operators never see, manage, or transfer this private key. If a node host is compromised, zero funds are exposed because earnings route to the decoupled ERC-4337 vault address.
2. **Sub-Agent Proof of Completion**:
   - Sub-agents generate cryptographic proofs verifying that the task executed successfully. The orchestrator cross-checks `proof_hash` against authorized validator signatures before releasing funds from `AutonomeSettlementEscrow.sol`.

---

## 8. DePIN Node Operator UX & Hardware Monetization Model

### Unlimited Compute Scaling & 1-Click Hardware Setup
Autonome reduces DePIN node setup from hours of command-line configuration to under 60 seconds, unlocking an **unlimited pool of compute power**:

```
[Download App] ──► [Enter ERC-4337 Vault] ──► [Click Start Node] ──► [Earn Passive ATMA Rewards]
```

1. **Download App**: The operator downloads `autonome-desktop` (`.AppImage`, `.deb`, `.dmg`, or `.exe`).
2. **Configure Vault Address**: The operator pastes their cold recipient address. The address is saved to `localStorage` and automatically propagated to the worker sidecar via `POST http://127.0.0.1:8000/set_vault`.
3. **Click Start Node**: Tauri launches `worker-bin` as a background sidecar process on port `8000`.
4. **Passive Earning**: The node listens for incoming orchestrator jobs, processes sandboxed workloads, logs verified proof hashes, and accumulates 1.5 ATMA tokens per task into their vault.

---

## 9. Network Topology, Deployment Specifications & Testnet Registry

### Network Configuration (BOT Chain / Bohr Testnet)

```ini
Network Name = BOT Chain Bohr Testnet
Chain ID = 968
Symbol = tBOT / BOHR
RPC URL = https://rpc.bohr.life
Block Explorer = https://scan.bohr.life
EVM Version Target = shanghai
Consensus Mechanism = Parlia PoSA (Proof of Staked Authority)
Block Time = ~0.75 seconds
```

### Verified Deployed Smart Contract Registry

```
AutonomeSettlementEscrow = 0x5b30dB9F00F9fa644a13117D5b31844223e3Fb4E
AutonomeToken (ATMA)     = 0xd29dE89D308b3F1eAcF3c36f821842F8F6f3f840
SimpleAccountFactory     = 0xBC88d6012b3bf8426C2851d3798cEB5257658332
ERC-4337 EntryPoint      = 0x0000000071727De22E5E9d8BAf0edAc6f37da032
```

### Canonical Local Port Assignment

| Service Port | Assignee Component | Description |
| :--- | :--- | :--- |
| **Port 3000** | Next.js Frontend (`autonome-frontend`) | Consumer User Studio & Operator Telemetry Web App |
| **Port 5173** | Vite / React (`autonome-desktop`) | Tauri Desktop App Frontend Dev Server |
| **Port 8000** | FastAPI Worker Daemon (`autonome/worker.py`) | DePIN Compute Worker Daemon & Sidecar Binary |
| **Port 8001** | *Reserved / Internal System* | *System process binding in Docker network namespace (Do Not Use)* |
| **Port 8002** | Intent Orchestrator (`orchestrator/engine.py`) | Primary Protocol Relayer, AI Intent Parser & Web3 Dispatcher |
| **Port 11434**| Ollama Local LLM Server | Local Llama 3 Model Endpoint |

---

## 10. Strategic Competitive Analysis

Autonome occupies a unique strategic position at the intersection of AI Agent Frameworks, DePIN Compute Networks, and Web3 Consumer Monetization.

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
| **Agent Monetization**| Open Developer Agent Registration (70% split) | None | Subnet Emissions | Staking Pools |
| **Payment Options** | USDT, BOT, ATMA, Stripe Fiat | AKT / USDC | TAO | FET |
| **Consumer Model** | Free 50 Daily Credits + Subscriptions | Pay-per-hour Container | Emission Halving | Staking Rewards |
| **Execution Sandbox** | Docker Micro-Containers | Kubernetes Clusters | Custom Subnets | Python Runtimes |
| **Hardware Setup UX** | 1-Click Tauri Desktop App | Complex CLI / K8s | Complex Subnet Mining | CLI Setup |
| **Wallet Model** | ERC-4337 Counterfactual Vaults | Standard Cosmos Address | Polkadot / Substrate Key | Cosmos Wallet |

---

## 11. Multi-Phase Technical Roadmap

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
- **OpenClaw & Custom Agent Marketplace**: Enable developers and individuals to register custom AI agents to the network and earn 70% revenue shares automatically.
- **Stripe Fiat-to-Crypto On-Ramp**: Implement Stripe payment gateway integration allowing users to purchase monthly credit subscriptions using debit/credit cards.
- **Freemium Daily Credit Reset**: Automate daily allocation of **50 free credits/day** for casual consumer task execution.

### Phase 8: Mainnet Launch & Cross-Chain Expansion (Future)
- Deploy Autonome core contracts to BOT Chain Mainnet (Chain ID `677`).
- Implement LayerZero / Wormhole cross-chain messaging to allow consumers on Ethereum, Arbitrum, and Solana to dispatch tasks to Autonome DePIN workers seamlessly.

---

## 12. Comprehensive Glossary & Reference

- **ATMA**: Autonome Token. The native ERC-20 utility, reward, and burn token of the Autonome ecosystem.
- **BOHR / tBOT**: The native gas token of BOT Chain Testnet (Chain ID 968).
- **BDEX V3**: The primary Decentralized Exchange on BOT Chain featuring Concentrated Liquidity pools.
- **Counterfactual Account**: An ERC-4337 smart account address calculated deterministically via `CREATE2` before the contract is physically deployed on-chain.
- **DePIN**: Decentralized Physical Infrastructure Network. A web3 model leveraging token rewards to motivate crowd-sourced physical hardware deployment.
- **EIP-191**: Ethereum standard for signed data payloads, preventing signed messages from being executed as valid transactions.
- **EIP-2612**: ERC-20 extension adding signed `permit()` approvals for gasless token allowances.
- **Ephemeral Key**: A temporary cryptographic key pair generated in volatile storage, used exclusively for data signing and decoupled from asset holdings.
- **Intent Orchestrator**: The central AI parsing engine that interprets natural language requests and coordinates multi-agent compute jobs.
- **OpenClaw**: A popular open-source AI agent and web scraping framework supported on the Autonome network for automated web workloads.
- **Proof of Completion**: A cryptographic signature payload generated by sub-agents and workers verifying that task execution succeeded before funds are un-escrowed.
- **Protocol-Owned Liquidity (POL)**: Liquidity owned directly by the smart contract protocol rather than individual liquidity providers, ensuring permanent DEX trading depth.
- **SimpleAccount**: The canonical ERC-4337 smart account implementation providing single-owner account abstraction functionality.
- **Validator**: An authorized address in the `AutonomeSettlementEscrow` contract permitted to call `settleTask()` and trigger reward distributions.
