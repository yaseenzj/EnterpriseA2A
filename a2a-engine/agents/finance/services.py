import uuid
import logging
from .schemas import JsonRpcRequest, JsonRpcResponse, JsonRpcError
from .config import CATALOG

logger = logging.getLogger("finance-agent")

def handle_expense_procurement(request: JsonRpcRequest) -> JsonRpcResponse:
    params = request.params
    item = params.get("item")
    quantity = params.get("quantity")
    approved_by = params.get("approved_by")
    
    if not item or not isinstance(quantity, int) or quantity <= 0:
        return JsonRpcResponse(
            error=JsonRpcError(code=-32602, message="Invalid method parameters: 'item' and 'quantity' are required"),
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
            "message": f"Successfully purchased {quantity} x {item}."
        },
        id=request.id
    )
