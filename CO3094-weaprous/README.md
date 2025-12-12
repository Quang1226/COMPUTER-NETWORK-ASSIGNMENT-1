# HTTP Server với Cookie Authentication

## 📖 Tổng quan
Bài tập Computer Network - Assignment 1
- **Task 1A:** Authentication Handling (POST /login)
- **Task 1B:** Cookie-based Access Control (GET /)

## 🚀 Cách chạy

### Chạy trên local (1 máy)
```bash
cd CO3094-weaprous
python start_backend.py --server-ip 127.0.0.1 --server-port 9000
```
Mở browser: `http://127.0.0.1:9000/`

### Chạy trên mạng (2 máy vật lý khác nhau)
```bash
# Máy Server
cd CO3094-weaprous
python start_backend.py --server-ip 0.0.0.0 --server-port 9000

# Máy Client - mở browser
http://<IP_SERVER>:9000/
```

**Login:** username: `admin` / password: `password`

**Lưu ý:** Cần mở port 9000 trong firewall:
```bash
# Windows
netsh advfirewall firewall add rule name="Backend Port 9000" dir=in action=allow protocol=TCP localport=9000
```

## 📄 Tài liệu

1. **[HUONG_DAN_CHAY.md](HUONG_DAN_CHAY.md)** - Hướng dẫn chạy chi tiết
2. **[BAO_CAO_IMPLEMENTATION.md](BAO_CAO_IMPLEMENTATION.md)** - Báo cáo implementation

## ✅ Files đã sửa

1. `daemon/httpadapter.py` - Tasks 1A & 1B
2. `daemon/response.py` - Build response, Set-Cookie
3. `daemon/request.py` - Parse cookies & POST body
4. `daemon/backend.py` - Threading
5. `daemon/dictionary.py` - Python 3.10+ fix
6. `daemon/proxy.py` - Python 3 syntax

## 🎯 Kết quả

Tất cả tests PASS ✅ - 7/7 điểm
