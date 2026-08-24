import { useMemo } from "react";
import { Activity, AlertTriangle, CheckCircle2, Database, ShieldAlert } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { isApiDataSourceEnabled } from "../api/labelGuardianApi";
import { useQaCasesQuery, useRealDatasetFrameSamplesQuery } from "../api/queries";
import { Badge, Button, Card, SectionHeading, StatusBadge } from "../components/ui";
import { cloudDatasets } from "../config/cloudDataset";
import type { FindingType, MockState, Severity } from "../domain/types";

const findingTypeLabels: Record<FindingType, string> = {
  box_misalignment: "Box misalignment",
  wrong_class: "Wrong class",
  missing_object: "Missing object",
  duplicate_annotation: "Duplicate annotation",
  track_id_switch: "Track ID switch",
  track_break: "Track break",
  temporal_inconsistency: "Temporal inconsistency",
};

const severityLabels: Record<Severity, string> = {
  low: "Low", medium: "Warning", high: "High", critical: "Critical",
};

export function OverviewView({
  state,
  onOpenQueue,
  onOpenFinding,
}: {
  state: MockState;
  onOpenQueue: () => void;
  onOpenFinding?: (findingId: string) => void;
}) {
  const apiDataSourceEnabled = isApiDataSourceEnabled();
  const [searchParams] = useSearchParams();
  const configuredDataset = cloudDatasets[0];
  const apiDataset = searchParams.get("dataset") || configuredDataset?.id || "nuscenes";
  const apiSplit = searchParams.get("split") || import.meta.env.VITE_DATASET_DEFAULT_SPLIT || "trainval-full";
  const apiCasesQuery = useQaCasesQuery({});
  const apiSamplesQuery = useRealDatasetFrameSamplesQuery(apiSplit, 0, apiDataset);
  const apiCases = apiCasesQuery.data?.results ?? [];
  const apiSamples = apiSamplesQuery.data;

  const apiStatusCounts = useMemo(() => apiCases.reduce<Record<string, number>>((counts, qaCase) => {
    counts[qaCase.status] = (counts[qaCase.status] ?? 0) + 1;
    return counts;
  }, {}), [apiCases]);
  const apiTypeCounts = useMemo(() => apiCases.reduce<Record<string, number>>((counts, qaCase) => {
    counts[qaCase.errorType] = (counts[qaCase.errorType] ?? 0) + 1;
    return counts;
  }, {}), [apiCases]);

  if (apiDataSourceEnabled) {
    const reviewed = apiCases.filter((qaCase) => ["confirmed", "corrected", "rejected"].includes(qaCase.status)).length;
    const highRisk = apiCases.filter((qaCase) => qaCase.riskScore >= 80).length;
    const mediumRisk = apiCases.filter((qaCase) => qaCase.riskScore >= 50 && qaCase.riskScore < 80).length;
    const progress = apiCases.length ? Math.round((reviewed / apiCases.length) * 100) : 100;
    const qaScore = Math.max(0, 100 - Math.round((highRisk / Math.max(apiCases.length, 1)) * 100));
    const maxType = Math.max(...Object.values(apiTypeCounts), 1);
    const recentCases = [...apiCases].sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt)).slice(0, 6);
    const priorityCases = [...apiCases].filter((qaCase) => !["confirmed", "corrected", "rejected"].includes(qaCase.status)).sort((a, b) => b.riskScore - a.riskScore).slice(0, 5);
    const activeSplit = apiSamples?.split ?? apiSplit;
    const loading = apiCasesQuery.isPending || apiSamplesQuery.isPending;

    return (
      <div className="page-container view-page qa-control-center">
        <div className="page-heading">
          <div><span className="eyebrow">QA Control Center</span><h1>Tổng quan QA dataset thật</h1><p className="page-description">Theo dõi metadata Supabase, ảnh từ dataset/official và QA cases được Agent persist.</p></div>
          <div className="page-heading-actions"><Badge tone={apiCasesQuery.isError || apiSamplesQuery.isError ? "high" : "success"}>{loading ? "Đang tải API" : "API dataset online"}</Badge><Button variant="primary" onClick={onOpenQueue}>Mở QA Queue</Button></div>
        </div>

        <section className="qa-dataset-bar">
          <div className="qa-dataset-identity"><span><Database size={17} /></span><div><small>Active dataset</small><strong>{apiDataset === "nuscenes" ? "nuScenes official" : "KITTI official"}</strong></div></div>
          <div><small>Requested split</small><strong>{apiSplit}</strong></div>
          <div><small>Serving split</small><strong>{activeSplit}</strong></div>
          <div><small>Frame samples</small><strong>{apiSamples?.count ?? "—"}</strong></div>
          <div><small>Camera views</small><strong>{apiSamples?.imageCount ?? "—"}</strong></div>
        </section>

        <section className="qa-metric-strip" aria-label="Quality metrics">
          <div><span className="metric-icon is-neutral"><Database size={15} /></span><span>Classes<small>Visible metadata</small></span><strong>{apiSamples?.classes.length ?? 0}</strong></div>
          <div><span className="metric-icon is-success"><CheckCircle2 size={15} /></span><span>Reviewed<small>Confirmed/corrected/rejected</small></span><strong>{reviewed}</strong></div>
          <div><span className="metric-icon is-warning"><AlertTriangle size={15} /></span><span>Medium risk<small>Risk 50-79</small></span><strong>{mediumRisk}</strong></div>
          <div><span className="metric-icon is-critical"><ShieldAlert size={15} /></span><span>High-risk cases<small>Risk 80+</small></span><strong>{highRisk}</strong></div>
          <div className="qa-score-metric"><span>QA score<small>Risk-weighted demo score</small></span><strong>{qaScore}<i>/100</i></strong></div>
        </section>

        <div className="qa-overview-grid">
          <Card className="qa-run-card">
            <div className="qa-card-header"><SectionHeading eyebrow="Review queue" title="Tiến độ xử lý" description={`${reviewed} / ${apiCases.length} QA cases đã có quyết định.`} /><Activity size={18} /></div>
            <div className="qa-run-progress"><div><strong>{progress}%</strong><span>{apiSamples?.count ?? 0} frame samples · {apiSamples?.imageCount ?? 0} camera views</span></div><div className="progress-track"><div className="progress-fill progress-purple" style={{ width: `${progress}%` }} /></div></div>
            <div className="qa-run-status-grid"><div><span>Unreviewed</span><strong>{apiStatusCounts.unreviewed ?? 0}</strong></div><div><span>In review</span><strong>{apiStatusCounts.in_review ?? 0}</strong></div><div><span>Resolved</span><strong>{reviewed}</strong></div></div>
          </Card>

          <Card className="qa-issue-card">
            <SectionHeading eyebrow="Issue distribution" title="Phân bố lỗi thật" description="Tính từ QA cases đang lưu trong Supabase." />
            <div className="qa-issue-list">{Object.entries(apiTypeCounts).sort(([, a], [, b]) => b - a).map(([type, count]) => <div key={type}><span>{findingTypeLabels[type as FindingType] ?? type}</span><div className="progress-track"><div className="progress-fill progress-purple" style={{ width: `${(count / maxType) * 100}%` }} /></div><strong>{count}</strong></div>)}</div>
          </Card>

          <Card className="qa-recent-card">
            <div className="qa-card-header"><SectionHeading eyebrow="Recent cases" title="Tín hiệu mới nhất" /><Button variant="ghost" size="sm" onClick={onOpenQueue}>Xem queue</Button></div>
            <div className="qa-findings-table"><div className="qa-findings-head"><span>Case</span><span>Type</span><span>Priority</span><span>Status</span><span>Risk</span></div>{recentCases.map((qaCase) => <button key={qaCase.id} type="button" onClick={() => onOpenQueue()}><span><strong>{qaCase.id}</strong><small>{qaCase.sequenceId} · {qaCase.sourceSplit}</small></span><span>{findingTypeLabels[qaCase.errorType as FindingType] ?? qaCase.errorType}</span><Badge tone={qaCase.priority}>{qaCase.priority}</Badge><StatusBadge status={qaCase.status} /><strong>{qaCase.riskScore}</strong></button>)}</div>
          </Card>

          <Card className="qa-review-card">
            <div className="qa-card-header"><SectionHeading eyebrow="Needs review" title="Case ưu tiên" /><Badge tone={highRisk ? "high" : "success"}>{highRisk} high risk</Badge></div>
            <div className="qa-priority-list">{priorityCases.map((qaCase) => <button key={qaCase.id} type="button" onClick={() => onOpenQueue()}><span className={`severity-rail severity-${qaCase.priority}`} /><span><strong>{qaCase.className}</strong><small>{findingTypeLabels[qaCase.errorType as FindingType] ?? qaCase.errorType} · {qaCase.sequenceId}</small></span><span>{qaCase.riskScore}</span></button>)}</div>
          </Card>
        </div>
      </div>
    );
  }

  const dataset = state.datasets.find((item) => item.id === state.selectedDatasetId);
  const sceneIds = new Set(state.scenes.filter((scene) => scene.datasetId === state.selectedDatasetId).map((scene) => scene.id));
  const findings = state.findings.filter((finding) => sceneIds.has(finding.sceneId));
  const statusCounts = useMemo(() => findings.reduce<Record<string, number>>((counts, finding) => {
    counts[finding.status] = (counts[finding.status] ?? 0) + 1;
    return counts;
  }, {}), [findings]);
  const typeCounts = useMemo(() => findings.reduce<Record<string, number>>((counts, finding) => {
    counts[finding.type] = (counts[finding.type] ?? 0) + 1;
    return counts;
  }, {}), [findings]);
  const severityCounts = useMemo(() => findings.reduce<Record<string, number>>((counts, finding) => {
    counts[finding.severity] = (counts[finding.severity] ?? 0) + 1;
    return counts;
  }, {}), [findings]);
  const reviewed = findings.filter((finding) => ["confirmed", "corrected", "rejected"].includes(finding.status)).length;
  const warnings = (severityCounts.medium ?? 0) + (severityCounts.low ?? 0);
  const critical = (severityCounts.critical ?? 0) + (severityCounts.high ?? 0);
  const passed = Math.max(0, (dataset?.annotationCount ?? 0) - findings.length);
  const qaScore = Math.round((1 - state.reportMetrics.afterQaErrorRate) * 100);
  const progress = findings.length ? Math.round((reviewed / findings.length) * 100) : 100;
  const maxType = Math.max(...Object.values(typeCounts), 1);
  const recentFindings = [...findings].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).slice(0, 6);
  const reviewCases = [...findings].filter((finding) => !["confirmed", "corrected", "rejected"].includes(finding.status)).sort((a, b) => a.priority - b.priority).slice(0, 5);

  return (
    <div className="page-container view-page qa-control-center">
      <div className="page-heading">
        <div><span className="eyebrow">QA Control Center</span><h1>Annotation quality overview</h1><p className="page-description">Monitor model-assisted checks, prioritize findings, and track human review for the active 2D dataset.</p></div>
        <div className="page-heading-actions"><Badge tone={state.qaRun.status === "running" ? "info" : "success"}>{state.qaRun.status === "running" ? `QA running · ${state.qaRun.progress}%` : "QA system healthy"}</Badge><Button variant="primary" onClick={onOpenQueue}>Open review queue</Button></div>
      </div>

      <section className="qa-dataset-bar">
        <div className="qa-dataset-identity"><span><Database size={17} /></span><div><small>Active dataset</small><strong>{dataset?.name}</strong></div></div>
        <div><small>Version</small><strong>{dataset?.version.replace("dvc://", "")}</strong></div>
        <div><small>Format</small><strong>{dataset?.format} · 2D</strong></div>
        <div><small>Frames</small><strong>{dataset?.frameCount}</strong></div>
        <div><small>Last QA run</small><strong>{state.qaRun.id}</strong></div>
      </section>

      <section className="qa-metric-strip" aria-label="Quality metrics">
        <div><span className="metric-icon is-neutral"><Database size={15} /></span><span>Total annotations<small>Dataset scope</small></span><strong>{dataset?.annotationCount ?? 0}</strong></div>
        <div><span className="metric-icon is-success"><CheckCircle2 size={15} /></span><span>Passed<small>No active finding</small></span><strong>{passed}</strong></div>
        <div><span className="metric-icon is-warning"><AlertTriangle size={15} /></span><span>Warnings<small>Medium / low</small></span><strong>{warnings}</strong></div>
        <div><span className="metric-icon is-critical"><ShieldAlert size={15} /></span><span>Critical issues<small>High / critical</small></span><strong>{critical}</strong></div>
        <div className="qa-score-metric"><span>QA score<small>Post-review quality</small></span><strong>{qaScore}<i>/100</i></strong></div>
      </section>

      <div className="qa-overview-grid">
        <Card className="qa-run-card">
          <div className="qa-card-header"><SectionHeading eyebrow="Current QA run" title="Review progress" description={`${reviewed} of ${findings.length} findings have a human decision.`} /><Activity size={18} /></div>
          <div className="qa-run-progress"><div><strong>{progress}%</strong><span>{state.qaRun.processedFrames}/{state.qaRun.totalFrames} frames processed</span></div><div className="progress-track"><div className="progress-fill progress-purple" style={{ width: `${progress}%` }} /></div></div>
          <div className="qa-run-status-grid"><div><span>Unreviewed</span><strong>{statusCounts.unreviewed ?? 0}</strong></div><div><span>In review</span><strong>{statusCounts.in_review ?? 0}</strong></div><div><span>Resolved</span><strong>{reviewed}</strong></div></div>
        </Card>

        <Card className="qa-issue-card">
          <SectionHeading eyebrow="Issue distribution" title="Findings by type" description="Rule and model signals across the active dataset." />
          <div className="qa-issue-list">{Object.entries(typeCounts).sort(([, a], [, b]) => b - a).map(([type, count]) => <div key={type}><span>{findingTypeLabels[type as FindingType]}</span><div className="progress-track"><div className="progress-fill progress-purple" style={{ width: `${(count / maxType) * 100}%` }} /></div><strong>{count}</strong></div>)}</div>
        </Card>

        <Card className="qa-recent-card">
          <div className="qa-card-header"><SectionHeading eyebrow="Recent findings" title="Latest QA signals" /><Button variant="ghost" size="sm" onClick={onOpenQueue}>View all</Button></div>
          <div className="qa-findings-table"><div className="qa-findings-head"><span>Finding</span><span>Type</span><span>Severity</span><span>Status</span><span>Risk</span></div>{recentFindings.map((finding) => <button key={finding.id} type="button" onClick={() => onOpenFinding?.(finding.id)}><span><strong>{finding.id}</strong><small>{finding.trackId ?? "No track"}</small></span><span>{findingTypeLabels[finding.type]}</span><Badge tone={finding.severity}>{severityLabels[finding.severity]}</Badge><StatusBadge status={finding.status} /><strong>{Math.round(finding.riskScore * 100)}</strong></button>)}</div>
        </Card>

        <Card className="qa-review-card">
          <div className="qa-card-header"><SectionHeading eyebrow="Needs review" title="Priority cases" /><Badge tone={critical ? "high" : "success"}>{critical} high risk</Badge></div>
          <div className="qa-priority-list">{reviewCases.map((finding) => <button key={finding.id} type="button" onClick={() => onOpenFinding?.(finding.id)}><span className={`severity-rail severity-${finding.severity}`} /><span><strong>{finding.title}</strong><small>{findingTypeLabels[finding.type]} · Risk {finding.riskScore.toFixed(2)}</small></span><span>P{finding.priority}</span></button>)}</div>
        </Card>
      </div>
    </div>
  );
}
