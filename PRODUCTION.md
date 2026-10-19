# Judge production cho ITMC OJ

Workflow này dành cho judge và OJ chạy cùng Linux VPS. Judge kết nối bridge TCP
qua Docker network, không qua HTTPS domain. Không cần mở cổng 9999 ra Internet.
Đối với máy judge riêng, cần thiết kế VPN/tunnel và đồng bộ problem data riêng.

## Khởi tạo

Cần Docker Engine, Compose plugin, GNU Make, Bash, OpenSSL và Python 3. Image judge
hiện dùng base VNOJ `judge-tiervnoj`, pin multi-platform digest trong Dockerfile.
Registry cung cấp amd64/arm64; native extensions vẫn cần build/test trên kiến trúc VPS.
Dockerfile hiện đặt DMOJ_TARGET_ARCH=x86-64; workflow này được build kiểm chứng trên
Linux amd64, không khẳng định hỗ trợ ARM chỉ dựa trên manifest của base.

```bash
cd ~
git clone --recurse-submodules git@github.com:ITMC-Projects/judge-server.git
cd judge-server
make prod-init
nano production/judge.env
```

Không copy `.env` dev. Init chỉ tạo file còn thiếu, điền key/path còn rỗng, không
ghi đè giá trị đã có. Judge key là 32 byte ngẫu nhiên (64 ký tự hex), không in ra log,
file env mode 600, bị loại khỏi Git và Docker build context.

Cấu hình trong `production/judge.env`:

```dotenv
DMOJ_JUDGE_NAME=judge-prod-01
DMOJ_JUDGE_KEY=GIU_KEY_DA_SINH
OJ_NETWORK=itmc-oj-prod_db
OJ_BRIDGE_HOST=itmc-oj-prod-bridged
OJ_BRIDGE_PORT=9999
OJ_PROBLEMS_DIR=/home/itmc/ITMC-OJ-docker/dmoj/production/data/problems
```

`prod-init` tự điền đường dẫn problems của repository OJ nằm cạnh judge-server;
sửa đường dẫn tuyệt đối nếu bố trí khác. Các tên network/bridge mặc định khớp OJ
production. Giá trị là literal không quote, không `$` hay nội suy shell.

Mở Django Admin của OJ → Judges → thêm judge với **đúng name và key** từ file trên,
cho phép kết nối nếu có tùy chọn. Đây là đăng ký tài khoản judge, không dùng OTS
service token. Không gửi key vào chat, commit hoặc log.

`production/config/judge.yml` cũng được init tạo từ template và mount read-only tại
`/judge/.docker/judge.yml`. Mặc định tìm problem data ở `/problems/**/`. Không đặt key
trong YAML; giữ credentials ở env. Config YAML cần mode 644 vì process judge hạ quyền.

## Khởi động

OJ phải được triển khai trước:

```bash
cd ~/ITMC-OJ-docker
make prod-ps
docker network inspect itmc-oj-prod_db >/dev/null
```

User judge trong container cần quyền đọc/traverse thư mục problems. Với thư mục
gốc mới được OJ prod-init tạo mode 700, quản trị viên cần cho phép traverse/read:

```bash
chmod 755 ~/ITMC-OJ-docker/dmoj/production/data/problems
```

Chỉ thực hiện nếu phù hợp chính sách tài khoản trên VPS. Nếu test data phải giữ
private với user khác, dùng ACL cho UID judge thay vì mở quyền other; xem phần dưới.
File/test directory bên trong cũng cần quyền đọc/traverse cho judge.

```bash
cd ~/judge-server
make prod
make prod-logs
```

Lần đầu chưa có image `itmc-oj-prod/judge:local`, prod tự build. Những lần sau **chỉ
reuse image và recreate/start**, không build lại. Sau khi sửa source hoặc cập nhật
Git, chạy `make prod-build` rồi `make prod`.

Trước khi start, script kiểm tra env/Compose, network OJ tồn tại và quyền đọc config,
problems bằng user judge thật. Container không publish port nào, problems/config
mount read-only, log rotation 10MB × 5 và restart unless-stopped. Không tự sửa quyền
trên dữ liệu dùng chung của OJ. Project/image production tách biệt Compose dev.

`make prod` xác nhận process chạy; chưa xác nhận authentication hoặc grading. Kiểm tra
log runtime self-test, judge online trên OJ và gửi một submission có test data thật.
Problems rỗng có thể cho judge online nhưng chưa có bài để chấm. Không tắt executor
self-test để che lỗi runtime/sandbox. Đây là judge thật, không phải simulated worker.

## Vận hành

* `make prod-init`: tạo các file thiếu, không ghi đè config/key đã tồn tại.
* `make prod`: kiểm tra và start/recreate; chỉ build nếu chưa có image.
* `make prod-build`: build lại image từ source hiện tại.
* `make prod-restart`: recreate để áp dụng config/env, cũng build nếu chưa có image.
* `make prod-check`: validate env/path và Compose, không build/start container.
* `make prod-logs`, `make prod-ps`: logs/status.
* `make prod-down`: dừng/remove container, không xóa problem data của OJ.

Không chạy production và dev bằng cùng judge name/key; mỗi worker phải có danh tính
riêng. Stop judge trước update và đợi submission đang xử lý hoàn tất; stop grace
120 giây không bảo đảm hoàn thành bài chạy lâu hơn. Backup problems thuộc workflow
OJ, còn judge key/config phải lưu trong kho bảo mật riêng.

## Lỗi thường gặp

* Network unavailable: OJ chưa start, khác Docker host/context hoặc OJ_NETWORK sai.
* Pull access denied cho `vnoj/judge-tier1`: Dockerfile cũ trỏ image không truy cập
  được. Chạy `git pull --ff-only`, rồi `make prod` (hoặc prod-build nếu đã có image).
  Dockerfile mới dùng public `vnoj/judge-tiervnoj`, pin digest đã kiểm tra registry.
  Lần đầu cần tải base image lớn hơn tier1 cũ và đủ dung lượng đĩa. Không sửa judge key
  hoặc OTS tokens để xử lý lỗi pull image; bước này chưa kết nối tới OJ.
* Connection refused/DNS: kiểm tra `make prod-logs SERVICE=bridged` phía OJ, bridge
  hostname và port 9999. Không dùng hostname dev `vnoj_bridged` cho production.
* Authentication failed: so sánh name/key với OJ Admin, bật cho phép kết nối; không
  nhầm key với SECRET_KEY Django hay OTS token.
* Problems permission denied: dùng quyền filesystem phù hợp. Ví dụ ACL cho UID judge
  sau khi image đã build (`sudo apt-get install acl` nếu thiếu setfacl):

  ```bash
  make prod-build
  judge_uid=$(docker run --rm --entrypoint /usr/bin/id itmc-oj-prod/judge:local -u judge)
  sudo setfacl -R -m "u:${judge_uid}:rX" /home/itmc/ITMC-OJ-docker/dmoj/production/data/problems
  sudo find /home/itmc/ITMC-OJ-docker/dmoj/production/data/problems -type d -exec setfacl -m "d:u:${judge_uid}:r-x" {} +
  make prod
  ```

  UID được dùng trực tiếp trên Linux Docker mặc định; user namespace remapping/rootless
  cần điều chỉnh mapping. Đối chiếu ACL sau các lần OJ thay thế directory/test data.
* Không thấy bài: kiểm tra `<problem_code>/init.yml`, testcase và storage glob; OJ
  problem code phải trùng directory. Kiểm tra runtime ngôn ngữ khởi tạo thành công.

## Kiểm chứng thay đổi

Chạy `python3 scripts/test-production.py` để kiểm tra initializer giữ nguyên config/key,
validation từ chối placeholder/key yếu/path thiếu, và Compose contract không publish
port, mount đúng read-only/network production. `bash -n scripts/prod.sh`, `make`,
`make -n prod` cũng được kiểm tra trong môi trường phát triển.

Sau bản sửa base image, đã kiểm chứng registry manifest của digest mới và chạy thành
công `docker build -t itmc-oj-prod/judge:local .` trên Docker Linux amd64, gồm native
extensions Python 3.14. Ba test cấu hình, Bash syntax và diff check đều pass.
Container test grading và cả smoke test chỉ chạy `/bin/true` bị Docker Desktop giữ
ở trạng thái Created, chưa có process/log. Vì vậy chưa kiểm chứng runtime, ACL thực
tế, authentication hoặc grading; cần chạy lại trên VPS. Không coi build thành công
là đã xác nhận judge online/chấm đúng.
