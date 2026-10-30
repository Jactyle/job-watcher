"""country.js reads a country from a location string for the Market page's outside-the-US chart.
It is browser code, so these tests run it with node (skipped where node is not installed)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")
ROOT = Path(__file__).resolve().parent.parent

SCRIPT = """
const fs = require('fs'), vm = require('vm');
const [file, cases] = process.argv.slice(-2);
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(file, 'utf8') + '\\nthis.countryOf = countryOf;', ctx);
console.log(JSON.stringify(JSON.parse(cases).map(s => ctx.countryOf(s))));
"""


def countries(*locations):
    out = subprocess.run([NODE, "-e", SCRIPT, str(ROOT / "country.js"), json.dumps(list(locations))],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


@pytest.mark.parametrize("location, country", [
    ("Redmond, WA, US", "United States"),
    ("McLean, VA", "United States"),           # a state code is a state, not a country
    ("Palo Alto, CA", "United States"),
    ("Toronto, ON, CA", "Canada"),            # the same CA at the end of a three-part place is Canada
    ("Bangalore, KA, IN", "India"),
    ("Barcelona, CT, ES", "Spain"),
    ("Perth, WA, AU; Adelaide, SA, AU", "Australia"),
    ("IND", "India"),
    ("Luxembourg, LUX", "Luxembourg"),
    ("Remote - India", "India"),
    ("Ireland - Dublin", "Ireland"),
    ("Mexico City, Mexico", "Mexico"),
    ("Baja California, Baja California, Mexico", "Mexico"),
    ("New Mexico", "United States"),
    ("San Jose, Costa Rica", "Costa Rica"),
    ("Spring Texas United States of America", "United States"),
    ("Rockville MD", "United States"),        # an address ending in a state code
])
def test_country_of_a_location(location, country):
    assert countries(location) == [country]


def test_a_posting_that_lists_a_us_place_counts_as_us():
    assert countries("Remote within Canada or United States",
                     "Seattle, San Francisco, New York, Chicago, Atlanta, Remote in the US, Canada") == ["United States"] * 2


def test_a_location_with_no_country_is_unknown_not_guessed():
    assert countries("Hybrid", "Remote", "Multiple Locations", "", "N/A") == [None] * 5
