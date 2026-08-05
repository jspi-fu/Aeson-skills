import json
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import make_github_request, safe_save_json, logger

STAR_ACCEPT = "application/vnd.github.star+json"



def extract_repo(item):
    """从 starred 列表条目提取分析所需字段。"""
    repo = item.get("repo", {})
    return {
        "full_name": repo.get("full_name"),
        "node_id": repo.get("node_id"),
        "description": repo.get("description"),
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "stargazers_count": repo.get("stargazers_count", 0),
        "pushed_at": repo.get("pushed_at"),
        "archived": repo.get("archived", False),
        "fork": repo.get("fork", False),
        "starred_at": item.get("starred_at"),
    }


def parse_last_page(link_header):
    """从 Link 头解析末页页码,解析失败返回 1。"""
    if not link_header:
        return 1
    for part in link_header.split(","):
        if 'rel="last"' in part and "page=" in part:
            try:
                url_part = part.split(";")[0].strip().strip("<>")
                return int(url_part.split("page=")[1].split("&")[0])
            except (IndexError, ValueError):
                pass
    return 1


def fetch_stars_page(page, per_page=100):
    url = f"https://api.github.com/user/starred?page={page}&per_page={per_page}"
    resp = make_github_request(url, headers={"Accept": STAR_ACCEPT})
    return [extract_repo(item) for item in resp.json()]


def fetch_all_stars(max_count=None):
    errors = []
    resp = make_github_request(
        "https://api.github.com/user/starred?page=1&per_page=100",
        headers={"Accept": STAR_ACCEPT},
    )
    all_repos = [extract_repo(item) for item in resp.json()]
    last_page = parse_last_page(resp.headers.get("Link", ""))

    if last_page > 1:
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_page = {
                executor.submit(fetch_stars_page, page): page
                for page in range(2, last_page + 1)
            }
            for future in as_completed(future_to_page):
                try:
                    all_repos.extend(future.result())
                except Exception as e:
                    errors.append(str(e))
                    logger.error(f"Error fetching page: {e}")
        if errors:
            logger.warning(f"{len(errors)} 个分页拉取失败,结果不完整。建议重试。")

    if max_count:
        all_repos = all_repos[:max_count]

    result = {"status": "success", "total": len(all_repos), "repos": all_repos}
    if errors:
        result["warnings"] = [f"{len(errors)} pages failed to fetch; data may be incomplete"]
    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch starred repositories")
    parser.add_argument("--max-count", type=int, default=None, help="Maximum number of repos to fetch")
    parser.add_argument("--sync", action="store_true",
                        help="Sync ~/.gh-star-manager/stars_state.json and user profile stats, print diff")
    parser.add_argument("-o", "--output-file", help="Save output JSON to file directly without redirection")
    args = parser.parse_args()

    result = fetch_all_stars(max_count=args.max_count)
    if args.sync:
        from state import update_stars_state, update_observed_stats
        update_observed_stats(result["repos"])
        result["sync_diff"] = update_stars_state(result["repos"])
    if args.output_file:
        safe_save_json(args.output_file, result)
        logger.info(f"Saved stars result to {args.output_file}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("warnings"):
        sys.exit(2)



if __name__ == "__main__":
    main()
