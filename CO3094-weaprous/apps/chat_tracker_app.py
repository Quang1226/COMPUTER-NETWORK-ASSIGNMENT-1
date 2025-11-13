# chat_tracker_app.py
# Tracker HTTP server cho ứng dụng chat hybrid (client-server + peer-to-peer)

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import time
import socket

# Danh sách peer đang online: peer_id -> {"ip": str, "port": int}
PEERS = {}

# Lưu log message theo channel (đơn giản để minh họa)
CHANNELS = {
    "general": [],
    "random": [],
}


class TrackerHandler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status: int = 200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------- GET ----------
    def do_GET(self):
        if self.path == "/get-list":
            # trả về list các peer hiện có
            peers_list = [
                {"peer_id": pid, "ip": info["ip"], "port": info["port"]}
                for pid, info in PEERS.items()
            ]
            self._send_json({"peers": peers_list})
            return

        if self.path == "/channels":
            # trả về danh sách channel
            self._send_json({"channels": list(CHANNELS.keys())})
            return

        # không khớp route nào
        self._send_json({"status": "not_found"}, 404)

    # ---------- POST ----------
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        # /login : đơn giản chỉ echo username, để minh họa "authentication"
        if self.path == "/login":
            user = data.get("username", "guest")
            self._send_json({"status": "ok", "user": user})
            return

        # /submit-info : peer đăng ký thông tin (peer discovery)
        if self.path == "/submit-info":
            peer_id = data.get("peer_id")
            ip = data.get("ip")
            port = data.get("port")
            if not peer_id or not ip or port is None:
                self._send_json(
                    {"status": "error", "message": "missing peer_id/ip/port"}, 400
                )
                return

            PEERS[peer_id] = {"ip": ip, "port": int(port)}
            # ghi system message vào channel general
            CHANNELS.setdefault("general", []).append(
                {
                    "type": "notify",
                    "from": "system",
                    "text": f"{peer_id} joined",
                    "timestamp": time.time(),
                }
            )
            self._send_json({"status": "ok", "peers": list(PEERS.keys())})
            return

        # /add-list : cho phép thêm/override peer từ client khác (tuỳ bài lab)
        if self.path == "/add-list":
            pid = data.get("peer_id")
            ip = data.get("ip")
            port = data.get("port")
            if not pid or not ip or port is None:
                self._send_json(
                    {"status": "error", "message": "missing peer_id/ip/port"}, 400
                )
                return
            PEERS[pid] = {"ip": ip, "port": int(port)}
            self._send_json({"status": "ok"})
            return

        # /broadcast-peer : server nhận 1 message rồi TCP tới mọi peer
        if self.path == "/broadcast-peer":
            sender = data.get("from") or data.get("peer_id") or "unknown"
            text = data.get("text", "")
            channel = data.get("channel", "general")

            msg = {
                "type": "chat",
                "from": sender,
                "text": text,
                "channel": channel,
                "timestamp": time.time(),
            }
            CHANNELS.setdefault(channel, []).append(msg)

            delivered = []
            for pid, info in PEERS.items():
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2.0)
                        s.connect((info["ip"], int(info["port"])))
                        s.sendall(json.dumps(msg).encode("utf-8"))
                    delivered.append(pid)
                except OSError:
                    # nếu peer offline thì bỏ qua
                    continue

            self._send_json({"status": "ok", "delivered_to": delivered})
            return

        # /send-peer : server gửi message tới đúng 1 peer
        if self.path == "/send-peer":
            sender = data.get("from") or data.get("from_peer_id") or "unknown"
            to_peer = data.get("to_peer_id")
            text = data.get("text", "")
            channel = data.get("channel", "general")

            if not to_peer:
                self._send_json(
                    {"status": "error", "message": "missing to_peer_id"}, 400
                )
                return

            info = PEERS.get(to_peer)
            if not info:
                self._send_json(
                    {"status": "error", "message": "peer not found"}, 404
                )
                return

            msg = {
                "type": "chat",
                "from": sender,
                "text": text,
                "channel": channel,
                "timestamp": time.time(),
            }
            CHANNELS.setdefault(channel, []).append(msg)

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    s.connect((info["ip"], int(info["port"])))
                    s.sendall(json.dumps(msg).encode("utf-8"))
                self._send_json({"status": "ok", "delivered_to": [to_peer]})
            except OSError:
                self._send_json({"status": "error", "message": "peer offline"})
            return

        # route không được hỗ trợ
        self._send_json({"status": "not_found"}, 404)


def run(host: str = "0.0.0.0", port: int = 8000):
    httpd = HTTPServer((host, port), TrackerHandler)
    print(f"[tracker] running on {host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
