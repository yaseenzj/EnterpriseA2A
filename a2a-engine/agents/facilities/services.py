import uuid
from .schemas import JsonRpcRequest, JsonRpcResponse, JsonRpcError

def handle_room_booking(request: JsonRpcRequest) -> JsonRpcResponse:
    time_val = request.params.get("time", "unknown")
    booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
    
    result = {
        "status": "SUCCESS",
        "booking_id": booking_id,
        "room": "Conference Room A",
        "calendar_invite_url": f"https://calendar.internal/{booking_id}"
    }
    
    return JsonRpcResponse(id=request.id, result=result)
