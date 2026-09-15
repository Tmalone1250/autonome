import re

with open("worker.py", "r") as f:
    content = f.read()

# 1. Refactor execute_task endpoint into a plain function.
# We will remove the @app.post("/task", response_model=TaskResponse) decorator.
# And we'll change it to accept a plain dict (the task from heartbeat).
# Wait, it's easier to just append the asyncio loop at the end and slightly modify the function.

# Let's replace the decorator and signature:
content = content.replace(
    '@app.post("/task", response_model=TaskResponse)\ndef execute_task(manifest: WorkloadManifest):',
    'def execute_docker_sandbox(manifest: dict):'
)
content = content.replace('manifest.task_id', 'manifest["task_id"]')
content = content.replace('manifest.operator_vault', 'manifest.get("operator_vault", "")')
content = content.replace('manifest.image', 'manifest["image"]')
content = content.replace('manifest.env_vars', 'manifest.get("env_vars", {})')
content = content.replace('manifest.domain', 'manifest.get("domain", "")')
content = content.replace('manifest.sub_agent', 'manifest.get("sub_agent", "")')

content = content.replace(
    'return TaskResponse(',
    'return dict('
)

# 2. Add asyncio polling loop
asyncio_loop_code = """
import asyncio
import requests

async def poll_for_tasks():
    orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://127.0.0.1:8002")
    node_address = Web3().eth.account.from_key(NODE_PRIVATE_KEY).address if NODE_PRIVATE_KEY else ""
    print(f"[Worker] Started Pull Polling Loop against {orchestrator_url}...")
    
    while True:
        try:
            vault = CURRENT_VAULT or os.environ.get("OPERATOR_VAULT", "")
            resp = requests.get(f"{orchestrator_url}/nodes/heartbeat?vault={vault}&node={node_address}", timeout=5)
            if resp.status_code == 200:
                task = resp.json()
                if task.get("status") != "idle":
                    print(f"[Worker] Received pulled task: {task.get('task_id')}")
                    
                    # 1. Execute Sandbox
                    result = execute_docker_sandbox(task)
                    
                    # 2. Post Proof to Orchestrator to trigger settlement
                    complete_resp = requests.post(f"{orchestrator_url}/tasks/complete", json=result, timeout=60)
                    if complete_resp.status_code == 200:
                        complete_data = complete_resp.json()
                        tx_hash = complete_data.get("tx_hash", "")
                        
                        # 3. Save Settlement Tx to local SQLite log
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE execution_logs SET tx_hash = ?, status = ? WHERE task_id = ?",
                                        (tx_hash, "Settled", task.get("task_id")))
                            conn.commit()
                            conn.close()
                            print(f"[Worker] Settlement success. Tx Hash updated: {tx_hash}")
                        except Exception as e:
                            print(f"[Worker] Failed to update local DB: {e}")
                    else:
                        print(f"[Worker] Orchestrator settlement failed: {complete_resp.text}")
        except requests.exceptions.RequestException:
            pass # Silent fail if orchestrator offline
        except Exception as e:
            print(f"[Worker] Polling loop error: {e}")
        
        await asyncio.sleep(3)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(poll_for_tasks())

"""
# We'll insert the asyncio loop just above @app.get("/logs")
content = content.replace('@app.get("/logs")', asyncio_loop_code + '\n@app.get("/logs")')

with open("worker.py", "w") as f:
    f.write(content)
