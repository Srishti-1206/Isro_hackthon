import json
import math
import queue
import random
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from main_orchestrator import run_phase6_simulation


customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")


APP_WIDTH = 1200
APP_HEIGHT = 700

COLOR_BG = "#0b1120"
COLOR_PANEL = "#111827"
COLOR_PANEL_ALT = "#172033"
COLOR_CYAN = "#22d3ee"
COLOR_RED = "#f43f5e"
COLOR_RED_DARK = "#4c0519"
COLOR_WHITE = "#f8fafc"
COLOR_MUTED = "#94a3b8"
COLOR_GREEN = "#34d399"

SCENARIO_OPTIONS = [
    "network_buffer_exhaustion",
    "bgp_route_flap",
    "memory_leak_decay",
]


class NocCopilotGui(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Net VigilAnz | Air-Gapped Predictive Copilot for Secure MPLS Operations")
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.minsize(1000, 620)
        self.configure(fg_color=COLOR_BG)

        self.result_queue = queue.Queue()
        self.worker_thread = None
        self.loading = False
        self.loading_tick = 0

        self.selected_scenario = tk.StringVar(value=SCENARIO_OPTIONS[0])

        self._configure_grid()
        self._build_sidebar()
        self._build_dashboard()
        self._draw_telemetry_graph(self.selected_scenario.get())

    def _configure_grid(self):
        self.grid_columnconfigure(0, minsize=300, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _build_sidebar(self):
        self.sidebar = customtkinter.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)

        title = customtkinter.CTkLabel(
            self.sidebar,
            text="Net VigilAnz",
            font=customtkinter.CTkFont(size=28, weight="bold"),
            text_color=COLOR_WHITE,
        )
        title.grid(row=0, column=0, padx=26, pady=(34, 6), sticky="w")

        subtitle = customtkinter.CTkLabel(
            self.sidebar,
            text="Air-Gapped Predictive Copilot for Secure MPLS Operations",
            font=customtkinter.CTkFont(size=14),
            text_color=COLOR_CYAN,
            wraplength=240,
            justify="left",
        )
        subtitle.grid(row=1, column=0, padx=26, pady=(0, 34), sticky="w")

        scenario_label = customtkinter.CTkLabel(
            self.sidebar,
            text="Failure mode",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            text_color=COLOR_MUTED,
        )
        scenario_label.grid(row=2, column=0, padx=26, pady=(0, 8), sticky="w")

        self.scenario_combo = customtkinter.CTkComboBox(
            self.sidebar,
            values=SCENARIO_OPTIONS,
            variable=self.selected_scenario,
            command=self._on_scenario_change,
            height=42,
            border_color=COLOR_CYAN,
            button_color=COLOR_CYAN,
            button_hover_color="#0891b2",
            dropdown_fg_color=COLOR_PANEL_ALT,
            dropdown_hover_color="#26364f",
            text_color=COLOR_WHITE,
            font=customtkinter.CTkFont(size=13),
        )
        self.scenario_combo.grid(row=3, column=0, padx=26, pady=(0, 28), sticky="ew")

        self.run_button = customtkinter.CTkButton(
            self.sidebar,
            text="Run Local AI Analysis",
            command=self._start_analysis,
            height=54,
            fg_color=COLOR_RED,
            hover_color="#be123c",
            text_color=COLOR_WHITE,
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        self.run_button.grid(row=4, column=0, padx=26, pady=(0, 20), sticky="ew")

        self.status_label = customtkinter.CTkLabel(
            self.sidebar,
            text="Status: idle",
            font=customtkinter.CTkFont(size=13),
            text_color=COLOR_MUTED,
            anchor="w",
        )
        self.status_label.grid(row=5, column=0, padx=26, pady=(0, 22), sticky="ew")

        self.sidebar.grid_rowconfigure(6, weight=1)

        footer = customtkinter.CTkLabel(
            self.sidebar,
            text="Local Ollama inference stays inside this host.",
            font=customtkinter.CTkFont(size=12),
            text_color=COLOR_MUTED,
            wraplength=240,
            justify="left",
        )
        footer.grid(row=7, column=0, padx=26, pady=(0, 28), sticky="sw")

    def _build_dashboard(self):
        self.dashboard = customtkinter.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.dashboard.grid(row=0, column=1, padx=18, pady=18, sticky="nsew")
        self.dashboard.grid_columnconfigure(0, weight=1)
        self.dashboard.grid_rowconfigure(0, weight=7)
        self.dashboard.grid_rowconfigure(1, weight=5)

        self.graph_frame = customtkinter.CTkFrame(
            self.dashboard,
            fg_color=COLOR_PANEL,
            border_color="#243044",
            border_width=1,
            corner_radius=8,
        )
        self.graph_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 14))
        self.graph_frame.grid_columnconfigure(0, weight=1)
        self.graph_frame.grid_rowconfigure(1, weight=1)

        graph_title = customtkinter.CTkLabel(
            self.graph_frame,
            text="Predictive Telemetry Trace",
            font=customtkinter.CTkFont(size=18, weight="bold"),
            text_color=COLOR_WHITE,
        )
        graph_title.grid(row=0, column=0, padx=18, pady=(14, 0), sticky="w")

        self.figure = Figure(figsize=(7, 3.6), dpi=100, facecolor=COLOR_PANEL)
        self.axis = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.graph_frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, padx=12, pady=12, sticky="nsew")

        self.data_frame = customtkinter.CTkFrame(
            self.dashboard,
            fg_color=COLOR_BG,
            corner_radius=0,
        )
        self.data_frame.grid(row=1, column=0, sticky="nsew")
        self.data_frame.grid_columnconfigure((0, 1), weight=1)
        self.data_frame.grid_rowconfigure(1, weight=1)

        self.issue_card, self.issue_value = self._build_metric_card(
            self.data_frame,
            row=0,
            column=0,
            title="Predicted Issue",
            value="Awaiting analysis",
            accent=COLOR_CYAN,
        )
        self.confidence_card, self.confidence_value = self._build_metric_card(
            self.data_frame,
            row=0,
            column=1,
            title="Confidence Score",
            value="--",
            accent=COLOR_GREEN,
        )

        self.impact_frame = customtkinter.CTkFrame(
            self.data_frame,
            fg_color=COLOR_RED_DARK,
            border_color=COLOR_RED,
            border_width=1,
            corner_radius=8,
        )
        self.impact_frame.grid(row=1, column=0, padx=(0, 7), pady=(14, 0), sticky="nsew")
        self.impact_frame.grid_columnconfigure(0, weight=1)

        impact_title = customtkinter.CTkLabel(
            self.impact_frame,
            text="Estimated Time to Impact",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            text_color=COLOR_MUTED,
        )
        impact_title.grid(row=0, column=0, padx=18, pady=(18, 4), sticky="w")

        self.impact_value = customtkinter.CTkLabel(
            self.impact_frame,
            text="--",
            font=customtkinter.CTkFont(size=34, weight="bold"),
            text_color=COLOR_WHITE,
        )
        self.impact_value.grid(row=1, column=0, padx=18, pady=(0, 10), sticky="w")

        self.scope_value = customtkinter.CTkLabel(
            self.impact_frame,
            text="No affected scope loaded.",
            font=customtkinter.CTkFont(size=13),
            text_color=COLOR_MUTED,
            justify="left",
            wraplength=360,
        )
        self.scope_value.grid(row=2, column=0, padx=18, pady=(0, 18), sticky="w")

        self.playbook_box = customtkinter.CTkTextbox(
            self.data_frame,
            fg_color=COLOR_PANEL,
            border_color="#243044",
            border_width=1,
            text_color=COLOR_WHITE,
            scrollbar_button_color=COLOR_CYAN,
            scrollbar_button_hover_color="#0891b2",
            corner_radius=8,
            font=customtkinter.CTkFont(size=13),
            wrap="word",
        )
        self.playbook_box.grid(row=1, column=1, padx=(7, 0), pady=(14, 0), sticky="nsew")
        self._set_playbook_text("Recommended action output will appear here.")

    def _build_metric_card(self, parent, row, column, title, value, accent):
        card = customtkinter.CTkFrame(
            parent,
            fg_color=COLOR_PANEL,
            border_color=accent,
            border_width=1,
            corner_radius=8,
        )
        padx = (0, 7) if column == 0 else (7, 0)
        card.grid(row=row, column=column, padx=padx, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        title_label = customtkinter.CTkLabel(
            card,
            text=title,
            font=customtkinter.CTkFont(size=13, weight="bold"),
            text_color=COLOR_MUTED,
        )
        title_label.grid(row=0, column=0, padx=18, pady=(14, 2), sticky="w")

        value_label = customtkinter.CTkLabel(
            card,
            text=value,
            font=customtkinter.CTkFont(size=22, weight="bold"),
            text_color=COLOR_WHITE,
            anchor="w",
        )
        value_label.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="ew")
        return card, value_label

    def _on_scenario_change(self, scenario_name):
        self._draw_telemetry_graph(scenario_name)
        self.status_label.configure(text="Status: scenario staged", text_color=COLOR_MUTED)

    def _start_analysis(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        scenario_name = self.selected_scenario.get()
        self._draw_telemetry_graph(scenario_name)
        self._set_loading_state(True)
        self._set_playbook_text("Waiting for local AI analysis...")

        self.worker_thread = threading.Thread(
            target=self._analysis_worker,
            args=(scenario_name,),
            daemon=True,
        )
        self.worker_thread.start()
        self.after(250, self._poll_result_queue)
        self.after(250, self._animate_loading)

    def _analysis_worker(self, scenario_name):
        try:
            result = run_phase6_simulation(scenario_name)
            if not isinstance(result, dict):
                raise TypeError(f"Expected dictionary response, got {type(result).__name__}")
            self.result_queue.put(("success", result))
        except Exception as exc:
            self.result_queue.put(("error", str(exc)))

    def _poll_result_queue(self):
        try:
            status, payload = self.result_queue.get_nowait()
        except queue.Empty:
            if self.loading:
                self.after(250, self._poll_result_queue)
            return

        self._set_loading_state(False)
        if status == "success":
            self._render_result(payload)
        else:
            self._render_error(payload)

    def _animate_loading(self):
        if not self.loading:
            return
        self.loading_tick = (self.loading_tick + 1) % 4
        dots = "." * self.loading_tick
        self.status_label.configure(
            text=f"Status: local inference running{dots}",
            text_color=COLOR_CYAN,
        )
        self.after(500, self._animate_loading)

    def _set_loading_state(self, is_loading):
        self.loading = is_loading
        if is_loading:
            self.run_button.configure(state="disabled", text="Analysis Running")
            self.scenario_combo.configure(state="disabled")
            self.issue_value.configure(text="Analyzing...")
            self.confidence_value.configure(text="--")
            self.impact_value.configure(text="--")
            self.scope_value.configure(text="Waiting for local model response.")
        else:
            self.run_button.configure(state="normal", text="Run Local AI Analysis")
            self.scenario_combo.configure(state="normal")
            self.status_label.configure(text="Status: idle", text_color=COLOR_MUTED)

    def _render_result(self, result):
        try:
            predicted_issue = self._safe_text(result.get("predicted_issue_type"), "Unknown issue")
            confidence = self._safe_float(result.get("confidence_score"))
            time_to_impact = self._safe_int(result.get("estimated_time_to_impact_seconds"))
            affected_devices = result.get("affected_devices") or []
            affected_services = result.get("affected_services") or []

            self.issue_value.configure(text=predicted_issue.replace("_", " "))
            self.confidence_value.configure(text=f"{confidence:.0%}" if confidence is not None else "--")
            self.impact_value.configure(text=self._format_duration(time_to_impact))
            self.scope_value.configure(
                text=self._format_scope(affected_devices, affected_services),
            )
            self._set_playbook_text(self._format_playbook(result))

            runtime = result.get("_runtime") or {}
            seconds = runtime.get("processing_seconds")
            status = f"Status: complete in {seconds}s" if seconds is not None else "Status: complete"
            self.status_label.configure(text=status, text_color=COLOR_GREEN)
        except Exception as exc:
            self._render_error(f"Unexpected response format: {exc}\n\nRaw response:\n{json.dumps(result, indent=2)}")

    def _render_error(self, error_text):
        self.issue_value.configure(text="Analysis error")
        self.confidence_value.configure(text="--")
        self.impact_value.configure(text="--")
        self.scope_value.configure(text="The backend returned an error.")
        self.status_label.configure(text="Status: error", text_color=COLOR_RED)
        self._set_playbook_text(error_text)
        messagebox.showerror("Net VigilAnz", error_text)

    def _set_playbook_text(self, text):
        self.playbook_box.configure(state="normal")
        self.playbook_box.delete("1.0", "end")
        self.playbook_box.insert("1.0", text)
        self.playbook_box.configure(state="disabled")

    def _format_playbook(self, result):
        action = result.get("recommended_action") or {}
        playbook = result.get("_playbook") or {}
        runtime = result.get("_runtime") or {}

        lines = [
            "RECOMMENDED ACTION",
            "",
            f"Playbook ID: {action.get('playbook_id', 'unknown')}",
            f"Action Type: {action.get('action_type', 'unknown')}",
            f"Human Approval Required: {action.get('requires_human_approval', True)}",
        ]

        if playbook:
            lines.extend([
                "",
                "Playbook Name:",
                playbook.get("name", "Unnamed playbook"),
                "",
                "Summary:",
                playbook.get("summary", "No summary available."),
            ])
            approved_actions = playbook.get("approved_actions") or []
            if approved_actions:
                lines.extend(["", "Approved Action Sequence:"])
                lines.extend(f"- {item}" for item in approved_actions)

        commands = action.get("commands") or []
        lines.extend(["", "Executable Commands:"])
        lines.extend(f"- {command}" for command in commands) if commands else lines.append("- none")

        warnings = runtime.get("parse_warnings") or []
        schema_errors = runtime.get("schema_errors") or []
        if warnings:
            lines.extend(["", "Parser Warnings:"])
            lines.extend(f"- {warning}" for warning in warnings)
        if schema_errors:
            lines.extend(["", "Schema Errors:"])
            lines.extend(f"- {error}" for error in schema_errors)

        return "\n".join(lines)

    def _format_scope(self, devices, services):
        device_text = ", ".join(str(item) for item in devices) if devices else "none"
        service_text = ", ".join(str(item) for item in services) if services else "none"
        return f"Affected devices: {device_text}\nAffected services: {service_text}"

    def _draw_telemetry_graph(self, scenario_name):
        x_values = list(range(1, 61))
        y_values, threshold, ylabel = self._build_scenario_series(scenario_name, x_values)

        self.axis.clear()
        self.figure.patch.set_facecolor(COLOR_PANEL)
        self.axis.set_facecolor("#0f172a")
        self.axis.plot(x_values, y_values, color=COLOR_CYAN, linewidth=2.5)
        self.axis.axhline(threshold, color=COLOR_RED, linewidth=1.8, linestyle="--")
        self.axis.fill_between(
            x_values,
            y_values,
            threshold,
            where=[value >= threshold for value in y_values],
            color=COLOR_RED,
            alpha=0.22,
        )
        self.axis.set_title(scenario_name.replace("_", " "), color=COLOR_WHITE, pad=12)
        self.axis.set_xlabel("Time window", color=COLOR_MUTED)
        self.axis.set_ylabel(ylabel, color=COLOR_MUTED)
        self.axis.tick_params(colors=COLOR_MUTED)
        self.axis.grid(color="#26364f", alpha=0.45)
        for spine in self.axis.spines.values():
            spine.set_color("#334155")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _build_scenario_series(self, scenario_name, x_values):
        random.seed(scenario_name)

        if scenario_name == "network_buffer_exhaustion":
            values = [min(120, 18 + 2.2 * math.exp(i / 14) + random.uniform(-1.8, 1.8)) for i in x_values]
            return values, 85, "Queue depth %"

        if scenario_name == "bgp_route_flap":
            values = []
            for i in x_values:
                base = 20 + 8 * math.sin(i / 1.8)
                bursts = 45 if i in range(20, 28) or i in range(42, 50) else 0
                values.append(base + bursts + random.uniform(-4, 4))
            return values, 55, "Route churn score"

        if scenario_name == "memory_leak_decay":
            values = [min(99, 42 + i * 0.78 + 4 * math.sin(i / 8) + random.uniform(-0.7, 0.7)) for i in x_values]
            return values, 90, "Memory used %"

        values = [35 + 8 * math.sin(i / 6) + random.uniform(-2, 2) for i in x_values]
        return values, 80, "Risk score"

    def _safe_text(self, value, fallback):
        if value is None:
            return fallback
        return str(value)

    def _safe_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _format_duration(self, seconds):
        if seconds is None:
            return "--"
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        remaining = seconds % 60
        if remaining:
            return f"{minutes}m {remaining}s"
        return f"{minutes}m"


if __name__ == "__main__":
    app = NocCopilotGui()
    app.mainloop()
