import os
from dotenv import load_dotenv
from botchain.client import BotChain
from settlement import load_abi, ESCROW_ADDRESS

# Load environment variables
load_dotenv()

DEPLOYER_PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
NODE_PRIVATE_KEY = os.getenv("NODE_PRIVATE_KEY")

def main():
    if not DEPLOYER_PRIVATE_KEY or not NODE_PRIVATE_KEY:
        print("Missing private keys in .env")
        return

    # 1. Init SDK for deployer
    client = BotChain(private_key=DEPLOYER_PRIVATE_KEY, is_testnet=True)
    
    # 2. Get Node Address
    from eth_account import Account
    node_address = Account.from_key(NODE_PRIVATE_KEY).address
    print(f"Setting validator to Node Address: {node_address}")

    # 3. Load Escrow Contract
    escrow_abi = load_abi("AutonomeSettlementEscrow.sol")
    contract = client.w3.eth.contract(
        address=client.w3.to_checksum_address(ESCROW_ADDRESS),
        abi=escrow_abi
    )
    
    # 4. Check current validator
    current_validator = contract.functions.validator().call()
    print(f"Current validator is: {current_validator}")
    
    if current_validator.lower() == node_address.lower():
        print("Node is already the validator!")
        return

    # 5. Build and send transaction
    print("Building transaction...")
    deployer_address = client.account.address
    tx = contract.functions.setValidator(
        client.w3.to_checksum_address(node_address)
    ).build_transaction({
        'from': deployer_address,
        'nonce': client.w3.eth.get_transaction_count(deployer_address),
        'chainId': client.chain_id,
        'gasPrice': client.w3.eth.gas_price
    })
    
    print("Signing transaction...")
    signed_tx = client.w3.eth.account.sign_transaction(tx, private_key=DEPLOYER_PRIVATE_KEY)
    
    print("Sending transaction...")
    tx_hash = client.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction Hash: {client.w3.to_hex(tx_hash)}")
    
    print("Waiting for receipt...")
    receipt = client.w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Success! Gas used: {receipt.gasUsed}")

if __name__ == "__main__":
    main()
