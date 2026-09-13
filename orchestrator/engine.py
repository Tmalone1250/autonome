import os
import sys
import json
import secrets
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure we can import from autonome/agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.bdex_screener import run_agent as bdex_run_agent

app = FastAPI(title="Autonome Orchestrator", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

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

    # 3. Return full lifecycle result
    return {
        "status": "success",
        "task_id": task_id,
        "parsed_intent": parsed_intent,
        "sub_agent_result": sub_agent_result
    }
