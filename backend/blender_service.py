"""Blender headless conversion service — DAE/OBJ/FBX/STL/PLY → GLB.

Runs Blender as a subprocess. Returns the path to the produced .glb on
success, or raises with a captured error message on failure.

Why no .skp?  SketchUp does not ship a Linux SDK so Blender cannot import
SketchUp files on our server. Architects export Collada (.dae) from SketchUp
Desktop — that DAE is what we accept and auto-convert here.
"""
from __future__ import annotations
import asyncio
import os
import shutil
from pathlib import Path

BLENDER_BIN = shutil.which("blender") or "/usr/bin/blender"
SCRIPT = Path(__file__).parent / "blender_convert.py"

SUPPORTED_EXTS = {".dae", ".obj", ".fbx", ".stl", ".ply", ".gltf", ".glb"}


def is_enabled() -> bool:
    return bool(BLENDER_BIN and os.path.isfile(BLENDER_BIN) and SCRIPT.is_file())


async def convert_to_glb(input_path: str, output_path: str, timeout_sec: int = 600) -> dict:
    """Run Blender headless to convert *input_path* into a .glb at *output_path*.

    Returns: { ok, bytes_written, stdout, stderr, exit_code }
    Raises RuntimeError when Blender exits non-zero or output is missing.
    """
    if not is_enabled():
        raise RuntimeError("Blender is not available on this server.")
    if not os.path.isfile(input_path):
        raise RuntimeError(f"Source file not found: {input_path}")
    ext = os.path.splitext(input_path)[1].lower()
    if ext not in SUPPORTED_EXTS:
        raise RuntimeError(
            f"Format {ext} nu este suportat de Blender pe Linux. "
            f"Suportate: {', '.join(sorted(SUPPORTED_EXTS))}. "
            f"Dacă ai un .skp, exportă-l din SketchUp ca .dae (File → Export → COLLADA)."
        )
    cmd = [BLENDER_BIN, "--background", "--python", str(SCRIPT), "--", input_path, output_path]
    # Pass an explicit env so Blender's bundled Python finds numpy + other deps
    # installed in our backend venv (otherwise the gltf exporter crashes with
    # ModuleNotFoundError under asyncio subprocess).
    env = os.environ.copy()
    extra_paths = [
        "/root/.venv/lib/python3.11/site-packages",
        "/usr/local/lib/python3.11/site-packages",
    ]
    cur_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = ":".join([p for p in extra_paths if os.path.isdir(p)] + ([cur_pp] if cur_pp else []))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        out_bytes, err_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
    except asyncio.TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"Blender timeout după {timeout_sec}s") from exc
    stdout = (out_bytes or b"").decode("utf-8", errors="replace")
    stderr = (err_bytes or b"").decode("utf-8", errors="replace")
    rc = proc.returncode or 0
    if rc != 0:
        # Try to surface the most useful error line.
        msg = next((ln for ln in stdout.splitlines() if "ERROR" in ln), None) or stderr.strip().split("\n")[-1]
        # Log full output for diagnosis
        import logging as _lg
        _lg.getLogger("propmanage.blender").error(
            f"Blender exit={rc}\n=== STDOUT ===\n{stdout}\n=== STDERR ===\n{stderr}"
        )
        raise RuntimeError(f"Blender exit={rc}: {msg}")
    if not os.path.isfile(output_path):
        raise RuntimeError("Blender returned OK but no .glb was produced.")
    return {
        "ok": True,
        "bytes_written": os.path.getsize(output_path),
        "stdout": stdout[-2000:],  # tail only
        "stderr": stderr[-1000:],
        "exit_code": rc,
    }
