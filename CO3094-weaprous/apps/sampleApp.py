import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from daemon.weaprous import WeApRous
import json

app = WeApRous()

# ===== LOGIN =====
@app.route('/login', methods=['POST'])
def login(headers, body):
    try:
        data = json.loads(body)
        username = data.get('username')
        password = data.get('password')
        if username == 'admin' and password == 'password':
            return {"status": "success", "message": "Login successful"}
        else:
            return {"status": "fail", "message": "Invalid credentials"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== HELLO =====
@app.route('/hello', methods=['GET'])
def hello(headers, body):
    return {"message": "Hello from WeApRous!"}

# ===== CONNECT-PEER =====
peers = []

@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers, body):
    try:
        data = json.loads(body)
        peer_ip = data.get('ip')
        peer_port = data.get('port')
        if peer_ip and peer_port:
            peers.append({'ip': peer_ip, 'port': peer_port})
            return {"status": "connected", "peers": peers}
        else:
            return {"status": "fail", "message": "Invalid peer info"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== GET-LIST =====
@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    return {"peers": peers}

# ===== BROADCAST-PEER =====
@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers, body):
    try:
        data = json.loads(body)
        msg = data.get('message', '')
        return {"broadcast": msg, "sent_to": len(peers)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    app.prepare_address('0.0.0.0', 8000)
    app.run()
