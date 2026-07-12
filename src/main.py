from textual.app import App, ComposeResult
from textual.theme import Theme
from textual import on, events, work
from textual.widgets import Header, Footer, TabbedContent, TabPane, Button, Static, Label, Input, Checkbox, DataTable, Collapsible
from textual.containers import Vertical, Horizontal, VerticalScroll
import os
import shlex
import subprocess
import time

from src.toolbox_manager import get_all_toolboxes, get_installed_toolboxes, detect_engines, get_os_toolbox_cmd, get_remote_image_date, is_remote_image_newer, create_toolbox, delete_toolbox
from src.model_manager import scan_local_models, get_hf_quants, get_download_cmd, get_models_dir, save_models_dir, is_quant_downloaded, get_active_platform, save_active_platform, get_default_toolbox, save_default_toolbox, get_benchmark_results_dir, save_benchmark_results_dir
from src.server_runner import build_server_cmd
from src.benchmark_runner import BenchmarkSettings, build_benchmark_jobs, run_benchmark_job, write_curve_summary
from src.config import load_models, get_platforms, get_platform, get_platform_registry, get_model_config, get_inference_profiles, get_mtp_config
from src.widgets import ConfirmModal, SelectModal, SearchableSelect
import pyfiglet

import importlib.metadata

def generate_banner() -> str:
    ascii_art = pyfiglet.figlet_format("Llama.cpp Cockpit", font="small")
    try:
        version = importlib.metadata.version("llama-cockpit")
        version_str = f"v{version}"
    except Exception:
        version_str = "v?.?.?"
        
    return f"[green]{ascii_art}[/green][dim]{version_str}[/dim]"

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

    .field-help {
        color: #9e9e9e;
        height: auto;
        margin-top: 1;
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

    .inline-row SearchableSelect {
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
        border: none;
        height: 1fr;
    }

    #benchmark_toolbox_list, #benchmark_model_list {
        border: none;
        height: 10;
    }

    #benchmark_selection_row {
        height: auto;
    }

    #benchmark_selection_row > Vertical {
        width: 1fr;
        height: auto;
    }

    #benchmark_settings_grid {
        height: auto;
    }

    #benchmark_settings_grid > Vertical {
        width: 1fr;
        height: auto;
        margin-right: 2;
    }

    #benchmark_results_row {
        height: auto;
    }

    #benchmark_results_row > Input {
        width: 1fr;
    }

    #inp_benchmark_rocm_ubatch, #inp_benchmark_vulkan_ubatch {
        width: 1fr;
    }

    #benchmark_options_row, #benchmark_kv_cache_row {
        height: auto;
        margin-top: 1;
    }

    #benchmark_options_row Checkbox {
        margin-right: 4;
    }

    #benchmark_kv_cache_row {
        display: none;
    }

    #benchmark_kv_cache_row .inline-label {
        width: auto;
        min-width: 16;
        color: #e57373;
        text-style: bold;
        padding-right: 1;
    }

    #benchmark_kv_cache_row SearchableSelect {
        width: 1fr;
        height: 3;
    }

    #benchmark_view Input {
        height: 3;
        padding: 0 1;
        background: #2a2a2a;
        border: tall #333333;
    }

    #benchmark_view Input:hover {
        border: tall #e57373;
    }

    #benchmark_view Input:focus {
        background: #333333;
        border: tall #d32f2f;
        color: #ffffff;
    }
    
    #model_manager_view {
        height: 1fr;
        padding: 0;
    }
    
    .model-zone {
        background: #1e1e1e;
        border: round #333333;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
    }
    
    .model-zone:focus-within {
        border: round #d32f2f;
    }
    
    #download_zone {
        height: auto;
    }
    
    #local_zone {
        height: 1fr;
    }
    
    .zone-title {
        color: #e57373;
        text-style: bold;
        background: transparent;
        width: 100%;
        margin-bottom: 0;
        margin-top: 0;
        height: auto;
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
    
    #mtp_zone, #profile_zone {
        display: none;
    }
    
    #lbl_profile_desc {
        color: #999999;
        text-style: italic;
        height: auto;
        margin-left: 1;
        width: 1fr;
    }
    
    .mtp-params-row {
        height: auto;
        max-height: 3;
    }
    
    .mtp-params-row .short-field {
        margin-right: 2;
    }
    
    #kv_cache_options_row {
        height: auto;
        max-height: 5;
        margin-top: 0;
        display: none;
    }
    
    #kv_cache_options_row .inline-label {
        width: auto;
        min-width: 12;
        text-style: bold;
        color: #e57373;
        padding-right: 1;
        height: 1;
        content-align: left middle;
    }
    
    #kv_cache_options_row SearchableSelect {
        width: 1fr;
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
                        Button("Set Default", id="btn_set_default", variant="primary"),
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
                        SearchableSelect(prompt="Select Container Engine", id="sel_engine"),
                        classes="inline-row"
                    ),
                    Horizontal(
                        Label("Image", classes="inline-label"),
                        SearchableSelect(prompt="Select Toolbox Image", id="sel_image"),
                        classes="inline-row"
                    ),
                    Horizontal(
                        Label("Model", classes="inline-label"),
                        SearchableSelect(prompt="Select Local Model", id="sel_model"),
                        classes="inline-row"
                    ),
                    Vertical(
                        Label("🧪 MTP (Multi-Token Prediction)", classes="zone-title"),
                        Horizontal(
                            Checkbox("Enable MTP Speculative Decoding", id="chk_mtp_enable", value=True),
                            classes="options-row"
                        ),
                        Horizontal(
                            Horizontal(Label("Draft Tokens", classes="inline-label"), Input(placeholder="2", id="inp_mtp_draft_n", value="2"), classes="short-field"),
                            Horizontal(Label("Parallel Seq", classes="inline-label"), Input(placeholder="1", id="inp_mtp_np", value="1"), classes="short-field"),
                            classes="mtp-params-row"
                        ),
                        id="mtp_zone", classes="model-zone"
                    ),
                    Vertical(
                        Label("🎛️ Inference Profile", classes="zone-title"),
                        Horizontal(
                            Label("Profile", classes="inline-label"),
                            SearchableSelect(prompt="Select inference profile...", id="sel_inference_profile"),
                            Label("", id="lbl_profile_desc"),
                            classes="inline-row"
                        ),
                        id="profile_zone", classes="model-zone"
                    ),
                    Horizontal(
                        Horizontal(Label("Context", classes="inline-label"), Input(placeholder="126976", id="inp_ctx", value="126976"), classes="short-field"),
                        Horizontal(Label("NGL", classes="inline-label"), Input(placeholder="999", id="inp_ngl", value="999"), classes="short-field"),
                        Horizontal(Label("Host", classes="inline-label"), Input(placeholder="localhost", id="inp_host", value="localhost"), classes="short-field"),
                        Horizontal(Label("Port", classes="inline-label"), Input(placeholder="8080", id="inp_port", value="8080"), classes="short-field"),
                        classes="inline-row"
                    ),
                    Horizontal(
                        Checkbox("Flash Attention (-fa 1)", id="chk_fa", value=True),
                        Checkbox("No Memory Mapping (--no-mmap)", id="chk_no_mmap", value=True),
                        Checkbox("KV Cache Quantization", id="chk_kv_cache", value=False),
                        classes="options-row"
                    ),
                    Horizontal(
                        Label("KV Cache Type", classes="inline-label"),
                        SearchableSelect(prompt="Select KV cache quant type", id="sel_kv_cache_type"),
                        id="kv_cache_options_row"
                    ),
                    Horizontal(
                        Label("HIP Devices", classes="inline-label", id="lbl_gpu_devices"),
                        Input(placeholder="e.g. 0 (leave empty to unset)", id="inp_hip_devices", value=""),
                        classes="inline-row"
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
                with Vertical(id="model_manager_view"):
                    # Zone 1: Hugging Face Downloader
                    with Vertical(id="download_zone", classes="model-zone"):
                        yield Label("📥 Curated HF Downloader", classes="zone-title")
                        with Horizontal(classes="inline-row"):
                            yield Label("Model Repo", classes="inline-label")
                            yield SearchableSelect(prompt="Search curated models (e.g. Qwen, Gemma)...", id="sel_download_model")
                            yield Button("Download", id="btn_download", variant="success")

                    # Zone 2: Local Models Library
                    with Vertical(id="local_zone", classes="model-zone"):
                        yield Label("📂 Local GGUF Directory", classes="zone-title")
                        with Horizontal(classes="inline-row"):
                            yield Label("Storage Path", classes="inline-label")
                            yield Input(placeholder="e.g. ~/models", id="inp_models_dir", value=str(get_models_dir()))
                            yield Button("Save Path", id="btn_save_models_path")
                            yield Button("Scan Local", id="btn_scan_models", variant="primary")

                        yield DataTable(id="local_model_list", cursor_type="row")
            with TabPane("Benchmark", id="tab-benchmark"):
                with VerticalScroll(id="benchmark_view"):
                    yield Static("Measure fixed prefill and generation workloads at identical starting KV depths. Raw JSONL and a combined CSV are saved in the results folder.", classes="box")
                    with Horizontal(id="benchmark_selection_row"):
                        with Vertical(classes="model-zone"):
                            yield Label("Toolboxes", classes="zone-title")
                            yield Button("Select/Deselect All", id="btn_benchmark_toggle_toolboxes", classes="btn-toggle-all")
                            yield DataTable(id="benchmark_toolbox_list", cursor_type="row")
                        with Vertical(classes="model-zone"):
                            yield Label("Models", classes="zone-title")
                            yield Button("Select/Deselect All", id="btn_benchmark_toggle_models", classes="btn-toggle-all")
                            yield DataTable(id="benchmark_model_list", cursor_type="row")

                    with Vertical(classes="model-zone"):
                        yield Label("Benchmark Settings", classes="zone-title")
                        with Horizontal(id="benchmark_settings_grid"):
                            with Vertical():
                                yield Label("Maximum starting depth", classes="field-label")
                                yield Input(value="65536", id="inp_benchmark_max_context")
                                yield Label("Starting depth step", classes="field-label")
                                yield Input(value="8192", id="inp_benchmark_context_step")
                                yield Label("Prefill chunk", classes="field-label")
                                yield Input(value="2048", id="inp_benchmark_prefill")
                            with Vertical():
                                yield Label("Generation tokens per frontier", classes="field-label")
                                yield Input(value="128", id="inp_benchmark_generation")
                                yield Label("Repetitions", classes="field-label")
                                yield Input(value="3", id="inp_benchmark_repetitions")
                                yield Label("Cooldown between runs (seconds)", classes="field-label")
                                yield Input(value="10", id="inp_benchmark_cooldown")
                                yield Label("Extra llama-bench arguments", classes="field-label")
                                yield Input(placeholder="Optional", id="inp_benchmark_extra_args")
                            with Vertical():
                                yield Label("ROCm / Vulkan ubatch override", classes="field-label")
                                with Horizontal(classes="inline-row"):
                                    yield Input(placeholder="Auto", id="inp_benchmark_rocm_ubatch")
                                    yield Input(placeholder="Auto", id="inp_benchmark_vulkan_ubatch")
                                yield Static(
                                    "Auto uses a measured model/platform value when available; otherwise llama.cpp's default.",
                                    classes="field-help",
                                )
                        with Horizontal(id="benchmark_options_row"):
                            yield Checkbox("Flash Attention (-fa 1)", id="chk_benchmark_fa", value=True)
                            yield Checkbox("No Memory Mapping (-mmp 0)", id="chk_benchmark_no_mmap", value=True)
                            yield Checkbox("KV Cache Quantization", id="chk_benchmark_kv_cache", value=False)
                        with Horizontal(id="benchmark_kv_cache_row"):
                            yield Label("KV Cache Type", classes="inline-label")
                            yield SearchableSelect(prompt="Select KV cache quant type", id="sel_benchmark_kv_cache_type")

                    with Vertical(classes="model-zone"):
                        yield Label("Results", classes="zone-title")
                        with Horizontal(id="benchmark_results_row"):
                            yield Input(value=str(get_benchmark_results_dir()), id="inp_benchmark_results_dir")
                            yield Button("Save Folder", id="btn_save_benchmark_path")
                            yield Button("Run Benchmarks", id="btn_run_benchmarks", variant="primary")
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
        self.selected_benchmark_toolboxes = set()
        self.selected_benchmark_models = set()
        self.refresh_toolboxes()
        self.refresh_models()
        self.check_app_updates()
        
        engines = detect_engines()
        sel_engine = self.query_one("#sel_engine", SearchableSelect)
        sel_engine.set_options([(e, e) for e in engines])
        if engines:
            sel_engine.value = engines[0]

        sel_kv = self.query_one("#sel_kv_cache_type", SearchableSelect)
        sel_kv.set_options([
            ("q8_0 (recommended)", "q8_0"),
            ("q5_1", "q5_1"),
            ("q5_0", "q5_0"),
            ("q4_1", "q4_1"),
            ("q4_0 (aggressive)", "q4_0"),
            ("iq4_nl", "iq4_nl"),
        ])
        sel_kv.value = "q8_0"

        sel_benchmark_kv = self.query_one("#sel_benchmark_kv_cache_type", SearchableSelect)
        sel_benchmark_kv.set_options([
            ("q8_0 (recommended)", "q8_0"),
            ("q5_1", "q5_1"),
            ("q5_0", "q5_0"),
            ("q4_1", "q4_1"),
            ("q4_0 (aggressive)", "q4_0"),
            ("iq4_nl", "iq4_nl"),
        ])
        sel_benchmark_kv.value = "q8_0"

        curated = load_models()
        sel_dl = self.query_one("#sel_download_model", SearchableSelect)
        dl_options = []
        for m in curated:
            compat = m.get("compatible_toolboxes")
            if compat:
                compat_str = ", ".join(compat)
                display_name = f"{m['name']} (Compatible with: {compat_str})"
            else:
                display_name = m["name"]
            dl_options.append((display_name, m["repo"]))
        sel_dl.set_options(dl_options)

    @work(thread=True)
    def check_app_updates(self):
        import urllib.request
        import json
        import importlib.metadata
        try:
            current_version = importlib.metadata.version("llama-cockpit")
            req = urllib.request.Request("https://api.github.com/repos/kyuz0/llama-toolboxes-cockpit/tags")
            req.add_header('User-Agent', 'Llama-Cockpit-Update-Checker')
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                if data:
                    latest_tag = data[0]['name']
                    latest_version = latest_tag.lstrip('v')
                    
                    curr_parts = tuple(int(x) for x in current_version.split('.') if x.isdigit())
                    latest_parts = tuple(int(x) for x in latest_version.split('.') if x.isdigit())
                    
                    if latest_parts > curr_parts:
                        msg = f"Update available: v{latest_version} (Current: v{current_version}).\nRun `pipx upgrade llama-cockpit` to update."
                        self.app.call_from_thread(self.notify, msg, title="Cockpit Update Available", severity="information", timeout=15)
        except Exception:
            pass

    def _update_platform_label(self):
        platform = get_platform(self.active_platform_id)
        if platform:
            name = platform.get("name", self.active_platform_id)
            desc = platform.get("description", "")
            self.query_one("#platform_label", Label).update(f"Platform: {name}  —  {desc}")
        else:
            self.query_one("#platform_label", Label).update(f"Platform: {self.active_platform_id}")

        try:
            lbl_gpu = self.query_one("#lbl_gpu_devices", Label)
            inp_gpu = self.query_one("#inp_hip_devices", Input)
            if "intel" in self.active_platform_id.lower():
                lbl_gpu.update("Level Zero Devices")
                inp_gpu.placeholder = "e.g. 0.0 (leave empty to unset)"
            else:
                lbl_gpu.update("HIP Devices")
                inp_gpu.placeholder = "e.g. 0 (leave empty to unset)"
        except Exception:
            pass

    def _toggle_row_selection(self, dt: DataTable, cursor_row: int):
        try:
            name = dt.get_cell_at((cursor_row, 1))
            if name in self.selected_toolboxes:
                self.selected_toolboxes.remove(name)
                dt.update_cell_at((cursor_row, 0), "\\[ ]")
            else:
                self.selected_toolboxes.add(name)
                dt.update_cell_at((cursor_row, 0), "\\[x]")
        except Exception:
            pass

    @on(events.MouseUp)
    def on_mouse_up(self, event: events.MouseUp):
        if isinstance(event.control, DataTable) and event.control.id and event.control.id.startswith("dt_"):
            import time
            self._last_dt_click_time = time.time()

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected):
        if event.control.id and event.control.id.startswith("dt_"):
            self._toggle_row_selection(event.control, event.cursor_row)

    @on(DataTable.RowSelected, "#benchmark_toolbox_list")
    def on_benchmark_toolbox_selected(self, event: DataTable.RowSelected):
        self._toggle_benchmark_selection(
            event.control,
            event.cursor_row,
            self.selected_benchmark_toolboxes,
        )

    @on(DataTable.RowSelected, "#benchmark_model_list")
    def on_benchmark_model_selected(self, event: DataTable.RowSelected):
        self._toggle_benchmark_selection(
            event.control,
            event.cursor_row,
            self.selected_benchmark_models,
        )

    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted):
        if getattr(self, "_mounting_tables", False):
            return
            
        if event.control.id and event.control.id.startswith("dt_"):
            import time
            if time.time() - getattr(self, "_last_dt_click_time", 0.0) < 0.1:
                self._toggle_row_selection(event.control, event.cursor_row)
                
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

    @staticmethod
    def _toggle_benchmark_selection(dt: DataTable, cursor_row: int, selected: set):
        try:
            key = dt.get_cell_at((cursor_row, 1))
            if key in selected:
                selected.remove(key)
                dt.update_cell_at((cursor_row, 0), "\\[ ]")
            else:
                selected.add(key)
                dt.update_cell_at((cursor_row, 0), "\\[x]")
        except Exception:
            pass

    def refresh_benchmark_toolboxes(self):
        try:
            dt = self.query_one("#benchmark_toolbox_list", DataTable)
        except Exception:
            return

        installed = {
            name: tb for name, tb in getattr(self, "toolboxes_dict", {}).items()
            if tb.get("status") != "Not Installed"
        }
        self.selected_benchmark_toolboxes.intersection_update(installed)

        dt.clear(columns=True)
        dt.add_columns("Sel", "Toolbox", "Image")
        for name in sorted(installed):
            marker = "\\[x]" if name in self.selected_benchmark_toolboxes else "\\[ ]"
            dt.add_row(marker, name, installed[name].get("image", ""))

    def refresh_benchmark_models(self):
        try:
            dt = self.query_one("#benchmark_model_list", DataTable)
        except Exception:
            return

        models = getattr(self, "current_models", [])
        available_paths = {model["path"] for model in models}
        self.selected_benchmark_models.intersection_update(available_paths)

        dt.clear(columns=True)
        dt.add_columns("Sel", "Path")
        for model in models:
            path = model["path"]
            marker = "\\[x]" if path in self.selected_benchmark_models else "\\[ ]"
            dt.add_row(marker, path)

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
        
        default_tag = get_default_toolbox(self.active_platform_id)
        if not default_tag:
            default_tag = platform.get("default_toolbox_tag")
        
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
                
                desc = tb.get('description', '')
                if default_tag and default_tag in tb.get('image', ''):
                    desc = f"[bold #e57373](Default)[/] {desc}"
                
                sel_fmt = "\\[x]" if tb['name'] in getattr(self, 'selected_toolboxes', set()) else "\\[ ]"
                table.add_row(sel_fmt, tb['name'], desc, status_fmt, tb.get('created', '')[:10], "")
                
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
            
        self.refresh_benchmark_toolboxes()
        self.call_next(finish_mounting)


    def refresh_server_images(self):
        sel_engine = self.query_one("#sel_engine", SearchableSelect)
        engine = sel_engine.value
        if not isinstance(engine, str) or not engine: return
        
        platform = get_platform(self.active_platform_id)
        registry = platform.get("registry", "") if platform else ""
        installed = get_installed_toolboxes(registry, engine)
        
        # Get all configured images for the platform from toolboxes.json
        configured_images = []
        if platform:
            for group in platform.get("groups", []):
                for tb in group.get("toolboxes", []):
                    tag = tb.get("tag", "latest")
                    configured_images.append(f"{registry}:{tag}")
                    
        sel_image = self.query_one("#sel_image", SearchableSelect)
        images = sorted(set([tb['image'] for tb in installed] + configured_images))
        sel_image.set_options([(img, img) for img in images])
        if images:
            default_tag = get_default_toolbox(self.active_platform_id)
            if not default_tag and platform:
                default_tag = platform.get("default_toolbox_tag")
                
            selected = images[0]
            if default_tag:
                for img in images:
                    if default_tag in img:
                        selected = img
                        break
            sel_image.value = selected

    @on(SearchableSelect.Changed, "#sel_engine")
    def on_engine_selected(self, event: SearchableSelect.Changed):
        self.refresh_server_images()

    @on(SearchableSelect.Changed, "#sel_image")
    def on_image_selected(self, event: SearchableSelect.Changed):
        self.refresh_models()

    @on(SearchableSelect.Changed, "#sel_model")
    def on_model_selected(self, event: SearchableSelect.Changed):
        """When a model is selected, configure MTP zone, inference profile zone, and extra args."""
        selected_path = str(event.value) if event.value else ""
        model_config = get_model_config(selected_path)
        
        # Store current model config for use by other handlers
        self._current_model_config = model_config
        
        # Reset Extra Args to base immediately so all change handlers start with a clean state
        inp = self.query_one("#inp_custom_args", Input)
        base_arg = "--no-jinja" if (model_config and model_config.get("no_jinja")) else "--jinja"
        self._expected_custom_args = base_arg
        inp.value = base_arg
        
        mtp_zone = self.query_one("#mtp_zone", Vertical)
        profile_zone = self.query_one("#profile_zone", Vertical)
        
        # ── MTP Zone ────────────────────────────────────────────────────
        mtp_config = get_mtp_config(model_config)
        if mtp_config:
            mtp_zone.styles.display = "block"
            chk = self.query_one("#chk_mtp_enable", Checkbox)
            chk.value = True
            self.query_one("#inp_mtp_draft_n", Input).value = str(mtp_config.get("default_draft_n", 2))
            self.query_one("#inp_mtp_np", Input).value = str(mtp_config.get("default_np", 1))
        else:
            mtp_zone.styles.display = "none"
        
        # ── Inference Profile Zone ──────────────────────────────────────
        profiles = get_inference_profiles(model_config)
        if profiles:
            profile_zone.styles.display = "block"
            sel_profile = self.query_one("#sel_inference_profile", SearchableSelect)
            profile_names = list(profiles.keys())
            options = [(name, name) for name in profile_names] + [("Default (empty)", "Default (empty)"), ("Custom", "Custom")]
            sel_profile.set_options(options)
            # Auto-select first profile
            sel_profile.value = profile_names[0]
            desc = profiles[profile_names[0]].get("description", "")
            self.query_one("#lbl_profile_desc", Label).update(desc)
        else:
            profile_zone.styles.display = "none"
            self.query_one("#sel_inference_profile", SearchableSelect).set_options([])
            self.query_one("#lbl_profile_desc", Label).update("")
        
        self._rebuild_extra_args()

    @on(SearchableSelect.Changed, "#sel_inference_profile")
    def on_profile_changed(self, event: SearchableSelect.Changed):
        """When a profile is selected, update description and rebuild extra args."""
        profile_name = str(event.value) if event.value else ""
        model_config = getattr(self, "_current_model_config", None)
        profiles = get_inference_profiles(model_config)
        
        if profile_name == "Custom" or not profile_name:
            self.query_one("#lbl_profile_desc", Label).update("Manual configuration")
            return
        elif profile_name == "Default (empty)":
            self.query_one("#lbl_profile_desc", Label).update("No extra sampling parameters")
        elif profile_name in profiles:
            desc = profiles[profile_name].get("description", "")
            self.query_one("#lbl_profile_desc", Label).update(desc)
        
        self._rebuild_extra_args()

    @on(Checkbox.Changed, "#chk_kv_cache")
    def on_kv_cache_toggled(self, event: Checkbox.Changed):
        """Show/hide KV cache type selector when checkbox is toggled."""
        kv_row = self.query_one("#kv_cache_options_row", Horizontal)
        kv_row.styles.display = "block" if event.value else "none"

    @on(Checkbox.Changed, "#chk_benchmark_kv_cache")
    def on_benchmark_kv_cache_toggled(self, event: Checkbox.Changed):
        kv_row = self.query_one("#benchmark_kv_cache_row", Horizontal)
        kv_row.styles.display = "block" if event.value else "none"

    @on(Checkbox.Changed, "#chk_mtp_enable")
    def on_mtp_toggled(self, event: Checkbox.Changed):
        """When MTP is toggled, rebuild extra args."""
        self._rebuild_extra_args()

    @on(Input.Changed, "#inp_mtp_draft_n")
    def on_mtp_draft_changed(self, event: Input.Changed):
        """When MTP draft tokens change, rebuild extra args."""
        self._rebuild_extra_args()

    @on(Input.Changed, "#inp_mtp_np")
    def on_mtp_np_changed(self, event: Input.Changed):
        """When MTP parallel sequences change, rebuild extra args."""
        self._rebuild_extra_args()

    @on(Input.Changed, "#inp_custom_args")
    def on_custom_args_changed(self, event: Input.Changed):
        """When user manually edits Extra Args, switch profile to Custom."""
        if getattr(self, "_expected_custom_args", None) == event.value:
            return
        
        # User is manually editing — switch profile dropdown to "Custom"
        model_config = getattr(self, "_current_model_config", None)
        profiles = get_inference_profiles(model_config)
        if profiles:
            sel_profile = self.query_one("#sel_inference_profile", SearchableSelect)
            if sel_profile.value != "Custom":
                sel_profile.value = "Custom"
                self.query_one("#lbl_profile_desc", Label).update("Manual configuration")

    def _rebuild_extra_args(self):
        """Rebuild the Extra Args field from base + profile args + MTP args.
        
        Named profiles always rebuild from scratch (base_arg + profile + MTP)
        to prevent stale args from a previous model/profile leaking through.
        Custom mode preserves the user's manual edits and only touches MTP flags.
        """
        inp = self.query_one("#inp_custom_args", Input)
        model_config = getattr(self, "_current_model_config", None)
        base_arg = "--no-jinja" if (model_config and model_config.get("no_jinja")) else "--jinja"
        
        # ── Determine profile state ─────────────────────────────────────
        profile_args = ""
        is_custom = True
        profiles = get_inference_profiles(model_config)
        if profiles:
            sel_profile = self.query_one("#sel_inference_profile", SearchableSelect)
            profile_name = str(sel_profile.value) if sel_profile.value else ""
            if profile_name == "Default (empty)":
                is_custom = False
                profile_args = ""
            elif profile_name and profile_name != "Custom" and profile_name in profiles:
                is_custom = False
                profile_args = profiles[profile_name].get("args", "")
        
        # ── Build merged args ───────────────────────────────────────────
        if is_custom:
            # Custom mode: preserve current value, only touch MTP flags below
            merged = inp.value or base_arg
        else:
            # Named profile: always rebuild from scratch
            merged = base_arg
            if profile_args:
                merged = self._merge_args(merged, profile_args)
        
        # ── MTP args (always add/remove cleanly) ────────────────────────
        mtp_config = get_mtp_config(model_config)
        if mtp_config:
            # Strip any existing MTP flags first
            merged = self._remove_flags(merged, ["--spec-type", "--spec-draft-n-max", "-np"])
            chk = self.query_one("#chk_mtp_enable", Checkbox)
            if chk.value:
                draft_n = self.query_one("#inp_mtp_draft_n", Input).value or "2"
                np_val = self.query_one("#inp_mtp_np", Input).value or "1"
                mtp_args = f"--spec-type draft-mtp --spec-draft-n-max {draft_n} -np {np_val}"
                merged = self._merge_args(merged, mtp_args)
                
        self._expected_custom_args = merged
        inp.value = merged

    @staticmethod
    def _remove_flags(arg_str: str, flags_to_remove: list) -> str:
        """Remove specified flags and their values from the argument string."""
        import shlex
        if not arg_str:
            return ""
        try:
            tokens = shlex.split(arg_str)
        except Exception:
            return arg_str
            
        new_tokens = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in flags_to_remove:
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                    i += 2
                else:
                    i += 1
            else:
                new_tokens.append(token)
                i += 1
        return " ".join(shlex.quote(t) for t in new_tokens)

    @staticmethod
    def _merge_args(base: str, override: str) -> str:
        """Merge two argument strings. Override args replace matching flags in base, new ones are appended."""
        import shlex
        
        if not override:
            return base
        if not base:
            return override
            
        base_tokens = shlex.split(base)
        override_tokens = shlex.split(override)
        
        # Parse into ordered list of (flag, value_or_None) pairs
        def parse_flags(tokens):
            flags = []
            i = 0
            while i < len(tokens):
                token = tokens[i]
                if token.startswith("-"):
                    # Check if next token is a value (not a flag)
                    if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                        flags.append((token, tokens[i + 1]))
                        i += 2
                    else:
                        flags.append((token, None))
                        i += 1
                else:
                    # Standalone value (shouldn't normally happen but be safe)
                    flags.append((token, None))
                    i += 1
            return flags
        
        base_flags = parse_flags(base_tokens)
        override_flags = parse_flags(override_tokens)
        
        # Build result: start with base, override matching, append new
        override_map = {f: v for f, v in override_flags}
        override_keys_used = set()
        
        result = []
        for flag, val in base_flags:
            if flag in override_map:
                # Replace with override value
                result.append((flag, override_map[flag]))
                override_keys_used.add(flag)
            else:
                result.append((flag, val))
        
        # Append any override flags not already in base
        for flag, val in override_flags:
            if flag not in override_keys_used:
                result.append((flag, val))
        
        # Serialize back (shlex.quote each token to preserve special chars like JSON)
        parts = []
        for flag, val in result:
            parts.append(shlex.quote(flag))
            if val is not None:
                parts.append(shlex.quote(val))
        return " ".join(parts)

    def refresh_models(self):
        models = scan_local_models()
        self.current_models = models
        dt = self.query_one("#local_model_list", DataTable)
        dt.clear(columns=True)
        dt.add_columns("Filename")
        
        sel_model = self.query_one("#sel_model", SearchableSelect)
        model_opts = []
        
        try:
            sel_image = self.query_one("#sel_image", SearchableSelect)
            selected_image = sel_image.value or ""
        except Exception:
            selected_image = ""
            
        is_rocmfp4_image = "rocmfp4" in str(selected_image).lower()
        
        for m in models:
            dt.add_row(m["name"])
            
            is_rocmfp4_model = "rocmfp4" in m["name"].lower()
            if is_rocmfp4_image:
                if not is_rocmfp4_model:
                    continue
            else:
                if is_rocmfp4_model:
                    continue
                    
            model_opts.append((m["name"], m["path"]))
            
        sel_model.set_options(model_opts)
        if model_opts:
            previous_val = sel_model.value
            if previous_val in [path for _, path in model_opts]:
                sel_model.value = previous_val
            else:
                sel_model.value = model_opts[0][1]
        else:
            sel_model.value = ""

        self.refresh_benchmark_models()

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
            "btn_set_default": self._handle_set_default,
            "btn_save_benchmark_path": self._handle_save_benchmark_path,
            "btn_run_benchmarks": self._handle_run_benchmarks,
            "btn_benchmark_toggle_toolboxes": self._handle_toggle_benchmark_toolboxes,
            "btn_benchmark_toggle_models": self._handle_toggle_benchmark_models,
        }

        btn_id = event.button.id
        if btn_id in handlers:
            handlers[btn_id]()
        elif btn_id and btn_id.startswith("btn_toggle_dt_"):
            self._handle_toggle_select_all(btn_id)

    # ── Platform Switch Handler ─────────────────────────────────────

    def _handle_set_default(self):
        selected = self.get_selected_toolboxes()
        if not selected:
            self.notify("Please select a single toolbox to set as default.", severity="error")
            return
        if len(selected) > 1:
            self.notify("Please select exactly one toolbox to set as default.", severity="error")
            return
            
        tb = selected[0]
        image = tb.get("image", "")
        tag = image.split(":")[-1] if ":" in image else image
        
        if save_default_toolbox(self.active_platform_id, tag):
            self.notify(f"Set {tag} as default for platform {self.active_platform_id}.", severity="success", timeout=5)
            self.refresh_toolboxes()
            self.refresh_server_images()
        else:
            self.notify("Failed to save default toolbox configuration.", severity="error")


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
        self.notify("Toolbox list refreshed.", timeout=3)

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
                if is_remote_image_newer(remote_date, tb.get('created', '')):
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
                    if is_remote_image_newer(remote_date, tb.get('created', '')):
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
        engine = self.query_one("#sel_engine", SearchableSelect).value
        image = self.query_one("#sel_image", SearchableSelect).value
        model_path = self.query_one("#sel_model", SearchableSelect).value
        ctx = self.query_one("#inp_ctx", Input).value
        ngl = self.query_one("#inp_ngl", Input).value
        host = self.query_one("#inp_host", Input).value
        port = self.query_one("#inp_port", Input).value
        use_fa = self.query_one("#chk_fa", Checkbox).value
        use_no_mmap = self.query_one("#chk_no_mmap", Checkbox).value
        custom_args = self.query_one("#inp_custom_args", Input).value
        hip_devices = self.query_one("#inp_hip_devices", Input).value

        # Check compatibility
        is_rocmfp4_image = "rocmfp4" in str(image).lower()
        is_rocmfp4_model = model_path and "rocmfp4" in str(model_path).lower()
        
        if is_rocmfp4_image and not is_rocmfp4_model:
            self.notify("The rocmfp4 toolbox only supports rocmfp4 quantized models.", severity="error")
            return
            
        if is_rocmfp4_model and not is_rocmfp4_image:
            self.notify("rocmfp4 models require a rocmfp4 compatible toolbox.", severity="error")
            return
            
        if model_path:
            model_config = get_model_config(model_path)
            if model_config and "compatible_toolboxes" in model_config:
                allowed = model_config["compatible_toolboxes"]
                image_lower = str(image).lower()
                compatible = any(alt.lower() in image_lower for alt in allowed)
                if not compatible:
                    allowed_str = ", ".join(allowed)
                    self.notify(f"Model compatibility error: Only supported on {allowed_str}", severity="error")
                    return

        use_kv_cache = self.query_one("#chk_kv_cache", Checkbox).value
        kv_cache_type = str(self.query_one("#sel_kv_cache_type", SearchableSelect).value) if use_kv_cache else ""

        if engine and image and model_path and ctx.isdigit():
            ngl_val = int(ngl) if ngl.isdigit() else 999
            
            engine_args = None
            if hasattr(self, "toolboxes_dict"):
                for tb in self.toolboxes_dict.values():
                    if tb.get("image") == image:
                        engine_args = tb.get("args")
                        break

            cmd = build_server_cmd(
                engine, image, model_path, int(ctx), use_fa, use_no_mmap, 
                custom_args, host, port, ngl_val, 
                hip_devices=hip_devices, 
                platform_id=self.active_platform_id, 
                engine_args=engine_args,
                kv_cache_type=kv_cache_type
            )
            with self.suspend():
                if any(str(arg).startswith("/dev/infiniband") for arg in cmd):
                    print("\n🔎 InfiniBand/RDMA detected — enabling RDMA for native server mode.")
                print(f"\nStarting server with command:\n{shlex.join(cmd)}\n")
                print("Press Ctrl+C to stop the server and return to the UI.\n")
                
                import signal
                # Clean up any stale container first
                subprocess.run([engine, "rm", "-f", "llama-cockpit-server"], capture_output=True)
                
                old_handler = signal.signal(signal.SIGINT, signal.default_int_handler)
                try:
                    proc = subprocess.Popen(cmd)
                    proc.wait()
                except KeyboardInterrupt:
                    # Ignore further Ctrl+C during cleanup to prevent aborting the cleanup
                    signal.signal(signal.SIGINT, signal.SIG_IGN)
                    print("\nInterrupt received. Force stopping server (this may take a few seconds)...")
                    subprocess.run([engine, "rm", "-f", "llama-cockpit-server"], capture_output=True)
                    proc.kill()
                    proc.wait()
                finally:
                    signal.signal(signal.SIGINT, old_handler)

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

    @staticmethod
    def _toggle_all_benchmark_rows(dt: DataTable, selected: set):
        keys = [dt.get_cell_at((row, 1)) for row in range(dt.row_count)]
        all_selected = bool(keys) and all(key in selected for key in keys)
        for row, key in enumerate(keys):
            if all_selected:
                selected.discard(key)
                dt.update_cell_at((row, 0), "\\[ ]")
            else:
                selected.add(key)
                dt.update_cell_at((row, 0), "\\[x]")

    def _handle_toggle_benchmark_toolboxes(self):
        dt = self.query_one("#benchmark_toolbox_list", DataTable)
        self._toggle_all_benchmark_rows(dt, self.selected_benchmark_toolboxes)

    def _handle_toggle_benchmark_models(self):
        dt = self.query_one("#benchmark_model_list", DataTable)
        self._toggle_all_benchmark_rows(dt, self.selected_benchmark_models)

    def _handle_save_benchmark_path(self):
        path = self.query_one("#inp_benchmark_results_dir", Input).value.strip()
        if not path:
            self.notify("Enter a benchmark results folder.", severity="error")
            return
        if save_benchmark_results_dir(path):
            self.notify(f"Benchmark results folder updated to {path}.")
        else:
            self.notify("Failed to save benchmark results folder.", severity="error")

    def _handle_run_benchmarks(self):
        if not self.selected_benchmark_toolboxes:
            self.notify("Select at least one installed toolbox.", severity="warning")
            return
        if not self.selected_benchmark_models:
            self.notify("Select at least one model.", severity="warning")
            return

        results_path = self.query_one("#inp_benchmark_results_dir", Input).value.strip()
        if not results_path:
            self.notify("Enter a benchmark results folder.", severity="error")
            return

        def positive_input(widget_id: str, label: str) -> int:
            raw = self.query_one(widget_id, Input).value.strip()
            if not raw.isdigit() or int(raw) <= 0:
                raise ValueError(f"{label} must be a positive integer.")
            return int(raw)

        def nonnegative_input(widget_id: str, label: str) -> int:
            raw = self.query_one(widget_id, Input).value.strip()
            if not raw.isdigit():
                raise ValueError(f"{label} must be zero or a positive integer.")
            return int(raw)

        def optional_positive_input(widget_id: str, label: str) -> int | None:
            raw = self.query_one(widget_id, Input).value.strip()
            if not raw:
                return None
            if not raw.isdigit() or int(raw) <= 0:
                raise ValueError(f"{label} must be blank or a positive integer.")
            return int(raw)

        try:
            settings = BenchmarkSettings(
                max_context=positive_input(
                    "#inp_benchmark_max_context", "Maximum starting depth"
                ),
                context_step=positive_input(
                    "#inp_benchmark_context_step", "Starting depth step"
                ),
                prefill=positive_input(
                    "#inp_benchmark_prefill", "Prefill chunk"
                ),
                generation=positive_input(
                    "#inp_benchmark_generation", "Generation tokens"
                ),
                repetitions=positive_input(
                    "#inp_benchmark_repetitions", "Repetitions"
                ),
                delay=nonnegative_input(
                    "#inp_benchmark_cooldown", "Cooldown"
                ),
                flash_attention=self.query_one("#chk_benchmark_fa", Checkbox).value,
                use_mmap=not self.query_one("#chk_benchmark_no_mmap", Checkbox).value,
                kv_cache_type=(
                    str(self.query_one("#sel_benchmark_kv_cache_type", SearchableSelect).value)
                    if self.query_one("#chk_benchmark_kv_cache", Checkbox).value
                    else ""
                ),
                platform_id=self.active_platform_id,
                rocm_ubatch=optional_positive_input(
                    "#inp_benchmark_rocm_ubatch", "ROCm ubatch override"
                ),
                vulkan_ubatch=optional_positive_input(
                    "#inp_benchmark_vulkan_ubatch", "Vulkan ubatch override"
                ),
                extra_args=self.query_one("#inp_benchmark_extra_args", Input).value.strip(),
            )
            # Validate quoting in custom arguments before suspending the UI.
            if settings.extra_args:
                shlex.split(settings.extra_args)
            if settings.max_context < settings.context_step:
                raise ValueError(
                    "Maximum starting depth must be at least the starting depth step."
                )
            if settings.max_context % settings.context_step:
                raise ValueError(
                    "Maximum starting depth must be divisible by the starting depth step."
                )
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return

        if not save_benchmark_results_dir(results_path):
            self.notify("Could not create or save the benchmark results folder.", severity="error")
            return

        model_paths = [
            model["path"] for model in getattr(self, "current_models", [])
            if model["path"] in self.selected_benchmark_models
        ]
        toolbox_names = sorted(self.selected_benchmark_toolboxes)
        jobs = build_benchmark_jobs(
            get_os_toolbox_cmd(),
            toolbox_names,
            model_paths,
            get_benchmark_results_dir(),
            settings,
        )

        completed = failed = skipped = 0
        cancelled = False
        with self.suspend():
            print(f"\nRunning {len(jobs)} llama-bench job(s) sequentially.")
            print(f"Results folder: {get_benchmark_results_dir()}\n")
            for index, job in enumerate(jobs, start=1):
                print(f"[{index}/{len(jobs)}] {job.toolbox_name} | {os.path.basename(job.model_path)} | {job.series} curve")
                print(f"  Command: {shlex.join(job.command)}")
                print(f"  Log: {job.output_path}")
                try:
                    status, return_code = run_benchmark_job(job)
                except KeyboardInterrupt:
                    cancelled = True
                    print("\nBenchmark run cancelled by user.")
                    break
                except Exception as exc:
                    failed += 1
                    print(f"  FAILED: {exc}\n")
                    continue

                if status == "completed":
                    completed += 1
                    print("  OK\n")
                elif status == "skipped":
                    skipped += 1
                    print("  SKIPPED: non-empty log already exists\n")
                else:
                    failed += 1
                    print(f"  FAILED: llama-bench exited with code {return_code}\n")

                if index < len(jobs) and status != "skipped" and settings.delay:
                    print(f"  Cooling down for {settings.delay} seconds before the next run...\n")
                    time.sleep(settings.delay)

            print(
                f"Benchmark run finished: {completed} completed, "
                f"{failed} failed, {skipped} skipped"
                f"{' (cancelled)' if cancelled else ''}."
            )
            summary_path = get_benchmark_results_dir() / "curve_summary.csv"
            summary_rows = write_curve_summary(jobs, summary_path)
            print(f"Curve summary: {summary_path} ({summary_rows} rows)")
            try:
                input("\nPress Enter to return to the cockpit...")
            except EOFError:
                pass

        severity = "warning" if failed or cancelled else "information"
        self.notify(
            f"Benchmarks {'cancelled' if cancelled else 'finished'}: "
            f"{completed} completed, {failed} failed, {skipped} skipped.",
            severity=severity,
            timeout=8,
        )



    # ── Model Manager Handlers ────────────────────────────────────

    def _handle_scan_models(self):
        self.refresh_models()
        self.notify("Local models scanned.", timeout=3)

    def _handle_save_models_path(self):
        new_path = self.query_one("#inp_models_dir", Input).value
        if save_models_dir(new_path):
            self.notify(f"Models directory updated to {new_path}")
            self.refresh_models()
        else:
            self.notify("Failed to save models directory config.", severity="error")

    def _handle_download(self):
        repo = self.query_one("#sel_download_model", SearchableSelect).value
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
            print(f"\nRunning: HF_XET_HIGH_PERFORMANCE=1 {shlex.join(cmd)}")
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
