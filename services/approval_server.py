"""
Approval Server — Lightweight HTTP server for handling delete approval links from emails.
Runs in a background thread alongside the Telegram bot.
"""

import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from config import config

logger = logging.getLogger(__name__)

# Shared state: pending deletes and callback for executing them
pending_deletes = {}  # {request_id: {"table": str, "match": dict, "user_id": int}}
_approval_callback = None  # Will be set by bot.py


def set_approval_callback(callback):
    """Register a callback function that bot.py provides to handle approvals."""
    global _approval_callback
    _approval_callback = callback


def get_approval_url(request_id: str, action: str) -> str:
    """Build the full approval/cancel URL for an email button."""
    base = config.APPROVAL_BASE_URL.rstrip("/")
    return f"{base}/delete/{action}/{request_id}"


class ApprovalHandler(BaseHTTPRequestHandler):
    """Handle GET requests for /delete/approve/<id> and /delete/cancel/<id>."""

    def do_GET(self):
        path = self.path.strip("/")
        parts = path.split("/")

        # Expected: delete/approve/<id> or delete/cancel/<id>
        if len(parts) == 3 and parts[0] == "delete" and parts[1] in ("approve", "cancel"):
            action = parts[1]
            request_id = parts[2]
            self._handle_delete_action(action, request_id)
        else:
            self._respond(404, "Not Found", "The requested page was not found.")

    def _handle_delete_action(self, action: str, request_id: str):
        if request_id not in pending_deletes:
            self._respond(400, "⚠️ Request Expired",
                          "This delete request has already been handled or has expired.")
            return

        pending = pending_deletes.pop(request_id)
        table_name = pending["table"]
        match = pending["match"]
        match_text = ", ".join(f"{k}={v}" for k, v in match.items())

        if action == "cancel":
            logger.info(f"Delete CANCELLED for {table_name} (where {match_text})")
            # Notify bot via callback
            if _approval_callback:
                _approval_callback("cancel", table_name, match, pending.get("user_id"), pending.get("chat_id"))
            self._respond(200, "🚫 Delete Cancelled",
                          f"The delete request for <b>{table_name}</b> (where {match_text}) has been cancelled. No rows were removed.")
        else:
            # action == "approve"
            logger.info(f"Delete APPROVED for {table_name} (where {match_text})")
            if _approval_callback:
                _approval_callback("approve", table_name, match, pending.get("user_id"), pending.get("chat_id"))
            self._respond(200, "✅ Delete Approved",
                          f"The delete request for <b>{table_name}</b> (where {match_text}) has been approved. The rows are being deleted.")

    def _respond(self, status: int, title: str, message: str):
        """Send a styled HTML response page."""
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title}</title>
<style>
  body {{ font-family: Arial, sans-serif; display: flex; justify-content: center;
         align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }}
  .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,.1);
           text-align: center; max-width: 500px; }}
  h1 {{ font-size: 24px; margin-bottom: 10px; }}
  p {{ color: #555; font-size: 16px; line-height: 1.5; }}
</style></head>
<body><div class="card"><h1>{title}</h1><p>{message}</p>
<p style="color:#999; font-size:13px; margin-top:20px;">You can close this tab now.</p>
</div></body></html>"""
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Redirect HTTP logs to our logger."""
        logger.info(f"ApprovalServer: {args[0]}")


def start_approval_server():
    """Start the approval HTTP server in a background daemon thread."""
    port = config.APPROVAL_PORT
    server = HTTPServer(("0.0.0.0", port), ApprovalHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Approval server running on port {port}")
    print(f"  🔗 Approval server: {config.APPROVAL_BASE_URL}")
    return server
