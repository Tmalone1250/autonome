import os
import sys
import json
import secrets
import signal
import socket
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

def free_port(port: int):
    """Kill any process holding a given port so we can bind cleanly."""
    try:
        import subprocess
        result = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True)
        pids = result.stdout.strip().split()
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
                print(f"[Orchestrator] Freed port {port} (killed PID {pid})")
            except (ProcessLookupError, PermissionError) as e:
                print(f"[Orchestrator] Could not kill PID {pid}: {e}")
    except Exception as e:
        print(f"[Orchestrator] Port-free check skipped: {e}")

# Ensure port 8002 is free before app initializes
_ORCHESTRATOR_PORT = int(os.environ.get("ORCHESTRATOR_PORT", "8002"))
free_port(_ORCHESTRATOR_PORT)

# Ensure we can import from autonome/agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.bdex_screener import run_agent as bdex_run_agent

from dotenv import load_dotenv
load_dotenv()
RELAYER_PRIVATE_KEY = os.getenv("RELAYER_PRIVATE_KEY")
if not RELAYER_PRIVATE_KEY:
    print("Warning: RELAYER_PRIVATE_KEY not set in .env")

from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as poa_middleware
except ImportError:
    try:
        from web3.middleware import geth_poa_middleware as poa_middleware
    except ImportError:
        poa_middleware = None

from eth_account import Account
Account.enable_unaudited_hdwallet_features()

# Setup Web3 for Bohr Testnet
w3 = Web3(Web3.HTTPProvider("https://rpc.bohr.life"))
if poa_middleware:
    w3.middleware_onion.inject(poa_middleware, layer=0)
if RELAYER_PRIVATE_KEY:
    relayer_account = Account.from_key(RELAYER_PRIVATE_KEY)
    w3.eth.default_account = relayer_account.address
else:
    relayer_account = None

ESCROW_ADDRESS = "0x5b30dB9F00F9fa644a13117D5b31844223e3Fb4E"
ESCROW_ABI = [{
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

app = FastAPI(title="Autonome Orchestrator", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


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


@app.get("/health")
@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "Autonome Orchestrator",
        "port": _ORCHESTRATOR_PORT,
        "relayer_address": relayer_account.address if relayer_account else None,
        "ollama_host": OLLAMA_HOST
    }

class OrchestrateRequest(BaseModel):
    prompt: str
    domain: str
    user_address: str

@app.post("/orchestrate")
def orchestrate(request: OrchestrateRequest):
    print(f"Received Orchestration Request for domain: {request.domain}")
    # 1. Parse intent using local Ollama (llama3)
    system_prompt = """You are the Autonome Orchestrator Brain.
You receive a raw user intent and must extract the parameters needed for specialized sub-agents.
Return ONLY a strictly valid JSON object (no markdown, no extra text) with the following schema:
{
  "task_type": "string (e.g. bdex_liquidity_analysis, general_query, etc.)",
  "parameters": {
    "key": "value"
  },
  "estimated_credits": number (between 0.5 and 50 depending on complexity)
}
"""
    
    payload = {
        "model": "llama3",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Domain: {request.domain}\nPrompt: {request.prompt}"}
        ],
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=60)
        response.raise_for_status()
        result_json = response.json()
        parsed_intent = json.loads(result_json["message"]["content"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama Parsing Failed: {str(e)}")

    task_id = "0x" + secrets.token_hex(32)
    
    # 2. Sub-Agent Routing
    if request.domain == "web3" or request.domain == "Web3 & DeFi":
        # Route to BDEX Screener
        print(f"Routing task {task_id} to BDEX Screener Sub-Agent...")
        sub_agent_result = bdex_run_agent(task_id, parsed_intent.get("parameters", {}), request.prompt)
    else:
        # Fallback or generic routing
        sub_agent_result = {"error": f"No active sub-agent for domain: {request.domain}"}

    # 4. Return full lifecycle result
    return {
        "status": "success",
        "task_id": task_id,
        "parsed_intent": parsed_intent,
        "sub_agent_result": sub_agent_result
    }
