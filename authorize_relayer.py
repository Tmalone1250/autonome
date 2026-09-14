import os
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
Account.enable_unaudited_hdwallet_features()
from dotenv import load_dotenv

load_dotenv()

DEPLOYER_PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
RELAYER_PRIVATE_KEY = os.getenv("RELAYER_PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider("https://rpc.bohr.life"))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

deployer_account = Account.from_key(DEPLOYER_PRIVATE_KEY)
relayer_account = Account.from_key(RELAYER_PRIVATE_KEY)

print(f"Deployer address: {deployer_account.address}")
print(f"Relayer address: {relayer_account.address}")

ESCROW_ADDRESS = "0x5b30dB9F00F9fa644a13117D5b31844223e3Fb4E"
ESCROW_ABI = [{
    "inputs": [{"internalType": "address", "name": "_validator", "type": "address"}],
    "name": "setValidator",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
}]

contract = w3.eth.contract(address=w3.to_checksum_address(ESCROW_ADDRESS), abi=ESCROW_ABI)

tx_dict = contract.functions.setValidator(
    w3.to_checksum_address(relayer_account.address)
).build_transaction({
    'from': deployer_account.address,
    'nonce': w3.eth.get_transaction_count(deployer_account.address),
    'chainId': 968,
    'gas': 100000,
    'gasPrice': w3.eth.gas_price
})

signed_tx = w3.eth.account.sign_transaction(tx_dict, private_key=DEPLOYER_PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

print(f"Transaction broadcasted! Hash: {tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print(f"Transaction mined! Status: {receipt.status}")
