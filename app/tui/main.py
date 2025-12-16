import os
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
    """
    Screen 1: The Mission Planner.
    Allows user to browse the ACTUAL file system and select multiple targets.
    """
    selected_paths = []

    def compose(self) -> ComposeResult:
        yield Label("MISSION SETUP: SELECT TARGETS", classes="header")
        
        yield Horizontal(
            # Left Pane: The File Browser
            Vertical(
                Label("1. Navigate & Select Folders/Drives:", classes="sub-header"),
                # Start browsing from root (/) or /mnt depending on your setup
                DirectoryTree("/", id="file-browser"), 
                Button("Add Selected Path to Mission", variant="primary", id="btn_add"),
                classes="left-pane"
            ),
            # Right Pane: The Selected List
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
        """Helper to track what the user is highlighting in the tree."""
        self.current_highlight = str(event.path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "btn_add":
            # Add the currently selected tree node to the list
            tree = self.query_one(DirectoryTree)
            if tree.cursor_node:
                # Get path from the tree cursor
                path_to_add = str(tree.cursor_node.data.path)
                
                # Visual check: Don't add duplicates
                if path_to_add not in self.selected_paths:
                    self.selected_paths.append(path_to_add)
                    self.query_one("#target-list").append(ListItem(Label(path_to_add)))
        
        elif event.button.id == "btn_clear":
            self.selected_paths = []
            self.query_one("#target-list").clear()

        elif event.button.id == "btn_start":
            if not self.selected_paths:
                # In a real app, we'd show an error modal here
                return
            # Pass the selected targets to the dashboard
            self.app.push_screen(DashboardScreen(targets=self.selected_paths))

class DashboardScreen(Screen):
    """Screen 2: The Live Dashboard."""
    
    def __init__(self, targets):
        super().__init__()
        self.targets = targets

    def compose(self) -> ComposeResult:
        yield SentryHeader()
        yield Container(
            Label(f"MISSION ACTIVE - SCANNING {len(self.targets)} TARGETS", classes="status-bar"),
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_quit":
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
    """

    def on_mount(self) -> None:
        self.push_screen(SelectionScreen())

if __name__ == "__main__":
    app = SentryApp()
    app.run()
