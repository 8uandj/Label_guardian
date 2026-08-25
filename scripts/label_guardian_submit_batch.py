#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

def run_cmd(cmd: list[str]) -> None:
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main() -> None:
    print("=== GCP Batch Ingestion Submitter ===")
    dataset = ""
    while dataset not in ("nuscenes", "kitti"):
        dataset = input("Select dataset (nuscenes, kitti): ").strip().lower()

    count_str = ""
    count = 30
    while not count_str.isdigit():
        count_str = input("Number of data (frames/samples) to process [default 30]: ").strip()
        if not count_str:
            count = 30
            break
        if count_str.isdigit():
            count = int(count_str)
            break
        print("Please enter a valid number.")

    project_root = Path(__file__).resolve().parent.parent
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
        run_cmd(["gcloud", "storage", "cp", str(tmp_req), gcs_request_uri])

        print(f"\nSubmitting Batch Job: {job_name} ...")
        cmd = [
            "gcloud", "batch", "jobs", "submit", job_name,
            "--location", "asia-southeast1",
            "--config", str(tmp_batch),
            "--project", "ai-lab-16-gcp-505508"
        ]
        run_cmd(cmd)
        
    print("\nDone! Batch job submitted successfully.")
    print("Mọi thứ sẽ được cập nhật tự động vào thư mục product (quy ước mới)!")

if __name__ == "__main__":
    main()
