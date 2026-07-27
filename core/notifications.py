import os
import psycopg
import logging

logger = logging.getLogger("notifications")
DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/postgres")

def send_notification(user_id: str, message: str, notif_type: str = "INFO"):
    """
    Sends a system notification to a specific user.
    Types: INFO, SUCCESS, ERROR, ALERT
    """
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, %s)",
                    (user_id, message, notif_type)
                )
            conn.commit()
        logger.info(f"Notification sent to {user_id}: [{notif_type}] {message}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def get_user_notifications(user_id: str, limit: int = 10):
    try:
        with psycopg.connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, message, type, created_at FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                    (user_id, limit)
                )
                results = cur.fetchall()
                
                return [
                    {
                        "id": str(r[0]),
                        "message": r[1],
                        "type": r[2],
                        "created_at": r[3].isoformat()
                    } for r in results
                ]
    except Exception as e:
        logger.error(f"Failed to fetch notifications: {e}")
        return []
