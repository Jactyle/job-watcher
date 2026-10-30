// Works out the country of a posting from its location text, because the history file has no country column.
// countryOf("Redmond, WA, US") -> "United States"; countryOf("Remote - India") -> "India"; countryOf("Hybrid") -> null.
// It knows country names and codes, US states, and the cities that appear on the watched boards. Anything else is
// unknown (null) and is counted as such instead of being guessed.
const COUNTRY_RULES = {
  "United States": ["united states of america", "united states", "usa", "u.s.a", "u.s.", "us", "america", "d.c.",
    "washington dc", "washington, dc", "district of columbia", "puerto rico",
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware", "florida", "georgia", "hawaii",
    "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming",
    "santa clara", "san francisco", "san jose", "sunnyvale", "cupertino", "mountain view", "palo alto", "menlo park", "redwood city",
    "san mateo", "oakland", "los angeles", "culver city", "santa monica", "irvine", "san diego", "sacramento", "seattle", "bellevue",
    "redmond", "kirkland", "portland", "hillsboro", "austin", "dallas", "houston", "plano", "frisco", "san antonio", "boston",
    "cambridge", "chicago", "denver", "boulder", "atlanta", "miami", "phoenix", "tempe", "salt lake city", "mclean", "arlington",
    "reston", "richmond", "plano", "charlotte", "raleigh", "durham", "nashville", "detroit", "pittsburgh", "philadelphia", "new york city",
    "brooklyn", "las vegas", "orlando", "tampa", "minneapolis", "st. louis", "saint louis", "kansas city", "columbus", "cleveland",
    "remote us", "bay area", "nyc", "lehi", "provo", "salt lake"],
  "Canada": ["canada", "ontario", "quebec", "alberta", "british columbia", "toronto", "vancouver", "montreal", "ottawa", "calgary", "waterloo", "kitchener"],
  "United Kingdom": ["united kingdom", "great britain", "england", "scotland", "wales", "northern ireland", "uk", "london", "manchester",
    "edinburgh", "nottingham", "weybridge", "abingdon", "reading, uk", "cambridge, uk", "belfast", "birmingham, uk", "bristol", "glasgow", "leeds"],
  "Ireland": ["ireland", "dublin", "cork", "galway", "limerick"],
  "India": ["india", "bangalore", "bengaluru", "hyderabad", "pune", "chennai", "mumbai", "gurgaon", "gurugram", "noida", "delhi", "new delhi",
    "kolkata", "ahmedabad", "kochi", "jaipur", "chandigarh", "coimbatore", "thiruvananthapuram", "indore", "nagpur"],
  "China": ["china", "dalian", "shanghai", "beijing", "shenzhen", "guangzhou", "hangzhou", "chengdu", "nanjing", "suzhou", "wuhan", "xi'an", "chongqing"],
  "Japan": ["japan", "minato", "tokyo", "osaka", "yokohama", "kyoto", "nagoya", "fukuoka"],
  "South Korea": ["south korea", "korea", "seoul", "busan", "pangyo"],
  "Taiwan": ["taiwan", "taipei", "hsinchu", "taichung", "kaohsiung"],
  "Singapore": ["singapore"],
  "Malaysia": ["malaysia", "penang", "kuala lumpur", "johor", "selangor", "cyberjaya"],
  "Philippines": ["philippines", "manila", "cebu", "taguig", "makati", "muntinlupa", "alabang", "quezon city"],
  "Vietnam": ["vietnam", "viet nam", "hanoi", "ho chi minh", "da nang"],
  "Thailand": ["thailand", "bangkok"], "Indonesia": ["indonesia", "jakarta"], "Hong Kong": ["hong kong"],
  "Australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "canberra", "adelaide"], "New Zealand": ["new zealand", "auckland", "wellington"],
  "Israel": ["israel", "tel aviv", "yokneam", "haifa", "herzliya", "jerusalem", "ra'anana", "raanana", "petah tikva", "kfar saba", "netanya"],
  "United Arab Emirates": ["united arab emirates", "uae", "dubai", "abu dhabi"], "Saudi Arabia": ["saudi arabia", "riyadh", "jeddah"],
  "Egypt": ["egypt", "cairo"], "Turkey": ["turkey", "turkiye", "istanbul", "ankara"], "South Africa": ["south africa", "johannesburg", "cape town"],
  "Nigeria": ["nigeria", "lagos"], "Kenya": ["kenya", "nairobi"], "Morocco": ["morocco", "casablanca"], "Pakistan": ["pakistan", "karachi", "lahore"],
  "Germany": ["germany", "deutschland", "berlin", "munich", "hamburg", "frankfurt", "cologne", "stuttgart", "dusseldorf", "dresden", "nuremberg"],
  "France": ["france", "paris", "lyon", "toulouse", "bordeaux", "nantes", "montpellier", "lille", "marseille", "rennes", "annecy", "saint-denis"],
  "Spain": ["spain", "madrid", "barcelona", "valencia", "seville", "malaga", "bilbao"], "Portugal": ["portugal", "lisbon", "porto"],
  "Italy": ["italy", "milan", "rome", "turin", "bologna", "naples"], "Netherlands": ["netherlands", "the netherlands", "amsterdam", "rotterdam", "eindhoven", "the hague", "utrecht"],
  "Belgium": ["belgium", "brussels", "antwerp", "leuven"], "Luxembourg": ["luxembourg", "luxemburg"], "Switzerland": ["switzerland", "zurich", "geneva", "lausanne", "basel", "zug"],
  "Austria": ["austria", "vienna", "wien", "graz"], "Sweden": ["sweden", "stockholm", "gothenburg", "malmo", "lund"], "Norway": ["norway", "oslo", "bergen", "lysaker"],
  "Denmark": ["denmark", "copenhagen", "aarhus"], "Finland": ["finland", "helsinki", "espoo", "tampere", "oulu"], "Iceland": ["iceland", "reykjavik"],
  "Poland": ["poland", "warsaw", "krakow", "wroclaw", "gdansk", "poznan", "katowice", "lodz"], "Czech Republic": ["czech republic", "czechia", "prague", "brno"],
  "Slovakia": ["slovakia", "bratislava", "kosice"], "Hungary": ["hungary", "budapest"], "Romania": ["romania", "bucharest", "cluj", "cluj-napoca", "iasi", "timisoara"],
  "Bulgaria": ["bulgaria", "sofia", "plovdiv"], "Greece": ["greece", "athens", "thessaloniki"], "Serbia": ["serbia", "belgrade", "novi sad"], "Croatia": ["croatia", "zagreb"],
  "Ukraine": ["ukraine", "kyiv", "kiev", "lviv"], "Lithuania": ["lithuania", "vilnius", "kaunas"], "Latvia": ["latvia", "riga"], "Estonia": ["estonia", "tallinn", "tartu"],
  "Mexico": ["mexico", "baja california", "mexico city", "guadalajara", "monterrey", "tlaquepaque", "jalisco", "queretaro"], "Brazil": ["brazil", "brasil", "sao paulo", "rio de janeiro", "campinas", "curitiba", "belo horizonte", "porto alegre"],
  "Argentina": ["argentina", "buenos aires", "cordoba"], "Colombia": ["colombia", "bogota", "medellin"], "Chile": ["chile", "santiago"], "Peru": ["peru", "lima"],
  "Costa Rica": ["costa rica", "san jose, costa rica", "heredia"], "Panama": ["panama"], "Uruguay": ["uruguay", "montevideo"], "Guatemala": ["guatemala"],
  "Armenia": ["armenia", "yerevan"], "Slovenia": ["slovenia", "ljubljana"], "Tunisia": ["tunisia", "tunis", "ariana"], "Qatar": ["qatar", "doha"],
  "Dominican Republic": ["dominican republic", "santo domingo"],
};
// Two- and three-letter codes, matched only as a whole comma/dash-separated part of the text.
const CODE2 = { us: "United States", ca: "Canada", gb: "United Kingdom", uk: "United Kingdom", ie: "Ireland", in: "India", cn: "China", jp: "Japan", kr: "South Korea",
  tw: "Taiwan", sg: "Singapore", my: "Malaysia", ph: "Philippines", vn: "Vietnam", th: "Thailand", id: "Indonesia", hk: "Hong Kong", au: "Australia", nz: "New Zealand",
  il: "Israel", ae: "United Arab Emirates", sa: "Saudi Arabia", eg: "Egypt", tr: "Turkey", za: "South Africa", ng: "Nigeria", ke: "Kenya", ma: "Morocco", pk: "Pakistan",
  de: "Germany", fr: "France", es: "Spain", pt: "Portugal", it: "Italy", nl: "Netherlands", be: "Belgium", lu: "Luxembourg", ch: "Switzerland", at: "Austria", se: "Sweden",
  no: "Norway", dk: "Denmark", fi: "Finland", pl: "Poland", cz: "Czech Republic", sk: "Slovakia", hu: "Hungary", ro: "Romania", bg: "Bulgaria", gr: "Greece", rs: "Serbia",
  hr: "Croatia", ua: "Ukraine", lt: "Lithuania", lv: "Latvia", ee: "Estonia", mx: "Mexico", br: "Brazil", ar: "Argentina", co: "Colombia", cl: "Chile", pe: "Peru", cr: "Costa Rica" };
const CODE3 = { usa: "United States", can: "Canada", gbr: "United Kingdom", irl: "Ireland", ind: "India", chn: "China", jpn: "Japan", kor: "South Korea", twn: "Taiwan",
  sgp: "Singapore", mys: "Malaysia", phl: "Philippines", vnm: "Vietnam", tha: "Thailand", idn: "Indonesia", hkg: "Hong Kong", aus: "Australia", nzl: "New Zealand",
  isr: "Israel", are: "United Arab Emirates", sau: "Saudi Arabia", egy: "Egypt", tur: "Turkey", zaf: "South Africa", nga: "Nigeria", ken: "Kenya", mar: "Morocco", pak: "Pakistan",
  deu: "Germany", fra: "France", esp: "Spain", prt: "Portugal", ita: "Italy", nld: "Netherlands", bel: "Belgium", lux: "Luxembourg", che: "Switzerland", aut: "Austria",
  swe: "Sweden", nor: "Norway", dnk: "Denmark", fin: "Finland", pol: "Poland", cze: "Czech Republic", svk: "Slovakia", hun: "Hungary", rou: "Romania", bgr: "Bulgaria",
  grc: "Greece", srb: "Serbia", hrv: "Croatia", ukr: "Ukraine", ltu: "Lithuania", lva: "Latvia", est: "Estonia", mex: "Mexico", bra: "Brazil", arg: "Argentina",
  col: "Colombia", chl: "Chile", per: "Peru", cri: "Costa Rica" };
const US_STATE_CODES = new Set("al ak az ar ca co ct de fl ga hi id il in ia ks ky la me md ma mi mn ms mo mt ne nv nh nj nm ny nc nd oh ok or pa ri sc sd tn tx ut vt va wa wv wi wy dc".split(" "));

const _plain = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[–—]/g, "-");
const _escape = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const _byName = new Map();
for (const [country, names] of Object.entries(COUNTRY_RULES)) for (const n of names) if (!_byName.has(n)) _byName.set(n, country);
// longest names first, so "united states of america" wins over "united states" and "new mexico" over "mexico"
const _names = new RegExp("(?:^|[^a-z])(" + [..._byName.keys()].sort((a, b) => b.length - a.length).map(_escape).join("|") + ")(?![a-z])", "g");

function _classify(location) {
  const s = _plain(location);
  if (!s) return null;
  const parts = s.split(/\s*(?:[,;|()\/]|\s-\s|---)\s*/).map(p => p.trim()).filter(Boolean);
  const hits = [];                                   // { pos, country, rank }: rank 2 = a country, 1 = a state or city
  let from = 0;
  parts.forEach((part, i) => {
    const pos = s.indexOf(part, from); from = Math.max(from, pos);
    if (part.length === 2 && /^[a-z]{2}$/.test(part)) {
      // "Bangalore, KA, IN" ends in a country code; "McLean, VA" ends in a state; a code alone is a state if it is one.
      const last = i === parts.length - 1, afterCode = i > 0 && parts[i - 1].length <= 2;
      if (last && afterCode && CODE2[part]) hits.push({ pos, name: part, country: CODE2[part], rank: 2 });
      else if (US_STATE_CODES.has(part)) hits.push({ pos, name: part, country: "United States", rank: 1 });
      else if (CODE2[part]) hits.push({ pos, name: part, country: CODE2[part], rank: 2 });
    } else if (CODE3[part]) hits.push({ pos, name: part, country: CODE3[part], rank: 2 });
  });
  for (const m of s.matchAll(_names)) {
    const name = m[1];
    hits.push({ pos: m.index + m[0].length - name.length, name, country: _byName.get(name), rank: COUNTRY_NAMES.has(name) ? 2 : 1 });
  }
  if (!hits.length) {  // street addresses end in a state code ("Rockville MD"); "CA Work From Home" starts with one
    const words = s.split(/[\s,]+/).filter(Boolean);
    if (words.length > 1 && (US_STATE_CODES.has(words[words.length - 1]) || (US_STATE_CODES.has(words[0]) && /work from home/.test(s)))) return "United States";
  }
  // A posting that lists a US location at all is not "outside the US": a US country marker, or two or more US places, makes it US.
  const us = hits.filter(h => h.country === "United States");
  if (us.some(h => h.rank === 2) || new Set(us.map(h => h.name)).size >= 2) return "United States";
  const pick = rank => hits.filter(h => h.rank === rank).sort((a, b) => a.pos - b.pos).pop();
  const best = pick(2) || pick(1);
  return best ? best.country : null;
}
const _memo = new Map();
function countryOf(location) {
  const key = location || "";
  if (!_memo.has(key)) _memo.set(key, _classify(key));
  return _memo.get(key);
}

// The names that are a country itself (the others are states, regions and cities).
const COUNTRY_NAMES = new Set(["united states of america", "united states", "usa", "u.s.a", "u.s.", "us", "america", "canada", "united kingdom", "great britain", "england", "scotland",
  "wales", "northern ireland", "ireland", "india", "china", "japan", "south korea", "korea", "taiwan", "singapore", "malaysia", "philippines", "vietnam", "viet nam", "thailand",
  "indonesia", "hong kong", "australia", "new zealand", "israel", "united arab emirates", "uae", "saudi arabia", "egypt", "turkey", "turkiye", "south africa", "nigeria", "kenya",
  "morocco", "pakistan", "germany", "deutschland", "france", "spain", "portugal", "italy", "netherlands", "the netherlands", "belgium", "luxembourg", "luxemburg", "switzerland",
  "austria", "sweden", "norway", "denmark", "finland", "iceland", "poland", "czech republic", "czechia", "slovakia", "hungary", "romania", "bulgaria", "greece", "serbia",
  "croatia", "ukraine", "lithuania", "latvia", "estonia", "mexico", "brazil", "brasil", "argentina", "colombia", "chile", "peru", "costa rica", "panama", "uruguay", "guatemala", "uk"]);
