import {
  ArrowRight,
  Bot,
  Check,
  ChevronDown,
  Cloud,
  Code2,
  Database,
  FileCheck2,
  GitBranch,
  GitCommitHorizontal,
  GitCompareArrows,
  History,
  LayoutGrid,
  Layers3,
  MousePointer2,
  Network,
  PencilRuler,
  Radar,
  ScanSearch,
  ShieldCheck,
  type LucideIcon,
  UserCheck,
} from "lucide-react";
import { useEffect, useState } from "react";

const issueTypes = ["Wrong class", "Loose bbox", "Missing label", "Duplicate label"];

const workflowSteps = [
  { icon: ScanSearch, label: "Triage", meta: "Risk ranked" },
  { icon: GitCompareArrows, label: "Compare", meta: "Label vs model" },
  { icon: PencilRuler, label: "Correct", meta: "Edit geometry" },
  { icon: GitCommitHorizontal, label: "Commit", meta: "New revision" },
];

interface LandingSection {
  id: string;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
}

const landingSections: LandingSection[] = [
  { id: "overview", label: "Overview", shortLabel: "Start", icon: LayoutGrid },
  { id: "signals", label: "Risk signals", shortLabel: "Signals", icon: Radar },
  { id: "pipeline", label: "QA pipeline", shortLabel: "Pipeline", icon: GitBranch },
  { id: "review", label: "Review workflow", shortLabel: "Review", icon: UserCheck },
  { id: "architecture", label: "Architecture", shortLabel: "System", icon: Network },
];

function LandingNavigation() {
  const [activeSection, setActiveSection] = useState(landingSections[0].id);
  const activeIndex = Math.max(0, landingSections.findIndex((section) => section.id === activeSection));
  const active = landingSections[activeIndex];
  const next = landingSections[(activeIndex + 1) % landingSections.length];
  const condensed = activeIndex > 0;

  useEffect(() => {
    const targets = landingSections
      .map((section) => document.getElementById(section.id))
      .filter((target): target is HTMLElement => Boolean(target));

    if (targets.length === 0 || typeof IntersectionObserver === "undefined") {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntry = entries
          .filter((entry) => entry.isIntersecting)
          .sort((first, second) => second.intersectionRatio - first.intersectionRatio)[0];

        if (visibleEntry) {
          setActiveSection(visibleEntry.target.id);
        }
      },
      {
        rootMargin: "-18% 0px -66% 0px",
        threshold: [0, 0.15, 0.35, 0.6],
      },
    );

    targets.forEach((target) => observer.observe(target));
    const requestedSection = window.location.hash.slice(1);
    const hashTarget = targets.find((target) => target.id === requestedSection);
    let restoreScrollTimer = 0;
    const hashTimer = window.setTimeout(() => {
      if (hashTarget) {
        const root = document.documentElement;
        const previousScrollBehavior = root.style.scrollBehavior;
        root.style.scrollBehavior = "auto";
        const targetTop = hashTarget.getBoundingClientRect().top + window.scrollY - 68;
        const maximumTop = Math.max(0, root.scrollHeight - window.innerHeight);
        window.scrollTo(0, Math.min(Math.max(0, targetTop), maximumTop));
        setActiveSection(hashTarget.id);
        restoreScrollTimer = window.setTimeout(() => {
          root.style.scrollBehavior = previousScrollBehavior;
        }, 0);
      }
    }, 120);

    return () => {
      window.clearTimeout(hashTimer);
      window.clearTimeout(restoreScrollTimer);
      observer.disconnect();
    };
  }, []);

  return (
    <>
      <header
        className={`landing-header${condensed ? " is-condensed" : ""}`}
        data-section-index={activeIndex}
      >
        <a className="landing-skip-link" href="#overview">Skip to content</a>
        <nav className="landing-nav" aria-label="Landing navigation">
          <a className="landing-brand" href="#overview">
            <span className="landing-brand-mark">LG</span>
            <span>Label Guardian</span>
          </a>

          <div className="landing-nav-center">
            <span className="landing-nav-current">{active.label}</span>
            <div className="landing-nav-links">
              {landingSections.slice(1).map((section) => (
                <a
                  key={section.id}
                  href={`#${section.id}`}
                  aria-current={activeSection === section.id ? "location" : undefined}
                >
                  {section.shortLabel}
                </a>
              ))}
            </div>
          </div>

          <div className="landing-nav-actions">
            <a
              className="landing-nav-next"
              href={`#${next.id}`}
              aria-label={`Go to ${next.label}`}
              title={`Next: ${next.label}`}
            >
              <ChevronDown size={17} aria-hidden="true" />
            </a>
            <a className="landing-nav-action" href="/overview">
              Open workspace
              <ArrowRight size={16} aria-hidden="true" />
            </a>
          </div>
        </nav>
        <span className="landing-nav-progress" aria-hidden="true" />
      </header>

      <aside
        className={`landing-section-dock${condensed ? " is-visible" : ""}`}
        aria-label="Jump to landing section"
        aria-hidden={!condensed}
      >
        <span className="landing-dock-current">{active.label}</span>
        <nav>
          {landingSections.map((section) => {
            const Icon = section.icon;
            const current = activeSection === section.id;
            return (
              <a
                key={section.id}
                href={`#${section.id}`}
                aria-label={`Go to ${section.label}`}
                aria-current={current ? "location" : undefined}
                title={section.label}
                tabIndex={condensed ? 0 : -1}
              >
                <Icon size={16} aria-hidden="true" />
                <span>{section.shortLabel}</span>
              </a>
            );
          })}
        </nav>
      </aside>
    </>
  );
}

export function LandingPage() {
  return (
    <main className="landing-page">
      <LandingNavigation />

      <section className="landing-hero" id="overview">
        <div className="landing-hero-copy">
          <p className="landing-kicker">Perception Data QA</p>
          <h1>Catch label errors before training.</h1>
          <p>Evidence-led review for autonomous-driving datasets.</p>
          <div className="landing-hero-actions">
            <a className="landing-primary-action" href="/overview">
              Open workspace
              <ArrowRight size={18} aria-hidden="true" />
            </a>
            <a className="landing-secondary-action" href="#pipeline">
              See pipeline
            </a>
          </div>
        </div>
        <figure className="landing-hero-visual">
          <img
            src="/label-guardian-hero.png"
            alt="Perception dataset review workstation with bounding boxes and risk evidence"
          />
        </figure>
      </section>

      <section className="landing-proof" aria-label="Product principles">
        <article className="landing-proof-item">
          <div className="proof-human" aria-hidden="true">
            <span><Bot size={17} /></span>
            <i />
            <span className="is-active"><UserCheck size={17} /></span>
            <i />
            <span><Check size={17} /></span>
          </div>
          <div>
            <strong>Human decides</strong>
            <small>Every flagged case ends with a reviewer.</small>
          </div>
        </article>
        <article className="landing-proof-item">
          <div className="proof-rules" aria-hidden="true">
            <Code2 size={18} />
            <span>IoU &lt; 0.50</span>
            <ArrowRight size={14} />
            <b>HIGH</b>
          </div>
          <div>
            <strong>Rules set severity</strong>
            <small>Models explain evidence. Code controls outcomes.</small>
          </div>
        </article>
        <article className="landing-proof-item">
          <div className="proof-cloud" aria-hidden="true">
            <Cloud size={18} />
            <span className="proof-packet" />
            <Database size={18} />
          </div>
          <div>
            <strong>Cloud-native data</strong>
            <small>Frames and metadata stay in their source systems.</small>
          </div>
        </article>
      </section>

      <section className="landing-problem" id="signals">
        <div className="landing-section-copy">
          <h2>See the failure, not another list.</h2>
          <p>Label Guardian turns scattered annotation defects into spatial evidence reviewers can inspect.</p>
          <div className="landing-issue-legend" aria-label="Detected issue types">
            {issueTypes.map((issue, index) => (
              <span key={issue}><i>{index + 1}</i>{issue}</span>
            ))}
          </div>
        </div>
        <figure className="landing-inspection-frame">
          <img src="/label-guardian-hero.png" alt="Road frames with annotation issues highlighted for inspection" />
          <span className="issue-box issue-box-one"><i>1</i></span>
          <span className="issue-box issue-box-two"><i>2</i></span>
          <span className="issue-box issue-box-three"><i>3</i></span>
          <span className="issue-box issue-box-four"><i>4</i></span>
          <figcaption>
            <span>scene_000142</span>
            <strong>4 signals found</strong>
          </figcaption>
        </figure>
      </section>

      <section className="landing-pipeline" id="pipeline">
        <div className="landing-section-copy landing-section-copy-compact">
          <h2>A QA pipeline you can follow.</h2>
          <p>Each case moves from raw annotation to review-ready evidence through deterministic stages.</p>
        </div>
        <div className="landing-pipeline-canvas" aria-label="Annotation QA pipeline">
          <article className="pipeline-source">
            <div className="pipeline-frame-stack" aria-hidden="true">
              <img src="/label-guardian-hero.png" alt="" />
              <span />
              <span />
            </div>
            <div><small>Input</small><strong>Annotation</strong></div>
          </article>
          <div className="pipeline-link" aria-hidden="true"><span /></div>
          <article className="pipeline-engine">
            <span className="pipeline-engine-icon"><Bot size={22} /></span>
            <div className="pipeline-engine-rings" aria-hidden="true"><i /><i /><i /></div>
            <div><small>Evidence engine</small><strong>Match + score</strong></div>
          </article>
          <div className="pipeline-link" aria-hidden="true"><span /></div>
          <article className="pipeline-output">
            <div className="pipeline-case-list" aria-hidden="true">
              <span><i /> Wrong class <b>H</b></span>
              <span><i /> Loose bbox <b>M</b></span>
              <span><i /> Missing label <b>H</b></span>
            </div>
            <div><small>Output</small><strong>Ranked QA cases</strong></div>
          </article>
        </div>
      </section>

      <section className="landing-review" id="review">
        <div className="landing-review-heading">
          <h2>One fluid path from signal to revision.</h2>
          <a className="landing-text-link" href="/qa-queue">
            Open QA Queue
            <ArrowRight size={16} aria-hidden="true" />
          </a>
        </div>
        <div className="landing-workflow">
          <ol className="workflow-steps">
            {workflowSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <li key={step.label} className={index === 1 ? "is-current" : ""}>
                  <span><Icon size={19} aria-hidden="true" /></span>
                  <div><strong>{step.label}</strong><small>{step.meta}</small></div>
                </li>
              );
            })}
          </ol>
          <div className="workflow-stage">
            <figure>
              <img src="/label-guardian-hero.png" alt="Frame under human review with model and annotation overlays" />
              <span className="workflow-bbox workflow-bbox-label" />
              <span className="workflow-bbox workflow-bbox-model" />
            </figure>
            <div className="workflow-decision">
              <div>
                <GitCompareArrows size={18} aria-hidden="true" />
                <span><small>Evidence</small><strong>Class mismatch</strong></span>
              </div>
              <div className="workflow-actions" aria-label="Review decisions">
                <span><Check size={15} />Accept</span>
                <span className="is-selected"><PencilRuler size={15} />Edit</span>
                <span><History size={15} />Restore</span>
              </div>
              <div className="workflow-revision">
                <GitCommitHorizontal size={17} />
                <span>revision_03</span>
                <b>saved</b>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-architecture" id="architecture">
        <div className="landing-section-copy landing-section-copy-compact">
          <h2>Data moves. Ownership stays clear.</h2>
          <p>A live path from private storage to reviewer decision, with every correction returning as a traceable revision.</p>
        </div>
        <div className="architecture-flow" aria-label="System architecture data flow">
          <div className="architecture-source architecture-gcs">
            <Cloud size={23} aria-hidden="true" />
            <span><small>Objects</small><strong>GCS frames</strong></span>
          </div>
          <div className="architecture-source architecture-db">
            <Database size={23} aria-hidden="true" />
            <span><small>State</small><strong>Supabase</strong></span>
          </div>
          <div className="architecture-beam architecture-beam-a" aria-hidden="true"><i /></div>
          <div className="architecture-beam architecture-beam-b" aria-hidden="true"><i /></div>
          <div className="architecture-core">
            <span className="architecture-core-icon"><ShieldCheck size={26} /></span>
            <small>Private API boundary</small>
            <strong>FastAPI + QA agent</strong>
            <div><Code2 size={14} /> deterministic rules</div>
          </div>
          <div className="architecture-beam architecture-beam-c" aria-hidden="true"><i /></div>
          <div className="architecture-reviewer">
            <Layers3 size={23} aria-hidden="true" />
            <span><small>Workspace</small><strong>React reviewer</strong></span>
          </div>
          <div className="architecture-return" aria-hidden="true"><span /></div>
          <div className="architecture-audit">
            <FileCheck2 size={19} aria-hidden="true" />
            <span><strong>Revision + audit event</strong><small>actor, note, status, timestamp</small></span>
          </div>
        </div>
      </section>

      <section className="landing-guardrails" aria-label="Product guardrails">
        <span><ShieldCheck size={18} />Human approval</span>
        <span><Code2 size={18} />Deterministic severity</span>
        <span><History size={18} />Immutable revisions</span>
        <span><Database size={18} />Traceable provenance</span>
      </section>

      <section className="landing-final">
        <div>
          <MousePointer2 size={24} aria-hidden="true" />
          <h2>Review the frames that matter first.</h2>
        </div>
        <a className="landing-primary-action" href="/overview">
          Enter workspace
          <ArrowRight size={18} aria-hidden="true" />
        </a>
      </section>
    </main>
  );
}
