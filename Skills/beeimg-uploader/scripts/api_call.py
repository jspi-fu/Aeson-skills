#!/usr/bin/env python3
"""Universal API call tool - supports multiple HTTP methods, headers, params, file upload, response parsing and error handling."""

import argparse
import json
import sys
import time

from coze_workload_identity import requests


def parse_json_arg(value, arg_name):
    """Parse a JSON string argument, returning dict on success or raising clear error."""
    if not value:
        return {}
    try:
        result = json.loads(value)
        if not isinstance(result, dict):
            return {"_error": f"{arg_name} must be a JSON object, got {type(result).__name__}"}
        return result
    except json.JSONDecodeError as e:
        return {"_error": f"Failed to parse {arg_name} as JSON: {str(e)}"}


def build_result(status, **kwargs):
    """Build a standardized JSON result dict."""
    result = {
        "status": status,
        "success": status == "success",
        "status_code": kwargs.get("status_code"),
        "headers": kwargs.get("headers"),
        "body": kwargs.get("body"),
        "elapsed_time": kwargs.get("elapsed_time"),
        "error_type": kwargs.get("error_type"),
        "error_message": kwargs.get("error_message"),
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Universal API call tool")
    parser.add_argument("--method", required=True,
                        choices=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                        help="HTTP method")
    parser.add_argument("--url", required=True, help="Request URL")
    parser.add_argument("--headers", default=None, help="JSON string of request headers")
    parser.add_argument("--params", default=None, help="JSON string of query parameters")
    parser.add_argument("--json-body", default=None, help="JSON string for request body (sets Content-Type: application/json)")
    parser.add_argument("--form-data", default=None, help="JSON string of form data key-value pairs")
    parser.add_argument("--files", default=None, help='JSON string of file uploads, e.g. \'{"file":"./path/to/file.png"}\'')
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")
    parser.add_argument("--output-format", choices=["json", "text", "headers", "status"], default="json",
                        help="Output format for response body (default: json)")

    args = parser.parse_args()

    # Parse JSON arguments
    headers = parse_json_arg(args.headers, "--headers")
    if "_error" in headers:
        print(json.dumps(build_result("error", error_type="json_parse_error", error_message=headers["_error"]),
                         ensure_ascii=False))
        sys.exit(1)

    params = parse_json_arg(args.params, "--params")
    if "_error" in params:
        print(json.dumps(build_result("error", error_type="json_parse_error", error_message=params["_error"]),
                         ensure_ascii=False))
        sys.exit(1)

    form_data = parse_json_arg(args.form_data, "--form-data")
    if "_error" in form_data:
        print(json.dumps(build_result("error", error_type="json_parse_error", error_message=form_data["_error"]),
                         ensure_ascii=False))
        sys.exit(1)

    files_spec = parse_json_arg(args.files, "--files")
    if "_error" in files_spec:
        print(json.dumps(build_result("error", error_type="json_parse_error", error_message=files_spec["_error"]),
                         ensure_ascii=False))
        sys.exit(1)

    # Open file handles for upload
    file_handles = []
    files_dict = {}
    try:
        for field, filepath in files_spec.items():
            f = open(filepath, "rb")
            file_handles.append(f)
            files_dict[field] = f
    except FileNotFoundError as e:
        print(json.dumps(build_result("error", error_type="file_not_found",
                                      error_message=f"Upload file not found: {str(e)}"),
                         ensure_ascii=False))
        sys.exit(1)
    except PermissionError as e:
        print(json.dumps(build_result("error", error_type="file_not_found",
                                      error_message=f"Permission denied: {str(e)}"),
                         ensure_ascii=False))
        sys.exit(1)

    try:
        # Build request kwargs
        kwargs = {
            "headers": headers if headers else None,
            "params": params if params else None,
            "timeout": args.timeout,
        }

        # Handle request body
        if args.json_body:
            kwargs["data"] = args.json_body.encode("utf-8")
            if headers and "Content-Type" not in {k.lower(): k for k in headers}:
                headers["Content-Type"] = "application/json"
                kwargs["headers"] = headers

        if form_data:
            kwargs["data"] = form_data

        if files_dict:
            kwargs["files"] = files_dict

        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # Execute request
        start_time = time.time()
        response = requests.request(args.method, args.url, **kwargs)
        elapsed = round(time.time() - start_time, 3)

        # Parse response body based on output format
        body = None
        if args.output_format == "json":
            try:
                body = response.json()
            except (json.JSONDecodeError, ValueError):
                body = response.text
        elif args.output_format == "text":
            body = response.text
        elif args.output_format == "headers":
            body = None
        elif args.output_format == "status":
            body = None

        # Build response headers dict
        resp_headers = dict(response.headers) if args.output_format != "headers" else dict(response.headers)

        result = build_result(
            "success",
            status_code=response.status_code,
            headers=resp_headers if args.output_format in ("headers", "json") else None,
            body=body,
            elapsed_time=elapsed,
        )

        # Add HTTP error info if status code indicates failure
        if not response.ok:
            result["status"] = "http_error"
            result["success"] = False
            result["error_type"] = "http_error"
            result["error_message"] = f"HTTP {response.status_code}: {response.reason}"

        print(json.dumps(result, ensure_ascii=False))

    except requests.exceptions.Timeout:
        print(json.dumps(build_result("error",
                                      error_type="timeout",
                                      error_message=f"Request timed out after {args.timeout}s"),
                         ensure_ascii=False))
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        error_msg = str(e)
        if "NameResolutionError" in error_msg or "Name or service not known" in error_msg:
            error_msg = f"Cannot resolve hostname. Check if the URL is correct."
        elif "Connection refused" in error_msg:
            error_msg = f"Connection refused. Check if the server is running."
        print(json.dumps(build_result("error",
                                      error_type="connection_error",
                                      error_message=error_msg),
                         ensure_ascii=False))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(json.dumps(build_result("error",
                                      error_type="http_error",
                                      error_message=str(e)),
                         ensure_ascii=False))
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(json.dumps(build_result("error",
                                      error_type="request_error",
                                      error_message=str(e)),
                         ensure_ascii=False))
        sys.exit(1)
    finally:
        for f in file_handles:
            f.close()


if __name__ == "__main__":
    main()
