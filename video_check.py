import subprocess
import os
import sys

def check_faststart(path):
    """
    Check if MP4 has 'moov' atom at beginning (faststart) or end.
    Returns: (is_faststart: bool, message: str)
    """
    try:
        # Run ffprobe with trace log to see atom order
        result = subprocess.run(
            ["ffprobe", "-v", "trace", "-i", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        log = result.stderr  # ffprobe trace writes to stderr
        # Look for 'moov' atom position
        lines = [line for line in log.splitlines() if "moov," in line or "moov " in line]
        if not lines:
            return False, "❌ No 'moov' atom found (file may be corrupted)"

        # If 'moov' appears only at the end → not faststart
        first_occurrence = lines[0]
        last_occurrence = lines[-1]

        if len(lines) == 1 and "moov," in first_occurrence:
            # If moov shows only once → check offset
            if "start:" in first_occurrence:
                # Example line: "[mov,mp4,...] type:'moov' size:1234 start:5678"
                try:
                    start = int(first_occurrence.split("start:")[1].split()[0])
                    if start < 100000:  # moov near start of file
                        return True, "✅ Faststart OK (moov atom at beginning)"
                    else:
                        return False, "⚠️ moov atom at end (not faststart, may break in Chrome)"
                except:
                    pass

        return False, "⚠️ moov atom likely at end (not faststart)"
    except Exception as e:
        return False, f"❌ Error: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_faststart.py file1.mp4 [file2.mp4 ...]")
        sys.exit(1)

    for f in sys.argv[1:]:
        if not os.path.exists(f):
            print(f"{f}: ❌ File not found")
            continue
        ok, msg = check_faststart(f)
        print(f"{f}: {msg}")

