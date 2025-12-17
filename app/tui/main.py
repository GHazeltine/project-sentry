import sys
import os
import multiprocessing
from datetime import datetime

# --- PATH HACK ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)
# -----------------

from app.workers.scanner import run_scanner
from app.database.models import ScanMission, FileRecord, engine
from app.database.report import generate_report
from sqlmodel import Session, select, func

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Static, Label, ProgressBar, DirectoryTree, ListView, ListItem, Log
from textual.screen import Screen

class SentryHeader(Static):
    def compose(self) -> ComposeResult:
        yield Label("PROJECT SENTRY: COMMAND CONSOLE", id="title")
        yield Label("● SYSTEM ONLINE", id="status")

class SelectionScreen(Screen):
    selected_paths = []

    def compose(self) -> ComposeResult:
        yield Label("MISSION SETUP: SELECT TARGETS", classes="header")
        
        yield Horizontal(
            Vertical(
                Label("1. Navigate & Select Folders/Drives:", classes="sub-header"),
                DirectoryTree("/", id="file-browser"), 
                Button("Add Selected Path", variant="primary", id="btn_add"),
                classes="left-pane"
            ),
            Vertical(
                Label("2. Mission Targets:", classes="sub-header"),
                ListView(id="target-list"),
                Button("CLEAR LIST", variant="warning", id="btn_clear"),
                classes="right-pane"
            ),
            classes="main-area"
        )
        
        yield Horizontal(
            Button("EXIT SYSTEM", variant="error", id="btn_exit_app"),
            Button("INITIATE SCAN PROTOCOL >>", variant="success", id="btn_start"),
            classes="bottom-row"
        )

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        pass 

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
            if not self.selected_paths: return 
            
            with Session(engine) as session:
                mission = ScanMission(root_paths=",".join(self.selected_paths), status="ACTIVE")
                session.add(mission)
                session.commit()
                session.refresh(mission)
                mission_id = mission.id
            
            self.app.push_screen(DashboardScreen(mission_id=mission_id, targets=self.selected_paths))
            
        elif event.button.id == "btn_exit_app":
            self.app.exit()

class DashboardScreen(Screen):
    """Screen 2: The Live Dashboard with Heartbeat Animation."""
    
    def __init__(self, mission_id, targets):
        super().__init__()
        self.mission_id = mission_id
        self.targets = targets
        self.worker_process = None
        self.last_logged_id = -1 
        self.anim_tick = 0 

    def compose(self) -> ComposeResult:
        yield SentryHeader()
        yield Container(
            Label(f"MISSION #{self.mission_id} ACTIVE", id="mission-status-label", classes="status-bar"),
            Vertical(
                Label("LIVE OPERATION LOG:", classes="log-header"),
                Log(id="live-log", highlight=True), 
                classes="panel-log"
            ),
            Vertical(
                Label("INITIALIZING ENGINE...", id="cpu-status"),
                # show_percentage=False hides the 0%
                ProgressBar(total=None, show_eta=False, show_percentage=False, id="cpu-progress"), 
                Label("Files Processed: 0", id="file-counter"),
                classes="panel"
            ),
            Horizontal(
                Button("GENERATE REPORT", variant="primary", id="btn_report", disabled=True),
                Button("RETURN TO MENU", variant="default", id="btn_return", disabled=True),
                Button("ABORT MISSION", variant="error", id="btn_quit"),
                classes="control-row"
            ),
            id="dashboard-container"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.worker_process = multiprocessing.Process(target=run_scanner, args=(self.mission_id,))
        self.worker_process.start()
        
        self.query_one("#live-log").write_line(f"[{datetime.now().time()}] Subroutine launched...")
        self.query_one("#cpu-progress").update(total=None) # Start indefinite
        
        self.set_interval(0.5, self.monitor_progress)

    def monitor_progress(self) -> None:
        try:
            with Session(engine) as session:
                # 1. Update Counter
                count = session.exec(select(func.count()).where(FileRecord.mission_id == self.mission_id)).one()
                self.query_one("#file-counter").update(f"Files Processed: {count}")

                # 2. Check for Completion
                mission = session.get(ScanMission, self.mission_id)
                
                if mission.status == "COMPLETED":
                    # --- FINISHED STATE ---
                    self.query_one("#cpu-progress").update(total=100, progress=100)
                    self.query_one("#mission-status-label").update(f"MISSION #{self.mission_id} COMPLETE")
                    self.query_one("#mission-status-label").styles.background = "#008800"
                    
                    self.query_one("#cpu-status").update("100% SCAN COMPLETE • ENGINE STANDBY")
                    
                    self.query_one("#btn_return").disabled = False
                    self.query_one("#btn_report").disabled = False
                    self.query_one("#btn_quit").display = False

                else:
                    # --- ACTIVE ANIMATION STATE ---
                    dots = "." * ((self.anim_tick % 3) + 1) 
                    self.anim_tick += 1
                    self.query_one("#cpu-status").update(f"CPU HASHING ENGINE RUNNING {dots}")

                # 3. Update Log
                last_file = session.exec(
                    select(FileRecord)
                    .where(FileRecord.mission_id == self.mission_id)
                    .order_by(FileRecord.id.desc())
                    .limit(1)
                ).first()
                
                if last_file and last_file.id != self.last_logged_id:
                    self.query_one("#live-log").write_line(f"Indexed: {last_file.filename} ({last_file.size_bytes} bytes)")
                    self.last_logged_id = last_file.id
                    
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_quit":
            if self.worker_process and self.worker_process.is_alive():
                self.worker_process.terminate()
            self.app.exit()
            
        elif event.button.id == "btn_return":
             self.app.pop_screen() 
             
        elif event.button.id == "btn_report":
            filename = generate_report()
            self.query_one("#live-log").write_line(f"SUCCESS: Report saved to {filename}")
            self.query_one("#btn_report").disabled = True 
            self.query_one("#btn_report").label = "REPORT SAVED"

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
    .panel-log { border: solid #00aa00; padding: 1; margin: 1; height: 1fr; }
    #live-log { background: #001100; color: #88ff88; height: 100%; overflow-y: scroll;}
    
    .status-bar { background: #004400; color: white; text-align: center; padding: 1; width: 100%; }
    #file-counter { text-align: center; text-style: bold; margin-top: 1; }
    .control-row { align: center middle; height: 3; margin-top: 1; }
    .bottom-row { align: center middle; height: 3; margin: 1; }
    #btn_exit_app { margin-right: 2; }
    """

    def on_mount(self) -> None:
        self.push_screen(SelectionScreen())

if __name__ == "__main__":
    app = SentryApp()
    app.run()
