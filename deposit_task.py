import os
import sys
from dotenv import load_dotenv
from botchain.client import BotChain
from settlement import load_abi, ESCROW_ADDRESS
from eth_account import Account

load_dotenv()

DEPLOYER_PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
ATMA_TOKEN_ADDRESS = "0xd29dE89D308b3F1eAcF3c36f821842F8F6f3f840"

# Standard ERC20 ABI for approve
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def main():
    if not DEPLOYER_PRIVATE_KEY:
        print("Missing DEPLOYER_PRIVATE_KEY in .env")
        return

    client = BotChain(private_key=DEPLOYER_PRIVATE_KEY, is_testnet=True)
    deployer_address = client.account.address
    print(f"Using Deployer Address: {deployer_address}")

    # Configuration
    task_id_str = sys.argv[1] if len(sys.argv) > 1 else "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    if task_id_str.startswith("0x"):
        task_id_str = task_id_str[2:]
    task_id = bytes.fromhex(task_id_str)
    amount = client.w3.to_wei(10, 'ether') # 10 ATMA

    # 1. Approve Escrow Contract to spend ATMA
    print("Approving Escrow Contract to spend ATMA...")
    atma_contract = client.w3.eth.contract(
        address=client.w3.to_checksum_address(ATMA_TOKEN_ADDRESS),
        abi=ERC20_ABI
    )
    
    current_nonce = client.w3.eth.get_transaction_count(deployer_address, 'pending')
    
    tx = atma_contract.functions.approve(
        client.w3.to_checksum_address(ESCROW_ADDRESS),
        amount
    ).build_transaction({
        'from': deployer_address,
        'nonce': current_nonce,
        'chainId': client.chain_id,
        'gasPrice': client.w3.eth.gas_price
    })
    
    signed_tx = client.w3.eth.account.sign_transaction(tx, private_key=DEPLOYER_PRIVATE_KEY)
    tx_hash = client.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Approval Tx Hash: {client.w3.to_hex(tx_hash)}")
    client.w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Approval confirmed!")

    # 2. Deposit Intent in Escrow
    print("Depositing task intent to Escrow...")
    escrow_abi = load_abi("AutonomeSettlementEscrow.sol")
    escrow_contract = client.w3.eth.contract(
        address=client.w3.to_checksum_address(ESCROW_ADDRESS),
        abi=escrow_abi
    )
    
    tx = escrow_contract.functions.depositIntent(
        task_id,
        amount
    ).build_transaction({
        'from': deployer_address,
        'nonce': current_nonce + 1,
        'chainId': client.chain_id,
        'gasPrice': client.w3.eth.gas_price
    })
    
    signed_tx = client.w3.eth.account.sign_transaction(tx, private_key=DEPLOYER_PRIVATE_KEY)
    tx_hash = client.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Deposit Tx Hash: {client.w3.to_hex(tx_hash)}")
    client.w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Task successfully escrowed!")

if __name__ == "__main__":
    main()
