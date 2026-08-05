import sys
import time
import json
import argparse
from utils import make_github_request, safe_load_json, safe_save_json, logger

GRAPHQL_URL = "https://api.github.com/graphql"
# Star Lists 属于未正式公开的 preview 接口,必须携带此 Accept 头
GRAPHQL_HEADERS = {"Accept": "application/vnd.github.beholder-preview+json"}

_typename_cache = {}


def run_graphql_query(query, variables=None):
    json_data = {"query": query}
    if variables:
        json_data["variables"] = variables
    resp = make_github_request(GRAPHQL_URL, method="POST", headers=GRAPHQL_HEADERS, json_data=json_data)
    result = resp.json()
    if "errors" in result:
        raise Exception(f"GraphQL error: {json.dumps(result['errors'], ensure_ascii=False)}")
    return result.get("data", {})


def _node_typename(node_id):
    """运行时探测节点的具体 GraphQL 类型名。preview schema 不稳定,不硬编码类型名。"""
    if node_id not in _typename_cache:
        data = run_graphql_query("query($id: ID!) { node(id: $id) { __typename } }", {"id": node_id})
        typename = (data.get("node") or {}).get("__typename")
        if not typename:
            raise Exception(f"Cannot resolve GraphQL node type for {node_id}")
        _typename_cache[node_id] = typename
    return _typename_cache[node_id]


def _fetch_items_page(list_id, cursor=None):
    """按游标拉取单个 List 的一页成员。"""
    typename = _node_typename(list_id)
    query = f"""
    query($id: ID!, $after: String) {{
      node(id: $id) {{
        ... on {typename} {{
          items(first: 100, after: $after) {{
            pageInfo {{ hasNextPage endCursor }}
            nodes {{ ... on Repository {{ id nameWithOwner }} }}
          }}
        }}
      }}
    }}
    """
    data = run_graphql_query(query, {"id": list_id, "after": cursor})
    return ((data.get("node") or {}).get("items")) or {}


def collect_list_items(list_id, first_items):
    """从嵌套查询的首页成员出发,翻页拉完该 List 的全部成员。"""
    repos = [{"node_id": n.get("id"), "full_name": n.get("nameWithOwner")}
             for n in first_items.get("nodes", [])]
    page_info = first_items.get("pageInfo") or {}
    cursor = page_info.get("endCursor")
    while page_info.get("hasNextPage"):
        items = _fetch_items_page(list_id, cursor)
        repos.extend({"node_id": n.get("id"), "full_name": n.get("nameWithOwner")}
                     for n in items.get("nodes", []))
        page_info = items.get("pageInfo") or {}
        cursor = page_info.get("endCursor")
    return repos


def fetch_all_lists(with_items=False):
    """游标分页拉取全部 Lists。with_items 时一并拉全每个 List 的成员(含翻页)。"""
    if with_items:
        items_block = """
            items(first: 100) {
              totalCount
              pageInfo { hasNextPage endCursor }
              nodes { ... on Repository { id nameWithOwner } }
            }"""
    else:
        items_block = "items(first: 1) { totalCount }"

    query = f"""
    query($after: String) {{
      viewer {{
        lists(first: 100, after: $after) {{
          pageInfo {{ hasNextPage endCursor }}
          nodes {{
            id
            name
            description
            isPrivate
{items_block}
          }}
        }}
      }}
    }}
    """

    formatted_lists = []
    warnings = []
    cursor = None
    while True:
        data = run_graphql_query(query, {"after": cursor})
        conn = data.get("viewer", {}).get("lists", {})
        for l in conn.get("nodes", []):
            items = l.get("items") or {}
            item = {
                "id": l.get("id"),
                "name": l.get("name"),
                "description": l.get("description"),
                "is_private": l.get("isPrivate"),
                "item_count": items.get("totalCount", 0),
            }
            if with_items:
                repos = collect_list_items(l.get("id"), items)
                item["repos"] = repos
                if item["item_count"] and len(repos) != item["item_count"]:
                    msg = f"List {l.get('name')}: 仅拉到 {len(repos)}/{item['item_count']} 个成员,数据可能不完整"
                    warnings.append(msg)
                    logger.warning(msg)
            formatted_lists.append(item)

        page_info = conn.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    result = {"status": "success", "lists": formatted_lists}
    if warnings:
        result["warnings"] = warnings
    return result


def get_list_items(list_id):
    res = fetch_all_lists(with_items=True)
    for l in res["lists"]:
        if l.get("id") == list_id:
            return {"status": "success", "list": l}
    return {"status": "error", "message": f"List not found: {list_id}"}


def create_user_list(name, description="", is_private=False):
    query = """
    mutation CreateList($name: String!, $description: String, $isPrivate: Boolean) {
      createUserList(input: {name: $name, description: $description, isPrivate: $isPrivate}) {
        list {
          id
          name
          description
          isPrivate
        }
      }
    }
    """
    data = run_graphql_query(query, {"name": name, "description": description, "isPrivate": is_private})
    created = data.get("createUserList", {}).get("list", {})
    return {"status": "success", "list": created}


def delete_user_list(list_id):
    query = """
    mutation DeleteList($listId: ID!) {
      deleteUserList(input: {listId: $listId}) {
        clientMutationId
      }
    }
    """
    run_graphql_query(query, {"listId": list_id})
    return {"status": "success", "list_id": list_id}


def update_user_list(list_id, name=None, description=None, is_private=None):
    query = """
    mutation UpdateList($listId: ID!, $name: String, $description: String, $isPrivate: Boolean) {
      updateUserList(input: {listId: $listId, name: $name, description: $description, isPrivate: $isPrivate}) {
        list {
          id
          name
          description
          isPrivate
        }
      }
    }
    """
    variables = {"listId": list_id}
    if name is not None:
        variables["name"] = name
    if description is not None:
        variables["description"] = description
    if is_private is not None:
        variables["isPrivate"] = is_private
    data = run_graphql_query(query, variables)
    updated = data.get("updateUserList", {}).get("list", {})
    return {"status": "success", "list": updated}


def set_lists_for_item(repo_node_id, list_ids):
    query = """
    mutation UpdateUserListsForItem($itemId: ID!, $listIds: [ID!]!) {
      updateUserListsForItem(input: {itemId: $itemId, listIds: $listIds}) {
        clientMutationId
      }
    }
    """
    run_graphql_query(query, {"itemId": repo_node_id, "listIds": list_ids})
    return {"status": "success", "repo_node_id": repo_node_id, "list_ids": list_ids}


def batch_set_lists(input_file=None, items=None):
    if items is None:
        items = safe_load_json(input_file)

    success_count = 0
    failed = []

    for idx, item in enumerate(items):
        node_id = item.get("node_id")
        list_ids = item.get("list_ids", [])
        try:
            set_lists_for_item(node_id, list_ids)
            success_count += 1
            time.sleep(0.3)
        except Exception as e:
            failed.append({"node_id": node_id, "error": str(e)})

    return {
        "status": "success" if not failed else "partial_success",
        "processed": len(items),
        "success_count": success_count,
        "failed": failed
    }


def main():
    parser = argparse.ArgumentParser(description="GitHub Lists Operations")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--with-items", action="store_true", help="Include items in lists")
    list_parser.add_argument("-o", "--output-file", help="Save output JSON to file directly without redirection")

    items_parser = subparsers.add_parser("items")
    items_parser.add_argument("--list-id", required=True, help="List node id, e.g. SL_xxx")
    items_parser.add_argument("-o", "--output-file", help="Save output JSON to file directly")

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--description", default="")
    create_parser.add_argument("--private", action="store_true")

    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("--list-id", required=True, help="List node id to delete")

    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("--list-id", required=True, help="List node id to update")
    update_parser.add_argument("--name", default=None)
    update_parser.add_argument("--description", default=None)
    update_parser.add_argument("--private", action="store_true", default=None)

    set_parser = subparsers.add_parser("set-lists")
    set_parser.add_argument("--repo-node-id", required=True)
    set_parser.add_argument("--list-ids", required=True, help="Comma separated list IDs")

    batch_parser = subparsers.add_parser("batch-set-lists")
    batch_parser.add_argument("--input-file", required=True)

    args = parser.parse_args()

    out_file = getattr(args, "output_file", None)

    if args.command == "list":
        res = fetch_all_lists(with_items=args.with_items)
        if out_file:
            safe_save_json(out_file, res)
            logger.info(f"Saved lists result to {out_file}")
        else:
            print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "items":
        res = get_list_items(args.list_id)
        if out_file:
            safe_save_json(out_file, res)
        else:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        if res["status"] == "error":
            sys.exit(1)
    elif args.command == "create":
        res = create_user_list(args.name, args.description, args.private)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "delete":
        res = delete_user_list(args.list_id)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "update":
        res = update_user_list(args.list_id, args.name, args.description, args.private)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "set-lists":
        ids = [i.strip() for i in args.list_ids.split(",") if i.strip()]
        res = set_lists_for_item(args.repo_node_id, ids)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "batch-set-lists":
        res = batch_set_lists(args.input_file)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        parser.print_help()



if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        err_msg = str(e)
        logger.error(f"GraphQL operation failed: {err_msg}")
        res = {
            "status": "error",
            "message": err_msg,
            "fallback_recommended": True,
            "fallback_reason": "GitHub GraphQL API unavailable or lacks Star List permissions. Safe to fallback to generating Awesome-List Markdown/HTML report."
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(1)


