import { useSearchParams } from "react-router-dom";
import { isApiDataSourceEnabled } from "../api/labelGuardianApi";
import { useQaCasesQuery, useRealDatasetFrameSamplesQuery } from "../api/queries";
import { Badge, Button, Card, SectionHeading, StatCard } from "../components/ui";
import { ApiDemoNotice } from "../components/ApiDemoNotice";
import { cloudDatasets } from "../config/cloudDataset";
import { useMockData } from "../state/MockDataProvider";

function displayTime(value?: string) {
  return value ? new Date(value).toLocaleString("vi-VN") : "—";
}

export function DatasetRunView() {
  const { state, actions } = useMockData();
  const apiDataSourceEnabled = isApiDataSourceEnabled();
  const [searchParams] = useSearchParams();
  const configuredDataset = cloudDatasets[0];
  const apiDataset = searchParams.get("dataset") || configuredDataset?.id || "nuscenes";
  const apiSplit = searchParams.get("split") || import.meta.env.VITE_DATASET_DEFAULT_SPLIT || "trainval-full";
  const apiCasesQuery = useQaCasesQuery({});
  const apiSamplesQuery = useRealDatasetFrameSamplesQuery(apiSplit, 0, apiDataset);
  const apiCases = apiCasesQuery.data?.results ?? [];
  const apiSamples = apiSamplesQuery.data;

  if (apiDataSourceEnabled) {
    const activeSplit = apiSamples?.split ?? apiSplit;
    const reviewed = apiCases.filter((qaCase) => ["confirmed", "corrected", "rejected"].includes(qaCase.status)).length;
    const highRisk = apiCases.filter((qaCase) => qaCase.riskScore >= 80).length;
    const classCounts = apiCases.reduce<Record<string, number>>((counts, qaCase) => {
      counts[qaCase.className] = (counts[qaCase.className] ?? 0) + 1;
      return counts;
    }, {});
    const sequenceCounts = apiCases.reduce<Record<string, number>>((counts, qaCase) => {
      counts[qaCase.sequenceId] = (counts[qaCase.sequenceId] ?? 0) + 1;
      return counts;
    }, {});

    return (
      <div className="page-container view-page dataset-run-page">
        <div className="page-heading">
          <div>
            <span className="eyebrow">Dataset operations</span>
            <h1>Datasets / Runs</h1>
            <p className="page-description">Theo dõi dataset official từ Supabase metadata và assets cache từ GCS `dataset/official`.</p>
          </div>
          <div className="page-heading-actions">
            <Badge tone={apiSamplesQuery.isError || apiCasesQuery.isError ? "high" : "success"}>{apiSamplesQuery.isPending ? "Đang đọc dataset" : "Dataset API online"}</Badge>
            <Badge tone="info">{apiDataset} · {activeSplit}</Badge>
          </div>
        </div>

        <ApiDemoNotice
          loading={apiSamplesQuery.isPending || apiCasesQuery.isPending}
          hasData={Boolean(apiSamples?.count || apiSamples?.imageCount || apiCases.length)}
          hasError={apiSamplesQuery.isError || apiCasesQuery.isError}
          description="Trang Datasets / Runs mẫu vẫn được giữ để demo trạng thái vận hành. Thông tin split, frame và QA run sẽ xuất hiện khi backend trả dữ liệu."
        />

        <Card className="privacy-safe-card">
          <div className="privacy-safe-icon">✓</div>
          <div><strong>Official cloud dataset</strong><p>Backend ưu tiên full split, tự fallback sang smoke khi full chưa publish; ảnh được stream từ local cache đồng bộ từ GCS.</p></div>
          <Badge tone="success">Read-only demo</Badge>
        </Card>

        <section className="dataset-run-kpi-grid">
          <StatCard label="Requested split" value={apiSplit} detail={`Serving ${activeSplit}`} tone="blue" />
          <StatCard label="Frame samples" value={apiSamples?.count ?? "—"} detail={`${apiSamples?.imageCount ?? 0} camera views`} tone="purple" />
          <StatCard label="Classes" value={apiSamples?.classes.length ?? 0} detail="Trong page metadata hiện tại" tone="orange" />
          <StatCard label="QA cases" value={apiCasesQuery.data?.count ?? apiCases.length} detail={`${highRisk} high-risk · ${reviewed} reviewed`} tone="green" />
        </section>

        <div className="dataset-run-grid">
          <Card className="qa-run-progress-card">
            <div className="qa-run-heading"><SectionHeading eyebrow="Current serving state" title="Full-first smoke fallback" description="Dùng full ngay khi metadata xuất hiện; hiện tại backend đang trả split khả dụng." /><Badge tone={activeSplit === apiSplit ? "success" : "info"}>{activeSplit === apiSplit ? "Full ready" : "Smoke fallback"}</Badge></div>
            <div className="qa-run-progress-value"><strong>{apiCases.length ? Math.round((reviewed / apiCases.length) * 100) : 100}%</strong><span>{reviewed}/{apiCases.length} QA cases reviewed</span></div>
            <div className="progress-track qa-run-track"><div className="progress-fill progress-blue" style={{ width: `${apiCases.length ? Math.round((reviewed / apiCases.length) * 100) : 100}%` }} /></div>
            <div className="qa-run-meta"><span>Dataset <strong>{apiDataset}</strong></span><span>Split <strong>{activeSplit}</strong></span><span>Sequences <strong>{Object.keys(sequenceCounts).length}</strong></span><span>Source <strong>Supabase + GCS cache</strong></span></div>
          </Card>

          <Card className="qa-run-config-card">
            <SectionHeading eyebrow="QA case profile" title="Risk và class đang phát sinh" description="Tóm tắt từ các case thật trong PostgreSQL." />
            <div className="qa-run-config-list"><div><span>High risk</span><strong>{highRisk}</strong></div><div><span>Unreviewed</span><strong>{apiCases.filter((qaCase) => qaCase.status === "unreviewed").length}</strong></div><div><span>Top class</span><strong>{Object.entries(classCounts).sort(([, a], [, b]) => b - a)[0]?.[0] ?? "—"}</strong></div><div><span>Available splits</span><strong>{apiSamples?.availableSplits.join(", ") ?? activeSplit}</strong></div></div>
          </Card>
        </div>

        <Card className="dataset-scene-card">
          <SectionHeading eyebrow="Dataset scope" title="Sequences có QA case" description="Dữ liệu thật đang được backend trả cho màn demo." />
          <div className="dataset-scene-list">{Object.entries(sequenceCounts).sort(([, first], [, second]) => second - first).map(([sequence, count]) => <div className="dataset-scene-row" key={sequence}><div><strong>{sequence}</strong><small>{apiDataset} · {activeSplit}</small></div><span>{count} QA cases</span><span>{apiCases.filter((qaCase) => qaCase.sequenceId === sequence && qaCase.riskScore >= 80).length} high risk</span><Badge tone="success">official</Badge></div>)}</div>
        </Card>
      </div>
    );
  }

  const dataset = state.datasets.find((item) => item.id === state.selectedDatasetId) ?? state.datasets[0];
  const scenes = state.scenes.filter((scene) => scene.datasetId === dataset.id);
  const frames = state.frames.filter((frame) => scenes.some((scene) => scene.id === frame.sceneId));
  const annotations = state.annotations.filter((annotation) => annotation.layer === "original" && frames.some((frame) => frame.id === annotation.frameId));
  const findings = state.findings.filter((finding) => scenes.some((scene) => scene.id === finding.sceneId));
  const run = state.qaRun.datasetId === dataset.id
    ? state.qaRun
    : { ...state.qaRun, datasetId: dataset.id, status: "idle" as const, progress: 0, processedFrames: 0, totalFrames: frames.length };
  const activeModels = state.models.filter((model) => model.enabled);
  const activeRules = state.rules.filter((rule) => rule.enabled);

  return (
    <div className="page-container view-page dataset-run-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Dataset operations</span>
          <h1>Datasets / Runs</h1>
          <p className="page-description">Theo dõi phiên bản dataset, phạm vi frame và tiến trình chạy QA mô phỏng trước khi kết nối backend thật.</p>
        </div>
        <div className="page-heading-actions">
          <Badge tone={dataset.anonymized ? "success" : "high"}>{dataset.anonymized ? "Anonymized dataset" : "Privacy review needed"}</Badge>
          <Badge tone="info">{dataset.version}</Badge>
        </div>
      </div>

      <Card className="privacy-safe-card">
        <div className="privacy-safe-icon">✓</div>
        <div><strong>Safe mock mode</strong><p>QA run chỉ cập nhật progress trong frontend state. Không có model inference thật và không ghi đè ground truth.</p></div>
        <Badge tone="success">No backend write</Badge>
      </Card>

      <section className="dataset-run-kpi-grid">
        <StatCard label="Dataset version" value={dataset.version.split("@").pop() ?? dataset.version} detail={dataset.format} tone="blue" />
        <StatCard label="Scenes" value={scenes.length} detail="Sequence trong version" tone="purple" />
        <StatCard label="Frames" value={frames.length} detail={`${run.processedFrames} đã chạy trong mock run`} tone="orange" />
        <StatCard label="Flagged findings" value={findings.length} detail="Case từ agent mock" tone="green" />
      </section>

      <div className="dataset-run-grid">
        <Card className="qa-run-progress-card">
          <div className="qa-run-heading"><SectionHeading eyebrow="Mock execution" title="QA run progress" description="Tiến trình giả lập theo từng bước 25%; không chạy model thật." /><Badge tone={run.status === "completed" ? "success" : run.status === "running" ? "info" : "neutral"}>{run.status === "completed" ? "Completed" : run.status === "running" ? "Running" : "Ready"}</Badge></div>
          <div className="qa-run-progress-value"><strong>{run.progress}%</strong><span>{run.processedFrames}/{run.totalFrames} frames</span></div>
          <div className="progress-track qa-run-track"><div className="progress-fill progress-blue" style={{ width: `${run.progress}%` }} /></div>
          <div className="qa-run-actions">
            <Button variant="primary" onClick={() => actions.startQaRun(dataset.id)} disabled={run.status === "running"}>{run.status === "completed" ? "Chạy lại mock QA" : "Start mock QA run"}</Button>
            <Button variant="secondary" onClick={actions.advanceQaRun} disabled={run.status !== "running"}>Advance +25%</Button>
          </div>
          <div className="qa-run-meta"><span>Run ID <strong>{run.id}</strong></span><span>Started <strong>{displayTime(run.startedAt)}</strong></span><span>Completed <strong>{displayTime(run.completedAt)}</strong></span><span>Duration <strong>{run.durationSeconds ? `${run.durationSeconds}s` : "—"}</strong></span></div>
        </Card>

        <Card className="qa-run-config-card">
          <SectionHeading eyebrow="Resolved configuration" title="Model và rules đang dùng" description="Snapshot cấu hình mock được gắn vào run khi bắt đầu." />
          <div className="qa-run-config-list"><div><span>Model</span><strong>{activeModels.map((model) => model.version).join(", ") || "No model enabled"}</strong></div><div><span>Rules</span><strong>{activeRules.length} enabled</strong></div><div><span>Rule snapshot</span><strong>{run.ruleVersion}</strong></div><div><span>Privacy</span><strong>{dataset.anonymized ? "Anonymized" : "Review required"}</strong></div></div>
        </Card>
      </div>

      <Card className="dataset-scene-card">
        <SectionHeading eyebrow="Dataset scope" title="Scenes trong version đang chọn" description="Thông tin read-only lấy từ mock dataset manifest." />
        <div className="dataset-scene-list">{scenes.map((scene) => { const sceneFrames = frames.filter((frame) => frame.sceneId === scene.id); const sceneAnnotations = annotations.filter((annotation) => sceneFrames.some((frame) => frame.id === annotation.frameId)); return <div className="dataset-scene-row" key={scene.id}><div><strong>{scene.name}</strong><small>{scene.location} · {scene.weather}</small></div><span>{sceneFrames.length} frames</span><span>{sceneAnnotations.length} annotations</span><Badge tone="success">{scene.annotatorId}</Badge></div>; })}</div>
      </Card>
    </div>
  );
}
