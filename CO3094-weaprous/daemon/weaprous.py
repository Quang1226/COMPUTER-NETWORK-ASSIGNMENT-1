# sampleApp.py
import sys
import os
from daemon.weaprous import WeApRous
import requests     # Gửi HTTP request (đăng ký tracker, gửi P2P).
import threading    # Chạy thread nền (heartbeat, discovery).
import time         # Delay (sleep).
import uuid         # Tạo UUID cho peer.
import json         # Parse/encode dữ liệu JSON từ body request.

# ============================================================
# P2P PEER CLASS
# ============================================================

class P2PChatPeer:
    def __init__(self, tracker_url='http://localhost:9000'):
        self.tracker_url = tracker_url
        self.peer_id = None
        self.username = None
        self.host = None
        self.port = None

        self.peer_list = []
        self.channels = {}            # {channel_name: [messages]}
        self.joined_channels = ['general']
        self.running = False

    def initialize(self, username, host, port):
        """Initialize peer with user info and start background tasks"""
        self.peer_id = str(uuid.uuid4())[:8]
        self.username = username
        self.host = host
        self.port = int(port)
        self.running = True

        # Start background tasks (daemon threads)
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        threading.Thread(target=self.peer_discovery_loop, daemon=True).start()

        return self.register_to_tracker()

    def register_to_tracker(self):
        """Register to centralized tracker (POST /submit-info)"""
        try:
            response = requests.post(
                f"{self.tracker_url}/submit-info",
                json={
                    'peer_id': self.peer_id,
                    'username': self.username,
                    'host': self.host,
                    'port': self.port,
                    'channels': self.joined_channels
                },
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ Registered to tracker: {self.username} ({self.peer_id})")
                self.fetch_peer_list()
                return True
            else:
                print(f"❌ Tracker returned {response.status_code}: {response.text}")
            return False
        except Exception as e:
            print(f"❌ Registration failed: {e}")
            return False

    def fetch_peer_list(self):
        """Fetch peer list from tracker (GET /get-list)"""
        try:
            response = requests.get(f"{self.tracker_url}/get-list", timeout=5)
            if response.status_code == 200:
                data = response.json()
                peers = data.get('peers', [])
                # Exclude self
                self.peer_list = [p for p in peers if p.get('peer_id') != self.peer_id]
                return self.peer_list
        except Exception:
            pass
        return []

    def send_to_peer_p2p(self, peer_info, channel, message):
        """Send message P2P directly to peer via their /receive-message endpoint"""
        try:
            url = f"http://{peer_info['host']}:{peer_info['port']}/receive-message"
            response = requests.post(
                url,
                json={
                    'channel': channel,
                    'message': message,
                    'sender': self.peer_id,
                    'sender_username': self.username,
                    'timestamp': time.time()
                },
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    def broadcast_message(self, channel, message):
        """Broadcast message P2P to all peers (store locally then send)"""
        if channel not in self.channels:
            self.channels[channel] = []

        msg_data = {
            'sender': self.peer_id,
            'sender_username': self.username,
            'message': message,
            'timestamp': time.time(),
            'channel': channel
        }
        # save locally
        self.channels[channel].append(msg_data)

        # refresh peer list and broadcast
        self.fetch_peer_list()
        success_count = 0
        for peer in self.peer_list:
            # if peer has channels info, check membership, otherwise assume default 'general'
            peer_channels = peer.get('channels') or ['general']
            if channel in peer_channels:
                if self.send_to_peer_p2p(peer, channel, message):
                    success_count += 1

        print(f"📤 Broadcast: {success_count}/{len(self.peer_list)} peers")
        return success_count

    def receive_message(self, data):
        """Handle incoming P2P message: save and print"""
        channel = data.get('channel', 'general')
        if channel not in self.channels:
            self.channels[channel] = []

        msg_data = {
            'sender': data.get('sender'),
            'sender_username': data.get('sender_username', 'unknown'),
            'message': data.get('message'),
            'timestamp': data.get('timestamp', time.time()),
            'channel': channel
        }
        self.channels[channel].append(msg_data)
        # Print a friendly message
        print(f"📩 [{channel}] {msg_data['sender_username']}: {msg_data['message']}")

    def heartbeat_loop(self):
        """Send heartbeat to tracker periodically (POST /heartbeat)"""
        while self.running:
            try:
                if self.peer_id:
                    requests.post(
                        f"{self.tracker_url}/heartbeat",
                        json={'peer_id': self.peer_id},
                        timeout=5
                    )
            except Exception:
                pass
            time.sleep(30)

    def peer_discovery_loop(self):
        """Periodically refresh peer list"""
        while self.running:
            self.fetch_peer_list()
            time.sleep(10)


# ============================================================
# WEAPROUS APPLICATION
# ============================================================

app = WeApRous()
peer = P2PChatPeer()


# ----------------------------
# Utility to safely parse headers param
# ----------------------------
def extract_path_from_headers(headers):
    """
    headers may be a dict-like or a raw string containing the request line.
    Attempt to extract the request path (e.g., '/get-messages/foo').
    """
    # If it's a dict-like
    try:
        if hasattr(headers, 'get'):
            path = headers.get('path') or headers.get('Path') or headers.get('REQUEST_URI') or ''
            if path:
                return path
    except Exception:
        pass

    # If it's a string, look for first request line
    if isinstance(headers, str):
        lines = headers.splitlines()
        if lines:
            first = lines[0]
            parts = first.split()
            if len(parts) >= 2:
                return parts[1]
    return ''


# ============================================================
# STATIC / PAGES
# ============================================================

@app.route('/', methods=['GET'])
def index(headers="", body=""):
    """Serve login page (string content)"""
    try:
        with open('www/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '<h1>Error: www/index.html not found</h1>'

@app.route('/chat', methods=['GET'])
def chat_page(headers="", body=""):
    """Serve chat page"""
    try:
        with open('www/chat.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '<h1>Error: www/chat.html not found</h1>'

# Static assets (basic)
@app.route('/static/css/login.css', methods=['GET'])
def serve_login_css(headers="", body=""):
    try:
        with open('static/css/login.css', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '/* CSS not found */'

@app.route('/static/css/chat.css', methods=['GET'])
def serve_chat_css(headers="", body=""):
    try:
        with open('static/css/chat.css', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '/* CSS not found */'

@app.route('/static/js/login.js', methods=['GET'])
def serve_login_js(headers="", body=""):
    try:
        with open('static/js/login.js', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '// JS not found'

@app.route('/static/js/chat.js', methods=['GET'])
def serve_chat_js(headers="", body=""):
    try:
        with open('static/js/chat.js', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '// JS not found'


# ============================================================
# API ROUTES - Client-Server Phase
# ============================================================

@app.route('/login', methods=['PUT'])
def login_handler(headers="", body=""):
    """
    API: User login and peer initialization
    Method: PUT
    Body: JSON { "username": "...", "port": 8001, "tracker": "http://..." }
    """
    try:
        data = json.loads(body) if body else {}
        username = data.get('username')
        port = data.get('port', 8001)
        tracker = data.get('tracker', peer.tracker_url)

        if not username:
            return json.dumps({'status': 'error', 'message': 'Username required'})

        # update tracker's URL if provided
        peer.tracker_url = tracker

        success = peer.initialize(username=username, host='0.0.0.0', port=port)
        if success:
            return json.dumps({
                'status': 'success',
                'message': 'Login successful',
                'peer_id': peer.peer_id,
                'username': peer.username,
                'port': peer.port,
                'online_peers': len(peer.peer_list)
            })
        else:
            return json.dumps({'status': 'error', 'message': 'Registration failed'})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


@app.route('/get-list', methods=['GET'])
def get_peer_list(headers="", body=""):
    """Return the list of active peers from tracker (proxy to tracker)"""
    try:
        # Refresh local view then return
        peers = peer.fetch_peer_list()
        return json.dumps({'status': 'success', 'peers': peers, 'count': len(peers)})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


# ============================================================
# API ROUTES - P2P Phase
# ============================================================

@app.route('/receive-message', methods=['POST'])
def receive_message_handler(headers="", body=""):
    """P2P API: Receive message from another peer"""
    try:
        data = json.loads(body) if body else {}
        peer.receive_message(data)
        # acknowledge
        return json.dumps({'status': 'success', 'peer_id': peer.peer_id})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


@app.route('/broadcast-message', methods=['POST'])
def broadcast_message_handler(headers="", body=""):
    """Broadcast message to all peers"""
    try:
        data = json.loads(body) if body else {}
        channel = data.get('channel', 'general')
        message = data.get('message')

        if not message:
            return json.dumps({'status': 'error', 'message': 'Message required'})

        count = peer.broadcast_message(channel, message)
        return json.dumps({
            'status': 'success',
            'sent_to': count,
            'total_peers': len(peer.peer_list)
        })
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


@app.route('/get-messages', methods=['GET'])
def get_messages_handler(headers="", body=""):
    """
    Get messages from channel.
    Supports:
      - /get-messages?channel=NAME (if WeApRous preserves path with query)
      - headers or request-line containing '/get-messages/NAME' (legacy)
      - default to 'general'
    """
    try:
        channel = 'general'
        # Try to extract from headers/request-line
        path = extract_path_from_headers(headers)
        if path:
            # check query string
            if '?' in path and 'channel=' in path:
                # /get-messages?channel=foo
                parts = path.split('?', 1)[1]
                for kv in parts.split('&'):
                    if kv.startswith('channel='):
                        channel = kv.split('=', 1)[1]
                        break
            elif '/get-messages/' in path:
                # /get-messages/foo
                channel = path.split('/get-messages/')[-1] or 'general'

        # fallback to check body (if client passes JSON with channel)
        if not channel or channel == '':
            try:
                data = json.loads(body) if body else {}
                channel = data.get('channel', 'general')
            except Exception:
                channel = 'general'

        messages = peer.channels.get(channel, [])
        return json.dumps({'status': 'success', 'channel': channel, 'messages': messages, 'count': len(messages)})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


# Convenience specific routes
@app.route('/get-messages/general', methods=['GET'])
def get_messages_general(headers="", body=""):
    messages = peer.channels.get('general', [])
    return json.dumps({'status': 'success', 'channel': 'general', 'messages': messages, 'count': len(messages)})

@app.route('/get-messages/random', methods=['GET'])
def get_messages_random(headers="", body=""):
    messages = peer.channels.get('random', [])
    return json.dumps({'status': 'success', 'channel': 'random', 'messages': messages, 'count': len(messages)})


@app.route('/get-channels', methods=['GET'])
def get_channels_handler(headers="", body=""):
    """Return available channels and joined channels"""
    try:
        return json.dumps({'status': 'success', 'channels': list(peer.channels.keys()), 'joined_channels': peer.joined_channels})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


@app.route('/status', methods=['GET'])
def status_handler(headers="", body=""):
    """Return peer status"""
    try:
        return json.dumps({
            'peer_id': peer.peer_id,
            'username': peer.username,
            'status': 'online' if peer.running else 'offline',
            'port': peer.port,
            'channels': list(peer.channels.keys()),
            'connected_peers': len(peer.peer_list)
        })
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    # Get port from command line or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    host = '0.0.0.0'

    print("\n" + "="*70)
    print("🚀 HYBRID P2P CHAT APPLICATION (WeApRous)")
    print("="*70)
    print(f"📍 Server: http://{host}:{port}")
    print("📍 Tracker: http://localhost:9000 (must be running)")
    print("\n📋 APIs:")
    print("  [GET]   /                     - Login page")
    print("  [GET]   /chat                 - Chat page")
    print("  [PUT]   /login                - User login (JSON body)")
    print("  [GET]   /get-list             - Get peer list (from tracker)")
    print("  [POST]  /receive-message      - Receive P2P message")
    print("  [POST]  /broadcast-message    - Broadcast message")
    print("  [GET]   /get-messages         - Get channel messages (query or path)")
    print("  [GET]   /get-messages/general - Get general channel messages")
    print("  [GET]   /status               - Peer status")
    print("="*70 + "\n")

    # Configure WeApRous address (port as int)
    app.prepare_address(host, port)

    # Start WeApRous server
    app.run()
