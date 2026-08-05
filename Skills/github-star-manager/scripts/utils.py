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


def load_dotenv():
    """Load .env exclusively from the skill directory, overriding system environment variables."""
    skill_dir_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(skill_dir_env):
        try:
            with open(skill_dir_env, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        os.environ[k] = v
        except Exception as e:
            logger.warning(f"Failed to load env file {skill_dir_env}: {e}")

def get_github_token():
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print(json.dumps({
            "status": "error",
            "message": "Missing GITHUB_TOKEN environment variable. Please set GITHUB_TOKEN in your environment or .env file."
        }), file=sys.stderr)
        sys.exit(1)
    return token

def get_organize_mode():
    load_dotenv()
    mode = os.getenv("STARS_ORGANIZE_MODE", "moderate").lower().strip()
    if mode not in ("conservative", "moderate", "aggressive"):
        logger.warning(f"Unknown STARS_ORGANIZE_MODE '{mode}', defaulting to 'moderate'")
        return "moderate"
    return mode

def cleanup_session_temp_files():
    """清除分类会话产生的所有临时中间产物与本地临时 stars 状态。"""
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
    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
                cleaned.append(f)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {f}: {e}")

    # Remove local stars state file (~/.gh-star-manager/stars_state.json)
    stars_state_file = os.path.expanduser("~/.gh-star-manager/stars_state.json")
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
