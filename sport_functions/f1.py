from datetime import date, datetime

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.padding import Padding
from rich_pixels import Pixels
from PIL import Image
from io import BytesIO


import requests
import sys
import pycountry


CURRENT_YEAR = date.today().year
RACE_DATES_API = f"https://api.openf1.org/v1/meetings?year={CURRENT_YEAR}"
RACE_DATA_API = "https://api.openf1.org/v1/sessions?"


def _get_race_dates():
    try:
        data = requests.get(RACE_DATES_API)
        if data.status_code != 200:
            data.raise_for_status()
        return [item for item in data.json() if item.get("year") == CURRENT_YEAR]
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        print("FAITAL ERROR. Exiting program.")
        sys.exit(1)
    
def _get_current_weeks_race():
    meetings = _get_race_dates()
    current_week = date.today().isocalendar()[1]
    races = []

    for meeting in meetings:

        date_string = meeting.get("date_start")
        date_week = datetime.fromisoformat(date_string).isocalendar()[1]
        
        if current_week == date_week:
            country_name = meeting.get("country_name")
            meeting_key = meeting.get("meeting_key")
            race_data = requests.get(RACE_DATA_API + f"country_name={country_name}&year={CURRENT_YEAR}&meeting_key={meeting_key}")
            return race_data

    return None

def _country_to_flag_emoji(country_name: str) -> str:
    try:
        country = pycountry.countries.search_fuzzy(country_name)[0]
        return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in country.alpha_2)
    except LookupError:
        return "🏳️"  # fallback for unknown

def _vcenter_pixels(pixels, cell_height: int, pixel_height: int) -> Group:
    """Vertically center a Pixels object using blank Text lines."""
    pad = (cell_height - pixel_height) // 2
    blank = Text("")
    return Group(
        *([blank] * pad),
        Align.center(pixels),
        *([blank] * pad),
    )

def _vcenter(renderable, cell_height: int, content_lines: int):
    pad = (cell_height - content_lines) // 2
    return Padding(renderable, pad=(pad, 0))

def display_data(dates, location, country_name, track_image_url):

    TRACK_W, TRACK_H = 24,24
    console = Console()
    table = Table(title="Race Schedule", style="bright_white", title_justify="center")
    table.add_column("Date",     style="cyan",    no_wrap=True, justify="center")
    table.add_column("Location", style="magenta",               justify="center")
    table.add_column("Track",    style="green",                 justify="center", max_width=TRACK_W + 10)

    # ── Track: a bit larger but still compact ─────────────────────────────
    try:
        track_img_data = requests.get(track_image_url).content
        track_pil = Image.open(BytesIO(track_img_data)).convert("RGBA")
        track_pil = track_pil.resize((TRACK_W, TRACK_H), Image.LANCZOS)
        track_render = _center_pixels(Pixels.from_image(track_pil))
    except Exception as e:
        print(e)
        track_render = Text("🖼️", justify="center")

    for date_str in dates:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        formatted_date = dt.strftime("%d %b")

        flag_emoji = _country_to_flag_emoji(country_name)

        # Location = 2 lines (location text + flag emoji)
        location_renderable = _vcenter(
            Align.center(Group(
                Text(location, justify="center"),
                Text(flag_emoji, justify="center"),
            )),
            cell_height=TRACK_H,
            content_lines=2,
        )

        # Date = 1 line
        date_renderable = _vcenter(
            Text(formatted_date, justify="center"),
            cell_height=TRACK_H,
            content_lines=1,
        )

        track_render = _vcenter_pixels(
            Pixels.from_image(track_pil),
            cell_height=TRACK_H,
            pixel_height=TRACK_H,
        )

        table.add_row(date_renderable, location_renderable, track_render)

    table = Align.center(table, vertical="middle")
    console.print(table)



if __name__ == "__main__":
    # Example data from your JSON
    dates = [
        "2026-06-12T11:30:00+00:00",
        "2026-06-12T15:00:00+00:00",
        "2026-06-13T10:30:00+00:00",
    ]
    location = "Barcelona, Spain"
    flag_url = "https://media.formula1.com/content/dam/fom-website/2018-redesign-assets/Flags%2016x9/spain-flag.png"
    track_image_url = "https://media.formula1.com/content/dam/fom-website/2018-redesign-assets/Track%20icons%204x3/Singapore%20carbon.png"

    display_data(dates, location, "Spain", track_image_url)