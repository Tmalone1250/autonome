# **BOT Chain Master Architecture and Development Specification**

## **1\. Executive Summary & Ecosystem Reality**

BOT Chain operates as an AI and DePIN-focused Layer 1 utilizing a three-tier decoupled architecture (Core Layer, Verifiable Execution Layer, and Modular Protocol Layer). Underneath the hood, the network relies on specific EVM constraints that developers and AI agents must strictly follow:

* **Underlying Engine:** The network is a heavily modified Geth/BSC fork.  
* **Consensus:** Proof of Staked Authority (PoSA) utilizing the Parlia consensus engine (BEP-126/BEP-341), delivering \~0.75s block times.  
* **EVM Target:** Pinned strictly to the **"shanghai"** upgrade. The network does *not* support Dencun opcodes (e.g., TSTORE, TLOAD, MCOPY). All smart contract compilations must strictly target evmVersion: "shanghai".  
* **Security Boundary:** The native node binaries utilize an unvetted, tampered go-bip39 library. **Do not run local node binaries or generate keys using their CLI.** All development must route through public JSON-RPC endpoints using standard EVM tooling (e.g., web3.py, Foundry) and standard EOA cryptography.  
* **Public RPC Limitation:** The eth\_getLogs method is **disabled** on the mainnet public RPC (https://rpc.botchain.ai). Event polling must be handled via WebSockets or third-party indexers.

## **2\. Network Parameters & Endpoints**

| Parameter | BOT Chain Mainnet | BOT Chain Testnet (Bohr) |
| :---- | :---- | :---- |
| **Chain ID** | 677 (0x2a5) | 968 (0x3c8) |
| **Public RPC** | https://rpc.botchain.ai | https://rpc.bohr.life |
| **Explorer** | https://scan.botchain.ai | https://scan.bohr.life |
| **Bundler RPC** | https://bundler.botchain.ai/rpc/ | https://bundler.bohr.life/rpc/ |
| **Native Token** | BOT | tBOT |

## **3\. Verified Contract Registry (Mainnet \- Chain ID 677\)**

BOT Chain utilizes a Uniswap V3 exact fork for its native DEX (BDEX V3).

* **V3 Factory:** 0x1C51c173323ec11BB4e3C4fD2314c225Dc4b5419  
* **SwapRouter:** 0x07032d47A1b9f8460cBeE9dC17c1d3E438693929  
* **QuoterV2:** 0x034A705b36067cff99ABf5C662Be881cBd8d0176  
* **NonfungiblePositionManager:** 0xDAc3FcFF004d8a8675b94E44941A1a2e3b240090

## **4\. Tokenomics & Execution Economics**

* **Supply:** 150,000,000 BOT fixed hard-cap.  
* **Transaction Fee:** 0.001 BOT per basic transaction.  
* **Deflationary Split:** 50% of gas is permanently burned, 20% is routed to nodes, and 30% is allocated to the ECO-FUND.  
* **Dual Mining:** Nodes can simultaneously participate in PoS staking and DePIN resource contribution mining.

## **5\. Account Abstraction & EOA Paymaster (MegaFuel)**

BOT Chain offers two distinct paths for transaction sponsorship:

### **Path A: EOA Paymaster (MegaFuel / MEV Bundling)**

* **How it works:** An Externally Owned Account (EOA) signs a transaction with gasPrice \= 0x0.  
* **Validation:** The payload is sent to the custom JSON-RPC method pm\_isSponsorable.  
* **Execution:** If approved by the sponsor policy, the transaction is submitted via eth\_sendRawTransaction. An MEV builder atomically bundles the zero-gas transaction with a sponsor transaction that pays the priority fee.

### **Path B: Canonical ERC-4337 (v0.7)**

* **How it works:** Smart contract wallets submit PackedUserOperation payloads to the dedicated Bundler RPC via eth\_sendUserOperation.  
* **Validation:** Processed natively through the EntryPoint contract (0x0000000071727De22E5E9d8BAf0edAc6f37da032) using a standard ERC-4337 Paymaster.

## **6\. Antigravity AI Core Constraints (.ai\_rules)**

When building SDKs, Compute Nodes, or related infrastructure, AI agents must adhere to the following constraints:

Trigger: Glob \*.py

\* Network Specs: All Web3 instances must connect exclusively to https://rpc.botchain.ai (Chain ID 677\) or https://rpc.bohr.life (Chain ID 968).  
\* Middleware Injection: All Web3 instances MUST inject \`geth\_poa\_middleware\` at layer 0 to handle Parlia consensus headers.  
\* Compiler Target: All contract interactions must assume the "shanghai" EVM target.  
\* Zero-Gas Middleware: Implement the EOA Paymaster via \`w3.middleware\_onion.inject\`. The middleware must intercept transactions, call the custom \`pm\_isSponsorable\` RPC method, and rewrite the transaction \`gasPrice\` to 0x0 upon policy approval.  
\* DEX Architecture: BDEX is a Uniswap V3 clone. Use standard Uniswap V3 ABIs mapped to the verified addresses.  
\* Logs Warning: Do not use \`eth\_getLogs\` on the mainnet public RPC.  
\* Cryptography: Manage local signing exclusively via standard web3.py EOA account structures. Never use BOT Chain node CLIs.

## **7\. DePIN AI Compute Node Blueprint**

The Autonome worker node architecture follows a strict sequence to monetize idle resources without requiring operators to pre-fund wallets:

1. **Inference Layer:** Local LLMs or AI sub-agents execute tasks securely inside isolated Docker containers.  
2. **API Routing:** A FastAPI backend ingests compute tasks from the Orchestrator and generates cryptographic execution proofs.  
3. **On-Chain Settlement:**  
   * The node formats a zero-gas transaction using botchain-sdk-py.  
   * The SDK pings the pm\_isSponsorable endpoint to subsidize gas via the protocol treasury.  
   * The execution is logged on-chain, triggering an automated release of ATMA rewards to the node, the sub-agent developer, and the POL treasury.  
4. **Liquidity Automation:** The platform utilizes an Automated Liquidity Manager (ALM) to programmatically swap earned protocol tokens for USDT on BDEX V3, deepening concentrated liquidity.