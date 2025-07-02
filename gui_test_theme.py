import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pandas as pd
from tabulate import tabulate
import ttkbootstrap as tb
from ttkbootstrap.constants import LEFT, INFO
from ttkbootstrap.tooltip import ToolTip

# Main application class for DataScope
class DataScopeApp:
    def __init__(self, root):
        self.root = root # Main window
        self.df = None  # Loaded DataFrame
        self.data_loaded = False # Flag to check if data is loaded
        self.max_cell_width = 40 # Maximum width for cell content in output
        self.search_var = tk.StringVar() # Search input variable
        self.search_column_var = tk.StringVar(value="All Columns") # Search column variable
        self.search_output_cache = None # Cache for search results
        self.analysis_output_cache = None # Cache for analysis results
        self.case_sensitive = tk.BooleanVar(value=False) # Case sensitivity for search
        self.whole_word = tk.BooleanVar(value=False) # Whole word search option
        self.match_indices = [] # List of match indices for search results
        self.current_match = -1 # Current match index for navigation
        self.setup_ui()  # Build the UI

    # Print output and show error dialog if needed
    def write_output(self, message):
        print(message)
        if "[Error]" in message or "[Display Error]" in message:
            messagebox.showerror("Error", message)

    # Check if data is loaded before running actions
    def check_data_loaded(self):
        if not self.data_loaded:
            self.write_output("[Error] Load data first before testing.")
            return False
        return True

    # Build the main UI layout and widgets
    def setup_ui(self):
        self.root.title("DataScope Day-0 Interface")
        style = tb.Style(theme="litera")
        ttk = tb.ttk

        # Title label
        ttk.Label(self.root, text="DataScope Project - Day-0 Interface",
                  font=("Arial", 16, "bold")).pack(pady=10)

        # --- Top Button Frame ---
        btn_frame = tb.Frame(self.root)
        btn_frame.pack(pady=10, padx=10, fill="x")

        load_btn = tb.Button(btn_frame, text="Load Data File", bootstyle=INFO, command=self.load_data) 
        load_btn.pack(side=LEFT, padx=(0, 5))

        self.convert_btn = tb.Button(btn_frame, text="Convert File", bootstyle=INFO, command=self.convert_file)
        self.convert_btn.pack(side=LEFT, padx=5)

        self.run_btn = tb.Button(btn_frame, text="Run Analysis", bootstyle=INFO, command=self.update_analysis_display,
                                 state="disabled")
        self.run_btn.pack(side=LEFT, padx=5)

        self.toggle_theme_btn = tb.Button(btn_frame, text="Toggle Theme", bootstyle=INFO, command=self.toggle_theme)
        self.toggle_theme_btn.pack(side=LEFT, padx=5)

        # --- Search Section ---
        search_frame = tb.Frame(self.root)
        search_frame.pack(padx=10, pady=(5, 5), fill="x")

        ttk.Label(search_frame, text="Search:").pack(side=LEFT)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=LEFT, padx=(5, 10))

        # Case sensitivity and whole word checkboxes
        case_cb = tb.Checkbutton(search_frame, text="Case Sensitive", variable=self.case_sensitive, bootstyle="round-toggle")
        case_cb.pack(side=LEFT, padx=(0, 5))
        word_cb = tb.Checkbutton(search_frame, text="Whole Word", variable=self.whole_word, bootstyle="round-toggle")
        word_cb.pack(side=LEFT, padx=(0, 10))

        ttk.Label(search_frame, text="in").pack(side=LEFT)
        self.search_column_dropdown = ttk.Combobox(search_frame, textvariable=self.search_column_var, state="readonly", width=20)
        self.search_column_dropdown.pack(side=LEFT, padx=(5, 10))
        self.search_column_dropdown['values'] = ["All Columns"]

        search_button = tb.Button(search_frame, text="Search", bootstyle=INFO, command=self.search_data)
        search_button.pack(side=LEFT, padx=(0, 5))

        # Navigation buttons for search results
        self.prev_btn = tb.Button(search_frame, text="Previous", bootstyle=INFO, command=self.goto_prev_match, state="normal")
        self.prev_btn.pack(side=LEFT, padx=(0, 2))
        self.next_btn = tb.Button(search_frame, text="Next", bootstyle=INFO, command=self.goto_next_match, state="normal")
        self.next_btn.pack(side=LEFT, padx=(0, 10))

        reset_button = tb.Button(search_frame, text="Reset", bootstyle=INFO, command=self.clear_output)
        reset_button.pack(side=LEFT, padx=(0, 5))

        self.match_count_label = ttk.Label(search_frame, text="Matches: 0")
        self.match_count_label.pack(side=LEFT, padx=(5, 0))
       
        # --- Analysis Section ---
        selection_frame = tb.Frame(self.root)
        selection_frame.pack(padx=10, pady=(10, 5), fill="x")
        selection_frame.columnconfigure(1, weight=1)
        selection_frame.columnconfigure(3, weight=1)

        ttk.Label(selection_frame, text="Select Analysis Type:").grid(row=0, column=0, sticky="w")
        analysis_options = ["Data Preview", "Missing Values", "Duplicate Detection", "Placeholder Detection", "Special Character Analysis"]
        self.analysis_dropdown = ttk.Combobox(selection_frame, values=analysis_options, state="readonly")
        self.analysis_dropdown.grid(row=0, column=1, padx=5, sticky="ew")
        self.analysis_dropdown.set("Data Preview")

        ttk.Label(selection_frame, text="Select Column:").grid(row=0, column=2, sticky="w", padx=(15, 0))
        self.column_dropdown = ttk.Combobox(selection_frame, values=["All Columns"], state="readonly")
        self.column_dropdown.grid(row=0, column=3, padx=5, sticky="ew")
        self.column_dropdown.set("All Columns")

        ttk.Label(selection_frame, text="Rows to show:").grid(row=0, column=4, sticky="w", padx=(15, 0))
        self.row_entry = tk.Spinbox(selection_frame, from_=1, to=1000, width=5)
        self.row_entry.grid(row=0, column=5, padx=5)
        self.row_entry.delete(0, "end")
        self.row_entry.insert(0, "10")

        ttk.Label(selection_frame, text="Sort Order:").grid(row=0, column=6, sticky="w", padx=(15, 0))
        self.sort_order_dropdown = ttk.Combobox(selection_frame, values=["Ascending", "Descending"], state="readonly", width=10)
        self.sort_order_dropdown.grid(row=0, column=7, padx=5)
        self.sort_order_dropdown.set("Ascending")

        ttk.Label(selection_frame, text="Encoding:").grid(row=0, column=8, sticky="w", padx=(15, 0))
        self.encoding_dropdown = ttk.Combobox(
            selection_frame,
            values=["Auto (Recommended)", "utf-8", "utf-8-sig", "latin-1", "ISO-8859-1", "cp1252", "utf-16"],
            state="readonly", width=18
        )
        self.encoding_dropdown.grid(row=0, column=9, padx=5)
        self.encoding_dropdown.set("Auto (Recommended)")

        ttk.Label(selection_frame, text="Delimiter:").grid(row=0, column=10, sticky="w", padx=(15, 0))
        self.delimiter_dropdown = ttk.Combobox(
            selection_frame,
            values=["Auto (Recommended)", "Comma (,)", "Tab (\\t)", "Semicolon (;)", "Pipe (|)"],
            state="readonly", width=18
        )
        self.delimiter_dropdown.grid(row=0, column=11, padx=5)
        self.delimiter_dropdown.set("Auto (Recommended)")

        # File and status labels
        self.file_label = ttk.Label(self.root, text="No file loaded", foreground="gray")
        self.file_label.pack(pady=(5, 0))

        self.shape_label = ttk.Label(self.root, text="", foreground="cyan")
        self.shape_label.pack()

        # Output display area
        output_frame = tb.Frame(self.root)
        output_frame.pack(padx=15, pady=15, fill="both", expand=True)
        self.output_display = tb.ScrolledText(output_frame, wrap=tk.NONE, font=("Consolas", 11), height=25)
        self.output_display.pack(side=tk.LEFT, fill="both", expand=True)
        x_scroll = tk.Scrollbar(output_frame, orient=tk.HORIZONTAL, command=self.output_display.xview)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.output_display.config(xscrollcommand=x_scroll.set)

        # File export options
        file_ops_frame = tb.LabelFrame(self.root, text="File Save Options")
        file_ops_frame.pack(padx=10, pady=15, fill="x")

        export_btn = tb.Button(file_ops_frame, text="Export Data", bootstyle=INFO, command=self.export_data)
        export_btn.pack(padx=10, pady=10)

        self.status_label = ttk.Label(self.root, text="Ready", foreground="cyan")
        self.status_label.pack(pady=(2, 10))

    # Clear the output display
    def clear_output(self):
        self.output_display.delete("1.0", tk.END)
        self.status_label.config(text="Output cleared.")

    # Search data in the DataFrame based on user input
    def search_data(self):
        if not self.data_loaded or self.df is None:
            self.write_output("[Error] No data loaded. Please load a file first.")
            return

        query = self.search_var.get().strip()
        selected_col = self.search_column_var.get()
        case_sensitive = self.case_sensitive.get()
        whole_word = self.whole_word.get()

        if not query:
            self.write_output("[Error] Please enter a search term.")
            return
        
        # Build regex pattern for search
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = r"\b{}\b".format(re.escape(query)) if whole_word else re.escape(query)

        try:
            if selected_col == "All Columns":
                # Search across all columns
                mask = self.df.astype(str).apply(
                    lambda col: col.str.contains(pattern, flags=flags, na=False, regex=True)
                ).any(axis=1)
                result = self.df[mask]
            else:
                # Search in a single column
                mask = self.df[selected_col].astype(str).str.contains(pattern, flags=flags, na=False, regex=True)
                result = self.df[mask]
            
            self.output_display.delete("1.0", tk.END)
            self.output_display.tag_configure("highlight", background="yellow", foreground="black")
            
            if result.empty:
                self.output_display.insert(tk.END, f"No results found for: '{query}' in {selected_col}.")
                self.search_output_cache = None
                self.match_indices = []
                self.current_match = -1
                self.prev_btn.config(state="disabled")
                self.next_btn.config(state="disabled")
            else:
                self.output_display.insert(tk.END, f"Results for: '{query}' in '{selected_col}'\n\n")
                preview = result.head(50)
                table_str = tabulate(preview, headers="keys", tablefmt="fancy_grid")
                self.output_display.insert(tk.END, table_str)
                
                # Highlight matches in the output
                content = self.output_display.get("1.0", tk.END)
                for match in re.finditer(pattern, content, flags):
                    start = f"1.0+{match.start()}c"
                    end = f"1.0+{match.end()}c"
                    self.output_display.tag_add("highlight", start, end)
                    self.match_indices.append((start, end))
                self.current_match = 0 if self.match_indices else -1
                self.match_count_label.config(text=f"Matches: {len(self.match_indices)}")

                # Enable/disable navigation buttons
                state = "normal" if self.match_indices else "disabled"
                self.prev_btn.config(state=state)
                self.next_btn.config(state=state)

            # Select and scroll to the first match
            if self.match_indices:
                self.goto_match(0)

            self.search_output_cache = result

        except Exception as e:
            self.write_output(f"[Error] Search failed: {str(e)}")
            self.search_output_cache = None
            self.match_indices = []
            self.current_match = -1
            self.prev_btn.config(state="disabled")
            self.next_btn.config(state="disabled")

    # Highlight and scroll to a specific match in the output
    def goto_match(self, idx):
        if not self.match_indices:
            self.match_count_label.config(text="Matches: 0")
            return
        start, end = self.match_indices[idx]
        self.output_display.tag_remove("sel", "1.0", tk.END)
        self.output_display.tag_add("sel", start, end)
        self.output_display.see(start)
        self.current_match = idx
        self.match_count_label.config(
            text=f"Match {self.current_match + 1} of {len(self.match_indices)}"
        )

    # Go to next search match
    def goto_next_match(self):
        if not self.match_indices:
            return
        next_idx = (self.current_match + 1) % len(self.match_indices)
        self.goto_match(next_idx)

    # Go to previous search match
    def goto_prev_match(self):
        if not self.match_indices:
            return
        prev_idx = (self.current_match - 1) % len(self.match_indices)
        self.goto_match(prev_idx) 

    # Try reading a CSV file with multiple encodings
    def try_read_csv_with_encodings(self, path, delimiter=None):
        encodings = ["utf-8", "utf-8-sig", "latin-1", "ISO-8859-1", "cp1252", "utf-16"]
        for enc in encodings:
            try:
                if delimiter:
                    df = pd.read_csv(path, encoding=enc, delimiter=delimiter,)
                else:
                    df = pd.read_csv(path, encoding=enc, sep=None, engine='python')
                return df, enc
            except Exception:
                continue
        raise UnicodeDecodeError("Unable to decode file with common encodings.")

    # Load data file (CSV, Excel, etc.)
    def load_data(self):
        self.status_label.config(text="Processing...")
        self.root.update()

        file_path = filedialog.askopenfilename(
            title="Select data file",
            filetypes=[
                ("CSV Files", ".csv"),
                ("Text Files", ".txt"),
                ("Excel Files", ".xlsx .xls"),
                ("All Files", ".*")
            ]
        )

        if file_path:
            try:
                ext = os.path.splitext(file_path)[1].lower()
                selected_encoding = self.encoding_dropdown.get()
                selected_delimiter_label = self.delimiter_dropdown.get()

                delimiter_map = {
                    "Comma (,)": ",",
                    "Tab (\\t)": "\t",
                    "Semicolon (;)": ";",
                    "Pipe (|)": "|"
                }

                delimiter = delimiter_map.get(selected_delimiter_label, None)

                if ext in [".csv", ".txt"]:
                    if selected_encoding == "Auto (Recommended)":
                        self.df, used_encoding = self.try_read_csv_with_encodings(file_path, delimiter)
                        self.write_output(f"[Load Data] File loaded using encoding: {used_encoding}, delimiter: {delimiter or 'Auto'}")
                    else:
                        if delimiter:
                            self.df = pd.read_csv(file_path, encoding=selected_encoding, delimiter=delimiter)
                        else:
                            self.df = pd.read_csv(file_path, encoding=selected_encoding, sep=None, engine="python")
                        self.write_output(f"[Load Data] File loaded using encoding: {selected_encoding}, delimiter: {delimiter or 'Auto'}")

                elif ext in [".xlsx", ".xls"]:
                    self.df = pd.read_excel(file_path)

                else:
                    self.write_output("[Load Data] Unsupported file type.")
                    self.status_label.config(text="Ready")
                    return

                self.data_loaded = True

                # Update UI labels with file name and shape
                self.file_label.config(text=f"Loaded: {os.path.basename(file_path)}", foreground="green")
                self.shape_label.config(text=f"Shape: {self.df.shape[0]} rows × {self.df.shape[1]} columns")

                self.status_label.config(text="Ready")
                self.run_btn.config(state="normal")

                cols = ["All Columns"] + list(self.df.columns)
                self.column_dropdown.config(values=cols)
                if "All Columns" not in cols:
                    cols.insert(0, "All Columns")
                self.column_dropdown.set("All Columns")
                self.search_column_dropdown.config(values=cols)
                self.search_column_dropdown.set("All Columns")

                self.row_entry.delete(0, tk.END)
                self.row_entry.insert(0, "10")
                self.sort_order_dropdown.set("Ascending")

                self.output_display.delete("1.0", tk.END)
                self.write_output(f"[Load Data] File loaded: {file_path}")

            except Exception as e:
                self.write_output(f"[Error] Failed to load file: {str(e)}")
                self.status_label.config(text="Error")
        else:
            self.write_output("[Load Data] No file selected.")
            self.status_label.config(text="Ready")

    # Run the selected analysis and display results
    def update_analysis_display(self):
        if not self.check_data_loaded():
            return

        self.run_btn.config(state="disabled")
        self.status_label.config(text="Running analysis...")
        self.root.update()

        self.output_display.delete("1.0", tk.END)
        selection = self.analysis_dropdown.get()
        col = self.column_dropdown.get()
        if col == "All Columns":
            col = None

        try:
            df_working = self.df.copy()
            try:
                num_rows = int(self.row_entry.get())
                if num_rows < 1:
                    raise ValueError
            except ValueError:
                self.write_output("[Error] Please enter a valid positive integer for rows to show.")
                self.status_label.config(text="Ready")
                self.run_btn.config(state="normal")
                return

            sort_order = self.sort_order_dropdown.get()

            if col:
                df_working = df_working[[col]]

            if sort_order == "Descending":
                df_working = df_working[::-1]

            # Data Preview analysis
            if selection == "Data Preview":
                preview = df_working.head(num_rows)
                dtypes_info = [(col, str(dtype)) for col, dtype in df_working.dtypes.items()]
                dtype_table = tabulate(dtypes_info, headers=["Column", "Data Type"], tablefmt="fancy_grid")
                preview_table = tabulate(preview, headers="keys", tablefmt="fancy_grid")
                full_output = f"[Data Types]\n{dtype_table}\n\n[Data Preview]\n{preview_table}"
                self.output_display.insert(tk.END, full_output)
                self.analysis_output_cache = full_output
                
            # Missing Values analysis
            elif selection == "Missing Values":
                try:
                    if df_working.empty:
                        msg = "Dataset is empty. Load a dataset first."
                        self.output_display.insert(tk.END, msg + "\n")
                        self.analysis_output_cache = msg
                    else:
                        missing_report = df_working.isnull().sum()
                        total_rows = len(df_working)

                        result = [
                            (col, count, f"{(count / total_rows) * 100:.2f}%")
                            for col, count in missing_report.items() if count > 0
                        ]

                        if result:
                            table = tabulate(
                                result,
                                headers=["Column", "Missing Count", "Percent (%)"],
                                tablefmt="fancy_grid"
                            )
                            summary = f"\nTotal Rows: {total_rows}\nTotal Columns with Missing Values: {len(result)}\n"
                            self.output_display.insert(tk.END, "=== Missing Values Report ===\n")
                            self.output_display.insert(tk.END, table + "\n")
                            self.output_display.insert(tk.END, summary + "\n")
                            self.analysis_output_cache = table + summary
                        else:
                            msg = "No missing values detected in the dataset."
                            self.output_display.insert(tk.END, msg + "\n")
                            self.analysis_output_cache = msg

                except Exception as e:
                    error_msg = f"An error occurred while checking missing values: {str(e)}"
                    self.output_display.insert(tk.END, error_msg + "\n")
                    self.analysis_output_cache = error_msg

            # Duplicate Detection analysis
            elif selection == "Duplicate Detection":
                total_rows = len(df_working)
                duplicate_rows = df_working[df_working.duplicated()]
                duplicate_all = df_working[df_working.duplicated(keep=False)]

                if not duplicate_rows.empty:
                    table = (
                        f"🔍 Duplicate Detection Report:\n"
                        f"- Total Rows: {total_rows}\n"
                        f"- Total Duplicate Entries (including repeats): {len(duplicate_all)}\n"
                        f"- Unique Duplicate Rows: {len(duplicate_rows)}\n\n"
                        f"Displaying the first {min(num_rows, len(duplicate_rows))} duplicate rows:\n\n"
                    )
                    table += tabulate(duplicate_rows.head(num_rows), headers="keys", tablefmt="fancy_grid")
                    table += "\n\n💡 Tip: Consider reviewing or removing these duplicates."

                    self.output_display.insert(tk.END, table)
                    self.analysis_output_cache = table
                else:
                    msg = (
                        f"✅ No duplicate rows found in the dataset.\n"
                        f"- Total Rows Checked: {total_rows}"
                    )
                    self.output_display.insert(tk.END, msg)
                    self.analysis_output_cache = msg

            # Placeholder Detection analysis
            elif selection == "Placeholder Detection":
                placeholders = {"N/A", "NA", "None", "none", "unknown", "Unknown", "-", "TBD", "tbd", "0000", "", "null", "NULL", "n/a"}
                report = []
                total_placeholders = 0

                for c in df_working.columns:
                    ser = df_working[c].astype(str).str.strip()
                    mask = ser.isin(placeholders)
                    count = mask.sum()
                    percent = (count / len(df_working)) * 100 if len(df_working) > 0 else 0
                    total_placeholders += count
                    chars = set("".join(ser[mask]))

                    if count > 0:
                        report.append([
                            c,
                            count,
                            f"{percent:.2f}%",
                            " ".join(sorted(chars)) if chars else "(none)"
                        ])

                if report:
                    table = tabulate(
                        report,
                        headers=["Column", "Placeholder Count", "Percent of Column", "Unique Placeholder Characters"],
                        tablefmt="fancy_grid"
                    )
                    summary = f"\nTotal Placeholders in Dataset: {total_placeholders}\n"
                    self.output_display.insert(tk.END, table + summary)
                    self.analysis_output_cache = table + summary
                else:
                    msg = "No placeholders detected in the dataset."
                    self.output_display.insert(tk.END, msg)
                    self.analysis_output_cache = msg

            # Special Character Analysis
            elif selection == "Special Character Analysis":
                special_chars_pattern = r"[^\w\s]|[^\x00-\x7F]"
                report = []
                for c in df_working.columns:
                    series = df_working[c].astype(str)
                    mask = series.str.contains(special_chars_pattern, regex=True)
                    count = mask.sum()
                    if count > 0:
                        joined_text = "".join(series[mask])
                        unique_chars = set(re.findall(special_chars_pattern, joined_text))
                        ascii_chars = sorted([ch for ch in unique_chars if ord(ch) < 128])
                        non_ascii_chars = sorted([ch for ch in unique_chars if ord(ch) >= 128])
                        ascii_str = " ".join(ascii_chars) if ascii_chars else "(none)"
                        non_ascii_str = " ".join(non_ascii_chars) if non_ascii_chars else "(none)"
                        sample_text = "; ".join(series[mask].unique()[:5])
                        report.append([c, count, ascii_str, non_ascii_str, sample_text])
                if report:
                    table = tabulate(report, headers=["Column", "Occurrences", "ASCII Characters", "Non-ASCII Characters", "Sample Values"], tablefmt="fancy_grid")
                    self.output_display.insert(tk.END, table)
                    self.analysis_output_cache = table
                else:
                    msg = "No special characters found."
                    self.output_display.insert(tk.END, msg)
                    self.analysis_output_cache = msg

            # Fallback for unimplemented analysis
            else:
                notice = f"[Notice] '{selection}' analysis not implemented."
                self.output_display.insert(tk.END, notice)
                self.analysis_output_cache = notice

        except Exception as e:
            self.write_output(f"[Display Error] {str(e)}")
            self.analysis_output_cache = None

        self.output_display.yview_moveto(0)
        self.status_label.config(text="Ready")
        self.run_btn.config(state="normal")

    # Export data or analysis results to file
    def export_data(self):
        from tkinter.simpledialog import askstring

        answer = askstring("Export Choice", "Enter export choice:\n- full\n- search\n- analysis\n\n(Type one)")

        if not answer:
            self.status_label.config(text="Export cancelled.")
            return

        answer = answer.strip().lower()

        try:
            if answer == "full":
                if not self.data_loaded or self.df is None:
                    messagebox.showerror("Error", "No full dataset loaded.")
                    return
                df_to_export = self.df

            elif answer == "search":
                if self.search_output_cache is None or self.search_output_cache.empty:
                    messagebox.showerror("Error", "No search results to export.")
                    return
                df_to_export = self.search_output_cache

            elif answer == "analysis":
                if self.analysis_output_cache is None:
                    messagebox.showerror("Error", "No analysis output to export.")
                    return
                # Export analysis as text file
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text File", "*.txt")],
                    title="Save analysis output as"
                )
                if not save_path:
                    self.status_label.config(text="Export cancelled.")
                    return
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(self.analysis_output_cache)
                self.status_label.config(text=f"Analysis output exported to {save_path}")
                messagebox.showinfo("Export Success", f"Analysis output exported to:\n{save_path}")
                return
            else:
                messagebox.showerror("Error", "Invalid export choice. Please enter full, search, or analysis.")
                return

            # Export DataFrame as CSV or Excel
            save_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV File", "*.csv"), ("Excel File", "*.xlsx")],
                title="Save exported data as"
            )
            if not save_path:
                self.status_label.config(text="Export cancelled.")
                return

            ext = os.path.splitext(save_path)[1].lower()
            if ext == ".csv":
                df_to_export.to_csv(save_path, index=False)
            elif ext == ".xlsx":
                df_to_export.to_excel(save_path, index=False)
            else:
                messagebox.showerror("Error", "Unsupported file extension for export.")
                return

            self.status_label.config(text=f"Data exported to {save_path}")
            messagebox.showinfo("Export Success", f"Data exported to:\n{save_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data:\n{str(e)}")
            self.status_label.config(text="Export failed.")

    # Toggle between light and dark themes
    def toggle_theme(self):
        style = tb.Style()
        current_theme = style.theme_use()
        new_theme = "litera" if current_theme == "superhero" else "superhero"
        style.theme_use(new_theme)
        self.status_label.config(text=f"Theme changed to {new_theme}")

    # Convert file between formats (CSV, Excel, etc.)
    def convert_file(self):
        file_path = filedialog.askopenfilename(
            title="Select file to convert",
            filetypes=[
                ("Text Files", "*.txt"),
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls"),
                ("All Files", ".*")
            ]
        )
        if not file_path:
            self.status_label.config(text="Conversion cancelled.")
            return

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext in [".txt", ".csv"]:
                # Try reading as CSV with auto delimiter
                try:
                    df = pd.read_csv(file_path, sep=None, engine='python')
                except Exception:
                    # fallback read as plain text with no delimiter
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    df = pd.DataFrame(lines, columns=["Data"])

            elif ext in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path)
            else:
                messagebox.showerror("Error", "Unsupported file type for conversion.")
                return

            # Ask save location and format
            save_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV File", "*.csv"), ("Excel File", "*.xlsx")],
                title="Save converted file as"
            )
            if not save_path:
                self.status_label.config(text="Conversion cancelled.")
                return

            save_ext = os.path.splitext(save_path)[1].lower()
            if save_ext == ".csv":
                df.to_csv(save_path, index=False)
            elif save_ext == ".xlsx":
                df.to_excel(save_path, index=False)
            else:
                messagebox.showerror("Error", "Unsupported save file extension.")
                return

            self.status_label.config(text=f"File converted and saved to {save_path}")
            messagebox.showinfo("Success", f"File converted and saved:\n{save_path}")

        except Exception as e:
            messagebox.showerror("Conversion Error", f"Failed to convert file:\n{str(e)}")
            self.status_label.config(text="Conversion failed.")

# Show splash/intro window before launching main app
def show_intro():
    splash = tk.Tk()
    splash.title("DataScope Loading...")
    splash.geometry("600x300+400+200")
    splash.configure(bg="#1e1e2f")
    splash.overrideredirect(True)

    try:
        logo_path = os.path.abspath(os.path.join(os.getcwd(), "assets", "protexxa-logo.png"))
        logo_image = Image.open(logo_path).resize((136, 41), Image.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_image)
    except Exception:
        logo_photo = None

    tk.Label(splash, text="PROPERTY OF", font=("Helvetica", 10, "bold"), bg="#1e1e2f", fg="white").pack()
    if logo_photo:
        tk.Label(splash, image=logo_photo, bg="#1e1e2f").pack(pady=(20, 5))
    tk.Label(
        splash,
        text="13.1°N 59.32°W → 43° 39' 11.6136'' N 79° 22' 59.4624'' W\n"
             "AICohort01: The Intelligence Migration \nData Cleaning Division",
        font=("Helvetica", 10), bg="#1e1e2f", fg="white", justify="center"
    ).pack(pady=(10, 5))

    # Launch main app after splash
    def launch():
        splash.destroy()
        root = tb.Window(title="DataScope Day-0 Interface", themename="litera")
        app = DataScopeApp(root)
        root.mainloop()

    splash.after(4000, launch)
    splash.bind("<Button-1>", lambda e: launch())
    splash.mainloop()

# Entry point
if __name__ == "__main__":
    show_intro()
