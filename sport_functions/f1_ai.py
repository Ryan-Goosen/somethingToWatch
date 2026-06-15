from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from io import BytesIO
import curses
import sys
import requests
import pycountry

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.padding import Padding
from rich_pixels import Pixels
from PIL import Image


# ─── Constants ────────────────────────────────────────────────────────────────

CURRENT_YEAR = date.today().year
MEETINGS_API = f"https://api.openf1.org/v1/meetings?year={CURRENT_YEAR}"
SESSIONS_API  = "https://api.openf1.org/v1/sessions"
RESULTS_API   = "https://api.openf1.org/v1/session_result"
DRIVERS_API   = "https://api.openf1.org/v1/drivers"

# Circuit type key returned by openF1 → human label
CIRCUIT_TYPE_LABELS = {
    "street":      "🏙️  Street",
    "race":        "🏁 Permanent",
    "temporary":   "⛺ Temporary",
}

LOCAL_TZ = datetime.now().astimezone().tzinfo  # system local timezone


# ─── Data fetching ────────────────────────────────────────────────────────────

def _get_meetings() -> list[dict]:
    """All race meetings for the current season."""
    try:
        resp = requests.get(MEETINGS_API, timeout=10)
        resp.raise_for_status()
        return [m for m in resp.json() if m.get("year") == CURRENT_YEAR]
    except requests.exceptions.RequestException as e:
        print(f"[F1] API request failed: {e}")
        sys.exit(1)


def _get_sessions_for_meeting(meeting_key: int, country_name: str) -> list[dict]:
    """All sessions (practice / quali / race) for a given meeting."""
    try:
        resp = requests.get(
            SESSIONS_API,
            params={
                "meeting_key":  meeting_key,
                "country_name": country_name,
                "year":         CURRENT_YEAR,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[F1] Session fetch failed: {e}")
        return []


def _get_current_week_sessions() -> tuple[list[dict], dict | None]:
    """
    Returns (sessions, meeting) for any meeting that falls in the current ISO week.
    sessions is [] and meeting is None if nothing is on this week.
    """
    current_week = date.today().isocalendar()[1]
    for meeting in _get_meetings():
        date_str = meeting.get("date_start", "")
        try:
            meeting_week = datetime.fromisoformat(date_str).isocalendar()[1]
        except ValueError:
            continue
        if meeting_week == current_week:
            sessions = _get_sessions_for_meeting(
                meeting["meeting_key"], meeting["country_name"]
            )
            return sessions, meeting
    return [], None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _country_to_flag(country_name: str) -> str:
    try:
        country = pycountry.countries.search_fuzzy(country_name)[0]
        return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in country.alpha_2)
    except LookupError:
        return "🏳️"


def _localise(iso_str: str) -> datetime:
    """Parse an ISO datetime string and convert to local system time."""
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ)


def _fetch_track_image(url: str, width: int, height: int):
    """
    Fetch a track image URL and return a rich-pixels Pixels object resized to
    (width, height). Returns a fallback Text on failure.
    """
    try:
        data = requests.get(url, timeout=8).content
        img = Image.open(BytesIO(data)).convert("RGBA")
        img = img.resize((width, height), Image.LANCZOS)
        return Pixels.from_image(img)
    except Exception:
        return Text("🖼️ [no image]", justify="center")


def _vcenter_pixels(pixels, cell_height: int, pixel_height: int) -> Group:
    pad = max((cell_height - pixel_height) // 2, 0)
    blank = Text("")
    return Group(*([blank] * pad), Align.center(pixels), *([blank] * pad))


def _vcenter(renderable, cell_height: int, content_lines: int):
    pad = max((cell_height - content_lines) // 2, 0)
    return Padding(renderable, pad=(pad, 0))


def _curses_centre_str(stdscr, y: int, text: str, attr: int = 0) -> None:
    """Write text centred on row y, safely clipped to terminal width."""
    _, max_x = stdscr.getmaxyx()
    x = max(0, (max_x - len(text)) // 2)
    stdscr.addstr(y, x, text[:max_x - 1], attr)


def _curses_hline(stdscr, y: int, attr: int = 0) -> None:
    """Draw a full-width horizontal line of dashes on row y."""
    _, max_x = stdscr.getmaxyx()
    stdscr.addstr(y, 0, "─" * (max_x - 1), attr)


def _curses_loading(stdscr, message: str = "Fetching data…") -> None:
    """Clear screen and show a centred loading message."""
    stdscr.clear()
    max_y, _ = stdscr.getmaxyx()
    _curses_centre_str(stdscr, max_y // 2, message, curses.color_pair(4) | curses.A_BOLD)
    stdscr.refresh()


# ─── Option 1 — All meetings (curses overlay + rich detail) ───────────────────


def _curses_error(stdscr, message: str, detail: str = "") -> None:
    """
    Show a full-screen error in curses with a red title.
    Blocks until the user presses any key, then returns so the caller
    can decide what to do (usually: return back up the call stack).
    """
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    mid = max_y // 2
    _curses_centre_str(stdscr, mid - 1, "⚠  Error", curses.color_pair(5) | curses.A_BOLD)
    _curses_centre_str(stdscr, mid,     message[:max_x - 1], curses.color_pair(3))
    if detail:
        _curses_centre_str(stdscr, mid + 1, detail[:max_x - 1], curses.color_pair(4))
    _curses_centre_str(stdscr, max_y - 1, " Press any key to go back ",
                       curses.color_pair(4))
    stdscr.refresh()
    stdscr.getch()


def _get_session_results(session_key: int) -> list[dict]:
    """Fetch finishing order for a completed session. Raises on network failure."""
    resp = requests.get(RESULTS_API, params={"session_key": session_key}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return []  # valid empty — session exists but no results yet
    return sorted(data, key=lambda r: r.get("position") or 999)


def _get_driver(driver_number: int, session_key: int) -> dict:
    """Fetch driver info for a given driver number and session."""
    try:
        resp = requests.get(
            DRIVERS_API,
            params={"driver_number": driver_number, "session_key": session_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else {}
    except requests.exceptions.RequestException:
        return {}


# Column widths for results table
_COL_POS  = 6
_COL_DRV  = 24
_COL_TEAM = 26
_COL_TIME = 16

# Medal attributes: (prefix, curses colour pair id)  — pairs initialised in _init_colours()
_MEDAL = {1: ("🥇", 6), 2: ("🥈", 7), 3: ("🥉", 8)}


def _init_colours() -> None:
    """Initialise all colour pairs used across the TUI. Safe to call once."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK,  curses.COLOR_CYAN)    # selected row
    curses.init_pair(2, curses.COLOR_CYAN,   -1)                   # header / title
    curses.init_pair(3, curses.COLOR_WHITE,  -1)                   # normal row
    curses.init_pair(4, curses.COLOR_YELLOW, -1)                   # footer / loading
    curses.init_pair(5, curses.COLOR_RED,    -1)                   # live dot
    curses.init_pair(6, curses.COLOR_YELLOW, -1)                   # gold  (P1)
    curses.init_pair(7, curses.COLOR_WHITE,  -1)                   # silver (P2)
    curses.init_pair(8, curses.COLOR_RED,    -1)                   # bronze (P3) — closest curses has
    curses.init_pair(9, curses.COLOR_MAGENTA,-1)                   # session name

    curses.init_pair(10,curses.COLOR_GREEN,  -1)                   # past session (selectable)


def _fmt_time(duration: float, leader: float | None, pos: int) -> str:
    """Format a duration into broadcast-style time or gap string."""
    if pos == 1:
        mins, secs = divmod(duration, 60)
        hrs, mins  = divmod(int(mins), 60)
        return f"{hrs}:{mins:02d}:{secs:06.3f}" if hrs else f"{int(mins)}:{secs:06.3f}"
    gap = duration - (leader or duration)
    return f"+{gap:.3f}s"


def _display_session_results(stdscr, session: dict) -> None:
    """
    Pure-curses results screen — broadcast layout:
    Pos | Driver | Team | Time / Gap
    Scrollable. Press q / Esc / Backspace to return.
    """
    session_key  = session.get("session_key")
    session_name = session.get("session_name", "Session")

    _curses_loading(stdscr, f"Loading results for {session_name}…")

    try:
        results = _get_session_results(session_key)
    except Exception as e:
        # Catch everything — RequestException, JSONDecodeError, ValueError, etc.
        # Show the actual exception type + message so we know exactly what broke.
        _curses_error(
            stdscr,
            f"Could not load results for {session_name}",
            detail=f"{type(e).__name__}: {e}"[:120],
        )
        return

    # Build driver cache + display rows — wrapped so any data error surfaces visibly
    driver_cache: dict[int, dict] = {}
    def cached_driver(num: int) -> dict:
        if num not in driver_cache:
            driver_cache[num] = _get_driver(num, session_key)
        return driver_cache[num]

    display_rows: list[tuple] = []
    leader_duration: float | None = None

    try:
        for result in results:
            pos      = result.get("position") or 0
            drv_num  = result.get("driver_number")
            duration = result.get("duration_seconds")
            status   = result.get("status", "")

            driver   = cached_driver(drv_num) if drv_num else {}
            name     = (driver.get("full_name") or driver.get("broadcast_name") or f"#{drv_num}")[:_COL_DRV - 1]
            team     = (driver.get("team_name") or "—")[:_COL_TEAM - 1]

            if duration is not None:
                if pos == 1:
                    leader_duration = duration
                time_str = _fmt_time(duration, leader_duration, pos)
            elif status:
                time_str = status
            else:
                time_str = "—"

            medal_pair = _MEDAL.get(pos, (None, 3))  # default = normal white
            display_rows.append((pos, medal_pair, name, team, time_str))
    except Exception as e:
        _curses_error(
            stdscr,
            "Failed to build results table",
            detail=f"{type(e).__name__}: {e}"[:120],
        )
        return

    # ── Render loop ───────────────────────────────────────────────────────────
    scroll = 0
    HEADER = (
        f"{'Pos':<{_COL_POS}}"
        f"{'Driver':<{_COL_DRV}}"
        f"{'Team':<{_COL_TEAM}}"
        f"{'Time / Gap':>{_COL_TIME}}"
    )

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        visible = max_y - 4

        # Title
        _curses_centre_str(stdscr, 0,
                           f"  {session_name} — Results  ",
                           curses.color_pair(2) | curses.A_BOLD)
        # Header
        stdscr.addstr(1, 0, HEADER[:max_x - 1], curses.color_pair(2) | curses.A_UNDERLINE)

        if not display_rows:
            _curses_centre_str(stdscr, max_y // 2,
                               "No results available yet.",
                               curses.color_pair(4))
        else:
            for idx, (pos, (prefix, pair), name, team, time_str) in                     enumerate(display_rows[scroll:scroll + visible]):
                y    = idx + 2
                attr = curses.color_pair(pair) | curses.A_BOLD if pos <= 3 else curses.color_pair(3)
                pos_label = f"{prefix or ''} {pos}"[:_COL_POS] if prefix else f"{pos:<{_COL_POS}}"
                row = (
                    f"{pos_label:<{_COL_POS}}"
                    f"{name:<{_COL_DRV}}"
                    f"{team:<{_COL_TEAM}}"
                    f"{time_str:>{_COL_TIME}}"
                )
                stdscr.addstr(y, 0, row[:max_x - 1], attr)

        # Footer
        footer = " ↑↓ scroll   q / ← back "
        stdscr.addstr(max_y - 1, 0, footer[:max_x - 1], curses.color_pair(4))
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        elif key in (curses.KEY_UP, ord("k")) and scroll > 0:
            scroll -= 1
        elif key in (curses.KEY_DOWN, ord("j")) and scroll < len(display_rows) - visible:
            scroll += 1
        elif key in (ord("q"), ord("Q"), 27, curses.KEY_BACKSPACE, 8):
            return  # back to meeting detail


def _render_meetings_curses(stdscr, meetings: list[dict]) -> dict | None:
    """
    Curses overlay: arrow keys to scroll, Enter to select, q to quit.
    Returns the selected meeting dict, or None if the user quit.
    """
    curses.curs_set(0)
    _init_colours()   # centralised — safe to call multiple times


    selected = 0
    scroll_offset = 0

    # Column widths (chars)
    COL_DATE     = 12
    COL_TIME     = 10
    COL_LOCATION = 22
    COL_COUNTRY  = 18
    COL_NAME     = 30
    COL_TYPE     = 14

    HEADER = (
        f"{'Date':<{COL_DATE}}"
        f"{'Time (local)':<{COL_TIME+2}}"
        f"{'Location':<{COL_LOCATION}}"
        f"{'Country':<{COL_COUNTRY}}"
        f"{'Race Name':<{COL_NAME}}"
        f"{'Circuit':<{COL_TYPE}}"
    )

    current_week = date.today().isocalendar()[1]

    def build_row(m: dict) -> tuple[str, bool]:
        """Returns (row_string, is_current_week)."""
        dt        = _localise(m.get("date_start", ""))
        date_s    = dt.strftime("%d %b %Y")
        time_s    = dt.strftime("%H:%M")
        loc       = (m.get("location") or "")[:COL_LOCATION - 1]
        country   = (m.get("country_name") or "")[:COL_COUNTRY - 1]
        name      = (m.get("meeting_name") or "")[:COL_NAME - 1]
        ctype     = CIRCUIT_TYPE_LABELS.get(
                        (m.get("circuit_short_name") or "").lower(), "🏁 Circuit"
                    )[:COL_TYPE - 1]
        date_week = datetime.fromisoformat(m.get("date_start", "")).isocalendar()[1]
        is_live   = date_week == current_week
        return (
            f"{date_s:<{COL_DATE}}"
            f"{time_s:<{COL_TIME+2}}"
            f"{loc:<{COL_LOCATION}}"
            f"{country:<{COL_COUNTRY}}"
            f"{name:<{COL_NAME}}"
            f"{ctype:<{COL_TYPE}}",
            is_live,
        )

    rows = [build_row(m) for m in meetings]

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        visible = max_y - 4  # header + footer take 4 lines

        # Ensure selected stays visible
        if selected < scroll_offset:
            scroll_offset = selected
        if selected >= scroll_offset + visible:
            scroll_offset = selected - visible + 1

        # ── Title ─────────────────────────────────────────────────────────────
        title = " 🏎  F1 Race Calendar "
        stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title,
                      curses.color_pair(2) | curses.A_BOLD)

        # ── Header ────────────────────────────────────────────────────────────
        stdscr.addstr(1, 0, HEADER[:max_x - 1], curses.color_pair(2) | curses.A_UNDERLINE)

        # ── Rows ──────────────────────────────────────────────────────────────
        for idx, (row, is_live) in enumerate(rows[scroll_offset: scroll_offset + visible]):
            screen_y = idx + 2
            absolute  = idx + scroll_offset
            is_selected = absolute == selected
            row_attr  = curses.color_pair(1) | curses.A_BOLD if is_selected \
                        else curses.color_pair(3)
            dot       = "● " if is_live else "  "
            dot_attr  = (curses.color_pair(1) | curses.A_BOLD) if is_selected \
                        else (curses.color_pair(5) | curses.A_BOLD)
            stdscr.addstr(screen_y, 0, dot, dot_attr)
            stdscr.addstr(screen_y, 2, row[:max_x - 3], row_attr)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = " ↑↓ navigate   Enter select   q quit "
        stdscr.addstr(max_y - 1, 0, footer[:max_x - 1], curses.color_pair(4))

        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        elif key in (curses.KEY_UP, ord("k")) and selected > 0:
            selected -= 1
        elif key in (curses.KEY_DOWN, ord("j")) and selected < len(meetings) - 1:
            selected += 1
        elif key in (curses.KEY_ENTER, 10, 13):
            _display_meeting_detail(stdscr, meetings[selected])  # stdscr flows through
            # Flush any keys that queued up while in the detail screen
            curses.flushinp()
        elif key in (ord("q"), ord("Q"), 27):  # q or ESC
            return None


def _display_meeting_detail(stdscr, meeting: dict) -> None:
    """
    Pure-curses session list for a selected meeting.
    Rows: Date | Time | Session name.
    Past sessions highlighted — press Enter on one to see results.
    q / Esc / Backspace to return to meeting list.
    """
    _curses_loading(stdscr, f"Loading sessions for {meeting.get('meeting_name', '')}…")

    sessions = _get_sessions_for_meeting(meeting["meeting_key"], meeting["country_name"])
    sessions.sort(key=lambda s: s.get("date_start", ""))

    now    = datetime.now(timezone.utc)
    flag   = _country_to_flag(meeting.get("country_name", ""))
    title  = f"{flag}  {meeting.get('meeting_name', 'Meeting')} — {meeting.get('location', '')}  {flag}"

    COL_DATE = 14
    COL_TIME = 10
    COL_NAME = 30

    HEADER = (
        f"{'Date':<{COL_DATE}}"
        f"{'Time':<{COL_TIME}}"
        f"{'Session':<{COL_NAME}}"
        f"  {'':>12}"
    )

    def is_past(s: dict) -> bool:
        end_str = s.get("date_end", "")
        if not end_str:
            return False
        return _localise(end_str).astimezone(timezone.utc) < now

    def build_row(s: dict) -> str:
        dt       = _localise(s.get("date_start", ""))
        date_s   = dt.strftime("%d %b %Y")
        time_s   = dt.strftime("%H:%M")
        name     = (s.get("session_name") or "")[:COL_NAME - 1]
        suffix   = "  ← results" if is_past(s) else ""
        return (
            f"{date_s:<{COL_DATE}}"
            f"{time_s:<{COL_TIME}}"
            f"{name:<{COL_NAME}}"
            f"{suffix}"
        )

    rows = [build_row(s) for s in sessions]

    selected = 0
    scroll   = 0

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        visible = max_y - 4

        # Scroll tracking
        if selected < scroll:
            scroll = selected
        if selected >= scroll + visible:
            scroll = selected - visible + 1

        # Title + header
        _curses_centre_str(stdscr, 0, title, curses.color_pair(2) | curses.A_BOLD)
        stdscr.addstr(1, 0, HEADER[:max_x - 1], curses.color_pair(2) | curses.A_UNDERLINE)

        for idx, (row, session) in enumerate(
            zip(rows[scroll:scroll + visible], sessions[scroll:scroll + visible])
        ):
            y           = idx + 2
            absolute    = idx + scroll
            is_selected = absolute == selected
            past        = is_past(session)

            if is_selected:
                attr = curses.color_pair(1) | curses.A_BOLD
            elif past:
                attr = curses.color_pair(10)   # green — selectable for results
            else:
                attr = curses.color_pair(3)

            stdscr.addstr(y, 0, row[:max_x - 1], attr)

        # Footer — hint changes based on whether selected session has results
        sel_session = sessions[selected] if sessions else None
        if sel_session and is_past(sel_session):
            footer = " ↑↓ navigate   Enter view results   q / ← back "
        else:
            footer = " ↑↓ navigate   Enter (results when available)   q / ← back "
        stdscr.addstr(max_y - 1, 0, footer[:max_x - 1], curses.color_pair(4))

        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        elif key in (curses.KEY_UP, ord("k")) and selected > 0:
            selected -= 1
        elif key in (curses.KEY_DOWN, ord("j")) and selected < len(sessions) - 1:
            selected += 1
        elif key in (curses.KEY_ENTER, 10, 13):
            if sel_session and is_past(sel_session):
                _display_session_results(stdscr, sel_session)  # pass stdscr straight through
                curses.flushinp()  # discard keys queued during results screen
        elif key in (ord("q"), ord("Q"), 27, curses.KEY_BACKSPACE, 8):
            return  # back to meeting list


def show_all_meetings(stdscr=None) -> None:
    """
    Entry point for Option 1.
    Pass stdscr if calling from an existing curses session (main TUI).
    Omit stdscr to run standalone — will create its own curses context.
    """
    meetings = _get_meetings()
    if not meetings:
        print("[F1] No meetings found for the current season.")
        return

    meetings.sort(key=lambda m: m.get("date_start", ""))

    if stdscr is not None:
        # Caller owns the curses session — use their screen directly
        _render_meetings_curses(stdscr, meetings)
    else:
        # Standalone — spin up our own curses context
        curses.wrapper(_render_meetings_curses, meetings)


# ─── Option 2 — Current week's races (rich table) ─────────────────────────────

def show_current_week() -> None:
    """
    Entry point for Option 2.
    Displays all sessions happening this ISO week as a rich table with track image
    sitting to the right via Columns — rendered once only.
    """
    console          = Console()
    sessions, meeting = _get_current_week_sessions()

    if not sessions or meeting is None:
        console.print("[yellow]No F1 races scheduled for this week.[/]")
        return

    country_name = meeting.get("country_name", "")
    flag         = _country_to_flag(country_name)
    meeting_name = meeting.get("meeting_name", "Race Weekend")

    table = Table(
        title=f"{flag}  This Week — {meeting_name}  {flag}",
        style="bright_white",
        title_justify="center",
        show_lines=True,
    )
    # Fixed widths so the body always extends ~10 chars past the title
    table.add_column("Date",         style="cyan",    no_wrap=True, justify="center", min_width=12)
    table.add_column("Time (local)", style="yellow",  no_wrap=True, justify="center", min_width=14)
    table.add_column("Event",        style="magenta",               justify="center", min_width=24)

    sessions.sort(key=lambda s: s.get("date_start", ""))
    for session in sessions:
        dt = _localise(session.get("date_start", ""))
        table.add_row(
            dt.strftime("%d %b"),
            dt.strftime("%H:%M"),
            session.get("session_name", "Unknown"),
        )

    console.print(Align.center(table))


# ─── Dev entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "week"

    if cmd == "all":
        show_all_meetings()
    elif cmd == "week":
        show_current_week()
    else:
        print("Usage: python f1.py [all | week]")