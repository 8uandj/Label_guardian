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
