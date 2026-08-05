"""为批量导入的 repo 抓取 README 摘要与近期 issues,供 agent 判断匹配度与归类理由。

用法:
    python scripts/repo_insight.py --input-file new_repos.json
输入文件: ["owner/repo1", "owner/repo2", ...]
每个 repo 产出: 基础信息 + README 开头(截断) + 最近 N 个 open issues 标题。
README 与 issues 抓取失败只记 warning,不中断整体流程。
"""
import json
import time
import argparse
from utils import make_github_request, safe_load_json, safe_save_json, logger

README_CHARS = 2000
ISSUES_COUNT = 5


def clean_name(name):
    return name.replace("https://github.com/", "").strip("/")


def fetch_repo(full_name):
    resp = make_github_request(f"https://api.github.com/repos/{full_name}")
    repo = resp.json()
    return {
        "full_name": repo.get("full_name"),
        "node_id": repo.get("node_id"),
        "description": repo.get("description"),
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "stargazers_count": repo.get("stargazers_count", 0),
        "open_issues_count": repo.get("open_issues_count", 0),
        "pushed_at": repo.get("pushed_at"),
        "archived": repo.get("archived", False),
        "fork": repo.get("fork", False),
    }


def fetch_readme_excerpt(full_name):
    """优先 README API(自动处理编码),失败回退 raw 端点;只取开头 N 字符。"""
    try:
        resp = make_github_request(f"https://api.github.com/repos/{full_name}/readme")
        data = resp.json()
        if data.get("encoding") == "base64":
            import base64
            text = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
            return text[:README_CHARS]
        return None
    except Exception:
        pass
    for host in ("https://raw.githubusercontent.com",):
        for branch in ("main", "master"):
            for fname in ("README.md", "README.rst", "README"):
                try:
                    resp = make_github_request(f"{host}/{full_name}/{branch}/{fname}")
                    return resp.text[:README_CHARS]
                except Exception:
                    continue
    return None


def fetch_recent_issues(full_name):
    resp = make_github_request(
        f"https://api.github.com/repos/{full_name}/issues",
        params={"state": "open", "sort": "created", "direction": "desc",
                "per_page": ISSUES_COUNT},
    )
    return [
        {"title": i.get("title"), "labels": [l.get("name") for l in i.get("labels", [])]}
        for i in resp.json() if "pull_request" not in i
    ][:ISSUES_COUNT]


def build_insight(name):
    full_name = clean_name(name)
    entry = {"repo": full_name, "warnings": []}
    try:
        entry.update(fetch_repo(full_name))
    except Exception as e:
        entry["warnings"].append(f"repo fetch failed: {e}")
        return entry

    try:
        excerpt = fetch_readme_excerpt(full_name)
        entry["readme_excerpt"] = excerpt or ""
        if not excerpt:
            entry["warnings"].append("no readme found")
    except Exception as e:
        entry["warnings"].append(f"readme failed: {e}")

    try:
        entry["recent_issues"] = fetch_recent_issues(full_name)
    except Exception as e:
        entry["recent_issues"] = []
        entry["warnings"].append(f"issues failed: {e}")

    return entry


def main():
    parser = argparse.ArgumentParser(description="Fetch repo insights for import review")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("-o", "--output-file", help="Save output JSON to file directly without redirection")
    args = parser.parse_args()

    names = safe_load_json(args.input_file)

    insights = []
    for name in names:
        insights.append(build_insight(name))
        time.sleep(0.3)

    res = {"status": "success", "insights": insights}
    if args.output_file:
        safe_save_json(args.output_file, res)
        logger.info(f"Saved repo insights to {args.output_file}")
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

