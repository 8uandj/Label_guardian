#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import re
from datetime import datetime
from pathlib import Path

try:
    import psycopg
    from dotenv import dotenv_values
except ImportError:
    psycopg = None

def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)

def get_stats(dataset: str, project_root: Path) -> tuple[int, int, int]:
    # 1. Total size
    total = 7481 if dataset == "kitti" else 34149
    
    # 2. Ingested size
    ingested = 0
    if psycopg:
        env = dotenv_values(project_root / ".env")
        db_url = env.get("LABEL_GUARDIAN_DATABASE_URL")
        if db_url:
            try:
                with psycopg.connect(db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT COUNT(*) FROM qa_images WHERE release = 'product' AND dataset = %s", (dataset,))
                        row = cur.fetchone()
                        if row:
                            ingested = row[0]
                            if dataset == "nuscenes":
                                ingested = ingested // 6
            except Exception as e:
                print(f"Warning: Could not query database: {e}")
    else:
        print("Warning: psycopg not installed. Cannot query database for ingested count.")

    # 3. Running size
    running = 0
    try:
        res = subprocess.run([
            "gcloud", "batch", "jobs", "list", 
            "--project", "ai-lab-16-gcp-505508", 
            "--format=json"
        ], capture_output=True, text=True, check=True)
        jobs = json.loads(res.stdout)
        
        for job in jobs:
            state = job.get("status", {}).get("state", "")
            if state in ("QUEUED", "SCHEDULED", "RUNNING"):
                name = job.get("name", "")
                # Job name format: projects/.../jobs/label-guardian-{dataset}-{count}-{timestamp}
                match = re.search(fr"label-guardian-{dataset}-(\d+)-\d+", name)
                if match:
                    running += int(match.group(1))
    except Exception as e:
        print(f"Warning: Could not fetch running batch jobs: {e}")
        
    return total, ingested, running

def main() -> None:
    print("=== GCP Batch Ingestion Submitter ===")
    dataset = ""
    while dataset not in ("nuscenes", "kitti"):
        dataset = input("Select dataset (nuscenes, kitti): ").strip().lower()

    project_root = Path(__file__).resolve().parent.parent

    print(f"\nĐang quét dữ liệu thống kê cho {dataset.upper()}...")
    total, ingested, running = get_stats(dataset, project_root)
    remaining = max(0, total - ingested - running)
    
    print("-" * 40)
    print(f"Thống kê dữ liệu {dataset.upper()}:")
    print(f"  - Tổng quy mô Dataset: {total} frames/samples")
    print(f"  - Đã có trong Database : {ingested}")
    print(f"  - Đang chạy trên Batch : {running}")
    print(f"  - CÒN LẠI CÓ THỂ CHẠY  : {remaining}")
    print("-" * 40)

    count_str = ""
    count = remaining
    while not count_str.isdigit():
        count_str = input(f"Number of data (frames/samples) to process [default {remaining}]: ").strip()
        if not count_str:
            count = remaining
            break
        if count_str.isdigit():
            count = int(count_str)
            break
        print("Please enter a valid number.")

    deploy_dir = project_root / "deploy" / "gcp"
    
    if dataset == "nuscenes":
        req_template_path = deploy_dir / "request-nuscenes-trainval-30.json"
        batch_template_path = deploy_dir / "batch-nuscenes-trainval-30.json"
    else:
        req_template_path = deploy_dir / "request-kitti-smoke.json"
        batch_template_path = deploy_dir / "batch-kitti-smoke.json"

    with open(req_template_path, "r", encoding="utf-8") as f:
        req_data = json.load(f)
    
    with open(batch_template_path, "r", encoding="utf-8") as f:
        batch_data = json.load(f)

    # Update request
    run_id = f"{dataset}-{count}"
    req_data["max_frames"] = count
    req_data["run_id"] = run_id
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    job_name = f"label-guardian-{dataset}-{count}-{timestamp}"
    gcs_request_uri = f"gs://label_guardian_bucket/ops/ingestion-runs/{run_id}/request.json"

    # Update batch config (update the command arguments to point to the new GCS URI)
    container = batch_data["taskGroups"][0]["taskSpec"]["runnables"][0]["container"]
    commands = container["commands"]
    try:
        uri_idx = commands.index("--request-gcs-uri") + 1
        commands[uri_idx] = gcs_request_uri
    except ValueError:
        print("Error: Could not find --request-gcs-uri in batch template commands.")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        tmp_req = tmp_dir / "request.json"
        tmp_batch = tmp_dir / "batch.json"

        with open(tmp_req, "w", encoding="utf-8") as f:
            json.dump(req_data, f, indent=2)
        with open(tmp_batch, "w", encoding="utf-8") as f:
            json.dump(batch_data, f, indent=2)
        
        print(f"\nUploading request JSON to {gcs_request_uri} ...")
        run_cmd(["gcloud", "storage", "cp", str(tmp_req), gcs_request_uri], check=True)

        print(f"\nSubmitting Batch Job: {job_name} ...")
        cmd = [
            "gcloud", "batch", "jobs", "submit", job_name,
            "--location", "asia-southeast1",
            "--config", str(tmp_batch),
            "--project", "ai-lab-16-gcp-505508"
        ]
        run_cmd(cmd, check=True)
        
    print("\nDone! Batch job submitted successfully.")
    print("Mọi thứ sẽ được cập nhật tự động vào thư mục product (quy ước mới)!")

if __name__ == "__main__":
    main()
