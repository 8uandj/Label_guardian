"""Standalone GPU inference runtime.

This app owns the detector dependency stack and image loading for model
execution. The main FastAPI app should call it with a GCS object reference
instead of forwarding image bytes.
"""

from __future__ import annotations

import hmac
from io import BytesIO
from pathlib import Path, PurePosixPath
from time import perf_counter
from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, status
from PIL import Image

from src.config import InferenceServiceSettings, IngestionSettings
from src.models.inference_schemas import InferenceDetection, InferenceRequest, InferenceResponse
from src.models.real_dataset_schemas import RealDatasetBBox
from src.services.google_cloud import create_gcs_storage_client
from src.services.inference_client import INFERENCE_AUTH_HEADER
from src.services.yolo import TARGET_DETECTION_CLASSES, get_yolo_model_by_name, resolve_class_ids


def _settings() -> InferenceServiceSettings:
    return InferenceServiceSettings()


def _gcs_settings() -> IngestionSettings:
    return IngestionSettings()


def _authorize(
    authorization_token: Annotated[str | None, Header(alias=INFERENCE_AUTH_HEADER)] = None,
    settings: InferenceServiceSettings = Depends(_settings),
) -> None:
    expected = settings.inference_auth_token
    if expected is None:
        return
    supplied = authorization_token or ""
    if not hmac.compare_digest(supplied, expected.get_secret_value()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid inference service token.",
        )


def _validated_object_key(key: str, settings: InferenceServiceSettings) -> str:
    normalized = key.strip().lstrip("/").replace("\\", "/")
    parts = normalized.split("/")
    if not normalized or any(part in {"", ".", ".."} for part in parts):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="objectKey must be a normalized GCS object key.",
        )
    allowed_prefixes = settings.allowed_object_prefix_values
    if allowed_prefixes and not any(
        normalized == prefix or normalized.startswith(f"{prefix}/") for prefix in allowed_prefixes
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested image object is outside the allowed inference prefixes.",
        )
    return normalized


def _download_gcs_bytes(
    *,
    bucket_name: str,
    object_key: str,
    settings: IngestionSettings,
) -> tuple[bytes, str]:
    client = create_gcs_storage_client(settings)
    blob = client.bucket(bucket_name).blob(object_key)
    try:
        blob.reload(client=client)
        return blob.download_as_bytes(client=client), blob.content_type or "application/octet-stream"
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image object does not exist or cannot be read: gs://{bucket_name}/{object_key}",
        ) from error


def _resolve_model_name(
    *,
    settings: InferenceServiceSettings,
    storage_settings: IngestionSettings,
) -> str:
    configured_name = settings.inference_model_name
    if not configured_name.startswith("gs://"):
        return configured_name

    parsed = urlparse(configured_name)
    bucket_name = parsed.netloc
    object_key = parsed.path.lstrip("/")
    parts = PurePosixPath(object_key).parts
    if not bucket_name or not object_key or any(part in {"", ".", ".."} for part in parts):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INFERENCE_MODEL_NAME must be a valid gs://bucket/object path.",
        )

    cache_root = settings.inference_model_cache_dir.resolve()
    cache_path = (cache_root / bucket_name / Path(*parts)).resolve()
    if not cache_path.is_relative_to(cache_root):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INFERENCE_MODEL_NAME resolves outside the model cache directory.",
        )
    if cache_path.is_file():
        return str(cache_path)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    client = create_gcs_storage_client(storage_settings)
    blob = client.bucket(bucket_name).blob(object_key)
    try:
        blob.download_to_filename(str(cache_path), client=client)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model artifact does not exist or cannot be read: {configured_name}",
        ) from error
    return str(cache_path)


def _run_yolo(
    image_bytes: bytes,
    *,
    settings: InferenceServiceSettings,
    storage_settings: IngestionSettings,
) -> tuple[list[InferenceDetection], dict[str, float | None], dict[str, Any]]:
    metadata: dict[str, Any] = {}
    model_load_start = perf_counter()
    resolved_model_name = _resolve_model_name(settings=settings, storage_settings=storage_settings)
    model = get_yolo_model_by_name(resolved_model_name)
    model_load_ms = (perf_counter() - model_load_start) * 1000

    matched_ids, unmatched_names = resolve_class_ids(model, TARGET_DETECTION_CLASSES)
    predict_kwargs: dict[str, Any] = {
        "conf": settings.inference_confidence_threshold,
        "verbose": False,
    }
    if matched_ids:
        predict_kwargs["classes"] = matched_ids
    if unmatched_names:
        metadata["unmatched_target_classes"] = unmatched_names
    if resolved_model_name != settings.inference_model_name:
        metadata["resolved_model_path"] = resolved_model_name

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            rgb_image = image.convert("RGB")
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image bytes cannot be decoded: {error}",
        ) from error

    inference_start = perf_counter()
    results = model(rgb_image, **predict_kwargs)
    inference_wall_ms = (perf_counter() - inference_start) * 1000

    first_result = results[0]
    speed = getattr(first_result, "speed", None) or {}
    latency_ms = {
        "model_load": round(model_load_ms, 3),
        "inference_wall": round(inference_wall_ms, 3),
        "preprocess": round(float(speed["preprocess"]), 3) if "preprocess" in speed else None,
        "inference": round(float(speed["inference"]), 3) if "inference" in speed else None,
        "postprocess": round(float(speed["postprocess"]), 3) if "postprocess" in speed else None,
    }

    names = first_result.names
    detections: list[InferenceDetection] = []
    for box in first_result.boxes:
        x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
        class_id = int(box.cls[0])
        detections.append(
            InferenceDetection(
                class_name=names[class_id],
                bbox=RealDatasetBBox(x1=x1, y1=y1, x2=x2, y2=y2),
                confidence=float(box.conf[0]),
            )
        )
    return detections, latency_ms, metadata


def create_inference_app(
    *,
    settings: InferenceServiceSettings | None = None,
    gcs_settings: IngestionSettings | None = None,
) -> FastAPI:
    service_settings = settings or _settings()
    storage_settings = gcs_settings or _gcs_settings()

    def authorize_request(
        authorization_token: Annotated[str | None, Header(alias=INFERENCE_AUTH_HEADER)] = None,
    ) -> None:
        expected = service_settings.inference_auth_token
        if expected is None:
            return
        supplied = authorization_token or ""
        if not hmac.compare_digest(supplied, expected.get_secret_value()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid inference service token.",
            )

    application = FastAPI(
        title=service_settings.inference_app_name,
        version=service_settings.inference_app_version,
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "label-guardian-inference",
            "environment": service_settings.inference_app_env,
            "version": service_settings.inference_app_version,
        }

    @application.get("/ready")
    async def readiness() -> dict[str, str]:
        _ = storage_settings.bucket_name
        create_gcs_storage_client(storage_settings)
        return {
            "status": "ok",
            "service": "label-guardian-inference",
            "environment": service_settings.inference_app_env,
            "version": service_settings.inference_app_version,
        }

    @application.post(
        "/v1/detect",
        response_model=InferenceResponse,
        dependencies=[Depends(authorize_request)],
    )
    async def detect(request: InferenceRequest) -> InferenceResponse:
        requested_bucket = request.image.bucket or storage_settings.bucket_name
        if requested_bucket != storage_settings.bucket_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The requested bucket is not served by this inference service.",
            )
        object_key = _validated_object_key(request.image.object_key, service_settings)
        image_bytes, content_type = _download_gcs_bytes(
            bucket_name=requested_bucket,
            object_key=object_key,
            settings=storage_settings,
        )
        detections, latency_ms, metadata = _run_yolo(
            image_bytes,
            settings=service_settings,
            storage_settings=storage_settings,
        )
        return InferenceResponse(
            model_name=service_settings.inference_model_name,
            model_version=service_settings.inference_model_version or service_settings.inference_model_name,
            detections=detections,
            latency_ms=latency_ms,
            metadata={
                **metadata,
                "content_type": content_type,
                "bucket": requested_bucket,
                "object_key": object_key,
                "dataset_id": request.image.dataset_id,
                "dataset_version": request.image.dataset_version,
                "split": request.image.split,
                "image_id": request.image.image_id,
            },
        )

    return application


app = create_inference_app()
