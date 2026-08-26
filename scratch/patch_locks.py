import re
with open("src/api/real_dataset.py", "r") as f:
    content = f.read()

# 1. Add locks and eviction
if "_cache_locks" not in content:
    imports_end = content.find("\n\nrouter = APIRouter(")
    new_code = """
_cache_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

async def _evict_cache_if_needed():
    def do_evict():
        try:
            cache_root = _gcs_cache_root()
            original_dir = cache_root / "original"
            if original_dir.exists():
                size = sum(f.stat().st_size for f in original_dir.glob("*") if f.is_file())
                if size > 10 * 1024 * 1024 * 1024:
                    files = [(f, f.stat().st_mtime) for f in original_dir.glob("*") if f.is_file()]
                    files.sort(key=lambda x: x[1])
                    for f, _ in files[:len(files)//4]:
                        try:
                            f.unlink(missing_ok=True)
                        except OSError:
                            pass
            thumb_dir = cache_root / "thumbnails"
            if thumb_dir.exists():
                size = sum(f.stat().st_size for f in thumb_dir.glob("*") if f.is_file())
                if size > 2 * 1024 * 1024 * 1024:
                    files = [(f, f.stat().st_mtime) for f in thumb_dir.glob("*") if f.is_file()]
                    files.sort(key=lambda x: x[1])
                    for f, _ in files[:len(files)//4]:
                        try:
                            f.unlink(missing_ok=True)
                        except OSError:
                            pass
        except Exception:
            pass
    await asyncio.to_thread(do_evict)
"""
    content = content[:imports_end] + "\n" + new_code + content[imports_end:]

# 2. Add BackgroundTasks to signature
if "background_tasks: BackgroundTasks" not in content:
    content = content.replace(
        "    service: Annotated[RealDatasetService, Depends(get_real_dataset_service)],",
        "    service: Annotated[RealDatasetService, Depends(get_real_dataset_service)],\n    background_tasks: BackgroundTasks,"
    )
    if "from fastapi import BackgroundTasks" not in content:
        content = content.replace("from fastapi import APIRouter", "from fastapi import APIRouter, BackgroundTasks")

# 3. Add locks and utime around thumbnail generation
old_thumb = """
            if is_thumbnail:
                data, _ = await asyncio.to_thread(_download_gcs_image, image_row)
                thumb_bytes = await asyncio.to_thread(_generate_thumbnail, data)
                thumb_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = thumb_path.with_name(f"{thumb_path.name}.tmp-{uuid.uuid4()}")
                tmp_path.write_bytes(thumb_bytes)
                os.replace(tmp_path, thumb_path)
                return FileResponse(thumb_path, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"})
"""

new_thumb = """
            if is_thumbnail:
                async with _cache_locks[f"thumb_{image_id}"]:
                    if thumb_path.exists():
                        try:
                            os.utime(thumb_path, None)
                        except OSError:
                            pass
                        return FileResponse(thumb_path, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"})
                    data, _ = await asyncio.to_thread(_download_gcs_image, image_row)
                    thumb_bytes = await asyncio.to_thread(_generate_thumbnail, data)
                    thumb_path.parent.mkdir(parents=True, exist_ok=True)
                    tmp_path = thumb_path.with_name(f"{thumb_path.name}.tmp-{uuid.uuid4()}")
                    tmp_path.write_bytes(thumb_bytes)
                    os.replace(tmp_path, thumb_path)
                background_tasks.add_task(_evict_cache_if_needed)
                return FileResponse(thumb_path, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"})
"""
content = content.replace(old_thumb.strip(), new_thumb.strip())

# 4. Add locks and utime around full image generation
old_full = """
            import pathlib
            ext = pathlib.Path(image_row.filename).suffix if hasattr(image_row, "filename") and image_row.filename else ".jpg"
            full_path = _gcs_cache_root() / "original" / f"{image_id}{ext}"
            
            import mimetypes
            content_type = mimetypes.guess_type(image_row.filename)[0] if hasattr(image_row, "filename") and image_row.filename else "image/jpeg"
            
            if full_path.exists():
                return FileResponse(full_path, media_type=content_type, headers={"Cache-Control": "private, max-age=31536000, immutable"})
                
            data, dl_content_type = await asyncio.to_thread(_download_gcs_image, image_row)
            content_type = dl_content_type or content_type
            
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = full_path.with_name(f"{full_path.name}.tmp-{uuid.uuid4()}")
                tmp_path.write_bytes(data)
                os.replace(tmp_path, full_path)
            except Exception as e:
                import logging
                logging.warning(f"Failed to cache full image to disk: {e}")
                
            return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=31536000, immutable"})
"""

new_full = """
            import pathlib
            ext = pathlib.Path(image_row.filename).suffix if hasattr(image_row, "filename") and image_row.filename else ".jpg"
            full_path = _gcs_cache_root() / "original" / f"{image_id}{ext}"
            
            import mimetypes
            content_type = mimetypes.guess_type(image_row.filename)[0] if hasattr(image_row, "filename") and image_row.filename else "image/jpeg"
            
            async with _cache_locks[f"full_{image_id}"]:
                if full_path.exists():
                    try:
                        os.utime(full_path, None)
                    except OSError:
                        pass
                    return FileResponse(full_path, media_type=content_type, headers={"Cache-Control": "private, max-age=31536000, immutable"})
                    
                data, dl_content_type = await asyncio.to_thread(_download_gcs_image, image_row)
                content_type = dl_content_type or content_type
                
                try:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    tmp_path = full_path.with_name(f"{full_path.name}.tmp-{uuid.uuid4()}")
                    tmp_path.write_bytes(data)
                    os.replace(tmp_path, full_path)
                    background_tasks.add_task(_evict_cache_if_needed)
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to cache full image to disk: {e}")
                    
                return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=31536000, immutable"})
"""
content = content.replace(old_full.strip(), new_full.strip())

# 5. Add utime for early return thumb
old_early_thumb = """
        if is_thumbnail:
            thumb_path = _gcs_cache_root() / "thumbnails" / f"{image_id}.webp"
            if thumb_path.exists():
                return FileResponse(thumb_path, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"})
"""
new_early_thumb = """
        if is_thumbnail:
            thumb_path = _gcs_cache_root() / "thumbnails" / f"{image_id}.webp"
            if thumb_path.exists():
                try:
                    os.utime(thumb_path, None)
                except OSError:
                    pass
                return FileResponse(thumb_path, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"})
"""
content = content.replace(old_early_thumb.strip(), new_early_thumb.strip())

with open("src/api/real_dataset.py", "w") as f:
    f.write(content)
print("Done patching.")
