# Remote Development Guide — Label Guardian VM

Tài liệu này hướng dẫn thành viên trong team SSH vào VM production/self-host của Label Guardian, mở workspace bằng VS Code Remote SSH, chỉnh sửa code và deploy thay đổi lên sản phẩm một cách có kiểm soát.

> Kế hoạch production dài hạn là mirror sang repo deploy mới, Vercel host frontend và VM chỉ host backend/API. Xem luồng triển khai trong [HYBRID_VERCEL_VM_DEPLOYMENT.md](./HYBRID_VERCEL_VM_DEPLOYMENT.md). Phần bên dưới vẫn mô tả VM self-host hiện tại.

## 1. Thông Tin VM

VM hiện tại:

```text
GCP project: ai-lab-16-gcp-505508
VM name: label-guardian-vm
Zone: asia-southeast1-a
Static IP: 34.143.247.68
Domain: https://labelguardian.space
Source path trên VM: /opt/label-guardian/app
Production env file: /opt/label-guardian/.env.production
Compose file: docker-compose.selfhost.yml
```

Stack production chạy bằng Docker Compose:

```text
backend   FastAPI
frontend  Nginx static frontend
proxy     Caddy HTTPS reverse proxy
```

## 2. Nguyên Tắc Làm Việc

VM này là môi trường self-host đang phục vụ sản phẩm public. Vì vậy, không nên coi VM là nơi mỗi người tự sửa tùy ý.

Nguyên tắc chung:

- Mọi thay đổi code phải đi qua Git.
- Không sửa trực tiếp file production rồi bỏ đó không commit.
- Không commit `.env`, secret, token, key hoặc credential.
- Không chạy lệnh destructive như `git reset --hard`, `docker system prune -a`, xóa volume hoặc xóa database nếu chưa thống nhất.
- Mỗi người làm trên branch riêng, không cùng sửa trực tiếp trên `main`.
- Chỉ deploy từ branch/commit đã rõ ràng.
- Trước khi deploy phải kiểm tra trạng thái container và health endpoint.

## 3. Cấp Quyền Cho Thành Viên

Mỗi thành viên cần có tài khoản Google Cloud được thêm vào project `ai-lab-16-gcp-505508`.

Role tối thiểu nên cấp:

```text
Compute OS Login
Compute Viewer
Service Account User hoặc quyền SSH phù hợp theo policy của project
```

Nếu team dùng OS Login, mỗi thành viên đăng nhập bằng tài khoản Google riêng. Không chia sẻ SSH private key hoặc tài khoản chung.

Kiểm tra account local:

```bash
gcloud auth login
gcloud config set project ai-lab-16-gcp-505508
gcloud config get-value account
```

## 4. SSH Vào VM Bằng Terminal

Lệnh SSH chuẩn:

```bash
gcloud compute ssh label-guardian-vm \
  --project=ai-lab-16-gcp-505508 \
  --zone=asia-southeast1-a
```

Sau khi vào VM:

```bash
cd /opt/label-guardian/app
git status
```

Kiểm tra container:

```bash
export SELFHOST_ENV_FILE=/opt/label-guardian/.env.production
sudo -E docker compose --env-file "$SELFHOST_ENV_FILE" \
  -f docker-compose.selfhost.yml \
  --profile internet ps
```

Kiểm tra app:

```bash
curl -f https://api.labelguardian.space/health
curl -f https://api.labelguardian.space/ready
curl -f https://api.labelguardian.space/api/v1/health
```

## 5. Mở Workspace VM Bằng VS Code Remote SSH

### 5.1. Cài Extension

Trên máy cá nhân, cài VS Code extension:

```text
Remote - SSH
```

Extension ID:

```text
ms-vscode-remote.remote-ssh
```

### 5.2. Tạo SSH Config Local

Chạy lệnh sau một lần để gcloud tạo SSH key/config:

```bash
gcloud compute ssh label-guardian-vm \
  --project=ai-lab-16-gcp-505508 \
  --zone=asia-southeast1-a \
  --dry-run
```

Lệnh này sẽ in ra command SSH thật. Sau đó mở file:

```bash
code ~/.ssh/config
```

Thêm host dạng sau. Nếu `IdentityFile` của bạn khác, lấy đúng đường dẫn từ output `--dry-run`.

```sshconfig
Host label-guardian-vm
  HostName 34.143.247.68
  User <your-linux-username>
  IdentityFile ~/.ssh/google_compute_engine
  IdentitiesOnly yes
  CheckHostIP no
  StrictHostKeyChecking no
```

Gợi ý: `<your-linux-username>` thường là username do gcloud tạo từ email Google của bạn. Cách chắc nhất là xem output của:

```bash
gcloud compute ssh label-guardian-vm \
  --project=ai-lab-16-gcp-505508 \
  --zone=asia-southeast1-a \
  --dry-run
```

### 5.3. Connect Bằng VS Code

Trong VS Code:

```text
F1 / Ctrl+Shift+P
Remote-SSH: Connect to Host...
label-guardian-vm
```

Sau khi VS Code mở cửa sổ remote:

```text
File → Open Folder
```

Chọn:

```text
/opt/label-guardian/app
```

Nếu repo nằm trong home của user khác, hỏi maintainer trước khi sửa quyền hoặc copy repo. Không tự `chmod -R 777`.

## 6. Workflow Chỉnh Code An Toàn

Trước khi sửa:

```bash
cd /opt/label-guardian/app
git fetch origin
git status
```

Nếu đang ở `main`, tạo branch riêng:

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/<short-task-name>
```

Ví dụ:

```bash
git switch -c feature/qa-case-filter
```

Trong quá trình sửa:

```bash
git status --short
git diff
```

Commit:

```bash
git add <files>
git commit -m "feat: describe the change"
```

Push branch:

```bash
git push -u origin feature/<short-task-name>
```

Sau đó mở PR hoặc nhờ reviewer merge vào `main`.

## 7. Cách Tránh Conflict Khi Nhiều Người Cùng Sửa

Không có cách nào loại bỏ conflict hoàn toàn, nhưng có thể giảm mạnh bằng quy ước làm việc.

Quy ước bắt buộc:

- Không cùng sửa trực tiếp trên `main`.
- Mỗi task dùng một branch riêng.
- Trước khi bắt đầu task, luôn `git pull --ff-only origin main`.
- Branch nhỏ, thay đổi nhỏ, merge sớm.
- Không format toàn bộ repo nếu task chỉ sửa một phần nhỏ.
- Không sửa file env production trừ khi task là deployment/config.
- Không sửa cùng một file lớn nếu chưa phân chia ownership.
- Khi cần đổi schema/API shared, báo team trước.

Quy ước ownership đề xuất:

- Backend/API: một người phụ trách route/service/model liên quan.
- Frontend/UI: một người phụ trách view/component liên quan.
- Ingestion/data: một người phụ trách script/job/adapter.
- Deployment/env: chỉ maintainer hoặc người được phân công sửa.

Trước khi merge branch:

```bash
git fetch origin
git rebase origin/main
```

Nếu có conflict, xử lý trên branch cá nhân, test lại, rồi push:

```bash
git push --force-with-lease
```

Chỉ dùng `--force-with-lease` trên branch của chính mình. Không force push `main`.

## 8. Đồng Bộ Từ Git Lên VM Và Deploy

VM deploy workspace hiện là bản source đồng bộ để chạy production, không phải nơi team chỉnh code trực tiếp. Quy trình chuẩn là sửa trên Git, merge/push branch rõ ràng, rồi dùng script local để đóng gói đúng Git snapshot và đồng bộ lên VM.

Script dùng chung:

```bash
scripts/deploy_selfhost_vm.sh
```

Script này sẽ:

- Lấy snapshot từ Git ref được chỉ định bằng `git archive`.
- Upload archive sang VM qua `scp`.
- Extract vào thư mục tạm trên VM.
- `rsync --delete` snapshot vào `/opt/label-guardian/app`.
- Không đồng bộ `.env`, secret, data runtime hoặc `node_modules`.
- Build lại backend Docker image.
- Chạy database migration.
- Restart backend và Caddy API proxy.
- Kiểm tra `https://api.labelguardian.space/health`, `/ready`, và `/api/v1/health`.

### 8.1. Chuẩn Bị Trước Khi Deploy

Trên máy cá nhân, đảm bảo SSH alias chạy được:

```bash
ssh label-guardian-vm 'hostname'
```

Kết quả mong đợi:

```text
label-guardian-vm
```

Đảm bảo code cần deploy đã nằm trong Git ref bạn muốn deploy. Ví dụ nếu deploy `origin/main`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
```

Nếu `git status --short` còn file chưa commit, các file đó sẽ không được deploy trừ khi bạn commit chúng vào Git ref được chọn.

### 8.2. Deploy `origin/main`

Đây là lệnh deploy chuẩn sau khi thay đổi đã merge vào `main`:

```bash
scripts/deploy_selfhost_vm.sh origin/main
```

Nếu muốn deploy local branch `main`:

```bash
scripts/deploy_selfhost_vm.sh main
```

Nếu muốn deploy một commit cụ thể:

```bash
scripts/deploy_selfhost_vm.sh <commit-sha>
```

Ví dụ:

```bash
scripts/deploy_selfhost_vm.sh 03640122
```

### 8.3. Deploy Không Chạy Migration

Chỉ dùng khi chắc chắn thay đổi không đụng schema/database:

```bash
SKIP_MIGRATIONS=1 scripts/deploy_selfhost_vm.sh origin/main
```

Mặc định nên để script chạy migration, vì migration idempotent theo Alembic và an toàn hơn khi có thay đổi backend/database.

### 8.4. Override Host Hoặc Đường Dẫn

Nếu SSH alias của bạn khác:

```bash
VM_HOST=label-guardian-vm scripts/deploy_selfhost_vm.sh origin/main
```

Nếu VM app dir thay đổi:

```bash
VM_APP_DIR=/opt/label-guardian/app scripts/deploy_selfhost_vm.sh origin/main
```

Các biến mặc định:

```text
VM_HOST=label-guardian-vm
VM_APP_DIR=/opt/label-guardian/app
SELFHOST_ENV_FILE=/opt/label-guardian/.env.production
SELFHOST_DATA_DIR=/opt/label-guardian/data
SELFHOST_GCLOUD_CONFIG_DIR=/opt/label-guardian/gcloud
IMAGE_TAG=vm-api
APP_HEALTH_URL=https://api.labelguardian.space/health
APP_READY_URL=https://api.labelguardian.space/ready
APP_V1_HEALTH_URL=https://api.labelguardian.space/api/v1/health
```

### 8.5. Vì Sao Cách Này Giảm Conflict

Cách này tách rõ hai nơi:

- Git branch là nơi phát triển và review code.
- VM là nơi nhận snapshot đã chọn để chạy sản phẩm.

VM không còn là nơi nhiều người cùng sửa file trực tiếp. Người nào muốn thay đổi sản phẩm phải đưa thay đổi vào Git trước, nhờ đó conflict được xử lý bằng Git trên branch cá nhân thay vì phát sinh âm thầm trên production server.

## 9. Đồng Bộ Snapshot Từ VM Về Máy

Chiều ngược lại, từ VM về máy local, chỉ nên dùng để inspect, recovery hoặc so sánh production đang có gì. Không dùng VM làm source of truth cho development.

Script dùng chung:

```bash
scripts/sync_selfhost_vm_from_vm.sh
```

Mặc định script kéo snapshot hiện tại trên VM về thư mục sibling:

```bash
../label-guardian-vm-snapshot
```

Lệnh chạy:

```bash
scripts/sync_selfhost_vm_from_vm.sh
```

Hoặc chỉ định thư mục đích:

```bash
scripts/sync_selfhost_vm_from_vm.sh ../label-guardian-vm-snapshot
```

Script này sẽ:

- Kéo source hiện đang nằm ở `/opt/label-guardian/app` trên VM về máy local.
- Không kéo `.env`, `.env.*`, secret, data runtime, `.git`, `node_modules`, cache hoặc virtualenv.
- Không xóa file local dư thừa theo mặc định.
- Có thể chạy dry-run trước để xem sẽ sync gì.

Dry run:

```bash
DRY_RUN=1 scripts/sync_selfhost_vm_from_vm.sh ../label-guardian-vm-snapshot
```

Nếu muốn snapshot local giống VM hơn và xóa file local dư trong thư mục snapshot:

```bash
DELETE_EXTRA=1 scripts/sync_selfhost_vm_from_vm.sh ../label-guardian-vm-snapshot
```

Script mặc định từ chối sync trực tiếp vào repo hiện tại để tránh ghi đè code đang làm. Nếu thật sự cần overwrite current repo từ VM, phải bật cờ rõ ràng và repo phải sạch:

```bash
ALLOW_CURRENT_REPO_OVERWRITE=1 scripts/sync_selfhost_vm_from_vm.sh .
```

Quy tắc an toàn:

- Ưu tiên sync về thư mục snapshot riêng.
- Sau đó dùng `diff`, `rsync --dry-run`, hoặc công cụ compare của VS Code để chọn file cần lấy.
- Không pull từ VM rồi commit thẳng nếu chưa hiểu vì sao VM khác Git.
- Nếu VM có hotfix chưa nằm trong Git, đưa hotfix đó vào branch mới, review, rồi merge lại theo quy trình bình thường.

## 10. Xem Logs

Backend logs:

```bash
sudo docker logs label-guardian-selfhost-backend-1 --tail 200 -f
```

Frontend logs:

```bash
sudo docker logs label-guardian-selfhost-frontend-1 --tail 200 -f
```

Caddy/HTTPS logs:

```bash
sudo docker logs label-guardian-selfhost-proxy-1 --tail 200 -f
```

Compose logs:

```bash
export SELFHOST_ENV_FILE=/opt/label-guardian/.env.production
sudo -E docker compose --env-file "$SELFHOST_ENV_FILE" \
  -f docker-compose.selfhost.yml \
  --profile internet logs -f --tail 200
```

## 11. Sửa Env Production

File env production:

```text
/opt/label-guardian/.env.production
```

Chỉ sửa file này khi thật sự cần đổi cấu hình deploy, domain, auth, database hoặc storage.

Trước khi sửa, backup:

```bash
sudo cp /opt/label-guardian/.env.production \
  /opt/label-guardian/.env.production.bak-$(date +%Y%m%d%H%M%S)
```

Sửa:

```bash
sudo nano /opt/label-guardian/.env.production
```

Sau khi sửa env, restart các service liên quan. Nếu đổi biến build-time của frontend như `VITE_*`, cập nhật biến trên Vercel và redeploy frontend ở đó.

## 12. Checklist Trước Khi Kết Thúc Task

Trước khi rời VM hoặc báo task xong:

- `git status` sạch hoặc đã ghi rõ file nào còn WIP.
- Branch đã push lên remote nếu có thay đổi code.
- Không để secret trong shell history, commit, log hoặc issue.
- Container đang healthy.
- `https://api.labelguardian.space/health` trả OK.
- `https://api.labelguardian.space/ready` trả OK.
- `https://api.labelguardian.space/api/v1/health` trả OK.
- Nếu có migration, đã xác nhận migration chạy thành công.
- Nếu có thay đổi auth/domain, đã cập nhật Supabase redirect URL tương ứng.

## 13. Khi Có Sự Cố

Nếu deploy lỗi:

```bash
sudo -E docker compose --env-file "$SELFHOST_ENV_FILE" \
  -f docker-compose.selfhost.yml \
  --profile internet ps

sudo docker logs label-guardian-selfhost-backend-1 --tail 200
sudo docker logs label-guardian-selfhost-frontend-1 --tail 200
sudo docker logs label-guardian-selfhost-proxy-1 --tail 200
```

Nếu backend unhealthy:

- Kiểm tra migration.
- Kiểm tra env production.
- Kiểm tra database connection.
- Kiểm tra import/module error trong logs.

Nếu HTTPS lỗi:

- Kiểm tra DNS `labelguardian.space` trỏ về `34.143.247.68`.
- Kiểm tra firewall port 80/443.
- Kiểm tra Caddy logs.

Nếu app không load data:

- Kiểm tra backend `/ready`.
- Kiểm tra auth token trong browser.
- Kiểm tra Supabase Auth redirect URL.
- Kiểm tra backend logs khi gọi dataset API.
- Kiểm tra GCS permission và dataset prefix.
