"""通用 GitHub Stars 方案生成器 (Generic Star Plan Generator)

设计原则:
- 完全通用，零硬编码用户特定仓库或列表；
- 动态识别“泛化兜底标签”（如大模型相关、小工具、Misc、未分类等），予以解散并精细重分；
- 动态识别“意图驱动标签”（如毕设、Thesis、待学习、Todo 等），实施冻结/只增不删策略；
- 结合仓库 Topics、语言与 Description 进行语义与领域重构。
"""

import json
import os
import re
import argparse
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import get_organize_mode, safe_load_json, safe_save_json, logger

# 泛化兜底标签识别模式（关键词及正则表达式）
GENERIC_NAME_PATTERNS = [
    r"^大模型相关$", r"^llm(s)?$", r"^ai$", r"^misc$", r"^utils$", r"^小工具$",
    r"^各色项目$", r"^未分类$", r"^待分类$", r"^其他$", r"^杂项$", r"^stuff$", r"^temp$"
]

# 意图/场景驱动标签识别模式
INTENT_NAME_PATTERNS = [
    r"毕设", r"thesis", r"graduation", r"待学习", r"todo", r"待整理",
    r"个人项目", r"my\s*project", r"试用", r"书签", r"bookmark"
]

def get_env_param(key, default):
    val = os.getenv(key)
    if val is not None and val.strip() != "":
        try:
            return type(default)(val.strip())
        except ValueError:
            pass
    return default

def is_generic_list(name, description=""):
    name_clean = name.strip().lower()
    for pat in GENERIC_NAME_PATTERNS:
        if re.search(pat, name_clean, re.IGNORECASE):
            return True
    return False

def is_intent_list(name, description=""):
    name_clean = name.strip().lower()
    for pat in INTENT_NAME_PATTERNS:
        if re.search(pat, name_clean, re.IGNORECASE):
            return True
    return False

def extract_keywords(repo):
    """从 repo 中提取语义关键词。"""
    text_parts = []
    if repo.get("full_name"):
        text_parts.append(repo["full_name"])
    if repo.get("description"):
        text_parts.append(repo["description"])
    if repo.get("language"):
        text_parts.append(repo["language"])
    for t in repo.get("topics") or []:
        text_parts.append(t)
    return " ".join(text_parts).lower()

def match_list_score(repo, list_obj):
    """计算 repo 与指定 List 的语义匹配度。"""
    kw_text = extract_keywords(repo)
    lname = list_obj.get("name", "").lower()
    ldesc = (list_obj.get("description") or "").lower()

    score = 0
    # List 名称命中
    lname_tokens = [t for t in re.split(r"[\s/_\-]+", lname) if len(t) > 1]
    for token in lname_tokens:
        if token in kw_text:
            score += 3

    # List 描述命中
    if ldesc:
        ldesc_tokens = [t for t in re.split(r"[\s/_\-]+", ldesc) if len(t) > 2]
        for token in ldesc_tokens:
            if token in kw_text:
                score += 1

    return score

def discover_new_list_candidates(unlisted_repos):
    """从未归类的 repos 中动态聚类发现值得新建的通用 List。"""
    clusters = {
        "Markdown & 文档工具": ["markdown", "docx", "pdf", "latex", "epub", "editor"],
        "Web 自动化与爬虫": ["crawler", "scraper", "playwright", "puppeteer", "browser", "selenium"],
        "音视频与多模态": ["video", "audio", "multimodal", "image", "vision", "speech"],
        "数据分析与数据库": ["database", "sql", "analytics", "parquet", "dataset", "dataframe"],
        "安全与逆向工程": ["security", "reverse-engineering", "malware", "pwn", "vulnerability"]
    }
    
    candidates = []
    matched_repo_ids = set()

    for cand_name, kw_list in clusters.items():
        count = 0
        for r in unlisted_repos:
            kw_text = extract_keywords(r)
            if any(k in kw_text for k in kw_list):
                count += 1
        if count >= 2:
            candidates.append({
                "name": cand_name,
                "description": f"自动聚类建议新建：专注于 {cand_name} 领域的开源项目集",
                "keywords": kw_list
            })

    return candidates

def categorize_repo_generic(repo, existing_lists, new_lists, dissolved_list_ids, intent_list_status, mode):
    stars = repo.get("stargazers_count", 0)
    archived = repo.get("archived", False)

    # Get current assigned list ids
    orig_curr_ids = list(repo.get("current_list_ids", []))
    
    # 1. 忽略被解散的泛化 List
    curr_ids = [lid for lid in orig_curr_ids if lid not in dissolved_list_ids]
    target_ids = set(curr_ids)
    reasons = []

    # Get thresholds
    if mode == "aggressive":
        default_unstar_safe = 5000
        default_low_stars = 200
    elif mode == "moderate":
        default_unstar_safe = 5000
        default_low_stars = 100
    else:  # conservative
        default_unstar_safe = 999999
        default_low_stars = 0

    unstar_safe_threshold = get_env_param("STARS_UNSTAR_SAFE_THRESHOLD", default_unstar_safe)
    low_stars_threshold = get_env_param("STARS_LOW_STARS_THRESHOLD", default_low_stars)

    # Check unstar condition
    if mode != "conservative" and stars < unstar_safe_threshold:
        if mode == "aggressive" and (archived or stars < low_stars_threshold):
            return {
                "full_name": repo.get("full_name"),
                "node_id": repo.get("node_id"),
                "description": repo.get("description", ""),
                "language": repo.get("language"),
                "stargazers_count": stars,
                "archived": archived,
                "action": "unstar",
                "list_ids": [],
                "reason": f"激进清理：项目已归档或关注度低于 {low_stars_threshold} stars",
                "match": "low"
            }
        elif mode == "moderate" and (archived and stars < low_stars_threshold):
            return {
                "full_name": repo.get("full_name"),
                "node_id": repo.get("node_id"),
                "description": repo.get("description", ""),
                "language": repo.get("language"),
                "stargazers_count": stars,
                "archived": archived,
                "action": "unstar",
                "list_ids": [],
                "reason": f"中等清理：项目已归档且 Star 数低于 {low_stars_threshold}",
                "match": "low"
            }

    # 2. 尝试与新建建议 List 匹配
    if mode in ("moderate", "aggressive"):
        kw_text = extract_keywords(repo)
        for nl in new_lists:
            kws = nl.get("keywords", [])
            if any(k in kw_text for k in kws):
                target_ids.add(nl["id"])
                reasons.append(f"命中领域关键词，建议新建归入 [{nl['name']}]")

    # 3. 尝试与现有非解散 List 动态语义匹配
    for l in existing_lists:
        if l["id"] in dissolved_list_ids or l["id"] in intent_list_status:
            continue
        score = match_list_score(repo, l)
        if score >= 3 and l["id"] not in target_ids:
            target_ids.add(l["id"])
            reasons.append(f"语义高度匹配已有分类，归入 [{l['name']}]")

    # 4. 意图驱动标签规则约束 (Intent Rules)
    for lid, st in intent_list_status.items():
        if lid in orig_curr_ids:
            # 规则：原有项目严禁从意图 List 中删除/移出
            target_ids.add(lid)
        else:
            if st.get("status") == "frozen":
                # 未指定意图：AI 不自动向其添加新项目
                target_ids.discard(lid)
            elif st.get("status") == "answered" and st.get("intent"):
                intent_kw = st.get("intent", "").lower()
                kw_text = extract_keywords(repo)
                if intent_kw in kw_text:
                    target_ids.add(lid)
                    reasons.append(f"符合用户填写的意图方向 [{st['intent']}]，归入 [{st['name']}]")

    action = "categorize" if target_ids != set(orig_curr_ids) else "keep"
    reason_str = "；".join(reasons) if reasons else "已在合适的 List 中，维持原状"

    return {
        "full_name": repo.get("full_name"),
        "node_id": repo.get("node_id"),
        "description": repo.get("description", ""),
        "language": repo.get("language"),
        "stargazers_count": stars,
        "archived": archived,
        "action": action,
        "list_ids": list(target_ids),
        "reason": reason_str,
        "match": "high" if len(target_ids) > 0 else "mid"
    }

def build_import_plan(insights_file, lists_file, output_file):
    insights_data = safe_load_json(insights_file).get("insights", [])
    lists_data = safe_load_json(lists_file).get("lists", [])

    clean_lists = [{"id": l["id"], "name": l["name"], "description": l.get("description", "")} for l in lists_data]
    plan_repos = []

    for item in insights_data:
        fname = item.get("repo") or item.get("full_name")
        best_target_ids = []
        reasons = []

        # Find matching lists
        for l in lists_data:
            score = match_list_score(item, l)
            if score >= 3:
                best_target_ids.append(l["id"])
                reasons.append(f"匹配已有 List [{l['name']}]")

        reason_str = "；".join(reasons) if reasons else "建议新加入收藏并设为分类关注"
        plan_repos.append({
            "full_name": fname,
            "node_id": item.get("node_id"),
            "description": item.get("description") or "",
            "language": item.get("language"),
            "stargazers_count": item.get("stargazers_count", 0),
            "archived": item.get("archived", False),
            "action": "categorize",
            "list_ids": best_target_ids,
            "reason": reason_str,
            "match": "high" if best_target_ids else "mid",
            "readme_excerpt": (item.get("readme_excerpt") or "")[:300]
        })

    plan = {
        "mode": "import",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "lists": clean_lists,
        "new_lists": [],
        "repos": plan_repos
    }

    safe_save_json(output_file, plan)
    print(f"Generated {output_file} successfully in import mode! Total repos: {len(plan_repos)}")


def main():
    parser = argparse.ArgumentParser(description="Generic Star Plan Generator")
    parser.add_argument("--plan-mode", choices=["organize", "import"], default="organize", help="Plan mode: organize or import")
    parser.add_argument("--intent-answers", default="{}", help='JSON string of intent answers, e.g. \'{"毕设":"多模态"}\'')
    parser.add_argument("--insights-file", default="insights.json", help="Path to insights.json for import mode")
    parser.add_argument("--output-file", "-o", default="review_plan.json", help="Output plan file path")
    args, _ = parser.parse_known_args()

    if args.plan_mode == "import":
        lists_file = "lists.json" if os.path.exists("lists.json") else "current_lists_with_items.json"
        build_import_plan(args.insights_file, lists_file, args.output_file)
        return

    try:
        intent_answers = json.loads(args.intent_answers)
    except Exception:
        intent_answers = {}

    mode = get_organize_mode()
    print(f"Generating review plan using Generic Engine in mode: '{mode}'")

    stars_file = "stars.json"
    lists_file = "lists.json" if os.path.exists("lists.json") else "current_lists_with_items.json"

    stars_data = safe_load_json(stars_file)
    lists_data = safe_load_json(lists_file)

    repos = stars_data.get('repos', [])
    lists = lists_data.get('lists', [])

    # 1. 动态识别泛化兜底标签与意图驱动标签
    dissolved_lists = []
    dissolved_list_ids = set()
    intent_list_status = {}

    for l in lists:
        lname = l['name']
        ldesc = l.get('description', '')
        lid = l['id']

        if is_generic_list(lname, ldesc):
            dissolved_list_ids.add(lid)
            dissolved_lists.append({
                "id": lid,
                "name": lname,
                "reason": f"禁用泛化兜底标签 [{lname}]，予以直接解散；原成员全部解绑重新归入具体精细分类"
            })
        elif is_intent_list(lname, ldesc):
            ans = intent_answers.get(lname)
            if ans:
                intent_list_status[lid] = {
                    "id": lid,
                    "name": lname,
                    "status": "answered",
                    "intent": ans,
                    "rule": f"针对意图 [{ans}] 运行：允许符合条件的新项目归入，严禁从 AI 方案中删除已有项目"
                }
            else:
                intent_list_status[lid] = {
                    "id": lid,
                    "name": lname,
                    "status": "frozen",
                    "intent": None,
                    "rule": "意图未指定 (FROZEN)：AI 方案严禁新增或从该 List 中移出项目"
                }

    # 2. 动态发现新 List 建议 (如中等/激进模式)
    new_lists = []
    if mode in ("moderate", "aggressive"):
        # 筛选未归类 repo 组
        node_to_list_ids = {}
        for l in lists:
            for item in l.get('repos', []):
                if item.get('node_id'):
                    node_to_list_ids.setdefault(item['node_id'], []).append(l['id'])
        
        unlisted = [r for r in repos if not node_to_list_ids.get(r.get('node_id'))]
        cands = discover_new_list_candidates(unlisted)
        for idx, cand in enumerate(cands):
            cand_id = f"NEW_{idx+1}"
            cand["id"] = cand_id
            new_lists.append(cand)

    node_to_list_ids = {}
    for l in lists:
        lid = l['id']
        for item in l.get('repos', []):
            nid = item.get('node_id')
            if nid:
                node_to_list_ids.setdefault(nid, []).append(lid)

    plan_repos = []
    categorized_count = 0
    keep_count = 0
    unstar_count = 0

    for r in repos:
        nid = r.get('node_id')
        r['current_list_ids'] = node_to_list_ids.get(nid, [])
        item_plan = categorize_repo_generic(r, lists, new_lists, dissolved_list_ids, intent_list_status, mode)
        plan_repos.append(item_plan)
        if item_plan['action'] == 'categorize':
            categorized_count += 1
        elif item_plan['action'] == 'unstar':
            unstar_count += 1
        else:
            keep_count += 1

    clean_lists = [{"id": l["id"], "name": l["name"], "description": l.get("description", "")} for l in lists]

    delete_list_ids = list(dissolved_list_ids)

    # In moderate and aggressive modes, identify empty lists for deletion
    if mode in ("moderate", "aggressive"):
        for l in lists:
            if l.get("item_count", 0) == 0 and l["id"] not in delete_list_ids:
                delete_list_ids.append(l["id"])

    plan = {
        "mode": "organize",
        "organize_mode": mode,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "lists": clean_lists,
        "new_lists": new_lists,
        "dissolved_lists": dissolved_lists,
        "intent_lists": list(intent_list_status.values()),
        "delete_list_ids": delete_list_ids,
        "repos": plan_repos
    }

    safe_save_json(args.output_file, plan)

    print(f"Generated {args.output_file} successfully using Generic Engine! (Mode: {mode})")
    print(f"Total repos: {len(plan_repos)}")
    print(f"New lists proposed: {len(new_lists)}")
    print(f"Dissolved generic lists: {len(dissolved_lists)}")
    print(f"Intent protected lists: {len(intent_list_status)}")
    print(f"Categorize actions: {categorized_count}")
    print(f"Keep actions: {keep_count}")
    print(f"Unstar actions: {unstar_count}")
    print(f"Delete list count: {len(delete_list_ids)}")

if __name__ == '__main__':
    main()

