from pydantic import BaseModel, Field, ValidationError

class CompleteTaskRequest(BaseModel):
    task_id: str
    inference_result: str
    proof_hash: str
    signature: str
    sub_agent: str
    node_address: str = Field(..., min_length=42, max_length=42, pattern=r'^0x[a-fA-F0-9]{40}$')

payload = {
    "task_id": "0x3bf97d862b7eb6f65e6412563d5d9ec0c7f1f40bd5cabf399cd9e44954d894f9",
    "inference_result": "dummy result",
    "proof_hash": "dummy hash",
    "signature": "",
    "sub_agent": None,
    "node_address": "0x8c406BeBAB2895D73Ad77f91c693ab7bf86753eb",
    "operator_vault": "0x4Ca3de89a133a6660b2D059b000847419256bfCA"
}

try:
    obj = CompleteTaskRequest(**payload)
    print("Success")
except ValidationError as e:
    print("Validation Error:")
    print(e.json())
