import os
import sys
import time
import json
import logging
import io
import requests

# 强制将 Windows / PowerShell 标准输出和标准错误输出重置为 UTF-8 编码，彻底消除 GBK 转换异常
if sys.platform == "win32":
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("gh-star-manager")

def safe_load_json(file_path):
    """Safely load JSON file handling various encodings (utf-8, utf-8-sig, utf-16) and control characters."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    encoding = "utf-8"
    if raw_bytes.startswith(b"\xff\xfe") or raw_bytes.startswith(b"\xfe\xff"):
        encoding = "utf-16"
    elif raw_bytes.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"

    text = raw_bytes.decode(encoding, errors="replace")
    return json.loads(text, strict=False)

def safe_save_json(file_path, data, indent=2):
    """Safely save JSON file strictly in UTF-8 without BOM."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def _env_file_candidates():
    """Ordered list of .env locations to consult (first hit wins per-key)."""
    candidates = []
    # 0) Explicit override: let the host (e.g. WorkBuddy) point at any managed secret file.
    explicit = os.getenv("GH_STAR_MANAGER_ENV")
    if explicit:
        candidates.append(explicit)
    # 1) User-level config dir: travels with the user across every workspace/project.
    candidates.append(os.path.join(os.path.expanduser("~"), ".gh-star-manager", ".env"))
    # 2) Legacy skill-dir .env: kept only for backward compatibility.
    candidates.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    return candidates


def load_dotenv():
    """Load config from a cascade of .env locations.

    Resolution priority (highest wins), applied per-key:
      1. Process environment already set (e.g. WorkBuddy-managed secrets / shell env).
         These are NEVER overwritten by file values.
      2. GH_STAR_MANAGER_ENV  -> explicit .env path supplied by the host.
      3. ~/.gh-star-manager/.env  -> user-level, portable across workspaces.
      4. <skill-dir>/.env  -> legacy location (backward compatible).

    Because existing os.environ values are preserved, a token injected by
    WorkBuddy (or the user's shell) always takes precedence over any file,
    which is what lets the skill run freely without a bundled .env.
    """
    for path in _env_file_candidates():
        if not path or not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except Exception as e:
            logger.warning(f"Failed to load env file {path}: {e}")


# Auto-load on import so every entry script (which imports utils) inherits the
# same cascade without needing to call load_dotenv() explicitly.
load_dotenv()


import subprocess

def get_github_token():
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    # Fallback to GitHub CLI token if `gh` is installed and authenticated
    try:
        res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            fetched_token = res.stdout.strip()
            os.environ["GITHUB_TOKEN"] = fetched_token
            logger.info("Successfully fetched GITHUB_TOKEN from GitHub CLI (`gh auth token`)")
            return fetched_token
    except Exception:
        pass

    print(json.dumps({
        "status": "error",
        "message": (
            "Missing GITHUB_TOKEN. Resolution order: "
            "(1) environment variable GITHUB_TOKEN (set by WorkBuddy/shell), "
            "(2) GH_STAR_MANAGER_ENV path, "
            "(3) ~/.gh-star-manager/.env, "
            "(4) <skill-dir>/.env, "
            "(5) GitHub CLI (`gh auth token`). "
            "To fix, run `gh auth login` in terminal, set GITHUB_TOKEN in your shell/WorkBuddy env, "
            "or create ~/.gh-star-manager/.env with GITHUB_TOKEN=ghp_xxx"
        )
    }), file=sys.stderr)
    sys.exit(1)


def get_organize_mode():
    mode = os.getenv("STARS_ORGANIZE_MODE", "moderate").lower().strip()
    if mode not in ("conservative", "moderate", "aggressive"):
        logger.warning(f"Unknown STARS_ORGANIZE_MODE '{mode}', defaulting to 'moderate'")
        return "moderate"
    return mode

def get_workdir():
    """Dedicated working directory for all session artifacts.

    Lives outside the user's project (defaults to ~/.gh-star-manager) so the
    skill never litters the workspace it runs in. Override with
    GH_STAR_MANAGER_WORKDIR to point at any WorkBuddy-managed location.
    """
    workdir = os.environ.get("GH_STAR_MANAGER_WORKDIR") or os.path.join(
        os.path.expanduser("~"), ".gh-star-manager"
    )
    try:
        os.makedirs(workdir, exist_ok=True)
    except Exception:
        pass
    return workdir


def cleanup_session_temp_files():
    """清除分类会话产生的所有临时中间产物与本地临时 stars 状态。

    同时清理专用工作目录（默认 ~/.gh-star-manager）与当前目录（历史遗留兼容），
    避免把产物残留在用户项目里。
    """
    workdir = get_workdir()
    temp_files = [
        "stars.json",
        "lists.json",
        "lists_with_items.json",
        "current_lists_with_items.json",
        "review_plan.json",
        "review_plan_saved.json",
        "insights.json",
        "new_repos.json",
        "set_lists.json",
        "unstar_repos.json",
        "review.html",
        "scratch_inspect.py",
        "scratch_schema.py"
    ]
    cleaned = []
    # 优先清理专用工作目录；同时兼容旧逻辑（产物写在 cwd 的情况）。
    for base in (workdir, "."):
        for f in temp_files:
            p = os.path.join(base, f)
            if os.path.exists(p):
                try:
                    os.remove(p)
                    cleaned.append(p)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {p}: {e}")

    # Remove local stars state file (usually already inside workdir).
    stars_state_file = os.path.join(workdir, "stars_state.json")
    if os.path.exists(stars_state_file):
        try:
            os.remove(stars_state_file)
            cleaned.append(stars_state_file)
        except Exception:
            pass
    logger.info(f"已清理中间产物文件: {cleaned}")
    return cleaned



def make_github_request(url, method="GET", headers=None, json_data=None, params=None, max_retries=3):
    token = get_github_token()
    req_headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "gh-star-manager-skill"
    }
    if headers:
        req_headers.update(headers)

    for attempt in range(max_retries):
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=req_headers,
                json=json_data,
                params=params,
                timeout=30
            )
            if resp.status_code in (403, 429):
                if attempt == max_retries - 1:
                    resp.raise_for_status()
                retry_after = resp.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after else (2 ** attempt) + 1
                logger.warning(f"Rate limited (status {resp.status_code}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep((2 ** attempt) + 1)
    raise Exception(f"Failed request to {url} after {max_retries} retries.")
