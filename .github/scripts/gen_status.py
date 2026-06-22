#!/usr/bin/env python3
"""Generate a live-status SVG card by probing public service endpoints.

Contract:
  - Input: the hardcoded SERVICES list only (no untrusted input).
  - For each service: HTTP GET with a timeout; capture (up, http_code, latency_ms).
    Any failure (timeout, DNS, TLS, connection reset) => down, and NEVER raises.
  - Output: writes dist/status.svg, overwriting. Exit 0 even if every service is down
    (a down service is data, not a script error).
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("dist/status.svg")
TIMEOUT = 12  # seconds, per service
SERVICES = [
    ("daaeonyxai.com", "https://daaeonyxai.com"),
    ("app · dashboard", "https://app.daaeonyxai.com"),
    ("frontierbenchmarks.com", "https://frontierbenchmarks.com"),
]


def probe(url: str) -> tuple[bool, int | None, int | None]:
    """Return (up, http_code, latency_ms). Never raises.

    A reachable host that answers < 500 counts as up. Anything that prevents a
    response (timeout, DNS, TLS, refused) counts as down with no code.
    """
    req = urllib.request.Request(
        url, method="GET",
        headers={"User-Agent": "Sthiven-R status probe (github-actions)"},
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ms = int((time.monotonic() - start) * 1000)
            return True, resp.status, ms
    except urllib.error.HTTPError as e:  # reachable, but error status
        ms = int((time.monotonic() - start) * 1000)
        return e.code < 500, e.code, ms
    except Exception:  # unreachable: timeout / DNS / TLS / refused
        return False, None, None


def tile(x: int, label: str, up: bool, code: int | None, ms: int | None) -> str:
    color = "#2ea043" if up else "#f85149"
    state = "UP" if up else "DOWN"
    if up and code is not None:
        detail = f"{code} · {ms}ms"
    elif code is not None:
        detail = str(code)
    else:
        detail = "unreachable"
    pulse = (
        '<animate attributeName="opacity" values="1;0.3;1" dur="1.8s" repeatCount="indefinite"/>'
        if up else ""
    )
    return (
        f'  <g transform="translate({x},0)">\n'
        f'    <circle cx="0" cy="80" r="5" fill="{color}">{pulse}</circle>\n'
        f'    <text x="16" y="76" font-size="13" fill="#e6edf3">{label}</text>\n'
        f'    <text x="16" y="94" font-size="11" fill="{color}">{state} · '
        f'<tspan fill="#7d8590">{detail}</tspan></text>\n'
        f'  </g>'
    )


def main() -> None:
    xs = [56, 336, 616]
    tiles = [
        tile(x, label, *probe(url))
        for x, (label, url) in zip(xs, SERVICES)
    ]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 120" width="840" height="120" '
        "font-family=\"ui-monospace, 'SF Mono', Consolas, monospace\" role=\"img\" "
        'aria-label="Live status of Sthiven R. services">\n'
        '  <rect x="8" y="8" width="824" height="104" rx="14" fill="#0a0e14" stroke="#22d3ee" stroke-opacity="0.22"/>\n'
        '  <circle cx="34" cy="34" r="4" fill="#22d3ee"><animate attributeName="opacity" values="1;0.3;1" dur="1.4s" repeatCount="indefinite"/></circle>\n'
        '  <text x="48" y="38" font-size="12" letter-spacing="2" fill="#22d3ee">LIVE STATUS</text>\n'
        f'  <text x="808" y="38" font-size="10" letter-spacing="1" fill="#576070" text-anchor="end">checked {stamp} · every 6h</text>\n'
        '  <line x1="24" y1="52" x2="816" y2="52" stroke="#1f2937"/>\n'
        + "\n".join(tiles) + "\n"
        "</svg>\n"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
