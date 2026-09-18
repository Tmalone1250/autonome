# Autonome Core Engine & DePIN Worker Node (`autonome/`)

The **Autonome Core Engine & DePIN Worker Node** is the backend execution engine of the BOT Chain Autonomous DePIN Compute Network. It provides agent orchestration, local LLM inference via Ollama, Docker container sandboxing, cryptographic proof signing, and automated web3 settlement dispatching.

---

## Architecture Overview

The `autonome` module comprises two primary runtime components:

1. **Intent Orchestrator (`orchestrator/engine.py`)**: Runs on **Port 8002**. Receives natural language prompts from the frontend, extracts parameters via Llama 3/Ollama, invokes specialized sub-agents, dispatches compute jobs to active worker nodes, and executes smart contract settlement on BOT Chain (Bohr Testnet).
2. **DePIN Compute Worker Node (`worker.py`)**: Runs on **Port 8000**. Operates as a lightweight FastAPI daemon (or standalone PyInstaller binary inside the Tauri Desktop App). It accepts compute tasks, executes isolated Docker containers, logs execution telemetry to an internal SQLite database, signs execution proofs with an auto-generated ephemeral EOA key, and exposes status endpoints.

```
       [ Consumer Frontend / App ]
                    │
                    ▼  (Port 8002)
         ┌─────────────────────┐
         │ Intent Orchestrator │ ──(Llama 3 Param Extraction)
         └──────────┬──────────┘
                    │
                    ▼  (Port 8000)
       ┌─────────────────────────┐
       │   DePIN Worker Node     │
       │ ┌─────────────────────┐ │
       │ │   Docker Sandbox    │ │
       │ └─────────────────────┘ │
       │  (Ephemeral Key Sign)   │
       └────────────┬────────────┘
                    │
                    ▼
    ┌──────────────────────────────┐
    │ AutonomeSettlementEscrow.sol │ ──(70/15/15 Token Split)
    └──────────────────────────────┘
```

---

## Directory Structure

```
autonome/
├── agents/
│   └── bdex_screener.py       # Sub-agent module for DEX token screening & data aggregation
├── orchestrator/
│   └── engine.py              # FastAPI Orchestrator (Port 8002) & Web3 Settlement Relayer
├── docs/                      # Technical specifications & architecture reference docs
├── worker.py                  # FastAPI Compute Worker Node (Port 8000)
├── settlement.py              # Web3 Settlement helper routines (Web3.py)
├── authorize_relayer.py       # Admin script: Register relayer address in Escrow contract
├── deposit_task.py            # Admin script: Deposit tBOT/ATMA escrow funds for tasks
├── set_validator.py           # Admin script: Register validator addresses
├── fund_node.py               # Utility: Transfer gas BOHR to ephemeral worker wallets
├── build_worker.sh            # PyInstaller packaging script for Tauri desktop sidecar
├── worker-bin.spec            # PyInstaller specification file
├── Dockerfile                 # Standalone worker node container image
├── docker-compose.yml         # Container orchestration manifest
├── requirements.txt           # Python dependency specifications
└── .env                       # Environment configuration file
```

---

## Core Features & Functionality

### 1. Intent Orchestrator (`orchestrator/engine.py`)
- **Natural Language Parsing**: Translates user prompts into structured execution payloads using local LLM models (e.g., Llama 3 via Ollama).
- **Sub-Agent Routing**: Dynamically matches prompts with specialized agent handlers (e.g., `bdex_screener.py` for decentralized finance analytics).
- **Gas-Managed Settlement**: Acts as the centralized protocol relayer. Obtains cryptographic proofs from workers and executes `settleTask(taskId, subAgent, operatorVault)` on `AutonomeSettlementEscrow.sol`.
- **Proof Relay & Status Syncing**: Post-settlement, asynchronously updates worker execution logs with the resulting on-chain transaction hash (`settlement_tx_hash`).

### 2. DePIN Compute Worker Node (`worker.py`)
- **Docker Container Isolation**: Pulls and runs isolated micro-containers (e.g., `python:3.10-slim`) to execute task code securely without host filesystem exposure.
- **Ephemeral Wallet Management**: Generates a local, encrypted Secp256k1 keypair on first boot saved at `~/.autonome/worker_key.json`. Operators never handle private keys manually.
- **Keccak256 Cryptographic Verification**: Hashes execution logs, stdout/stderr, and output artifacts, producing an Ethereum EIP-191 signature (`proof_hash` + `signature`).
- **Dynamic Vault Syncing**: Accepts node operator vault address updates via `/set_vault` to ensure reward routing to ERC-4337 smart account vaults.
- **Local Persistence**: Stores task metadata, proof hashes, execution logs, and transaction links in SQLite (`~/.autonome/worker.db`).

---

## API Reference

### Orchestrator Endpoints (`http://localhost:8002`)

| Endpoint | Method | Description | Payload / Query |
| :--- | :--- | :--- | :--- |
| `/prompt` | `POST` | Primary entrypoint for user prompts. Parses intent, delegates to sub-agents, triggers worker, and settles on-chain. | `{"prompt": "string"}` |
| `/tasks` | `GET` | Retrieves full listing of orchestrator execution logs and settlement records. | N/A |
| `/health` | `GET` | System health check and model connectivity status. | N/A |
| `/admin/nodes` | `GET` | (Protected) Retrieves the full registry of connected worker nodes, capabilities, and health status. | N/A |
| `/admin/queues` | `GET` | (Protected) Retrieves queue metrics and task orchestration routing status. | N/A |

### Worker Node Endpoints (`http://localhost:8000`)

| Endpoint | Method | Description | Payload / Query |
| :--- | :--- | :--- | :--- |
| `/execute` | `POST` | Receives and executes code inside a Docker container. Generates signed proof. | `{"task_id": "string", "code": "string", "operator_vault": "0x..."}` |
| `/logs` | `GET` | Fetches historical execution records and settlement transaction hashes. | N/A |
| `/logs/{task_id}` | `PATCH` | Updates a specific task's `settlement_tx_hash` post-on-chain execution. | `{"settlement_tx_hash": "0x..."}` |
| `/set_vault` | `POST` | Updates the active Node Operator ERC-4337 Vault address. | `{"operator_vault": "0x..."}` |
| `/node_info` | `GET` | Exposes node ephemeral EOA wallet address, vault address, and system metrics. | N/A |

---

## Environment Configuration (`.env`)

Create or update `.env` in `autonome/` with the following variables:

```ini
# BOT Chain RPC Node
RPC_URL=https://rpc.bohr.life
CHAIN_ID=968

# Protocol Contracts (Bohr Testnet)
ESCROW_CONTRACT_ADDRESS=0x5b30dB9F00F9fa644a13117D5b31844223e3Fb4E
ATMA_TOKEN_ADDRESS=0xd29dE89D308b3F1eAcF3c36f821842F8F6f3f840

# Orchestrator Relayer EOA Private Key (Must have BOHR gas)
RELAYER_PRIVATE_KEY=0x...

# Worker Node Settings
WORKER_PORT=8000
ORCHESTRATOR_PORT=8002
OLLAMA_HOST=http://localhost:11434
```

---

## Local Setup & Development

### Prerequisites
- **Python**: 3.10 or higher
- **Docker**: Docker Engine / Desktop running locally
- **Ollama**: Installed and running with `llama3` model pulled (`ollama pull llama3`)

### Virtual Environment Setup

```bash
# Navigate to autonome directory
cd autonome

# Create and activate virtual environment
python3 -m venv .autonome-venv
source .autonome-venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Components Individually

**1. Start Worker Node (Port 8000):**
```bash
python worker.py
```

**2. Start Intent Orchestrator (Port 8002):**
```bash
uvicorn orchestrator.engine:app --host 0.0.0.0 --port 8002 --reload
```

---

## PyInstaller Desktop Sidecar Packaging

The Tauri Desktop App bundles `worker.py` as a standalone binary executable (`worker-bin`). To compile the binary:

```bash
chmod +x build_worker.sh
./build_worker.sh
```

This generates `dist/worker-bin`, which is automatically copied to `autonome-desktop/binaries/worker-bin-x86_64-unknown-linux-gnu`.

---

## Utility Scripts

- **`authorize_relayer.py`**: Grants the orchestrator relayer address `SETTLER_ROLE` in the `AutonomeSettlementEscrow` contract.
- **`set_validator.py`**: Adds worker node addresses to the authorized validator whitelist.
- **`deposit_task.py`**: Escrows tBOT / ATMA rewards into the smart contract for task funding.
- **`fund_node.py`**: Sends initial BOHR native gas tokens to newly generated worker node ephemeral addresses.
