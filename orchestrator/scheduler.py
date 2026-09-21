import asyncio
import os
import time
import json
from arq import cron
import redis.asyncio as redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

async def get_redis_pool() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)

async def watchdog_task(ctx):
    """
    Cleans up dead workers (no heartbeat in last 10s)
    """
    redis_client: redis.Redis = ctx['redis']
    now = time.time()
    
    # Get all workers from a Redis Hash containing last_heartbeat
    workers = await redis_client.hgetall("active_workers")
    for node, last_hb in workers.items():
        if now - float(last_hb) > 10:
            print(f"[Scheduler] Worker {node} disconnected. Removing.")
            await redis_client.hdel("active_workers", node)
            # Remove any specific hardware telemetry stored for this worker if needed
            await redis_client.delete(f"worker_hw:{node}")

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

async def startup(ctx):
    ctx['redis'] = await get_redis_pool()
    print("[Scheduler] ARQ Worker Started.")

async def shutdown(ctx):
    await ctx['redis'].close()
    print("[Scheduler] ARQ Worker Shutdown.")

class WorkerSettings:
    functions = []
    cron_jobs = [
        cron(watchdog_task, second=set(range(0, 60, 2))),  # run every 2s
        cron(session_monitor_task, second=set(range(0, 60, 2))) # run every 2s
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = None # Uses REDIS_URL env var implicitly via ARQ defaults if set, but we define custom redis client in ctx
    
    @classmethod
    async def get_redis_settings(cls):
        from arq.connections import RedisSettings
        # Parse REDIS_URL "redis://127.0.0.1:6379/0"
        import urllib.parse
        url = urllib.parse.urlparse(REDIS_URL)
        return RedisSettings(host=url.hostname or '127.0.0.1', port=url.port or 6379)
