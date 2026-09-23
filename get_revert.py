import sys
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://rpc.bohr.life"))
tx_hash = "0xb9bb59e5270514b40dcd1f5a5ad9a935c46ab695ec7697cc0880de9a150dec4a"

tx = w3.eth.get_transaction(tx_hash)
try:
    w3.eth.call({
        'to': tx['to'],
        'from': tx['from'],
        'value': tx['value'],
        'data': tx['input'],
        'gas': tx['gas'],
        'gasPrice': tx['gasPrice']
    }, tx.blockNumber - 1)
except Exception as e:
    print(f"Revert Reason: {e}")
