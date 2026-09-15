import re

with open("orchestrator/engine.py", "r") as f:
    content = f.read()

# 1. Add Queue Dictionaries and Endpoints
new_endpoints = """
PENDING_TASKS = {}
COMPLETED_TASKS = {}

class TaskManifest(BaseModel):
    task_id: str
    domain: str
    image: str
    env_vars: dict = {}
    operator_vault: str
    sub_agent: str

@app.post("/tasks/enqueue")
def enqueue_task(manifest: TaskManifest):
    PENDING_TASKS[manifest.task_id] = manifest.dict()
    return {"status": "enqueued", "task_id": manifest.task_id}

@app.get("/nodes/heartbeat")
def node_heartbeat(vault: str = "", node: str = ""):
    if not PENDING_TASKS:
        return {"status": "idle"}
    task_id = next(iter(PENDING_TASKS))
    task = PENDING_TASKS.pop(task_id)
    if vault and not task.get("operator_vault"):
        task["operator_vault"] = vault
    return task

@app.get("/tasks/status/{task_id}")
def get_task_status(task_id: str):
    if task_id in COMPLETED_TASKS:
        return {"status": "completed", "result": COMPLETED_TASKS[task_id]}
    if task_id in PENDING_TASKS:
        return {"status": "pending"}
    return {"status": "processing"}

class CompleteTaskRequest(BaseModel):
    task_id: str
    inference_result: str
    proof_hash: str
    signature: str
    sub_agent: str
    operator_vault: str

@app.post("/tasks/complete")
def complete_task(request: CompleteTaskRequest):
    t_id = request.task_id
    tx_hash = ""
    error = ""
    if relayer_account:
        print(f"Worker execution completed. Settling on-chain as Relayer...")
        try:
            contract = w3.eth.contract(address=w3.to_checksum_address(ESCROW_ADDRESS), abi=ESCROW_ABI)
            if t_id.startswith('0x'):
                task_id_bytes = w3.to_bytes(hexstr=t_id)
            else:
                task_id_bytes = w3.keccak(text=t_id)
            sub_agent_address = w3.to_checksum_address(request.sub_agent)
            operator_vault = w3.to_checksum_address(request.operator_vault)
            
            import subprocess
            import os
            deposit_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "deposit_task.py"))
            subprocess.run(["python3", deposit_script, t_id], check=True)

            tx_dict = contract.functions.settleTask(
                task_id_bytes,
                sub_agent_address,
                operator_vault
            ).build_transaction({
                'from': relayer_account.address,
                'nonce': w3.eth.get_transaction_count(relayer_account.address),
                'chainId': 968,
                'gas': 1500000,
                'gasPrice': w3.eth.gas_price
            })
            signed_tx = w3.eth.account.sign_transaction(tx_dict, private_key=RELAYER_PRIVATE_KEY)
            tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = w3.to_hex(tx_hash_bytes)
            
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=15)
            if receipt.status != 1:
                raise RuntimeError(f"Settlement reverted on-chain: {tx_hash}")
                
            print(f"Successfully settled task {t_id} with tx_hash {tx_hash}")
        except Exception as e:
            error = f"Relayer settlement failed: {str(e)}"
            print(error)

    COMPLETED_TASKS[t_id] = {
        "inference_result": request.inference_result,
        "proof_hash": request.proof_hash,
        "settlement_tx_hash": tx_hash,
        "error": error
    }
    return {"status": "completed", "task_id": t_id, "tx_hash": tx_hash}
"""

content = content.replace('OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")', 'OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")\n\n' + new_endpoints)

# 2. Remove Settlement Logic from /orchestrate
# We'll use regex to remove everything from "# 3. Relayer Settlement" to the end of the return statement
import re
pattern = r'# 3\. Relayer Settlement.*?(?=# 4\. Return full lifecycle result)'
content = re.sub(pattern, '', content, flags=re.DOTALL)

with open("orchestrator/engine.py", "w") as f:
    f.write(content)
