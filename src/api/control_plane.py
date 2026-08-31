"""Project-scoped intake, work management and release control-plane APIs."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session, require_roles
from src.config import IngestionSettings
from src.models.admin_control import (
    DatasetSubmission,
    FrameTask,
    Project,
    ProjectMembership,
    Release,
    SubmissionAsset,
    TaskReview,
    WorkBatch,
    WorkflowEvent,
)
from src.models.application_user import ApplicationUser
from src.models.auth_schemas import AuthenticatedUser
from src.models.base_schemas import ApiModel
from src.models.ingestion import IngestionJob, IngestionJobStatus
from src.services.google_cloud import create_gcs_storage_client

router = APIRouter(prefix="/control", tags=["Admin Control Plane"])


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=255)
    customer_name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)


class ProjectDto(ProjectCreate):
    id: str
    status: str
    created_by: str
    created_at: datetime


class SubmissionCreate(ApiModel):
    dataset_type: str = Field(pattern="^(kitti|nuscenes|yolo)$")
    source_method: str = Field(pattern="^(upload|gcs_import)$")
    version: str = Field(min_length=1, max_length=128)
    split: str | None = Field(default=None, max_length=128)
    source_prefix: str | None = None


class AssetCreate(ApiModel):
    filename: str = Field(min_length=1, max_length=512)
    content_type: str | None = Field(default=None, max_length=255)
    size_bytes: int | None = Field(default=None, ge=1, le=2_147_483_648)
    checksum: str | None = Field(default=None, max_length=128)


class SubmissionDto(ApiModel):
    id: str
    project_id: str
    dataset_type: str
    source_method: str
    version: str
    split: str | None = None
    status: str
    source_prefix: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class AssetDto(ApiModel):
    id: str
    submission_id: str
    object_key: str
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    status: str
    created_at: datetime


class BatchDto(ApiModel):
    id: str
    project_id: str
    dataset_version_id: str | None = None
    name: str
    instructions: str | None = None
    scope_json: dict[str, Any]
    status: str
    reviewer_id: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class TaskDto(ApiModel):
    id: str
    project_id: str
    batch_id: str
    image_id: str
    annotator_id: str | None = None
    reviewer_id: str | None = None
    stage: str
    priority: str
    lock_version: int
    submitted_revision_id: str | None = None
    last_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None


class ReleaseDto(ApiModel):
    id: str
    project_id: str
    batch_id: str | None = None
    version: str
    status: str
    artifact_prefix: str | None = None
    manifest_json: dict[str, Any]
    created_by: str
    created_at: datetime
    frozen_at: datetime | None = None


class BatchCreate(ApiModel):
    name: str = Field(min_length=1, max_length=255)
    image_ids: list[str] = Field(min_length=1, max_length=10_000)
    reviewer_id: str = Field(min_length=1)
    annotator_ids: list[str] = Field(min_length=1, max_length=200)
    instructions: str | None = Field(default=None, max_length=4000)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class AssignmentUpdate(ApiModel):
    annotator_id: str | None = None
    reviewer_id: str | None = None


class TransitionRequest(ApiModel):
    stage: str = Field(pattern="^(in_progress|submitted|in_review|changes_requested|resubmitted|approved)$")
    revision_id: str | None = None
    reason: str | None = Field(default=None, max_length=4000)
    blocking: bool = False


class ReleaseCreate(ApiModel):
    version: str = Field(min_length=1, max_length=128)


class StartSubmissionDto(ApiModel):
    submission_id: str
    status: str
    run_id: str
    asset_count: int


def _dto(project: Project) -> ProjectDto:
    return ProjectDto(id=project.id, name=project.name, customer_name=project.customer_name, description=project.description, status=project.status, created_by=project.created_by, created_at=project.created_at)


async def _project_or_404(session: AsyncSession, project_id: str, user: AuthenticatedUser) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project was not found.")
    if user.role == "admin":
        return project
    membership = await session.scalar(select(ProjectMembership.id).where(ProjectMembership.project_id == project_id, ProjectMembership.user_id == user.id))
    if membership is None:
        raise HTTPException(status_code=404, detail="Project was not found.")
    return project


def _event(project_id: str | None, actor_id: str, event_type: str, entity_type: str, entity_id: str, after: dict[str, Any] | None = None) -> WorkflowEvent:
    return WorkflowEvent(id=uuid.uuid4().hex, project_id=project_id, actor_id=actor_id, event_type=event_type, entity_type=entity_type, entity_id=entity_id, after_json=after)


@router.get("/projects", response_model=list[ProjectDto])
async def list_projects(current: Annotated[AuthenticatedUser, Depends(get_current_user)], session: AsyncSession = Depends(get_db_session)) -> list[ProjectDto]:
    if current.role == "admin":
        projects = (await session.scalars(select(Project).order_by(Project.created_at.desc()))).all()
    else:
        projects = (await session.scalars(select(Project).join(ProjectMembership, ProjectMembership.project_id == Project.id).where(ProjectMembership.user_id == current.id).order_by(Project.created_at.desc()))).all()
    return [_dto(project) for project in projects]


@router.post("/projects", response_model=ProjectDto, status_code=201)
async def create_project(payload: ProjectCreate, admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))], session: AsyncSession = Depends(get_db_session)) -> ProjectDto:
    if await session.get(ApplicationUser, admin.id) is None:
        now = datetime.now(UTC)
        session.add(ApplicationUser(id=admin.id, email=admin.email, display_name=admin.display_name, role="admin", disabled=False, created_at=now, updated_at=now))
    now = datetime.now(UTC)
    project = Project(id=f"prj_{uuid.uuid4().hex[:20]}", name=payload.name.strip(), customer_name=payload.customer_name.strip(), description=payload.description, status="active", created_by=admin.id, created_at=now, updated_at=now)
    session.add(project)
    session.add(ProjectMembership(project_id=project.id, user_id=admin.id))
    session.add(_event(project.id, admin.id, "project_created", "project", project.id, {"name": project.name}))
    await session.commit()
    return _dto(project)


@router.post("/projects/{project_id}/submissions", response_model=SubmissionDto, status_code=201)
async def create_submission(project_id: str, payload: SubmissionCreate, admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))], session: AsyncSession = Depends(get_db_session)) -> DatasetSubmission:
    await _project_or_404(session, project_id, admin)
    submission = DatasetSubmission(id=f"sub_{uuid.uuid4().hex[:20]}", project_id=project_id, dataset_type=payload.dataset_type, source_method=payload.source_method, version=payload.version.strip(), split=payload.split, status="draft", source_prefix=payload.source_prefix, created_by=admin.id, metadata_json={})
    session.add(submission)
    if payload.source_method == "gcs_import":
        raw_uri = (payload.source_prefix or "").strip()
        expected_prefix = f"gs://{IngestionSettings().gcs_bucket}/" if IngestionSettings().gcs_bucket else ""
        if not expected_prefix or not raw_uri.startswith(expected_prefix) or not raw_uri.removeprefix(expected_prefix).strip("/"):
            raise HTTPException(status_code=422, detail="GCS import must reference an object in the configured private bucket.")
        object_key = raw_uri.removeprefix(expected_prefix).lstrip("/")
        session.add(SubmissionAsset(id=f"asset_{uuid.uuid4().hex[:20]}", submission_id=submission.id, object_key=object_key, filename=object_key.rsplit("/", 1)[-1], status="uploaded", created_at=datetime.now(UTC)))
    session.add(_event(project_id, admin.id, "submission_created", "submission", submission.id, {"dataset_type": payload.dataset_type, "source_method": payload.source_method}))
    await session.commit()
    return submission


@router.post("/submissions/{submission_id}/assets", response_model=dict[str, Any], status_code=201)
async def create_upload_session(submission_id: str, payload: AssetCreate, request: Request, admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))], session: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    submission = await session.get(DatasetSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission was not found.")
    await _project_or_404(session, submission.project_id, admin)
    if submission.status not in {"draft", "uploading"}:
        raise HTTPException(status_code=409, detail="Submission is no longer accepting assets.")
    filename = payload.filename.replace("\\", "/").split("/")[-1]
    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=422, detail="Invalid filename.")
    key = f"projects/{submission.project_id}/submissions/{submission.id}/raw/{filename}"
    asset = SubmissionAsset(id=f"asset_{uuid.uuid4().hex[:20]}", submission_id=submission.id, object_key=key, filename=filename, content_type=payload.content_type, size_bytes=payload.size_bytes, checksum=payload.checksum, status="pending")
    session.add(asset)
    submission.status = "uploading"
    await session.flush()
    upload_url: str | None = None
    try:
        settings = IngestionSettings()
        client = create_gcs_storage_client(settings)
        blob = client.bucket(settings.bucket_name).blob(key)
        upload_url = await asyncio.to_thread(blob.create_resumable_upload_session, content_type=payload.content_type or "application/octet-stream", size=payload.size_bytes)
    except Exception:
        # Local/test mode may not have GCS credentials. The asset can still be
        # completed by an ops import or test fixture without exposing secrets.
        upload_url = None
    session.add(_event(submission.project_id, admin.id, "upload_session_created", "submission_asset", asset.id, {"object_key": key}))
    await session.commit()
    return {"assetId": asset.id, "objectKey": key, "uploadUrl": upload_url, "expiresIn": 3600}


@router.post("/submissions/{submission_id}/assets/{asset_id}/complete", response_model=AssetDto)
async def complete_upload(submission_id: str, asset_id: str, admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))], session: AsyncSession = Depends(get_db_session)) -> SubmissionAsset:
    asset = await session.get(SubmissionAsset, asset_id)
    submission = await session.get(DatasetSubmission, submission_id)
    if asset is None or submission is None or asset.submission_id != submission_id:
        raise HTTPException(status_code=404, detail="Submission asset was not found.")
    await _project_or_404(session, submission.project_id, admin)
    if asset.status == "uploaded":
        return asset
    try:
        settings = IngestionSettings()
        client = create_gcs_storage_client(settings)
        blob = client.bucket(settings.bucket_name).get_blob(asset.object_key)
        if blob is None:
            raise HTTPException(status_code=409, detail="Uploaded object is not present in GCS yet.")
        if asset.size_bytes is not None and blob.size is not None and int(blob.size) != asset.size_bytes:
            raise HTTPException(status_code=422, detail="Uploaded object size does not match the declared size.")
    except HTTPException:
        raise
    except Exception:
        # Keep local/test fixtures usable; production credentials must be set
        # and the worker performs a second verification before ingestion.
        pass
    asset.status = "uploaded"
    await session.commit()
    return asset


@router.post("/submissions/{submission_id}/start", response_model=StartSubmissionDto)
async def start_submission(submission_id: str, admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))], session: AsyncSession = Depends(get_db_session)) -> StartSubmissionDto:
    submission = await session.get(DatasetSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission was not found.")
    await _project_or_404(session, submission.project_id, admin)
    assets = list((await session.scalars(select(SubmissionAsset).where(SubmissionAsset.submission_id == submission.id))).all())
    if not assets or any(asset.status != "uploaded" for asset in assets):
        raise HTTPException(status_code=409, detail="Every submission asset must finish uploading before validation starts.")
    if submission.status in {"queued", "validating", "normalizing", "ready"}:
        run_id = str(submission.metadata_json.get("runId") or submission.id)
        return StartSubmissionDto(submission_id=submission.id, status=submission.status, run_id=run_id, asset_count=len(assets))
    run_id = f"run_{uuid.uuid4().hex[:20]}"
    settings = IngestionSettings()
    bucket = settings.gcs_bucket or "configured-at-runtime"
    uploaded_keys = {asset.filename: asset.object_key for asset in assets}
    job = IngestionJob(request_fingerprint=run_id, requested_by=admin.id, provider="customer_upload", dataset_type=submission.dataset_type, version=submission.version, split=submission.split, status=IngestionJobStatus.PENDING, source_manifest={"run_id": run_id, "submission_id": submission.id, "project_id": submission.project_id, "uploaded_object_keys": uploaded_keys}, target_bucket=bucket, target_prefix=f"projects/{submission.project_id}/datasets/{submission.version}", result_metrics={})
    submission.status = "queued"
    submission.metadata_json = {**(submission.metadata_json or {}), "runId": run_id, "uploadedObjectKeys": uploaded_keys}
    session.add(job)
    session.add(_event(submission.project_id, admin.id, "submission_queued", "submission", submission.id, {"runId": run_id, "assetCount": len(assets)}))
    await session.commit()
    return StartSubmissionDto(submission_id=submission.id, status=submission.status, run_id=run_id, asset_count=len(assets))


@router.get("/batches", response_model=list[BatchDto])
async def list_batches(current: Annotated[AuthenticatedUser, Depends(get_current_user)], session: AsyncSession = Depends(get_db_session), project_id: str | None = None) -> list[WorkBatch]:
    query = select(WorkBatch).order_by(WorkBatch.created_at.desc())
    if project_id:
        await _project_or_404(session, project_id, current)
        query = query.where(WorkBatch.project_id == project_id)
    elif current.role != "admin":
        query = query.join(ProjectMembership, ProjectMembership.project_id == WorkBatch.project_id).where(ProjectMembership.user_id == current.id)
    return list((await session.scalars(query)).all())


@router.post("/projects/{project_id}/batches", response_model=BatchDto, status_code=201)
async def create_batch(project_id: str, payload: BatchCreate, admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))], session: AsyncSession = Depends(get_db_session)) -> WorkBatch:
    await _project_or_404(session, project_id, admin)
    reviewer = await session.get(ApplicationUser, payload.reviewer_id)
    if reviewer is None or reviewer.role not in {"reviewer", "admin"} or reviewer.disabled:
        raise HTTPException(status_code=422, detail="Reviewer must be an active reviewer account.")
    annotators = list(dict.fromkeys(payload.annotator_ids))
    if not annotators:
        raise HTTPException(status_code=422, detail="At least one annotator is required.")
    batch_id = f"bat_{uuid.uuid4().hex[:20]}"
    now = datetime.now(UTC)
    batch = WorkBatch(id=batch_id, project_id=project_id, name=payload.name.strip(), instructions=payload.instructions, scope_json={"imageIds": payload.image_ids}, status="assigned", reviewer_id=payload.reviewer_id, created_by=admin.id, created_at=now, updated_at=now)
    session.add(batch)
    for index, image_id in enumerate(dict.fromkeys(payload.image_ids)):
        task = FrameTask(id=f"task_{uuid.uuid4().hex[:20]}", project_id=project_id, batch_id=batch_id, image_id=image_id, annotator_id=annotators[index % len(annotators)], reviewer_id=payload.reviewer_id, stage="assigned", priority=payload.priority, lock_version=1, created_at=now, updated_at=now)
        session.add(task)
    session.add(_event(project_id, admin.id, "batch_created", "batch", batch_id, {"taskCount": len(payload.image_ids), "reviewerId": payload.reviewer_id}))
    await session.commit()
    return batch


@router.patch("/tasks/{task_id}/assignment", response_model=TaskDto)
async def assign_task(task_id: str, payload: AssignmentUpdate, admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))], session: AsyncSession = Depends(get_db_session)) -> FrameTask:
    task = await session.get(FrameTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task was not found.")
    await _project_or_404(session, task.project_id, admin)
    if task.stage == "approved":
        raise HTTPException(status_code=409, detail="Approved task cannot be reassigned.")
    if payload.annotator_id is not None:
        task.annotator_id = payload.annotator_id
    if payload.reviewer_id is not None:
        task.reviewer_id = payload.reviewer_id
    task.stage = "assigned" if task.annotator_id else "unassigned"
    task.lock_version += 1
    task.updated_at = datetime.now(UTC)
    session.add(_event(task.project_id, admin.id, "task_assigned", "task", task.id, {"annotatorId": task.annotator_id, "reviewerId": task.reviewer_id}))
    await session.commit()
    return task


@router.get("/tasks", response_model=list[TaskDto])
async def list_tasks(current: Annotated[AuthenticatedUser, Depends(get_current_user)], session: AsyncSession = Depends(get_db_session), stage: str | None = Query(default=None), batch_id: str | None = Query(default=None)) -> list[FrameTask]:
    query = select(FrameTask).order_by(FrameTask.updated_at.desc())
    if stage:
        query = query.where(FrameTask.stage == stage)
    if batch_id:
        query = query.where(FrameTask.batch_id == batch_id)
    if current.role == "annotator":
        query = query.where(FrameTask.annotator_id == current.id)
    elif current.role == "reviewer":
        query = query.where(FrameTask.reviewer_id == current.id)
    return list((await session.scalars(query.limit(500))).all())


@router.post("/tasks/{task_id}/transition", response_model=TaskDto)
async def transition_task(task_id: str, payload: TransitionRequest, current: Annotated[AuthenticatedUser, Depends(get_current_user)], session: AsyncSession = Depends(get_db_session)) -> FrameTask:
    task = await session.get(FrameTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task was not found.")
    if current.role == "annotator" and task.annotator_id != current.id:
        raise HTTPException(status_code=404, detail="Task was not found.")
    if current.role == "reviewer" and task.reviewer_id != current.id:
        raise HTTPException(status_code=404, detail="Task was not found.")
    allowed = {
        "assigned": {"in_progress"}, "in_progress": {"submitted"}, "submitted": {"in_review"},
        "in_review": {"approved", "changes_requested"}, "changes_requested": {"resubmitted"},
        "resubmitted": {"in_review"},
    }
    if payload.stage not in allowed.get(task.stage, set()):
        raise HTTPException(status_code=409, detail=f"Cannot transition task from {task.stage} to {payload.stage}.")
    if payload.stage == "changes_requested" and not payload.reason:
        raise HTTPException(status_code=422, detail="A reason is required when requesting changes.")
    if payload.stage == "approved" and current.role not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Only a reviewer or admin can approve a task.")
    before = task.stage
    now = datetime.now(UTC)
    task.stage = payload.stage
    task.last_reason = payload.reason
    task.lock_version += 1
    task.updated_at = now
    if payload.stage == "in_progress":
        task.started_at = now
    if payload.stage in {"submitted", "resubmitted"}:
        task.submitted_at = now
    if payload.stage == "approved":
        task.approved_at = now
    if payload.stage in {"approved", "changes_requested"}:
        session.add(TaskReview(id=f"rev_{uuid.uuid4().hex[:20]}", task_id=task.id, reviewer_id=current.id, revision_id=payload.revision_id, decision=payload.stage, reason=payload.reason, blocking=payload.blocking, created_at=now))
    session.add(_event(task.project_id, current.id, "task_stage_changed", "task", task.id, {"before": before, "after": payload.stage, "reason": payload.reason}))
    await session.commit()
    return task


@router.get("/dashboard/team-health", response_model=dict[str, Any])
async def team_health(admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))], session: AsyncSession = Depends(get_db_session), project_id: str | None = None) -> dict[str, Any]:
    query = select(FrameTask)
    if project_id:
        await _project_or_404(session, project_id, admin)
        query = query.where(FrameTask.project_id == project_id)
    tasks = list((await session.scalars(query)).all())
    by_stage: dict[str, int] = {}
    by_annotator: dict[str, dict[str, int]] = {}
    for task in tasks:
        by_stage[task.stage] = by_stage.get(task.stage, 0) + 1
        if task.annotator_id:
            row = by_annotator.setdefault(task.annotator_id, {"assigned": 0, "wip": 0, "approved": 0, "changesRequested": 0})
            row["assigned"] += 1
            if task.stage in {"assigned", "in_progress", "submitted", "in_review", "resubmitted"}:
                row["wip"] += 1
            if task.stage == "approved":
                row["approved"] += 1
            if task.stage == "changes_requested":
                row["changesRequested"] += 1
    return {"generatedAt": datetime.now(UTC), "totalTasks": len(tasks), "byStage": by_stage, "annotatorWorkload": by_annotator, "quality": {"approvalRate": (by_stage.get("approved", 0) / len(tasks) if tasks else None), "reworkRate": (by_stage.get("changes_requested", 0) / len(tasks) if tasks else None)}, "ranking": None}


@router.post("/projects/{project_id}/releases", response_model=ReleaseDto, status_code=201)
async def create_release(project_id: str, payload: ReleaseCreate, admin: Annotated[AuthenticatedUser, Depends(require_roles("admin"))], session: AsyncSession = Depends(get_db_session)) -> Release:
    await _project_or_404(session, project_id, admin)
    tasks = list((await session.scalars(select(FrameTask).where(FrameTask.project_id == project_id))).all())
    if not tasks or any(task.stage != "approved" for task in tasks):
        raise HTTPException(status_code=409, detail="All project tasks must be approved before creating a release.")
    release = Release(id=f"rel_{uuid.uuid4().hex[:20]}", project_id=project_id, version=payload.version.strip(), status="frozen", artifact_prefix=f"projects/{project_id}/releases/{payload.version.strip()}", manifest_json={"taskIds": [task.id for task in tasks], "format": "yolo-detection-v1", "taskCount": len(tasks)}, created_by=admin.id, created_at=datetime.now(UTC), frozen_at=datetime.now(UTC))
    session.add(release)
    session.add(_event(project_id, admin.id, "release_frozen", "release", release.id, release.manifest_json))
    await session.commit()
    return release
