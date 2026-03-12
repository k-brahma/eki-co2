import csv
import os
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
import tkinter as tk
from dotenv import load_dotenv
from tkinter import filedialog, messagebox, ttk


class CO2App:
    def __init__(self, root: tk.Tk) -> None:
        load_dotenv()
        self.api_key = os.getenv("EKISPERT_API_KEY", "").strip()
        self.train_api_url = (
            "https://api.ekispert.jp/v1/json/search/course/plain"
            "?key={API_KEY}&from={station_from}&to={station_to}"
        )
        self.geocode_api_url = "https://msearch.gsi.go.jp/address-search/AddressSearch?q={query}"
        self.distance_api_url = "https://vldb.gsi.go.jp/sokuchi/surveycalc/surveycalc/bl2st_calc.pl"

        self.root = root
        self.root.title("通勤経路 CO2 チェッカー")
        self.root.geometry("1160x1000")
        self.root.minsize(980, 780)

        self.data_dir = Path("data")
        self.results_dir = Path("results")
        self.data_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)

        self.csv_path: Path | None = None
        self.rows: list[dict[str, str]] = []
        self.fieldnames: list[str] = ["mode", "from", "to", "co2"]
        self.mode_key = "mode"
        self.from_key = "from"
        self.to_key = "to"
        self.co2_key = "co2"

        self.path_var = tk.StringVar(value="CSV未選択")
        self.status_var = tk.StringVar(value="CSVを開いてください。")
        self.summary_var = tk.StringVar(value="0件")
        self.mode_var = tk.StringVar(value="電車")
        self.from_var = tk.StringVar()
        self.to_var = tk.StringVar()
        self.co2_var = tk.StringVar()
        self.car_co2_per_km_var = tk.StringVar(value="120")
        self.sort_state: dict[str, bool] = {}

        self._configure_style()
        self._build_ui()
        self._load_initial_rows()

    def _configure_style(self) -> None:
        self.root.configure(bg="#f4efe7")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f4efe7")
        style.configure("Card.TFrame", background="#fffaf3")
        style.configure(
            "Title.TLabel",
            background="#f4efe7",
            foreground="#1f2937",
            font=("Yu Gothic UI", 21, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background="#f4efe7",
            foreground="#4b5563",
            font=("Yu Gothic UI", 10),
        )
        style.configure(
            "Field.TLabel",
            background="#fffaf3",
            foreground="#374151",
            font=("Yu Gothic UI", 10, "bold"),
        )
        style.configure(
            "Primary.TButton",
            font=("Yu Gothic UI", 10, "bold"),
            foreground="#fffaf3",
            background="#0f766e",
            padding=(14, 8),
            borderwidth=0,
        )
        style.map("Primary.TButton", background=[("active", "#115e59"), ("disabled", "#94a3b8")])
        style.configure(
            "Secondary.TButton",
            font=("Yu Gothic UI", 10),
            foreground="#1f2937",
            background="#efe3d3",
            padding=(12, 8),
            borderwidth=0,
        )
        style.map("Secondary.TButton", background=[("active", "#e6d5bf")])
        style.configure(
            "Treeview",
            font=("Yu Gothic UI", 10),
            rowheight=34,
            background="#fffdf9",
            fieldbackground="#fffdf9",
            foreground="#111827",
            bordercolor="#d8c7b0",
            lightcolor="#d8c7b0",
            darkcolor="#d8c7b0",
        )
        style.configure(
            "Treeview.Heading",
            font=("Yu Gothic UI", 10, "bold"),
            background="#dcc9af",
            foreground="#1f2937",
            relief="raised",
            borderwidth=1,
            lightcolor="#8b7355",
            darkcolor="#8b7355",
            bordercolor="#8b7355",
            padding=(10, 8),
        )
        style.map("Treeview.Heading", background=[("active", "#d2bfa4")])
        style.map("Treeview", background=[("selected", "#c7e7df")], foreground=[("selected", "#111827")])

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=20)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="App.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="通勤経路 CO2 チェッカー", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="CSVの移動手段が「電車」なら駅すぱあと、「車」なら直線距離 × g/km で計算します。",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        toolbar = ttk.Frame(outer, style="Card.TFrame", padding=16)
        toolbar.pack(fill="x", pady=(18, 14))

        buttons = ttk.Frame(toolbar, style="Card.TFrame")
        buttons.pack(fill="x")
        ttk.Button(buttons, text="CSVを開く", style="Primary.TButton", command=self.open_csv).pack(side="left")
        ttk.Button(buttons, text="全件を計算", style="Primary.TButton", command=self.calculate_all).pack(
            side="left", padx=(10, 0)
        )
        ttk.Button(buttons, text="保存", style="Secondary.TButton", command=self.save_csv).pack(
            side="left", padx=(10, 0)
        )
        car_settings = ttk.Frame(buttons, style="Card.TFrame")
        car_settings.pack(side="right")
        ttk.Label(car_settings, text="車 g/km", style="Field.TLabel").pack(side="left", padx=(0, 8))
        self._make_compact_entry(car_settings, self.car_co2_per_km_var, width=8)

        meta = ttk.Frame(toolbar, style="Card.TFrame")
        meta.pack(fill="x", pady=(14, 0))
        ttk.Label(meta, textvariable=self.path_var, style="Body.TLabel").pack(side="left")
        ttk.Label(meta, textvariable=self.summary_var, style="Body.TLabel").pack(side="right")

        content = ttk.Frame(outer, style="App.TFrame")
        content.pack(fill="both", expand=True)

        table_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        table_card.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_card,
            columns=("mode", "from", "to", "co2"),
            show="headings",
            selectmode="extended",
        )
        self.tree.heading("mode", text="移動手段", command=lambda: self.sort_by_column("mode"))
        self.tree.heading("from", text="出発地", command=lambda: self.sort_by_column("from"))
        self.tree.heading("to", text="到着地", command=lambda: self.sort_by_column("to"))
        self.tree.heading("co2", text="CO2(g)", command=lambda: self.sort_by_column("co2"))
        self.tree.column("mode", width=120, anchor="center", stretch=False)
        self.tree.column("from", width=310, anchor="w", stretch=True)
        self.tree.column("to", width=310, anchor="w", stretch=True)
        self.tree.column("co2", width=140, anchor="center", stretch=False)
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_row)

        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        form_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        form_card.pack(fill="x", pady=(14, 0))

        ttk.Label(
            form_card,
            text="選択行の編集",
            style="Field.TLabel",
        ).pack(anchor="w")

        fields = ttk.Frame(form_card, style="Card.TFrame")
        fields.pack(fill="x", pady=(10, 0))
        self._make_combobox_field(fields, "移動手段", self.mode_var, ("電車", "車"), 0)
        self._make_field(fields, "出発地", self.from_var, 1)
        self._make_field(fields, "到着地", self.to_var, 2)
        self._make_field(fields, "CO2(g)", self.co2_var, 3, readonly=True)

        actions = ttk.Frame(form_card, style="Card.TFrame")
        actions.pack(fill="x", pady=(14, 0))
        ttk.Button(actions, text="行を追加", style="Primary.TButton", command=self.add_row).pack(side="left")
        ttk.Button(actions, text="選択行を更新", style="Secondary.TButton", command=self.update_selected_row).pack(
            side="left", padx=(10, 0)
        )
        ttk.Button(actions, text="選択行を削除", style="Secondary.TButton", command=self.delete_selected_rows).pack(
            side="left", padx=(10, 0)
        )

        footer = ttk.Frame(outer, style="App.TFrame")
        footer.pack(fill="x", pady=(14, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Body.TLabel").pack(anchor="w")
        ttk.Label(
            footer,
            text="列幅は見出しの境界線をドラッグして調整できます。",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(4, 0))

    def _normalize_mode(self, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"train", "電車"}:
            return "電車"
        if normalized in {"car", "車"}:
            return "車"
        return "電車"

    def _format_log_line(
        self,
        current: int,
        total: int,
        mode: str,
        api_label: str,
        start: str,
        end: str,
        result: str,
    ) -> str:
        start_label = self._fit_text(start, 20)
        end_label = self._fit_text(end, 20)
        mode_label = "[電車]" if mode == "電車" else "[ 車 ]"
        return (
            f"{current:>2}/{total:<2} | "
            f"{mode_label} | "
            f"{self._pad_display(api_label, 12)} | "
            f"{self._pad_display(start_label, 20)} | "
            f"{self._pad_display(end_label, 20)} | "
            f"{result:>6}"
        )

    def _display_width(self, value: str) -> int:
        width = 0
        for char in value:
            width += 2 if unicodedata.east_asian_width(char) in {"F", "W", "A"} else 1
        return width

    def _fit_text(self, value: str, width: int) -> str:
        if self._display_width(value) <= width:
            return value

        result = []
        current_width = 0
        for char in value:
            char_width = 2 if unicodedata.east_asian_width(char) in {"F", "W", "A"} else 1
            if current_width + char_width > width - 3:
                break
            result.append(char)
            current_width += char_width
        return "".join(result) + "..."

    def _pad_display(self, value: str, width: int) -> str:
        padding = max(0, width - self._display_width(value))
        return value + (" " * padding)

    def sort_by_column(self, column: str) -> None:
        reverse = self.sort_state.get(column, False)

        def sort_key(row: dict[str, str]) -> tuple[int, object]:
            if column == "mode":
                value = self._normalize_mode(row.get(self.mode_key, "電車"))
                order = {"電車": 0, "車": 1}
                return (0, order.get(value, 99))
            if column == "co2":
                value = row.get(self.co2_key, "").strip()
                return (1, float("inf")) if value == "" else (0, int(value))
            key_name = self.from_key if column == "from" else self.to_key
            return (0, row.get(key_name, ""))

        self.rows.sort(key=sort_key, reverse=reverse)
        self.sort_state[column] = not reverse
        self._refresh_tree()
        direction = "降順" if reverse else "昇順"
        self.status_var.set(f"{self._column_label(column)} で{direction}ソートしました。")

    def _column_label(self, column: str) -> str:
        labels = {
            "mode": "移動手段",
            "from": "出発地",
            "to": "到着地",
            "co2": "CO2(g)",
        }
        return labels.get(column, column)

    def _make_field(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        column: int,
        readonly: bool = False,
    ) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=0, column=column, sticky="ew", padx=(0, 12))
        parent.columnconfigure(column, weight=1)

        ttk.Label(frame, text=label, style="Field.TLabel").pack(anchor="w")
        entry_box = tk.Frame(
            frame,
            bg="#8b7355",
            highlightbackground="#8b7355",
            highlightcolor="#8b7355",
            highlightthickness=1,
            bd=0,
        )
        entry_box.pack(fill="x", pady=(8, 0))
        entry = tk.Entry(
            entry_box,
            textvariable=variable,
            font=("Yu Gothic UI", 11),
            relief="flat",
            bg="#fffdf9",
            fg="#111827",
            disabledbackground="#f3f4f6",
            disabledforeground="#6b7280",
            insertbackground="#111827",
            bd=0,
        )
        if readonly:
            entry.configure(state="readonly")
        entry.pack(fill="x", padx=1, pady=1, ipady=8)

    def _make_combobox_field(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
        column: int,
    ) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=0, column=column, sticky="ew", padx=(0, 12))
        parent.columnconfigure(column, weight=1)

        ttk.Label(frame, text=label, style="Field.TLabel").pack(anchor="w")
        entry_box = tk.Frame(
            frame,
            bg="#8b7355",
            highlightbackground="#8b7355",
            highlightcolor="#8b7355",
            highlightthickness=1,
            bd=0,
        )
        entry_box.pack(fill="x", pady=(8, 0))
        combo = ttk.Combobox(entry_box, textvariable=variable, values=values, state="readonly", font=("Yu Gothic UI", 11))
        combo.pack(fill="x", padx=1, pady=1, ipady=4)

    def _make_compact_entry(self, parent: ttk.Frame, variable: tk.StringVar, width: int) -> None:
        entry_box = tk.Frame(
            parent,
            bg="#8b7355",
            highlightbackground="#8b7355",
            highlightcolor="#8b7355",
            highlightthickness=1,
            bd=0,
        )
        entry_box.pack(side="left")
        entry = tk.Entry(
            entry_box,
            textvariable=variable,
            width=width,
            justify="right",
            font=("Yu Gothic UI", 10),
            relief="flat",
            bg="#fffdf9",
            fg="#111827",
            insertbackground="#111827",
            bd=0,
        )
        entry.pack(padx=1, pady=1, ipady=6)

    def _load_blank_rows(self) -> None:
        self.rows = [
            {"mode": "電車", "from": "有楽町", "to": "新橋", "co2": ""},
            {"mode": "電車", "from": "新橋", "to": "品川", "co2": ""},
            {"mode": "車", "from": "東京都千代田区丸の内1-1", "to": "東京都千代田区有楽町2-9-17", "co2": ""},
        ]
        self.fieldnames = ["mode", "from", "to", "co2"]
        self.mode_key = "mode"
        self.from_key = "from"
        self.to_key = "to"
        self.co2_key = "co2"
        self._refresh_tree()
        self.path_var.set("未保存の新規データ")
        self.status_var.set("サンプル行を表示しています。")

    def _load_initial_rows(self) -> None:
        sample_path = self.data_dir / "sample.csv"
        if sample_path.exists() and self._read_csv(sample_path):
            self.csv_path = sample_path
            self.path_var.set(str(sample_path))
            self.status_var.set("`data/sample.csv` を読み込みました。")
            return
        self._load_blank_rows()

    def _refresh_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, row in enumerate(self.rows):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    row.get(self.mode_key, "電車"),
                    row.get(self.from_key, ""),
                    row.get(self.to_key, ""),
                    row.get(self.co2_key, ""),
                ),
            )
        self.summary_var.set(f"{len(self.rows)}件")

    def _detect_keys(self, fieldnames: list[str]) -> None:
        lowered = {name.lower(): name for name in fieldnames}
        self.mode_key = lowered.get("mode") or lowered.get("移動手段") or "mode"
        self.from_key = lowered.get("from") or lowered.get("station_from") or lowered.get("出発駅") or fieldnames[0]
        self.to_key = (
            lowered.get("to")
            or lowered.get("station_to")
            or lowered.get("到着駅")
            or fieldnames[min(1, len(fieldnames) - 1)]
        )
        self.co2_key = lowered.get("co2") or lowered.get("co2(g)") or lowered.get("排出量") or "co2"
        self.fieldnames = fieldnames[:]
        for key in (self.mode_key, self.from_key, self.to_key, self.co2_key):
            if key not in self.fieldnames:
                self.fieldnames.append(key)

    def _read_csv(self, path: str | Path) -> bool:
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                if not reader.fieldnames:
                    raise ValueError("ヘッダー行がありません。")
                self._detect_keys(reader.fieldnames)
                self.rows = []
                for row in reader:
                    normalized = {key: (value or "").strip() for key, value in row.items() if key}
                    normalized[self.mode_key] = self._normalize_mode(normalized.get(self.mode_key, "電車"))
                    normalized.setdefault(self.from_key, "")
                    normalized.setdefault(self.to_key, "")
                    normalized.setdefault(self.co2_key, "")
                    self.rows.append(normalized)
        except Exception as exc:
            messagebox.showerror("CSV読み込みエラー", str(exc))
            return False

        self._refresh_tree()
        return True

    def open_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="CSVを選択",
            initialdir=str(self.data_dir),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        if not self._read_csv(path):
            return

        self.csv_path = Path(path)
        self.path_var.set(str(self.csv_path))
        self.status_var.set("CSVを読み込みました。必要に応じて行編集または計算を実行してください。")

    def add_row(self) -> None:
        start = self.from_var.get().strip()
        end = self.to_var.get().strip()
        if not start or not end:
            messagebox.showwarning("入力不足", "出発地と到着地を入力してください。")
            return

        row = {name: "" for name in self.fieldnames}
        row[self.mode_key] = self.mode_var.get().strip() or "電車"
        row[self.from_key] = start
        row[self.to_key] = end
        row[self.co2_key] = ""
        self.rows.append(row)
        self._refresh_tree()
        self.status_var.set("行を追加しました。")

    def update_selected_row(self) -> None:
        selected = self.tree.selection()
        if len(selected) != 1:
            messagebox.showwarning("選択エラー", "更新する行を1件だけ選択してください。")
            return

        index = int(selected[0])
        start = self.from_var.get().strip()
        end = self.to_var.get().strip()
        if not start or not end:
            messagebox.showwarning("入力不足", "出発地と到着地を入力してください。")
            return

        self.rows[index][self.mode_key] = self.mode_var.get().strip() or "電車"
        self.rows[index][self.from_key] = start
        self.rows[index][self.to_key] = end
        self._refresh_tree()
        self.tree.selection_set(str(index))
        self.status_var.set("選択行を更新しました。")

    def delete_selected_rows(self) -> None:
        selected = sorted((int(item) for item in self.tree.selection()), reverse=True)
        if not selected:
            messagebox.showwarning("選択エラー", "削除する行を選択してください。")
            return

        for index in selected:
            del self.rows[index]
        self._refresh_tree()
        self.mode_var.set("電車")
        self.from_var.set("")
        self.to_var.set("")
        self.co2_var.set("")
        self.status_var.set(f"{len(selected)}件削除しました。")

    def on_select_row(self, _event: object) -> None:
        selected = self.tree.selection()
        if len(selected) != 1:
            return

        row = self.rows[int(selected[0])]
        self.mode_var.set(row.get(self.mode_key, "電車"))
        self.from_var.set(row.get(self.from_key, ""))
        self.to_var.set(row.get(self.to_key, ""))
        self.co2_var.set(row.get(self.co2_key, ""))

    def calculate_all(self) -> None:
        if not self.rows:
            messagebox.showwarning("データなし", "先にCSVを読み込むか行を追加してください。")
            return
        self._calculate_rows(list(range(len(self.rows))))

    def _calculate_rows(self, indexes: list[int]) -> None:
        if not self.api_key and any(self.rows[index].get(self.mode_key, "電車") == "電車" for index in indexes):
            messagebox.showerror("APIキー未設定", "`.env` に `EKISPERT_API_KEY` を設定してください。")
            return

        try:
            car_co2_per_km = float(self.car_co2_per_km_var.get())
        except ValueError:
            messagebox.showerror("入力エラー", "車のCO2排出量(g/km)には数値を入力してください。")
            return

        self.status_var.set(f"{len(indexes)}件のCO2排出量を取得しています。")
        self.root.update_idletasks()
        session = requests.Session()
        completed = 0

        for index in indexes:
            mode = self._normalize_mode(self.rows[index].get(self.mode_key, "電車"))
            start = self.rows[index].get(self.from_key, "").strip()
            end = self.rows[index].get(self.to_key, "").strip()
            if not start or not end:
                message = f"{index + 1}行目: 出発地または到着地が空です。"
                print(message)
                self.status_var.set(message)
                self.root.update_idletasks()
                continue

            try:
                if mode == "車":
                    co2_value = self._calculate_car_co2(session, start, end, car_co2_per_km)
                    api_label = "距離測定"
                else:
                    co2_value = self._calculate_train_co2(session, start, end)
                    api_label = "駅すぱあと"

                self.rows[index][self.mode_key] = mode
                self.rows[index][self.co2_key] = co2_value
                self.tree.item(
                    str(index),
                    values=(mode, start, end, co2_value),
                )
                if len(self.tree.selection()) == 1 and self.tree.selection()[0] == str(index):
                    self.mode_var.set(mode)
                    self.co2_var.set(co2_value)

                completed += 1
                message = self._format_log_line(
                    completed,
                    len(indexes),
                    mode,
                    api_label,
                    start,
                    end,
                    f"{co2_value}g",
                )
                print(message)
                self.status_var.set(message)
                self.root.update_idletasks()
            except Exception as exc:
                api_label = "距離測定" if mode == "車" else "駅すぱあと"
                message = self._format_log_line(
                    index + 1,
                    len(indexes),
                    mode,
                    api_label,
                    start,
                    end,
                    f"ERROR: {exc}",
                )
                print(message)
                self.status_var.set(message)
                self.root.update_idletasks()

        final_message = f"計算完了: {completed}/{len(indexes)}件を更新しました。"
        print(final_message)
        self.status_var.set(final_message)

    def _calculate_train_co2(self, session: requests.Session, start: str, end: str) -> str:
        url = self.train_api_url.format(
            API_KEY=self.api_key,
            station_from=quote(start),
            station_to=quote(end),
        )
        response = session.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        course = data["ResultSet"]["Course"][0]
        return str(int(float(course["Route"]["exhaustCO2"])))

    def _calculate_car_co2(self, session: requests.Session, start: str, end: str, car_co2_per_km: float) -> str:
        start_point = self._geocode(session, start)
        end_point = self._geocode(session, end)
        params = {
            "outputType": "json",
            "ellipsoid": "GRS80",
            "latitude1": start_point["lat"],
            "longitude1": start_point["lon"],
            "latitude2": end_point["lat"],
            "longitude2": end_point["lon"],
        }
        response = session.get(self.distance_api_url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        distance_m = float(data["OutputData"]["geoLength"])
        co2 = int((distance_m / 1000.0) * car_co2_per_km)
        return str(co2)

    def _geocode(self, session: requests.Session, address: str) -> dict[str, float]:
        response = session.get(self.geocode_api_url.format(query=quote(address)), timeout=20)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise ValueError(f"位置を取得できません: {address}")
        coordinates = data[0]["geometry"]["coordinates"]
        return {"lon": float(coordinates[0]), "lat": float(coordinates[1])}

    def save_csv(self) -> None:
        base_name = "co2_results"
        if self.csv_path is not None:
            base_name = self.csv_path.stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = self.results_dir / f"{base_name}_{timestamp}.csv"

        try:
            with open(target, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writeheader()
                for row in self.rows:
                    writer.writerow({name: row.get(name, "") for name in self.fieldnames})
        except Exception as exc:
            messagebox.showerror("保存エラー", str(exc))
            return

        self.csv_path = target
        self.path_var.set(str(self.csv_path))
        message = f"CSVを保存しました: {target}"
        print(message)
        self.status_var.set(message)
        messagebox.showinfo("保存完了", message)


def main() -> None:
    root = tk.Tk()
    CO2App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
