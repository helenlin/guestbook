import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_PATH = ROOT / "guestbook.md"
JSON_PATH = ROOT / "guestbook.json"
MARKDOWN_ESCAPE = re.compile(r"([\\`*_{}\[\]()#+.!|<>~-])")


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def escaped_markdown(value):
    return MARKDOWN_ESCAPE.sub(r"\\\1", value).replace("\n", "<br>")


def main():
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        fail("GITHUB_EVENT_PATH is not set")

    with open(event_path, encoding="utf-8") as event_file:
        event = json.load(event_file)

    issue = event.get("issue", {})
    title = issue.get("title", "")
    if not title.startswith("Guestbook: "):
        fail("Issue is not a guestbook entry")

    name = " ".join(title[len("Guestbook: "):].split())[:60]
    message = issue.get("body") or ""
    message = "\n".join(line.rstrip() for line in message.splitlines()).strip()
    if not name or not message:
        fail("Guestbook entries require a name and a message")
    if len(message) > 500:
        fail("Guestbook messages must be 500 characters or fewer")

    issue_number = issue.get("number")
    if not isinstance(issue_number, int) or issue_number < 1:
        fail("Issue number is missing or invalid")

    try:
        entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Could not read {JSON_PATH.name}: {error}")
    if not isinstance(entries, list):
        fail(f"{JSON_PATH.name} must contain a JSON array")

    if any(entry.get("issue") == issue_number for entry in entries if isinstance(entry, dict)):
        print(f"Issue #{issue_number} is already in the guestbook.")
        return

    entries.append({
        "issue": issue_number,
        "name": name,
        "message": message,
        "created_at": issue.get("created_at", ""),
    })
    entries.sort(key=lambda entry: entry["issue"])

    markdown = [
        "# Guestbook",
        "",
        "Messages submitted through GitHub Issues appear here.",
        "",
    ]
    for entry in entries:
        markdown.extend([
            f"## {escaped_markdown(entry['name'])}",
            "",
            escaped_markdown(entry["message"]),
            "",
            f"*Issue #{entry['issue']} - {entry['created_at'][:10]}*",
            "",
        ])

    MARKDOWN_PATH.write_text("\n".join(markdown), encoding="utf-8")
    JSON_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Recorded guestbook entry from issue #{issue_number}.")


if __name__ == "__main__":
    main()
