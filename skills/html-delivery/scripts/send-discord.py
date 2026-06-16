#!/usr/bin/env python3
"""Send a file to the user via Discord webhook.
Requires HERMES_DISCORD_WEBHOOK environment variable.
Usage: python send-discord.py <file_path> [message]
"""
import os, sys, json, urllib.request, urllib.error

def main():
    if len(sys.argv) < 2:
        print("Usage: python send-discord.py <file_path> [message]", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    message = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    webhook_url = os.environ.get("HERMES_DISCORD_WEBHOOK", "").strip()
    if not webhook_url:
        print("ERROR: HERMES_DISCORD_WEBHOOK not set.", file=sys.stderr)
        print("  export HERMES_DISCORD_WEBHOOK=\"https://discord.com/api/webhooks/...\"", file=sys.stderr)
        sys.exit(1)

    boundary = "----HermesHtmlDeliveryBoundary"
    filename = os.path.basename(filepath)

    body_parts = []
    if message:
        body_parts.append(f"--{boundary}")
        body_parts.append('Content-Disposition: form-data; name="content"')
        body_parts.append("")
        body_parts.append(message)

    body_parts.append(f"--{boundary}")
    body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"')
    body_parts.append("Content-Type: application/octet-stream")
    body_parts.append("")

    body = "\r\n".join(body_parts).encode("utf-8")
    with open(filepath, "rb") as f:
        body += b"\r\n" + f.read() + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(webhook_url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                print("OK: Delivered to Discord")
            else:
                print(f"ERROR: Discord returned HTTP {resp.status}", file=sys.stderr)
                sys.exit(1)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"ERROR: HTTP {e.code} — {body_text[:200]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
