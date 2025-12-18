from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DirectoryTree, Button, Label, Input, Static
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual import on
import os
import subprocess
from app.workers.scanner import run_scanner

class NetworkMountModal(ModalScreen):
    """Screen for mounting a remote drive."""
    def compose(self) -> ComposeResult:
        with Container(classes="modal_box"):
            yield Label("Mount Network Drive (SMB/CIFS)")
            yield Input(placeholder="//SERVER/Share", id="remote_path")
            yield Input(placeholder="Username", id="user")
            yield Input(placeholder="Password", password=True, id="password")
            yield Horizontal(
                Button("Mount", variant="success", id="btn_mount"),
                Button("Cancel", variant="error", id="btn_cancel"),
                classes="modal_buttons"
            )

    @on(Button.Pressed, "#btn_cancel")
    def cancel(self):
        self.dismiss()

    @on(Button.Pressed, "#btn_mount")
    def mount_drive(self):
        remote = self.query_one("#remote_path").value
        user = self.query_one("#user").value
        pwd = self.query_one("#password").value
        
        # Create a clean mount point name
        mount_name = remote.replace("/", "_").replace("\\", "_").strip("_")
        local_path = f"/mnt/{mount_name}"
        
        if not os.path.exists(local_path):
            os.makedirs(local_path)

        # Execute Mount Command
        cmd = [
            "mount", "-t", "cifs", remote, local_path,
            f"-o", f"username={user},password={pwd},ro" # ro = Read Only for safety
        ]
        
        try:
            subprocess.run(cmd, check=True)
            self.dismiss(f"Mounted {remote} at {local_path}")
        except Exception as e:
            self.dismiss(f"Error: {str(e)}")

class SentryApp(App):
    CSS = """
    .modal_box {
        background: $surface;
        border: solid green;
        padding: 2;
        width: 60;
        height: auto;
    }
    .modal_buttons {
        margin-top: 1;
        align: center middle;
    }
    #tree_panel {
        width: 100%;
        height: 70%;
        border: solid blue;
    }
    #status_panel {
        height: 20%;
        border: solid yellow;
        content-align: center middle;
    }
    .selected_path {
        background: green;
        color: white;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("m", "mount_network", "Mount Drive"),
        ("space", "toggle_select", "Select Folder"),
        ("s", "start_scan", "START SCAN"),
    ]

    selected_paths = set()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Navigate and Press [SPACE] to Select Folders. Press [M] to Mount Network Drive."),
            DirectoryTree("/", id="tree_panel"),
            id="main_container"
        )
        yield Static("Ready.", id="status_panel")
        yield Footer()

    def action_mount_network(self):
        def mount_callback(result):
            if result:
                self.query_one("#status_panel").update(str(result))
                self.query_one("#tree_panel").reload() # Refresh tree
        self.push_screen(NetworkMountModal(), mount_callback)

    def action_toggle_select(self):
        tree = self.query_one("#tree_panel")
        if tree.cursor_node:
            path = tree.cursor_node.data.path
            path_str = str(path)
            
            if path_str in self.selected_paths:
                self.selected_paths.remove(path_str)
                # Visual toggle would require custom Tree logic, 
                # for now we update status to show selection count.
            else:
                self.selected_paths.add(path_str)
            
            self.update_status()

    def update_status(self):
        count = len(self.selected_paths)
        targets = "\n".join(list(self.selected_paths)[-3:]) # Show last 3
        msg = f"Selected Targets: {count}\n{targets}..."
        self.query_one("#status_panel").update(msg)

    def action_start_scan(self):
        if not self.selected_paths:
            self.query_one("#status_panel").update("NO TARGETS SELECTED!")
            return
        
        self.query_one("#status_panel").update("🚀 SCANNING INITIATED... Check Logs.")
        
        # Launch Scanner in Background
        # In a real app we'd use a Worker, strictly calling the function here for V1
        targets = list(self.selected_paths)
        run_scanner(targets)
        self.query_one("#status_panel").update("✅ Scan Complete.")

if __name__ == "__main__":
    # Start the background Dashboard (FastAPI) automatically
    import threading
    import uvicorn
try:
    from server import app as web_app
except ImportError:
    from app.server import app as web_app
    
    # Run the web server in a separate thread so it doesn't block the TUI
    threading.Thread(target=lambda: uvicorn.run(web_app, host="0.0.0.0", port=8000), daemon=True).start()
    
    # Launch the TUI
    ui = SentryApp()
    ui.run()

