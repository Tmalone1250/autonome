import os
import sys
import json
import asyncio
import secrets
import signal
import time
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import requests

# Ensure port 8002 is free before app initializes
def free_port(port: int):
    try:
        import subprocess
        result = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True)
        pids = result.stdout.strip().split()
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    except Exception:
        pass

_ORCHESTRATOR_PORT = int(os.environ.get("ORCHESTRATOR_PORT", "8002"))
free_port(_ORCHESTRATOR_PORT)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agents.bdex_screener import build_manifest as bdex_build_manifest

from dotenv import load_dotenv
load_dotenv()
RELAYER_PRIVATE_KEY = os.getenv("RELAYER_PRIVATE_KEY")
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

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

app = FastAPI(title="Autonome Orchestrator", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Global Redis Client
redis_client = None

@app.on_event("startup")
async def startup_event():
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    print(f"[Orchestrator] Connected to Redis at {REDIS_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    if redis_client:
        await redis_client.close()

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
    cost: float = 0.0

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

class HeartbeatRequest(BaseModel):
    node_id: str
    vault: str
    hardware: dict

class CreateSessionRequest(BaseModel):
    agent: str
    interval: int
    duration: int
    parameters: dict
    operator_vault: str
    user_address: str

# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------
def _run_settlement_sync(t_id: str, sub_agent: str, operator_vault: str) -> dict:
    tx_hash = ""
    error = ""
    if not relayer_account:
        return {"tx_hash": "", "error": "No relayer account configured"}

    try:
        contract = w3.eth.contract(address=w3.to_checksum_address(ESCROW_ADDRESS), abi=ESCROW_ABI)
        task_id_bytes = w3.to_bytes(hexstr=t_id) if t_id.startswith("0x") else w3.keccak(text=t_id)
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
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_settlement_sync, t_id, sub_agent, operator_vault)

# ---------------------------------------------------------------------------
# Task Queue Endpoints (Stateless)
# ---------------------------------------------------------------------------
@app.post("/tasks/enqueue")
async def enqueue_task(manifest: TaskManifest):
    await redis_client.rpush("tasks:pending", json.dumps(manifest.dict()))
    print(f"[Orchestrator] Task {manifest.task_id} enqueued globally.")
    return {"status": "enqueued", "task_id": manifest.task_id}

@app.post("/nodes/heartbeat")
async def node_heartbeat(req: HeartbeatRequest):
    now = time.time()
    await redis_client.hset("active_workers", req.node_id, now)
    await redis_client.set(f"worker_vault:{req.node_id}", req.vault)
    await redis_client.set(f"worker_hw:{req.node_id}", json.dumps(req.hardware))
    
    # Try to pop a task
    task_json = await redis_client.lpop("tasks:pending")
    if task_json:
        task_data = json.loads(task_json)
        # Inherit node vault if task vault is empty or zero
        if not task_data.get("operator_vault") or task_data["operator_vault"] == "0x0000000000000000000000000000000000000000":
            task_data["operator_vault"] = req.vault
        
        # Keep track of processing tasks
        await redis_client.hset("tasks:processing", task_data["task_id"], json.dumps(task_data))
        return {"status": "task", "task": task_data}
    
    return {"status": "idle"}

@app.get("/tasks/status/{task_id}")
async def get_task_status(task_id: str):
    completed = await redis_client.hget("tasks:completed", task_id)
    if completed:
        return {"status": "completed", "result": json.loads(completed)}
    processing = await redis_client.hget("tasks:processing", task_id)
    if processing:
        return {"status": "processing"}
    return {"status": "pending"}

@app.websocket("/ws/worker")
async def legacy_worker_ws(websocket: WebSocket, vault: str = "", node: str = ""):
    await websocket.accept()
    if not node:
        node = "legacy_node_" + secrets.token_hex(4)
    print(f"[Orchestrator] Legacy WebSocket connected: {node}")
    try:
        while True:
            # Emulate heartbeat
            now = time.time()
            await redis_client.hset("active_workers", node, now)
            if vault:
                await redis_client.set(f"worker_vault:{node}", vault)
            await redis_client.set(f"worker_hw:{node}", json.dumps({"legacy": True}))
            
            # Try to pop a task for this worker
            task_json = await redis_client.lpop("tasks:pending")
            if task_json:
                task_data = json.loads(task_json)
                if not task_data.get("operator_vault") or task_data["operator_vault"] == "0x0000000000000000000000000000000000000000":
                    task_data["operator_vault"] = vault
                
                await redis_client.hset("tasks:processing", task_data["task_id"], json.dumps(task_data))
                await websocket.send_json(task_data)
                print(f"[Orchestrator] Legacy WS sent task {task_data['task_id']} to {node}")
                
            try:
                # Wait for any incoming messages (like task completion) with a timeout
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=3.0)
                try:
                    result_data = json.loads(msg)
                    if "task_id" in result_data and "inference_result" in result_data:
                        t_id = result_data["task_id"]
                        sub_agent = result_data.get("sub_agent", "")
                        operator_vault = result_data.get("operator_vault", vault)
                        asyncio.create_task(_process_legacy_completion(result_data, t_id, sub_agent, operator_vault))
                except json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        await redis_client.hdel("active_workers", node)
        print(f"[Orchestrator] Legacy WebSocket disconnected: {node}")
    except Exception as e:
        print(f"[Orchestrator] Legacy WS error: {e}")
        try:
            await redis_client.hdel("active_workers", node)
        except:
            pass

async def _process_legacy_completion(req, t_id, sub_agent, operator_vault):
    settlement = await _settle_async(t_id, sub_agent, operator_vault)
    result_data = {
        "inference_result": req.get("inference_result", ""),
        "proof_hash": req.get("proof_hash", ""),
        "settlement_tx_hash": settlement["tx_hash"],
        "error": settlement["error"],
    }
    await redis_client.hset("tasks:completed", t_id, json.dumps(result_data))
    await redis_client.hdel("tasks:processing", t_id)
    print(f"[Orchestrator] Legacy WS completed task {t_id}")


@app.post("/tasks/complete")
async def complete_task(req: CompleteTaskRequest):
    t_id = req.task_id
    
    # Check if this is a session tick
    is_session_tick = "-tick-" in t_id
    
    settlement = await _settle_async(t_id, req.sub_agent, req.operator_vault)
    
    result_data = {
        "inference_result": req.inference_result,
        "proof_hash": req.proof_hash,
        "settlement_tx_hash": settlement["tx_hash"],
        "error": settlement["error"],
    }
    
    await redis_client.hset("tasks:completed", t_id, json.dumps(result_data))
    await redis_client.hdel("tasks:processing", t_id)
    
    if is_session_tick:
        # Handle Session state updates and credit deduction
        session_id = t_id.split("-tick-")[0]
        session_data = await redis_client.hgetall(f"session:{session_id}")
        if session_data:
            tick_cost = float(session_data.get("cost_per_tick", 0))
            pre_auth = float(session_data.get("pre_auth_credits", 0))
            new_pre_auth = max(0, pre_auth - tick_cost)
            tick_count = int(session_data.get("tick_count", 0)) + 1
            total_earned = float(session_data.get("total_settled_atma", 0)) + tick_cost
            
            await redis_client.hmset(f"session:{session_id}", {
                "pre_auth_credits": new_pre_auth,
                "tick_count": tick_count,
                "total_settled_atma": total_earned,
                "last_result": json.dumps(result_data)
            })
            print(f"[Orchestrator] Session {session_id} tick complete. Credits remaining: {new_pre_auth}")

    return {"status": "completed", "task_id": t_id, "tx_hash": settlement["tx_hash"]}

# ---------------------------------------------------------------------------
# Sessions Endpoints
# ---------------------------------------------------------------------------
@app.post("/sessions/create")
async def create_session(req: CreateSessionRequest):
    session_id = "0x" + secrets.token_hex(16)
    
    # Calculate costs
    ticks = req.duration // req.interval
    cost_per_tick = 10.0 # Standardize for now, could be dynamic
    total_cost = ticks * cost_per_tick
    
    now = time.time()
    
    session_data = {
        "user_address": req.user_address,
        "status": "RUNNING",
        "agent_image": req.agent,
        "agent_env": json.dumps(req.parameters),
        "operator_vault": req.operator_vault,
        "sub_agent": "0x0000000000000000000000000000000000000000",
        "interval_seconds": req.interval,
        "duration_seconds": req.duration,
        "started_at": now,
        "next_tick_at": now,
        "tick_count": 0,
        "total_settled_atma": 0.0,
        "pre_auth_credits": total_cost,
        "cost_per_tick": cost_per_tick,
        "last_result": ""
    }
    
    await redis_client.hmset(f"session:{session_id}", session_data)
    await redis_client.zadd("active_session_ticks", {session_id: now})
    await redis_client.sadd(f"user_sessions:{req.user_address}", session_id)
    
    print(f"[Orchestrator] Created Session {session_id} for {req.duration}s. Pre-auth: {total_cost} credits.")
    return {"status": "created", "session_id": session_id, "pre_auth_credits": total_cost}

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    data = await redis_client.hgetall(f"session:{session_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data

@app.patch("/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    data = await redis_client.hgetall(f"session:{session_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    new_status = "PAUSED" if data["status"] == "RUNNING" else "RUNNING"
    await redis_client.hset(f"session:{session_id}", "status", new_status)
    
    if new_status == "RUNNING":
        # Resume tick
        await redis_client.zadd("active_session_ticks", {session_id: time.time()})
    else:
        await redis_client.zrem("active_session_ticks", session_id)
        
    return {"status": new_status, "session_id": session_id}

@app.delete("/sessions/{session_id}")
async def cancel_session(session_id: str):
    await redis_client.hset(f"session:{session_id}", "status", "CANCELLED")
    await redis_client.zrem("active_session_ticks", session_id)
    return {"status": "cancelled", "session_id": session_id}

# ---------------------------------------------------------------------------
# Health & Orchestration
# ---------------------------------------------------------------------------
@app.get("/health")
@app.get("/")
async def health_check():
    active_workers = await redis_client.hlen("active_workers")
    pending = await redis_client.llen("tasks:pending")
    return {
        "status": "ok",
        "service": "Autonome Orchestrator",
        "version": "2.1.0 (Stateless)",
        "active_workers": active_workers,
        "pending_tasks": pending,
    }

@app.get("/admin/nodes")
async def admin_get_nodes():
    now = time.time()
    workers = await redis_client.hgetall("active_workers")
    nodes = []
    for node_id, last_beat in workers.items():
        vault = await redis_client.get(f"worker_vault:{node_id}") or ""
        hw_raw = await redis_client.get(f"worker_hw:{node_id}")
        hw = json.loads(hw_raw) if hw_raw else {}
        nodes.append({
            "node_id": node_id,
            "vault": vault,
            "status": "ONLINE", # watchdog removes them if LOST
            "last_heartbeat": float(last_beat),
            "hardware": hw
        })
    return {"nodes": nodes}

@app.get("/admin/queues")
async def admin_get_queues():
    pending = await redis_client.llen("tasks:pending")
    completed = await redis_client.hlen("tasks:completed")
    processing = await redis_client.hlen("tasks:processing")
    return {
        "pending_tasks": pending,
        "processing_tasks": processing,
        "completed_tasks": completed,
    }

@app.post("/orchestrate")
async def orchestrate(request: OrchestrateRequest):
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
        import functools
        import re
        loop = asyncio.get_event_loop()
        req_func = functools.partial(requests.post, f"{OLLAMA_HOST}/api/chat", json=payload, timeout=60)
        resp = await loop.run_in_executor(None, req_func)
        resp.raise_for_status()
        
        raw_content = resp.json()["message"]["content"]
        print(f"[Orchestrator] Raw Ollama response: {raw_content}")
        
        # Clean markdown if present
        json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        clean_json = json_match.group(0) if json_match else raw_content
        
        parsed_intent = json.loads(clean_json)
    except Exception as e:
        print(f"[Orchestrator] Ollama parsing error: {e}")
        raise HTTPException(status_code=500, detail=f"Ollama Parsing Failed: {str(e)}")

    task_id = "0x" + secrets.token_hex(32)

    if request.domain in ("web3", "Web3 & DeFi"):
        sub_agent_result = bdex_build_manifest(task_id, parsed_intent.get("parameters", {}), request.prompt)
        if "manifest" in sub_agent_result:
            manifest_dict = sub_agent_result.pop("manifest")
            await redis_client.rpush("tasks:pending", json.dumps(manifest_dict))
            print(f"[Orchestrator] Task {task_id} successfully queued to tasks:pending")
    else:
        sub_agent_result = {"error": f"No active sub-agent for domain: {request.domain}"}

    return {
        "status":           "success",
        "task_id":          task_id,
        "parsed_intent":    parsed_intent,
        "sub_agent_result": sub_agent_result,
    }
