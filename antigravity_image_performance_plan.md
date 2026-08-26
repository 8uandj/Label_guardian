

# Antigravity Implementation Plan — Image Loading & Frame Navigation Performance
# Agent Environment Setup — REQUIRED

Before modifying the project, inspect the current environment and install the following tools if they are not already available:

Required:
1. Serena
2. Context7
3. Repomix

Optional:
4. ast-grep

Do NOT install Promptfoo, Grafana MCP, Semgrep, or other infrastructure tools unless they are needed for the current task.

Rules:
- Check whether each tool is already installed before installing.
- Use project-local installation when possible.
- Do not overwrite existing configuration without inspecting it first.
- After installation, verify that each tool works.
- If installation requires elevated sudo/root permissions, IAM changes, credentials, or destructive configuration changes, stop that installation and report the required action instead.
- Continue the implementation using available tools if an optional tool cannot be installed.

Before implementation:

- [ ] Check Serena
- [ ] Install/configure Serena if missing
- [ ] Check Context7
- [ ] Install/configure Context7 if missing
- [ ] Check Repomix
- [ ] Install Repomix if missing
- [ ] Verify all installed tools
- [ ] Inspect repository
- [ ] Start P0

## 0. Mission

Optimize image loading and frame navigation performance for the current production architecture without introducing unnecessary infrastructure changes.

### Current architecture

```text
Frontend: Vercel
    |
    v
Backend: GCP VM / containerized FastAPI service
    |
    +--> Supabase
    |
    +--> Private GCS bucket
```

The backend currently remains in the image data plane because direct GCS signed delivery is not enabled under the current IAM/service-account configuration.

### Baseline

Endpoint:

```text
/api/v1/dataset/images/{split}/{image_id}/content
```

Current benchmark:

```text
p50 = 2740.01 ms
p95 = 3408.57 ms
p99 = 3793.00 ms
```

### Primary goals

```text
Uncached GCS request p95      < 700 ms
Uncached stretch target       < 300 ms
Local disk cache hit p95      < 20 ms
Cached frame navigation UX    < 50 ms perceived latency
48 thumbnails total payload   < 1–2 MB
```

Do not claim a performance improvement without before/after measurements.

---

# 1. Execution Rules for the Agent

The agent MUST follow these rules during implementation.

## 1.1 Measure before optimizing

Before each optimization:

1. Record baseline.
2. Make one logical change.
3. Run tests.
4. Run benchmark.
5. Compare before/after.
6. Keep the change only if it improves performance without breaking correctness.

Do not combine many unrelated optimizations before measuring.

## 1.2 Avoid architectural over-engineering

Do NOT introduce the following unless measurements prove they are necessary:

```text
Redis
Kafka / Redpanda
Kubernetes
new database
new CDN provider
distributed cache
message queue
```

Use the existing:

```text
GCP VM
FastAPI
Supabase
GCS
Vercel
```

## 1.3 Preserve API compatibility

Existing callers must continue to work.

The existing endpoint:

```text
/images/{split}/{image_id}/content
```

must preserve its default behavior.

New functionality may be added through an optional query parameter:

```text
?size=thumbnail
```

## 1.4 Do not optimize by guessing

Every performance statement must be backed by at least one of:

```text
benchmark
trace
profiling result
payload measurement
browser DevTools evidence
```

---

# 2. Delivery Strategy

Implement in phases.

```text
P0 -> benchmark
   -> backend request-path optimization
   -> browser caching

P1 -> thumbnails
   -> lazy loading
   -> fetch priority
   -> prev/next prefetch

BENCHMARK CHECKPOINT

If targets are already satisfied:
    STOP.

If performance is still insufficient:
    P2 -> bounded local disk cache

Future:
    direct GCS delivery using signed URLs / CDN
```

Do not implement P2 before benchmarking P0 + P1 unless an existing requirement explicitly demands local caching.

---

# 3. Phase P0 — Measurement & Backend Hot Path

## 3.1 Benchmark instrumentation

Update:

```text
scratch/benchmark_images.py
```

Create separate benchmarks.

### A. Cold GCS fetch

Test at least 100 distinct images.

Purpose:

```text
measure real remote object-fetch latency
avoid local disk cache
avoid browser cache
```

Record:

```text
count
success rate
p50
p95
p99
min
max
mean
payload size
```

### B. Warm GCS connection benchmark

Fetch at least 100 requests sequentially using the same backend process.

Purpose:

```text
measure effect of GCS client reuse
measure persistent TCP/TLS connection behavior
```

### C. Concurrent image benchmark

Test representative concurrency.

Minimum scenarios:

```text
1 user   -> 48 thumbnail-like requests
5 users  -> 240 requests
10 users -> 480 requests
```

If safe in the development environment, also test:

```text
25 users -> 1200 requests
```

Measure:

```text
p50
p95
p99
throughput
error rate
CPU
memory
GCS request count if observable
```

Do not overload production to run this benchmark.

---

# 4. Phase P0 — Reuse GCS Client

Primary backend file:

```text
src/api/real_dataset.py
```

## Current anti-pattern to eliminate

Do not create a new:

```python
storage.Client()
```

for every image request.

## Required implementation

Create one client per application process.

Conceptual pattern:

```python
_gcs_client = storage.Client()
```

All request handlers should reuse it.

Important:

```text
"global singleton" means singleton per process.
```

If the server runs multiple workers:

```text
worker 1 -> client 1
worker 2 -> client 2
worker 3 -> client 3
worker 4 -> client 4
```

This is acceptable.

## Acceptance criteria

After the change:

```text
No storage.Client() construction inside the hot image request path.
Existing image endpoint behavior remains correct.
Unit tests pass.
Warm benchmark is measurably better or no worse.
```

---

# 5. Phase P0 — Remove Redundant GCS Metadata Roundtrips

Inspect:

```text
_gcs_blob
_stream_gcs_image
get_real_dataset_image_content
```

Remove request-path patterns equivalent to:

```python
blob.exists()
blob.reload()
blob.download_as_bytes()
```

when the endpoint only needs the object contents.

Preferred flow:

```text
attempt object download
    |
    +-- success -> return data
    |
    +-- NotFound -> return current expected 404 behavior
```

Do not convert a single required network operation into multiple metadata calls.

## Error handling

Explicitly preserve handling for:

```text
object missing
permission denied
GCS timeout
network failure
unexpected storage error
```

Do not expose cloud credentials or raw internal exceptions to the frontend.

## Acceptance criteria

Compare:

```text
before GCS fetch p50/p95/p99
after  GCS fetch p50/p95/p99
```

Document the reduction.

---

# 6. Phase P0 — Browser Cache Headers

For static release images, return:

```http
Cache-Control: private, max-age=31536000, immutable
```

Use `private`, not `public`, because dataset images may be user/private data.

## Important invariant

Long-lived immutable caching is allowed only when the URL identifies immutable content.

The implementation MUST verify one of the following is true:

```text
A. object paths never change within a release
OR
B. release/path changes whenever image contents change
OR
C. the URL includes an explicit version/generation
```

If the same URL can later point to different image bytes, do NOT use a one-year immutable policy without URL versioning.

## Browser verification

Preferred evidence:

```text
from memory cache
from disk cache
```

For a fresh immutable cached resource, the ideal result is:

```text
no network request
```

A `304 Not Modified` response is acceptable fallback behavior, but it still incurs a network roundtrip and is not the ideal cache-hit state.

---

# 7. Phase P1 — Thumbnail Endpoint

Extend:

```text
/images/{split}/{image_id}/content
```

with:

```text
?size=thumbnail
```

Default / omitted:

```text
original image
```

Thumbnail:

```text
240 x 135
WebP
```

Preserve aspect ratio.

If exact dimensions require cropping, prefer contain/fit behavior unless existing product requirements specify crop.

## Target

Reduce the complete thumbnail-grid payload from approximately:

```text
~12 MB
```

toward:

```text
< 1–2 MB total
```

The previously estimated ~900 KB is a target to validate, not a guaranteed result.

## Thumbnail generation behavior

Do not regenerate an already available thumbnail on every request.

Required flow:

```text
thumbnail request
      |
      v
check thumbnail cache/artifact
      |
  +---+---+
  |       |
 HIT     MISS
  |       |
serve   download/read original
          |
          v
       decode
          |
          v
       resize
          |
          v
      WebP encode
          |
          v
       persist
          |
          v
        serve
```

Until P2 disk caching is implemented, keep thumbnail implementation simple and safe.

Avoid CPU-heavy generation loops inside unrelated request paths.

---

# 8. Phase P1 — Frontend Loading Strategy

Modify:

```text
frontend/src/views/ApiAnnotatorWorkspaceView.tsx
frontend/src/views/RealDataQAView.tsx
```

## Thumbnail URLs

Use:

```text
?size=thumbnail
```

for thumbnail elements.

Do not use original full-resolution images for the grid.

## Thumbnail loading attributes

Use:

```tsx
loading="lazy"
fetchPriority="low"
```

where supported.

## Main image

The main currently selected image should receive high scheduling priority.

Use:

```tsx
fetchPriority="high"
```

where supported.

Do NOT mark all images as high priority.

## Desired scheduling

```text
main selected frame
        |
        +--> highest priority

visible thumbnails
        |
        +--> normal / lower priority

offscreen thumbnails
        |
        +--> lazy
```

---

# 9. Phase P1 — Next / Previous Frame Prefetch

Implement prefetch in:

```text
ApiAnnotatorWorkspaceView.tsx
RealDataQAView.tsx
```

Use a `useEffect` or equivalent lifecycle mechanism.

When the user is viewing frame `N`:

```text
display N
    |
    +--> prefetch N + 1
    |
    +--> optionally prefetch N - 1
```

## Prefetch rules

Do not aggressively prefetch a large sequence.

Default maximum:

```text
next 1 frame
previous 1 frame
```

Prefer the next frame when navigation is normally forward.

Do not prefetch when:

```text
tab is hidden
connection is clearly constrained if detectable
the requested neighboring image is already cached/in-flight
component has unmounted
```

Avoid duplicate fetches.

Cancel obsolete prefetch work where practical when the user navigates rapidly.

## UX acceptance criteria

Measure:

```text
navigation trigger timestamp
        ->
main image rendered timestamp
```

Targets:

```text
cached navigation p95     < 50 ms
prefetched navigation p95 < 100 ms where device/browser permits
```

Do not report `0 ms`; report measured values.

---

# 10. Benchmark Checkpoint After P0 + P1

Before P2, run:

```text
pytest tests/
```

and all performance benchmarks.

Collect a result table.

Example:

| Metric | Before | After P0 | After P1 | Target |
|---|---:|---:|---:|---:|
| GCS p50 | 2740 ms | ... | ... | — |
| GCS p95 | 3409 ms | ... | ... | <700 ms |
| GCS p99 | 3793 ms | ... | ... | — |
| Thumbnail payload | ... | ... | ... | <1–2 MB |
| Main image first render p95 | ... | ... | ... | <1 s |
| Cached navigation p95 | ... | ... | ... | <50 ms |
| Error rate | ... | ... | ... | no regression |

## Stop condition

If:

```text
UX is acceptable
AND
uncached p95 target is met or close enough for product requirements
AND
browser cache/prefetch works correctly
```

then STOP.

Do not implement local disk cache only because it is in the plan.

---

# 11. Phase P2 — Bounded Local Disk Cache

Implement only if P0 + P1 are insufficient.

Cache root:

```text
/app/data/gcs_cache/
```

Separate:

```text
/app/data/gcs_cache/original/
/app/data/gcs_cache/thumbnail/
```

## Initial limits

```text
MAX_ORIGINAL_CACHE_SIZE  = 10 GB
MAX_THUMBNAIL_CACHE_SIZE = 5 GB
```

Make both configurable through environment variables.

Do not hard-code production capacity assumptions.

---

# 12. P2 — Cache Key

Minimum cache key inputs:

```text
bucket
object_key
size_variant
```

Example:

```text
sha256(bucket + object_key + size_variant)
```

## Required invariant

Document:

```text
Object paths MUST be immutable within a dataset release.
```

If this cannot be guaranteed, add one of:

```text
GCS generation
ETag
dataset release version
object content version
```

to the cache key.

Do not cache mutable contents behind an immutable cache key.

---

# 13. P2 — Single-Flight

Use process-local single-flight to prevent duplicate work inside one worker.

Concept:

```python
locks: dict[str, asyncio.Lock]
```

Flow:

```text
cache miss
    |
acquire key-specific lock
    |
check cache again
    |
    +-- now exists -> serve
    |
    +-- absent -> fetch/generate/write
```

## Critical limitation

`asyncio.Lock` only protects one Python process.

It is NOT a multi-process lock.

If multiple Gunicorn/Uvicorn workers share the cache directory, correctness must not depend on the process-local lock.

---

# 14. P2 — Cross-Process Safety

Use atomic filesystem writes.

Required algorithm:

```text
write unique temporary file
        |
flush/close
        |
os.replace(temp, final)
        |
serve final
```

Example temp filename:

```text
filename.webp.tmp-<uuid>
```

`os.replace()` must occur in the same filesystem/directory hierarchy so rename remains atomic.

## Optional cross-process deduplication

If duplicate thumbnail generation across workers becomes measurable, add a lightweight filesystem lock such as:

```text
flock / lock file
```

Do not introduce Redis/distributed locks solely for this purpose.

Atomic write correctness is mandatory.

Cross-process duplicate-work prevention is optional unless benchmarks show contention.

---

# 15. P2 — Eviction

Do NOT rely blindly on Linux `atime` as a precise LRU signal.

Filesystems may use:

```text
relatime
noatime
```

## Recommended v1 approach

On successful cache hit, update a cache-recency signal intentionally.

Simple option:

```python
os.utime(path, None)
```

Then treat `mtime` as last-used time for cache eviction.

Alternative:

```text
small SQLite/index metadata table
```

Only use the more complex index if needed.

## Eviction policy

Trigger:

```text
cache usage >= 90% configured limit
```

Evict oldest entries until:

```text
cache usage <= 75%
```

Run eviction outside the latency-critical request path where possible.

Do not allow multiple expensive eviction sweeps to run concurrently.

---

# 16. P2 — Disk-Full Handling

All cache writes must handle:

```text
OSError
ENOSPC
permission errors
I/O errors
```

If the cache write fails:

```text
log warning
attempt/trigger eviction asynchronously
serve/stream the already fetched object if possible
do not crash the request solely because caching failed
```

Cache is an optimization.

The image endpoint must remain functional when cache storage is unavailable.

---

# 17. Cache Observability

Expose or log enough information to calculate:

```text
cache_hit_total
cache_miss_total
cache_eviction_total
cache_write_error_total
thumbnail_generation_total
```

Recommended metrics:

```text
cache_hit_ratio
cache_bytes
thumbnail_generation_seconds
GCS_fetch_seconds
image_endpoint_seconds
```

If Prometheus already exists, expose these as Prometheus metrics.

If no metrics stack exists yet, structured logs are acceptable for the first iteration.

The agent must not introduce a large observability platform solely to complete this performance task.

---

# 18. Testing Requirements

## Unit tests

Add/adjust tests for:

```text
original endpoint unchanged
thumbnail parameter works
invalid size value handled correctly
GCS NotFound behavior
cache header behavior
thumbnail dimensions/format
cache key determinism
atomic write helper
disk-write failure fallback
```

For P2 also test:

```text
concurrent same-key request behavior
cache hit
cache miss
eviction boundary
stale/mutable key assumptions if applicable
```

## Regression rule

No implementation is accepted if:

```text
existing pytest suite fails
API response correctness changes unexpectedly
authorization is bypassed
private images become public
```

---

# 19. Performance Verification

Run at least these five segmented benchmarks.

## 19.1 Cold GCS

```text
100+ distinct objects
no local cache
```

## 19.2 Warm GCS

```text
100+ requests
same backend process
connection reused
```

## 19.3 Local disk cache

Only after P2:

```text
100+ cached objects
500+ cache-hit requests preferred
```

## 19.4 Browser cache

Verify using browser DevTools.

Expected:

```text
from memory cache
or
from disk cache
```

## 19.5 UI navigation

Measure:

```text
user navigation trigger
        ->
main image visible/rendered
```

Collect p50/p95 if practical.

## 19.6 Concurrent thumbnail grid

Load representative 48-thumbnail grids.

Capture:

```text
total transferred bytes
request count
largest-contentful image timing if useful
main-image completion time
thumbnail completion time
backend CPU
backend memory
error rate
```

---

# 20. Required Final Performance Report

The agent MUST produce a final report before marking the task complete.

Create:

```text
performance_optimization_report.md
```

Include:

## Changes made

```text
files modified
key implementation decisions
features deliberately not implemented
```

## Before / After

| Metric | Before | After | Change |
|---|---:|---:|---:|
| GCS p50 | 2740.01 ms | ... | ... |
| GCS p95 | 3408.57 ms | ... | ... |
| GCS p99 | 3793.00 ms | ... | ... |
| Thumbnail grid payload | ... | ... | ... |
| Cached navigation p95 | ... | ... | ... |
| Error rate | ... | ... | ... |

## Resource impact

```text
CPU before/after
memory before/after
disk cache size if P2
GCS requests if observable
```

## Remaining bottlenecks

List measured remaining bottlenecks only.

Do not speculate unless clearly labeled as hypothesis.

---

# 21. Rollback Strategy

Every phase should remain independently revertible.

Suggested commit boundaries:

```text
perf: add image benchmark instrumentation

perf: reuse GCS storage client

perf: remove redundant GCS metadata requests

perf: add immutable private browser caching

perf: add optimized thumbnail delivery

perf: prioritize main image and lazy load thumbnails

perf: prefetch adjacent frames

perf: add bounded local image cache       # only if P2 required
```

If an optimization causes correctness or reliability regression:

```text
revert the smallest affected commit
```

Do not revert unrelated performance improvements.

---

# 22. Security Constraints

Never:

```text
make the private GCS bucket public
embed GCP service account credentials in frontend code
send long-lived cloud credentials to browser
log signed credentials/tokens
bypass existing authorization checks
```

Browser caching must not weaken authorization.

A user must be authorized before the backend returns the protected image response.

---

# 23. Future Optimization — Direct GCS Delivery

Do NOT implement this in the current phase unless explicitly requested.

Current constraint:

```text
VM uses Compute Engine metadata credentials
bucket is private
current signing IAM flow is not configured
```

Future architecture:

```text
Browser
   |
   | request authorization / URL
   v
Backend
   |
   | short-lived signed access
   v
Browser ------------------> GCS
```

This can remove the backend VM from the image payload data plane.

Potential future work:

```text
service-account signing permission
IAM signBlob flow
signed URLs
Cloud CDN / Media CDN evaluation
GCS object version-aware delivery
```

Treat this as a future architectural optimization, not a blocker for the current implementation.

---

# 24. Recommended Open-Source Agent Tooling

Install only tools that materially improve this task.

Priority order:

```text
1. Serena
2. Context7
3. Repomix
4. Promptfoo
5. Grafana MCP           # if Grafana exists / is being added
6. ast-grep              # optional
7. Semgrep               # optional guardrail
```

---

## 24.1 Serena — highest-value coding-agent addition

Use case:

```text
semantic codebase navigation
symbol-aware search
find references
targeted edits
reduced need to read entire files
```

Why use it:

The performance task spans backend helpers, endpoint handlers, frontend components, tests, and benchmark scripts. Symbol-aware retrieval reduces unnecessary context and helps the agent locate the exact call graph before editing.

Recommended setup with an MCP-compatible client:

```bash
uvx --from git+https://github.com/oraios/serena serena-mcp-server \
  --context ide-assistant \
  --project "$(pwd)"
```

If the installed Serena version exposes a newer command name, follow its current README rather than guessing.

Recommended agent rule:

```text
Use Serena for symbol search, reference lookup, and targeted editing.
Do not read entire large files when symbol-level retrieval is sufficient.
Before changing a function, inspect its references and callers.
```

---

## 24.2 Context7 — current library documentation inside the agent

Use for:

```text
FastAPI
google-cloud-storage
Pillow
React
browser APIs
pytest
library-specific configuration
```

Context7 provides current/version-aware library docs through MCP/skills.

Antigravity setup is supported by Context7 tooling.

Example setup:

```bash
ctx7 setup --cli --antigravity
```

Alternative MCP setup:

```bash
npx -y @upstash/context7-mcp
```

Recommended agent rule:

```text
Whenever implementation depends on a library/API detail,
consult Context7 before assuming syntax or behavior.
Do not use Context7 for ordinary business-logic reasoning.
```

---

## 24.3 Repomix — fast whole-repo context snapshot

Use when:

```text
the agent needs an architecture overview
starting a fresh conversation
handoff between agents
reviewing cross-file dependencies
generating a compact repository snapshot
```

Quick use:

```bash
npx repomix@latest
```

For a focused snapshot:

```bash
npx repomix@latest \
  --include "src/**/*.py,frontend/src/**/*.tsx,tests/**/*,scratch/**/*" \
  --compress
```

Repomix can also run as MCP:

```bash
npx -y repomix --mcp
```

Do NOT attach a huge whole-repo dump to every prompt.

Use Serena for precise live navigation and Repomix for occasional architecture snapshots.

---

## 24.4 Promptfoo — regression tests for agent prompts and skills

Use Promptfoo if you maintain a reusable Antigravity prompt/SKILL for backend performance work.

Install / initialize:

```bash
npx promptfoo@latest init
```

Run evals:

```bash
npx promptfoo@latest eval
```

Optimize a configured prompt:

```bash
npx promptfoo@latest optimize
```

Suggested prompt eval cases:

```text
Agent must benchmark before claiming improvement.
Agent must not make GCS bucket public.
Agent must not implement Redis without measured need.
Agent must recognize asyncio.Lock is process-local.
Agent must not use atime blindly for LRU.
Agent must preserve API compatibility.
Agent must produce before/after p50/p95/p99.
```

This is useful for improving the quality of your reusable agent instructions, not for runtime image performance itself.

---

## 24.5 Grafana MCP — performance investigation by the agent

Install only if Grafana exists or you intentionally add it for observability.

It lets an MCP-compatible agent query:

```text
metrics
logs
traces
dashboards
alerts
```

Typical local invocation:

```bash
uvx mcp-grafana
```

Recommended use:

```text
"Compare image endpoint p95 before and after deployment."
"Find whether GCS latency or CPU is responsible for the spike."
"Check cache hit rate during the last benchmark."
```

Use a least-privilege Grafana service account.

---

## 24.6 ast-grep — structural search/refactoring

Useful when the agent must locate or rewrite repeated code patterns across the repo.

Install:

```bash
npm install --global @ast-grep/cli
```

Examples of good use:

```text
find all storage.Client() constructions
find repeated image-fetch patterns
find all frontend image elements missing loading/fetchPriority
```

Prefer this over fragile regex for structural code patterns.

---

## 24.7 Semgrep — optional safety/correctness guardrail

Semgrep is useful as a post-edit static-analysis step.

Potential task-specific checks:

```text
no hard-coded cloud credentials
no public bucket configuration introduced
no dangerous file-path construction
no obvious authorization bypass
no duplicate insecure GCS helper implementation
```

Do not block the performance work on building a large custom Semgrep ruleset.

Use it as an additional guardrail, not as the core performance tool.

---

# 25. Recommended Tooling Combination

For this project, start with only:

```text
Antigravity
    |
    +-- Serena
    |
    +-- Context7
    |
    +-- Repomix
    |
    +-- project SKILL.md / implementation plan
```

Then optionally:

```text
Promptfoo
    -> improve/test reusable Antigravity prompts

Grafana MCP
    -> investigate real production metrics

ast-grep
    -> large structural search/refactor

Semgrep
    -> security/static-analysis guardrail
```

Do not install every MCP server available.

Too many tools:

```text
increase agent decision overhead
increase context/tool noise
increase permissions surface
increase failure modes
```

---

# 26. Suggested Antigravity Agent Instruction

Use the following instruction together with this plan:

```text
Implement the attached performance optimization plan phase by phase.

Rules:
1. Start by inspecting the current implementation and benchmark script.
2. Do not modify code before identifying the relevant request path and callers.
3. Execute P0 first.
4. Run tests and benchmarks after each logical optimization.
5. Execute P1 only after P0 is verified.
6. Stop after P0+P1 and compare results against acceptance criteria.
7. Implement P2 local disk cache only if benchmarks show it is still needed.
8. Preserve API compatibility and authorization behavior.
9. Do not make the GCS bucket public.
10. Do not introduce Redis, Kafka, Kubernetes, a new DB, or other infrastructure without measured justification.
11. Treat asyncio.Lock as process-local only.
12. Use atomic filesystem writes for any shared disk cache.
13. Do not rely on filesystem atime for precise LRU.
14. Do not claim performance improvements without before/after metrics.
15. At completion, create performance_optimization_report.md with p50/p95/p99, payload, error-rate, resource-impact, and remaining measured bottlenecks.

Use Serena for symbol-level repository navigation where available.
Use Context7 for current library/API documentation where available.
Use Repomix only when a broader repository architecture snapshot is useful.
```

---

# 27. Definition of Done

The task is complete only when all applicable items are satisfied.

## Correctness

- [ ] Existing API behavior is preserved.
- [ ] Existing authorization is preserved.
- [ ] All relevant tests pass.
- [ ] Thumbnail path returns correct image content.
- [ ] No private storage exposure is introduced.

## Performance

- [ ] Baseline is recorded.
- [ ] Post-P0 benchmark is recorded.
- [ ] Post-P1 benchmark is recorded.
- [ ] Cold/warm GCS benchmarks are separated.
- [ ] Concurrent thumbnail scenario is measured.
- [ ] Browser cache behavior is verified.
- [ ] Frame navigation latency is measured.
- [ ] p95 result is compared against target.

## Frontend

- [ ] Grid uses thumbnails rather than originals.
- [ ] Offscreen thumbnails are lazy loaded.
- [ ] Main image is prioritized.
- [ ] Adjacent-frame prefetch is bounded.
- [ ] Cached/prefetched navigation is measured.

## P2 only if required

- [ ] Cache capacity is bounded.
- [ ] Original and thumbnail caches are separated.
- [ ] Cache writes are atomic.
- [ ] Process-local single-flight exists.
- [ ] Cross-process correctness does not depend on asyncio.Lock.
- [ ] Eviction does not rely blindly on atime.
- [ ] Disk-full failure degrades gracefully.
- [ ] Cache hit/miss behavior is measurable.

## Documentation

- [ ] `performance_optimization_report.md` exists.
- [ ] Before/after p50/p95/p99 are documented.
- [ ] Payload reduction is documented.
- [ ] Error rate is documented.
- [ ] Resource impact is documented.
- [ ] Remaining bottlenecks are evidence-based.
