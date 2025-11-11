# peer.py – peer hybrid chat, chạy với chat_tracker_app.py thuần Python 3

import socket
import threading
import json
import time
import http.client
import os

# ==== cấu hình của peer này ====
MY_ID = "peerB"          # terminal 1: để peerA, terminal 2: sửa thành peerB
MY_IP = "127.0.0.1"
MY_PORT = 5006           # terminal 2 nhớ đổi 5002

TRACKER_HOST = "127.0.0.1"
TRACKER_PORT = 8000
# ================================

# log mỗi peer vào file riêng để khỏi trộn
LOG_FILE = os.path.join(os.path.dirname(__file__), f"chat_{MY_ID}.log")


def log_message(direction: str, msg_obj: dict):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.ctime()} [{direction}] {json.dumps(msg_obj, ensure_ascii=False)}\n")


# ---------- gọi API tới tracker ----------
def call_api(method, path, body=None):
    conn = http.client.HTTPConnection(TRACKER_HOST, TRACKER_PORT)
    headers = {"Content-Type": "application/json"}
    if body is None:
        conn.request(method, path)
    else:
        conn.request(method, path, body=json.dumps(body), headers=headers)
    resp = conn.getresponse()
    data = resp.read().decode()
    conn.close()
    return json.loads(data) if data else {}


def api_login():
    return call_api("POST", "/login", {"username": MY_ID, "password": "123"})


def api_submit_info():
    return call_api("POST", "/submit-info", {
        "peer_id": MY_ID,
        "ip": MY_IP,
        "port": MY_PORT
    })


def api_get_list():
    data = call_api("GET", "/get-list")
    # bỏ chính mình ra
    return [p for p in data.get("peers", []) if p["peer_id"] != MY_ID]


def api_broadcast_via_server(text, channel="general"):
    return call_api("POST", "/broadcast-peer", {
        "from": MY_ID,
        "text": text,
        "channel": channel
    })


def api_send_via_server(to_peer, text, channel="general"):
    return call_api("POST", "/send-peer", {
        "to": to_peer,
        "from": MY_ID,
        "text": text,
        "channel": channel
    })
# ------------------------------------------


# ------------ phần nhận TCP ---------------
def handle_client(conn, addr):
    try:
        data = conn.recv(4096)
        if not data:
            return
        msg = json.loads(data.decode())
        ch = msg.get("channel", "general")
        sender = msg.get("from", "unknown")
        text = msg.get("text", "")
        print(f"\n[{ch}] {sender}: {text}")
        log_message("RECV", msg)
    finally:
        conn.close()


def start_listener():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((MY_IP, MY_PORT))
    s.listen()
    print(f"[{MY_ID}] listening on {MY_IP}:{MY_PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
# ------------------------------------------


# ------------ phần gửi P2P ----------------
def send_p2p(peer_ip, peer_port, text, channel="general"):
    payload = {
        "type": "chat",
        "from": MY_ID,
        "text": text,
        "channel": channel,
        "timestamp": time.time()
    }
    log_message("SEND", payload)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((peer_ip, peer_port))
        s.send(json.dumps(payload).encode())
        s.close()
    except OSError:
        print(f"[{MY_ID}] cannot connect to {peer_ip}:{peer_port}")


def broadcast_p2p(text, channel="general"):
    # mỗi lần gửi thì hỏi lại tracker để lấy peer mới join
    peers = api_get_list()
    for p in peers:
        send_p2p(p["ip"], p["port"], text, channel=channel)
# ------------------------------------------


def input_loop():
    current_channel = "general"
    print(f"[{MY_ID}] commands:")
    print("  /list               -> in danh sách peer hiện có")
    print("  /ch <name>          -> đổi channel")
    print("  /srv-bc <text>      -> nhờ server broadcast tới tất cả")
    print("  /srv-send <id> <t>  -> nhờ server gửi cho 1 peer")
    print("  text thường         -> gửi P2P trực tiếp")

    while True:
        text = input("> ").strip()
        if not text:
            continue

        # 1) xem list
        if text == "/list":
            peers = api_get_list()
            print("known peers:", peers)
            continue

        # 2) đổi channel
        if text.startswith("/ch "):
            current_channel = text.split(maxsplit=1)[1]
            print(f"switched to channel {current_channel}")
            continue

        # 3) broadcast qua server
        if text.startswith("/srv-bc "):
            content = text[len("/srv-bc "):]
            res = api_broadcast_via_server(content, channel=current_channel)
            print("server broadcast result:", res)
            # không gửi p2p nữa
            continue

        # 4) gửi riêng qua server
        if text.startswith("/srv-send "):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                print("usage: /srv-send <peer_id> <text>")
                continue
            target_id = parts[1]
            content = parts[2]
            res = api_send_via_server(target_id, content, channel=current_channel)
            print("server send result:", res)
            # không gửi p2p nữa
            continue

        # 5) còn lại: gửi p2p
        broadcast_p2p(text, channel=current_channel)


if __name__ == "__main__":
    # khởi tạo với tracker
    api_login()
    api_submit_info()
    print(f"[{MY_ID}] initial peers:", api_get_list())

    # lắng nghe
    threading.Thread(target=start_listener, daemon=True).start()

    # vòng nhập
    input_loop()
