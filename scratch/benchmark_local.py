import time
import asyncio
from fastapi.testclient import TestClient
from src.main import app
from src.api.dependencies import get_current_user

# Override auth
def override_get_current_user():
    class MockUser:
        id = "mock"
        role = "annotator"
        email = "mock@mock.com"
    return MockUser()

app.dependency_overrides[get_current_user] = override_get_current_user

def run_benchmark():
    with TestClient(app) as client:
        # 1. Fetch samples to get image IDs
        response = client.get("/api/v1/dataset/frame-samples?split=product&dataset=nuscenes")
        if response.status_code != 200:
            print("Failed to fetch samples:", response.status_code, response.text)
            return
        data = response.json()
        image_ids = []
        for item in data.get("results", []):
            for cam in item.get("cameras", []):
                image_ids.append(cam["id"])
        
        if not image_ids:
            print("No image IDs found")
            return
            
        print(f"Found {len(image_ids)} images.")
        
        # 2. Benchmark full image
        latencies = []
        for i, img_id in enumerate(image_ids[:20]):
            start = time.perf_counter()
            resp = client.get(f"/api/v1/dataset/images/product/{img_id}/content")
            end = time.perf_counter()
            if resp.status_code == 200:
                latencies.append((end - start)*1000)
            else:
                print(f"Failed to fetch {img_id}:", resp.status_code, resp.text)
        
        if latencies:
            import statistics
            print("--- FULL IMAGE BENCHMARK ---")
            print(f"Mean: {statistics.mean(latencies):.2f} ms")
            print(f"p50: {statistics.median(latencies):.2f} ms")
            if len(latencies) >= 2:
                print(f"p95: {statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 100 else sorted(latencies)[int(len(latencies)*0.95)]:.2f} ms")
                
        # 3. Benchmark thumbnail
        latencies_thumb = []
        for i, img_id in enumerate(image_ids[:20]):
            start = time.perf_counter()
            resp = client.get(f"/api/v1/dataset/images/product/{img_id}/content?size=thumbnail")
            end = time.perf_counter()
            if resp.status_code == 200:
                latencies_thumb.append((end - start)*1000)
                
        if latencies_thumb:
            print("--- THUMBNAIL BENCHMARK ---")
            print(f"Mean: {statistics.mean(latencies_thumb):.2f} ms")
            print(f"p50: {statistics.median(latencies_thumb):.2f} ms")

run_benchmark()
