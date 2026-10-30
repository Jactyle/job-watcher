"""Download each watched employer's icon into logos/<source>.png, so the site shows it next to that
employer's postings and serves it from its own address (no request to anyone else when you browse).

    python -m pipeline.logos [source ...]

Run it by hand when an employer is added or its icon changes; the daily run does not use it.
The icons are the employers' own, used only to identify them.
"""
from __future__ import annotations

import json
import re
import struct
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from .sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
LOGOS = ROOT / "logos"
ICON_SERVICE = "https://www.google.com/s2/favicons?sz=256&domain="
COMMON_PATHS = ["apple-touch-icon.png", "apple-touch-icon-180x180.png", "apple-touch-icon-precomposed.png",
                "android-chrome-512x512.png", "android-chrome-192x192.png", "favicon-196x196.png", "favicon-192x192.png", "favicon-96x96.png"]
MAX_BYTES = 5_000_000  # an icon is a few KB; never read more than this from a site
MIN_SHARP = 128  # px: enough for the largest tile (about 45 px across) on a high-density screen
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
PNG = b"\x89PNG\r\n\x1a\n"

# The website each source's icon is taken from.
DOMAINS = {
    "robinhood": "robinhood.com", "coinbase": "coinbase.com", "stripe": "stripe.com", "affirm": "affirm.com",
    "brex": "brex.com", "mercury": "mercury.com", "chime": "chime.com", "carta": "carta.com", "toast": "toasttab.com",
    "sofi": "sofi.com", "gusto": "gusto.com", "betterment": "betterment.com", "databricks": "databricks.com",
    "airbnb": "airbnb.com", "palantir": "palantir.com", "spotify": "spotify.com", "ramp": "ramp.com",
    "notion": "notion.so", "openai": "openai.com", "epicgames": "store.epicgames.com", "riotgames": "riotgames.com",
    "roblox": "roblox.com", "discord": "discord.com", "taketwo": "take2games.com", "rockstargames": "rockstargames.com",
    "bungie": "bungie.net", "scopely": "scopely.com", "twitch": "twitch.tv", "cloudflare": "cloudflare.com",
    "supercell": "supercell.com", "ubisoft": "ubisoft.com", "microsoft": "microsoft.com", "netflix": "netflix.com",
    "apple": "apple.com", "amazon": "amazon.com", "amd": "ir.amd.com", "servicenow": "servicenow.com",
    "fidelity": "fidelity.com", "mastercard": "mastercard.com", "capitalone": "capitalone.com", "sony": "sony.com",
    "intel": "intel.com", "samsung": "samsung.com", "adobe": "adobe.com", "cisco": "cisco.com",
    "salesforce": "salesforce.com", "snap": "snap.com", "hp": "hp.com", "nvidia": "nvidia.com",
}


def _get(url: str, timeout: int = 15) -> bytes:
    # Links come from other sites' pages, so only follow web addresses (urllib would also open file: ones).
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"not a web address: {url[:60]}")
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(MAX_BYTES)


def _is_png(data: bytes) -> bool:
    return data.startswith(PNG) and len(data) >= 24  # signature + the width and height that follow


def _size(png: bytes) -> int:
    """The smaller side of a PNG, so a wide banner does not look like a big icon."""
    return min(struct.unpack(">II", png[16:24]))


def _png_from_ico(data: bytes) -> bytes:
    """An .ico file can hold several sizes, some of them PNG; return the largest PNG inside (b"" if none)."""
    if len(data) < 6 or data[:4] != b"\x00\x00\x01\x00":
        return b""
    best = b""
    for i in range(struct.unpack("<H", data[4:6])[0]):
        entry = data[6 + 16 * i: 22 + 16 * i]
        if len(entry) < 16:
            break
        length, offset = struct.unpack("<II", entry[8:16])
        image = data[offset: offset + length]
        if _is_png(image) and (not best or _size(image) > _size(best)):
            best = image
    return best


def _icon_urls(domain: str):
    """Places a site's icon may be: the icon service, the icon links in its home page, its web manifest, common paths."""
    yield ICON_SERVICE + urllib.parse.quote(domain)
    for host in (domain, "www." + domain):
        base = f"https://{host}/"
        try:
            html = _get(base).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 - blocked or down: the common paths may still work
            html = ""
        for tag in re.findall(r"<link[^>]+>", html, re.I):
            href = re.search(r"href=[\"']([^\"']+)", tag, re.I)
            if not href:
                continue
            if re.search(r"rel=[\"'][^\"']*icon", tag, re.I):
                yield urllib.parse.urljoin(base, href.group(1))
            elif re.search(r"rel=[\"']manifest", tag, re.I):
                try:
                    manifest_url = urllib.parse.urljoin(base, href.group(1))
                    for icon in json.loads(_get(manifest_url)).get("icons", []):
                        yield urllib.parse.urljoin(manifest_url, icon["src"])
                except Exception:  # noqa: BLE001 - no usable manifest
                    pass
        for path in COMMON_PATHS:
            yield base + path


def fetch_icon(domain: str) -> bytes:
    """The largest PNG found for the site. It stops early once one is sharp enough (MIN_SHARP px)."""
    best = b""
    for url in _icon_urls(domain):
        try:
            data = _get(url)
        except Exception:  # noqa: BLE001 - not there, try the next place
            continue
        data = data if _is_png(data) else _png_from_ico(data)
        if _is_png(data) and (not best or _size(data) > _size(best)):
            best = data
            if _size(best) >= MIN_SHARP:
                break
    if not best:
        raise ValueError("no icon found")
    return best


def main(argv: list[str]) -> int:
    names = argv or [s["name"] for s in SOURCES]
    LOGOS.mkdir(exist_ok=True)
    failed = []
    for name in names:
        path = LOGOS / f"{name}.png"
        try:
            data = fetch_icon(DOMAINS[name])
            old = _size(path.read_bytes()) if path.exists() else 0
            if _size(data) > old:  # never replace a logo with a smaller one
                path.write_bytes(data)
                print(f"ok     {name} <- {DOMAINS[name]}  {old or '-'} -> {_size(data)} px")
            else:
                print(f"kept   {name}  {old} px (nothing larger found)")
        except Exception as exc:  # noqa: BLE001 - report it and carry on with the rest
            failed.append(name)
            print(f"FAILED {name}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
