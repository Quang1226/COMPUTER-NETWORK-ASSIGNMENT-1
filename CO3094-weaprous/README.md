# HTTP Server với Cookie Authentication

## 📖 Tổng quan
Bài tập Computer Network - Assignment 1
- **Task 1A:** Authentication Handling (POST /login)
- **Task 1B:** Cookie-based Access Control (GET /)

## 🚀 Cách chạy
```bash
cd c:\Users\Admin\Documents\MMT\COMPUTER-NETWORK-ASSIGNMENT-1\CO3094-weaprous
python start_backend.py --server-ip 127.0.0.1 --server-port 9000
```

Mở browser: `http://127.0.0.1:9000/`
Login: **admin** / **password**

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
