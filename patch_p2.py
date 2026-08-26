import re

with open("src/api/real_dataset.py", "r") as f:
    content = f.read()

import_mimetypes = "import mimetypes"
if import_mimetypes not in content:
    content = content.replace("import os", "import os\nimport mimetypes")

old_code = """
            if is_thumbnail:
                data, _ = await asyncio.to_thread(_download_gcs_image, image_row)
                thumb_bytes = await asyncio.to_thread(_generate_thumbnail, data)
                thumb_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = thumb_path.with_name(f"{thumb_path.name}.tmp-{uuid.uuid4()}")
                tmp_path.write_bytes(thumb_bytes)
                os.replace(tmp_path, thumb_path)
                return FileResponse(thumb_path, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"})

            chunks, content_type, headers = await asyncio.to_thread(_stream_gcs_image, image_row)
            return StreamingResponse(
                chunks,
                media_type=content_type,
                headers=headers,
            )
"""

new_code = """
            if is_thumbnail:
                data, _ = await asyncio.to_thread(_download_gcs_image, image_row)
                thumb_bytes = await asyncio.to_thread(_generate_thumbnail, data)
                thumb_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = thumb_path.with_name(f"{thumb_path.name}.tmp-{uuid.uuid4()}")
                tmp_path.write_bytes(thumb_bytes)
                os.replace(tmp_path, thumb_path)
                return FileResponse(thumb_path, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"})

            ext = pathlib.Path(image_row.filename).suffix if hasattr(image_row, "filename") and image_row.filename else ".jpg"
            full_path = _gcs_cache_root() / "original" / f"{image_id}{ext}"
            
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

if old_code.strip() in content:
    content = content.replace(old_code.strip(), new_code.strip())
    with open("src/api/real_dataset.py", "w") as f:
        f.write(content)
    print("Patched!")
else:
    print("Could not find old_code")
