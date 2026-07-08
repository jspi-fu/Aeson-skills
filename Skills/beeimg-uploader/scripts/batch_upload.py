#!/usr/bin/env python3
"""Batch image uploader - scan a local directory for images and upload them to BeeImg, returning public URLs.

BeeImg rate limits:
  - Max file size: 10 MB
  - Max concurrency: 10
  - Max uploads per minute: 20
  - Max uploads per hour: 100
"""

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from coze_workload_identity import requests

BEEIMG_UPLOAD_URL = "https://www.beeimg.cn/api/v2/upload"
DEFAULT_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "tiff", "tif"}

# BeeImg platform limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_CONCURRENCY = 10
RATE_LIMIT_PER_MINUTE = 20
RATE_LIMIT_PER_HOUR = 100


class RateLimiter:
    """Thread-safe rate limiter tracking upload timestamps."""

    def __init__(self, per_minute, per_hour):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.timestamps = []
        self.lock = threading.Lock()

    def acquire(self):
        """Block until an upload slot is available. Returns True if acquired, False if hourly limit reached."""
        while True:
            with self.lock:
                now = time.time()
                # Clean old timestamps
                self.timestamps = [t for t in self.timestamps if now - t < 3600]

                # Check hourly limit
                if len(self.timestamps) >= self.per_hour:
                    return False

                # Check per-minute limit
                recent = [t for t in self.timestamps if now - t < 60]
                if len(recent) < self.per_minute:
                    self.timestamps.append(now)
                    return True

                # Need to wait until the oldest recent timestamp expires
                wait_time = 60 - (now - recent[0]) + 0.1
            time.sleep(max(0.1, wait_time))

    def get_stats(self):
        """Return current upload counts."""
        with self.lock:
            now = time.time()
            self.timestamps = [t for t in self.timestamps if now - t < 3600]
            minute_count = len([t for t in self.timestamps if now - t < 60])
            hour_count = len(self.timestamps)
        return {"minute_count": minute_count, "hour_count": hour_count}


def scan_images(directory, recursive, extensions, max_file_size):
    """Scan directory for image files within size limit, returning (valid_paths, skipped_files)."""
    image_paths = []
    skipped = []
    if recursive:
        for root, _dirs, files in os.walk(directory):
            for fname in sorted(files):
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                if ext in extensions:
                    fpath = os.path.join(root, fname)
                    fsize = os.path.getsize(fpath)
                    if fsize > max_file_size:
                        skipped.append({
                            "filename": fname,
                            "error": f"File size {fsize / (1024*1024):.2f} MB exceeds limit of {max_file_size / (1024*1024):.0f} MB",
                        })
                    elif fsize == 0:
                        skipped.append({"filename": fname, "error": "File is empty (0 bytes)"})
                    else:
                        image_paths.append(fpath)
    else:
        for fname in sorted(os.listdir(directory)):
            fpath = os.path.join(directory, fname)
            if os.path.isfile(fpath):
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                if ext in extensions:
                    fsize = os.path.getsize(fpath)
                    if fsize > max_file_size:
                        skipped.append({
                            "filename": fname,
                            "error": f"File size {fsize / (1024*1024):.2f} MB exceeds limit of {max_file_size / (1024*1024):.0f} MB",
                        })
                    elif fsize == 0:
                        skipped.append({"filename": fname, "error": "File is empty (0 bytes)"})
                    else:
                        image_paths.append(fpath)
    return image_paths, skipped


def upload_single(filepath, storage_id, timeout, rate_limiter, stop_flag):
    """Upload a single image file to BeeImg with rate limiting. Returns a result dict."""
    filename = os.path.basename(filepath)

    # Check if we should stop (hourly limit reached)
    if stop_flag.is_set():
        return {
            "file": filepath,
            "filename": filename,
            "status": "skipped",
            "error": "Hourly upload limit (100) reached, skipped",
            "public_url": None,
        }

    # Acquire rate limit slot
    acquired = rate_limiter.acquire()
    if not acquired:
        return {
            "file": filepath,
            "filename": filename,
            "status": "skipped",
            "error": "Hourly upload limit (100) reached",
            "public_url": None,
        }

    # Check stop flag again after waiting
    if stop_flag.is_set():
        return {
            "file": filepath,
            "filename": filename,
            "status": "skipped",
            "error": "Hourly upload limit (100) reached, skipped",
            "public_url": None,
        }

    try:
        with open(filepath, "rb") as f:
            files = {"file": (filename, f)}
            data = {"storage_id": str(storage_id)}
            headers = {"Accept": "application/json"}
            response = requests.post(
                BEEIMG_UPLOAD_URL,
                files=files,
                data=data,
                headers=headers,
                timeout=timeout,
            )

        if response.ok:
            resp_json = response.json()
            img_data = resp_json.get("data", {})
            return {
                "file": filepath,
                "filename": filename,
                "status": "success",
                "public_url": img_data.get("public_url", ""),
                "width": img_data.get("width"),
                "height": img_data.get("height"),
                "md5": img_data.get("md5", ""),
                "size_bytes": os.path.getsize(filepath),
            }
        else:
            # If we hit 429, signal other threads to slow down
            if response.status_code == 429:
                stop_flag.set()

            error_msg = f"HTTP {response.status_code}"
            try:
                err_body = response.json()
                error_msg += f": {err_body.get('message', response.reason)}"
            except (json.JSONDecodeError, ValueError):
                error_msg += f": {response.reason}"
            return {
                "file": filepath,
                "filename": filename,
                "status": "failed",
                "error": error_msg,
                "public_url": None,
            }

    except requests.exceptions.Timeout:
        return {
            "file": filepath,
            "filename": filename,
            "status": "failed",
            "error": f"Upload timed out after {timeout}s",
            "public_url": None,
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "file": filepath,
            "filename": filename,
            "status": "failed",
            "error": f"Connection error: {str(e)[:200]}",
            "public_url": None,
        }
    except requests.exceptions.RequestException as e:
        return {
            "file": filepath,
            "filename": filename,
            "status": "failed",
            "error": f"Request error: {str(e)[:200]}",
            "public_url": None,
        }
    except FileNotFoundError:
        return {
            "file": filepath,
            "filename": filename,
            "status": "failed",
            "error": "File not found",
            "public_url": None,
        }
    except Exception as e:
        return {
            "file": filepath,
            "filename": filename,
            "status": "failed",
            "error": f"Unexpected error: {str(e)[:200]}",
            "public_url": None,
        }


def main():
    parser = argparse.ArgumentParser(description="Batch image uploader for BeeImg")
    parser.add_argument("--dir", required=True, help="Directory path containing images to upload")
    parser.add_argument("--storage-id", type=int, default=1, help="BeeImg storage ID (default: 1)")
    parser.add_argument("--recursive", action="store_true", help="Recursively scan subdirectories")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="Number of concurrent uploads, max 10 (default: 5)")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Per-file upload timeout in seconds (default: 30)")
    parser.add_argument("--extensions", default=None,
                        help="Comma-separated image extensions (default: jpg,jpeg,png,gif,bmp,webp,svg,tiff,tif)")
    parser.add_argument("--max-file-size", type=int, default=MAX_FILE_SIZE,
                        help=f"Max file size in bytes (default: {MAX_FILE_SIZE}, 10MB)")

    args = parser.parse_args()

    # Validate directory
    if not os.path.isdir(args.dir):
        result = {
            "status": "error",
            "error_type": "invalid_directory",
            "error_message": f"Directory not found: {args.dir}",
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # Parse extensions
    if args.extensions:
        extensions = {ext.strip().lower().lstrip(".") for ext in args.extensions.split(",")}
    else:
        extensions = DEFAULT_EXTENSIONS

    # Clamp concurrency to platform limit
    concurrency = max(1, min(args.concurrency, MAX_CONCURRENCY))

    # Scan for images (with file size check)
    image_paths, size_skipped = scan_images(args.dir, args.recursive, extensions, args.max_file_size)

    total_scanned = len(image_paths) + len(size_skipped)

    if not image_paths and not size_skipped:
        result = {
            "status": "success",
            "total": 0,
            "success_count": 0,
            "fail_count": 0,
            "skipped_count": 0,
            "elapsed_time": 0,
            "results": [],
            "errors": [],
            "message": f"No image files found in {args.dir} (extensions: {', '.join(sorted(extensions))})",
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    if not image_paths and size_skipped:
        result = {
            "status": "success",
            "total": total_scanned,
            "success_count": 0,
            "fail_count": 0,
            "skipped_count": len(size_skipped),
            "elapsed_time": 0,
            "results": [],
            "errors": size_skipped,
            "message": "All files exceeded size limit or are empty",
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    # Initialize rate limiter and stop flag
    rate_limiter = RateLimiter(per_minute=RATE_LIMIT_PER_MINUTE, per_hour=RATE_LIMIT_PER_HOUR)
    stop_flag = threading.Event()

    # Upload images concurrently with rate limiting
    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_path = {
            executor.submit(upload_single, fpath, args.storage_id, args.timeout, rate_limiter, stop_flag): fpath
            for fpath in image_paths
        }
        for future in as_completed(future_to_path):
            result = future.result()
            results.append(result)

    elapsed = round(time.time() - start_time, 2)

    # Sort results by filename for consistent output
    results.sort(key=lambda r: r.get("filename", ""))

    # Categorize results
    successes = [r for r in results if r["status"] == "success"]
    failures = [r for r in results if r["status"] == "failed"]
    skipped = [r for r in results if r["status"] == "skipped"]

    # Combine all errors (size-skipped + upload failures + rate-limited skips)
    all_errors = size_skipped + [
        {"filename": r["filename"], "error": r["error"]}
        for r in failures + skipped
    ]

    # Get rate limiter stats
    rate_stats = rate_limiter.get_stats()

    output = {
        "status": "success",
        "total": total_scanned,
        "success_count": len(successes),
        "fail_count": len(failures),
        "skipped_count": len(skipped) + len(size_skipped),
        "elapsed_time": elapsed,
        "rate_limit": {
            "uploads_this_minute": rate_stats["minute_count"],
            "uploads_this_hour": rate_stats["hour_count"],
            "limits": {
                "per_minute": RATE_LIMIT_PER_MINUTE,
                "per_hour": RATE_LIMIT_PER_HOUR,
                "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
                "max_concurrency": MAX_CONCURRENCY,
            },
        },
        "results": [
            {
                "filename": r["filename"],
                "public_url": r["public_url"],
                "width": r.get("width"),
                "height": r.get("height"),
                "md5": r.get("md5", ""),
            }
            for r in successes
        ],
        "errors": all_errors,
    }

    # Add warning if hourly limit was reached
    if stop_flag.is_set():
        output["warning"] = "Hourly upload limit (100) was reached. Remaining files were skipped. Try again later."

    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
