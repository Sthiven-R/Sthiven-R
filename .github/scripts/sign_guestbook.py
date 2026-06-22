#!/usr/bin/env python3
"""Append a sanitized guestbook signature to the profile README.

TRUST BOUNDARY: ISSUE_BODY is attacker-controlled — anyone can open an issue.
GH_USER is GitHub-controlled (the authenticated login that opened the issue).

Defense:
  - The username is validated against GitHub's own format ([A-Za-z0-9-], <=39).
    Anything else is refused outright.
  - The message is reduced to ONE line, then filtered through a strict
    whitelist (letters/digits/space + a tiny set of safe punctuation). Every
    markdown/HTML control character (< > [ ] ( ) ` | * _ # ! ~ etc.) is dropped,
    so a signature cannot inject layout, links, images, or HTML.
  - Length is capped, and the total number of entries is capped.
We render only the sanitized text — never the raw body.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

README = Path("README.md")
START = "<!-- GUESTBOOK:START -->"
END = "<!-- GUESTBOOK:END -->"
MAX_LEN = 100
MAX_ENTRIES = 30

# Whitelist of characters allowed in a message. Everything else is stripped.
_DISALLOWED = re.compile(r"[^0-9A-Za-zÀ-ÿ \.,!\?'\-:;&]")
# GitHub username format.
_USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


def sanitize_message(body: str) -> str:
    # Issue-form bodies look like "### Your message\n\n<text>". Drop heading
    # lines and the form scaffolding, keep the rest as a single line.
    lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith("#")]
    text = " ".join(lines)
    text = _DISALLOWED.sub("", text)          # strip markdown/HTML control chars
    text = re.sub(r"\s+", " ", text).strip()  # collapse whitespace
    if len(text) > MAX_LEN:
        text = text[:MAX_LEN].rstrip() + "…"
    return text


def main() -> None:
    user = (os.environ.get("GH_USER") or "").strip()
    body = os.environ.get("ISSUE_BODY") or ""

    if not _USERNAME.match(user):
        print(f"refusing: invalid username {user!r}")
        return

    msg = sanitize_message(body) or "signed the guestbook"

    readme = README.read_text(encoding="utf-8")
    if START not in readme or END not in readme:
        print("guestbook markers not found; nothing to do")
        return

    pre, rest = readme.split(START, 1)
    _old_mid, post = rest.split(END, 1)

    existing = [
        ln for ln in _old_mid.splitlines() if ln.strip().startswith("- ")
    ]
    entry = f"- **[@{user}](https://github.com/{user})** — {msg}"
    entries = ([entry] + existing)[:MAX_ENTRIES]  # newest first, capped

    new_mid = "\n" + "\n".join(entries) + "\n"
    README.write_text(pre + START + new_mid + END + post, encoding="utf-8")
    print(f"added signature from @{user}: {msg!r}")


if __name__ == "__main__":
    main()
