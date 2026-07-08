#!/usr/bin/env python3
"""API configuration template manager - save, load, list, delete and execute API request templates."""

import argparse
import json
import os
import subprocess
import sys

TEMPLATE_DIR = os.path.join(os.path.expanduser("~"), ".beeimg-uploader-templates")
TEMPLATE_FILE = os.path.join(TEMPLATE_DIR, "templates.json")


def ensure_template_file():
    """Ensure template directory and file exist."""
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    if not os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, "w") as f:
            json.dump({}, f)


def load_templates():
    """Load all templates from file."""
    ensure_template_file()
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_templates(templates):
    """Save all templates to file."""
    ensure_template_file()
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


def output_json(data):
    """Print JSON result to stdout."""
    print(json.dumps(data, ensure_ascii=False))


def cmd_save(args):
    """Save a new API template or update existing one."""
    templates = load_templates()

    # Parse JSON fields
    headers = json.loads(args.headers) if args.headers else {}
    params = json.loads(args.params) if args.params else {}
    form_data = json.loads(args.form_data) if args.form_data else {}

    template = {
        "method": args.method,
        "url": args.url,
        "headers": headers,
        "params": params,
        "json_body": args.json_body,
        "form_data": form_data,
        "description": args.description or "",
    }

    is_update = args.name in templates
    templates[args.name] = template
    save_templates(templates)

    action = "updated" if is_update else "saved"
    output_json({
        "status": "success",
        "message": f"Template '{args.name}' {action}",
        "template": template,
    })


def cmd_load(args):
    """Load a specific template by name."""
    templates = load_templates()
    if args.name not in templates:
        output_json({
            "status": "error",
            "error_type": "not_found",
            "error_message": f"Template '{args.name}' not found. Use 'list' to see available templates.",
        })
        sys.exit(1)

    output_json({
        "status": "success",
        "template_name": args.name,
        "template": templates[args.name],
    })


def cmd_list(args):
    """List all saved templates with summary info."""
    templates = load_templates()
    summary = {}
    for name, tmpl in templates.items():
        summary[name] = {
            "method": tmpl.get("method", "GET"),
            "url": tmpl.get("url", ""),
            "description": tmpl.get("description", ""),
        }

    output_json({
        "status": "success",
        "count": len(summary),
        "templates": summary,
    })


def cmd_delete(args):
    """Delete a template by name."""
    templates = load_templates()
    if args.name not in templates:
        output_json({
            "status": "error",
            "error_type": "not_found",
            "error_message": f"Template '{args.name}' not found.",
        })
        sys.exit(1)

    del templates[args.name]
    save_templates(templates)

    output_json({
        "status": "success",
        "message": f"Template '{args.name}' deleted",
    })


def cmd_run(args):
    """Execute an API call based on a saved template, with optional parameter overrides."""
    templates = load_templates()
    if args.name not in templates:
        output_json({
            "status": "error",
            "error_type": "not_found",
            "error_message": f"Template '{args.name}' not found. Use 'list' to see available templates.",
        })
        sys.exit(1)

    tmpl = templates[args.name]

    # Build api_call.py command with template values as base
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = [
        sys.executable,
        os.path.join(script_dir, "api_call.py"),
        "--method", tmpl.get("method", "GET"),
        "--url", tmpl.get("url", ""),
    ]

    # Apply template defaults
    if tmpl.get("headers"):
        cmd.extend(["--headers", json.dumps(tmpl["headers"], ensure_ascii=False)])
    if tmpl.get("params"):
        cmd.extend(["--params", json.dumps(tmpl["params"], ensure_ascii=False)])
    if tmpl.get("json_body"):
        cmd.extend(["--json-body", tmpl["json_body"]])
    if tmpl.get("form_data"):
        cmd.extend(["--form-data", json.dumps(tmpl["form_data"], ensure_ascii=False)])

    # Apply overrides from command line
    if args.headers:
        cmd.extend(["--headers", args.headers])
    if args.params:
        cmd.extend(["--params", args.params])
    if args.json_body:
        cmd.extend(["--json-body", args.json_body])
    if args.form_data:
        cmd.extend(["--form-data", args.form_data])
    if args.files:
        cmd.extend(["--files", args.files])
    if args.timeout:
        cmd.extend(["--timeout", str(args.timeout)])
    if args.output_format:
        cmd.extend(["--output-format", args.output_format])

    # Execute api_call.py
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        # Pass through the output from api_call.py
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            # Merge stderr into output as error info
            try:
                err = json.loads(result.stderr)
                output_json(err)
            except json.JSONDecodeError:
                print(result.stderr, end="", file=sys.stderr)
        sys.exit(result.returncode)
    except subprocess.TimeoutExpired:
        output_json({
            "status": "error",
            "error_type": "timeout",
            "error_message": "Template execution timed out after 120s",
        })
        sys.exit(1)
    except FileNotFoundError:
        output_json({
            "status": "error",
            "error_type": "script_not_found",
            "error_message": f"api_call.py not found at {os.path.join(script_dir, 'api_call.py')}",
        })
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="API configuration template manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # save
    save_parser = subparsers.add_parser("save", help="Save or update an API template")
    save_parser.add_argument("--name", required=True, help="Template name (unique identifier)")
    save_parser.add_argument("--method", required=True,
                             choices=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                             help="HTTP method")
    save_parser.add_argument("--url", required=True, help="Request URL")
    save_parser.add_argument("--headers", default=None, help="JSON string of request headers")
    save_parser.add_argument("--params", default=None, help="JSON string of query parameters")
    save_parser.add_argument("--json-body", default=None, help="JSON string for request body")
    save_parser.add_argument("--form-data", default=None, help="JSON string of form data")
    save_parser.add_argument("--description", default="", help="Template description")

    # load
    load_parser = subparsers.add_parser("load", help="Load a template by name")
    load_parser.add_argument("--name", required=True, help="Template name")

    # list
    subparsers.add_parser("list", help="List all saved templates")

    # delete
    del_parser = subparsers.add_parser("delete", help="Delete a template")
    del_parser.add_argument("--name", required=True, help="Template name")

    # run
    run_parser = subparsers.add_parser("run", help="Execute API call from template")
    run_parser.add_argument("--name", required=True, help="Template name")
    run_parser.add_argument("--headers", default=None, help="Override: JSON string of request headers")
    run_parser.add_argument("--params", default=None, help="Override: JSON string of query parameters")
    run_parser.add_argument("--json-body", default=None, help="Override: JSON string for request body")
    run_parser.add_argument("--form-data", default=None, help="Override: JSON string of form data")
    run_parser.add_argument("--files", default=None, help="Override: JSON string of file uploads")
    run_parser.add_argument("--timeout", type=int, default=None, help="Override: timeout in seconds")
    run_parser.add_argument("--output-format", choices=["json", "text", "headers", "status"],
                            default=None, help="Override: output format")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "save": cmd_save,
        "load": cmd_load,
        "list": cmd_list,
        "delete": cmd_delete,
        "run": cmd_run,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
