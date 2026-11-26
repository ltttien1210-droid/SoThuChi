# Sổ Mộc — Quản lý thu chi cá nhân bằng Python

Ứng dụng web tiếng Việt cho cá nhân hoặc nhóm nhỏ dùng tài khoản độc lập trên một máy chủ. Python 3.12, Starlette, Uvicorn và SQLite. Giao diện HTML/CSS/JavaScript chạy cùng nguồn với API, không tải tài nguyên từ CDN.

## Bắt đầu nhanh trên Mac

Giải nén toàn bộ thư mục và nhấp đúp **Mo_So_Moc.command**. Hoặc mở Terminal tại thư mục có file start.py và chạy **python3 start.py**. Chương trình tạo môi trường ảo, cài thư viện từ thư mục wheels đi kèm và mở trình duyệt khi máy chủ sẵn sàng. Cần có Python 3.9 trở lên với venv, pip, SQLite và hashlib.pbkdf2_hmac.

- Nhấn **Enter** để xem sổ mẫu. Trang đăng nhập điền sẵn tài khoản. Bấm **Đăng nhập** để xem giao dịch.
- Nhập **2** để mở sổ cá nhân. Lần đầu chọn **Đăng ký** để tạo tài khoản riêng.
- Giữ Terminal mở trong khi dùng. Nhấn **Ctrl+C** để dừng máy chủ.
- Nếu cập nhật từ phiên bản cũ, dừng ứng dụng rồi sao chép nguyên thư mục **data** từ bản cũ sang thư mục vừa giải nén trước lần chạy đầu tiên để tiếp tục dùng sổ của mình.
- Trên Windows, mở PowerShell trong thư mục này và chạy **py -3.12 start.py**.

## Tài khoản và dữ liệu mẫu

Sau khi cài requirements.txt, chạy **python demo.py** trong môi trường ảo rồi mở http://127.0.0.1:8001. Tên đăng nhập **demo**, mật khẩu **SoMocDemo123!**. Bản demo dùng data/demo.sqlite3 riêng, có 8 giao dịch và ngân sách cho mỗi tháng trong tháng hiện tại và tháng trước. Chạy lại vẫn giữ các chỉnh sửa. Dùng run.py để mở sổ cá nhân ở cổng 8000.

## Chạy trên macOS hoặc Linux

Giải nén, mở Terminal trong thư mục có run.py, khuyến nghị Python 3.12. Hai gói chính hỗ trợ từ Python 3.9.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt && python run.py
```

## Chạy trên Windows

Trong PowerShell, tại thư mục vừa giải nén:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Mở http://127.0.0.1:8000 và chọn **Chưa có tài khoản? Đăng ký**. Dùng chính xác địa chỉ trên để trình duyệt gửi đúng Origin. Dữ liệu tự tạo tại data/ledger.sqlite3. Dừng máy chủ bằng Ctrl+C. Chạy lại trong cùng thư mục để mở sổ cũ.

## Sử dụng

1. Thêm khoản thu hoặc chi, chọn ngày và danh mục, nhập số nguyên đồng. Ghi chú tối đa 200 ký tự.
2. Chọn tháng để xem tổng thu, tổng chi, số dư đầu và cuối tháng. Số dư cuối tháng = đầu tháng + thu − chi. Đầu tháng lấy từ mọi giao dịch trước đó. Khi bắt đầu dùng giữa năm, có thể ghi một khoản thu “Số dư ban đầu” vào ngày trước tháng đầu tiên cần theo dõi.
3. Bấm vào dòng giao dịch để sửa hoặc xóa. Nếu hai tab cùng sửa, tab lưu sau sẽ nhận thông báo xung đột. Tải lại trang để xem phiên bản mới nhất.
4. Nhập danh mục hoặc ghi chú rồi chọn Tìm. Có thể nhập không dấu, ví dụ “an uong”. Từ khóa và các nút Khoản thu/Khoản chi lọc cả danh sách và tệp CSV. Các thẻ tổng quan và ngân sách luôn tính toàn tháng. Danh sách phân trang 20 dòng.
5. Chọn Thiết lập để đặt ngân sách theo tháng, nhập 0 để gỡ. Mục Chi theo danh mục tổng hợp từng nhóm chi.
6. Xuất CSV theo tháng và loại đang chọn. Tệp UTF-8 có BOM để mở bằng Excel. CSV là báo cáo, bản sao SQLite mới chứa đủ dữ liệu để khôi phục.

## Triển khai trên VPS

Cần Docker Engine với Compose v2, một tên miền đã trỏ đến VPS, cổng TCP 80/443 truy cập được từ Internet. Sao chép .env.example thành .env và đổi DOMAIN thành tên miền thật, chỉ nhập hostname. Từ thư mục dự án:

```bash
docker compose config
docker compose up -d --build
docker compose logs -f proxy app
```

Mở https://ten-mien-cua-ban. Caddy xử lý TLS, app chỉ nối mạng nội bộ. Volume ledger lưu dữ liệu qua các lần cập nhật. Lệnh docker compose down -v sẽ xóa volume dữ liệu. Để cập nhật mã, sao lưu trước rồi chạy lại docker compose up -d --build. Nếu subnet 172.29.90.0/24 trùng với mạng VPS, đổi subnet và địa chỉ proxy ở cả compose.yaml và Dockerfile trước khi build. Mô hình dành cho một instance và ổ đĩa cục bộ.

## Bảo vệ và vận hành

- Mật khẩu mới băm bằng PBKDF2-HMAC-SHA256 (600.000 vòng), salt ngẫu nhiên riêng. Session 12 giờ, token ngẫu nhiên lưu dạng băm trong DB. Cookie HttpOnly, SameSite=Strict và Secure khi dùng HTTPS.
- Ghi dữ liệu yêu cầu đúng Origin, header riêng và JSON. API kiểm tra kiểu, ngày, số tiền và danh mục. SQL dùng tham số, các truy vấn giao dịch gắn với tài khoản hiện tại.
- Giới hạn đăng nhập theo IP và tên tài khoản, giới hạn đăng ký theo IP trong cửa sổ 10 phút. Triển khai mặc định mở đăng ký cho người truy cập.
- SQLite và CSV chứa dữ liệu tài chính dạng đọc được với người có quyền truy cập file. Bảo vệ ổ đĩa, quyền quản trị máy và bản sao lưu. Hạn chế ai được đọc volume, không đưa dữ liệu thật vào Git.
- Quản trị viên có quyền truy cập máy có thể đặt lại mật khẩu bằng **python manage.py reset-password TEN_DANG_NHAP**. Với tài khoản cũ lưu bằng scrypt, nếu chuyển sang Python thiếu scrypt thì dùng lệnh đặt lại mật khẩu này để giữ sổ hiện có. Lệnh hỏi mật khẩu kín, đồng thời thu hồi các phiên hiện có. Trong Docker dùng **docker compose exec app python manage.py reset-password TEN_DANG_NHAP**.

## Sao lưu và phục hồi

Trên máy cá nhân, chạy **python manage.py backup ban-sao.sqlite3**. Công cụ sao lưu nhất quán qua SQLite Backup API, kiểm tra toàn vẹn và yêu cầu tên file mới.

Với Docker, sao lưu vào volume rồi chép ra khỏi VPS để dự phòng:

```bash
docker compose exec app python manage.py backup /var/lib/ledger/backup-01.sqlite3
docker compose cp app:/var/lib/ledger/backup-01.sqlite3 ./backup-01.sqlite3
```

Để thử khôi phục an toàn, sao chép bản backup vào thư mục dữ liệu **mới**, đặt biến LEDGER_DB trỏ đến bản sao rồi chạy ứng dụng. Ví dụ trên macOS/Linux:

```bash
mkdir restored
cp backup-01.sqlite3 restored/ledger.sqlite3
LEDGER_DB=restored/ledger.sqlite3 python run.py
```

Dừng instance cục bộ cũ trước khi dùng cùng cổng. Khi phục hồi VPS, dùng volume mới và cấp quyền đọc/ghi file, thư mục cho UID 10001 trước khi khởi động. Không trộn bản phục hồi với các file WAL/SHM của bản cũ.

## Cấu trúc

| Đường dẫn | Vai trò |
|---|---|
| app/main.py | Starlette, định tuyến, xác thực request và response |
| app/auth.py | Thông tin đăng nhập, session, hạn mức yêu cầu |
| app/db.py | Schema, kết nối và transaction SQLite |
| app/ledger.py | Nghiệp vụ giao dịch, báo cáo và CSV |
| app/templates/, app/static/ | Giao diện responsive tiếng Việt |
| tests/test_ledger.py | Kiểm thử tích hợp bằng SQLite tạm |
| manage.py | Sao lưu và khôi phục quyền truy cập |
| Dockerfile, compose.yaml, Caddyfile | Đóng gói và cấu hình triển khai |

## Kiểm thử

Trong môi trường ảo, chạy **python -m pip install -r requirements-dev.txt** rồi **python -m unittest -v**. Bộ test kiểm tra tính tiền giữa các tháng, phân trang, ngân sách, CSV, kiểm soát truy cập giữa tài khoản, hủy phiên, giới hạn đăng nhập, chống gửi lặp và xung đột cập nhật.
