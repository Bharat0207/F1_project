import unicodedata
from pathlib import Path

BASE = Path("assets")

# Allow fallback if folder is at root 'drivers/' instead of 'assets/drivers/'
DRIVERS = BASE / "drivers" if (BASE / "drivers").exists() else Path("drivers")
CARS = BASE / "cars" if (BASE / "cars").exists() else Path("cars")
CIRCUITS = BASE / "circuits" if (BASE / "circuits").exists() else Path("circuits")
TEAMS = BASE / "teams" if (BASE / "teams").exists() else Path("teams")

TEAM_COLORS = {
    "Mercedes": "#00D2BE",
    "Ferrari": "#DC0000",
    "McLaren": "#FF8700",
    "Red Bull": "#0600EF",
    "Red Bull Racing": "#0600EF",
    "RB F1 Team": "#2B4562",
    "Racing Bulls": "#2B4562",
    "Williams": "#005AFF",
    "Aston Martin": "#006F62",
    "Alpine": "#0090FF",
    "Alpine F1 Team": "#0090FF",
    "Kick Sauber": "#52E252",
    "Sauber": "#52E252",
    "Haas": "#FFFFFF",
    "Haas F1 Team": "#FFFFFF",
}


def _strip_accents(text):
    """Converts 'Pérez' -> 'perez' and 'Hülkenberg' -> 'hulkenberg'."""
    if not text:
        return ""
    nfkd_form = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()


def short_driver_name(name):
    parts = name.split()
    if len(parts) <= 2:
        return name
    return " ".join(parts[-2:])


def get_team_color(team):
    return TEAM_COLORS.get(team, "#666666")


def get_driver_image(driver_name):
    if not driver_name or not DRIVERS.exists():
        return None

    # Strip accents from API input name (e.g. 'Pérez' -> 'perez')
    last_name = _strip_accents(driver_name.split()[-1])

    for img in DRIVERS.glob("*"):
        stem = _strip_accents(img.stem)

        if stem == last_name or stem.replace("ll", "l") == last_name.replace("ll", "l"):
            return str(img)

    return None


def get_circuit_image(country):
    if not country or not CIRCUITS.exists():
        return None

    country = _strip_accents(country.replace(" ", "_"))

    for img in CIRCUITS.glob("*"):
        if country in _strip_accents(img.stem):
            return str(img)

    return None


def _clean_team_str(text):
    return (
        _strip_accents(text)
        .replace(" ", "")
        .replace("-", "")
        .replace("f1team", "")
        .replace("racing", "")
    )


def get_team_car(team):
    if not team or not CARS.exists():
        return None

    cleaned_team = _clean_team_str(team)

    for img in CARS.glob("*"):
        if cleaned_team in _clean_team_str(img.stem):
            return str(img)

    return None


def get_team_logo(team):
    if not team or not TEAMS.exists():
        return None

    cleaned_team = _clean_team_str(team)

    for img in TEAMS.glob("*"):
        if cleaned_team in _clean_team_str(img.stem):
            return str(img)

    return None