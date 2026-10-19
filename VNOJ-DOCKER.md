# Judge image cho VNOJ

Base image hiện dùng public `vnoj/judge-tiervnoj` với digest pin trong Dockerfile.
Repository `vnoj/judge-tier1` cũ không còn truy cập được. Với production dùng
`make prod-init`, chỉnh `production/judge.env`, đăng ký name/key bên OJ rồi
`make prod`; xem `PRODUCTION.md`.

Build source local (Linux amd64, VNOJ runtimes):

```powershell
docker build -t vnoj/judge-server:local .
```

Base image được cố định bằng digest. Source local, kể cả thay đổi chưa commit,
được biên dịch vào image. Không cài dependency khi container khởi động.

Đăng ký judge trong Django Admin của VNOJ (Judges): đặt name và auth key
ngẫu nhiên, duy nhất. Dùng đúng `DMOJ_JUDGE_NAME` và `DMOJ_JUDGE_KEY`
trong `.env` để đăng ký. Không commit key.
Compose tự đọc `.env` để thay biến và nạp vào container qua `env_file`.
Máy mới: copy `.env.example` thành `.env`, thay key trước khi chạy.

```powershell
docker compose -f compose.vnoj.yml up -d
docker compose -f compose.vnoj.yml logs -f judge
```

Judge kết nối `vnoj_bridged:9999` qua network `dmoj_db`, không kết nối
trực tiếp HTTP của `vnoj_site`. Bridge và site phải đang chạy.
Đổi `VNOJ_NETWORK` nếu Compose project dùng tên network khác.
Bridge hiện tại bind trên network `dmoj_db`; `dmoj_site` từ chối kết nối.
Launcher giữ multiprocessing `fork`, cần cho cache runtime/problem trên Python 3.14.
`VNOJ_PROBLEMS_DIR` trỏ tới thư mục problem data của site; mặc định dùng
`../ITMC-OJ-docker/dmoj/problems`. Judge cần quyền đọc các file này.

Kiểm tra judge online tại trang trạng thái VNOJ, sau đó gửi submission
cho bài có test data. Image hỗ trợ các runtime khả dụng trong base VNOJ;
xem runtime khởi tạo thành công trong log. Không bỏ qua executor self-test.

Compose nạp `/judge/.docker/judge.yml`, khai báo `problem_storage_globs`
trỏ tới `/problems/**/`. Mỗi bài cần thư mục `<problem_code>` chứa
`init.yml` và test data tương ứng. Thư mục trống vẫn cho judge online,
nhưng chưa có bài để chấm. Upload test data qua VNOJ hoặc đặt dữ liệu
đúng định dạng vào `VNOJ_PROBLEMS_DIR`.

```powershell
docker compose -f compose.vnoj.yml stop judge
```

Dừng judge giữ nguyên database và problem data.
