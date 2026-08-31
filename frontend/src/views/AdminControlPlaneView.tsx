import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Activity, Database, UploadCloud, Users, Workflow } from "lucide-react";
import {
  useAdminBatchesQuery,
  useAdminProjectsQuery,
  useApplicationUsersQuery,
  useInviteApplicationUserMutation,
  useTeamHealthQuery,
  useUpdateApplicationUserStatusMutation,
} from "../api/queries";
import { labelGuardianApiV1 } from "../api/labelGuardianApi";
import { useAuth } from "../auth/AuthProvider";
import { Badge, Button, Card } from "../components/ui";
import "../styles/admin-control-plane.css";

export function AdminControlPlaneView() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const projects = useAdminProjectsQuery(auth.enabled && auth.user?.role === "admin");
  const project = projects.data?.[0];
  const health = useTeamHealthQuery(project?.id, Boolean(project));
  const batches = useAdminBatchesQuery(project?.id, Boolean(project));
  const users = useApplicationUsersQuery(auth.enabled && auth.user?.role === "admin");
  const invite = useInviteApplicationUserMutation();
  const status = useUpdateApplicationUserStatusMutation();
  const [projectForm, setProjectForm] = useState({ name: "Demo customer intake", customerName: "Customer demo" });
  const [inviteForm, setInviteForm] = useState({ email: "", displayName: "", role: "annotator" as "annotator" | "reviewer" | "admin" });
  const [uploadState, setUploadState] = useState("");
  const [intakeForm, setIntakeForm] = useState({ datasetType: "yolo" as "kitti" | "nuscenes" | "yolo", sourceMethod: "upload" as "upload" | "gcs_import", sourcePrefix: "" });
  const [activeTab, setActiveTab] = useState<"operations" | "team" | "intake">("operations");

  const activeUsers = useMemo(() => users.data?.results.filter((user) => !user.disabled) ?? [], [users.data]);
  const handleUpload = async (file: File) => {
    if (!project) {
      setUploadState("Tạo project trước khi upload dữ liệu.");
      return;
    }
    setUploadState("Đang tạo submission…");
    try {
      const submission = await labelGuardianApiV1.createAdminSubmission(project.id, { datasetType: intakeForm.datasetType, sourceMethod: intakeForm.sourceMethod, sourcePrefix: intakeForm.sourcePrefix || undefined, version: `customer-${new Date().toISOString().slice(0, 10)}` });
      const session = await labelGuardianApiV1.createAdminUploadSession(submission.id, { filename: file.name, contentType: file.type || "application/zip", sizeBytes: file.size });
      if (!session.uploadUrl) throw new Error("Backend chưa cấp upload URL GCS. Kiểm tra credential và bucket cấu hình.");
      setUploadState("Đang upload trực tiếp lên bucket…");
      const response = await fetch(session.uploadUrl, { method: "PUT", headers: { "Content-Type": file.type || "application/zip" }, body: file });
      if (!response.ok) throw new Error(`Upload thất bại (HTTP ${response.status}).`);
      await labelGuardianApiV1.completeAdminUpload(submission.id, session.assetId);
      const queued = await labelGuardianApiV1.startAdminSubmission(submission.id);
      setUploadState(`Upload hoàn tất. Run ${queued.runId} đã vào hàng đợi validate/ingest.`);
    } catch (error) {
      setUploadState(error instanceof Error ? error.message : "Upload thất bại.");
    }
  };
  const handleGcsImport = async () => {
    if (!project || !intakeForm.sourcePrefix.trim()) return;
    setUploadState("Đang đăng ký GCS import…");
    try {
      const submission = await labelGuardianApiV1.createAdminSubmission(project.id, { datasetType: intakeForm.datasetType, sourceMethod: "gcs_import", sourcePrefix: intakeForm.sourcePrefix.trim(), version: `customer-${new Date().toISOString().slice(0, 10)}` });
      const queued = await labelGuardianApiV1.startAdminSubmission(submission.id);
      setUploadState(`GCS import đã vào hàng đợi với run ${queued.runId}.`);
    } catch (error) { setUploadState(error instanceof Error ? error.message : "Không thể import GCS object."); }
  };

  if (!auth.enabled || auth.user?.role !== "admin") {
    return <div className="page-container view-page access-denied-page"><Badge tone="high">Admin only</Badge><h1>Không có quyền truy cập</h1><p className="page-description">Control plane chỉ hiển thị cho tài khoản admin đã xác thực.</p></div>;
  }

  return (
    <div className="page-container view-page admin-control-plane">
      <div className="page-heading admin-heading"><div><h1>Admin control plane</h1><p className="page-description">Nhận dữ liệu, phân công công việc và theo dõi sức khỏe team trong một workspace.</p></div><Badge tone="success">Live access</Badge></div>
      <nav className="admin-tabs" aria-label="Admin sections">
        <button className={activeTab === "operations" ? "is-active" : ""} onClick={() => setActiveTab("operations")} type="button"><Workflow size={15} />Operations</button>
        <button className={activeTab === "intake" ? "is-active" : ""} onClick={() => setActiveTab("intake")} type="button"><UploadCloud size={15} />Data intake</button>
        <button className={activeTab === "team" ? "is-active" : ""} onClick={() => setActiveTab("team")} type="button"><Users size={15} />Team</button>
      </nav>
      {activeTab === "intake" && project && intakeForm.sourceMethod === "gcs_import" ? <Button variant="primary" onClick={() => void handleGcsImport()}>Start GCS import</Button> : null}

      {activeTab === "operations" ? <>
        <section className="admin-signal-grid" aria-label="Workflow health">
          <Card><span className="admin-signal-icon"><Activity size={16} /></span><strong>{health.data?.totalTasks ?? 0}</strong><small>Total frame tasks</small></Card>
          <Card><span className="admin-signal-icon"><Database size={16} /></span><strong>{health.data?.byStage?.in_review ?? 0}</strong><small>Awaiting review</small></Card>
          <Card><span className="admin-signal-icon"><Users size={16} /></span><strong>{activeUsers.length}</strong><small>Active members</small></Card>
          <Card><span className="admin-signal-icon"><Workflow size={16} /></span><strong>{batches.data?.length ?? 0}</strong><small>Work batches</small></Card>
        </section>
        <Card className="admin-panel"><div className="admin-panel-heading"><div><h2>Workflow funnel</h2><p>Backlog theo stage, lấy trực tiếp từ frame tasks.</p></div><Badge tone="info">Project scope</Badge></div><div className="workflow-funnel">{Object.entries(health.data?.byStage ?? {}).map(([stage, count]) => <div className="workflow-row" key={stage}><span>{stage.replaceAll("_", " ")}</span><div><i style={{ width: `${Math.min(100, count / Math.max(1, health.data?.totalTasks ?? 1) * 100)}%` }} /></div><strong>{count}</strong></div>)}</div></Card>
      </> : null}

      {activeTab === "intake" ? <Card className="admin-panel intake-panel"><div className="admin-panel-heading"><div><h2>Customer data intake</h2><p>Archive được upload thẳng vào private GCS qua resumable session.</p></div><Badge tone="neutral">KITTI · nuScenes · YOLO</Badge></div>{!project ? <form className="admin-form" onSubmit={async (event) => { event.preventDefault(); try { await labelGuardianApiV1.createAdminProject(projectForm); await queryClient.invalidateQueries({ queryKey: ["api-v1", "control", "projects"] }); setUploadState("Project đã được tạo."); } catch (error) { setUploadState(error instanceof Error ? error.message : "Không thể tạo project."); } }}><label>Project name<input value={projectForm.name} onChange={(event) => setProjectForm({ ...projectForm, name: event.target.value })} /></label><label>Customer<input value={projectForm.customerName} onChange={(event) => setProjectForm({ ...projectForm, customerName: event.target.value })} /></label><Button variant="primary" type="submit">Create project</Button></form> : <><p className="project-context">{project.name} · {project.customerName}</p><div className="intake-options"><label>Format<select value={intakeForm.datasetType} onChange={(event) => setIntakeForm({ ...intakeForm, datasetType: event.target.value as typeof intakeForm.datasetType })}><option value="yolo">YOLO</option><option value="kitti">KITTI</option><option value="nuscenes">nuScenes</option></select></label><label>Source<select value={intakeForm.sourceMethod} onChange={(event) => setIntakeForm({ ...intakeForm, sourceMethod: event.target.value as typeof intakeForm.sourceMethod })}><option value="upload">Browser upload</option><option value="gcs_import">GCS object import</option></select></label></div>{intakeForm.sourceMethod === "gcs_import" ? <input className="gcs-source-input" placeholder="gs://bucket/path/archive.zip" value={intakeForm.sourcePrefix} onChange={(event) => setIntakeForm({ ...intakeForm, sourcePrefix: event.target.value })} /> : <label className="upload-dropzone"><UploadCloud size={22} /><strong>Chọn archive để upload</strong><small>ZIP/TAR · tối đa 2 GB trong demo</small><input type="file" accept=".zip,.tar,.tgz,.gz" onChange={(event) => { const file = event.target.files?.[0]; if (file) void handleUpload(file); }} /></label>}<p className="admin-feedback" role="status">{uploadState}</p></>}</Card> : null}

      {activeTab === "team" ? <div className="admin-team-layout"><Card className="admin-panel"><div className="admin-panel-heading"><div><h2>Members</h2><p>Invite, phân quyền và khóa account ngay lập tức.</p></div><Badge tone="info">{users.data?.count ?? 0} users</Badge></div><form className="admin-form compact" onSubmit={(event) => { event.preventDefault(); if (!inviteForm.email || !inviteForm.displayName) return; invite.mutate(inviteForm, { onSuccess: () => setInviteForm({ email: "", displayName: "", role: "annotator" }) }); }}><input aria-label="Email" placeholder="email@customer.com" value={inviteForm.email} onChange={(event) => setInviteForm({ ...inviteForm, email: event.target.value })} /><input aria-label="Display name" placeholder="Display name" value={inviteForm.displayName} onChange={(event) => setInviteForm({ ...inviteForm, displayName: event.target.value })} /><select aria-label="Role" value={inviteForm.role} onChange={(event) => setInviteForm({ ...inviteForm, role: event.target.value as typeof inviteForm.role })}><option value="annotator">Annotator</option><option value="reviewer">QA Reviewer</option><option value="admin">Admin</option></select><Button variant="primary" type="submit" disabled={invite.isPending}>Invite</Button></form><div className="member-list">{users.data?.results.map((user) => <div className="member-row" key={user.id}><div><strong>{user.displayName}</strong><small>{user.email}</small></div><Badge tone={user.disabled ? "neutral" : user.role === "admin" ? "info" : "success"}>{user.disabled ? "Disabled" : user.role}</Badge><Button variant="ghost" size="sm" disabled={user.id === auth.user?.id || status.isPending} onClick={() => status.mutate({ userId: user.id, disabled: !user.disabled })}>{user.disabled ? "Enable" : "Disable"}</Button></div>)}</div></Card><Card className="admin-panel"><div className="admin-panel-heading"><div><h2>Team health</h2><p>Flow và quality signal, không leaderboard.</p></div></div>{Object.entries(health.data?.annotatorWorkload ?? {}).map(([userId, row]) => <div className="workload-row" key={userId}><div><strong>{userId}</strong><small>{row.wip} WIP · {row.approved} approved · {row.changesRequested} rework</small></div><div className="workload-bar"><i style={{ width: `${Math.min(100, row.wip * 10)}%` }} /></div></div>)}<div className="quality-summary"><span>Approval rate <strong>{health.data?.quality.approvalRate == null ? "Not tracked" : `${Math.round(health.data.quality.approvalRate * 100)}%`}</strong></span><span>Rework rate <strong>{health.data?.quality.reworkRate == null ? "Not tracked" : `${Math.round(health.data.quality.reworkRate * 100)}%`}</strong></span></div></Card></div> : null}
    </div>
  );
}
