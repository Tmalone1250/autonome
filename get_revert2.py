import sys
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://rpc.bohr.life"))
tx_hash = "0x31615571bf05773d229011b28197a68c3b33d534f2ac00f3f3e939c2b41c73f9"

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
