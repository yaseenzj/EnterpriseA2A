import uuid
import logging
import os
import psycopg
import json
from langchain_groq import ChatGroq
from .schemas import JsonRpcRequest, JsonRpcResponse, JsonRpcError
from .config import CATALOG

logger = logging.getLogger("finance-agent")
DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

def handle_expense_procurement(request: JsonRpcRequest) -> JsonRpcResponse:
    params = request.params
    item = params.get("item")
    quantity = params.get("quantity")
    justification = params.get("justification", "")
    approved_by = params.get("approved_by")
    
    if not item or not isinstance(quantity, int) or quantity <= 0 or not justification:
        return JsonRpcResponse(
            error=JsonRpcError(code=-32602, message="Invalid method parameters: 'item', 'quantity', and 'justification' are required"),
            id=request.id
        )
    
    # Resolve Price
    price_per_unit = CATALOG.get(item)
    if not price_per_unit:
        return JsonRpcResponse(
            error=JsonRpcError(code=-32002, message=f"Item '{item}' is not registered in the catalog"),
            id=request.id
        )
    
    total_cost = price_per_unit * quantity
    
    # Policy Evaluation (Knowledge Base)
    policy_text = ""
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                # Basic search for matching rules
                search_term = item.replace("_", " ")
                cur.execute("SELECT content FROM enterprise_knowledge_base WHERE content ILIKE %s LIMIT 1", (f"%{search_term}%",))
                row = cur.fetchone()
                if row:
                    policy_text = row[0]
    except Exception as e:
        logger.error(f"Failed to fetch policy from KB: {e}")

    llm_rejection_reason = None
    if policy_text and not approved_by:
        try:
            llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
            prompt = f"""You are a strict corporate compliance officer. 
Evaluate if the employee's justification for an expense matches the corporate policy.

Policy: {policy_text}
Item Requested: {item} (Quantity: {quantity})
Employee's Justification: {justification}

Does this request strictly comply with the policy?
Return a JSON object with two keys:
"compliant": boolean
"reason": string (brief explanation)
"""
            resp = llm.invoke(prompt)
            # parse json
            content = resp.content
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                parsed = json.loads(content[start_idx:end_idx+1])
                if not parsed.get("compliant"):
                    llm_rejection_reason = parsed.get("reason", "Violates corporate policy.")
        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")

    if llm_rejection_reason:
        logger.error(f"Compliance Violation (Policy): {llm_rejection_reason}")
        return JsonRpcResponse(
            error=JsonRpcError(
                code=-32001, 
                message=f"Policy Violation: {llm_rejection_reason} Requires 'approved_by' manager approval token.",
                data={"total_cost": total_cost, "requires_approval": True, "policy_reason": llm_rejection_reason}
            ),
            id=request.id
        )

    # Financial Compliance Check (5000 INR Limit)
    if total_cost > 5000.0 and not approved_by:
        logger.error(f"Compliance Violation: Expense of {total_cost} INR requires manager approval.")
        return JsonRpcResponse(
            error=JsonRpcError(
                code=-32001, 
                message=f"Financial Compliance Limit Exceeded. Total cost is {total_cost} INR. Requires 'approved_by' manager approval token.",
                data={"total_cost": total_cost, "requires_approval": True}
            ),
            id=request.id
        )
    
    # Transaction processed successfully
    txn_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    invoice_id = f"INV-2026-{uuid.uuid4().hex[:6].upper()}"
    
    if approved_by:
        logger.info(f"Compliance check passed: Expense of {total_cost} INR approved by '{approved_by}'")
    logger.info(f"Processed transaction {txn_id} for {total_cost} INR")
    
    return JsonRpcResponse(
        result={
            "status": "SETTLED",
            "transaction_id": txn_id,
            "invoice_id": invoice_id,
            "total_cost": total_cost,
            "currency": "INR",
            "message": f"Successfully booked {quantity} x {item} (Reason: {justification})."
        },
        id=request.id
    )
