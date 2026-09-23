import asyncio
import os
import time
import json
from arq import cron
import redis.asyncio as redis
from web3 import Web3
from eth_account import Account

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

async def get_redis_pool() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)

async def watchdog_task(ctx):
    """
    Cleans up dead workers (no heartbeat in last 10s)
    and requeues any orphaned tasks they were processing.
    """
    redis_client: redis.Redis = ctx['redis']
    now = time.time()
    
    # Get all workers from a Redis Hash containing last_heartbeat
    workers = await redis_client.hgetall("active_workers")
    dead_nodes = set()
    for node, last_hb in workers.items():
        if now - float(last_hb) > 30:
            print(f"[Scheduler] Worker {node} disconnected. Removing.")
            await redis_client.hdel("active_workers", node)
            # Remove any specific hardware telemetry stored for this worker if needed
            await redis_client.delete(f"worker_hw:{node}")
            dead_nodes.add(node)
            
    # Scan tasks:processing to requeue orphaned leases
    processing = await redis_client.hgetall("tasks:processing")
    for t_id, entry_json in processing.items():
        try:
            entry = json.loads(entry_json)
            # Support both new wrapper format and legacy raw format
            if "leased_at" in entry and "payload" in entry:
                node_id = entry.get("node_id")
                leased_at = entry.get("leased_at", 0)
                payload = entry.get("payload")
                
                # Orphan condition: Node is dead OR lease is older than 300s
                if node_id in dead_nodes or (now - float(leased_at) > 300):
                    print(f"[Scheduler] Requeuing orphaned task {t_id} from node {node_id}")
                    await redis_client.hdel("tasks:processing", t_id)
                    # Requeue at the front of the line
                    await redis_client.lpush("tasks:pending", json.dumps(payload))
            else:
                # It's an old task without a lease wrapper, just ignore or eventually clean it up
                pass
        except Exception as e:
            print(f"[Scheduler] Error processing lease for {t_id}: {e}")

async def session_monitor_task(ctx):
    """
    Scans active_session_ticks ZSET.
    Pops due ticks, enqueues to tasks:pending, re-schedules if not expired.
    """
    redis_client: redis.Redis = ctx['redis']
    now = time.time()
    
    # Get all due sessions (score <= now)
    due_sessions = await redis_client.zrangebyscore("active_session_ticks", "-inf", now)
    
    for session_id in due_sessions:
        session_data = await redis_client.hgetall(f"session:{session_id}")
        if not session_data or session_data.get("status") != "RUNNING":
            # Clean up ZSET if session was cancelled or paused
            await redis_client.zrem("active_session_ticks", session_id)
            continue
            
        started_at = float(session_data["started_at"])
        duration = float(session_data["duration_seconds"])
        interval = float(session_data["interval_seconds"])
        
        # Check if session has expired
        if now >= started_at + duration:
            print(f"[Scheduler] Session {session_id} completed (duration expired).")
            await redis_client.hset(f"session:{session_id}", "status", "COMPLETED")
            await redis_client.zrem("active_session_ticks", session_id)
            continue
            
        # Check if pre-authorized credits are depleted
        pre_auth = float(session_data.get("pre_auth_credits", 0))
        tick_cost = float(session_data.get("cost_per_tick", 0))
        if pre_auth < tick_cost:
            print(f"[Scheduler] Session {session_id} paused (insufficient pre-auth credits).")
            await redis_client.hset(f"session:{session_id}", "status", "PAUSED")
            await redis_client.hset(f"session:{session_id}", "error", "Insufficient credits for next tick.")
            await redis_client.zrem("active_session_ticks", session_id)
            continue
            
        # Dispatch a tick to the global pool!
        tick_count = int(session_data.get("tick_count", 0))
        tick_task_id = f"{session_id}-tick-{tick_count}"
        
        task_payload = {
            "task_id": tick_task_id,
            "session_id": session_id,
            "domain": "Session",
            "image": session_data.get("agent_image", "alpine"),
            "env_vars": json.loads(session_data.get("agent_env", "{}")),
            "operator_vault": session_data.get("operator_vault", "0x0000000000000000000000000000000000000000"),
            "sub_agent": session_data.get("sub_agent", "0x0000000000000000000000000000000000000000"),
            "cost": tick_cost
        }
        
        # Enqueue the tick payload to the right side of the list
        await redis_client.rpush("tasks:pending", json.dumps(task_payload))
        print(f"[Scheduler] Dispatched tick {tick_count} for session {session_id}")
        
        # Reschedule next tick
        next_tick = now + interval
        await redis_client.zadd("active_session_ticks", {session_id: next_tick})

async def master_relayer_task(ctx):
    """
    Sequentially processes completed tasks from tasks:settlement queue.
    Ensures safe nonce handling by doing one by one.
    """
    redis_client: redis.Redis = ctx['redis']
    
    if await redis_client.llen("tasks:settlement") == 0:
        return
        
    RELAYER_PRIVATE_KEY = os.environ.get("RELAYER_PRIVATE_KEY")
    if not RELAYER_PRIVATE_KEY:
        print("[Relayer] No RELAYER_PRIVATE_KEY configured.")
        return
        
    try:
        from web3.middleware import ExtraDataToPOAMiddleware as poa_middleware
    except ImportError:
        try:
            from web3.middleware import geth_poa_middleware as poa_middleware
        except ImportError:
            poa_middleware = None
            
    w3 = Web3(Web3.HTTPProvider("https://rpc.bohr.life"))
    if poa_middleware:
        w3.middleware_onion.inject(poa_middleware, layer=0)
        
    relayer_account = Account.from_key(RELAYER_PRIVATE_KEY)
    
    ESCROW_ADDRESS = "0xA3F9009a755a468Ca5cf99Bc389372C5B3A8D90F"
    ATMA_TOKEN_ADDRESS = "0xd29dE89D308b3F1eAcF3c36f821842F8F6f3f840"
    
    ESCROW_ABI = [
        {"inputs": [{"internalType": "bytes32", "name": "taskId", "type": "bytes32"}, {"internalType": "address", "name": "subAgentVault", "type": "address"}, {"internalType": "address[]", "name": "computeNodes", "type": "address[]"}, {"internalType": "address[]", "name": "operatorVaults", "type": "address[]"}], "name": "settleTask", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"internalType": "bytes32", "name": "taskId", "type": "bytes32"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "depositIntent", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
    ]
    
    ERC20_ABI = [
        {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"}
    ]
    
    contract = w3.eth.contract(address=w3.to_checksum_address(ESCROW_ADDRESS), abi=ESCROW_ABI)
    atma_contract = w3.eth.contract(address=w3.to_checksum_address(ATMA_TOKEN_ADDRESS), abi=ERC20_ABI)
    
    SIMPLE_ACCOUNT_FACTORY = "0xBC88d6012b3bf8426C2851d3798cEB5257658332"
    FACTORY_ABI = [
        {"inputs": [{"internalType": "address", "name": "owner", "type": "address"}, {"internalType": "uint256", "name": "salt", "type": "uint256"}], "name": "getAddress", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"}
    ]
    factory_contract = w3.eth.contract(address=w3.to_checksum_address(SIMPLE_ACCOUNT_FACTORY), abi=FACTORY_ABI)
    
    while True:
        task_json = await redis_client.lpop("tasks:settlement")
        if not task_json:
            break
            
        payload = json.loads(task_json)
        t_id = payload["task_id"]
        sub_agent = payload["sub_agent"]
        compute_nodes = payload.get("compute_nodes", [])
        
        # We ignore operator_vaults from the payload and compute it dynamically
            
        try:
            print(f"[Relayer] Processing settlement for {t_id}", flush=True)
            task_id_bytes = w3.to_bytes(hexstr=t_id) if t_id.startswith("0x") else w3.keccak(text=t_id)
            sub_agent_addr = w3.to_checksum_address(sub_agent) if sub_agent else w3.to_checksum_address("0x0000000000000000000000000000000000000000")
            
            node_addrs = []
            vault_addrs = []
            
            for node in compute_nodes:
                if node and node != "0x0000000000000000000000000000000000000000":
                    c_node = w3.to_checksum_address(node)
                    node_addrs.append(c_node)
                    
                    try:
                        derived_vault = factory_contract.functions.getAddress(c_node, 0).call()
                        vault_addrs.append(w3.to_checksum_address(derived_vault))
                        print(f"[Relayer] Derived Vault {derived_vault} for Node {c_node}")
                    except Exception as e:
                        print(f"[Relayer] Failed to derive vault for node {c_node} on task {t_id}: {e}. Substituting relayer address.")
                        vault_addrs.append(relayer_account.address)
            
            if not node_addrs:
                # Fallback if no valid compute nodes
                print(f"[Relayer] No valid compute nodes provided for task {t_id}. Falling back to relayer address.")
                node_addrs = [relayer_account.address]
                vault_addrs = [relayer_account.address]
                
            amount = w3.to_wei(10, 'ether')
            
            nonce = w3.eth.get_transaction_count(relayer_account.address, 'pending')
            
            # 1. Approve
            approve_tx = atma_contract.functions.approve(
                w3.to_checksum_address(ESCROW_ADDRESS), amount
            ).build_transaction({
                'from': relayer_account.address,
                'nonce': nonce,
                'chainId': 968,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price
            })
            signed_app = w3.eth.account.sign_transaction(approve_tx, private_key=RELAYER_PRIVATE_KEY)
            w3.eth.send_raw_transaction(signed_app.raw_transaction)

            # 2. Deposit
            dep_tx = contract.functions.depositIntent(
                task_id_bytes, amount
            ).build_transaction({
                'from': relayer_account.address,
                'nonce': nonce + 1,
                'chainId': 968,
                'gas': 500000,
                'gasPrice': w3.eth.gas_price
            })
            signed_dep = w3.eth.account.sign_transaction(dep_tx, private_key=RELAYER_PRIVATE_KEY)
            w3.eth.send_raw_transaction(signed_dep.raw_transaction)

            # 3. Settle
            tx_dict = contract.functions.settleTask(
                task_id_bytes, sub_agent_addr, node_addrs, vault_addrs
            ).build_transaction({
                "from": relayer_account.address,
                "nonce": nonce + 2,
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
                
            print(f"[Relayer] ✅ Settled {t_id} — tx: {tx_hash}")
            
            # Update the completed task hash with the tx_hash
            completed_json = await redis_client.hget("tasks:completed", t_id)
            if completed_json:
                completed_data = json.loads(completed_json)
                completed_data["settlement_tx_hash"] = tx_hash
                await redis_client.hset("tasks:completed", t_id, json.dumps(completed_data))
                
        except Exception as e:
            error = f"Relayer settlement failed: {str(e)}"
            print(f"[Relayer] ❌ {error} for task {t_id}")
            
            # Update error in DB
            completed_json = await redis_client.hget("tasks:completed", t_id)
            if completed_json:
                completed_data = json.loads(completed_json)
                completed_data["error"] = error
                await redis_client.hset("tasks:completed", t_id, json.dumps(completed_data))

async def startup(ctx):
    ctx['redis'] = await get_redis_pool()
    print("[Scheduler] ARQ Worker Started.")

async def shutdown(ctx):
    await ctx['redis'].close()
    print("[Scheduler] ARQ Worker Shutdown.")

import urllib.parse
from arq.connections import RedisSettings
url = urllib.parse.urlparse(REDIS_URL)

class WorkerSettings:
    functions = []
    cron_jobs = [
        cron(watchdog_task, second=set(range(0, 60, 2))),  # run every 2s
        cron(session_monitor_task, second=set(range(0, 60, 2))), # run every 2s
        cron(master_relayer_task, second=set(range(0, 60, 2))) # run every 2s
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(host=url.hostname or '127.0.0.1', port=url.port or 6379)
