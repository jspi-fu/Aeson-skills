"""用户画像与 stars 持续状态文件的存取。

状态目录: ~/.gh-star-manager/
  - profile.json      用户画像: 观察统计(脚本算) + 洞察/偏好(agent 维护)
  - stars_state.json  持续更新的全量 stars 列表(每次 --sync 刷新并对比差异)
"""
import os
import json
from datetime import datetime, timedelta, timezone

from utils import get_workdir

STATE_DIR = get_workdir()
PROFILE_PATH = os.path.join(STATE_DIR, "profile.json")
STARS_STATE_PATH = os.path.join(STATE_DIR, "stars_state.json")

PREFERENCE_CAP = 50
RECENT_DAYS = 90


def _ensure_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def _load(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return default


def _save(path, data):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_profile():
    return _load(PROFILE_PATH, {"updated_at": None, "login": None,
                                "stats": {}, "insights": {}, "preferences": []})


def save_profile(profile):
    profile["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save(PROFILE_PATH, profile)


def update_observed_stats(repos, login=None):
    """从 stars 数据重算观察统计。保留 agent 维护的 insights 与 preferences。"""
    profile = load_profile()
    if login:
        profile["login"] = login

    languages = {}
    topics = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        for t in r.get("topics") or []:
            topics[t] = topics.get(t, 0) + 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    recent = []
    for r in repos:
        starred_at = r.get("starred_at")
        if not starred_at:
            continue
        try:
            ts = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts >= cutoff:
            recent.append((ts, r.get("full_name")))
    recent.sort(key=lambda x: x[0], reverse=True)

    profile["stats"] = {
        "total_stars": len(repos),
        "top_languages": dict(sorted(languages.items(), key=lambda x: -x[1])[:8]),
        "top_topics": [t for t, _ in sorted(topics.items(), key=lambda x: -x[1])[:15]],
        "recent_starred": [name for _, name in recent[:20]],
        "recent_days": RECENT_DAYS,
    }
    save_profile(profile)
    return profile


def add_preferences(rules):
    """追加偏好规则(字符串列表),按文本去重,超出上限丢弃最旧的。"""
    rules = [r.strip() for r in rules if r and r.strip()]
    if not rules:
        return load_profile()
    profile = load_profile()
    prefs = profile.get("preferences") or []
    today = datetime.now().strftime("%Y-%m-%d")
    existing = {p.get("rule") for p in prefs}
    for rule in rules:
        if rule not in existing:
            prefs.append({"rule": rule, "learned_at": today})
            existing.add(rule)
    profile["preferences"] = prefs[-PREFERENCE_CAP:]
    save_profile(profile)
    return profile


def load_stars_state():
    return _load(STARS_STATE_PATH, None)


def update_stars_state(repos):
    """覆盖写入最新全量 stars,返回与上次状态的差异 {added, removed}。"""
    prev = load_stars_state()
    prev_names = {r.get("full_name") for r in (prev or {}).get("repos", [])}
    curr_names = {r.get("full_name") for r in repos}
    diff = {
        "added": sorted(curr_names - prev_names),
        "removed": sorted(prev_names - curr_names),
    } if prev else {"added": [], "removed": []}

    state = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(repos),
        "last_diff": diff,
        "repos": repos,
    }
    _save(STARS_STATE_PATH, state)
    return diff


def apply_diff_to_stars_state(added=None, removed=None):
    """写操作后增量维护 stars_state(不发 API 请求)。added 为 repo dict 列表。"""
    state = load_stars_state()
    if not state:
        return
    repos = {r.get("full_name"): r for r in state.get("repos", [])}
    for name in removed or []:
        repos.pop(name, None)
    for r in added or []:
        if r.get("full_name"):
            repos[r["full_name"]] = r
    state["repos"] = list(repos.values())
    state["total"] = len(state["repos"])
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save(STARS_STATE_PATH, state)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="User profile and stars state")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("dump-profile")

    add_p = sub.add_parser("add-preference")
    add_p.add_argument("rule")

    set_i = sub.add_parser("set-insights")
    set_i.add_argument("json_blob", help='e.g. {"research_focus":[...],"recent_focus":[...]}')

    sub.add_parser("dump-stars-state")

    args = parser.parse_args()

    if args.command == "dump-profile":
        print(json.dumps(load_profile(), ensure_ascii=False, indent=2))
    elif args.command == "add-preference":
        print(json.dumps(add_preferences([args.rule]), ensure_ascii=False, indent=2))
    elif args.command == "set-insights":
        profile = load_profile()
        profile["insights"] = json.loads(args.json_blob)
        print(json.dumps(save_profile(profile), ensure_ascii=False, indent=2))
    elif args.command == "dump-stars-state":
        state = load_stars_state()
        if state:
            summary = {k: v for k, v in state.items() if k != "repos"}
            summary["repos_sample"] = [r.get("full_name") for r in state.get("repos", [])[:5]]
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"status": "empty",
                              "message": "尚未同步,先运行 fetch_stars.py --sync"}, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
