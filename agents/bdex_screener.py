import os
import secrets
import requests
from web3 import Web3
import json

# Network Configuration - Read Layer (BOT Chain Mainnet)
RPC_URL = "https://rpc.botchain.ai"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# BDEX QuoterV2 Contract (Uniswap V3 Fork)
QUOTER_V2_ADDRESS = "0x034A705b36067cff99ABf5C662Be881cBd8d0176"
QUOTER_V2_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "internalType": "struct IQuoterV2.QuoteExactInputSingleParams",
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
            {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Asset Configurations
WBOT_ADDRESS = "0xD5452816194a3784dBa983426cCe7c122F4abd30"
USDT_ADDRESS = "0xaBabc7Ddc03e501d190C676BF3d92ef0e6e87a3C"
POOL_FEE = 3000  # 0.3%

# DePIN Compute Node Endpoint (Settlement Layer)
WORKER_URL = os.environ.get("WORKER_URL", "http://localhost:8000")
NODE_ENDPOINT = f"{WORKER_URL}/task"
# Simulated Sub-Agent Address
SUB_AGENT_ADDRESS = "0x0000000000000000000000000000000000000001"

def get_operator_vault() -> str:
    """
    Fetches the operator's real vault address from the live worker node.
    The worker holds this in-memory after the desktop app calls /set_vault.
    Falls back to OPERATOR_VAULT env var, then a zero address.
    """
    try:
        res = requests.get(f"{WORKER_URL}/status", timeout=5)
        if res.status_code == 200:
            vault = res.json().get("operator_vault_debug", "")
            if vault and vault.startswith("0x") and len(vault) == 42:
                print(f"[BDEXScreener] Resolved operator vault from worker: {vault}")
                return vault
    except Exception as e:
        print(f"[BDEXScreener] Warning: Could not fetch vault from worker: {e}")
    
    env_vault = os.environ.get("OPERATOR_VAULT", "")
    if env_vault and env_vault.startswith("0x"):
        print(f"[BDEXScreener] Using OPERATOR_VAULT env var: {env_vault}")
        return env_vault
    
    print("[BDEXScreener] CRITICAL: No valid operator vault found. Task will be aborted.")
    return ""

def get_onchain_quote(amount_in_wbot: float) -> float:
    """
    Fetches the expected USDT output for a given amount of WBOT using BDEX QuoterV2 on Mainnet.
    WBOT has 18 decimals, USDT has 6 decimals.
    """
    quoter = w3.eth.contract(address=w3.to_checksum_address(QUOTER_V2_ADDRESS), abi=QUOTER_V2_ABI)
    
    # Format the QuoteExactInputSingleParams struct
    params = (
        w3.to_checksum_address(WBOT_ADDRESS),
        w3.to_checksum_address(USDT_ADDRESS),
        w3.to_wei(amount_in_wbot, 'ether'),  # WBOT has 18 decimals
        POOL_FEE,
        0  # No price limit
    )
    
    print(f"Fetching on-chain quote for {amount_in_wbot} WBOT from BDEX V3 Mainnet...")
    try:
        # Call the quoter contract
        result = quoter.functions.quoteExactInputSingle(params).call()
        amount_out_raw = result[0]
        
        # USDT has 6 decimals, so divide by 10**6
        usdt_received = amount_out_raw / (10**6)
        return usdt_received
    except Exception as e:
        print(f"Failed to fetch quote: {e}")
        return 0.0

def run_agent(task_id: str, parameters: dict, prompt_intent: str) -> dict:
    """
    Callable sub-agent entry point.
    Receives parsed intent, fetches on-chain context, formats the payload, and dispatches to the Compute Node.
    """
    print(f"--- BDEX Screener Sub-Agent (Dual-Chain Aware) ---")
    
    amount_in = float(parameters.get("amount_in", 10.0))
    expected_usdt = get_onchain_quote(amount_in)
    
    if expected_usdt == 0.0:
        return {"error": "Aborting task dispatch due to missing on-chain context."}
        
    rate = expected_usdt / amount_in
    print(f"On-Chain Swap Rate: 1 WBOT = {rate:.4f} USDT\n")
    
    # Enrich the original intent with on-chain context
    enriched_prompt = (
        f"{prompt_intent}\n"
        f"--- ON-CHAIN CONTEXT ---\n"
        f"The current BDEX V3 swap rate is {rate:.4f} USDT per WBOT.\n"
        f"Analyze based on this live rate."
    )
    
    # 3. Resolve the real operator vault before dispatching (if known locally)
    # The worker can also supply this during the heartbeat if empty.
    operator_vault = get_operator_vault()

    # 4. Enqueue to Orchestrator Pull Queue
    payload = {
        "task_id": task_id,
        "domain": "Web3 & DeFi",
        "image": "alpine",
        "env_vars": {"PROMPT": enriched_prompt},
        "operator_vault": operator_vault or "0x0000000000000000000000000000000000000000",
        "sub_agent": SUB_AGENT_ADDRESS
    }
    
    import time
    enqueue_url = "http://127.0.0.1:8002/tasks/enqueue"
    status_url = f"http://127.0.0.1:8002/tasks/status/{task_id}"

    print(f"Enqueuing task {task_id} for Pull Workers ...")
    try:
        response = requests.post(enqueue_url, json=payload, timeout=5)
        if response.status_code != 200:
            return {"error": f"Orchestrator Enqueue Error: {response.text}"}
        
        print("\n✅ Task Successfully Enqueued for Pull Workers!")
        return {"status": "enqueued", "task_id": task_id}

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to enqueue task: {e}"}

if __name__ == "__main__":
    # Test execution
    test_task = "0x" + secrets.token_hex(32)
    print(run_agent(test_task, {"amount_in": 10.0}, "Analyze the optimal tick spacing for a new pool."))
