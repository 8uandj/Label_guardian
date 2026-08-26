import asyncio
import httpx
import time
import argparse
import json
import statistics

# Set this to the backend API base url for testing locally
BASE_URL = "http://127.0.0.1:8000/api/v1/dataset"

# Example images to test with
# You might need to change these to valid image IDs in your local DB
TEST_SPLIT = "product"
TEST_IMAGES = [] # Add real image IDs here when testing

async def fetch_image(client: httpx.AsyncClient, image_id: str, split: str = TEST_SPLIT):
    url = f"{BASE_URL}/images/{split}/{image_id}/content"
    start_time = time.perf_counter()
    response = await client.get(url, timeout=30.0)
    end_time = time.perf_counter()
    return response.status_code, (end_time - start_time) * 1000, len(response.content)

async def cold_benchmark():
    if not TEST_IMAGES:
        print("No TEST_IMAGES defined. Please populate.")
        return

    print(f"--- Cold Fetch Benchmark ({len(TEST_IMAGES)} distinct images) ---")
    async with httpx.AsyncClient() as client:
        latencies = []
        payloads = []
        success = 0
        for img_id in TEST_IMAGES:
            status, latency, size = await fetch_image(client, img_id)
            if status == 200:
                success += 1
                latencies.append(latency)
                payloads.append(size)
            else:
                print(f"Failed to fetch {img_id}: {status}")

    if latencies:
        print(f"Success rate: {success}/{len(TEST_IMAGES)}")
        print(f"Mean: {statistics.mean(latencies):.2f} ms")
        print(f"p50: {statistics.median(latencies):.2f} ms")
        print(f"p95: {statistics.quantiles(latencies, n=100)[94]:.2f} ms")
        print(f"p99: {statistics.quantiles(latencies, n=100)[98]:.2f} ms")
        print(f"Min: {min(latencies):.2f} ms")
        print(f"Max: {max(latencies):.2f} ms")
        print(f"Avg Payload size: {statistics.mean(payloads)/1024:.2f} KB")

async def warm_benchmark():
    if not TEST_IMAGES:
        return
    # use only 1 image, fetch it 100 times to see connection reuse
    img_id = TEST_IMAGES[0]
    print(f"\n--- Warm Fetch Benchmark (100 sequential requests for {img_id}) ---")
    
    latencies = []
    success = 0
    async with httpx.AsyncClient() as client:
        for _ in range(100):
            status, latency, _ = await fetch_image(client, img_id)
            if status == 200:
                success += 1
                latencies.append(latency)
                
    if latencies:
        print(f"Success rate: {success}/100")
        print(f"Mean: {statistics.mean(latencies):.2f} ms")
        print(f"p50: {statistics.median(latencies):.2f} ms")
        print(f"p95: {statistics.quantiles(latencies, n=100)[94]:.2f} ms")
        print(f"p99: {statistics.quantiles(latencies, n=100)[98]:.2f} ms")

async def concurrent_benchmark(users=1):
    if not TEST_IMAGES:
        return
    print(f"\n--- Concurrent Fetch Benchmark ({users} users, 48 requests each) ---")
    requests_to_make = (TEST_IMAGES * 48)[:48] # Just pick first 48 or duplicate
    
    async def simulate_user(user_id):
        async with httpx.AsyncClient() as client:
            tasks = [fetch_image(client, img_id) for img_id in requests_to_make]
            return await asyncio.gather(*tasks)

    start_time = time.perf_counter()
    results = await asyncio.gather(*[simulate_user(i) for i in range(users)])
    end_time = time.perf_counter()

    latencies = []
    success = 0
    total_requests = 0
    for user_result in results:
        for status, latency, _ in user_result:
            total_requests += 1
            if status == 200:
                success += 1
                latencies.append(latency)

    duration = end_time - start_time
    if latencies:
        print(f"Total time: {duration:.2f} s")
        print(f"Throughput: {total_requests / duration:.2f} req/s")
        print(f"Success rate: {success}/{total_requests}")
        print(f"p50: {statistics.median(latencies):.2f} ms")
        print(f"p95: {statistics.quantiles(latencies, n=100)[94]:.2f} ms")
        print(f"p99: {statistics.quantiles(latencies, n=100)[98]:.2f} ms")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auth-token', help="Auth token if needed")
    args = parser.parse_args()

    # In a real run we should fetch valid image IDs from the DB or an endpoint.
    
    # We will just run them if TEST_IMAGES are populated
    await cold_benchmark()
    await warm_benchmark()
    await concurrent_benchmark(users=1)
    await concurrent_benchmark(users=5)
    await concurrent_benchmark(users=10)

if __name__ == "__main__":
    asyncio.run(main())
