"""CloudConvert API v2 — async client for SKP → GLB conversion.

Used by routes/digital_twin.py to automatically convert SketchUp files
(uploaded as .skp archives) into .glb files that can be rendered in the
browser by Three.js.

Pipeline:
  1. create_skp_to_glb_job() — creates a CloudConvert job with 3 tasks:
       import/upload → convert (skp→glb) → export/url
  2. upload_file_for_import_task() — POSTs the .skp file to the import URL.
  3. get_job(id) — polled to check status (waiting / processing / finished / error).
  4. extract_export_file_url() — pulls the download URL from a finished job.
  5. download_file() — streams the .glb back to local disk.

API key lives in backend/.env as CLOUDCONVERT_API_KEY (JWT bearer token,
with scopes user.read / task.read / task.write).
"""
from __future__ import annotations
import os
from typing import Any, Tuple

import httpx

BASE_URL = os.environ.get("CLOUDCONVERT_BASE_URL", "https://api.cloudconvert.com/v2")
API_KEY = os.environ.get("CLOUDCONVERT_API_KEY") or ""


def _headers_json() -> dict:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def _headers_auth_only() -> dict:
    return {"Authorization": f"Bearer {API_KEY}"}


def is_enabled() -> bool:
    """True if the integration is configured (API key set)."""
    return bool(API_KEY)


async def create_skp_to_glb_job() -> dict[str, Any]:
    """Create a 3-task CloudConvert job: import/upload → convert(skp→glb) → export/url."""
    if not API_KEY:
        raise RuntimeError("CLOUDCONVERT_API_KEY not configured.")
    payload = {
        "tasks": {
            "import-skp": {"operation": "import/upload"},
            "convert-skp-to-glb": {
                "operation": "convert",
                "input": "import-skp",
                "input_format": "skp",
                "output_format": "glb",
            },
            "export-glb": {
                "operation": "export/url",
                "input": "convert-skp-to-glb",
                "inline": False,
                "archive_multiple_files": False,
            },
        },
        "tag": "propmanage-skp-to-glb",
    }
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        r = await client.post("/jobs", json=payload, headers=_headers_json())
        r.raise_for_status()
        return r.json()["data"]


async def get_job(job_id: str) -> dict[str, Any]:
    """Fetch a CloudConvert job by ID."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        r = await client.get(f"/jobs/{job_id}", headers=_headers_auth_only())
        r.raise_for_status()
        return r.json()["data"]


async def upload_file_for_import_task(job: dict[str, Any], file_path: str, filename: str) -> None:
    """POST the local .skp file to the import/upload task's URL using its signed form."""
    import_task = next((t for t in job.get("tasks", []) if t.get("operation") == "import/upload"), None)
    if import_task is None or not import_task.get("result", {}).get("form"):
        raise RuntimeError("Import/upload form not present in job (CloudConvert returned empty form).")
    form = import_task["result"]["form"]
    url = form["url"]
    parameters: dict[str, str] = form.get("parameters", {}) or {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(file_path, "rb") as f:
            data = {k: (None, str(v)) for k, v in parameters.items()}
            files = {"file": (filename, f, "application/octet-stream")}
            r = await client.post(url, data=data, files=files)
            r.raise_for_status()


def extract_export_file_url(job: dict[str, Any]) -> Tuple[str, str]:
    """Return (download_url, filename) of the export/url task's first file."""
    export_task = next((t for t in job.get("tasks", []) if (t.get("operation") or "").startswith("export/url")), None)
    if export_task is None:
        raise RuntimeError("export/url task not found.")
    if export_task.get("status") != "finished":
        raise RuntimeError(f"export/url task not finished yet (status={export_task.get('status')}).")
    files = (export_task.get("result") or {}).get("files") or []
    if not files:
        raise RuntimeError("export/url has no files.")
    file_info = files[0]
    return file_info["url"], file_info.get("filename") or "model.glb"


def aggregate_job_status(job: dict[str, Any]) -> dict[str, Any]:
    """Summarize a CloudConvert job into a friendly status dict for the frontend."""
    cc_status = job.get("status") or "waiting"  # waiting / processing / finished / error
    tasks = job.get("tasks") or []
    # Pick the most informative task for progress reporting.
    convert_task = next((t for t in tasks if t.get("operation") == "convert"), None)
    convert_status = convert_task.get("status") if convert_task else None
    convert_pct = convert_task.get("percent") if convert_task else None
    err = None
    if cc_status == "error":
        # Find first failed task's error message
        failed = next((t for t in tasks if t.get("status") == "error"), None)
        if failed:
            err = failed.get("message") or failed.get("code") or "CloudConvert task failed"
    return {
        "cc_status": cc_status,
        "convert_status": convert_status,
        "convert_percent": convert_pct,
        "error_message": err,
    }


async def download_file(url: str, dest_path: str, chunk_size: int = 1024 * 1024) -> int:
    """Stream the converted .glb from CloudConvert's temporary URL to local disk.

    Returns total bytes written.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    total = 0
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as out:
                async for chunk in r.aiter_bytes(chunk_size=chunk_size):
                    if chunk:
                        out.write(chunk)
                        total += len(chunk)
    return total
