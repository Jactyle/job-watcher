"""The Globe page places each country on the map from a table in globe.js, and the service worker caches a list of
site files. These checks keep both in step with country.js and the repository, using only the standard library."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def js_block(name, text):
    """The text of `const NAME = { ... };` up to its closing line."""
    start = text.index(f"const {name} = {{")
    return text[start:text.index("\n};", start)]


def countries_in_country_js():
    block = js_block("COUNTRY_RULES", (ROOT / "country.js").read_text())
    return set(re.findall(r'"([A-Z][^"]*)": \[', block))   # several countries can share a line


def positions_in_globe_js():
    block = js_block("COUNTRY_POS", (ROOT / "globe.js").read_text())
    return {name: (float(a), float(b)) for name, a, b in re.findall(r'"([^"]+)": \[(-?[\d.]+), (-?[\d.]+)\]', block)}


def test_every_country_countryOf_can_return_has_a_place_on_the_globe():
    names = countries_in_country_js()
    assert len(names) > 60                       # the parse found the whole table, not a few lines
    assert names - set(positions_in_globe_js()) == set()


def test_globe_positions_are_valid_latitudes_and_longitudes():
    for name, (lat, lon) in positions_in_globe_js().items():
        assert -90 <= lat <= 90 and -180 <= lon <= 180, name


def test_land_outline_is_a_topology_with_a_land_object():
    topo = json.loads((ROOT / "land-110m.json").read_text())
    assert topo["type"] == "Topology"
    assert topo["objects"]["land"]["geometries"] and topo["arcs"] and topo["transform"]


def test_service_worker_caches_only_files_that_exist_and_includes_every_page():
    sw = (ROOT / "sw.js").read_text()
    shell = re.search(r"const SHELL = \[(.*?)\];", sw, re.S).group(1)
    files = re.findall(r'"([^"]+)"', shell)
    for f in files:                              # cache.addAll fails the whole install if one file is missing
        assert f == "./" or (ROOT / f).exists(), f
    for page in ["index.html", "browse.html", "market.html", "globe.html", "globe.js", "land-110m.json"]:
        assert page in files, page


def test_every_page_links_the_same_navigation():
    pages = re.findall(r'\["([a-z]+\.html)", "', (ROOT / "app.js").read_text())
    assert pages == ["index.html", "browse.html", "market.html", "globe.html"]
    for p in pages:
        assert (ROOT / p).exists()


def test_every_page_loads_sfx_before_app_js():
    """app.js uses the sound module (sfx.js) while it starts, so each page must load sfx.js first."""
    for page in ["index.html", "browse.html", "market.html", "globe.html"]:
        html = (ROOT / page).read_text()
        assert html.index('<script src="sfx.js">') < html.index('<script src="app.js">'), page


def test_manifest_icons_exist_and_a_maskable_one_is_offered():
    manifest = json.loads((ROOT / "manifest.webmanifest").read_text())
    for icon in manifest["icons"]:
        assert (ROOT / icon["src"]).exists(), icon["src"]
    assert any(i["purpose"] == "maskable" for i in manifest["icons"])
    assert {"192x192", "512x512"} <= {i["sizes"] for i in manifest["icons"]}


def test_every_page_decides_about_the_startup_monitor_before_it_paints():
    """The dead-monitor intro is switched on by a small script in each head (once per session; never for automation, deep links,
    reduced motion or FX off), and app.js and the stylesheet carry the rest."""
    for page in ["index.html", "browse.html", "market.html", "globe.html"]:
        head = (ROOT / page).read_text().split("</head>")[0]
        assert "job-watcher-booted" in head and "navigator.webdriver" in head and "prefers-reduced-motion" in head, page
    assert 'classList.contains("intro")' in (ROOT / "app.js").read_text()
    css = (ROOT / "app.css").read_text()
    assert "html.intro" in css and ".crt-half" in css and "introsafety" in css


def test_every_terminal_has_its_own_background_loop_and_ambient_sound():
    """Each page theme needs a visual loop (app.js and app.css) and a scene in the ambient sound (sfx.js)."""
    js, css, sfx = (ROOT / "app.js").read_text(), (ROOT / "app.css").read_text(), (ROOT / "sfx.js").read_text()
    for theme in ["today", "browse", "market", "globe"]:
        assert f".bg-{theme}" in css, theme
        assert f"{theme}:" in js.split("backgroundLoop")[1], theme
        assert f"    {theme}(c, k)" in sfx, theme


def test_every_page_shares_one_palette():
    """The outline asks for one set of fonts and colors. The four page themes may differ in patterns, shapes and motion, but a
    theme block in app.css must not define color tokens: the palette lives only in :root."""
    css = (ROOT / "app.css").read_text()
    blocks = re.findall(r'html\[data-theme="(\w+)"\] \{([^}]*)\}', css)
    assert {name for name, _ in blocks} == {"today", "browse", "market", "globe"}
    for name, body in blocks:
        tokens = set(re.findall(r"(--[\w-]+):", body))
        assert tokens <= {"--lattice"}, (name, tokens)
