"""静态确认页生成: 方案 JSON -> 自包含只读 HTML。

用法:
    python scripts/build_review.py --plan-file review_plan.json --output review.html [--open]

静态页可交互调整分类,但无法直接执行写回(file:// 无后端);
页面提供「导出方案 JSON」,由 Agent 接管后续执行。
"""
import os
import sys
import json
import argparse
import webbrowser

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import utils

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "assets", "review_template.html")


def render_html(plan):
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        tpl = f.read()
    # JSON 内的 "<" 统一转义,防止 </script> 等破坏内联脚本
    blob = json.dumps(plan, ensure_ascii=False).replace("<", "\\u003c")
    return tpl.replace("__REVIEW_DATA__", blob).replace("__EXEC_CONFIG__", "null")


def main():
    parser = argparse.ArgumentParser(description="Build static review HTML")
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--open", action="store_true", help="生成后自动打开浏览器")
    args = parser.parse_args()

    with open(args.plan_file, "r", encoding="utf-8") as f:
        plan = json.load(f)

    html = render_html(plan)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(json.dumps({"status": "success", "html": os.path.abspath(args.output)}, ensure_ascii=False))
    if args.open:
        webbrowser.open("file:///" + os.path.abspath(args.output).replace("\\", "/"))


if __name__ == "__main__":
    main()
