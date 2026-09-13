# BOT Chain: Master Development & Architecture Specification

## 1. Executive Summary & Ecosystem Reality
BOT Chain operates as an AI and DePIN-focused Layer 1 utilizing a three-tier decoupled architecture (Core Layer, Verifiable Execution Layer, and Modular Protocol Layer)[cite: 3]. Underneath the hood, the network relies on specific EVM constraints that developers must follow:

*   **Underlying Engine:** The network is a heavily modified Geth/BSC fork[cite: 1].
*   **Consensus:** Proof of Staked Authority (PoSA) utilizing the Parlia consensus engine (BEP-126/BEP-341), delivering ~0.75s block times[cite: 1].
*   **EVM Target:** Pinned strictly to the **"shanghai"** upgrade[cite: 1]. The network does *not* support Dencun opcodes (e.g., `TSTORE`, `TLOAD`, `MCOPY`)[cite: 1]. 
*   **Security Boundary:** The native node binaries utilize a tampered `go-bip39` library[cite: 1]. Developers must avoid local node binaries for key generation and exclusively use standard EVM tooling (e.g., `web3.py`, Foundry) over public JSON-RPC endpoints[cite: 1].
*   **Public RPC Limitation:** The `eth_getLogs` method is disabled on the mainnet public RPC (`https://rpc.botchain.ai`)[cite: 1]. Event polling must be handled via WebSockets or third-party indexers[cite: 1].

---

## 2. Network Parameters & Endpoints

| Parameter | BOT Chain Mainnet | BOT Chain Testnet (Bohr) |
| :--- | :--- | :--- |
| **Chain ID** | 677 (0x2a5) | 968 (0x3c8) |
| **Public RPC** | https://rpc.botchain.ai | https://rpc.bohr.life |
| **Explorer** | https://scan.botchain.ai | https://scan.bohr.life |
| **Bundler RPC** | https://bundler.botchain.ai/rpc/ | https://bundler.bohr.life/rpc/ |
| **Native Token** | BOT | tBOT |

*(Data derived from network specifications[cite: 1, 4])*

---

## 3. Verified Contract Registry (Mainnet - Chain ID 677)
BOT Chain utilizes a Uniswap V3 exact fork for its native DEX (BDEX V3)[cite: 1, 5]. 

*   **V3 Factory:** `0x1C51c173323ec11BB4e3C4fD2314c225Dc4b5419`[cite: 1, 5]
*   **SwapRouter:** `0x07032d47A1b9f8460cBeE9dC17c1d3E438693929`[cite: 1, 5]
*   **QuoterV2:** `0x034A705b36067cff99ABf5C662Be881cBd8d0176`[cite: 1, 5]
*   **NonfungiblePositionManager:** `0xDAc3FcFF004d8a8675b94E44941A1a2e3b240090`[cite: 1]

---

## 4. Tokenomics & Execution Economics
*   **Supply:** 150,000,000 BOT fixed hard-cap[cite: 3].
*   **Transaction Fee:** 0.001 BOT per basic transaction[cite: 3].
*   **Deflationary Split:** 50% of gas is permanently burned, 20% is routed to nodes, and 30% is allocated to the ECO-FUND[cite: 3].
*   **Dual Mining:** Nodes can simultaneously participate in PoS staking and DePIN resource contribution mining[cite: 3].

---

## 5. Antigravity AI Core Constraints (`.ai_rules`)
When building the `botchain-sdk-py` or related infrastructure, AI agents must adhere to the following constraints[cite: 1]:

*   **Network Specs:** Connect exclusively to `https://rpc.botchain.ai` (Chain ID 677) for mainnet operations[cite: 1].
*   **Compiler Target:** All smart contracts must compile with `evmVersion: "shanghai"`[cite: 1].
*   **Zero-Gas Middleware:** Implement the EOA Paymaster via `w3.middleware_onion.inject`[cite: 1]. The middleware intercepts transactions, calls the custom `pm_isSponsorable` RPC method, and sets `gasPrice` to `0x0` upon policy approval[cite: 1].
*   **DEX Architecture:** Use standard Uniswap V3 ABIs mapped to the verified BDEX addresses[cite: 1].
*   **Logs Warning:** Do not utilize `eth_getLogs` on the mainnet public RPC[cite: 1].
*   **Cryptography:** Handle local signing strictly via standard `web3.py` EOA account structures[cite: 1].

---

## 6. DePIN AI Compute Node Blueprint
The worker node architecture follows a strict sequence to monetize idle resources without requiring operators to pre-fund wallets[cite: 1]:

1.  **Inference Layer:** Local LLMs or AI agents execute tasks securely inside isolated Docker containers[cite: 1].
2.  **API Routing:** A FastAPI backend ingests compute tasks and generates cryptographic execution proofs[cite: 1].
3.  **On-Chain Settlement:** 
    *   The node formats a zero-gas transaction using `botchain-sdk-py`[cite: 1].
    *   The SDK pings the `pm_isSponsorable` endpoint to subsidize gas via the protocol treasury[cite: 1].
    *   The execution is logged on-chain, triggering an automated release of BOT rewards to the node[cite: 1].
4.  **Liquidity Automation:** Nodes can optionally use the SDK to programmatically swap BOT for USDT on BDEX V3[cite: 1].