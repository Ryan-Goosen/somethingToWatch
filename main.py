from sport_functions.f1_ai import show_all_meetings

import curses

def curses_menu(stdscr, options, title="Menu", tooltip_on_disabled=True):
    """
    Generic curses menu.

    Args:
        stdscr: curses screen object.
        options: list of options. Each element can be:
                 - a tuple (label, enabled)   e.g. ("Formula 1", True)
                 - a tuple (label, enabled, user_data) – returns user_data
                 - a string (interpreted as enabled)
        title: string displayed at the top.
        tooltip_on_disabled: if True, pressing Enter on a disabled option shows a tooltip.

    Returns:
        - The index (int) of the selected option (if enabled and selected with Enter).
        - The user_data from the tuple (if provided) – but you can extend.
        - None if user pressed 'q' or ESC.
    """
    curses.curs_set(0)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK,  curses.COLOR_CYAN)   # selected row
        curses.init_pair(2, curses.COLOR_CYAN,   -1)                  # header
        curses.init_pair(3, curses.COLOR_WHITE,  -1)                  # normal enabled
        curses.init_pair(4, curses.COLOR_RED,    -1)                  # disabled
        curses.init_pair(5, curses.COLOR_YELLOW, -1)                  # footer/tooltip

    # Normalise options: (label, enabled, user_data, action_func)
    norm_opts = []
    for opt in options:
        if isinstance(opt, str):
            norm_opts.append((opt, True, None, None))
        elif isinstance(opt, tuple) and len(opt) >= 2:
            label, enabled = opt[0], opt[1]
            user_data = opt[2] if len(opt) > 2 else None
            action_func = opt[3] if len(opt) > 3 else None
            norm_opts.append((label, enabled, user_data, action_func))
        else:
            raise ValueError("Option must be string or tuple")

    selected = 0
    scroll_offset = 0

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        visible = max_y - 4   # header + footer space
        if visible < 1:
            visible = 1

        # Scroll logic
        if selected < scroll_offset:
            scroll_offset = selected
        if selected >= scroll_offset + visible:
            scroll_offset = selected - visible + 1
        scroll_offset = max(0, min(scroll_offset, len(norm_opts) - visible))

        # Title
        if title:
            stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title,
                          curses.color_pair(2) | curses.A_BOLD)

        # Header line (simple)
        header = "Available options:"
        stdscr.addstr(1, 2, header[:max_x-3], curses.color_pair(2) | curses.A_UNDERLINE)

        # List options
        for idx, (label, enabled, _, _) in enumerate(norm_opts[scroll_offset:scroll_offset + visible]):
            screen_y = idx + 2
            absolute = idx + scroll_offset
            # Build display line with arrow for selected
            prefix = "➤ " if absolute == selected else "  "
            if enabled:
                line = f"{prefix}{label}"
                attr = curses.color_pair(1) | curses.A_BOLD if absolute == selected else curses.color_pair(3)
            else:
                line = f"{prefix}{label} (disabled)"
                attr = curses.color_pair(4) | curses.A_DIM
                if absolute == selected:
                    attr = curses.A_REVERSE | curses.color_pair(4)
            if len(line) > max_x - 3:
                line = line[:max_x-3]
            stdscr.addstr(screen_y, 2, line, attr)

        # Footer
        footer = " ↑/↓ navigate   Enter select   q quit "
        stdscr.addstr(max_y - 1, max(0, (max_x - len(footer)) // 2), footer,
                      curses.color_pair(5))

        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_UP and selected > 0:
            selected -= 1
        elif key == curses.KEY_DOWN and selected < len(norm_opts) - 1:
            selected += 1
        elif key in (curses.KEY_ENTER, 10, 13):
            label, enabled, user_data, action_func = norm_opts[selected]
            if enabled:
                # Return the index (or user_data if you prefer)
                if callable(action_func):
                    try:
                        action_func(stdscr)
                    except TypeError:
                        action_func()
                        
                return selected if user_data is None else user_data
            elif tooltip_on_disabled:
                # Show tooltip
                msg = f"⚠ {label} is not available. ⚠"
                tooltip_y = max_y - 2
                stdscr.addstr(tooltip_y, max(0, (max_x - len(msg)) // 2), msg,
                              curses.color_pair(5) | curses.A_BOLD)
                stdscr.refresh()
                curses.napms(1500)
                # continue loop, redraw on next iteration
                continue
        elif key in (ord('q'), ord('Q'), 27):
            return None
        elif key == curses.KEY_RESIZE:
            continue


def main(stdscr):
    sports = [
        ("Formula 1",      True,  "F1", show_all_meetings),
        ("Football",       False, "⚽"),
        ("UFC",            False, "🥊"),
        ("Field Hockey",   False, "🏑"),
    ]
    while True:

        selected_sport = curses_menu(stdscr, sports, "Sport Selector")

        if selected_sport is None:
            return
        if selected_sport == "Formula 1":
            # Run your F1 calendar code (which also uses curses)
            # Make sure to call curses.endwin() before your other curses code? No,
            # because you're already inside a curses wrapper. You can directly call
            # your F1 selection function (like _render_meetings_curses) which expects
            # the same stdscr. They can share the same curses session.
            meeting = show_all_meetings()   # but you need meetings list
            # ...
            stdscr.clear()
            stdscr.refresh()
            curses.curs_set(0)
            if curses.has_colors():
                curses.init_pair(1, curses.COLOR_BLACK,  curses.COLOR_CYAN)
                curses.init_pair(2, curses.COLOR_CYAN,   -1)
                curses.init_pair(3, curses.COLOR_WHITE,  -1)
                curses.init_pair(4, curses.COLOR_RED,    -1)
                curses.init_pair(5, curses.COLOR_YELLOW, -1)

        else:
            # Should not happen because disabled sports won't return, but fallback
            pass

if __name__ == "__main__":
    curses.wrapper(main)
