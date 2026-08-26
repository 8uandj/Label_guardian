import asyncio
from src.config import IngestionSettings
from src.services.google_cloud import create_gcs_storage_client

settings = IngestionSettings()
client = create_gcs_storage_client(settings)
bucket = client.bucket(settings.bucket_name)
blobs = list(bucket.list_blobs(max_results=1))
if blobs:
    blob = bucket.blob(blobs[0].name)
    stream = blob.open("rb")
    print("Content-type before read:", blob.content_type)
    chunk = stream.read(1024)
    print("Content-type after read:", blob.content_type)
    print("ETag after read:", blob.etag)
    stream.close()
