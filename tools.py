"""
tools.py  -  live gadgets that compute the answer instead of looking it up

  time     Python's clock + zoneinfo        (no internet, no key)
  calc     safe arithmetic evaluator        (no internet, no key)
  weather  Open-Meteo geocoding + forecast  (free, no key, needs internet)
"""
import ast
import operator as op
import re
from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

import requests

HEADERS = {"User-Agent": "PipsPocket/1.0 (learning project)"}

# ------------------------------------------------------------ place parsing --
_NOISE = set("what whats is the a current time date weather forecast temperature today now right "
             "like in at for of how hot cold it please tell me".split())


def _place(q):
    m = re.search(r"\b(?:in|at|for|of)\s+([a-zA-Z][a-zA-Z .'-]{1,40}?)"
                  r"(?:\s+(?:now|right now|today|currently|at the moment|please))*\s*[?.!]*$", q.strip(), re.I)
    if m:
        return m.group(1).strip()
    rest = [w for w in re.findall(r"[A-Za-z']+", q) if w.lower() not in _NOISE]
    return " ".join(rest) or None


# ---------------------------------------------------------------------- time --
_COUNTRY_TZ = {
    "india": "Asia/Kolkata", "delhi": "Asia/Kolkata", "mumbai": "Asia/Kolkata", "hyderabad": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata", "bengaluru": "Asia/Kolkata", "chennai": "Asia/Kolkata", "pune": "Asia/Kolkata",
    "japan": "Asia/Tokyo", "uk": "Europe/London", "england": "Europe/London", "britain": "Europe/London",
    "france": "Europe/Paris", "germany": "Europe/Berlin", "italy": "Europe/Rome", "spain": "Europe/Madrid",
    "usa": "America/New_York", "us": "America/New_York", "new york": "America/New_York",
    "california": "America/Los_Angeles", "san francisco": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles", "texas": "America/Chicago",
    "canada": "America/Toronto", "uae": "Asia/Dubai", "china": "Asia/Shanghai", "beijing": "Asia/Shanghai",
    "korea": "Asia/Seoul", "south korea": "Asia/Seoul", "australia": "Australia/Sydney",
    "russia": "Europe/Moscow", "egypt": "Africa/Cairo", "nepal": "Asia/Kathmandu", "pakistan": "Asia/Karachi",
    "sri lanka": "Asia/Colombo", "bangladesh": "Asia/Dhaka", "brazil": "America/Sao_Paulo",
    "south africa": "Africa/Johannesburg", "nigeria": "Africa/Lagos", "kenya": "Africa/Nairobi",
    "saudi arabia": "Asia/Riyadh", "turkey": "Europe/Istanbul", "thailand": "Asia/Bangkok",
    "vietnam": "Asia/Ho_Chi_Minh", "indonesia": "Asia/Jakarta", "mexico": "America/Mexico_City",
}
_CITY_TZ = {z.split("/")[-1].replace("_", " ").lower(): z for z in available_timezones() if "/" in z}


def _fmt_time(now, label, tz):
    off = now.strftime("%z")
    clock = now.strftime("%I:%M %p").lstrip("0")
    return (f"It is **{clock}** on {now.strftime('%A, %d %B %Y')} in {label}.\n\n"
            f"- Time zone: {tz} (UTC{off[:3]}:{off[3:]})")


def current_time(q):
    place = _place(q)
    if not place:
        now = datetime.now().astimezone()
        return _fmt_time(now, "your own time zone (from your Mac's clock)", now.tzname())
    key = place.lower().strip(" .")
    tz = _COUNTRY_TZ.get(key) or _CITY_TZ.get(key)
    if not tz:
        return (f"I don't know the time zone for '{place}' yet. Try a major city or country, "
                "or add it to _COUNTRY_TZ in tools.py.")
    return _fmt_time(datetime.now(ZoneInfo(tz)), place.title(), tz)


# ---------------------------------------------------------------------- calc --
_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Pow: op.pow, ast.Mod: op.mod, ast.USub: op.neg, ast.UAdd: op.pos}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        a, b = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(b) > 100:
            raise ValueError("exponent too large")
        return _OPS[type(node.op)](a, b)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported")


def calculate(q):
    s = q.lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return f"{a:g}% of {b:g} = **{a * b / 100:g}**"
    m = re.search(r"(?:square root of|sqrt)\s*\(?\s*(\d+(?:\.\d+)?)", s)
    if m:
        return f"The square root of {m.group(1)} = **{float(m.group(1)) ** 0.5:.6g}**"
    expr = re.findall(r"[\d.\s\+\-\*/\(\)\^%x×÷]{3,}", s)
    expr = max(expr, key=len).strip() if expr else ""
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")
    expr = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "*", expr)
    try:
        val = _eval(ast.parse(expr, mode="eval"))
        return f"{expr.replace('**', '^')} = **{val:,.10g}**"
    except Exception:
        return "I couldn't read that sum. Try something like `12 * (3 + 4)` or `15% of 240`."


# ------------------------------------------------------------------- weather --
_WMO = {0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "freezing fog",
        51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
        71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers", 81: "rain showers",
        82: "violent rain showers", 95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail"}


def weather(q):
    place = _place(q)
    if not place:
        return "Which place? Try 'weather in Hyderabad'."
    try:
        g = requests.get("https://geocoding-api.open-meteo.com/v1/search", headers=HEADERS, timeout=8,
                         params={"name": place, "count": 1}).json()
        if not g.get("results"):
            return f"I couldn't find a place called '{place}'."
        r = g["results"][0]
        w = requests.get("https://api.open-meteo.com/v1/forecast", headers=HEADERS, timeout=8, params={
            "latitude": r["latitude"], "longitude": r["longitude"], "timezone": "auto",
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        }).json()["current"]
        name = ", ".join(x for x in (r["name"], r.get("admin1"), r.get("country")) if x)
        return (f"Right now in **{name}**: {_WMO.get(w['weather_code'], 'unsettled weather')}.\n\n"
                f"- Temperature: {w['temperature_2m']}°C (feels like {w['apparent_temperature']}°C)\n"
                f"- Humidity: {w['relative_humidity_2m']}%\n"
                f"- Wind: {w['wind_speed_10m']} km/h")
    except Exception as e:
        return f"My weather vane couldn't reach the weather service ({type(e).__name__}). Check your internet."


def run(tool, question):
    """Returns (answer_text, source_label)."""
    if tool == "time":
        return current_time(question), "your Mac's clock"
    if tool == "calc":
        return calculate(question), "calculator"
    if tool == "weather":
        return weather(question), "Open-Meteo (free)"
    return "Unknown tool.", "none"
