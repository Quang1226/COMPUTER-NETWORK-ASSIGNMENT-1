# peer.py – peer hybrid chat, chạy với chat_tracker_app.py thuần Python 3

import socket
import threading
import json
import time
import http.client
import os
import argparse

# ==== cấu hình mặc định của peer này (có thể override bằng tham số CLI) ====
MY_ID = "peerA"
MY_IP = "127.0.0.1"
MY_PORT = 5001

TRACKER_HOST = "127.0.0.1"
TRACKER_PORT = 8000
# ================================

# log mỗi peer vào file riêng để khỏi trộn
LOG_FILE = os.path.join(os.path.dirname(__file__), f"chat_{MY_ID}.log")


def log_message(direction: str, msg_obj: dict):
    """
    Ghi log message gửi / nhận vào file theo peer.
    direction: "SEND" hoặc "RECV"
    """
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.ctime()} [{direction}] {json.dumps(msg_obj, ensure_ascii=False)}\n")
    except OSError:
        # nếu không ghi được log thì bỏ qua, không làm chết peer
        pass


def call_api(method, path, body=None):
    """
    Gọi API tới tracker với xử lý lỗi cơ bản.
    Luôn cố gắng parse JSON kể cả khi HTTP status >= 400 để lấy message lỗi.
    """
    try:
        conn = http.client.HTTPConnection(TRACKER_HOST, TRACKER_PORT, timeout=5)
        headers = {"Content-Type": "application/json"}
        if body is None:
            conn.request(method, path)
        else:
            conn.request(method, path, body=json.dumps(body), headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        status = resp.status
    except Exception as e:
        print(f"[{MY_ID}] tracker API error {method} {path}: {e}")
        return {}
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # luôn log nếu status là lỗi, nhưng KHÔNG return sớm, vẫn cố parse JSON
    if status >= 400:
        print(f"[{MY_ID}] tracker API returned HTTP {status} for {method} {path}")

    if not data:
        return {}

    try:
        return json.loads(data)
    except json.JSONDecodeError:
        print(f"[{MY_ID}] cannot decode JSON from tracker on {method} {path}: {data!r}")
        return {}



def api_login():
    return call_api("POST", "/login", {"username": MY_ID})


def api_submit_info():
    body = {"peer_id": MY_ID, "ip": MY_IP, "port": MY_PORT}
    return call_api("POST", "/submit-info", body)


def api_get_list():
    data = call_api("GET", "/get-list")
    # loại chính mình ra
    peers = data.get("peers", [])
    return [p for p in peers if p.get("peer_id") != MY_ID]


def api_get_channels():
    data = call_api("GET", "/channels")
    return data.get("channels", [])


def api_broadcast_via_server(text: str, channel: str):
    body = {"from": MY_ID, "text": text, "channel": channel}
    return call_api("POST", "/broadcast-peer", body)


def api_send_via_server(to_peer_id: str, text: str, channel: str):
    body = {
        "from": MY_ID,
        "to_peer_id": to_peer_id,
        "text": text,
        "channel": channel,
    }
    return call_api("POST", "/send-peer", body)


# ---------- peer-to-peer ----------
def send_p2p(peer_ip: str, peer_port: int, text: str, channel: str = "general"):
    payload = {
        "type": "chat",
        "from": MY_ID,
        "text": text,
        "channel": channel,
        "timestamp": time.time(),
    }
    log_message("SEND", payload)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((peer_ip, int(peer_port)))
        s.sendall(json.dumps(payload).encode("utf-8"))
        s.close()
    except OSError:
        print(f"[{MY_ID}] cannot connect to {peer_ip}:{peer_port}")


def broadcast_p2p(text: str, channel: str = "general"):
    peers = api_get_list()
    if not peers:
        print(f"[{MY_ID}] no peers to send to")
        return
    for p in peers:
        send_p2p(p["ip"], p["port"], text, channel)


# ---------- listener ----------
def handle_client(conn: socket.socket, addr):
    try:
        data = conn.recv(4096)
        if not data:
            return
        try:
            msg = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            print(f"[{MY_ID}] received non-JSON from {addr}: {data!r}")
            return

        log_message("RECV", msg)
        ch = msg.get("channel", "general")
        sender = msg.get("from", "unknown")
        text = msg.get("text", "")
        print(f"[{ch}] {sender}: {text}")
    finally:
        try:
            conn.close()
        except OSError:
            pass


def start_listener():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((MY_IP, MY_PORT))
    s.listen(5)
    print(f"[{MY_ID}] listening on {MY_IP}:{MY_PORT} ...")

    while True:
        try:
            conn, addr = s.accept()
        except OSError:
            # socket closed
            break
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()


# ---------- CLI ----------
def input_loop():
    current_channel = "general"
    print(f"[{MY_ID}] commands:")
    print("  /list               -> in danh sách peer hiện có")
    print("  /channels           -> xem danh sách channel trên server")
    print("  /ch <name>          -> đổi channel")
    print("  /srv-bc <text>      -> nhờ server broadcast tới tất cả")
    print("  /srv-send <id> <t>  -> nhờ server gửi cho 1 peer")
    print("  text thường         -> gửi P2P trực tiếp")

    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            break

        if not text:
            continue

        # 1) xem list peer
        if text == "/list":
            peers = api_get_list()
            print("known peers:", peers)
            continue

        # 1b) xem danh sách channel
        if text == "/channels":
            chans = api_get_channels()
            if chans:
                print("channels:", ", ".join(chans))
            else:
                print("no channels from tracker")
            continue

        # 2) đổi channel
        if text.startswith("/ch "):
            current_channel = text.split(maxsplit=1)[1]
            print(f"switched to channel {current_channel}")
            continue

        # 3) broadcast qua server
        if text.startswith("/srv-bc "):
            msg = text[len("/srv-bc "):]
            res = api_broadcast_via_server(msg, current_channel)
            print("server broadcast result:", res)
            continue

        # 4) gửi qua server cho 1 peer
        if text.startswith("/srv-send "):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                print("usage: /srv-send <peer_id> <text>")
                continue
            _, to_peer, msg = parts
            res = api_send_via_server(to_peer, msg, current_channel)
            print("server send result:", res)
            continue

        # 5) mặc định: broadcast P2P trực tiếp
        broadcast_p2p(text, current_channel)


if __name__ == "__main__":
    # đọc tham số dòng lệnh để dễ chạy nhiều peer khác nhau
    parser = argparse.ArgumentParser(description="Hybrid P2P chat peer")
    parser.add_argument("--id", "--peer-id", dest="peer_id", default=MY_ID,
                        help="Peer ID (mặc định: %(default)s)")
    parser.add_argument("--ip", dest="peer_ip", default=MY_IP,
                        help="IP để peer listen (mặc định: %(default)s)")
    parser.add_argument("--port", dest="peer_port", type=int, default=MY_PORT,
                        help="Port để peer listen (mặc định: %(default)s)")
    parser.add_argument("--tracker-host", dest="tracker_host", default=TRACKER_HOST,
                        help="Địa chỉ tracker (mặc định: %(default)s)")
    parser.add_argument("--tracker-port", dest="tracker_port", type=int, default=TRACKER_PORT,
                        help="Port tracker (mặc định: %(default)s)")
    args = parser.parse_args()

    # override cấu hình global theo tham số
    MY_ID = args.peer_id
    MY_IP = args.peer_ip
    MY_PORT = args.peer_port
    TRACKER_HOST = args.tracker_host
    TRACKER_PORT = args.tracker_port
    LOG_FILE = os.path.join(os.path.dirname(__file__), f"chat_{MY_ID}.log")

    # khởi tạo với tracker
    api_login()
    api_submit_info()
    print(f"[{MY_ID}] initial peers:", api_get_list())

    # lắng nghe trên thread riêng
    threading.Thread(target=start_listener, daemon=True).start()

    # vòng nhập CLI
    input_loop()
