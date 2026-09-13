# Autonome: DePIN AI Compute Node Ecosystem

**Autonome** is the DePIN (Decentralized Physical Infrastructure Network) AI worker node ecosystem built on the **BOT Chain** network. The platform connects decentralized hardware providers (Compute Nodes) with AI Sub-Agents, enabling fully verifiable, zero-gas LLM executions backed by smart contract settlements.

---

## 🏗️ Architecture Overview

Autonome consists of a deeply integrated three-tier architecture:

### 1. `autonome/` (Compute Node Backend)
The compute node layer runs on the local hardware of the DePIN worker (e.g., consumer laptops, rigs).
- **FastAPI Router (`worker.py`)**: Ingests tasks from the network orchestrator, communicates directly with local AI models (such as `Llama-3` running on Ollama via REST), and generates cryptographic execution proofs.
- **On-Chain Settlement (`settlement.py`)**: Interacts with the BOT Chain network to securely submit proofs on-chain. It builds the zero-gas payload and leverages an Automated Liquidity Manager (ALM) to automatically swap earned tokens for USDT on BDEX V3.
- **Hardware Isolation**: Executed entirely within a Docker container to ensure security while maintaining local host gateway access (`http://host.docker.internal:11434`) for accelerated local AI inference.

### 2. `autonome-contracts/` (Smart Contract Settlement Layer)
The on-chain truth and DePIN reward systems are built on standard EVM (Shanghai) Solidity contracts deployed on the BOT Chain (Mainnet: 677, Bohr Testnet: 968).
- **`AutonomeSettlementEscrow.sol`**: The core settlement contract. It verifies cryptographic execution proofs from worker nodes and processes the release of ATMA rewards to the Compute Node, the Sub-Agent Developer, and the Protocol Treasury. The entry point is `settleTask(bytes32 taskId, address subAgent, address computeNode)`.
- **`AutonomeToken.sol` (ATMA)**: The native utility and reward token of the Autonome ecosystem used to incentivize hardware providers.

### 3. `botchain-sdk-py/` (Middleware & Automation)
The official Python SDK bridging the Compute Node to the BOT Chain network, featuring:
- **Zero-Gas Paymaster Middleware (`MegaFuel`)**: Intercepts transactions and rewrites `gasPrice` to 0. It queries the `pm_isSponsorable` JSON-RPC endpoint to let the protocol treasury subsidize gas costs, abstracting away the need for node operators to hold gas tokens.
- **Agent Policy & Executor**: Standardized Model Context Protocol (MCP) tooling and trade policies to govern on-chain AI agent behaviors and swaps.
- **BDEX V3 & ALM Integration**: Provides deterministic tick math and optimal rebalancing routing to interact with BOT Chain's concentrated liquidity DEX (BDEX V3).

---

## 🚀 The Build & Workflow

Once a node operator joins the network, the complete autonomous workflow operates as follows:

1. **Task Ingestion**: The orchestrator assigns a prompt to the node via `POST /task`.
2. **Local Inference**: `worker.py` pings the local Ollama instance (running entirely off-chain on local CPU/GPU hardware).
3. **Cryptographic Proofing**: The node hashes the `task_id`, `prompt`, and `inference_result`, then signs the payload with the node's private EOA key.
4. **Zero-Gas Settlement**: `settlement.py` uses the `botchain-sdk-py` client to construct the `settleTask` transaction. The SDK's middleware intercepts it, approves sponsorship, and pushes it to the chain without consuming the node's native BOT tokens.
5. **Reward Distribution**: `AutonomeSettlementEscrow` receives the proof, updates the state, and mints/transfers ATMA tokens to the node operator.
6. **Automated Liquidity (ALM)**: (Optional) The node triggers an optimal rebalance sequence via `ALMManager`, pulling the earned ATMA and converting a portion to USDT directly on BDEX V3.

---

## 🛠️ Getting Started

### Prerequisites
- Docker & Docker Compose
- [Ollama](https://ollama.ai/) running locally with the `llama3` (or equivalent) model.
- An EOA Private Key for signing transactions.

### Running the Worker Node
1. Boot your local AI instance:
   ```bash
   ollama run llama3
   ```
2. Build the Docker image from the root directory:
   ```bash
   docker build -t autonome-worker -f autonome/Dockerfile .
   ```
3. Run the container:
   ```bash
   docker run -p 8000:8000 \
     -e NODE_PRIVATE_KEY="YOUR_PRIVATE_KEY" \
     --add-host=host.docker.internal:host-gateway \
     autonome-worker
   ```

The node will automatically listen on `http://localhost:8000/task` for incoming DePIN tasks and handle all interactions with the BOT Chain network seamlessly.
