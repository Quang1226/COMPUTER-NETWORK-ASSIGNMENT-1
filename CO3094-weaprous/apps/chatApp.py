import sys
import os

from daemon.weaprous import WeApRous
from daemon.response import Response
import requests
import threading
import time
import uuid
import json

# ============================================================
# P2P PEER CLASS
# ============================================================

class P2PChatPeer:
    #Khởi tạo peer với URL tracker. Các thuộc tính lưu thông tin peer, danh sách peer khác, tin nhắn theo channel.
    def __init__(self, tracker_url='http://localhost:9000'):
        self.tracker_url = tracker_url
        self.peer_id = None
        self.username = None
        self.host = None
        self.port = None
        
        self.peer_list = []
        self.channels = {}
        self.joined_channels = ['general']
        self.running = False
        
    def initialize(self, username, host, port):
        # Khởi động peer: Tạo ID, lưu info, set running=True. 
        # Chạy 2 thread daemon (chạy ngầm, tự tắt khi chương trình kết thúc): 
        # heartbeat (gửi tín hiệu sống) và discovery (cập nhật danh sách peer). 
        # Cuối cùng đăng ký với tracker.
        """Initialize peer with user info"""
        self.peer_id = str(uuid.uuid4())[:8]
        self.username = username
        self.host = host
        self.port = port
        self.running = True
        
        # Start background tasks
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        threading.Thread(target=self.peer_discovery_loop, daemon=True).start()
        
        return self.register_to_tracker()
    
    def register_to_tracker(self):
        # Gửi POST request đến tracker để đăng ký peer.
        """Register to centralized tracker"""
        try:
            response = requests.post(
                f"{self.tracker_url}/submit-info",
                json={
                    'peer_id': self.peer_id,
                    'username': self.username,
                    'host': self.host,
                    'port': self.port
                },
                timeout=5
            )
            #Nếu thành công (status 200), in thông báo và lấy danh sách peer.
            if response.status_code == 200:
                print(f"✅ Registered to tracker: {self.username}")
                self.fetch_peer_list()
                return True
            return False
        except Exception as e:
            print(f"Registration failed: {e}")
            return False
    
    def fetch_peer_list(self):
        # Lấy danh sách peer từ tracker qua GET request. Lọc bỏ peer của chính mình.
        """Fetch peer list from tracker"""
        try:
            response = requests.get(f"{self.tracker_url}/get-list", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.peer_list = [
                    p for p in data.get('peers', [])
                    if p['peer_id'] != self.peer_id
                ]
                return self.peer_list
        except:
            pass
        return []
    
    def send_to_peer_p2p(self, peer_info, channel, message):
        # Gửi tin nhắn P2P trực tiếp đến một peer khác qua POST request đến endpoint /receive-message của peer đó.
        """Send message P2P directly to peer"""
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
        except:
            return False
    
    def broadcast_message(self, channel, message):
        #Phát tán tin nhắn đến tất cả peer:
        # Lưu tin nhắn local trước, rồi lặp qua danh sách peer và gửi P2P nếu peer join channel đó.
        # Đếm số thành công.
        """Broadcast message P2P to all peers"""
        # Save locally
        if channel not in self.channels:
            self.channels[channel] = []
        
        msg_data = {
            'sender': self.peer_id,
            'sender_username': self.username,
            'message': message,
            'timestamp': time.time(),
            'channel': channel
        }
        self.channels[channel].append(msg_data)
        
        # Broadcast P2P
        self.fetch_peer_list()
        success_count = 0
        for peer in self.peer_list:
            if channel in peer.get('channels', ['general']):
                if self.send_to_peer_p2p(peer, channel, message):
                    success_count += 1
        
        print(f"📤 Broadcast: {success_count}/{len(self.peer_list)} peers")
        return success_count
    
    def receive_message(self, data):
        #Xử lý tin nhắn nhận từ peer khác: Lưu vào channels, in ra console.
        """Receive message from another peer"""
        channel = data.get('channel', 'general')
        
        if channel not in self.channels:
            self.channels[channel] = []
        
        msg_data = {
            'sender': data.get('sender'),
            'sender_username': data.get('sender_username'),
            'message': data.get('message'),
            'timestamp': data.get('timestamp', time.time()),
            'channel': channel
        }
        
        self.channels[channel].append(msg_data)
        print(f"📩 [{channel}] {msg_data['sender_username']}: {msg_data['message']}")
    
    def heartbeat_loop(self):
        #Thread ngầm: Mỗi 30 giây gửi heartbeat đến tracker để xác nhận peer còn online.
        """Send heartbeat to tracker"""
        while self.running:
            try:
                if self.peer_id:
                    requests.post(
                        f"{self.tracker_url}/heartbeat",
                        json={'peer_id': self.peer_id},
                        timeout=5
                    )
            except:
                pass
            time.sleep(30)
    
    def peer_discovery_loop(self):
        #Thread ngầm: Mỗi 10 giây cập nhật danh sách peer từ tracker.
        """Refresh peer list periodically"""
        while self.running:
            self.fetch_peer_list()
            time.sleep(10)


# ============================================================
# WEAPROUS APPLICATION
# ============================================================

# Tạo instance app
app = WeApRous()

# Tạo peer toàn cục
peer = P2PChatPeer()


# ============================================================
# STATIC FILE ROUTES
# ============================================================

@app.route('/', methods=['GET'])
# Mỗi route mở file tương ứng, đọc nội dung, trả về string. Nếu file không tồn tại, trả về lỗi đơn giản.
def index(request):
    """Serve login page"""
    try:
        with open('www/index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return Response(html_content, content_type='text/html')
    except FileNotFoundError:
        return Response('<h1>Error: www/index.html not found</h1>', status=404)


@app.route('/chat', methods=['GET'])
def chat_page(request):
    """Serve chat page"""
    try:
        with open('www/chat.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return Response(html_content, content_type='text/html')
    except FileNotFoundError:
        return Response('<h1>Error: www/chat.html not found</h1>', status=404)


@app.route('/static/css/<filename>', methods=['GET'])
def serve_css(request, filename):
    """Serve CSS files"""
    try:
        with open(f'static/css/{filename}', 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, content_type='text/css')
    except FileNotFoundError:
        return Response('/* CSS not found */', status=404)


@app.route('/static/js/<filename>', methods=['GET'])
def serve_js(request, filename):
    """Serve JavaScript files"""
    try:
        with open(f'static/js/{filename}', 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, content_type='application/javascript')
    except FileNotFoundError:
        return Response('// JS not found', status=404)


# ============================================================
# API ROUTES - Client-Server Phase
# ============================================================

# @app.route('/login', methods=['PUT'])
# def login_handler(request):
#     """
#     API: User login and peer initialization
#     Method: PUT (theo yêu cầu đề bài)
#     """
#     try:
#         data = request.json
#         username = data.get('username')
#         port = data.get('port', 8001)
        
#         if not username:
#             return Response(
#                 json.dumps({'status': 'error', 'message': 'Username required'}),
#                 status=400,
#                 content_type='application/json'
#             )
        
#         # Initialize peer
#         success = peer.initialize(
#             username=username,
#             host='0.0.0.0',
#             port=port
#         )
        
#         if success:
#             return Response(
#                 json.dumps({
#                     'status': 'success',
#                     'message': 'Login successful',
#                     'peer_id': peer.peer_id,
#                     'username': username,
#                     'port': port,
#                     'online_peers': len(peer.peer_list)
#                 }),
#                 content_type='application/json'
#             )
#         else:
#             return Response(
#                 json.dumps({'status': 'error', 'message': 'Registration failed'}),
#                 status=500,
#                 content_type='application/json'
#             )
            
#     except Exception as e:
#         return Response(
#             json.dumps({'status': 'error', 'message': str(e)}),
#             status=500,
#             content_type='application/json'
#         )


# @app.route('/get-list', methods=['GET'])
# def get_peer_list(request):
#     """
#     API: Get list of active peers
#     Method: GET
#     """
#     peer.fetch_peer_list()
    
#     return Response(
#         json.dumps({
#             'status': 'success',
#             'peers': peer.peer_list,
#             'count': len(peer.peer_list)
#         }),
#         content_type='application/json'
#     )


# ============================================================
# API ROUTES - P2P Phase
# ============================================================

@app.route('/receive-message', methods=['POST'])
def receive_message_handler(request):
    """
    P2P API: Receive message from another peer
    Method: POST
    """
    try:
        data = request.json
        peer.receive_message(data)
        
        return Response(
            json.dumps({
                'status': 'success',
                'peer_id': peer.peer_id
            }),
            content_type='application/json'
        )
    except Exception as e:
        return Response(
            json.dumps({'status': 'error', 'message': str(e)}),
            status=500,
            content_type='application/json'
        )


@app.route('/broadcast-message', methods=['POST'])
def broadcast_message_handler(request):
    """
    API: Broadcast message to all peers
    Method: POST
    """
    try:
        data = request.json
        channel = data.get('channel', 'general')
        message = data.get('message')
        
        if not message:
            return Response(
                json.dumps({'status': 'error', 'message': 'Message required'}),
                status=400,
                content_type='application/json'
            )
        
        count = peer.broadcast_message(channel, message)
        
        return Response(
            json.dumps({
                'status': 'success',
                'sent_to': count,
                'total_peers': len(peer.peer_list)
            }),
            content_type='application/json'
        )
    except Exception as e:
        return Response(
            json.dumps({'status': 'error', 'message': str(e)}),
            status=500,
            content_type='application/json'
        )


@app.route('/get-messages/<channel>', methods=['GET'])
def get_messages_handler(request, channel):
    """
    API: Get messages from channel
    Method: GET
    """
    messages = peer.channels.get(channel, [])
    
    return Response(
        json.dumps({
            'status': 'success',
            'channel': channel,
            'messages': messages,
            'count': len(messages)
        }),
        content_type='application/json'
    )


@app.route('/get-channels', methods=['GET'])
def get_channels_handler(request):
    """
    API: Get available channels
    Method: GET
    """
    return Response(
        json.dumps({
            'status': 'success',
            'channels': list(peer.channels.keys()),
            'joined_channels': peer.joined_channels
        }),
        content_type='application/json'
    )


@app.route('/status', methods=['GET'])
def status_handler(request):
    """
    API: Get peer status
    Method: GET
    """
    return Response(
        json.dumps({
            'peer_id': peer.peer_id,
            'username': peer.username,
            'status': 'online' if peer.running else 'offline',
            'port': peer.port,
            'channels': list(peer.channels.keys()),
            'connected_peers': len(peer.peer_list)
        }),
        content_type='application/json'
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("HYBRID P2P CHAT APPLICATION (WeApRous)")
    print("="*70)
    print("Server: http://0.0.0.0:8001")
    print("Tracker: http://localhost:9000 (must be running)")
    print("\nAPIs:")
    print("  [GET]   /              - Login page")
    print("  [GET]   /chat          - Chat page")
    print("  [PUT]   /login         - User login")
    print("  [GET]   /get-list      - Get peer list")
    print("  [POST]  /receive-message   - Receive P2P message")
    print("  [POST]  /broadcast-message - Broadcast message")
    print("  [GET]   /get-messages/<channel> - Get channel messages")
    print("  [GET]   /status        - Peer status")
    print("="*70 + "\n")
    
    # Start WeApRous server
    app.run(host='0.0.0.0', port=8001)