#!/usr/bin/env python3
"""Send a file to the user via Telegram Bot API.
Requires HERMES_TELEGRAM_BOT_TOKEN and HERMES_TELEGRAM_CHAT_ID environment variables.
Usage: python send-telegram.py <file_path> [caption]
"""
import os, sys, json, urllib.request, urllib.error

def main():
    if len(sys.argv) < 2:
        print("Usage: python send-telegram.py <file_path> [caption]", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    token = os.environ.get("HERMES_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("HERMES_TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("ERROR: HERMES_TELEGRAM_BOT_TOKEN or HERMES_TELEGRAM_CHAT_ID not set.", file=sys.stderr)
        print("  export HERMES_TELEGRAM_BOT_TOKEN=\"1234...ort HERMES_TELEGRAM_CHAT_ID=\"87654321\"", file=sys.stderr)
        sys.exit(1)

    url = f"https://api.telegram.org/bot{token}/sendDocument"

    import mimetypes
    mime_type, _ = mimetypes.guess_type(filepath)
    if not mime_type:
        mime_type = "application/octet-stream"

    boundary = "----HermesHtmlDeliveryBoundary"
    filename = os.path.basename(filepath)

    body_parts = []
    body_parts.append(f"--{boundary}")
    body_parts.append(f'Content-Disposition: form-data; name="chat_id"')
    body_parts.append("")
    body_parts.append(chat_id)

    if caption:
        body_parts.append(f"--{boundary}")
        body_parts.append(f'Content-Disposition: form-data; name="caption"')
        body_parts.append("")
        body_parts.append(caption)

    body_parts.append(f"--{boundary}")
    body_parts.append(f'Content-Disposition: form-data; name="document"; filename="{filename}"')
    body_parts.append(f"Content-Type: {mime_type}")
    body_parts.append("")

    body = "\r\n".join(body_parts).encode("utf-8")
    with open(filepath, "rb") as f:
        body += b"\r\n" + f.read() + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                msg_id = result.get("result", {}).get("message_id", "?")
                print(f"OK: Delivered to Telegram (message_id={msg_id})")
            else:
                print(f"ERROR: Telegram API returned: {result.get('description', 'unknown error')}", file=sys.stderr)
                sys.exit(1)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"ERROR: HTTP {e.code} — {body[:200]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
