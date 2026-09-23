import os
import json
from botchain.client import BotChain
from botchain.dex_alm import ALMManager
from botchain.dex import BDexManager

ESCROW_ADDRESS = "0xF54eA7205dc77C02FdCf86c4707f7cF7BDB3C372"
ATMA_TOKEN = "0xd29dE89D308b3F1eAcF3c36f821842F8F6f3f840"

def load_abi(filename):
    base_dir = os.path.dirname(__file__)
    json_name = filename.replace(".sol", ".json")
    local_abi_path = os.path.join(base_dir, "abis", json_name)
    out_abi_path = os.path.join(base_dir, "..", "autonome-contracts", "out", filename, json_name)
    
    path = local_abi_path if os.path.exists(local_abi_path) else out_abi_path
    if not os.path.exists(path):
        if filename == "AutonomeSettlementEscrow.sol":
            return [{
                "inputs": [
                    {"internalType": "bytes32", "name": "taskId", "type": "bytes32"},
                    {"internalType": "address", "name": "subAgent", "type": "address"},
                    {"internalType": "address", "name": "computeNode", "type": "address"}
                ],
                "name": "settleTask",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }]
        raise FileNotFoundError(f"ABI file not found at {path}")
    with open(path, 'r') as f:
        data = json.load(f)
        return data["abi"] if "abi" in data else data

def execute_settlement(task_id: str, sub_agent_address: str, private_key: str) -> str:
    # 1. Initialize SDK
    client = BotChain(private_key=private_key, is_testnet=True)
    client.enable_zero_gas_paymaster()

    # 2. Load Escrow Contract
    escrow_abi = load_abi("AutonomeSettlementEscrow.sol")
    contract = client.w3.eth.contract(
        address=client.w3.to_checksum_address(ESCROW_ADDRESS),
        abi=escrow_abi
    )

    node_address = client.account.address
    
    # Ensure task_id is bytes32
    if isinstance(task_id, str):
        if task_id.startswith('0x'):
            task_id_bytes = client.w3.to_bytes(hexstr=task_id)
        else:
            task_id_bytes = client.w3.keccak(text=task_id)
    else:
        task_id_bytes = task_id

    # 3. Build Transaction
    tx = contract.functions.settleTask(
        task_id_bytes,
        client.w3.to_checksum_address(sub_agent_address),
        client.w3.to_checksum_address(node_address)
    ).build_transaction({
        'from': node_address,
        'nonce': client.w3.eth.get_transaction_count(node_address),
        'chainId': client.chain_id,
        'gasPrice': client.w3.eth.gas_price
    })

    from botchain.middleware import check_and_apply_sponsorship
    tx = check_and_apply_sponsorship(client.w3, tx)

    signed_tx = client.w3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = client.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    return client.w3.to_hex(tx_hash)

def execute_liquidity_automation(private_key: str, token_id: int):
    """Optional ALM step: swaps earned ATMA for USDT and re-centers position"""
    client = BotChain(private_key=private_key, is_testnet=True)
    dex = BDexManager(client)
    alm = ALMManager(dex)
    
    USDT = "0xaBabc7Ddc03e501d190C676BF3d92ef0e6e87a3C"
    
    alm.execute_optimal_rebalance(
        token_id=token_id,
        token0=ATMA_TOKEN,
        token1=USDT,
        fee=3000,
        current_tick=0,
        tick_spacing=60,
        range_percentage=0.1
    )
