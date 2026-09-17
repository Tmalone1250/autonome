import os
import sys
import json
import asyncio
import secrets
import signal
import socket
import requests
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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

app = FastAPI(title="Autonome Orchestrator", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# ---------------------------------------------------------------------------
# Task State
# ---------------------------------------------------------------------------
PENDING_TASKS: dict = {}   # HTTP fallback queue for non-WS workers
COMPLETED_TASKS: dict = {} # Finalized results keyed by task_id
ACTIVE_WORKERS: dict = {}  # {node_address: WebSocket} — live connections
PENDING_DEPOSITS: dict = {} # {task_id: asyncio.Task} — tracks active deposit processes

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class TaskManifest(BaseModel):
    task_id: str
    domain: str
    image: str
    env_vars: dict = {}
    operator_vault: str
    sub_agent: str

class CompleteTaskRequest(BaseModel):
    task_id: str
    inference_result: str
    proof_hash: str
    signature: str
    sub_agent: str
    operator_vault: str

class OrchestrateRequest(BaseModel):
    prompt: str
    domain: str
    user_address: str

# ---------------------------------------------------------------------------
# Settlement — runs in a thread executor to avoid blocking the event loop
# ---------------------------------------------------------------------------
def _run_settlement_sync(t_id: str, sub_agent: str, operator_vault: str) -> dict:
    """
    Blocking Web3 settlement. Must be called via run_in_executor — never directly
    from async code, as wait_for_transaction_receipt blocks the thread.
    """
    tx_hash = ""
    error = ""

    if not relayer_account:
        return {"tx_hash": "", "error": "No relayer account configured"}

    try:
        contract = w3.eth.contract(
            address=w3.to_checksum_address(ESCROW_ADDRESS), abi=ESCROW_ABI
        )

        if t_id.startswith("0x"):
            task_id_bytes = w3.to_bytes(hexstr=t_id)
        else:
            task_id_bytes = w3.keccak(text=t_id)

        sub_agent_addr = w3.to_checksum_address(sub_agent)
        vault_addr = w3.to_checksum_address(operator_vault)

        tx_dict = contract.functions.settleTask(
            task_id_bytes, sub_agent_addr, vault_addr
        ).build_transaction({
            "from": relayer_account.address,
            "nonce": w3.eth.get_transaction_count(relayer_account.address),
            "chainId": 968,
            "gas": 1500000,
            "gasPrice": w3.eth.gas_price,
        })

        signed_tx = w3.eth.account.sign_transaction(tx_dict, private_key=RELAYER_PRIVATE_KEY)
        tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = w3.to_hex(tx_hash_bytes)

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=30)
        if receipt.status != 1:
            raise RuntimeError(f"Settlement reverted: {tx_hash}")

        print(f"[Orchestrator] ✅ Settled {t_id} — tx: {tx_hash}")

    except Exception as e:
        error = f"Relayer settlement failed: {str(e)}"
        print(f"[Orchestrator] ❌ {error}")

    return {"tx_hash": tx_hash, "error": error}


async def _settle_async(t_id: str, sub_agent: str, operator_vault: str) -> dict:
    """Async wrapper — offloads blocking Web3 call to thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_settlement_sync, t_id, sub_agent, operator_vault)


# ---------------------------------------------------------------------------
# WebSocket Endpoint — primary task dispatch path
# ---------------------------------------------------------------------------
@app.websocket("/ws/worker")
async def worker_websocket(websocket: WebSocket, vault: str = "", node: str = ""):
    await websocket.accept()
    ACTIVE_WORKERS[node] = websocket
    print(f"[Orchestrator] ✅ Worker connected: {node}  vault: {vault}")

    # Drain any tasks queued before this worker came online
    if PENDING_TASKS:
        task_id = next(iter(PENDING_TASKS))
        task = PENDING_TASKS.pop(task_id)
        if vault and not task.get("operator_vault"):
            task["operator_vault"] = vault
        print(f"[Orchestrator] Draining queued task {task_id} → {node}")
        await websocket.send_json({"type": "task", **task})

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "task_complete":
                t_id = data.get("task_id", "")
                print(f"[Orchestrator] task_complete received for {t_id} from {node}")

                # Wait for the background deposit to finish mining (if it hasn't already)
                deposit_task = PENDING_DEPOSITS.pop(t_id, None)
                if deposit_task:
                    print(f"[Orchestrator] Awaiting deposit confirmation for {t_id} before settling...")
                    await deposit_task

                # Settle on-chain without blocking the event loop
                settlement = await _settle_async(
                    t_id,
                    data.get("sub_agent", ""),
                    data.get("operator_vault", "")
                )

                COMPLETED_TASKS[t_id] = {
                    "inference_result": data.get("inference_result", ""),
                    "proof_hash":       data.get("proof_hash", ""),
                    "settlement_tx_hash": settlement["tx_hash"],
                    "error":            settlement["error"],
                }

                # Notify worker so it can update its local SQLite log
                await websocket.send_json({
                    "type":    "settlement_complete",
                    "task_id": t_id,
                    "tx_hash": settlement["tx_hash"],
                    "error":   settlement["error"],
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ACTIVE_WORKERS.pop(node, None)
        print(f"[Orchestrator] Worker disconnected: {node}")
    except Exception as e:
        ACTIVE_WORKERS.pop(node, None)
        print(f"[Orchestrator] WebSocket error ({node}): {e}")


# ---------------------------------------------------------------------------
# Task Queue Endpoints
# ---------------------------------------------------------------------------
async def run_deposit_async(task_id: str):
    try:
        deposit_script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "deposit_task.py")
        )
        proc = await asyncio.create_subprocess_exec(
            "python3", deposit_script, task_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            print(f"[Orchestrator] ❌ Deposit failed for {task_id}: {stderr.decode()}")
        else:
            print(f"[Orchestrator] 💰 Deposit confirmed for {task_id}")
    except Exception as e:
        print(f"[Orchestrator] ❌ Deposit script exception for {task_id}: {e}")

@app.post("/tasks/enqueue")
async def enqueue_task(manifest: TaskManifest):
    task_dict = manifest.dict()

    # Launch deposit script asynchronously and track the task
    PENDING_DEPOSITS[manifest.task_id] = asyncio.create_task(run_deposit_async(manifest.task_id))
    print(f"[Orchestrator] 💰 True Pipelining: Deposit task started for {manifest.task_id}")

    # Push directly to a live WebSocket worker (sub-50ms dispatch)
    for node_addr, ws in list(ACTIVE_WORKERS.items()):
        try:
            await ws.send_json({"type": "task", **task_dict})
            print(f"[Orchestrator] ⚡ Pushed {manifest.task_id} via WS → {node_addr}")
            return {"status": "enqueued", "task_id": manifest.task_id}
        except Exception:
            # Stale connection — remove and try next
            ACTIVE_WORKERS.pop(node_addr, None)

    # Fallback: queue for HTTP heartbeat pickup
    PENDING_TASKS[manifest.task_id] = task_dict
    print(f"[Orchestrator] No WS workers online. Task {manifest.task_id} queued for HTTP pickup.")
    return {"status": "enqueued", "task_id": manifest.task_id}


@app.get("/nodes/heartbeat")
def node_heartbeat(vault: str = "", node: str = ""):
    """HTTP fallback heartbeat — retained for backward compatibility."""
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


@app.post("/tasks/complete")
async def complete_task(request: CompleteTaskRequest):
    """HTTP fallback completion — for workers still using HTTP heartbeat."""
    t_id = request.task_id

    # Wait for the background deposit to finish mining (if it hasn't already)
    deposit_task = PENDING_DEPOSITS.pop(t_id, None)
    if deposit_task:
        print(f"[Orchestrator] Awaiting deposit confirmation for {t_id} before settling...")
        await deposit_task

    settlement = await _settle_async(t_id, request.sub_agent, request.operator_vault)

    COMPLETED_TASKS[t_id] = {
        "inference_result":   request.inference_result,
        "proof_hash":         request.proof_hash,
        "settlement_tx_hash": settlement["tx_hash"],
        "error":              settlement["error"],
    }
    return {"status": "completed", "task_id": t_id, "tx_hash": settlement["tx_hash"]}


# ---------------------------------------------------------------------------
# Health & Orchestration
# ---------------------------------------------------------------------------
@app.get("/health")
@app.get("/")
def health_check():
    return {
        "status":          "ok",
        "service":         "Autonome Orchestrator",
        "version":         "2.0.0",
        "port":            _ORCHESTRATOR_PORT,
        "relayer_address": relayer_account.address if relayer_account else None,
        "ollama_host":     OLLAMA_HOST,
        "active_workers":  len(ACTIVE_WORKERS),
        "pending_tasks":   len(PENDING_TASKS),
    }


@app.post("/orchestrate")
def orchestrate(request: OrchestrateRequest):
    print(f"Received Orchestration Request for domain: {request.domain}")

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
            {"role": "user",   "content": f"Domain: {request.domain}\nPrompt: {request.prompt}"}
        ],
        "stream": False,
        "format": "json",
    }

    try:
        response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=60)
        response.raise_for_status()
        result_json = response.json()
        parsed_intent = json.loads(result_json["message"]["content"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama Parsing Failed: {str(e)}")

    task_id = "0x" + secrets.token_hex(32)

    if request.domain in ("web3", "Web3 & DeFi"):
        print(f"Routing task {task_id} to BDEX Screener Sub-Agent...")
        sub_agent_result = bdex_run_agent(task_id, parsed_intent.get("parameters", {}), request.prompt)
    else:
        sub_agent_result = {"error": f"No active sub-agent for domain: {request.domain}"}

    return {
        "status":           "success",
        "task_id":          task_id,
        "parsed_intent":    parsed_intent,
        "sub_agent_result": sub_agent_result,
    }
