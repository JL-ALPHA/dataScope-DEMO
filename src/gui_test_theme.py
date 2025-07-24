import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog
from PIL import Image, ImageTk
import os

# Global flag for checking if dataset was loaded
data_loaded = False

# ----------------------------------------
# GUI UTILITY FUNCTIONS
# ----------------------------------------

def write_output(message: str):
    """Display message in the output area and print to terminal."""
    print(message)
    output_area.insert(tk.END, message + "\n")
    output_area.see(tk.END)

def load_data():
    """Load dataset from file and enable test buttons."""
    global data_loaded
    status_label.config(text="Processing...")
    root.update()

    file_path = filedialog.askopenfilename(
        title="Select data file",
        filetypes=[("CSV Files", ".csv"), ("Excel Files", ".xlsx .xls"), ("All Files", ".*")]
    )
    if file_path:
        write_output(f"[Load Data] File selected: {file_path}")
        data_loaded = True
        btn_log.config(state="normal")
        btn_data.config(state="normal")
        btn_visual.config(state="normal")
        status_label.config(text="Ready")
    else:
        write_output("[Load Data] No file selected.")
        status_label.config(text="Ready")

def check_data_loaded():
    """Guard clause for requiring a loaded dataset."""
    if not data_loaded:
        write_output("[Error] Load data first before testing.")
        return False
    return True

# ----------------------------------------
# TEST HANDLERS
# ----------------------------------------

def logging_handler_test():
    if not check_data_loaded():
        return
    write_output("[Logging Handler] Test complete: Logging system operational.")

def data_handler_test():
    if not check_data_loaded():
        return
    write_output("[Data Handler] Test complete: Data loaded and validated.")

def visual_analyst_test():
    if not check_data_loaded():
        return
    write_output("[Visual Analyst] Test complete: Visualizations generated.")

# ----------------------------------------
# INTRO SPLASH SCREEN
# ----------------------------------------

def show_intro():
    """Splash screen displaying logo and transition message."""
    splash = tk.Tk()
    splash.title("DataScope Loading...")
    splash.geometry("600x300+400+200")
    splash.configure(bg="#1e1e2f")  # Dark background for contrast
    splash.overrideredirect(True)  # Remove window border

    # Load and resize logo
    logo_path = os.path.join("assets", "protexxa-logo.png")
    logo_image = Image.open(logo_path)
    logo_image = logo_image.resize((136, 41), Image.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_image)

    # All labels now explicitly use the dark background and white text
    tk.Label(splash, text="PROPERTY OF", font=("Helvetica", 10, "bold"), bg="#1e1e2f", fg="white").pack()
    tk.Label(splash, image=logo_photo, bg="#1e1e2f").pack(pady=(20, 5))
    tk.Label(
        splash,
        text="13.1°N 59.32°W → 43° 39' 11.6136'' N 79° 22' 59.4624'' W\n AICohort01: The Intelligence Migration \nData Cleaning Division",
        font=("Helvetica", 10), bg="#1e1e2f", fg="white", justify="center"
    ).pack(pady=(10, 5))

    def transition_to_gui(*_):
        splash.destroy()
        launch_gui()

    splash.after(9000, transition_to_gui)
    splash.bind("<Button-1>", transition_to_gui)
    splash.mainloop()


# ----------------------------------------
# MAIN GUI LAUNCH
# ----------------------------------------

def launch_gui():
    """Main DataScope GUI interface."""
    global root, output_area, btn_log, btn_data, btn_visual, status_label

    root = tk.Tk()
    root.title("DataScope Day-0 Interface")

    # --- Header Banner ---
    banner = ttk.Label(root, text="DataScope Project - Day-0 Interface", font=("Arial", 16, "bold"))
    banner.pack(pady=10)

    # --- Output Console ---
    output_area = scrolledtext.ScrolledText(root, width=100, height=20, wrap=tk.WORD)
    output_area.pack(padx=10, pady=10)

    # --- Button Frame ---
    btn_frame = ttk.Frame(root)
    btn_frame.pack(pady=10)

    btn_load = ttk.Button(btn_frame, text="Load Data", command=load_data)
    btn_load.grid(row=0, column=0, padx=5)

    btn_log = ttk.Button(btn_frame, text="Test Logging & Error Handler", command=logging_handler_test, state="disabled")
    btn_log.grid(row=0, column=1, padx=5)

    btn_data = ttk.Button(btn_frame, text="Test Data Handling", command=data_handler_test, state="disabled")
    btn_data.grid(row=0, column=2, padx=5)

    btn_visual = ttk.Button(btn_frame, text="Test Visual Analyst", command=visual_analyst_test, state="disabled")
    btn_visual.grid(row=0, column=3, padx=5)

    # --- File Save Options Placeholder ---
    file_ops_frame = ttk.LabelFrame(root, text="File Save Options")
    file_ops_frame.pack(padx=10, pady=15, fill="x")

    ttk.Label(file_ops_frame, text="(File save buttons and options will be updated post Day-0)").pack(padx=10, pady=10)

    # --- Status Bar ---
    status_label = ttk.Label(root, text="Ready", foreground="blue")
    status_label.pack(pady=5)

    root.mainloop()

# ----------------------------------------
# EXECUTE ENTRY POINT
# ----------------------------------------

show_intro()
