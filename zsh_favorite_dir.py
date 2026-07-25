#!/usr/bin/env python3

# Required Python3.3+

import os
import select
import sys
import termios
import tty

Q_DIR = os.path.join(os.path.expanduser("~"), "Q")


class DirEntry:
    def __init__(self, real_path, name, description):
        self.real_path = real_path
        self.name = name
        self.description = description

    def __repr__(self):
        return "DirEntry(real_path={!r}, name={!r}, description={!r})".format(
            self.real_path, self.name, self.description
        )


def get_directories(base_dir):
    """
    :rtype: List[DirEntry]
    """

    if not os.path.isdir(base_dir):
        return []

    # Read description file if present
    descriptions = {}
    list_file = os.path.join(base_dir, ".list")
    if os.path.isfile(list_file):
        try:
            with open(list_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and ":" in line and not line.startswith("#"):
                        name, desc = line.split(":", 1)
                        descriptions[name.strip()] = desc.strip()
        except OSError:
            pass

    try:
        entries = os.listdir(base_dir)
        dirs = []
        for d in entries:
            d_path = os.path.join(base_dir, d)
            if not os.path.isdir(d_path) or d.startswith("."):
                continue

            san_name = ascii(d)[1:-1]
            san_descr = ascii(descriptions.get(san_name, "No description"))[1:-1]
            dirs.append(
                DirEntry(
                    real_path=os.path.realpath(d_path),
                    name=san_name,
                    description=san_descr,
                )
            )
        return sorted(dirs, key=lambda x: x.name.lower())
    except PermissionError:
        return []


def read_key(tty_in):
    """Reads a single keypress or variable-length escape sequence directly from /dev/tty."""
    fd = tty_in.fileno()
    old_settings = termios.tcgetattr(fd)

    def _read_sequence(buffer=""):
        # Read the next available byte
        ch = tty_in.read(1).decode("utf-8", errors="ignore")
        buffer += ch

        # Non-blocking check (20ms window) to see if more bytes belong to this escape sequence
        r, _, _ = select.select([tty_in], [], [], 0.02)
        if r:
            return _read_sequence(buffer)

        # Normalize Zsh / Application Cursor mode keys (\x1bOA -> \x1b[A)
        if buffer.startswith("\x1bO") and len(buffer) == 3:
            return "\x1b[" + buffer[2]

        return buffer

    try:
        tty.setraw(fd)
        return _read_sequence()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class UI:
    def __init__(self, tty_in, tty_out, dirs):
        """
        :param tty_in: Input terminal interface
        :param tty_out: Output terminal interface
        :type dirs: List[DirEntry]
        """
        self.tty_in = tty_in
        self.tty_out = tty_out
        self.dirs = dirs
        self._dirs_len = len(dirs)
        self.selected = 0
        self.top_index = 0

        self.UI_MAX_ROWS = 10  # Visible count + 2
        self.UI_PAGE_LEN = 5

        # self._debug_file = open("/tmp/q_picker.log", "at", newline="\n")

        # Add to the end of UI.__init__
        self.search_mode = False
        self.filter_query = ""

    def hide_cursor(self):
        self.tty_out.write("\x1b[?25l")
        self.tty_out.flush()

    def show_cursor(self):
        self.tty_out.write("\x1b[?25h")
        self.tty_out.flush()

    def get_raw_rows(self):
        try:
            return os.get_terminal_size(self.tty_out.fileno()).lines
        except OSError:
            return 24

    def get_rows(self):
        return min(self.UI_MAX_ROWS, self.get_raw_rows())

    def update_selection_from_query(self):
        """Moves selection to the first directory matching filter_query without hiding items."""
        if not self.filter_query:
            return

        q = self.filter_query.lower()

        # Priority 1: Directory name STARTS WITH the query
        for idx, d in enumerate(self.dirs):
            if d.name.lower().startswith(q):
                self.selected = idx
                return

        # Priority 2: Fallback to substring match in directory name or description
        for idx, d in enumerate(self.dirs):
            if q in d.name.lower() or q in d.description.lower():
                self.selected = idx
                return

    def lines_to_render(self):
        """
        :return: Out lines array and visible count (only rows)
        :rtype: Tuple[List[str], int]
        """
        total_items = self._dirs_len
        selected = self.selected
        top_index = self.top_index

        # Query /dev/tty directly so pipes inside $() don't break terminal size detection
        term_rows = self.get_rows()

        max_visible = max(2, term_rows - 2)
        visible_count = min(total_items, max_visible)

        # Keep top_index aligned with current selection
        if selected < top_index:
            top_index = selected
        elif selected >= top_index + visible_count:
            top_index = selected - visible_count + 1

        needs_scrollbar = total_items > visible_count
        # return

        # Calculate scrollbar thumb size and position
        if needs_scrollbar:
            thumb_size = max(1, round(visible_count * visible_count / total_items))
            max_top = total_items - visible_count
            max_thumb_top = visible_count - thumb_size
            thumb_top = (
                round((top_index / max_top) * max_thumb_top) if max_top > 0 else 0
            )
        else:
            thumb_size = 0
            thumb_top = 0

        # Render UI
        # \x1b and \033 are the same (27 in DEC).
        # \x1b used for the control sequences and \033 for the visual things.
        out = []
        # Display query in header if active
        header_prefix = "Select directory in {} ({}/{}) ".format(
            Q_DIR, self.selected + 1, total_items
        )
        if self.search_mode or self.filter_query:
            header = (
                header_prefix
                + "\033[1;34m[Search: \033[0m{}\033[1;34m]:\033[0m".format(
                    self.filter_query
                )
            )
        else:
            header = header_prefix + "\033[1;34m[/, ↑/↓, Enter, ESC]:\033[0m"

        out.append(
            "\r\x1b[K\033[1;34m{}\033[0m\r".format(header)
        )  # \x1b[K removes from cursor to EOL

        for row_i in range(visible_count):
            item_idx = top_index + row_i
            d = self.dirs[item_idx]

            # Build visual scrollbar column
            if needs_scrollbar:
                if thumb_top <= row_i < thumb_top + thumb_size:
                    sb_char = "\033[36m█\033[0m"  # Cyan scrollbar thumb
                else:
                    sb_char = "\033[90m│\033[0m"  # Dim track line
                sb_prefix = sb_char + " "
            else:
                sb_prefix = ""

            # Format item row
            if item_idx == selected:
                out.append(
                    "\r\x1b[K{}{} > {}  {}{}\033[0m\r".format(
                        sb_prefix, "\033[7m", d.name, "\033[2m", d.description
                    )
                )
            else:
                out.append(
                    "\r\x1b[K{}   {}  {}{}\033[0m\r".format(
                        sb_prefix, d.name, "\033[2m", d.description
                    )
                )

        return out, visible_count

    def move_row(self, visible_count, delta, clamp=True):
        if delta == 0:
            return

        total_items = self._dirs_len

        self.selected += delta
        if self.selected < 0:  # Wrap around to bottom
            if clamp:
                self.selected = 0
                self.top_index = 0
            else:
                self.selected = total_items - 1
                self.top_index = max(0, total_items - visible_count)
        elif self.selected >= total_items:  # Wrap around to top
            if clamp:
                self.selected = total_items - 1
                self.top_index = max(0, total_items - visible_count)
            else:
                self.selected = 0
                self.top_index = 0

        if self.selected < self.top_index:
            self.top_index = self.selected
        elif self.selected >= self.top_index + visible_count:
            self.top_index = self.selected - visible_count + 1

    def clear(self, lines_rendered):
        self.tty_out.write("\x1b[{}A\x1b[J".format(lines_rendered))
        self.tty_out.flush()

    def process_key(self, visible_count, lines_rendered):
        key = read_key(self.tty_in)
        # self._debug_file.write(repr(key) + "\n")

        # 1. Backspace in search mode
        if key in ("\x7f", "\x08", "\x1b[3~"):
            if self.filter_query:
                self.filter_query = self.filter_query[:-1]
                self.update_selection_from_query()
            elif self.search_mode:
                self.search_mode = False

        # 2. Enter key - confirm selection
        elif key in ("\r", "\n"):  # Enter
            # Clear UI from screen
            # WARN: minus one because last line is without \n
            self.clear(lines_rendered - 1)
            # Print path to stdout for Zsh cd command
            print(self.dirs[self.selected].real_path)
            return "exit-0"

        # 3. ESC key - clear search query first, or exit app
        elif key in ("\x1b", "\x03") or (
            not self.search_mode and key == "q"
        ):  # ESC or Ctrl+C
            if self.search_mode or self.filter_query:
                self.search_mode = False
                self.filter_query = ""
            else:
                # Moves cursor up and removes lines
                self.clear(lines_rendered - 1)
                return "exit-1"

        elif key == "\x1b[A" or (not self.search_mode and key == "k"):  # Up / k
            self.move_row(visible_count, -1)
        elif key == "\x1b[B" or (not self.search_mode and key == "j"):  # Down / j
            self.move_row(visible_count, +1)
        elif key == "\x1b[5~" or (not self.search_mode and key == "K"):  # PageUp / K
            self.move_row(visible_count, -self.UI_PAGE_LEN)
        elif key == "\x1b[6~" or (not self.search_mode and key == "J"):  # PageDn / J
            self.move_row(visible_count, +self.UI_PAGE_LEN)

        # 5. Activate search mode with '/'
        elif key == "/" and not self.search_mode:
            self.search_mode = True

        # 6. Type printable characters to update query and jump to match
        elif self.search_mode and len(key) == 1 and key.isprintable():
            self.filter_query += key
            self.update_selection_from_query()

    def ui_main(self):
        """
        Main UI function.

        :return: Status indicating what action to take
        :rtype: Literal['exit-1', 'exit-0', 'continue']
        """

        out, visible_count = self.lines_to_render()
        lines_rendered = len(out)

        self.tty_out.write("\n".join(out))
        self.tty_out.flush()

        r = self.process_key(visible_count, lines_rendered)
        if r is not None:
            return r

        # Move cursor back up to top line for redraw
        self.tty_out.write("\x1b[{}A".format(lines_rendered - 1))
        self.tty_out.flush()
        return "continue"


def main_inner(tty_in, tty_out, dirs):
    ui = UI(tty_in, tty_out, dirs)
    ui.hide_cursor()

    try:
        while True:
            loop_result = ui.ui_main()

            if loop_result == "continue":
                continue
            elif loop_result == "exit-0":
                sys.exit(0)
            elif loop_result == "exit-1":
                sys.exit(1)

    finally:
        # Restore cursor & close handles
        ui.show_cursor()
        tty_out.write("\x1b[?25h")
        tty_out.flush()
        tty_out.close()
        tty_in.close()


def main():
    dirs = get_directories(Q_DIR)
    if not dirs:
        # Skip two lines (for p10k-like themes) and one line for the line itself
        sys.stderr.write(
            "\033[31mNo directories found in {}\033[0m\n\n\n".format(Q_DIR)
        )
        sys.exit(2)

    # Explicitly open /dev/tty for interactive input and rendering
    try:
        # fmt: off
        with \
            open("/dev/tty", "w") as tty_out, \
            open("/dev/tty", "rb", buffering=0) as tty_in \
        :
        # fmt: on
            return main_inner(tty_in, tty_out, dirs)
    except OSError as e:
        sys.stderr.write("\033[31mCannot open /dev/tty: {!s}\033[0m\n\n\n".format(e))
        sys.exit(2)


if __name__ == "__main__":
    main()
