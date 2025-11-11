# chat_tracker_app.py
# Tracker viết bằng Python 3 thuần, không cần weaprous

from http.server import BaseHTTPRequestHandler, HTTPServer
import json

PEERS = {}      # peer_id -> {"ip":..., "port":...}
CHANNELS = {
    "general": [],
    "random": []
}

class TrackerHandler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---- GET ----
    def do_GET(self):
        if self.path == "/get-list":
            peers_list = [
                {"peer_id": k, "ip": v["ip"], "port": v["port"]}
                for k, v in PEERS.items()
            ]
            self._send_json({"peers": peers_list})
        elif self.path == "/channels":
            self._send_json({"channels": list(CHANNELS.keys())})
        else:
            self._send_json({"status": "not_found"}, 404)

    # ---- POST ----
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length > 0 else "{}"
        try:
            data = json.loads(body)
        except:
            data = {}

        # /login
        if self.path == "/login":
            user = data.get("username", "guest")
            self._send_json({"status": "ok", "user": user})
            return

        # /submit-info
        if self.path == "/submit-info":
            peer_id = data["peer_id"]
            PEERS[peer_id] = {"ip": data["ip"], "port": data["port"]}
            CHANNELS["general"].append({
                "type": "notify",
                "from": "system",
                "text": f"{peer_id} joined"
            })
            self._send_json({"status": "ok", "peers": list(PEERS.keys())})
            return

        # /add-list
        if self.path == "/add-list":
            pid = data["peer_id"]
            PEERS[pid] = {"ip": data["ip"], "port": data["port"]}
            self._send_json({"status": "ok"})
            return

        # /connect-peer
        if self.path == "/connect-peer":
            target_id = data["peer_id"]
            if target_id in PEERS:
                self._send_json({
                    "status": "ok",
                    "peer": {
                        "peer_id": target_id,
                        "ip": PEERS[target_id]["ip"],
                        "port": PEERS[target_id]["port"],
                    }
                })
            else:
                self._send_json({"status": "error", "message": "peer not found"}, 404)
            return

        # /broadcast-peer
        if self.path == "/broadcast-peer":
            channel = data.get("channel", "general")
            msg = {
                "type": "chat",
                "from": data.get("from", "unknown"),
                "text": data.get("text", ""),
                "channel": channel
            }
            CHANNELS.setdefault(channel, []).append(msg)

            # gửi tới từng peer qua TCP
            delivered = []
            import socket
            for pid, info in PEERS.items():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((info["ip"], info["port"]))
                    s.send(json.dumps(msg).encode())
                    s.close()
                    delivered.append(pid)
                except OSError:
                    pass
            self._send_json({"status": "ok", "delivered_to": delivered})
            return

        # /send-peer
        if self.path == "/send-peer":
            target = data["to"]
            if target not in PEERS:
                self._send_json({"status": "error", "message": "target not found"}, 404)
                return
            msg = {
                "type": "chat",
                "from": data.get("from", "unknown"),
                "text": data.get("text", ""),
                "channel": data.get("channel", "general")
            }
            import socket
            info = PEERS[target]
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((info["ip"], info["port"]))
                s.send(json.dumps(msg).encode())
                s.close()
                self._send_json({"status": "ok"})
            except OSError:
                self._send_json({"status": "error", "message": "peer offline"})
            return

        self._send_json({"status": "not_found"}, 404)


def run(host="0.0.0.0", port=8000):
    httpd = HTTPServer((host, port), TrackerHandler)
    print(f"[tracker] running on {host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
