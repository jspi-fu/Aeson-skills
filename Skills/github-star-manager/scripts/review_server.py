"""本地确认页服务: 浏览器中调整分类方案并一键执行写回。

用法:
    python scripts/review_server.py --plan-file review_plan.json [--port 0] [--no-open]

安全模型:
  - 绑定 127.0.0.1 + 端口 0(系统随机分配);
  - 每次启动生成一次性 token,注入页面;POST 必须携带正确 token;
  - Host 头白名单校验,防 DNS-rebinding;
  - 执行写回前服务端强制创建备份(不依赖页面/Agent 自觉)。

plan JSON 契约(agent 生成):
  mode: "organize"(整理) | "import"(批量导入)
  lists:     现有 List [{"id","name","description"}]
  new_lists: 建议新建 [{"id":"NEW_1","name","description"}]  (页面也可增删)
  repos: [{
    "full_name","node_id","description","language","stargazers_count","archived",
    "action": "categorize"|"keep"|"unstar"(organize) / "reject"(import),
    "list_ids": [完整目标 List 集合],
    "reason"(归类理由), "match"("high"/"mid"/"low"), "issues_note", "readme_excerpt"
  }]
"""
import os
import sys
import json
import secrets
import argparse
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from utils import logger, cleanup_session_temp_files
from state import apply_diff_to_stars_state
from fetch_stars import fetch_all_stars
from github_lists import fetch_all_lists, create_user_list, batch_set_lists, delete_user_list
from star_ops import (batch_star_info, batch_unstar, get_repo_details,
                      create_backup_from_data)

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "assets", "review_template.html")


class PlanError(Exception):
    pass


def validate_plan(plan):
    mode = plan.get("mode")
    if mode not in ("organize", "import"):
        raise PlanError("plan.mode 必须是 organize 或 import")
    valid_actions = {"categorize", "keep", "unstar"} if mode == "organize" \
        else {"categorize", "keep", "reject"}
    repos = plan.get("repos") or []
    if not repos:
        raise PlanError("plan.repos 为空")
    known = {l.get("id") for l in plan.get("lists", [])}
    known.update(l.get("id") for l in plan.get("new_lists", []))
    unstar_names = []
    for r in repos:
        if r.get("action") not in valid_actions:
            raise PlanError(f"非法 action: {r.get('full_name')} -> {r.get('action')}")
        for lid in r.get("list_ids", []):
            if lid not in known:
                raise PlanError(f"未知 list_id: {lid} (repo: {r.get('full_name')})")
        if r.get("action") == "unstar":
            unstar_names.append(r.get("full_name"))
    limit = int(os.getenv("STARS_UNSTAR_LIMIT", 50))
    if len(unstar_names) > limit:
        raise PlanError(f"unstar 数量 {len(unstar_names)} 超过单批上限 {limit}")
    return repos, unstar_names


def resolve_node_id(full_name):
    """缺失 node_id 时通过 REST 补查;查不到返回 None。"""
    try:
        return get_repo_details(full_name).get("node_id")
    except Exception:
        return None


def execute_plan(plan):
    """备份 -> 建 List -> (import: 先 star) -> 归类写回 -> (organize: unstar) -> 删 List。"""
    mode = plan.get("mode")
    repos, _ = validate_plan(plan)

    # 1. 强制备份 checkpoint(当前真实状态)
    stars = fetch_all_stars()["repos"]
    lists_data = fetch_all_lists(with_items=True)["lists"]
    backup = create_backup_from_data(stars, lists_data)
    logger.info(f"备份完成: {backup['backup_file']}")

    # 2. 创建新 List,记录占位 id -> 真实 id
    id_map = {}
    created_lists = []
    for nl in plan.get("new_lists", []):
        res = create_user_list(nl.get("name", ""), nl.get("description", ""),
                               nl.get("is_private", False))
        real_id = res["list"].get("id")
        id_map[nl["id"]] = real_id
        created_lists.append({"name": nl.get("name"), "id": real_id})

    resolve = lambda lid: id_map.get(lid, lid)

    # 3. import 模式: 先 star 选中 repo,并收集 node_id
    starred_details = []
    if mode == "import":
        to_star = [r["full_name"] for r in repos if r.get("action") in ("categorize", "keep")]
        if to_star:
            res = batch_star_info(repo_names=to_star)
            starred_details = res.get("starred", [])

    node_id_by_name = {d.get("full_name"): d.get("node_id") for d in starred_details}
    if mode == "organize":
        for r in repos:
            if r.get("action") == "categorize" and not r.get("node_id"):
                r["node_id"] = resolve_node_id(r["full_name"])
    else:
        for r in repos:
            if r.get("action") == "categorize" and not r.get("node_id"):
                r["node_id"] = node_id_by_name.get(r["full_name"]) or resolve_node_id(r["full_name"])

    # 4. 归类写回(全量替换语义,list_ids 必须已是完整集合)
    set_items = [{"node_id": r["node_id"], "list_ids": [resolve(x) for x in r.get("list_ids", [])]}
                 for r in repos
                 if r.get("action") == "categorize" and r.get("node_id") and r.get("list_ids")]
    set_res = batch_set_lists(items=set_items) if set_items else {"success_count": 0, "failed": []}

    # 5. organize 模式: 执行 unstar(脚本内强制高星保护)
    unstar_res = {"unstarred": [], "failed": [], "skipped_high_stars": []}
    if mode == "organize":
        unstar_names = [r["full_name"] for r in repos if r.get("action") == "unstar"]
        if unstar_names:
            unstar_res = batch_unstar(repo_names=unstar_names)

    # 6. 删除标记的 List
    deleted_lists = []
    for list_id in plan.get("delete_list_ids", []):
        try:
            delete_user_list(list_id)
            deleted_lists.append(list_id)
            logger.info(f"成功删除 List: {list_id}")
        except Exception as e:
            logger.warning(f"删除 List {list_id} 失败: {e}")
    failed = list(set_res.get("failed", [])) + list(unstar_res.get("failed", []))
    
    # 7. 用户确认写回完成后，自动清理分类过程生成的所有临时中间产物文件
    cleaned_files = cleanup_session_temp_files()

    return {
        "backup_file": backup["backup_file"],
        "created_lists": created_lists,
        "deleted_lists": deleted_lists,
        "categorized": set_res.get("success_count", 0),
        "starred": len(starred_details),
        "unstarred": unstar_res.get("unstarred", []),
        "skipped_high_stars": unstar_res.get("skipped_high_stars", []),
        "cleaned_files": cleaned_files,
        "failed": failed,
    }


class Handler(BaseHTTPRequestHandler):
    plan_html = None      # 注入后的页面
    token = None
    executed = False

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        host = self.headers.get("Host", "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._host_ok():
            self.send_error(403)
            return
        if self.path in ("/", "/index.html"):
            body = self.plan_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if not self._host_ok():
            self.send_error(403)
            return
        if self.path != "/action":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "error": "invalid json"}, 400)
            return
        if payload.get("token") != self.token:
            self._send_json({"ok": False, "error": "bad token"}, 403)
            return
        if payload.get("mode") == "save_plan":
            path = os.path.abspath("review_plan_saved.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload.get("plan", {}), f, ensure_ascii=False, indent=2)
            self._send_json({"ok": True, "path": path})
        elif payload.get("mode") == "execute":
            if Handler.executed:
                self._send_json({"ok": False, "error": "本次会话已执行过,请重启服务再执行"})
                return
            try:
                validate_plan(payload.get("plan", {}))
            except PlanError as e:
                self._send_json({"ok": False, "error": str(e)})
                return
            try:
                result = execute_plan(payload.get("plan", {}))
                Handler.executed = True
                self._send_json({"ok": True, "result": result})
                logger.info("写回成功完成，服务将在 3 秒后自动安全退出。")
                threading.Timer(3.0, lambda: self.server.shutdown()).start()
            except Exception as e:
                logger.exception("execute failed")
                self._send_json({"ok": False, "error": str(e)})
        else:
            self._send_json({"ok": False, "error": "unknown mode"}, 400)

    def log_message(self, fmt, *args):
        logger.info(fmt % args)


def open_browser(url):
    """跨平台可靠打开浏览器，包含 OS 原生命令兜底。"""
    try:
        if webbrowser.open(url):
            return
    except Exception:
        pass
    try:
        if sys.platform == "win32":
            os.system(f'start "" "{url}"')
        elif sys.platform == "darwin":
            os.system(f'open "{url}"')
        else:
            os.system(f'xdg-open "{url}"')
    except Exception as e:
        logger.warning(f"Failed to open browser: {e}")


def main():
    parser = argparse.ArgumentParser(description="Review server for star plans")
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--port", type=int, default=0, help="0 = 系统随机端口")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    with open(args.plan_file, "r", encoding="utf-8") as f:
        plan = json.load(f)
    try:
        validate_plan(plan)
    except PlanError as e:
        print(json.dumps({"status": "error", "message": f"plan 校验失败: {e}"}, ensure_ascii=False))
        sys.exit(1)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        tpl = f.read()

    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"

    blob = json.dumps(plan, ensure_ascii=False).replace("<", "\\u003c")
    exec_config = json.dumps({"token": token, "endpoint": "/action"})
    Handler.plan_html = tpl.replace("__REVIEW_DATA__", blob).replace("__EXEC_CONFIG__", exec_config)
    Handler.token = token

    print(json.dumps({"status": "success", "url": url,
                      "message": "已自动尝试在浏览器中打开确认页；执行完成后服务将自动关闭退出。"},
                     ensure_ascii=False), flush=True)

    # 空闲超时自动保护（30 分钟无操作自动关停）
    timeout_timer = threading.Timer(1800.0, lambda: server.shutdown())
    timeout_timer.daemon = True
    timeout_timer.start()

    if not args.no_open:
        threading.Timer(0.3, lambda: open_browser(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

