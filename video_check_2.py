import os
import re
import sys
import subprocess

MOOV_RE = re.compile(r"type:'moov'.*?sz:\s*(\d+)\s+(\d+)\s+(\d+)")
MOOF_RE = re.compile(r"type:'moof'")

def check_faststart(path):
    """
    Uses `ffprobe -v trace` to locate the 'moov' atom.
    Returns a dict with fields:
      ok, faststart, moov_start, moov_size, moov_end, file_size, reason
    """
    p = subprocess.run(
        ["ffprobe", "-hide_banner", "-v", "trace", "-i", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    log = p.stderr
    fsize = os.path.getsize(path)

    moov = MOOV_RE.search(log)
    if not moov:
        if MOOF_RE.search(log):
            return {
                "ok": False,
                "faststart": False,
                "moov_start": None,
                "moov_size": None,
                "moov_end": None,
                "file_size": fsize,
                "reason": "No 'moov' found; file appears to be fragmented (fMP4 with 'moof')."
            }
        return {
            "ok": False,
            "faststart": False,
            "moov_start": None,
            "moov_size": None,
            "moov_end": None,
            "file_size": fsize,
            "reason": "No 'moov' atom found."
        }

    moov_size, moov_start, moov_end = map(int, moov.groups())

    # Heuristics: moov near start if within 256 KiB or within first 5% of file.
    near_start = (moov_start < 256 * 1024) or (moov_start <= fsize * 0.05)
    near_end = abs(fsize - moov_end) < 256 * 1024 or (moov_end >= fsize * 0.95)

    reason = "moov near beginning" if near_start else ("moov near end" if near_end else "moov in middle")

    return {
        "ok": True,
        "faststart": near_start,
        "moov_start": moov_start,
        "moov_size": moov_size,
        "moov_end": moov_end,
        "file_size": fsize,
        "reason": reason,
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_faststart.py file1.mp4 [file2.mp4 ...]")
        sys.exit(1)

    for path in sys.argv[1:]:
        if not os.path.exists(path):
            print(f"{path}: ❌ file not found")
            continue
        info = check_faststart(path)
        if not info["ok"]:
            print(f"{path}: ❌ {info['reason']}")
            continue
        pct = (info["moov_start"] / info["file_size"]) * 100 if info["file_size"] else 0
        status = "✅ FASTSTART" if info["faststart"] else "⚠️ NOT FASTSTART"
        print(
            f"{path}: {status} — {info['reason']} "
            f"(moov_start={info['moov_start']} / {info['file_size']} bytes, {pct:.2f}%)"
        )

