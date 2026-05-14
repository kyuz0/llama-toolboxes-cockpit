from textual.app import App, ComposeResult
from textual.theme import Theme
from textual import on, events, work
from textual.widgets import Header, Footer, TabbedContent, TabPane, Button, Static, Label, Input, Checkbox, DataTable, Collapsible, Select
from textual.containers import Vertical, Horizontal, VerticalScroll
import os
import subprocess

from src.toolbox_manager import get_all_toolboxes, get_installed_toolboxes, detect_engines, get_os_toolbox_cmd, get_remote_image_date, create_toolbox, delete_toolbox
from src.model_manager import scan_local_models, get_hf_quants, get_download_cmd, get_models_dir, save_models_dir, is_quant_downloaded, get_active_platform, save_active_platform
from src.server_runner import build_server_cmd
from src.config import load_models, get_platforms, get_platform, get_platform_registry
from src.widgets import ConfirmModal, SelectModal
import pyfiglet

def generate_banner() -> str:
    ascii_art = pyfiglet.figlet_format("Llama.cpp Cockpit", font="small")
    return f"[green]{ascii_art}[/green]"

class LlamaCockpitApp(App):
    TITLE = "Llama.cpp Cockpit"
    CSS = """
    DataTable > .datatable--cursor {
        background: #333333;
        color: auto;
        text-style: none;
    }
    
    DataTable.inactive-table > .datatable--cursor {
        background: transparent;
        text-style: none;
    }
    
    DataTable > .datatable--header {
        background: #2a2a2a;
    }
    
    OptionList > .option-list--option-highlighted {
        background: transparent;
        color: #e57373;
        text-style: bold;
    }
    
    Header {
        background: #d32f2f;
    }
    
    Tab, Tab:hover, Tab:focus, Tab.-active {
        background: transparent !important;
    }
    
    Tab:focus {
        color: #e57373 !important;
        text-style: bold;
    }
    
    Underline > .underline--active {
        background: #d32f2f !important;
    }
    
    Tabs .underline--active {
        background: #d32f2f !important;
    }
    
    Tabs:focus .underline--active {
        background: #d32f2f !important;
    }
    
    Tab.-active {
        color: #e57373 !important;
    }
    
    .field-label {
        margin-top: 1;
        margin-bottom: 0;
        text-style: bold;
        color: #e57373;
    }

    .inline-row {
        height: auto;
        max-height: 5;
        margin-top: 1;
    }

    .inline-row .inline-label {
        width: auto;
        min-width: 12;
        text-style: bold;
        color: #e57373;
        padding-right: 1;
        height: 1;
        content-align: left middle;
    }

    .inline-row Select {
        width: 1fr;
    }

    .inline-row Input {
        width: 1fr;
    }

    .short-field {
        width: 1fr;
        height: auto;
        max-height: 3;
        margin-right: 2;
    }

    .short-field .inline-label {
        width: auto;
        min-width: 8;
        height: 1;
    }

    .options-row {
        height: auto;
        max-height: 3;
        margin-top: 1;
    }

    .options-row Checkbox {
        margin-right: 4;
    }
    
    #banner {
        text-align: center;
        margin-bottom: 0;
        height: auto;
        text-style: bold;
    }
    
    #platform_row {
        align: center middle;
        height: auto;
        margin-bottom: 1;
    }
    
    #platform_label {
        color: #e57373;
        text-style: bold;
        margin-right: 2;
    }
    
    #btn_switch_platform {
        height: 1;
        min-width: 18;
        border: none;
        background: #333333;
    }
    
    #btn_switch_platform:hover {
        background: #d32f2f;
    }
    
    TabbedContent { height: 1fr; }
    
    TabPane { 
        padding: 1 2; 
    }
    
    .box { 
        padding: 1 2; 
        margin-bottom: 1; 
        background: $surface; 
        border: round #d32f2f; 
        color: $text;
        text-style: bold;
        text-align: center;
        height: auto;
    }
    
    #btn_row { 
        margin-top: 1; 
        height: auto; 
        align: left middle;
    }
    
    Button {
        margin-right: 1;
        height: 1;
        border: none;
        min-width: 12;
    }
    
    #host_port_row {
        height: auto;
    }
    
    #models_dir_row {
        height: auto;
        align: left middle;
        margin-bottom: 1;
    }
    #models_dir_row > Input {
        width: 1fr;
    }
    
    .btn-toggle-all {
        height: auto;
        min-width: 10;
        margin: 1 0;
        border: none;
        background: #333333;
    }
    .btn-toggle-all:hover {
        background: #d32f2f;
    }
    
    #host_port_row Vertical {
        width: 1fr;
        height: auto;
    }
    
    #inp_host, #inp_port {
        width: 1fr;
    }
    
    #toolbox_container {
        height: 1fr;
    }
    
    #toolbox_container DataTable {
        height: auto;
        border: none;
        margin-bottom: 1;
    }
    
    #toolbox_container Vertical {
        height: auto;
    }
    
    #local_model_list {
        border: solid #d32f2f;
        height: 1fr;
    }
    
    Input, Checkbox {
        margin: 0;
        height: 1;
        border: none;
    }
    
    ConfirmModal, SelectModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #confirm_dialog {
        width: 90%;
        max-width: 100;
        height: auto;
        border: solid #d32f2f;
        background: #1e1e1e;
        padding: 1 2;
    }
    
    #select_dialog {
        width: 90%;
        max-width: 100;
        height: 80%;
        border: solid #d32f2f;
        background: #1e1e1e;
        padding: 1 2;
    }
    
    #confirm_message, #select_title {
        text-align: center;
        text-style: bold;
        color: #e57373;
        margin-bottom: 1;
        width: 100%;
    }

    #confirm_buttons, #select_buttons {
        align: center middle;
        height: auto;
    }
    
    #select_list {
        border: solid #d32f2f;
        height: 1fr;
        min-height: 10;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(generate_banner(), id="banner")
        yield Horizontal(
            Label("", id="platform_label"),
            Button("Switch Platform", id="btn_switch_platform"),
            id="platform_row"
        )
        with TabbedContent(initial="tab-toolboxes"):
            with TabPane("Interactive Toolboxes", id="tab-toolboxes"):
                yield Vertical(
                    Static("Manage and enter llama.cpp toolbox containers. The cockpit auto-detects your OS and selects the correct backend (toolbox on Fedora/RHEL, distrobox on Ubuntu/Arch).", classes="box"),
                    VerticalScroll(id="toolbox_container"),
                    Horizontal(
                        Button("Enter", id="btn_enter", variant="success"),
                        Button("Create/Update", id="btn_create_update", variant="warning"),
                        Button("Delete", id="btn_delete", variant="error"),
                        Button("Check Updates", id="btn_check_updates"),
                        Button("Refresh", id="btn_refresh"),
                        id="btn_row"
                    )
                )
            with TabPane("Server Mode", id="tab-server"):
                yield VerticalScroll(
                    Static("Launch a Llama.cpp inference server directly without entering an interactive environment.", classes="box"),
                    Horizontal(
                        Label("Engine", classes="inline-label"),
                        Select([], id="sel_engine", prompt="Select Container Engine"),
                        classes="inline-row"
                    ),
                    Horizontal(
                        Label("Image", classes="inline-label"),
                        Select([], id="sel_image", prompt="Select Toolbox Image"),
                        classes="inline-row"
                    ),
                    Horizontal(
                        Label("Model", classes="inline-label"),
                        Select([], id="sel_model", prompt="Select Local Model"),
                        classes="inline-row"
                    ),
                    Horizontal(
                        Horizontal(Label("Context", classes="inline-label"), Input(placeholder="12288", id="inp_ctx", value="12288"), classes="short-field"),
                        Horizontal(Label("Host", classes="inline-label"), Input(placeholder="localhost", id="inp_host", value="localhost"), classes="short-field"),
                        Horizontal(Label("Port", classes="inline-label"), Input(placeholder="8080", id="inp_port", value="8080"), classes="short-field"),
                        classes="inline-row"
                    ),
                    Horizontal(
                        Checkbox("Flash Attention (-fa 1)", id="chk_fa", value=True),
                        Checkbox("No Memory Mapping (--no-mmap)", id="chk_no_mmap", value=True),
                        classes="options-row"
                    ),
                    Horizontal(
                        Label("Extra Args", classes="inline-label"),
                        Input(placeholder="e.g. --batch-size 512", id="inp_custom_args", value="--jinja"),
                        classes="inline-row"
                    ),
                    Horizontal(
                        Button("Start Server", id="btn_start_server", variant="primary"),
                        id="btn_row"
                    )
                )
            with TabPane("Model Manager", id="tab-models"):
                yield Vertical(
                    Static("Download and manage GGUF models for inference.\nModels will be downloaded to and scanned from the directory configured below.", classes="box"),
                    Horizontal(
                        Input(placeholder="~/models", id="inp_models_dir", value=str(get_models_dir())),
                        Button("Save Path", id="btn_save_models_path"),
                        id="models_dir_row"
                    ),
                    Horizontal(
                        Select([], id="sel_download_model", prompt="Download Curated Model"),
                        Button("Download", id="btn_download", variant="success"),
                        Button("Scan Local", id="btn_scan_models"),
                        id="btn_row"
                    ),
                    Label("Local GGUF Models", classes="inline-label"),
                    DataTable(id="local_model_list", cursor_type="row"),
                )
        yield Footer()

    def on_mount(self):
        cockpit_theme = Theme(
            name="cockpit-red",
            primary="#d32f2f",
            secondary="#b71c1c",
            accent="#e57373",
            foreground="#ffffff",
            background="#121212",
            surface="#1e1e1e",
            panel="#2a2a2a",
            warning="#ffa000",
            error="#d32f2f",
            success="#4caf50",
            dark=True,
        )
        self.register_theme(cockpit_theme)
        self.theme = "cockpit-red"
        
        self.active_platform_id = get_active_platform()
        self._update_platform_label()
        
        self.selected_toolboxes = set()
        self.refresh_toolboxes()
        self.refresh_models()
        
        engines = detect_engines()
        sel_engine = self.query_one("#sel_engine", Select)
        sel_engine.set_options([(e, e) for e in engines])
        if engines:
            sel_engine.value = engines[0]

        curated = load_models()
        sel_dl = self.query_one("#sel_download_model", Select)
        sel_dl.set_options([(m["name"], m["repo"]) for m in curated])

    def _update_platform_label(self):
        platform = get_platform(self.active_platform_id)
        if platform:
            name = platform.get("name", self.active_platform_id)
            desc = platform.get("description", "")
            self.query_one("#platform_label", Label).update(f"Platform: {name}  —  {desc}")
        else:
            self.query_one("#platform_label", Label).update(f"Platform: {self.active_platform_id}")

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected):
        if event.control.id and event.control.id.startswith("dt_"):
            try:
                name = event.control.get_cell_at((event.cursor_row, 1))
                if name in self.selected_toolboxes:
                    self.selected_toolboxes.remove(name)
                    event.control.update_cell_at((event.cursor_row, 0), "\\[ ]")
                else:
                    self.selected_toolboxes.add(name)
                    event.control.update_cell_at((event.cursor_row, 0), "\\[x]")
                

            except Exception:
                pass

    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted):
        if getattr(self, "_mounting_tables", False):
            return
            
        if event.control.id and event.control.id.startswith("dt_"):
            try:
                name = event.control.get_cell_at((event.cursor_row, 1))
                self.active_toolbox_name = name
                
                for dt in self.query(DataTable):
                    if dt.id and dt.id.startswith("dt_"):
                        if dt == event.control:
                            dt.remove_class("inactive-table")
                        else:
                            dt.add_class("inactive-table")
            except Exception:
                pass

    def on_descendant_focus(self, event: events.DescendantFocus):
        widget = event.widget
        if isinstance(widget, DataTable) and widget.id and widget.id.startswith("dt_"):
            for dt in self.query(DataTable):
                if dt.id and dt.id.startswith("dt_"):
                    if dt == widget:
                        dt.remove_class("inactive-table")
                        try:
                            self.active_toolbox_name = dt.get_cell_at((dt.cursor_row, 1))
                        except Exception:
                            pass
                    else:
                        dt.add_class("inactive-table")

    def get_selected_toolboxes(self):
        tb_dict = getattr(self, 'toolboxes_dict', {})
        selected = []
        if getattr(self, 'selected_toolboxes', set()):
            for name in self.selected_toolboxes:
                if name in tb_dict:
                    selected.append(tb_dict[name])
        return selected

    def get_selected_toolbox(self):
        tb_dict = getattr(self, 'toolboxes_dict', {})
        if getattr(self, 'selected_toolboxes', set()) and len(self.selected_toolboxes) == 1:
            return tb_dict.get(list(self.selected_toolboxes)[0])
        return None

    def refresh_toolboxes(self):
        self._mounting_tables = True
        
        platform = get_platform(self.active_platform_id)
        if not platform:
            self._mounting_tables = False
            return
        registry = platform.get("registry", "")
        grouped_data = get_all_toolboxes(registry, platform)
        
        self.toolboxes_dict = {}
        
        container = self.query_one("#toolbox_container", VerticalScroll)
        container.remove_children()
        
        for group_name, toolboxes in grouped_data.items():
            if not toolboxes: continue
            collapsed = group_name != "Official Toolboxes"
            table = DataTable(id=f"dt_{group_name.replace(' ', '_').replace('/', '')}", cursor_type="row")
            table.add_class("inactive-table")
            table.add_columns("Sel", "Toolbox Name", "Description", "Status", "Created", "Latest Release")
            
            for tb in toolboxes:
                self.toolboxes_dict[tb["name"]] = tb
                if tb["status"] == "Not Installed":
                    status_fmt = "[red]Needs Download[/red]"
                else:
                    status_fmt = "[green]Running[/green]" if "Up" in tb.get("status", "") else "[dim]Downloaded[/dim]"
                
                sel_fmt = "\\[x]" if tb['name'] in getattr(self, 'selected_toolboxes', set()) else "\\[ ]"
                table.add_row(sel_fmt, tb['name'], tb.get('description', ''), status_fmt, tb.get('created', ''), "")
                
            btn_toggle = Button("Select/Deselect All", id=f"btn_toggle_{table.id}", classes="btn-toggle-all")
            col = Collapsible(Vertical(btn_toggle, table), title=f"{group_name} ({len(toolboxes)})", collapsed=collapsed)
            container.mount(col)
            
        def finish_mounting():
            first = True
            for dt in self.query(DataTable):
                if dt.id and dt.id.startswith("dt_"):
                    if first and dt.row_count > 0:
                        dt.remove_class("inactive-table")
                        try:
                            self.active_toolbox_name = dt.get_cell_at((dt.cursor_row, 1))
                        except Exception:
                            pass
                        first = False
                    else:
                        dt.add_class("inactive-table")

            self._mounting_tables = False
            
        self.call_next(finish_mounting)


    def refresh_server_images(self):
        sel_engine = self.query_one("#sel_engine", Select)
        engine = sel_engine.value
        if not isinstance(engine, str): return
        
        registry = get_platform_registry(self.active_platform_id)
        installed = get_installed_toolboxes(registry, engine)
        sel_image = self.query_one("#sel_image", Select)
        images = sorted(set([tb['image'] for tb in installed]))
        sel_image.set_options([(img, img) for img in images])
        if images:
            sel_image.value = images[0]

    @on(Select.Changed, "#sel_engine")
    def on_engine_selected(self, event: Select.Changed):
        self.refresh_server_images()

    def refresh_models(self):
        models = scan_local_models()
        self.current_models = models
        dt = self.query_one("#local_model_list", DataTable)
        dt.clear(columns=True)
        dt.add_columns("Filename")
        
        sel_model = self.query_one("#sel_model", Select)
        model_opts = []
        
        for m in models:
            dt.add_row(m["name"])
            model_opts.append((m["name"], m["path"]))
            
        sel_model.set_options(model_opts)
        if model_opts:
            sel_model.value = model_opts[0][1]

    def on_button_pressed(self, event: Button.Pressed):
        handlers = {
            "btn_refresh": self._handle_refresh,
            "btn_scan_models": self._handle_scan_models,
            "btn_check_updates": self._handle_check_updates,
            "btn_delete": self._handle_delete,
            "btn_create_update": self._handle_create_update,
            "btn_enter": self._handle_enter_toolbox,
            "btn_start_server": self._handle_start_server,
            "btn_save_models_path": self._handle_save_models_path,
            "btn_download": self._handle_download,
            "btn_switch_platform": self._handle_switch_platform,
        }

        btn_id = event.button.id
        if btn_id in handlers:
            handlers[btn_id]()
        elif btn_id and btn_id.startswith("btn_toggle_dt_"):
            self._handle_toggle_select_all(btn_id)

    # ── Platform Switch Handler ─────────────────────────────────────

    def _handle_switch_platform(self):
        platforms = get_platforms()
        display_options = []
        for p in platforms:
            marker = "● " if p["id"] == self.active_platform_id else "  "
            display_options.append(f"{marker}{p['name']}  —  {p.get('description', '')}")
        self._switch_platforms = platforms
        self.app.push_screen(
            SelectModal("Select Platform:", display_options),
            self._on_platform_selected
        )

    def _on_platform_selected(self, choice_idx: int | None) -> None:
        if choice_idx is None:
            return
        platforms = self._switch_platforms
        if 0 <= choice_idx < len(platforms):
            new_id = platforms[choice_idx]["id"]
            if new_id == self.active_platform_id:
                return
            self.active_platform_id = new_id
            save_active_platform(new_id)
            self._update_platform_label()
            self.selected_toolboxes.clear()
            self.refresh_toolboxes()
            self.refresh_server_images()
            self.notify(f"Switched to {platforms[choice_idx]['name']}", timeout=3)

    # ── Toolbox Handlers ──────────────────────────────────────────

    def _handle_refresh(self):
        self.refresh_toolboxes()

    def _handle_check_updates(self):
        tbs = self.get_selected_toolboxes()
        if not tbs:
            self.notify("No toolboxes selected.", severity="warning")
            return
        self.notify(f"Checking updates for {len(tbs)} toolbox(es)...", timeout=3)
        self._check_updates_bg(tbs)

    @work(thread=True, exclusive=True)
    def _check_updates_bg(self, tbs: list):
        for tb in tbs:
            remote_date = get_remote_image_date(tb['image'])
            if remote_date:
                remote_date_str = remote_date[:10]
                self.app.call_from_thread(self._update_toolbox_cell, tb['name'], 5, remote_date_str)
                created_date = self._get_toolbox_cell(tb['name'], 4)
                if created_date and remote_date_str > created_date:
                    self.app.call_from_thread(self._update_toolbox_cell, tb['name'], 3, "[yellow]Needs Update[/yellow]")
        self.app.call_from_thread(self.notify, "Update check complete.", timeout=3)

    def _handle_delete(self):
        tbs = self.get_selected_toolboxes()
        tbs = [tb for tb in tbs if tb["status"] != "Not Installed"]
        if not tbs:
            self.notify("No installed toolboxes selected.", severity="warning")
            return
        names = ", ".join([tb['name'] for tb in tbs])
        self._pending_delete_tbs = tbs
        self.app.push_screen(
            ConfirmModal(f"Are you sure you want to delete: {names}?"),
            self._on_delete_confirmed
        )

    def _handle_create_update(self):
        tbs = self.get_selected_toolboxes()
        if not tbs:
            self.notify("No toolboxes selected.", severity="warning")
            return
        to_create, to_update, already_updated = [], [], []

        with self.suspend():
            print("\nChecking latest image versions from registry...")
        for tb in tbs:
            if tb["status"] == "Not Installed":
                to_create.append(tb)
            else:
                remote_date = get_remote_image_date(tb['image'])
                if remote_date:
                    remote_date_str = remote_date[:10]
                    if tb.get('created') and remote_date_str > tb.get('created', ''):
                        to_update.append(tb)
                    else:
                        already_updated.append(tb)
                else:
                    already_updated.append(tb)

        if already_updated:
            with self.suspend():
                print("\nThe following toolboxes are already up-to-date:")
                for tb in already_updated:
                    print(f"  - {tb['name']}")

        if not to_create and not to_update:
            with self.suspend():
                input("\nNothing to do. Press Enter to return to UI...")
            self.selected_toolboxes.clear()
            self.refresh_toolboxes()
            return

        if to_update:
            names = ", ".join([tb['name'] for tb in to_update])
            warning_msg = (
                f"The following toolboxes have updates available and will be DELETED and RECREATED:\n"
                f"  {names}\n\n"
                f"Any manually installed packages via apt/dnf inside them will be lost. Continue?"
            )
            self._pending_update_tbs = to_update
            self._pending_create_tbs = to_create
            self.app.push_screen(ConfirmModal(warning_msg), self._on_update_confirmed)
        else:
            self._do_create_toolboxes(to_create)

    def _handle_enter_toolbox(self):
        tb = self.get_selected_toolbox()
        if not tb:
            self.notify("Select exactly one toolbox to enter.", severity="warning")
            return
        if tb["status"] == "Not Installed":
            self.notify("Cannot enter a toolbox that is not installed.", severity="warning")
            return
        cmd = get_os_toolbox_cmd()
        with self.suspend():
            os.system(f"{cmd} enter {tb['name']}")

    # ── Server Handler ────────────────────────────────────────────

    def _handle_start_server(self):
        engine = self.query_one("#sel_engine", Select).value
        image = self.query_one("#sel_image", Select).value
        model_path = self.query_one("#sel_model", Select).value
        ctx = self.query_one("#inp_ctx", Input).value
        host = self.query_one("#inp_host", Input).value
        port = self.query_one("#inp_port", Input).value
        use_fa = self.query_one("#chk_fa", Checkbox).value
        use_no_mmap = self.query_one("#chk_no_mmap", Checkbox).value
        custom_args = self.query_one("#inp_custom_args", Input).value

        if engine and image and model_path and ctx.isdigit():
            cmd = build_server_cmd(engine, image, model_path, int(ctx), use_fa, use_no_mmap, custom_args, host, port)
            with self.suspend():
                print(f"\nStarting server with command:\n{' '.join(cmd)}\n")
                print("Press Ctrl+C to stop the server and return to the UI.\n")
                subprocess.run(cmd)

    # ── Toggle Select All ─────────────────────────────────────────

    def _handle_toggle_select_all(self, btn_id: str):
        dt_id = btn_id.replace("btn_toggle_", "")
        dt = self.query_one(f"#{dt_id}", DataTable)

        all_selected = all(
            dt.get_cell_at((i, 1)) in self.selected_toolboxes
            for i in range(dt.row_count)
        )

        for i in range(dt.row_count):
            name = dt.get_cell_at((i, 1))
            if all_selected:
                self.selected_toolboxes.discard(name)
                dt.update_cell_at((i, 0), "\\[ ]")
            else:
                self.selected_toolboxes.add(name)
                dt.update_cell_at((i, 0), "\\[x]")



    # ── Model Manager Handlers ────────────────────────────────────

    def _handle_scan_models(self):
        self.refresh_models()

    def _handle_save_models_path(self):
        new_path = self.query_one("#inp_models_dir", Input).value
        if save_models_dir(new_path):
            self.notify(f"Models directory updated to {new_path}")
            self.refresh_models()
        else:
            self.notify("Failed to save models directory config.", severity="error")

    def _handle_download(self):
        repo = self.query_one("#sel_download_model", Select).value
        if not isinstance(repo, str) or not repo:
            return
        with self.suspend():
            print(f"\nQuerying Hugging Face for {repo}...")
        quants = get_hf_quants(repo)
        if not quants:
            with self.suspend():
                print("No GGUF quants found.")
                try: input("Press Enter to return...")
                except: pass
            return

        display_options = []
        installed_flags = []
        with self.suspend():
            print("\nChecking local installation status...")
        for q in quants:
            if is_quant_downloaded(repo, q):
                display_options.append(f"[green]\u2713 Installed[/green]  {q}")
                installed_flags.append(True)
            else:
                display_options.append(q)
                installed_flags.append(False)

        self._download_quants = quants
        self._download_installed_flags = installed_flags
        self._download_repo = repo
        self.app.push_screen(
            SelectModal("Available Quantizations:", display_options),
            self._on_quant_selected
        )

    # ── DataTable Helpers ─────────────────────────────────────────

    def _update_toolbox_cell(self, name: str, col: int, value: str):
        for dt in self.query(DataTable):
            if dt.id and dt.id.startswith("dt_"):
                for row_idx in range(dt.row_count):
                    if dt.get_cell_at((row_idx, 1)) == name:
                        dt.update_cell_at((row_idx, col), value)
                        return

    def _get_toolbox_cell(self, name: str, col: int):
        for dt in self.query(DataTable):
            if dt.id and dt.id.startswith("dt_"):
                for row_idx in range(dt.row_count):
                    if dt.get_cell_at((row_idx, 1)) == name:
                        return dt.get_cell_at((row_idx, col))
        return None

    def _on_delete_confirmed(self, confirmed: bool) -> None:
        if confirmed:
            tbs = self._pending_delete_tbs
            with self.suspend():
                for tb in tbs:
                    print(f"Deleting {tb['name']}...")
                    delete_toolbox(tb['name'])
            self.selected_toolboxes.clear()
            self.refresh_toolboxes()

    def _on_update_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            return
        to_update = self._pending_update_tbs
        to_create = self._pending_create_tbs
        with self.suspend():
            for tb in to_update:
                delete_toolbox(tb['name'])
        self._do_create_toolboxes(to_create + to_update)

    def _do_create_toolboxes(self, tbs: list) -> None:
        with self.suspend():
            for tb in tbs:
                print(f"\nDownloading and creating toolbox {tb['name']}...")
                create_toolbox(tb['name'], tb['image'], tb.get('args', []))
            input("\nSuccess! Press Enter to return to UI...")
        self.selected_toolboxes.clear()
        self.refresh_toolboxes()

    def _on_quant_selected(self, choice_idx: int | None) -> None:
        if choice_idx is None:
            return
        quants = self._download_quants
        installed_flags = self._download_installed_flags
        repo = self._download_repo
        if 0 <= choice_idx < len(quants):
            self._download_choice_idx = choice_idx
            if installed_flags[choice_idx]:
                self.app.push_screen(
                    ConfirmModal(f"The quant {quants[choice_idx]} appears to be already downloaded.\nDo you want to download it anyway?"),
                    self._on_redownload_confirmed
                )
            else:
                self._do_download_quant(repo, quants[choice_idx])

    def _on_redownload_confirmed(self, confirmed: bool) -> None:
        if confirmed:
            self._do_download_quant(self._download_repo, self._download_quants[self._download_choice_idx])

    def _do_download_quant(self, repo: str, quant: str) -> None:
        cmd = get_download_cmd(repo, quant)
        with self.suspend():
            print(f"\nRunning: HF_XET_HIGH_PERFORMANCE=1 {' '.join(cmd)}")
            try:
                env = os.environ.copy()
                env["HF_XET_HIGH_PERFORMANCE"] = "1"
                subprocess.run(cmd, env=env, check=True)
                print("\nDownload Complete!")
            except FileNotFoundError:
                print("\n[ERROR] 'hf' is not installed or not found in PATH.")
            except subprocess.CalledProcessError as e:
                print(f"\n[ERROR] Download failed with exit code {e.returncode}.")
            except Exception as e:
                print(f"\n[ERROR] An unexpected error occurred: {e}")
            try:
                input("\nPress Enter to return to UI...")
            except EOFError:
                pass
        self.refresh_models()

def cli_main():
    app = LlamaCockpitApp()
    app.run()

if __name__ == "__main__":
    cli_main()
