# Label Guardian UI Upgrade Strategy

## 1. Mục tiêu

Nâng Label Guardian thành một perception QA platform có ngôn ngữ hình ảnh thống nhất từ landing page đến workspace, đồng thời giữ nguyên toàn bộ logic nghiệp vụ, route, API contract, quyền truy cập và workflow review.

Kết quả mong muốn:

- Landing page giàu chuyển động, giúp người xem hiểu nhanh data flow và human review workflow.
- Workspace yên tĩnh, rõ trạng thái, tối ưu cho thao tác lặp lại và dữ liệu dày.
- Màu sắc thống nhất giữa overview, queue, case review, editor, reports và settings.
- Mỗi trạng thái semantic có ý nghĩa cố định, không dùng màu trang trí để biểu diễn dữ liệu.
- Có lộ trình rollout từng phần, kiểm thử được và có thể quay lại token cũ nếu cần.

## 2. Nguyên tắc không thay đổi logic

Các hạng mục sau là bất biến trong quá trình nâng cấp:

- Không đổi URL, route slug hoặc mapping trong information architecture.
- Không đổi API request, response DTO, query key hoặc cache behavior.
- Không đổi state transition của QA case và annotation revision.
- Không đổi role permission, authentication flow hoặc route guard.
- Không đổi tên field, form order và command label đang được test hoặc dùng cho automation.
- Không đổi data selection, filter semantics, severity calculation và report metric.
- Không gộp component nếu việc gộp làm thay đổi ownership hoặc event flow.

Mọi pull request về giao diện phải tách biệt thay đổi presentation khỏi thay đổi nghiệp vụ. Nếu cần chỉnh logic, thực hiện bằng một pull request riêng.

## 3. Audit hiện trạng

### Điểm đang tốt

- Dark workspace phù hợp với dữ liệu perception và thời gian review dài.
- IA đã rõ: Overview, QA Queue, QA Cases, Case Review, 2D Editor, Datasets / Runs, Pipeline, Reports và Settings.
- Các trạng thái risk, run, review và revision đã có cấu trúc semantic.
- Landing page đã có visual asset và mô phỏng đúng data workflow.
- Workspace có shell dùng chung, thuận lợi để rollout token theo chiều ngang.

### Điểm cần giải quyết

- Landing dùng teal, workspace shell dùng violet, queue/editor dùng blue và cyan.
- Nhiều màu hex và rgba đang hard-code trong từng stylesheet.
- Token hiện tại dùng tên màu như `--blue` và `--purple`, chưa mô tả vai trò.
- Surface, line và text tone thay đổi giữa queue, editor và report.
- Typography chưa có scale chung cho app heading, panel heading, metadata và số liệu.
- Radius trải từ 4px đến pill, thiếu quy tắc component-level.
- Motion có ở sidebar và landing nhưng chưa có motion language thống nhất.
- Loading, empty và error state chưa cùng một cấu trúc hình ảnh.

## 4. North star

### Landing

Dark-tech, cinematic và có data motion. Chuyển động chỉ dùng để chỉ hướng pipeline, thay đổi section và phản hồi tương tác.

### Workspace

Quiet operations console. Ít hiệu ứng nền, surface rõ cấp độ, density cao vừa phải và trạng thái nhìn được trong một lần quét.

### Ngôn ngữ chung

- Nền charcoal có tint xanh lục rất nhẹ.
- Teal là brand action duy nhất.
- Success, warning và danger chỉ xuất hiện khi có ý nghĩa trạng thái.
- Dữ liệu số dùng tabular figures.
- Border mảnh thay cho shadow nặng.
- Ảnh perception là visual chủ đạo, không thêm illustration trang trí.

## 5. Hệ màu đề xuất

### Core surfaces

| Token | Giá trị | Vai trò |
| --- | --- | --- |
| `--color-canvas` | `#090d10` | Nền ứng dụng |
| `--color-canvas-subtle` | `#0d1418` | Nền section hoặc sidebar |
| `--color-surface-1` | `#121b20` | Card và panel |
| `--color-surface-2` | `#172329` | Control và surface nổi |
| `--color-surface-3` | `#1c2b31` | Hover và selected surface |
| `--color-line` | `rgba(205, 235, 235, 0.10)` | Divider mặc định |
| `--color-line-strong` | `rgba(205, 235, 235, 0.18)` | Control boundary |

### Text

| Token | Giá trị | Vai trò |
| --- | --- | --- |
| `--color-text-strong` | `#edf5f5` | Heading và dữ liệu chính |
| `--color-text` | `#c4d1d3` | Body và label |
| `--color-text-muted` | `#8fa3a8` | Metadata |
| `--color-text-faint` | `#62777d` | Placeholder và disabled |

### Brand action

| Token | Giá trị | Vai trò |
| --- | --- | --- |
| `--color-brand` | `#56c9bf` | Focus, active indicator |
| `--color-brand-strong` | `#2b7973` | Primary button |
| `--color-brand-hover` | `#348b84` | Primary hover |
| `--color-brand-soft` | `rgba(86, 201, 191, 0.11)` | Selected surface |

### Semantic status

| Token | Giá trị | Phạm vi |
| --- | --- | --- |
| `--color-success` | `#63b78f` | Confirmed, corrected, healthy |
| `--color-warning` | `#d2a35d` | Medium risk, pending attention |
| `--color-danger` | `#d9707a` | High risk, failed, destructive |
| `--color-info` | `#73a8ce` | Informational state, không dùng cho CTA |

Quy tắc phân bổ: 80% neutral surfaces, 15% brand teal, tối đa 5% semantic colors. Violet hiện tại không còn là generic accent. Trong giai đoạn migration, `--blue` ánh xạ tạm sang `--color-brand` để tránh thay đổi component behavior.

## 6. Typography

### Font

- Giai đoạn đầu giữ stack hiện tại để giảm rủi ro layout.
- Giai đoạn typography chuyển sang self-hosted Geist Sans hoặc một grotesk tương đương.
- Metadata, ID, timestamp và số liệu kỹ thuật dùng Geist Mono hoặc system monospace.
- Không tải font từ CDN trong production.

### Scale

| Role | Size | Weight | Line height |
| --- | --- | --- | --- |
| App title | 28-32px | 650-700 | 1.1 |
| Section title | 20-24px | 650 | 1.2 |
| Panel title | 13-15px | 650 | 1.3 |
| Body | 12-14px | 450-500 | 1.5 |
| Metadata | 10-11px | 500-600 | 1.4 |
| Data number | 20-30px | 650 | 1 |

Mọi số liệu dùng `font-variant-numeric: tabular-nums`. Heading dùng `text-wrap: balance`, body dùng `text-wrap: pretty`.

## 7. Spacing, shape và elevation

### Spacing

Dùng thang 4px: 4, 8, 12, 16, 20, 24, 32, 40 và 48. Page padding desktop 24-32px, mobile 12-16px.

### Radius

- Buttons và inputs: 7-8px.
- Inner tiles và compact controls: 6px.
- Cards và panels: 10px.
- Landing media containers: 16px.
- Pill chỉ dùng cho filter chip, segmented state hoặc status có nội dung ngắn.

### Elevation

- Level 0: canvas, không shadow.
- Level 1: border và surface contrast.
- Level 2: popover dùng shadow tint theo canvas.
- Level 3: modal hoặc command palette, kết hợp scrim.

Không dùng shadow để phân tách mọi card.

## 8. Motion language

| Motion | Duration | Dùng cho |
| --- | --- | --- |
| Instant | 100-140ms | Checkbox, icon feedback |
| Standard | 180-220ms | Hover, selection, menu |
| Emphasis | 260-340ms | Sidebar, panel expansion |
| Narrative | 420-700ms | Landing section transition |

Quy tắc:

- Chỉ animate `transform` và `opacity`.
- Không dùng scroll listener cập nhật React state theo frame.
- Landing dùng IntersectionObserver hoặc CSS scroll-driven animation.
- Workspace không dùng parallax hoặc perpetual decoration.
- Mọi motion lớn hơn standard phải hỗ trợ `prefers-reduced-motion`.

## 9. Component system cần chuẩn hóa

### Foundation

- Semantic color tokens.
- Typography roles.
- Focus ring và keyboard navigation.
- Shared radius, spacing và z-index scale.

### Controls

- Button: primary, secondary, ghost, danger.
- IconButton: tooltip bắt buộc khi icon không tự giải thích.
- Select, input, search và textarea.
- Checkbox, toggle và segmented control.
- Badge chỉ dành cho semantic status.

### Data display

- KPI stat với tabular figures.
- Data table row states: default, hover, selected, loading và disabled.
- Evidence block và metadata group.
- Empty, loading và error panel dùng chung.
- Skeleton giữ đúng kích thước final layout để tránh CLS.

### Navigation

- Global workspace topbar.
- Collapsible sidebar với active route rõ.
- Breadcrumb cho Case Review và Editor.
- Landing contextual header và section dock.

## 10. Chiến lược theo từng page

### Authentication

- Đồng bộ canvas và teal brand với landing.
- Giảm blue glow, tăng contrast của form.
- Thêm link quay về landing rõ ràng.
- Giữ nguyên Supabase Auth flow và field order.

### Workspace shell

- Thay violet generic bằng brand teal.
- Chuẩn hóa topbar, sidebar, account popover và focus state.
- Dataset và role switcher dùng cùng control tokens.
- Giữ nguyên navigation mapping và role filtering.

### Overview

- KPI dùng một grid hierarchy, không dùng nhiều màu cho từng card.
- Chỉ risk và health state được dùng semantic color.
- Ưu tiên queue entry point và dataset health.
- Giữ nguyên query, metrics và CTA handlers.

### QA Queue và QA Cases

- Đây là surface có density cao nhất.
- Chuẩn hóa filter bar, selected row, image viewer và evidence panel.
- Selected state dùng brand soft; severity dùng semantic color.
- Không thay đổi filter semantics, pagination hoặc case selection.

### Case Review

- Xây hierarchy ba tầng: frame, evidence, decision.
- Sticky decision rail trên desktop, bottom action tray trên mobile.
- Revision history dùng timeline nhẹ, không dùng nhiều card lồng nhau.
- Giữ nguyên approve, edit, restore và status transition.

### 2D Editor

- Tách tool color khỏi semantic status.
- Toolbar dùng icon button có tooltip và selected state rõ.
- Label, prediction và selection overlay có palette riêng, đạt contrast trên ảnh.
- Không đổi geometry math, shortcut, save hoặc restore behavior.

### Datasets / Runs

- Run progress, ingestion state và dataset version cùng một visual grammar.
- Dùng timeline hoặc stage rail thay cho nhiều progress card.
- Giữ nguyên run state và backend polling.

### Pipeline

- Dùng stage graph và live log hierarchy.
- Running, completed và failed có icon + text, không phụ thuộc màu đơn thuần.
- Giữ nguyên worker log, stage mapping và refresh behavior.

### Reports

- Chart palette giới hạn: brand, neutral và semantic colors.
- Legend và tooltip dùng token chung.
- Export controls cùng pattern với topbar controls.
- Không thay đổi metric calculation hoặc export data.

### Settings

- Group cấu hình theo Rules, Models, Access và Data.
- Sticky save area chỉ được thêm khi có dirty state thật.
- Validation hiển thị inline.
- Giữ nguyên threshold range, role control và persistence.

## 11. Lộ trình rollout

### Phase 0: Baseline

- Chụp screenshot desktop và mobile cho mọi route.
- Ghi lại keyboard flow, network request và test baseline.
- Lập danh sách visual selectors đang được automation sử dụng.

### Phase 1: Token bridge

- Tạo `tokens.css` với semantic token mới.
- Import trước `base.css`.
- Ánh xạ token cũ sang token mới để component chưa migrate vẫn hoạt động.
- Không thay component markup trong phase này.

### Phase 2: Shell

- Migrate body, topbar, sidebar, navigation, popover và controls chung.
- Test role visibility, auth redirect và route navigation.

### Phase 3: Core review workflow

- Migrate QA Queue, QA Cases, Case Review và 2D Editor.
- Đây là phase có mức ưu tiên cao nhất vì trực tiếp ảnh hưởng thời gian xử lý case.

### Phase 4: Operations

- Migrate Overview, Datasets / Runs và Pipeline.
- Chuẩn hóa loading, empty, error và live status.

### Phase 5: Reporting và administration

- Migrate Reports và Settings.
- Hoàn thiện chart palette, form validation và access-denied state.

### Phase 6: Cleanup

- Xóa alias token cũ sau khi `rg` không còn consumer.
- Xóa hard-coded color không thuộc image overlay hoặc data visualization.
- Chạy accessibility, responsive, visual regression và bundle audit.

## 12. Cách tổ chức code

Đề xuất:

```text
frontend/src/styles/
  tokens.css
  foundations.css
  components/
    buttons.css
    forms.css
    navigation.css
    states.css
  pages/
    overview.css
    queue.css
    case-review.css
    editor.css
    operations.css
    reports.css
```

Không cần di chuyển toàn bộ file ngay. Tạo token bridge trước, sau đó di chuyển CSS khi một page được migrate hoàn chỉnh.

## 13. Verification contract

Mỗi phase phải đạt:

- TypeScript typecheck.
- Unit và integration test hiện có.
- Route smoke test cho mọi role.
- Không tăng số API request khi chỉ thay UI.
- Keyboard test: skip link, tab order, focus visible và menu escape.
- Screenshot desktop 1440px, laptop 1280px, tablet 768px và mobile 390px.
- Contrast WCAG AA cho body và control.
- `prefers-reduced-motion` không còn perpetual animation.
- Không có horizontal overflow.
- Không có text hoặc control overlap.
- Build production thành công.

## 14. Chỉ số đánh giá sau rollout

- Thời gian từ mở QA Queue đến quyết định đầu tiên.
- Số click để mở case, sửa annotation và lưu revision.
- Tỷ lệ reviewer quay lại queue sau khi xử lý case.
- Số lỗi thao tác do selected state hoặc active route không rõ.
- Tỷ lệ task hoàn thành bằng keyboard.
- CLS, INP và LCP cho landing và các route chính.

## 15. Thứ tự ưu tiên đề xuất

1. Token bridge và workspace shell.
2. QA Queue và Case Review.
3. 2D Editor.
4. Overview và Datasets / Runs.
5. Pipeline.
6. Reports và Settings.
7. Auth polish và cleanup cuối.

Thứ tự này đưa thay đổi có giá trị vận hành cao nhất lên trước, đồng thời giữ blast radius nhỏ và dễ kiểm chứng.

---

# Phần II — Workspace Product UI Plan v2

Phần này là kế hoạch ưu tiên mới cho `Overview`, `QA Queue`, `QA Cases`, `Datasets / Runs` và `Reports`. Nó thay thế mức chi tiết page-level ở mục 10, 11 và 15 đối với năm trang này; các foundation về token, typography, color và verification ở Phần I vẫn giữ nguyên.

## 16. Decision record

- Mode: **Operate**, không phải marketing dashboard.
- Persona chính: **QA Reviewer**.
- Persona phụ nhưng bắt buộc demo đầy đủ: **Annotator** và **Admin / ML Engineer**.
- Được phép thay đổi mạnh bố cục, hierarchy và thứ tự thông tin.
- Desktop-first; tablet hỗ trợ monitoring, triage, assignment, comment và approve đơn giản.
- Mobile là inbox/read-only companion. Editor, frame comparison và bulk operation có fallback `Optimized for desktop`.
- Mục tiêu content: giảm 50–65% prose trên Overview, Dataset và Report; dữ liệu, hình ảnh frame, flow, chart và trạng thái thay cho paragraph.

## 17. Product workflow north star

```text
Customer data
  → Intake & validation
  → Reviewer creates batches
  → Assign frame tasks
  → Annotator labels
  → Submit revision
  → Reviewer reviews
      → Approve
      → Request changes + anchored comment
  → Annotator reworks
  → Re-review
  → Approved dataset release
```

Admin / ML Engineer chạy song song một vòng hiệu chứng:

```text
Agent evaluation
  → Compare with reviewer decisions
  → Inspect disagreement / false positives
  → Tune rule or threshold
  → Publish model/rule version
  → Monitor drift on the next run
```

Nguyên tắc cốt lõi:

- Mỗi frame task có đúng một `current stage`, một `current owner` và một `next action`.
- Reviewer có thể sửa lỗi nhỏ trực tiếp hoặc gửi rework về annotator.
- `Request changes` bắt buộc có reason category; free-text comment là phần bổ sung.
- Comment phải neo vào frame, object hoặc bbox và revision cụ thể.
- Rework quay lại reviewer cũ hoặc reviewer pool đã cấu hình.
- Revision history hiện tại tiếp tục là nguồn audit chính.
- Agent confidence không được hiển thị như độ đúng của annotation.

## 18. Domain model cần thể hiện trong UI

### Primary objects

```text
Customer Submission
  → Dataset Version
  → Batch
  → Frame Task
  → Annotation Revision
  → QA Case
  → Review Decision
  → Release
```

### State model

Không dùng một `ReviewStatus` để gánh assignment, workflow và resolution. Ba nhóm trạng thái phải độc lập:

| Nhóm | Trạng thái đề xuất |
| --- | --- |
| Task workflow | `unassigned → assigned → in_progress → submitted → in_review → changes_requested → resubmitted → approved` |
| Case outcome | `confirmed_issue`, `corrected`, `false_positive`, `escalated`, `skipped` |
| Batch lifecycle | `draft → ready → active → review → rework → approved → exported` |

Batch progress được tính từ task states, không nhập hoặc lưu lặp bằng tay.

### Comment contract

Một feedback item tối thiểu phải có:

- author và role;
- frame/object/bbox target;
- annotation revision;
- reason category;
- blocking hoặc non-blocking;
- resolved state;
- timestamp và audit event liên quan.

## 19. Information architecture mới

```text
Home
  Overview

Operations
  QA Queue
  QA Cases
  Datasets / Runs

Insights
  Reports

Administration
  Agent Calibration
  Pipeline
  Access & Settings
```

Ranh giới bắt buộc:

- **QA Queue**: focused processing mode cho công việc tiếp theo của user hiện tại.
- **QA Cases**: system of record để tìm kiếm, phân công, theo dõi và audit toàn bộ case.
- **Datasets / Runs**: intake, validation, batch creation, task division, run và release readiness.
- **Reports**: phân tích xu hướng và quyết định; không lặp lại operational inbox của Overview.

## 20. Shared workspace shell

### Global header

- Dataset/version context luôn hiện nhưng không chiếm spotlight.
- Global search hoặc command palette tìm dataset, batch, frame, task và case ID.
- Notification center nhóm theo `Assignment`, `Comment`, `Review decision`, `Run`.
- Role không chỉ là badge; Overview và primary action thay đổi theo role thật.
- Breadcrumb giữ return location và filter khi đi từ Case → Editor → Case → Queue.

### Role-aware primary action

| Role | Global primary action |
| --- | --- |
| Reviewer | `Start next review` |
| Annotator | `Continue labeling` hoặc `Resolve feedback` |
| Admin / ML Engineer | `Inspect agent drift` |

### Navigation behavior

- Desktop dùng sidebar ổn định; label không phụ thuộc hoàn toàn vào hover.
- Active route dùng teal soft + icon + text.
- Count chỉ dành cho actionable backlog, không dùng như decoration.
- Tablet thu gọn thành icon rail có tooltip.
- Mobile giữ tối đa bốn mục: Overview, Queue, Cases, More.

## 21. Overview — role-aware attention cockpit

### Job

Trả lời một câu duy nhất: **“Tôi cần xử lý gì ngay bây giờ?”**

### First viewport

1. Compact context bar: dataset, active batch, freshness và health.
2. Một primary action theo role.
3. Workflow funnel trực quan, click vào từng stage để mở filtered Queue/Cases.
4. `Attention map`: severity × queue age để nhận ra backlog nguy hiểm.

### Visual modules

- **Work funnel**: Assigned → In progress → Submitted → Review → Rework → Approved.
- **Attention map**: heatmap nhỏ, không dùng nhiều KPI card.
- **Dataset health**: coverage, blocking issue và run freshness bằng segmented bar.
- **Priority strip**: 5–8 task có thumbnail, owner, age và next action.
- **Agent signal strip** cho Admin: disagreement, failed evaluation và active rule/model version.

### Role variants

| Reviewer | Annotator | Admin / ML Engineer |
| --- | --- | --- |
| Waiting review | New assignments | Agent disagreement |
| Returned for re-review | Rework requested | Drift alerts |
| Critical unassigned | Unread comments | Failed runs |
| Reviewer workload | Batch progress | Rule/model changes |

### Actions

- Reviewer: `Start next review`, `Assign tasks`.
- Annotator: `Continue labeling`, `Resolve feedback`.
- Admin: `Inspect drift`, `Compare versions`.
- KPI hoặc chart selection phải deep-link sang page đã lọc; không có chart chỉ để xem.

### Remove or compress

- Bỏ welcome copy và phần mô tả hệ thống.
- Giữ tối đa 3–4 headline metrics.
- Không dùng mỗi màu cho một KPI card.
- Không lặp cùng một count ở KPI, chart và priority list.

## 22. QA Queue — focused workbench

### Job

Đưa user từ task hiện tại đến quyết định hoặc submission tiếp theo với ít chuyển context nhất.

### Desktop layout

```text
Task rail  |  Dominant frame viewer  |  Evidence / action rail
```

- Task rail: saved view, compact filter, thumbnail, stage, age và unread comment.
- Viewer: frame + GT/prediction overlay, compare modes và sequence context.
- Action rail: evidence, current owner, anchored comments và sticky decision area.
- Footer hoặc top toolbar: previous/next, queue position, keyboard hints trong tooltip.

### Saved views

- `My queue`
- `Unassigned`
- `Critical`
- `Awaiting review`
- `Changes requested`
- `Rework returned`
- `Agent disagreement`

### Role actions

| Reviewer | Annotator | Admin / ML Engineer |
| --- | --- | --- |
| Approve | Save revision | Run evaluation |
| Request changes | Submit for review | Inspect evidence |
| False positive | Reply to feedback | Compare rule/model version |
| Escalate | Skip with reason | Mark calibration sample |

### Interaction requirements

- Primary action duy nhất theo current stage.
- `Claim next` hoặc reservation để tránh hai reviewer xử lý cùng task.
- Return từ Editor giữ nguyên queue position, filters, zoom và selected overlay.
- `J/K`: previous/next; `Enter`: open; `E`: editor; `A`: approve; `Shift+R`: request changes.
- Shortcut tắt khi user đang nhập liệu.
- Error cục bộ giữ frame/data cũ và cho retry; không thay toàn page bằng error card.

### Visual density

- Không đặt KPI grid phía trên workbench.
- Risk luôn đi cùng issue type và evidence signal.
- Description của Agent tối đa 2–3 dòng; evidence định lượng hiển thị trước.

## 23. QA Cases — registry, planning and audit

### Job

Cho Reviewer/Admin tìm, lọc, assign và theo dõi toàn bộ lifecycle; cho Annotator thấy phần được giao và feedback liên quan.

### Default composition

1. Saved-view tabs dạng underline, không dùng pill.
2. Unified filter bar: search, stage, risk, assignee; filter khác nằm trong `More filters`.
3. Dense table là surface chính.
4. Selection mở side inspector; full visual review mở QA Queue.
5. Bulk bar chỉ xuất hiện khi có selection.

### Table columns

- checkbox;
- frame thumbnail;
- case / class;
- issue type;
- risk + evidence indicator;
- batch;
- owner;
- workflow stage;
- age / updated;
- unresolved comments;
- overflow action.

### Stage rail

`Detected → Assigned → Annotated → Review → Rework → Resolved`

Board view có thể được thêm sau nhưng chỉ nhóm theo stage; không xây Kanban trang trí hoặc drag/drop nếu backend chưa có transaction assignment an toàn.

### Bulk actions

- Assign / reassign.
- Change priority.
- Start review.
- Add to batch.
- Skip with reason.
- Select all filtered results phải là action tách biệt với select current page.

### Request changes flow

Form ngắn gồm reason category, target, comment, assignee và blocking flag. Sau submit:

1. tạo blocking comment;
2. chuyển task sang `changes_requested`;
3. trả task về annotator;
4. ghi audit event;
5. gửi notification;
6. hiển thị snapshot revision trong thread.

## 24. Datasets / Runs — intake to release control plane

### Job

Quản lý customer data, dataset version, batch, assignment, run và release readiness trong một control plane trực quan.

### First viewport

- Dense dataset/version list hoặc tree ở trái.
- Dataset lifecycle rail ở trung tâm:

```text
Intake → Validate → Batch → Assign → Label → Review → Approve → Export
```

- Context drawer bên phải cho selected batch/run.

### Primary visuals

- Segmented progress bar theo lifecycle, không dùng một dãy progress card.
- Coverage heatmap theo scene/sequence.
- Workload allocation theo annotator bằng horizontal bars.
- Blocking issues list có owner và retry/resolve action.
- Run comparison chỉ hiển thị delta với run trước: pass rate, risk cases, processing errors, rule/model version.
- Scene/frame preview dùng ảnh thật để user kiểm tra scope.

### Role actions

| Reviewer | Annotator | Admin / ML Engineer |
| --- | --- | --- |
| Create batch | View assigned scope | Start run |
| Assign frames | Open assigned tasks | Configure evaluation |
| Mark release ready | View batch instructions | Retry failed stage |
| Inspect blockers | View comments | View logs / compare version |

### Production truth

- Phân biệt rõ `official`, `smoke fallback` và `mock` bằng provenance, không chỉ bằng màu.
- Không hiển thị calibration score trước khi có evaluation set và công thức được xác nhận.
- Ingestion error hiển thị stage, timestamp, scope và retry action; không dùng paragraph mô tả hạ tầng.

## 25. Reports — question-led decision workspace

### Job

Trả lời bốn câu hỏi có thể hành động, không trở thành gallery biểu đồ.

### Tabs

1. **Quality** — label quality đang tốt lên hay xấu đi?
2. **Operations** — backlog nằm ở đâu và workflow chậm tại stage nào?
3. **Agent** — Agent đồng thuận với reviewer đến đâu và drift ở rule/model nào?
4. **Release** — dataset version đã đủ điều kiện export chưa?

### Shared filter bar

Dataset, split, batch/run, time range, issue type, stage và assignee. Filter đồng bộ URL; export là secondary action cùng toolbar, không đặt trong một card giải thích riêng.

### Visual plan

| Tab | Visual chính | Drill-through |
| --- | --- | --- |
| Quality | quality trend, issue mix, class × issue heatmap, rework rate | filtered Cases |
| Operations | workflow funnel, stage cycle time, backlog aging, workload balance | Queue hoặc Cases |
| Agent | reviewer disagreement, false-positive pattern, precision/recall by version | calibration samples |
| Release | approved coverage, blockers, unresolved comments, run freshness | Dataset batch |

Ưu tiên stacked trends, horizontal bars, heatmap và bullet charts. Hạn chế donut vì khó so sánh. Mỗi chart phải có tooltip, accessible summary/table và click-to-filter.

### Measurement ethics

- Không xếp hạng annotator chỉ bằng tốc độ.
- People analytics phải có approval, rework, difficulty và sample size context.
- Metric thiếu denominator hoặc telemetry hiển thị `Not tracked`, không dùng `0`.
- Không tạo một quality score tổng hợp che mất nguồn lỗi.

## 26. Button and control system

### Hierarchy

- **Primary**: tiến workflow (`Approve`, `Assign`, `Submit for review`, `Run agent`). Tối đa một primary trong mỗi vùng hành động.
- **Secondary**: mở công cụ hoặc tác vụ hỗ trợ (`Open editor`, `Export`, `Save view`).
- **Ghost**: navigation hoặc thao tác phụ ít rủi ro.
- **Danger**: destructive/irreversible; không dùng cho backlog bình thường.
- **IconButton**: chỉ dùng familiar symbols; bắt buộc tooltip và accessible name.

### Dimensions and labels

- Standard button: 36px; compact table button: 32px; icon button desktop: 32×32px.
- Touch target trên tablet/mobile tối thiểu 44px.
- Radius 6px; không dùng pill cho command button.
- Label bắt đầu bằng động từ, tối đa 2–3 từ.
- Loading giữ nguyên width, thay leading icon bằng spinner và khóa double-submit.
- Disabled phải có lý do; permission denied không được giả làm disabled state.

### Contextual actions

- Bulk actions nằm trong sticky selection bar, không rải button trên mỗi row.
- Rare actions nằm trong overflow menu.
- Action tác động trên hơn 20 items hoặc destructive phải confirm với số lượng/scope.
- Partial failure phải báo số thành công/thất bại và cho retry phần lỗi.
- Toast có `Undo` chỉ khi backend support transaction đảo ngược an toàn.

## 27. Color and data-visualization rules

- 80–90% màn hình là neutral canvas/surfaces.
- Teal xuất hiện dưới 5% diện tích và chỉ dành cho focus, active path hoặc primary action.
- Success, warning, danger và info luôn kèm icon/text, không truyền nghĩa chỉ bằng màu.
- `Unreviewed` là neutral, không phải danger.
- Annotation overlay dùng palette riêng: ground truth, prediction và selection không tái sử dụng status colors.
- Chart palette bắt đầu từ neutral + brand; semantic color chỉ dùng khi dữ liệu thật sự là semantic status.
- Không dùng gradient trang trí, glow, shadow card hoặc colored border stripe.
- Font tối thiểu 12px trong workspace; loại toàn bộ label 7–10px hiện tại.

## 28. Responsive contract

| Viewport | Capability |
| --- | --- |
| ≥1440px | Full three-column workbench, persistent inspector, full table |
| 1200–1439px | Filter drawer, inspector hẹp, vẫn hỗ trợ full review |
| 1024–1199px | Table + drawer; viewer và inspector không mở đồng thời |
| 768–1023px | Triage, assignment, comment, simple approval; charts một cột |
| <768px | Inbox, status, comment, notification và quick approval có giới hạn |

Mobile/tablet fallback:

- Editor, bbox resize, frame comparison và bulk operation hiển thị `Optimized for desktop`.
- Fallback giải thích ngắn lý do và giữ deep link để mở lại trên PC.
- Không render desktop table bị ép nhỏ; chuyển sang compact row list.
- Không hiển thị bảy icon navigation trên một hàng.

## 29. Backend and domain dependencies

### Có thể làm UI-first

- Giảm prose, đổi hierarchy và layout.
- Role-aware Overview bằng dữ liệu hiện có.
- Unified filter bar, saved-view presentation và side inspector.
- Button hierarchy, semantic color, keyboard/focus và responsive fallback.
- Reports tabs và chart composition trên metrics hiện có.

### Cần API/domain trước khi UI được coi là hoàn chỉnh

- Batch và frame-task assignment.
- Workflow stage tách khỏi review outcome.
- Reservation/lock cho reviewer.
- Anchored threaded comments và blocking resolution.
- Notification/inbox theo role.
- Return-to-reviewer routing.
- Workload, cycle-time và backlog-aging telemetry.
- Agent calibration sample, rule/model version comparison và disagreement labels.
- Frozen release object và release-readiness contract.

Không mock các capability này như đã tồn tại trong production UI. Trong demo, phải gắn nhãn `Demo workflow` hoặc dùng data fixture có contract rõ.

## 30. Rollout plan

### Phase A — Workflow contract

- Chốt domain objects, state transitions, role permission và event audit.
- Tạo fixture realistic cho một vòng approve và một vòng request-changes/rework.
- Chốt URL state cần giữ giữa Queue, Cases và Editor.

### Phase B — Shared interaction foundation

- Button/IconButton, tooltip, filter bar, saved views, bulk bar, drawer, toast và skeleton.
- Chuẩn hóa table density, chart wrapper, empty/loading/error state.
- Loại font dưới 12px và decorative grid khỏi workspace text pages.

### Phase C — QA Cases + QA Queue

- Xây case registry, assignment, comment/rework và focused review workbench.
- Đây là vertical slice đầu tiên phải demo end-to-end đủ ba role.

### Phase D — Datasets / Runs

- Intake, lifecycle rail, batch creation, frame assignment, run delta và release readiness.

### Phase E — Role-aware Overview

- Lắp các deep link và actionable summaries từ workflow thật.
- Overview làm sau Queue/Cases/Dataset để không tạo metric giả hoặc duplicated state.

### Phase F — Reports + Agent calibration

- Quality, Operations, Agent và Release tabs.
- Mọi chart drill-through về dữ liệu nguồn.

### Phase G — Responsive and production hardening

- Desktop 1440/1280, tablet 1024/768 và mobile 390.
- Keyboard, screen reader, contrast, performance và visual regression.

## 31. Acceptance metrics

### User outcomes

- Time-to-first-case từ Overview.
- Assignment latency từ batch ready đến annotator nhận task.
- Review turnaround từ submitted đến decision.
- Correction loop count mỗi task.
- Cases per focused session, không dùng đơn độc để xếp hạng người dùng.
- Tỷ lệ unresolved blocking comments.
- Agent false-positive/disagreement theo rule/model version.

### UX gates

- Mỗi viewport chỉ có một dominant action theo role/stage.
- Không có page-level horizontal overflow.
- Không có text/control overlap ở bốn viewport chuẩn.
- Không có body/control text dưới 12px desktop.
- Severity/stage không phụ thuộc màu đơn thuần.
- Loading không gây layout shift đáng kể.
- Error cục bộ không xóa dữ liệu còn dùng được.
- Tất cả chart có text summary và drill-through.
- Full keyboard path: Overview → Queue → Case → Editor → Case → next task.

## 32. Market references

Các pattern được tham khảo, không sao chép trực tiếp:

- [Scale Rapid Pipelines](https://scale.com/docs/rapid-or-pipelines): attempt/review và vòng rejected quay lại annotation.
- [Scale Rapid Production](https://scale.com/docs/rapid-or-production): calibration, training/evaluation tasks và quality monitoring.
- [Labelbox Workflows](https://docs.labelbox.com/docs/workflows): multi-step review/rework, assignment và task caps.
- [Encord Project Analytics](https://docs.encord.com/platform-documentation/Annotate/annotate-projects/annotate-project-analytics): throughput, review outcome và stage-specific analytics.
- [Encord Consensus Workflows](https://docs.encord.com/platform-documentation/Annotate/annotate-projects/annotate-workflows-consensus): role visibility, reviewer comparison và queue monitoring.
- [V7/Darwin Workflows](https://docs.v7labs.com/docs/use-workflows-to-manage-your-projects): annotate → review → complete và conditional routing.
- [V7 Review Stage](https://docs.v7labs.com/docs/the-review-stage): approve/reject branches và assignment cho reviewer.
- [V7 Assign and Complete Tasks](https://docs.v7labs.com/docs/assign-and-complete-tasks): manual assignment, send-to-review và comment giữa stages.

Điều cần tránh là copy enterprise workflow builder quá sớm. Label Guardian nên giữ workflow cố định, dễ demo và có audit tốt trước; node-based customization chỉ có giá trị khi khách hàng thật sự cần nhiều pipeline khác nhau.
