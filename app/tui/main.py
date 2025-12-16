import sys
import os
import multiprocessing

# --- PATH HACK (MUST BE FIRST) ---
# This tells Python where to look for the 'app' folder
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)
# -----------------------------------------------------------

# Now we can safely import our own code
from app.workers.scanner import run_scanner
from app.database.models import ScanMission, engine
from sqlmodel import Session

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Static, Label, ProgressBar, DirectoryTree, ListView, ListItem
from textual.screen import Screen

class SentryHeader(Static):
    """A sleek header for the project."""
    def compose(self) -> ComposeResult:
        yield Label("PROJECT SENTRY: COMMAND CONSOLE", id="title")
        yield Label("● SYSTEM ONLINE", id="status")

class SelectionScreen(Screen):
    """Screen 1: The Mission Planner."""
    selected_paths = []

    def compose(self) -> ComposeResult:
        yield Label("MISSION SETUP: SELECT TARGETS", classes="header")
        
        yield Horizontal(
            Vertical(
                Label("1. Navigate & Select Folders/Drives:", classes="sub-header"),
                DirectoryTree("/", id="file-browser"), 
                Button("Add Selected Path to Mission", variant="primary", id="btn_add"),
                classes="left-pane"
            ),
            Vertical(
                Label("2. Mission Targets:", classes="sub-header"),
                ListView(id="target-list"),
                Button("CLEAR LIST", variant="error", id="btn_clear"),
                classes="right-pane"
            ),
            classes="main-area"
        )
        
        yield Button("INITIATE SCAN PROTOCOL >>", variant="success", id="btn_start")

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.current_highlight = str(event.path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_add":
            tree = self.query_one(DirectoryTree)
            if tree.cursor_node:
                path_to_add = str(tree.cursor_node.data.path)
                if path_to_add not in self.selected_paths:
                    self.selected_paths.append(path_to_add)
                    self.query_one("#target-list").append(ListItem(Label(path_to_add)))
        
        elif event.button.id == "btn_clear":
            self.selected_paths = []
            self.query_one("#target-list").clear()

        elif event.button.id == "btn_start":
            if not self.selected_paths:
                return 
            
            # Create Mission in DB
            with Session(engine) as session:
                mission = ScanMission(
                    root_paths=",".join(self.selected_paths),
                    status="ACTIVE"
                )
                session.add(mission)
                session.commit()
                session.refresh(mission)
                mission_id = mission.id
            
            # Switch to Dashboard
            self.app.push_screen(DashboardScreen(mission_id=mission_id, targets=self.selected_paths))

class DashboardScreen(Screen):
    """Screen 2: The Live Dashboard."""
    
    def __init__(self, mission_id, targets):
        super().__init__()
        self.mission_id = mission_id
        self.targets = targets
        self.worker_process = None

    def compose(self) -> ComposeResult:
        yield SentryHeader()
        yield Container(
            Label(f"MISSION #{self.mission_id} ACTIVE - TARGETING {len(self.targets)} LOCATIONS", classes="status-bar"),
            Vertical(
                Label("Active Targets:", classes="log-header"),
                Label("\n".join(self.targets), classes="log-content"),
                classes="panel"
            ),
            Vertical(
                Label("CPU HASHING ENGINE", id="cpu-status"),
                ProgressBar(total=100, show_eta=True, id="cpu-progress"),
                classes="panel"
            ),
            Horizontal(
                Button("PAUSE OPERATION", variant="warning"),
                Button("ABORT MISSION", variant="error", id="btn_quit"),
                classes="control-row"
            ),
            id="dashboard-container"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called automatically when this screen appears."""
        # Launch the Scanner in a separate process!
        self.worker_process = multiprocessing.Process(
            target=run_scanner, 
            args=(self.mission_id,)
        )
        self.worker_process.start()
        self.query_one("#cpu-status").update(f"CPU HASHING ENGINE: PID {self.worker_process.pid} RUNNING")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_quit":
            if self.worker_process and self.worker_process.is_alive():
                self.worker_process.terminate()
            self.app.exit()

class SentryApp(App):
    CSS = """
    Screen { align: center middle; background: #0f1f2f; color: #00ff00; }
    #title { text-style: bold; margin-left: 1; }
    #status { color: #00ff00; text-align: right; margin-right: 1; }
    .header { text-align: center; text-style: bold; background: #004400; width: 100%; padding: 1; }
    .sub-header { text-align: center; background: #002200; width: 100%; }
    .main-area { height: 70%; margin: 1; }
    .left-pane { width: 50%; border: solid #00aa00; margin-right: 1; }
    .right-pane { width: 50%; border: solid #00aa00; margin-left: 1; }
    #file-browser { height: 1fr; background: #001100; color: #88ff88; }
    #target-list { height: 1fr; background: #001100; border: solid #004400; }
    #btn_add { width: 100%; margin-top: 1; }
    #btn_start { width: 60%; margin-top: 1; margin-bottom: 1; }
    .panel { border: solid #00aa00; padding: 1; margin: 1; height: auto; }
    .log-content { color: #88ff88; }
    .status-bar { background: #004400; color: white; text-align: center; padding: 1; width: 100%; }
    """

    def on_mount(self) -> None:
        self.push_screen(SelectionScreen())

if __name__ == "__main__":
    app = SentryApp()
    app.run()
