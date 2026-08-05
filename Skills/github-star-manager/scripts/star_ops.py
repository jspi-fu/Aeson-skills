import os
import sys
import time
import json
import argparse
from datetime import datetime
from utils import make_github_request, get_github_token, logger

BACKUP_DIR = os.path.expanduser("~/.github-stars-backup")

def get_current_user():
    resp = make_github_request("https://api.github.com/user")
    data = resp.json()
    return {
        "status": "success",
        "user": {
            "login": data.get("login"),
            "id": data.get("id"),
            "name": data.get("name")
        }
    }

def check_scopes():
    resp = make_github_request("https://api.github.com/user")
    scopes_header = resp.headers.get("X-OAuth-Scopes", "")
    scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]
    has_user = "user" in scopes
    has_public_repo = "public_repo" in scopes or "repo" in scopes
    has_read_user = "read:user" in scopes or "user" in scopes
    return {
        "status": "success",
        "scopes": scopes,
        "can_create_lists": has_user,
        "has_required_scopes": has_public_repo and has_read_user
    }

def star_repo(full_name):
    url = f"https://api.github.com/user/starred/{full_name}"
    make_github_request(url, method="PUT")
    return {"status": "success", "repo": full_name}

def unstar_repo(full_name):
    url = f"https://api.github.com/user/starred/{full_name}"
    make_github_request(url, method="DELETE")
    return {"status": "success", "repo": full_name}

def get_repo_details(full_name):
    url = f"https://api.github.com/repos/{full_name}"
    resp = make_github_request(url)
    repo = resp.json()
    return {
        "full_name": repo.get("full_name"),
        "node_id": repo.get("node_id"),
        "description": repo.get("description"),
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "stargazers_count": repo.get("stargazers_count", 0),
        "pushed_at": repo.get("pushed_at"),
        "archived": repo.get("archived", False),
        "fork": repo.get("fork", False)
    }

def batch_star_info(input_file=None, repo_names=None):
    if repo_names is None:
        with open(input_file, "r", encoding="utf-8") as f:
            repo_names = json.load(f)

    starred = []
    failed = []

    for name in repo_names:
        clean_name = name.replace("https://github.com/", "").strip("/")
        try:
            star_repo(clean_name)
            details = get_repo_details(clean_name)
            starred.append(details)
            time.sleep(0.3)
        except Exception as e:
            failed.append({"repo": clean_name, "error": str(e)})

    return {
        "status": "success" if not failed else "partial_success",
        "starred": starred,
        "failed": failed,
        "summary": {"total": len(repo_names), "success": len(starred), "failed": len(failed)}
    }

def batch_unstar(input_file=None, repo_names=None):
    if repo_names is None:
        with open(input_file, "r", encoding="utf-8") as f:
            repo_names = json.load(f)

    safe_threshold = int(os.getenv("STARS_UNSTAR_SAFE_THRESHOLD", 5000))
    limit = int(os.getenv("STARS_UNSTAR_LIMIT", 50))

    if len(repo_names) > limit:
        return {
            "status": "error",
            "message": f"Exceeded batch unstar limit of {limit}. Got {len(repo_names)} repos."
        }

    unstarred = []
    failed = []
    skipped_high_stars = []

    for name in repo_names:
        try:
            details = get_repo_details(name)
            if details["stargazers_count"] >= safe_threshold:
                skipped_high_stars.append({"repo": name, "stars": details["stargazers_count"]})
                continue
            unstar_repo(name)
            unstarred.append(name)
            time.sleep(0.3)
        except Exception as e:
            failed.append({"repo": name, "error": str(e)})

    return {
        "status": "success" if not failed else "partial_success",
        "unstarred": unstarred,
        "failed": failed,
        "skipped_high_stars": skipped_high_stars
    }

def create_backup(stars_file=None, lists_file=None, output_dir=None):
    stars_data = []
    if stars_file and os.path.exists(stars_file):
        with open(stars_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
            stars_data = raw.get("repos", raw) if isinstance(raw, dict) else raw

    lists_data = []
    if lists_file and os.path.exists(lists_file):
        with open(lists_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
            lists_data = raw.get("lists", raw) if isinstance(raw, dict) else raw

    return create_backup_from_data(stars_data, lists_data, output_dir)

def create_backup_from_data(stars_data, lists_data, output_dir=None):
    target_dir = output_dir or BACKUP_DIR
    os.makedirs(target_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(target_dir, f"backup_{ts}.json")

    backup_payload = {
        "timestamp": ts,
        "stars": stars_data,
        "lists": lists_data
    }

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_payload, f, ensure_ascii=False, indent=2)

    return {"status": "success", "backup_file": backup_path, "total_stars": len(stars_data), "total_lists": len(lists_data)}

def list_backups(output_dir=None):
    target_dir = output_dir or BACKUP_DIR
    if not os.path.exists(target_dir):
        return {"status": "success", "backups": []}

    backups = []
    for fname in sorted(os.listdir(target_dir), reverse=True):
        if fname.startswith("backup_") and fname.endswith(".json"):
            fpath = os.path.join(target_dir, fname)
            backups.append({"filename": fname, "filepath": fpath, "created_at": datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat()})

    return {"status": "success", "backups": backups}

def load_backup(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"status": "success", "data": data}

def main():
    parser = argparse.ArgumentParser(description="GitHub Star Operations")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("user")
    subparsers.add_parser("check-scopes")

    batch_star_parser = subparsers.add_parser("batch-star-info")
    batch_star_parser.add_argument("--input-file", required=True)

    batch_unstar_parser = subparsers.add_parser("batch-unstar")
    batch_unstar_parser.add_argument("--input-file", required=True)

    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("--stars-file", required=True)
    backup_parser.add_argument("--lists-file", default=None)
    backup_parser.add_argument("--output-dir", default=None)

    list_backups_parser = subparsers.add_parser("list-backups")
    list_backups_parser.add_argument("--output-dir", default=None)

    load_parser = subparsers.add_parser("load-backup")
    load_parser.add_argument("--filepath", required=True)

    batch_star_simple = subparsers.add_parser("batch-star")
    batch_star_simple.add_argument("--input-file", required=True)

    args = parser.parse_args()

    if args.command == "user":
        print(json.dumps(get_current_user(), ensure_ascii=False, indent=2))
    elif args.command == "check-scopes":
        print(json.dumps(check_scopes(), ensure_ascii=False, indent=2))
    elif args.command == "batch-star-info":
        print(json.dumps(batch_star_info(args.input_file), ensure_ascii=False, indent=2))
    elif args.command == "batch-unstar":
        print(json.dumps(batch_unstar(args.input_file), ensure_ascii=False, indent=2))
    elif args.command == "backup":
        print(json.dumps(create_backup(args.stars_file, args.lists_file, args.output_dir), ensure_ascii=False, indent=2))
    elif args.command == "list-backups":
        print(json.dumps(list_backups(args.output_dir), ensure_ascii=False, indent=2))
    elif args.command == "load-backup":
        print(json.dumps(load_backup(args.filepath), ensure_ascii=False, indent=2))
    elif args.command == "batch-star":
        with open(args.input_file, "r", encoding="utf-8") as f:
            repos = json.load(f)
        starred = []
        failed = []
        for r in repos:
            try:
                star_repo(r)
                starred.append(r)
                time.sleep(0.3)
            except Exception as e:
                failed.append({"repo": r, "error": str(e)})
        print(json.dumps({
            "status": "success" if not failed else "partial_success",
            "starred": starred,
            "failed": failed,
        }, ensure_ascii=False, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
