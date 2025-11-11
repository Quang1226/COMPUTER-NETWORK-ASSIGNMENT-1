# 🚀 HƯỚNG DẪN CHẠY

## Bước 1: Start Server

Mở **Command Prompt**, chạy lệnh:

```bash
cd c:\Users\Admin\Documents\MMT\COMPUTER-NETWORK-ASSIGNMENT-1\CO3094-weaprous
python start_backend.py --server-ip 127.0.0.1 --server-port 9000
```

Thấy dòng này là OK:
```
[Backend] Listening on port 9000
```

**✅ Giữ cửa sổ này mở!**

---

## Bước 2: Test Trên Browser

### 1. Mở Chrome/Firefox, truy cập: `http://127.0.0.1:9000/`

Kết quả:
```
401 Unauthorized
Authentication required. Please login.
```
✅ **Đúng rồi!** (Task 1B - chặn khi chưa login)

---

### 2. Click link "login" hoặc vào: `http://127.0.0.1:9000/login.html`

Thấy form đăng nhập:
```
Login
Username: [____]
Password: [____]
[Login]
```

---

### 3. Đăng nhập

Nhập:
- **Username:** `admin`
- **Password:** `password`

Click **Login**

---

### 4. Sau khi login thành công

Thấy trang chủ:
```
bksysnet@hcmut Domain
This domain is for use in illustrative examples in documents.
```

✅ **Task 1A hoạt động!** Cookie đã được set.

---

### 5. Kiểm tra Cookie (Optional)

Nhấn **F12** để mở DevTools:
- Tab **Application** → **Cookies** → `http://127.0.0.1:9000`
- Thấy: `auth = true`

---

### 6. Test Cookie Hoạt Động

**Refresh trang (F5):**
- Vẫn thấy trang chủ
- ✅ Authenticated!

**Xóa cookie:**
- Trong DevTools → Cookies → Chuột phải `auth` → Delete
- Refresh trang
- Quay lại "401 Unauthorized"

✅ **Task 1B hoạt động!**

---

## 🎯 TÓM TẮT DEMO

| Action | Kết quả | Task |
|--------|---------|------|
| Truy cập / không login | 401 Unauthorized | Task 1B ✅ |
| Login admin/password | Cookie + trang chủ | Task 1A ✅ |
| Refresh trang | Vẫn thấy trang chủ | Task 1B ✅ |
| Xóa cookie, refresh | 401 Unauthorized | Task 1B ✅ |

---

## 🔑 THÔNG TIN ĐĂNG NHẬP

- **Username:** `admin`
- **Password:** `password`
- **URL:** `http://127.0.0.1:9000/`

---

## 🛑 DỪNG SERVER

Trong cửa sổ Command Prompt: **Ctrl + C**

---

## ⚠️ LỖI THƯỜNG GẶP

### Port 9000 đã được dùng
```bash
netstat -ano | findstr :9000
taskkill /PID <số_PID> /F
```

### Python chưa cài
```bash
python --version
```
Nếu lỗi → cài từ python.org

---

## ✅ CHECKLIST

- [ ] Server chạy (thấy "Listening on port 9000")
- [ ] Truy cập / thấy 401
- [ ] Login admin/password thành công
- [ ] Cookie auth=true được set
- [ ] Refresh vẫn authenticated
- [ ] Xóa cookie → quay lại 401

**Tất cả ✅ → Hoàn thành!** 🎉
