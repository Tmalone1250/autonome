import os
from dotenv import load_dotenv
from botchain.client import BotChain
from eth_account import Account

load_dotenv()

DEPLOYER_PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
NODE_PRIVATE_KEY = os.getenv("NODE_PRIVATE_KEY")

def main():
    if not DEPLOYER_PRIVATE_KEY or not NODE_PRIVATE_KEY:
        print("Missing private keys in .env")
        return

    # Init client with deployer
    client = BotChain(private_key=DEPLOYER_PRIVATE_KEY, is_testnet=True)
    
    deployer_address = client.account.address
    node_address = Account.from_key(NODE_PRIVATE_KEY).address
    
    # Check balances
    deployer_bal = client.w3.eth.get_balance(deployer_address)
    node_bal = client.w3.eth.get_balance(node_address)
    
    print(f"Deployer Balance: {client.w3.from_wei(deployer_bal, 'ether')} BOHR")
    print(f"Node Balance: {client.w3.from_wei(node_bal, 'ether')} BOHR")
    
    if node_bal >= client.w3.to_wei(0.1, 'ether'):
        print("Node already has enough funds for gas!")
        return
        
    print(f"Funding Node {node_address} with 1 BOHR for gas fees...")
    
    tx = {
        'to': node_address,
        'value': client.w3.to_wei(1, 'ether'),
        'gas': 21000,
        'gasPrice': client.w3.eth.gas_price,
        'nonce': client.w3.eth.get_transaction_count(deployer_address),
        'chainId': client.chain_id
    }
    
    signed_tx = client.w3.eth.account.sign_transaction(tx, private_key=DEPLOYER_PRIVATE_KEY)
    tx_hash = client.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Funding Tx Hash: {client.w3.to_hex(tx_hash)}")
    
    client.w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Node successfully funded!")
    
    # Verify new balance
    new_bal = client.w3.eth.get_balance(node_address)
    print(f"New Node Balance: {client.w3.from_wei(new_bal, 'ether')} BOHR")

if __name__ == "__main__":
    main()
