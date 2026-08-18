import time
import psutil
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical
from textual.widgets import Header, Footer, DataTable, Static, Input

class MetricsZone(Grid):
    def compose(self):
        yield Static("DOWNLOAD SPEED: 0.00 B/s", id="down-speed")
        yield Static("UPLOAD SPEED: 0.00 B/s", id="up-speed")
        yield Static("Total Received: 0.00 B", id="down-total")
        yield Static("Total Transferred: 0.00 B", id="up-total")

    def on_mount(self):
        io_start = psutil.net_io_counters()
        self.last_bytes_recv = io_start.bytes_recv
        self.last_bytes_sent = io_start.bytes_sent
        self.last_time = time.time()
        self.set_interval(1.0, self.update_network_stats)

    def format_bytes(self, size_in_bytes):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} PB"

    def update_network_stats(self):
        current_io = psutil.net_io_counters()
        current_time = time.time()
        time_elapsed = current_time - self.last_time

        if time_elapsed <= 0:
            return

        download_speed = (current_io.bytes_recv - self.last_bytes_recv) / time_elapsed
        upload_speed = (current_io.bytes_sent - self.last_bytes_sent) / time_elapsed

        self.query_one("#down-speed", Static).update(f"DOWNLOAD SPEED: [bold cyan]{self.format_bytes(download_speed)}/s[/bold cyan]")
        self.query_one("#up-speed", Static).update(f"UPLOAD SPEED: [bold magenta]{self.format_bytes(upload_speed)}/s[/bold magenta]")
        self.query_one("#down-total", Static).update(f"Total Received: [bold]{self.format_bytes(current_io.bytes_recv)}[/bold]")
        self.query_one("#up-total", Static).update(f"Total Transferred: [bold]{self.format_bytes(current_io.bytes_sent)}[/bold]")

        self.last_bytes_recv = current_io.bytes_recv
        self.last_bytes_sent = current_io.bytes_sent
        self.last_time = current_time


class TableRec(Vertical):
    def compose(self):
        yield Input(placeholder="Type to filter by PID, Name, IP, or State (e.g., chrome, ESTABLISHED, 192.168)...", id="search-bar")
        yield DataTable(id="connections-table")

    def on_mount(self):
        data = self.query_one(DataTable)
        data.add_columns("PID", "NAME", "LOCAL ADDRESS", "FOREIGN ADDRESS", "STATE")
        data.cursor_type = "row"
        self.refresh_table()
        self.set_interval(2.0, self.refresh_table)

    def format_state(self, state):
        colors = {
            "ESTABLISHED": "[bold green]ESTABLISHED[/bold green]",
            "LISTEN": "[bold yellow]LISTEN[/bold yellow]",
            "TIME_WAIT": "[dim blue]TIME_WAIT[/dim blue]",
            "CLOSE_WAIT": "[bold red]CLOSE_WAIT[/bold red]",
            "SYN_SENT": "[bold magenta]SYN_SENT[/bold magenta]",
        }
        return colors.get(state, f"[dim]{state}[/dim]")

    def refresh_table(self):
        data = self.query_one(DataTable)
        search_bar = self.query_one("#search-bar", Input)
        query = search_bar.value.strip().lower()
        current_cursor = data.cursor_coordinate
        try:
            connections = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            connections = []

        rows = []
        for conn in connections[:120]:
            pid = str(conn.pid) if conn.pid else "N/A"
            name = "System / Unknown"
            if conn.pid:
                try:
                    name = psutil.Process(conn.pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    name = "Access Denied"
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
            raw_state = conn.status or "N/A"
            if query:
                searchable_text = f"{pid} {name} {laddr} {raddr} {raw_state}".lower()
                if query not in searchable_text:
                    continue

            formatted_state = self.format_state(raw_state)
            rows.append((pid, name, laddr, raddr, formatted_state))

        data.clear()
        data.add_rows(rows)
        if current_cursor and current_cursor.row < len(rows):
            data.move_cursor(row=current_cursor.row, column=current_cursor.column)


class SystemMonitor(App):
    CSS = """
    Screen {
        layout: vertical;
        background: $surface-darken-1;
    }

    MetricsZone {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1 2;
        padding: 1 1 0 1;
        height: 9;
        width: 100%;
    }

    MetricsZone Static {
        background: $panel;
        color: $text;
        border: solid $accent;
        content-align: center middle;
    }

    TableRec {
        height: 1fr;
        width: 100%;
        padding: 0 1 1 1;
    }

    #search-bar {
        margin: 0 0 1 0;
        border: tall $secondary;
        background: $surface;
    }

    DataTable {
        height: 100%;
        width: 100%;
        border: round $primary;
    }
    """

    BINDINGS = [
        ("d", "toggle_dark", "Toggle Theme"),
        ("/", "focus_search", "Search"),
        ("k", "kill_process", "Kill PID"),
        ("q", "quit", "Quit App"),
    ]

    TITLE = "TUI System Network Monitor"
    SUBTITLE = f"Date: {datetime.now().strftime('%Y-%m-%d')}"

    def compose(self):
        yield Header(show_clock=True)
        yield MetricsZone()
        yield TableRec()
        yield Footer()

    def action_focus_search(self):
        self.query_one("#search-bar", Input).focus()

    def action_kill_process(self):
        table = self.query_one(DataTable)
        if table.cursor_coordinate:
            row_idx = table.cursor_coordinate.row
            row_data = table.get_row_at(row_idx)
            pid_str = row_data[0]

            if pid_str.isdigit():
                pid = int(pid_str)
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                    proc.terminate()
                    self.notify(
                        f"Sent SIGTERM to process '{proc_name}' (PID {pid})",
                        title="Process Terminated",
                        severity="information",
                    )
                except psutil.AccessDenied:
                    self.notify(
                        f"Permission denied to kill PID {pid}. Try running with sudo.",
                        title="Access Denied",
                        severity="error",
                    )
                except psutil.NoSuchProcess:
                    self.notify(f"Process PID {pid} no longer exists.", severity="warning")
            else:
                self.notify("Selected row has no valid process PID.", severity="warning")

    def action_toggle_dark(self):
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"


if __name__ == "__main__":
    SystemMonitor().run()
