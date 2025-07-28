import sys, os

# Determine where assets were unpacked.
if getattr(sys, "frozen", False):
    # Running as a bundled EXE
    ASSETS_DIR = os.path.join(sys._MEIPASS, "assets")
else:
    # Running from source
    ASSETS_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "assets")
    )


import flet as ft
import asyncio
import os
import logging
import sys
import pandas as pd
import json
import math



import data_handler
from data_handler import (
    create_dataset_environment,
    load_data,
    run_analysis,
    convert_file,
    search_dataframe,
    export_dataframe,
    export_text,
)



from pathlib import Path
import json
import sys
import math

dev_mode = False  # Set to True for development mode, False for production

# Global variable to store the DF (SEAN FEATURE BUILDOUT)
current_df = None
current_theme_mode = ft.ThemeMode.LIGHT


# Ensure the current directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# SETTINGS!-----------------------------------------------------------------------------------------
# Directory under the user's home folder for storing preferences.
# Using the home directory ensures the path is writable even when the
# application is packaged as an executable.
PREFERENCES_DIR = Path.home() / "ProtexxaDatascope" / "preferences"

# Full path to the theme configuration file.
SETTINGS_FILE = PREFERENCES_DIR / "theme.json"


def load_theme_preference() -> bool:
    """Retrieve the stored theme preference, if available."""

    if SETTINGS_FILE.exists():
        try:
            with SETTINGS_FILE.open("r") as f:
                data = json.load(f)
            return data.get("dark_mode", False)
        except json.JSONDecodeError:
            logging.error("Failed to parse %s", SETTINGS_FILE)
            print(f"[Preferences] Failed parsing {SETTINGS_FILE}")
    return False


# Dark Mode Save Function
def save_theme_preference(dark_mode: bool) -> None:
    """Persist the dark mode preference to disk."""

    PREFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open("w") as f:
        json.dump({"dark_mode": dark_mode}, f)
    logging.info("Saved theme preference to %s", SETTINGS_FILE)
    print(f"[Preferences] Theme saved -> {SETTINGS_FILE}")


# SETTINGS!-----------------------------------------------------------------------------------------

# Global flag for checking if dataset was loaded
data_loaded = False
# Indicates if a long operation is running
app_busy = False
# Default chunk size for CSV splitting operations
CHUNK_SIZE_DEFAULT = 256

# File conversion helper variables
convert_input_path = None
convert_output_dir = None

# Icon to represent CSV splitting. Older versions of this file referenced
# ``ft.Icon.SPLIT_CSV_OUTLINE`` which does not exist in Flet.  We gracefully
# fall back to ``HORIZONTAL_SPLIT_OUTLINED`` to avoid runtime errors.
SPLIT_CSV_ICON = getattr(
    ft.Icons, "SPLIT_CSV_OUTLINE", ft.Icons.HORIZONTAL_SPLIT_OUTLINED
)

# Control references
dialog_controls = {
    "output_text_field": None,
    "btn_log": None,
    "btn_data": None,
    "btn_visual": None,
    "status_label": None,
    "file_picker": None,
    "theme_switch": None,
    "chunk_size_input": None,
    "chunk_status": None,
    "logo_image": None,
    "tabs": None,
    "splash_container": None,
    "convert_status": None,
    "convert_file_picker": None,
    "convert_dir_picker": None,
    "convert_file_display": None,
    "convert_dir_display": None,
    "progress_bar": None,
    "progress_text": None,
    "export_picker": None,
    "match_label": None,
    "export_format": "csv",
    "encoding": "auto",
    "delimiter": None,
    "search_results": None,
    "search_index": 0,
    "convert_format": "csv",
    "analysis_text": "",
    "data_table": None,
    "data_table_info": None,
    "current_page": 1,
    "rows_per_page": 25,  # Reduced from 50 to 25 for faster GUI performance
    "total_pages": 1,
    "current_data": None,
    "pagination_info": None,
    "prev_page_btn": None,
    "next_page_btn": None,
    "page_size_dropdown": None,
    "goto_page_input": None,
}

export_context = None


export_context = None


async def write_output(message: str, page: ft.Page):
    print(message)
    if dialog_controls["output_text_field"]:
        dialog_controls["output_text_field"].value += message + "\n"
        page.update()


async def check_data_loaded(page: ft.Page):
    if not data_loaded:
        await write_output("[Error] Load data first before testing.", page)
        return False
    return True


# Flash the logo between grayscale and color when app_busy is True
async def flash_logo(page: ft.Page):
    step = 0
    speed = 1.1  # Smaller is slower breathing

    while True:
        logo_ref = dialog_controls.get("logo_image")
        logo = logo_ref.current if logo_ref else None

        if not logo:
            await asyncio.sleep(0.5)
            continue

        if app_busy:
            # Use a sine wave for smooth breathing (ease-in-out feel)
            # Maps step from 0 to π (half sine wave) for inhale → exhale
            # Normalized from 0.3 to 1.0 opacity
            t = (math.sin(step) + 1) / 2  # t in [0, 1]
            logo.opacity = 0.3 + t * 0.7  # scale to [0.3, 1.0]
            logo.update()
            step += speed
            if step > math.pi * 2:
                step = 0
            await asyncio.sleep(0.05)  # Higher = choppier
        else:
            if logo.opacity != 1.0:
                logo.opacity = 1.0
                logo.update()
            await asyncio.sleep(0.5)


def focus_console_tab(page: ft.Page):
    """Switch to the Console tab if the tab control exists."""
    tabs = dialog_controls.get("tabs")
    if tabs:
        tabs.selected_index = 0
        page.update()


def focus_dataview_tab(page: ft.Page):
    """Switch to the Data View tab if the tab control exists."""
    tabs = dialog_controls.get("tabs")
    if tabs:
        tabs.selected_index = 1  # Data View tab is at index 1
        page.update()


def get_paginated_data(df, page_num=1, rows_per_page=25):
    """Get a specific page of data from a DataFrame."""
    if df is None or df.empty:
        return df, 0, 1
    
    total_rows = len(df)
    total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
    
    # Ensure page_num is within valid range
    page_num = max(1, min(page_num, total_pages))
    
    start_idx = (page_num - 1) * rows_per_page
    end_idx = start_idx + rows_per_page
    
    paginated_df = df.iloc[start_idx:end_idx].reset_index(drop=True)
    
    return paginated_df, total_rows, total_pages


def update_pagination_info(page: ft.Page):
    """Update pagination information display and page buttons."""
    current_page = dialog_controls.get("current_page", 1)
    total_pages = dialog_controls.get("total_pages", 1)
    rows_per_page = dialog_controls.get("rows_per_page", 25)
    current_data = dialog_controls.get("current_data")
    
    if current_data is not None:
        total_rows = len(current_data)
        start_row = (current_page - 1) * rows_per_page + 1
        end_row = min(current_page * rows_per_page, total_rows)
        
        pagination_info = dialog_controls.get("pagination_info")
        if pagination_info:
            pagination_info.value = f"Showing {start_row}-{end_row} of {total_rows} rows"
    
    # Update button states
    prev_btn = dialog_controls.get("prev_page_btn")
    next_btn = dialog_controls.get("next_page_btn")
    first_btn = dialog_controls.get("first_page_btn")
    last_btn = dialog_controls.get("last_page_btn")
    
    if prev_btn:
        prev_btn.disabled = current_page <= 1
    if next_btn:
        next_btn.disabled = current_page >= total_pages
    if first_btn:
        first_btn.disabled = current_page <= 1
    if last_btn:
        last_btn.disabled = current_page >= total_pages
    
    # Update page buttons
    page_buttons_row = dialog_controls.get("page_buttons_row")
    if page_buttons_row and total_pages > 1:
        page_buttons_row.controls = create_page_buttons(page)
    
    page.update()


async def on_prev_page(e: ft.ControlEvent):
    """Handle previous page navigation."""
    current_page = dialog_controls.get("current_page", 1)
    if current_page > 1:
        dialog_controls["current_page"] = current_page - 1
        await refresh_current_view(e.page)


async def on_next_page(e: ft.ControlEvent):
    """Handle next page navigation."""
    current_page = dialog_controls.get("current_page", 1)
    total_pages = dialog_controls.get("total_pages", 1)
    if current_page < total_pages:
        dialog_controls["current_page"] = current_page + 1
        await refresh_current_view(e.page)


async def on_first_page(e: ft.ControlEvent):
    """Handle first page navigation."""
    if dialog_controls.get("current_page", 1) > 1:
        dialog_controls["current_page"] = 1
        await refresh_current_view(e.page)


async def on_last_page(e: ft.ControlEvent):
    """Handle last page navigation."""
    total_pages = dialog_controls.get("total_pages", 1)
    if dialog_controls.get("current_page", 1) < total_pages:
        dialog_controls["current_page"] = total_pages
        await refresh_current_view(e.page)


def on_page_number_click(page_num):
    """Handle clicking on a specific page number."""
    async def handler(e: ft.ControlEvent):
        dialog_controls["current_page"] = page_num
        await refresh_current_view(e.page)
    return handler


def create_page_buttons(page: ft.Page):
    """Create numbered page buttons with ellipsis for large page counts."""
    current_page = dialog_controls.get("current_page", 1)
    total_pages = dialog_controls.get("total_pages", 1)
    
    if total_pages <= 1:
        return []
    
    buttons = []
    
    # Determine if we're in dark mode for theming
    is_dark_mode = page.theme_mode == ft.ThemeMode.DARK
    
    # Color scheme based on theme
    if is_dark_mode:
        active_bg = ft.Colors.BLUE_700
        active_text = ft.Colors.WHITE
        inactive_bg = ft.Colors.GREY_800
        inactive_text = ft.Colors.GREY_300
        hover_bg = ft.Colors.GREY_700
    else:
        active_bg = ft.Colors.BLUE_600
        active_text = ft.Colors.WHITE
        inactive_bg = ft.Colors.GREY_100
        inactive_text = ft.Colors.GREY_700
        hover_bg = ft.Colors.GREY_200
    
    # Logic for showing page numbers
    if total_pages <= 7:
        # Show all pages if 7 or fewer
        for i in range(1, total_pages + 1):
            is_current = i == current_page
            button = ft.Container(
                content=ft.Text(
                    str(i),
                    color=active_text if is_current else inactive_text,
                    weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL,
                    size=14,
                ),
                bgcolor=active_bg if is_current else inactive_bg,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=6,
                border=ft.border.all(1, active_bg if is_current else ft.Colors.GREY_400),
                on_click=on_page_number_click(i),
                animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            )
            # Add hover effect for non-current pages
            if not is_current:
                button.on_hover = lambda e, bg=hover_bg: setattr(e.control, 'bgcolor', bg if e.data == "true" else inactive_bg) or e.page.update()
            
            buttons.append(button)
    else:
        # Show smart pagination with ellipsis
        # Always show first page
        buttons.append(create_page_button(1, current_page, is_dark_mode))
        
        if current_page > 4:
            # Add ellipsis after first page
            buttons.append(ft.Text("...", color=inactive_text))
        
        # Show pages around current page
        start = max(2, current_page - 1)
        end = min(total_pages - 1, current_page + 1)
        
        for i in range(start, end + 1):
            buttons.append(create_page_button(i, current_page, is_dark_mode))
        
        if current_page < total_pages - 3:
            # Add ellipsis before last page
            buttons.append(ft.Text("...", color=inactive_text))
        
        # Always show last page
        if total_pages > 1:
            buttons.append(create_page_button(total_pages, current_page, is_dark_mode))
    
    return buttons


def create_page_button(page_num, current_page, is_dark_mode):
    """Create a single page button with proper theming."""
    is_current = page_num == current_page
    
    # Color scheme based on theme
    if is_dark_mode:
        active_bg = ft.Colors.BLUE_700
        active_text = ft.Colors.WHITE
        inactive_bg = ft.Colors.GREY_800
        inactive_text = ft.Colors.GREY_300
        hover_bg = ft.Colors.GREY_700
    else:
        active_bg = ft.Colors.BLUE_600
        active_text = ft.Colors.WHITE
        inactive_bg = ft.Colors.GREY_100
        inactive_text = ft.Colors.GREY_700
        hover_bg = ft.Colors.GREY_200
    
    button = ft.Container(
        content=ft.Text(
            str(page_num),
            color=active_text if is_current else inactive_text,
            weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL,
            size=14,
        ),
        bgcolor=active_bg if is_current else inactive_bg,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=6,
        border=ft.border.all(1, active_bg if is_current else ft.Colors.GREY_400),
        on_click=on_page_number_click(page_num),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )
    
    # Add hover effect for non-current pages
    if not is_current:
        button.on_hover = lambda e, bg=hover_bg: setattr(e.control, 'bgcolor', bg if e.data == "true" else inactive_bg) or e.page.update()
    
    return button


async def on_page_size_change(e: ft.ControlEvent):
    """Handle page size change."""
    try:
        new_size = int(e.control.value)
        dialog_controls["rows_per_page"] = new_size
        dialog_controls["current_page"] = 1  # Reset to first page
        await refresh_current_view(e.page)
    except ValueError:
        pass


async def refresh_current_view(page: ft.Page):
    """Refresh the current data view with pagination."""
    current_data = dialog_controls.get("current_data")
    if current_data is not None:
        current_page = dialog_controls.get("current_page", 1)
        rows_per_page = dialog_controls.get("rows_per_page", 25)
        
        # Get current search state
        search_term = dialog_controls.get("search_term", "")
        search_column = dialog_controls.get("search_column", "")
        highlight_term = search_term.value if hasattr(search_term, 'value') and search_term.value else None
        highlight_column = search_column.value if hasattr(search_column, 'value') and search_column.value != "All Columns" else None
        
        paginated_df, total_rows, total_pages = get_paginated_data(current_data, current_page, rows_per_page)
        
        dialog_controls["total_pages"] = total_pages
        
        update_data_table(paginated_df, page, 
                         highlight_term=highlight_term, 
                         highlight_column=highlight_column,
                         is_paginated=True)
        update_pagination_info(page)


def apply_data_table_theme(page: ft.Page):
    """Apply theme colors to the DataTable, search, and pagination containers based on current theme mode."""
    data_table = dialog_controls.get("data_table")
    if not data_table:
        return
    
    # Determine if we're in dark mode
    is_dark_mode = page.theme_mode == ft.ThemeMode.DARK
    
    # Apply colors based on theme
    if is_dark_mode:
        data_table.bgcolor = ft.Colors.GREY_900
        data_table.heading_row_color = ft.Colors.GREY_700
        data_table.border = ft.border.all(1, ft.Colors.GREY_600)
        data_table.vertical_lines = ft.BorderSide(1, ft.Colors.GREY_600)
        data_table.horizontal_lines = ft.BorderSide(1, ft.Colors.GREY_600)
        
        # Dark theme colors for containers
        container_bg = ft.Colors.GREY_800
        container_border = ft.Colors.GREY_600
        info_color = ft.Colors.GREY_300
    else:
        data_table.bgcolor = ft.Colors.WHITE
        data_table.heading_row_color = ft.Colors.GREY_100
        data_table.border = ft.border.all(1, ft.Colors.GREY_400)
        data_table.vertical_lines = ft.BorderSide(1, ft.Colors.GREY_300)
        data_table.horizontal_lines = ft.BorderSide(1, ft.Colors.GREY_300)
        
        # Light theme colors for containers
        container_bg = ft.Colors.GREY_50
        container_border = ft.Colors.BLUE_GREY_200
        info_color = ft.Colors.GREY_600
    
    # Update pagination info text color
    pagination_info = dialog_controls.get("pagination_info")
    if pagination_info:
        pagination_info.color = info_color
    
    # Also update the container borders if they exist
    tabs = dialog_controls.get("tabs")
    if tabs and len(tabs.tabs) > 1:  # Data View is at index 1
        data_view_tab = tabs.tabs[1]
        if hasattr(data_view_tab, 'content') and hasattr(data_view_tab.content, 'controls'):
            for control in data_view_tab.content.controls:
                if isinstance(control, ft.Container):
                    # Update search container theme
                    if hasattr(control.content, 'controls') and len(control.content.controls) > 0:
                        first_control = control.content.controls[0]
                        if hasattr(first_control, 'value') and "🔍 Search Data" in str(first_control.value):
                            control.bgcolor = container_bg
                            control.border = ft.border.all(1, container_border)
                    
                    # Update pagination container theme
                    elif hasattr(control.content, 'controls') and len(control.content.controls) > 0:
                        # Check if this is a pagination container by looking for Column with Rows
                        first_control = control.content.controls[0]
                        if isinstance(first_control, ft.Column) and len(first_control.controls) > 0:
                            # Look for navigation buttons in the first row of the column
                            first_row = first_control.controls[0]
                            if isinstance(first_row, ft.Row):
                                for row_control in first_row.controls:
                                    if hasattr(row_control, 'icon') and row_control.icon in [ft.Icons.FIRST_PAGE, ft.Icons.ARROW_BACK]:
                                        control.bgcolor = container_bg
                                        control.border = ft.border.all(1, container_border)
                                        break
                    
                    # Update data table container
                    elif (hasattr(control.content, 'controls') and 
                          len(control.content.controls) > 0 and 
                          hasattr(control.content.controls[0], 'controls') and
                          len(control.content.controls[0].controls) > 0 and
                          control.content.controls[0].controls[0] == data_table):
                        if is_dark_mode:
                            control.border = ft.border.all(1, ft.Colors.GREY_600)
                        else:
                            control.border = ft.border.all(1, ft.Colors.GREY_300)


def update_data_table(df, page: ft.Page, max_rows=None, highlight_term=None, highlight_column=None, is_paginated=False):
    """Update the data table with DataFrame content and switch to Data View tab."""
    if df is None or df.empty:
        return
    
    # Store current data for pagination if not already paginated
    if not is_paginated:
        dialog_controls["current_data"] = df
        dialog_controls["current_page"] = 1
        
        # Apply pagination if data is large
        if max_rows is None and len(df) > dialog_controls.get("rows_per_page", 25):
            rows_per_page = dialog_controls.get("rows_per_page", 25)
            display_df, total_rows, total_pages = get_paginated_data(df, 1, rows_per_page)
            dialog_controls["total_pages"] = total_pages
        else:
            display_df = df if max_rows is None else df.head(max_rows)
            dialog_controls["total_pages"] = 1
    else:
        # Data is already paginated
        display_df = df
    
    # Create columns for the DataTable
    columns = [ft.DataColumn(ft.Text(col)) for col in display_df.columns]
    
    # Create rows for the DataTable with highlighting support
    rows = []
    for index, row in display_df.iterrows():
        cells = []
        for col_name, value in row.items():
            cell_text = str(value)
            
            # Apply highlighting if search term is provided
            if (highlight_term and highlight_term.lower() in cell_text.lower() and 
                (highlight_column is None or highlight_column == col_name)):
                # Determine colors based on theme
                is_dark_mode = page.theme_mode == ft.ThemeMode.DARK
                if is_dark_mode:
                    highlight_bg = ft.Colors.AMBER_700
                    highlight_text = ft.Colors.BLACK
                else:
                    highlight_bg = ft.Colors.YELLOW_300
                    highlight_text = ft.Colors.BLACK
                
                cell_content = ft.Container(
                    content=ft.Text(cell_text, color=highlight_text),
                    bgcolor=highlight_bg,
                    padding=4,
                    border_radius=3,
                )
                cells.append(ft.DataCell(cell_content))
            else:
                cells.append(ft.DataCell(ft.Text(cell_text)))
        rows.append(ft.DataRow(cells=cells))
    
    # Update the data table
    data_table = dialog_controls.get("data_table")
    if data_table:
        data_table.columns = columns
        data_table.rows = rows
        
        # Update the row count label
        if not is_paginated:
            current_data = dialog_controls.get("current_data")
            total_rows = len(current_data) if current_data is not None else len(df)
            displayed_rows = len(display_df)
            
            if dialog_controls.get("total_pages", 1) > 1:
                current_page = dialog_controls.get("current_page", 1)
                start_row = (current_page - 1) * dialog_controls.get("rows_per_page", 25) + 1
                end_row = min(current_page * dialog_controls.get("rows_per_page", 25), total_rows)
                dialog_controls["data_table_info"].value = f"Showing rows {start_row}-{end_row} of {total_rows} total"
            else:
                if max_rows is None:
                    dialog_controls["data_table_info"].value = f"Showing all {displayed_rows} rows"
                else:
                    dialog_controls["data_table_info"].value = f"Showing {displayed_rows} of {total_rows} rows"
        
        # Apply theme colors to the table
        apply_data_table_theme(page)
        
        # Update pagination info if paginated
        if dialog_controls.get("total_pages", 1) > 1:
            update_pagination_info(page)
        
        # Switch to Data View tab and update
        focus_dataview_tab(page)


async def update_progress(progress: float, message: str, page: ft.Page):
    """Update progress bar value and accompanying text.

    A small utility that ensures the UI reflects the given progress
    percentage. Also prints/logs the update for traceability.
    """
    logging.info("Progress update: %s%% - %s", progress, message)
    print(f"Progress update: {progress}% - {message}")
    if dialog_controls["progress_bar"]:
        dialog_controls["progress_bar"].value = progress / 100.0
        dialog_controls["progress_text"].value = f"{message} ({progress:.0f}%)"
        page.update()


async def show_progress(show: bool, page: ft.Page):
    """Toggle visibility of progress related widgets."""
    logging.info("Show progress widgets: %s", show)
    print(f"Show progress widgets: {show}")
    if dialog_controls["progress_bar"]:
        dialog_controls["progress_bar"].visible = show
        dialog_controls["progress_text"].visible = show
        page.update()


def show_error(message: str, page: ft.Page) -> None:
    """Display an error dialog with the provided message."""
    logging.error("Dialog error: %s", message)
    print(f"[GUI Error] {message}")
    
    # Show traditional error dialog
    dlg = ft.AlertDialog(title=ft.Text("Error"), content=ft.Text(message))
    page.dialog = dlg
    dlg.open = True
    page.update()


async def reset_app_state(page: ft.Page):
    """Return the UI to a safe baseline after an error.

    This helper clears global flags, resets dropdown options and updates
    the status label so that the user can attempt the operation again
    without stale state lingering.
    """
    global current_df, data_loaded, app_busy
    logging.error("Resetting application state due to error")
    print("[GUI] Resetting application state due to error")
    current_df = None
    data_loaded = False
    app_busy = False

    cd = dialog_controls.get("column_dropdown")
    if cd:
        cd.options = [ft.dropdown.Option("All Columns")]
        cd.value = "All Columns"

    dialog_controls["status_label"].value = "An error occurred, Please try again, Ready"
    dialog_controls["status_label"].color = ft.Colors.GREEN
    page.update()


async def logging_handler_test(e: ft.ControlEvent):
    page = e.page
    if not await check_data_loaded(page):
        return
    await write_output(
        "[Logging Handler] Beep Boop Beep, Test Complete! (This is just text output.)", page
    )
    # Show a sample of the data in the Data View tab with pagination
    if current_df is not None:
        sample_df = current_df.head(20)  # Show first 20 rows as a test
        update_data_table(sample_df, page)


async def data_handler_test(e: ft.ControlEvent):
    page = e.page
    if not await check_data_loaded(page):
        return
    await write_output("[Data Handler] Beep Boop Beep, Test Complete! (This is just text output.)", page)
    # Show data summary in the Data View tab with pagination
    if current_df is not None:
        summary_df = current_df.describe(include='all').transpose()  # Show data summary
        update_data_table(summary_df, page)


async def visual_analyst_test(e: ft.ControlEvent):
    page = e.page
    if not await check_data_loaded(page):
        return
    await write_output(
        "[Visual Analyst] Beep Boop Beep, Test Complete! (This is just text output.)", page
    )
    # Show data types and info in the Data View tab with pagination
    if current_df is not None:
        # Create a DataFrame with column information
        info_data = {
            'Column': current_df.columns.tolist(),
            'Data Type': [str(dtype) for dtype in current_df.dtypes],
            'Non-Null Count': [current_df[col].count() for col in current_df.columns],
            'Null Count': [current_df[col].isnull().sum() for col in current_df.columns],
        }
        info_df = pd.DataFrame(info_data)
        update_data_table(info_df, page)


# FILE HANDLER BLOCK----------------------------------------------------------------------------------------
from data_handler import save_filepath, get_data_stats, split_into_chunks
from pathlib import Path

# ----------------------------------------------------------------------------------------------------------


async def display_validation_results(validation_results: dict, page: ft.Page):
    """Display file validation results to the user."""
    if not validation_results:
        return
    
    # Display encoding detection results
    encoding_info = validation_results.get('encoding_detection', {})
    if encoding_info:
        detected_encoding = encoding_info.get('detected_encoding', 'unknown')
        confidence = encoding_info.get('confidence', 0)
        if confidence > 0.7:
            await write_output(f"[Auto-Detection] Encoding: {detected_encoding} (confidence: {confidence:.1%})", page)
        else:
            await write_output(f"[Auto-Detection] Encoding: {detected_encoding} (low confidence: {confidence:.1%})", page)
    
    # Display delimiter detection results
    delimiter_info = validation_results.get('delimiter_detection', {})
    if delimiter_info:
        detected_delimiter = delimiter_info.get('detected_delimiter', 'unknown')
        confidence = delimiter_info.get('confidence', 0)
        delimiter_display = repr(detected_delimiter) if detected_delimiter else 'unknown'
        method = delimiter_info.get('method', 'unknown')
        await write_output(f"[Auto-Detection] Delimiter: {delimiter_display} via {method} (confidence: {confidence:.1%})", page)
    
    # Display file size warnings
    size_info = validation_results.get('size_validation', {})
    if size_info and size_info.get('level') in ['WARNING', 'ERROR']:
        await write_output(f"[File Size] {size_info.get('message', '')}", page)
    
    # Display memory warnings
    memory_info = validation_results.get('memory_estimation', {})
    if memory_info:
        file_size = memory_info.get('file_size_mb', 0)
        estimated_memory = memory_info.get('estimated_memory_mb', 0)
        recommendation = memory_info.get('recommendation', 'UNKNOWN')
        
        if recommendation in ['HIGH_RISK', 'MEDIUM_RISK']:
            await write_output(f"[Memory Warning] File: {file_size:.1f}MB, Estimated RAM: {estimated_memory:.1f}MB", page)
            await write_output(f"[Memory Warning] {memory_info.get('warning_message', '')}", page)
        else:
            await write_output(f"[Memory Check] File: {file_size:.1f}MB, Estimated RAM: {estimated_memory:.1f}MB - OK", page)
    
    # Display overall warnings
    overall = validation_results.get('overall_assessment', {})
    warnings = overall.get('warnings', [])
    if warnings:
        for warning in warnings:
            await write_output(f"[Validation Warning] {warning}", page)
    
    # Display final data info
    final_info = validation_results.get('final_data_info', {})
    if final_info:
        rows = final_info.get('rows', 0)
        cols = final_info.get('columns', 0)
        memory_used = final_info.get('memory_usage_mb', 0)
        encoding_used = final_info.get('encoding_used', 'unknown')
        delimiter_used = final_info.get('delimiter_used', 'unknown')
        
        await write_output(f"[Load Success] {rows:,} rows × {cols} columns, {memory_used:.1f}MB RAM", page)
        if encoding_used != 'unknown':
            await write_output(f"[Load Success] Using encoding: {encoding_used}", page)
        if delimiter_used and delimiter_used != 'unknown':
            delimiter_display = repr(delimiter_used)
            await write_output(f"[Load Success] Using delimiter: {delimiter_display}", page)


async def show_size_warning(file_info: dict, page: ft.Page):
    """Show file size warning dialog."""
    if not file_info or file_info.get('level') != 'WARNING':
        return
    
    dlg = ft.AlertDialog(
        title=ft.Text("Large File Warning"),
        content=ft.Text(f"{file_info.get('message', '')}\n\nDo you want to continue?"),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
            ft.TextButton("Continue", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
        ],
    )
    page.dialog = dlg
    dlg.open = True
    page.update()


async def show_memory_warning(memory_info: dict, page: ft.Page):
    """Show memory usage warning dialog."""
    if not memory_info or memory_info.get('recommendation') not in ['HIGH_RISK', 'MEDIUM_RISK']:
        return
    
    estimated_mb = memory_info.get('estimated_memory_mb', 0)
    available_mb = memory_info.get('available_memory_mb', 0)
    warning_msg = memory_info.get('warning_message', '')
    
    dlg = ft.AlertDialog(
        title=ft.Text("Memory Usage Warning"),
        content=ft.Text(
            f"Estimated memory usage: {estimated_mb:.1f}MB\n"
            f"Available memory: {available_mb:.1f}MB\n\n"
            f"{warning_msg}\n\n"
            f"Do you want to continue loading?"
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
            ft.TextButton("Continue", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
        ],
    )
    page.dialog = dlg
    dlg.open = True
    page.update()


async def load_data_result(e: ft.FilePickerResultEvent):
    """Handle data selection and load the chosen file asynchronously."""
    global current_df, data_loaded, app_busy
    page = e.page

    if e.files:
        file_path = e.files[0].path
        save_filepath(file_path)  # ← store the real string path
        dialog_controls["loaded_file"] = file_path

        # 1. Get dataset name from file
        dataset_name = Path(file_path).stem

        # Indicate busy state
        app_busy = True

        # 2. Create environment folders for this dataset
        project_paths = create_dataset_environment(dataset_name)
        await write_output(
            f"[Environment] Folders created at: {project_paths['project']}", page
        )

        # 3. Show status
        dialog_controls["status_label"].value = "Working..."
        dialog_controls["status_label"].color = ft.Colors.AMBER
        page.update()
        await asyncio.sleep(0.1)

        loop = asyncio.get_running_loop()

        def progress_cb(p, m):
            asyncio.run_coroutine_threadsafe(update_progress(p, m, page), loop)

        await show_progress(True, page)

        result = await asyncio.to_thread(
            load_data,
            file_path,
            progress_cb,
            dialog_controls.get("encoding", "auto"),
            dialog_controls.get("delimiter"),
        )
        
        # Handle the new tuple return (df, validation_results)
        if isinstance(result, tuple):
            df, validation_results = result
            current_df = df
            
            # Display validation results
            await display_validation_results(validation_results, page)
        else:
            # Backward compatibility - treat as just DataFrame
            df = result
            current_df = df
            validation_results = {}

        await show_progress(False, page)

        if df is None:
            await write_output("[Error] Failed to load dataset.", page)
            show_error("Failed to load dataset", page)
            await reset_app_state(page)
            return

        cd = dialog_controls["column_dropdown"]
        options = [ft.dropdown.Option("All Columns")] + [
            ft.dropdown.Option(c) for c in current_df.columns
        ]
        cd.options = options
        cd.value = "All Columns"
        sc = dialog_controls.get("search_column")
        if sc:
            sc.options = options
            sc.value = "All Columns"
        page.update()

        info = get_data_stats(df, file_path)
        await write_output(info["log1"], page)
        await write_output(info["log2"], page)

        # Update the data table with loaded data using pagination
        update_data_table(df, page)
        
        if len(df) > dialog_controls.get("rows_per_page", 25):
            await write_output(f"[Info] Dataset has {len(df)} rows. Using pagination for display.", page)

        # 4. Toggle buttons now that loading succeeded
        data_loaded = True
        dialog_controls["btn_log"].disabled = False
        dialog_controls["btn_data"].disabled = False
        dialog_controls["btn_visual"].disabled = False
        dialog_controls["btn_dataview"].disabled = False
        dialog_controls["status_label"].value = "Ready"
        dialog_controls["status_label"].color = ft.Colors.GREEN
        dialog_controls["status_label"].weight = ft.FontWeight.BOLD
        app_busy = False

    else:
        await write_output("[Load Data] No file selected.", page)
        dialog_controls["status_label"].value = "Ready"
        dialog_controls["status_label"].color = ft.Colors.RED
        app_busy = False

    page.update()


def handle_file_result(e: ft.FilePickerResultEvent):
    if e.files:
        selected_file = e.files[0].path
        dialog_controls["status_label"].value = f"Loaded: {selected_file}"
        dialog_controls["status_label"].color = ft.Colors.GREEN


async def load_data_handler(e: ft.ControlEvent):
    page = e.page
    dialog_controls["status_label"].value = "Waiting..."
    dialog_controls["status_label"].color = ft.Colors.ORANGE

    # ✅ Make sure the file_picker is set up *before* calling pick_files
    if dialog_controls["file_picker"] is None:
        dialog_controls["file_picker"] = ft.FilePicker(on_result=load_data_result)
        page.overlay.append(
            dialog_controls["file_picker"]
        )  # required for FilePicker to work

    page.update()
    dialog_controls["file_picker"].pick_files(
        allow_multiple=False,
        allowed_extensions=["csv", "xlsx", "xls", "txt"],
    )


async def chunk_csv_handler(e: ft.ControlEvent):

    try:
        if not save_filepath:
            await write_output("[Error] No file loaded to chunk.", e.page)
            return

        dataset_name = Path(save_filepath).stem
        paths = create_dataset_environment(dataset_name)
        chunks_dir = str(paths["chunks"])

        await write_output(f"[GUI] Chunking started: {save_filepath}", e.page)

        split_into_chunks(save_filepath, chunks_dir, chunk_size_mb=256)

        await write_output(
            f"[GUI] ✅ Chunking complete. Files saved in:\n{chunks_dir}", e.page
        )

    except Exception as ex:
        await write_output(f"[Error] Failed to chunk file: {ex}", e.page)
        show_error(f"Chunking failed: {ex}", e.page)


async def handle_chunk_button(e: ft.ControlEvent):
    """Handle the click event for the CSV chunking button.

    This routine validates the input, spawns the CSV splitting process on
    a background thread and updates the UI with progress information.
    """
    global app_busy
    page = e.page

    file_path = data_handler.saved_filepath  # ✅ get latest saved path

    if not file_path or not isinstance(file_path, (str, Path)):
        dialog_controls["chunk_status"].value = "Please load a file first."
        page.update()
        return

    dataset_name = Path(file_path).stem

    try:
        chunk_size = int(dialog_controls["chunk_size_input"].value)
    except ValueError:
        dialog_controls["chunk_status"].value = (
            "Please enter a valid number for chunk size."
        )
        page.update()
        return

    dialog_controls["chunk_status"].value = "Chunking in progress..."
    app_busy = True
    page.update()

    loop = asyncio.get_running_loop()

    def progress_cb(p, m):
        asyncio.run_coroutine_threadsafe(update_progress(p, m, page), loop)

    await show_progress(True, page)

    result = await asyncio.to_thread(
        split_into_chunks,
        dataset_name,
        file_path,
        chunk_size_mb=chunk_size,
        logger_fn=lambda msg: print(msg),
        progress_fn=progress_cb,
    )

    await show_progress(False, page)

    if result and result["total_chunks"] > 0:
        dialog_controls["chunk_status"].value = (
            f"Chunked {result['total_rows']} rows into {result['total_chunks']} files."
        )
    else:
        dialog_controls["chunk_status"].value = "Chunking failed. See logs."

    app_busy = False
    page.update()


async def on_chunk_csv(e: ft.ControlEvent):
    """Launch CSV chunking using the size stored on the page object."""
    page = e.page
    chunk_size = getattr(page, "chunk_size", CHUNK_SIZE_DEFAULT)
    dialog_controls["chunk_size_input"].value = str(chunk_size)
    print(f"[GUI] Chunk CSV requested with {chunk_size} MB")
    logging.info("Chunk CSV requested with %s MB", chunk_size)
    await handle_chunk_button(e)


def convert_file_result(e: ft.FilePickerResultEvent):
    """Store the file selected for conversion and update the display."""
    global convert_input_path
    if e.files:
        convert_input_path = e.files[0].path
        dialog_controls["convert_file_display"].value = convert_input_path
    else:
        convert_input_path = None
        dialog_controls["convert_file_display"].value = "No file selected"
    e.page.update()


def convert_dir_result(e: ft.FilePickerResultEvent):
    """Store the output directory chosen for conversion."""
    global convert_output_dir
    if e.path:
        convert_output_dir = e.path
        dialog_controls["convert_dir_display"].value = convert_output_dir
    else:
        convert_output_dir = None
        dialog_controls["convert_dir_display"].value = "No folder selected"
    e.page.update()


async def on_convert_file(e: ft.ControlEvent):
    """Convert the selected file using the chosen format."""
    global app_busy
    page = e.page

    if not convert_input_path or not convert_output_dir:
        dialog_controls["convert_status"].value = "Select input file and folder."
        page.update()
        return

    dialog_controls["convert_status"].value = "Converting..."
    app_busy = True
    page.update()

    try:
        loop = asyncio.get_running_loop()

        def progress_cb(p, m):
            asyncio.run_coroutine_threadsafe(update_progress(p, m, page), loop)

        await show_progress(True, page)

        output_file = await asyncio.to_thread(
            convert_file,
            convert_input_path,
            convert_output_dir,
            dialog_controls.get("convert_format", "csv"),
            progress_cb,
        )
        dialog_controls["convert_status"].value = f"Saved to {output_file}"
        await show_progress(False, page)
    except Exception as ex:
        dialog_controls["convert_status"].value = f"Error: {ex}"
        show_error(f"Conversion failed: {ex}", page)
        await show_progress(False, page)

    app_busy = False
    page.update()


# FILE HANDLER BLOCK END----------------------------------------------------------------------------------------
# SEAN FEATURE BUILDOUT BLOCK-----------------------------------------------------------------


async def analysis_handler(e: ft.ControlEvent):
    global app_busy
    page = e.page

    if not data_loaded:
        await write_output("[Error] Load data first.", page)
        return

    # Pull the widgets out of dialog_controls
    ad = dialog_controls["analysis_dropdown"]
    cd = dialog_controls["column_dropdown"]
    ri = dialog_controls["rows_input"]
    ss = dialog_controls["sort_switch"]

    # Read their values
    atype = ad.value
    col = cd.value if cd.value != "All Columns" else None

    try:
        num = int(ri.value)
    except ValueError:
        await write_output("[Error] Rows must be an integer.", page)
        return

    desc = ss.value

    # Run the analysis on a background thread
    app_busy = True
    result = await asyncio.to_thread(run_analysis, current_df, atype, col, num, desc)
    dialog_controls["analysis_text"] = result
    await write_output(result, page)
    
    # Switch to Data View tab when running analysis
    focus_dataview_tab(page)
    
    # If analysis returns tabular data, show it in the data table
    if atype in ["Data Preview", "Missing Values", "Duplicate Detection", "Special Character Analysis", "Placeholder Detection"]:
        if atype == "Data Preview":
            # Show preview of the data
            preview_df = current_df.head(num) if not desc else current_df.tail(num)
            if col and col != "All Columns":
                preview_df = preview_df[[col]]
            update_data_table(preview_df, page)
        elif atype == "Missing Values":
            # Show missing values summary as a table
            missing_data = {
                'Column': current_df.columns.tolist(),
                'Missing Count': [current_df[col].isnull().sum() for col in current_df.columns],
                'Missing Percentage': [round((current_df[col].isnull().sum() / len(current_df)) * 100, 2) for col in current_df.columns],
                'Total Count': [len(current_df) for _ in current_df.columns],
                'Non-Missing Count': [current_df[col].count() for col in current_df.columns]
            }
            missing_df = pd.DataFrame(missing_data)
            # Sort by missing count if requested
            if desc:
                missing_df = missing_df.sort_values('Missing Count', ascending=False)
            update_data_table(missing_df, page)
        elif atype == "Placeholder Detection":
            # Show placeholder detection as a table
            placeholders = ['N/A', 'NULL', 'null', 'None', 'none', 'nan', 'NaN', '-', '?', 'Unknown', 'unknown', '']
            placeholder_data = []
            for column in current_df.columns:
                if current_df[column].dtype == 'object':  # Only analyze text columns
                    placeholder_count = 0
                    found_placeholders = []
                    for placeholder in placeholders:
                        count = (current_df[column].astype(str) == placeholder).sum()
                        if count > 0:
                            placeholder_count += count
                            found_placeholders.append(f"{placeholder} ({count})")
                    
                    placeholder_data.append({
                        'Column': column,
                        'Placeholder Count': placeholder_count,
                        'Placeholders Found': ', '.join(found_placeholders),
                        'Percentage': round((placeholder_count / len(current_df)) * 100, 2) if len(current_df) > 0 else 0
                    })
            
            if placeholder_data:
                placeholder_df = pd.DataFrame(placeholder_data)
                if desc:
                    placeholder_df = placeholder_df.sort_values('Placeholder Count', ascending=False)
                update_data_table(placeholder_df, page)
        elif atype == "Special Character Analysis":
            # Show special character analysis as a table with ASCII and Non-ASCII breakdown
            import pandas as pd
            char_data = []
            for column in current_df.columns:
                if current_df[column].dtype == 'object':  # Only analyze text columns
                    # Get all text from this column
                    all_text = ' '.join(current_df[column].astype(str).tolist())
                    
                    # Separate ASCII and Non-ASCII special characters
                    ascii_special = []
                    non_ascii_special = []
                    
                    for char in set(all_text):
                        if not char.isalnum() and not char.isspace():
                            if ord(char) < 128:  # ASCII range
                                ascii_special.append(char)
                            else:  # Non-ASCII
                                non_ascii_special.append(char)
                    
                    # Count total special characters
                    total_special = len(ascii_special) + len(non_ascii_special)
                    
                    # Get counts of each character type in the actual data
                    ascii_count = sum(all_text.count(char) for char in ascii_special)
                    non_ascii_count = sum(all_text.count(char) for char in non_ascii_special)
                    
                    char_data.append({
                        'Column': column,
                        'Total Special Chars': total_special,
                        'ASCII Special Count': len(ascii_special),
                        'Non-ASCII Count': len(non_ascii_special),
                        'ASCII Characters': ''.join(sorted(ascii_special)),
                        'Non-ASCII Characters': ''.join(sorted(non_ascii_special)),
                        'ASCII Frequency': ascii_count,
                        'Non-ASCII Frequency': non_ascii_count
                    })
            
            if char_data:
                char_df = pd.DataFrame(char_data)
                if desc:
                    char_df = char_df.sort_values('Total Special Chars', ascending=False)
                update_data_table(char_df, page)
        elif atype == "Duplicate Detection":
            # Show duplicate rows
            duplicates = current_df[current_df.duplicated(keep=False)]
            if not duplicates.empty:
                update_data_table(duplicates, page)
    
    app_busy = False


async def show_search_result(page: ft.Page):
    """Display the current search result in the console and data table."""
    results = dialog_controls.get("search_results")
    if not results:
        return
    idx = dialog_controls.get("search_index", 0)
    row = current_df.iloc[[results[idx]]]
    await write_output(row.to_string(index=False), page)
    dialog_controls["match_label"].value = f"{idx+1}/{len(results)}"
    
    # Show the search result row in the data table
    update_data_table(row, page)
    page.update()


async def on_search(e: ft.ControlEvent):
    """Execute a DataFrame search based on UI selections."""
    if current_df is None:
        show_error("Load data before searching", e.page)
        return

    term = dialog_controls["search_term"].value
    col_value = dialog_controls["search_column"].value
    column = None if col_value == "All Columns" else col_value
    case = dialog_controls["case_switch"].value
    whole = dialog_controls["whole_switch"].value

    if not term:
        await write_output("Enter a search term.", e.page)
        return

    results = search_dataframe(current_df, term, column, case, whole)
    dialog_controls["search_results"] = results
    dialog_controls["search_index"] = 0

    if not results:
        await write_output("No matches found.", e.page)
        dialog_controls["match_label"].value = "0/0"
        # Show all data without highlighting
        update_data_table(current_df, e.page)
        return

    # Show all search results in the data table with highlighting
    search_results_df = current_df.iloc[results]
    
    # Apply highlighting to the search results with pagination
    highlight_col = column if column != "All Columns" else None
    update_data_table(search_results_df, e.page, highlight_term=term, highlight_column=highlight_col)
    
    await write_output(f"Found {len(results)} matches for '{term}'", e.page)
    dialog_controls["match_label"].value = f"{len(results)} matches found"


async def on_prev_match(e: ft.ControlEvent):
    results = dialog_controls.get("search_results")
    if not results:
        return
    dialog_controls["search_index"] = (dialog_controls["search_index"] - 1) % len(results)
    await show_search_result(e.page)


async def on_next_match(e: ft.ControlEvent):
    results = dialog_controls.get("search_results")
    if not results:
        return
    dialog_controls["search_index"] = (dialog_controls["search_index"] + 1) % len(results)
    await show_search_result(e.page)


async def clear_search_handler(e: ft.ControlEvent):
    """Clear search results and show all data."""
    dialog_controls["search_results"] = None
    dialog_controls["search_index"] = 0
    dialog_controls["search_term"].value = ""
    dialog_controls["match_label"].value = "0/0"
    
    if current_df is not None:
        # Show all data without highlighting, with pagination
        update_data_table(current_df, e.page)
    
    await write_output("Search cleared.", e.page)
    e.page.update()


def export_picker_result(e: ft.FilePickerResultEvent):
    """Handle path selection from the export file picker."""
    global export_context
    if not e.path:
        return
    try:
        if export_context == "dataset" and current_df is not None:
            export_dataframe(current_df, e.path, dialog_controls.get("export_format", "csv"))
        elif export_context == "search" and dialog_controls.get("search_results"):
            df = current_df.iloc[dialog_controls["search_results"]]
            export_dataframe(df, e.path, dialog_controls.get("export_format", "csv"))
        elif export_context == "analysis":
            export_text(dialog_controls.get("analysis_text", ""), e.path)
        dialog_controls["status_label"].value = f"Saved: {e.path}"
    except Exception as ex:
        show_error(str(ex), e.page)
    finally:
        export_context = None
        e.page.update()


def export_dataset(e: ft.ControlEvent):
    global export_context
    export_context = "dataset"
    dialog_controls["export_picker"].save_file()


def export_search_results(e: ft.ControlEvent):
    if not dialog_controls.get("search_results"):
        show_error("Run a search first", e.page)
        return
    global export_context
    export_context = "search"
    dialog_controls["export_picker"].save_file()


def export_analysis_text(e: ft.ControlEvent):
    if not dialog_controls.get("analysis_text"):
        show_error("Run analysis first", e.page)
        return
    global export_context
    export_context = "analysis"
    dialog_controls["export_picker"].save_file()


# SEAN FEATURE BUILDOUT BLOCK END------------------------------------------------------------
def build_advanced_content() -> ft.Column:
    """Construct the Advanced tools tab and make it scrollable.

    The Advanced tools tab contains many widgets. Automatic scrolling allows
    all controls to remain accessible regardless of screen size.
    """

    logging.info("Building Advanced tools UI")
    print("[GUI] Building Advanced tools UI")

    advanced_content = ft.Column(
        [
            ft.Text("Analysis", style="titleMedium"),
            dialog_controls.get("analysis_dropdown"),
            dialog_controls.get("desc_text"),
            dialog_controls.get("column_dropdown"),
            ft.Row(
                [
                    dialog_controls.get("rows_input"),
                    dialog_controls.get("sort_switch"),
                ],
                spacing=20,
            ),
            dialog_controls.get("run_btn"),
            ft.Divider(),
            ft.Text("Load Options", weight=ft.FontWeight.BOLD),
            ft.Row([dialog_controls.get("enc_dropdown"), dialog_controls.get("delim_dropdown")], spacing=10),
            ft.Text("💡 Auto-detection analyzes your files for optimal settings", 
                   size=11, color=ft.Colors.BLUE_GREY_600, italic=True),
            ft.Divider(),
            ft.Text("Export", style="titleMedium"),
            ft.Row([dialog_controls.get("export_fmt"), dialog_controls.get("export_ds_btn")], spacing=10),
            ft.Row([dialog_controls.get("export_search_btn"), dialog_controls.get("export_analysis_btn")], spacing=10),
        ],
        spacing=10,
        alignment=ft.MainAxisAlignment.START,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    return advanced_content


# Synchronous theme toggle handler to avoid threading issues
def on_theme_toggle(e: ft.ControlEvent):
    page = e.page
    dark_mode = e.control.value
    global current_theme_mode

    # Define your light and dark seeds
    light_seed = "#00FF7F"  # Tech Green for Light Theme
    dark_seed = "#1E90FF"   # Tech Blue for Dark Theme

    # Apply theme mode
    page.theme_mode = ft.ThemeMode.DARK if dark_mode else ft.ThemeMode.LIGHT
    current_theme_mode = page.theme_mode

    # Set theme based on the selected mode
    if dark_mode:
        page.dark_theme = ft.Theme(color_scheme_seed=dark_seed)
    else:
        page.theme = ft.Theme(color_scheme_seed=light_seed)

    # Always update data table colors when theme changes
    apply_data_table_theme(page)

    save_theme_preference(dark_mode)
    page.update()



async def main(page: ft.Page):
    """Primary entry point for the Flet UI."""
    global data_loaded

    # Window appearance and behavior
    page.window.frameless = True
    page.window.title_bar_hidden = True
    page.window.resizable = True
    page.vertical_alignment = ft.CrossAxisAlignment.START

    # Window size
    page.window.width = 700
    page.window.height = 640

    # Center the window on screen
    page.window.center()

    # Set app metadata
    page.title = "Protexxa Datascope - Alpha"
    # Load saved theme preference
    dark_mode_enabled = load_theme_preference()
    page.theme_mode = ft.ThemeMode.DARK if dark_mode_enabled else ft.ThemeMode.LIGHT

    page.window.icon = "favicon.ico"

    # Default chunk size stored on page for reuse in handlers
    page.chunk_size = CHUNK_SIZE_DEFAULT

    page.update()

    # Start background task to flash the logo when busy
    asyncio.create_task(flash_logo(page))

    # FilePicker
    dialog_controls["file_picker"] = ft.FilePicker(on_result=load_data_result)
    page.overlay.append(dialog_controls["file_picker"])

    dialog_controls["convert_file_picker"] = ft.FilePicker(
        on_result=convert_file_result
    )
    page.overlay.append(dialog_controls["convert_file_picker"])

    dialog_controls["convert_dir_picker"] = ft.FilePicker(on_result=convert_dir_result)
    page.overlay.append(dialog_controls["convert_dir_picker"])

    dialog_controls["export_picker"] = ft.FilePicker(on_result=export_picker_result)
    page.overlay.append(dialog_controls["export_picker"])

    # Theme toggle switch
    dialog_controls["theme_switch"] = ft.Switch(
        label="Dark Mode", value=dark_mode_enabled, on_change=on_theme_toggle
    )

    # Frameless Splash screen
    splash_content = ft.Column(
        [
            ft.Text(
                "PROPERTY OF",
                font_family="Helvetica",
                size=10,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
            ),
            ft.Image(
                src="protexxa-logo.png",
                width=156,
                height=61,
                fit=ft.ImageFit.CONTAIN,
                error_content=ft.Text("Logo not found", color=ft.Colors.RED),
            ),
            ft.Text(
                "13.1°N 59.32°W → 43° 39' 11.6136'' N 79° 22' 59.4624'' W\n"
                "AICohort01: The Intelligence Migration\n"
                "Data Cleaning Division",
                font_family="Helvetica",
                size=10,
                color=ft.Colors.WHITE,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,  # <--- vertical centering
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # <--- horizontal centering
        expand=True,
    )
    splash_container = ft.Container(
        content=splash_content,
        expand=True,
        bgcolor="#1e1e2f",
        alignment=ft.alignment.center,
        on_click=on_splash_click,
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        opacity=1.0,
    )
    dialog_controls["splash_container"] = splash_container

    page.add(splash_container)
    page.update()
    await asyncio.sleep(1)  # SPLASH SCREEN DELAY (CURRENTLY 1 SECOND FOR TESTING)
    await transition_to_gui(page)


def on_splash_click(e: ft.ControlEvent):
    """Handle splash screen click by transitioning to GUI."""
    asyncio.create_task(transition_to_gui(e.page))


async def transition_to_gui(page: ft.Page):
    # 1) Fade out splash screen
    splash = dialog_controls.get("splash_container")
    if splash:
        splash.opacity = 0
        page.update()
        await asyncio.sleep(0.3)

    # 2) Restore window chrome & clear splash
    page.window.frameless = False
    page.window.title_bar_hidden = False
    page.controls.clear()
    page.update()

    # 2) Header
    logo_ref = ft.Ref[ft.Image]()
    logo_img = ft.Image(
        src="protexxa_logo_cropped.png",
        width=40,
        height=40,
        fit=ft.ImageFit.CONTAIN,
        error_content=ft.Text("Logo missing", color=ft.Colors.RED),
        ref=logo_ref,
    )
    header = ft.WindowDragArea(
        content=ft.Row(
            controls=[
                ft.Text(
                    "Protexxa Datascope - 1.2",
                    font_family="Arial",
                    size=20,
                    weight=ft.FontWeight.NORMAL,
                ),
                logo_img,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            width=800,
        )
    )

    dialog_controls["logo_image"] = logo_ref

    # 3) Console & File‑ops UI (must come before Tabs)
    dialog_controls["output_text_field"] = ft.TextField(
        multiline=True,
        read_only=True,
        min_lines=20,
        max_lines=20,
        width=700,
        height=300,
        border_radius=20,
        border_color=ft.Colors.BLUE_GREY_200,
        content_padding=10,
        value="",
    )
    dialog_controls["progress_bar"] = ft.ProgressBar(
        width=700,
        height=10,
        bgcolor=ft.Colors.GREY_300,
        color=ft.Colors.BLUE,
        value=0,
        visible=False,
    )
    dialog_controls["progress_text"] = ft.Text(
        value="",
        size=12,
        color=ft.Colors.BLUE,
        text_align=ft.TextAlign.CENTER,
        visible=False,
        weight=ft.FontWeight.BOLD,
    )

    # load / test buttons
    btn_load = ft.ElevatedButton(
        text="Load Data",
        on_click=load_data_handler,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    dialog_controls["btn_log"] = ft.ElevatedButton(
        text="Test Logging",
        on_click=logging_handler_test,
        disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    dialog_controls["btn_data"] = ft.ElevatedButton(
        text="Test Data Handling",
        on_click=data_handler_test,
        disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    dialog_controls["btn_visual"] = ft.ElevatedButton(
        text="Test Visual Analyst",
        on_click=visual_analyst_test,
        disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    
    # Add a button to manually switch to Data View for testing
    btn_dataview = ft.ElevatedButton(
        text="View Data Table",
        on_click=lambda e: focus_dataview_tab(e.page),
        disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    dialog_controls["btn_dataview"] = btn_dataview
    
    button_row = ft.Row(
        controls=[
            btn_load,
            dialog_controls["btn_log"],
            dialog_controls["btn_data"],
            dialog_controls["btn_visual"],
            dialog_controls["btn_dataview"],
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=10,
    )

    file_ops_frame = ft.Container(
        content=ft.Column(
            [ft.Text("(File save buttons will go here)", color=ft.Colors.GREY_600)]
        ),
        border_radius=10,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
        padding=10,
        width=700,
    )

    dialog_controls["status_label"] = ft.Text("Ready", color=ft.Colors.BLUE)

    # 4) Advanced Tab Widgets (SEAN FEATURE BUILDOUT)
    analysis_help = {
        "Data Preview": "Show sample rows and types.",
        "Missing Values": "Report null counts.",
        "Duplicate Detection": "Find duplicated rows.",
        "Placeholder Detection": "Check for placeholder tokens.",
        "Special Character Analysis": "Analyze ASCII and Non-ASCII special characters with frequencies.",
    }

    desc_text = ft.Text(value="", size=12, color=ft.Colors.BLUE_GREY_600)
    dialog_controls["desc_text"] = desc_text

    def on_analysis_change(e: ft.ControlEvent):
        desc_text.value = analysis_help.get(e.control.value, "")
        e.page.update()

    analysis_dropdown = ft.Dropdown(
        label="Analysis Type",
        width=200,
        options=[
            ft.dropdown.Option("Data Preview"),
            ft.dropdown.Option("Missing Values"),
            ft.dropdown.Option("Duplicate Detection"),
            ft.dropdown.Option("Placeholder Detection"),
            ft.dropdown.Option("Special Character Analysis"),
        ],
        on_change=on_analysis_change,
        tooltip="Choose analysis to run",
    )
    column_dropdown = ft.Dropdown(
        label="Column", width=200, options=[ft.dropdown.Option("All Columns")]
    )
    rows_input = ft.TextField(label="Rows to show", value="10", width=100)
    sort_switch = ft.Switch(label="Descending order", value=False)
    run_btn = ft.ElevatedButton("Run Analysis", on_click=analysis_handler)

    # stash for the handler
    dialog_controls["analysis_dropdown"] = analysis_dropdown
    dialog_controls["column_dropdown"] = column_dropdown
    dialog_controls["rows_input"] = rows_input
    dialog_controls["sort_switch"] = sort_switch
    dialog_controls["run_btn"] = run_btn
    dialog_controls["match_label"] = ft.Text("0/0")

    enc_dropdown = ft.Dropdown(
        label="Encoding",
        width=120,
        value="auto",
        options=[
            ft.dropdown.Option("auto", "Auto-Detect"),
            ft.dropdown.Option("utf-8"),
            ft.dropdown.Option("latin1"),
            ft.dropdown.Option("utf-16"),
            ft.dropdown.Option("cp1252"),
        ],
        on_change=lambda e: dialog_controls.__setitem__("encoding", e.control.value),
        tooltip="File encoding (Auto-Detect recommended)",
    )
    dialog_controls["enc_dropdown"] = enc_dropdown

    def on_delim_change(e: ft.ControlEvent):
        dialog_controls["delimiter"] = None if e.control.value == "Auto" else e.control.value

    delim_dropdown = ft.Dropdown(
        label="Delimiter",
        width=120,
        value="Auto",
        options=[
            ft.dropdown.Option("Auto"),
            ft.dropdown.Option(","),
            ft.dropdown.Option("\t"),
            ft.dropdown.Option(";"),
            ft.dropdown.Option("|"),
        ],
        on_change=on_delim_change,
        tooltip="Field delimiter",
    )
    dialog_controls["delim_dropdown"] = delim_dropdown

    search_term = ft.TextField(
        label="Search term", 
        width=200, 
        tooltip="Enter text to search (press Enter to search)",
        on_submit=on_search,  # Allow search on Enter key
    )
    search_column = ft.Dropdown(label="Search Column", width=150, options=[ft.dropdown.Option("All Columns")])
    case_switch = ft.Switch(label="Case", value=False)
    whole_switch = ft.Switch(label="Whole", value=False)
    search_btn = ft.ElevatedButton(text="Search", on_click=on_search)
    prev_btn = ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=on_prev_match, tooltip="Previous")
    next_btn = ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=on_next_match, tooltip="Next")

    dialog_controls["search_term"] = search_term
    dialog_controls["search_column"] = search_column
    dialog_controls["case_switch"] = case_switch
    dialog_controls["whole_switch"] = whole_switch
    dialog_controls["search_btn"] = search_btn
    dialog_controls["prev_btn"] = prev_btn
    dialog_controls["next_btn"] = next_btn

    export_fmt = ft.Dropdown(
        label="Format",
        width=120,
        value="csv",
        options=[ft.dropdown.Option("csv"), ft.dropdown.Option("xlsx")],
        on_change=lambda e: dialog_controls.__setitem__("export_format", e.control.value),
    )
    dialog_controls["export_fmt"] = export_fmt
    export_ds_btn = ft.ElevatedButton("Export Dataset", on_click=export_dataset, tooltip="Save full dataset")
    export_search_btn = ft.ElevatedButton("Export Search", on_click=export_search_results, tooltip="Save search matches")
    export_analysis_btn = ft.ElevatedButton("Export Analysis", on_click=export_analysis_text, tooltip="Save last analysis")

    dialog_controls["export_ds_btn"] = export_ds_btn
    dialog_controls["export_search_btn"] = export_search_btn
    dialog_controls["export_analysis_btn"] = export_analysis_btn
    
    # Create scrollable Advanced tools tab content
    advanced_content = build_advanced_content()

    # 5) Build Tabs in one shot
    dialog_controls["chunk_size_input"] = ft.TextField(
        label="Chunk size (MB)",
        width=200,
        value=str(page.chunk_size),
        on_change=lambda e: setattr(page, "chunk_size", int(e.control.value)),
    )
    dialog_controls["chunk_status"] = ft.Text(value="", color=ft.Colors.GREY_700)

    csv_chunker_card = ft.Card(
        elevation=3,
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("CSV Chunker", style="headlineSmall"),
                    ft.Row(
                        [
                            dialog_controls["chunk_size_input"],
                            ft.ElevatedButton(
                                text="Chunk CSV",
                                icon=SPLIT_CSV_ICON,
                                on_click=on_chunk_csv,
                            ),
                        ],
                        spacing=16,
                        alignment="start",
                    ),
                ]
            ),
        ),
    )

    dialog_controls["convert_status"] = ft.Text(value="", color=ft.Colors.GREY_700)
    dialog_controls["convert_file_display"] = ft.Text(
        "No file selected", color=ft.Colors.GREY_700
    )
    dialog_controls["convert_dir_display"] = ft.Text(
        "No folder selected", color=ft.Colors.GREY_700
    )

    convert_card = ft.Card(
        elevation=3,
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("File Converter", style="headlineSmall"),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                text="Select File",
                                # Using ``ft.Icons`` because ``ft`` exposes icons via this enumeration
                                # rather than ``ft.icons`` which does not exist.
                                icon=ft.Icons.UPLOAD_FILE,
                                on_click=lambda e: dialog_controls[
                                    "convert_file_picker"
                                ].pick_files(allow_multiple=False),
                            ),
                            dialog_controls["convert_file_display"],
                        ],
                        spacing=16,
                        alignment="start",
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                text="Choose Folder",
                                # Replace ``ft.icons`` with ``ft.Icons`` to prevent attribute errors
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=lambda e: dialog_controls[
                                    "convert_dir_picker"
                                ].get_directory_path(),
                            ),
                            dialog_controls["convert_dir_display"],
                        ],
                        spacing=16,
                        alignment="start",
                    ),
                    ft.Row(
                        [
                            ft.Dropdown(
                                width=100,
                                value="csv",
                                options=[ft.dropdown.Option("csv"), ft.dropdown.Option("xlsx")],
                                on_change=lambda e: dialog_controls.__setitem__("convert_format", e.control.value),
                                tooltip="Output format",
                            ),
                            ft.ElevatedButton(
                                text="Convert",
                                icon=ft.Icons.DOWNLOAD,
                                on_click=on_convert_file,
                            ),
                        ],
                        spacing=10,
                    ),
                    dialog_controls["convert_status"],
                ]
            ),
        ),
    )

    # Create the Data View tab controls
    dialog_controls["data_table"] = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("No Data"))],  # Default column to avoid error
        rows=[],
        border=ft.border.all(1, ft.Colors.GREY_400),
        border_radius=10,
        vertical_lines=ft.BorderSide(1, ft.Colors.GREY_300),
        horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_300),
        heading_row_color=ft.Colors.GREY_100,
        heading_row_height=50,
        data_row_min_height=30,
        data_row_max_height=60,
        show_checkbox_column=False,
        bgcolor=ft.Colors.WHITE,  # Ensure background is white
        column_spacing=20,  # Add spacing between columns
        horizontal_margin=10,  # Add horizontal margin
    )
    
    dialog_controls["data_table_info"] = ft.Text(
        "No data loaded",
        color=ft.Colors.GREY_600,
        size=12
    )

    # Create pagination controls
    dialog_controls["prev_page_btn"] = ft.IconButton(
        icon=ft.Icons.ARROW_BACK,
        tooltip="Previous page",
        on_click=on_prev_page,
        disabled=True,
    )
    
    dialog_controls["next_page_btn"] = ft.IconButton(
        icon=ft.Icons.ARROW_FORWARD,
        tooltip="Next page",
        on_click=on_next_page,
        disabled=True,
    )
    
    dialog_controls["first_page_btn"] = ft.IconButton(
        icon=ft.Icons.FIRST_PAGE,
        tooltip="First page",
        on_click=on_first_page,
        disabled=True,
    )
    
    dialog_controls["last_page_btn"] = ft.IconButton(
        icon=ft.Icons.LAST_PAGE,
        tooltip="Last page",
        on_click=on_last_page,
        disabled=True,
    )
    
    dialog_controls["page_buttons_row"] = ft.Row(
        controls=[],
        spacing=5,
        alignment=ft.MainAxisAlignment.CENTER,
    )
    
    dialog_controls["page_size_dropdown"] = ft.Dropdown(
        label="Rows per page",
        width=120,
        value="50",
        options=[
            ft.dropdown.Option("25"),
            ft.dropdown.Option("50"),
            ft.dropdown.Option("100"),
            ft.dropdown.Option("200"),
            ft.dropdown.Option("500"),
        ],
        on_change=on_page_size_change,
        tooltip="Number of rows per page",
    )
    
    dialog_controls["pagination_info"] = ft.Text(
        "Page 1 of 1",
        color=ft.Colors.GREY_600,
        size=12,
        weight=ft.FontWeight.W_500,
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        expand=True,
        tabs=[
            ft.Tab(
                text="Console",
                content=ft.Column(
                    [
                        dialog_controls["output_text_field"],
                        dialog_controls["progress_bar"],
                        dialog_controls["progress_text"],
                        button_row,
                        file_ops_frame,
                        dialog_controls["status_label"],
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
            ),
            ft.Tab(
                text="Data View",
                content=ft.Column(
                    [
                        ft.Text("📊 Data View", style="titleMedium", color=ft.Colors.GREY_800),
                        dialog_controls["data_table_info"],
                        # Search Controls
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("🔍 Search Data", style="titleSmall", weight=ft.FontWeight.BOLD),
                                    ft.Row(
                                        [
                                            dialog_controls.get("search_term"),
                                            dialog_controls.get("search_column"),
                                            dialog_controls.get("search_btn"),
                                            ft.IconButton(
                                                icon=ft.Icons.CLEAR,
                                                tooltip="Clear search",
                                                on_click=clear_search_handler,
                                            ),
                                        ],
                                        spacing=10,
                                        alignment=ft.MainAxisAlignment.START,
                                    ),
                                    ft.Row(
                                        [
                                            dialog_controls.get("case_switch"),
                                            dialog_controls.get("whole_switch"),
                                            dialog_controls.get("match_label"),
                                        ],
                                        spacing=15,
                                        alignment=ft.MainAxisAlignment.START,
                                    ),
                                ]
                            ),
                            padding=10,
                            border_radius=8,
                            margin=ft.margin.only(bottom=10),
                        ),
                        # Pagination Controls
                        ft.Container(
                            content=ft.Column(
                                [
                                    # Top row: Navigation buttons and page info
                                    ft.Row(
                                        [
                                            dialog_controls.get("first_page_btn"),
                                            dialog_controls.get("prev_page_btn"),
                                            dialog_controls.get("pagination_info"),
                                            dialog_controls.get("next_page_btn"),
                                            dialog_controls.get("last_page_btn"),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=10,
                                    ),
                                    # Bottom row: Page numbers and page size
                                    ft.Row(
                                        [
                                            dialog_controls.get("page_buttons_row"),
                                            ft.VerticalDivider(width=1),
                                            dialog_controls.get("page_size_dropdown"),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=10,
                                    ),
                                ],
                                spacing=8,
                            ),
                            padding=12,
                            border_radius=8,
                            margin=ft.margin.only(bottom=10),
                        ),
                        # Data Table Container
                        ft.Container(
                            content=ft.Row(
                                [dialog_controls["data_table"]],
                                scroll=ft.ScrollMode.AUTO,  # Enable horizontal scrolling
                                expand=True,
                            ),
                            expand=True,
                            padding=10,
                            border_radius=10,
                            border=ft.border.all(1, ft.Colors.GREY_300),
                            # Remove bgcolor from container to let DataTable handle its own background
                        ),
                    ],
                    spacing=10,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,  # Enable vertical scrolling
                ),
            ),
            ft.Tab(
                text="Data Tools",
                content=ft.Column(
                    [
                        ft.Text(
                            "🔧 Data Tools",
                            style="titleMedium",
                            color=ft.Colors.GREY_800,
                        ),
                        csv_chunker_card,
                        dialog_controls["chunk_status"],
                        convert_card,
                    ]
                ),
            ),
            ft.Tab(text="Advanced tools", content=advanced_content),
            ft.Tab(
                text="Settings",
                content=ft.Column(
                    [
                        ft.Text("⚙️ Settings and preferences", color=ft.Colors.GREY_500),
                        dialog_controls["theme_switch"],
                    ]
                ),
            ),
        ],
    )
    dialog_controls["tabs"] = tabs

    # 6) Render with fade-in
    main_container = ft.Column(
        [header, tabs],
        expand=True,
        opacity=0.0,
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
    )
    page.add(main_container)
    page.update()
    main_container.opacity = 1.0
    
    # Apply initial theme colors to containers
    apply_data_table_theme(page)
    
    page.update()


if __name__ == "__main__":
    ft.app(target=main, assets_dir=ASSETS_DIR)



"""Main Flet UI for the Datascope application."""

import sys, os

# Determine where assets were unpacked.
if getattr(sys, "frozen", False):
    # Running as a bundled EXE
    ASSETS_DIR = os.path.join(sys._MEIPASS, "assets")
else:
    # Running from source
    ASSETS_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "assets")
    )


import flet as ft
import asyncio
import os
import logging
import sys



import data_handler
from data_handler import (
    create_dataset_environment,
    load_data,
    run_analysis,
    convert_file,
    search_dataframe,
    export_dataframe,
    export_text,
)



from pathlib import Path
import json
import sys
import math

# When ``True`` developer-only buttons are shown in the UI.
# Restart the application after changing this value.
dev_mode: bool = False  # Set to ``True`` for development mode

# Global variable to store the DF (SEAN FEATURE BUILDOUT)
current_df = None


# Ensure the current directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# SETTINGS!-----------------------------------------------------------------------------------------
# Directory under the user's home folder for storing preferences.
# Using the home directory ensures the path is writable even when the
# application is packaged as an executable.
PREFERENCES_DIR = Path.home() / "ProtexxaDatascope" / "preferences"

# Full path to the theme configuration file.
SETTINGS_FILE = PREFERENCES_DIR / "theme.json"


def load_theme_preference() -> bool:
    """Retrieve the stored theme preference, if available."""

    if SETTINGS_FILE.exists():
        try:
            with SETTINGS_FILE.open("r") as f:
                data = json.load(f)
            return data.get("dark_mode", False)
        except json.JSONDecodeError:
            logging.error("Failed to parse %s", SETTINGS_FILE)
            print(f"[Preferences] Failed parsing {SETTINGS_FILE}")
    return False


# Dark Mode Save Function
def save_theme_preference(dark_mode: bool) -> None:
    """Persist the dark mode preference to disk."""

    PREFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open("w") as f:
        json.dump({"dark_mode": dark_mode}, f)
    logging.info("Saved theme preference to %s", SETTINGS_FILE)
    print(f"[Preferences] Theme saved -> {SETTINGS_FILE}")


# SETTINGS!-----------------------------------------------------------------------------------------

# Global flag for checking if dataset was loaded
data_loaded = False
# Indicates if a long operation is running
app_busy = False
# Default chunk size for CSV splitting operations
CHUNK_SIZE_DEFAULT = 256

# File conversion helper variables
convert_input_path = None
convert_output_dir = None

# Icon to represent CSV splitting. Older versions of this file referenced
# ``ft.Icon.SPLIT_CSV_OUTLINE`` which does not exist in Flet.  We gracefully
# fall back to ``HORIZONTAL_SPLIT_OUTLINED`` to avoid runtime errors.
SPLIT_CSV_ICON = getattr(
    ft.Icons, "SPLIT_CSV_OUTLINE", ft.Icons.HORIZONTAL_SPLIT_OUTLINED
)

# Control references
dialog_controls = {
    "output_text_field": None,
    "btn_log": None,
    "btn_data": None,
    "btn_visual": None,
    "status_label": None,
    "file_picker": None,
    "theme_switch": None,
    "chunk_size_input": None,
    "chunk_status": None,
    "logo_image": None,
    "tabs": None,
    "splash_container": None,
    "convert_status": None,
    "convert_file_picker": None,
    "convert_dir_picker": None,
    "convert_file_display": None,
    "convert_dir_display": None,
    "progress_bar": None,
    "progress_text": None,
    "export_picker": None,
    "match_label": None,
    "export_format": "csv",
    "encoding": "utf-8",
    "delimiter": None,
    "search_results": None,
    "search_index": 0,
    "convert_format": "csv",
    "analysis_text": "",
    "data_table": None,
    "data_table_info": None,
}

export_context = None


async def write_output(message: str, page: ft.Page):
    print(message)
    if dialog_controls["output_text_field"]:
        dialog_controls["output_text_field"].value += message + "\n"
        page.update()


async def check_data_loaded(page: ft.Page):
    if not data_loaded:
        await write_output("[Error] Load data first before testing.", page)
        return False
    return True


# Flash the logo between grayscale and color when app_busy is True
async def flash_logo(page: ft.Page):
    step = 0
    speed = 1.1  # Smaller is slower breathing

    while True:
        logo_ref = dialog_controls.get("logo_image")
        logo = logo_ref.current if logo_ref else None

        if not logo:
            await asyncio.sleep(0.5)
            continue

        if app_busy:
            # Use a sine wave for smooth breathing (ease-in-out feel)
            # Maps step from 0 to π (half sine wave) for inhale → exhale
            # Normalized from 0.3 to 1.0 opacity
            t = (math.sin(step) + 1) / 2  # t in [0, 1]
            logo.opacity = 0.3 + t * 0.7  # scale to [0.3, 1.0]
            logo.update()
            step += speed
            if step > math.pi * 2:
                step = 0
            await asyncio.sleep(0.05)  # Higher = choppier
        else:
            if logo.opacity != 1.0:
                logo.opacity = 1.0
                logo.update()
            await asyncio.sleep(0.5)


def focus_console_tab(page: ft.Page):
    """Switch to the Console tab if the tab control exists."""
    tabs = dialog_controls.get("tabs")
    if tabs:
        tabs.selected_index = 0
        page.update()


def focus_dataview_tab(page: ft.Page):
    """Switch to the Data View tab if the tab control exists."""
    tabs = dialog_controls.get("tabs")
    if tabs:
        tabs.selected_index = 1  # Data View tab is at index 1
        page.update()


def apply_data_table_theme(page: ft.Page):
    """Apply theme colors to the DataTable based on current theme mode."""
    data_table = dialog_controls.get("data_table")
    if not data_table:
        return
    
    # Determine if we're in dark mode
    is_dark_mode = page.theme_mode == ft.ThemeMode.DARK
    
    # Apply colors based on theme
    if is_dark_mode:
        data_table.bgcolor = ft.Colors.GREY_900
        data_table.heading_row_color = ft.Colors.GREY_700
        data_table.border = ft.border.all(1, ft.Colors.GREY_600)
        data_table.vertical_lines = ft.BorderSide(1, ft.Colors.GREY_600)
        data_table.horizontal_lines = ft.BorderSide(1, ft.Colors.GREY_600)
    else:
        data_table.bgcolor = ft.Colors.WHITE
        data_table.heading_row_color = ft.Colors.GREY_100
        data_table.border = ft.border.all(1, ft.Colors.GREY_400)
        data_table.vertical_lines = ft.BorderSide(1, ft.Colors.GREY_300)
        data_table.horizontal_lines = ft.BorderSide(1, ft.Colors.GREY_300)
    
    # Also update the container border if it exists
    data_table_container = None
    tabs = dialog_controls.get("tabs")
    if tabs and len(tabs.tabs) > 1:  # Data View is at index 1
        data_view_tab = tabs.tabs[1]
        if hasattr(data_view_tab, 'content') and hasattr(data_view_tab.content, 'controls'):
            for control in data_view_tab.content.controls:
                if isinstance(control, ft.Container) and hasattr(control, 'content'):
                    if control.content == data_table:
                        data_table_container = control
                        break
    
    if data_table_container:
        if is_dark_mode:
            data_table_container.border = ft.border.all(1, ft.Colors.GREY_600)
        else:
            data_table_container.border = ft.border.all(1, ft.Colors.GREY_300)


def update_data_table(df, page: ft.Page, max_rows=100):
    """Update the data table with DataFrame content and switch to Data View tab."""
    if df is None or df.empty:
        return
    
    # Limit the number of rows to display for performance
    display_df = df.head(max_rows)
    
    # Create columns for the DataTable
    columns = [ft.DataColumn(ft.Text(col)) for col in display_df.columns]
    
    # Create rows for the DataTable
    rows = []
    for index, row in display_df.iterrows():
        cells = [ft.DataCell(ft.Text(str(value))) for value in row]
        rows.append(ft.DataRow(cells=cells))
    
    # Update the data table
    data_table = dialog_controls.get("data_table")
    if data_table:
        data_table.columns = columns
        data_table.rows = rows
        
        # Update the row count label
        total_rows = len(df)
        displayed_rows = len(display_df)
        dialog_controls["data_table_info"].value = f"Showing {displayed_rows} of {total_rows} rows"
        
        # Apply theme colors to the table
        apply_data_table_theme(page)
        
        # Switch to Data View tab and update
        focus_dataview_tab(page)


async def update_progress(progress: float, message: str, page: ft.Page):
    """Update progress bar value and accompanying text.

    A small utility that ensures the UI reflects the given progress
    percentage. Also prints/logs the update for traceability.
    """
    logging.info("Progress update: %s%% - %s", progress, message)
    print(f"Progress update: {progress}% - {message}")
    if dialog_controls["progress_bar"]:
        dialog_controls["progress_bar"].value = progress / 100.0
        dialog_controls["progress_text"].value = f"{message} ({progress:.0f}%)"
        page.update()


async def show_progress(show: bool, page: ft.Page):
    """Toggle visibility of progress related widgets."""
    logging.info("Show progress widgets: %s", show)
    print(f"Show progress widgets: {show}")
    if dialog_controls["progress_bar"]:
        dialog_controls["progress_bar"].visible = show
        dialog_controls["progress_text"].visible = show
        page.update()


def show_error(message: str, page: ft.Page) -> None:
    """Display an error dialog with the provided message."""
    logging.error("Dialog error: %s", message)
    print(f"[GUI Error] {message}")
    dlg = ft.AlertDialog(title=ft.Text("Error"), content=ft.Text(message))
    page.dialog = dlg
    dlg.open = True
    page.update()


async def reset_app_state(page: ft.Page):
    """Return the UI to a safe baseline after an error.

    This helper clears global flags, resets dropdown options and updates
    the status label so that the user can attempt the operation again
    without stale state lingering.
    """
    global current_df, data_loaded, app_busy
    logging.error("Resetting application state due to error")
    print("[GUI] Resetting application state due to error")
    current_df = None
    data_loaded = False
    app_busy = False

    cd = dialog_controls.get("column_dropdown")
    if cd:
        cd.options = [ft.dropdown.Option("All Columns")]
        cd.value = "All Columns"

    dialog_controls["status_label"].value = "An error occurred, Please try again, Ready"
    dialog_controls["status_label"].color = ft.Colors.GREEN
    page.update()


def unload_current_dataset(page: ft.Page) -> None:
    """Clear the current dataset and disable test buttons."""

    global current_df, data_loaded
    if not data_loaded:
        return

    logging.info("Unloading current dataset")
    print("[GUI] Unloading current dataset")
    current_df = None
    data_loaded = False

    for btn_key in ("btn_log", "btn_data", "btn_visual"):
        btn = dialog_controls.get(btn_key)
        if btn:
            btn.disabled = True

    dialog_controls["status_label"].value = "Dataset unloaded. Select a file."
    dialog_controls["status_label"].color = ft.Colors.BLUE

    out = dialog_controls.get("output_text_field")
    if out:
        out.value = ""

    try:
        data_handler.saved_filepath = None
    except Exception:
        pass

    page.update()


async def logging_handler_test(e: ft.ControlEvent):
    page = e.page
    if not await check_data_loaded(page):
        return
    await write_output(
        "[Logging Handler] Beep Boop Beep, Test Complete! (This is just text output.)", page
    )
    # Show a sample of the data in the Data View tab
    if current_df is not None:
        sample_df = current_df.head(5)  # Show first 5 rows as a test
        update_data_table(sample_df, page)


async def data_handler_test(e: ft.ControlEvent):
    page = e.page
    if not await check_data_loaded(page):
        return
    await write_output("[Data Handler] Beep Boop Beep, Test Complete! (This is just text output.)", page)
    # Show data summary in the Data View tab
    if current_df is not None:
        summary_df = current_df.describe(include='all').transpose()  # Show data summary
        update_data_table(summary_df, page)


async def visual_analyst_test(e: ft.ControlEvent):
    page = e.page
    if not await check_data_loaded(page):
        return
    await write_output(
        "[Visual Analyst] Beep Boop Beep, Test Complete! (This is just text output.)", page
    )
    # Show data types and info in the Data View tab
    if current_df is not None:
        # Create a DataFrame with column information
        import pandas as pd
        info_data = {
            'Column': current_df.columns.tolist(),
            'Data Type': [str(dtype) for dtype in current_df.dtypes],
            'Non-Null Count': [current_df[col].count() for col in current_df.columns],
            'Null Count': [current_df[col].isnull().sum() for col in current_df.columns],
        }
        info_df = pd.DataFrame(info_data)
        update_data_table(info_df, page)


# FILE HANDLER BLOCK----------------------------------------------------------------------------------------
from data_handler import save_filepath, get_data_stats, split_into_chunks
from pathlib import Path

# ----------------------------------------------------------------------------------------------------------


async def load_data_result(e: ft.FilePickerResultEvent):
    """Handle data selection and load the chosen file asynchronously."""
    global current_df, data_loaded, app_busy
    page = e.page

    if e.files:
        file_path = e.files[0].path
        save_filepath(file_path)  # ← store the real string path
        dialog_controls["loaded_file"] = file_path

        # 1. Get dataset name from file
        dataset_name = Path(file_path).stem

        # Indicate busy state
        app_busy = True

        # 2. Create environment folders for this dataset
        project_paths = create_dataset_environment(dataset_name)
        await write_output(
            f"[Environment] Folders created at: {project_paths['project']}", page
        )

        # 3. Show status
        dialog_controls["status_label"].value = "Working..."
        dialog_controls["status_label"].color = ft.Colors.AMBER
        page.update()
        await asyncio.sleep(0.1)

        loop = asyncio.get_running_loop()

        def progress_cb(p, m):
            asyncio.run_coroutine_threadsafe(update_progress(p, m, page), loop)

        await show_progress(True, page)

        df = await asyncio.to_thread(
            load_data,
            file_path,
            progress_cb,
            dialog_controls.get("encoding", "utf-8"),
            dialog_controls.get("delimiter"),
        )
        current_df = df

        await show_progress(False, page)

        if df is None:
            await write_output("[Error] Failed to load dataset.", page)
            show_error("Failed to load dataset", page)
            await reset_app_state(page)
            return

        cd = dialog_controls["column_dropdown"]
        options = [ft.dropdown.Option("All Columns")] + [
            ft.dropdown.Option(c) for c in current_df.columns
        ]
        cd.options = options
        cd.value = "All Columns"
        sc = dialog_controls.get("search_column")
        if sc:
            sc.options = options
            sc.value = "All Columns"
        page.update()

        info = get_data_stats(df, file_path)
        await write_output(info["log1"], page)
        await write_output(info["log2"], page)

        # Update the data table with loaded data
        update_data_table(df, page)

        # 4. Toggle buttons now that loading succeeded
        data_loaded = True
        dialog_controls["btn_log"].disabled = False
        dialog_controls["btn_data"].disabled = False
        dialog_controls["btn_visual"].disabled = False
        dialog_controls["btn_dataview"].disabled = False
        dialog_controls["status_label"].value = "Ready"
        dialog_controls["status_label"].color = ft.Colors.GREEN
        dialog_controls["status_label"].weight = ft.FontWeight.BOLD
        app_busy = False

    else:
        await write_output("[Load Data] No file selected.", page)
        dialog_controls["status_label"].value = "Ready"
        dialog_controls["status_label"].color = ft.Colors.RED
        app_busy = False

    page.update()


def handle_file_result(e: ft.FilePickerResultEvent):
    if e.files:
        selected_file = e.files[0].path
        dialog_controls["status_label"].value = f"Loaded: {selected_file}"
        dialog_controls["status_label"].color = ft.Colors.GREEN


async def load_data_handler(e: ft.ControlEvent):
    """Prompt the user for a file and ensure previous data is cleared."""

    page = e.page

    # Clear any previously loaded dataset before prompting for a new file
    unload_current_dataset(page)

    dialog_controls["status_label"].value = "Waiting..."
    dialog_controls["status_label"].color = ft.Colors.ORANGE

    # (Re)create the file picker so prior selections do not persist
    if dialog_controls["file_picker"] is not None:
        try:
            page.overlay.remove(dialog_controls["file_picker"])
        except ValueError:
            pass

    dialog_controls["file_picker"] = ft.FilePicker(on_result=load_data_result)
    page.overlay.append(dialog_controls["file_picker"])

    page.update()
    dialog_controls["file_picker"].pick_files(
        allow_multiple=False,
        allowed_extensions=["csv", "xlsx", "xls", "txt"],
    )


async def chunk_csv_handler(e: ft.ControlEvent):

    try:
        if not save_filepath:
            await write_output("[Error] No file loaded to chunk.", e.page)
            return

        dataset_name = Path(save_filepath).stem
        paths = create_dataset_environment(dataset_name)
        chunks_dir = str(paths["chunks"])

        await write_output(f"[GUI] Chunking started: {save_filepath}", e.page)

        split_into_chunks(save_filepath, chunks_dir, chunk_size_mb=256)

        await write_output(
            f"[GUI] ✅ Chunking complete. Files saved in:\n{chunks_dir}", e.page
        )

    except Exception as ex:
        await write_output(f"[Error] Failed to chunk file: {ex}", e.page)
        show_error(f"Chunking failed: {ex}", e.page)


async def handle_chunk_button(e: ft.ControlEvent):
    """Handle the click event for the CSV chunking button.

    This routine validates the input, spawns the CSV splitting process on
    a background thread and updates the UI with progress information.
    """
    global app_busy
    page = e.page

    file_path = data_handler.saved_filepath  # ✅ get latest saved path

    if not file_path or not isinstance(file_path, (str, Path)):
        dialog_controls["chunk_status"].value = "Please load a file first."
        page.update()
        return

    dataset_name = Path(file_path).stem

    try:
        chunk_size = int(dialog_controls["chunk_size_input"].value)
    except ValueError:
        dialog_controls["chunk_status"].value = (
            "Please enter a valid number for chunk size."
        )
        page.update()
        return

    dialog_controls["chunk_status"].value = "Chunking in progress..."
    app_busy = True
    page.update()

    loop = asyncio.get_running_loop()

    def progress_cb(p, m):
        asyncio.run_coroutine_threadsafe(update_progress(p, m, page), loop)

    await show_progress(True, page)

    result = await asyncio.to_thread(
        split_into_chunks,
        dataset_name,
        file_path,
        chunk_size_mb=chunk_size,
        logger_fn=lambda msg: print(msg),
        progress_fn=progress_cb,
    )

    await show_progress(False, page)

    if result and result["total_chunks"] > 0:
        dialog_controls["chunk_status"].value = (
            f"Chunked {result['total_rows']} rows into {result['total_chunks']} files."
        )
    else:
        dialog_controls["chunk_status"].value = "Chunking failed. See logs."

    app_busy = False
    page.update()


async def on_chunk_csv(e: ft.ControlEvent):
    """Launch CSV chunking using the size stored on the page object."""
    page = e.page
    chunk_size = getattr(page, "chunk_size", CHUNK_SIZE_DEFAULT)
    dialog_controls["chunk_size_input"].value = str(chunk_size)
    print(f"[GUI] Chunk CSV requested with {chunk_size} MB")
    logging.info("Chunk CSV requested with %s MB", chunk_size)
    await handle_chunk_button(e)


def convert_file_result(e: ft.FilePickerResultEvent):
    """Store the file selected for conversion and update the display."""
    global convert_input_path
    if e.files:
        convert_input_path = e.files[0].path
        dialog_controls["convert_file_display"].value = convert_input_path
    else:
        convert_input_path = None
        dialog_controls["convert_file_display"].value = "No file selected"
    e.page.update()


def convert_dir_result(e: ft.FilePickerResultEvent):
    """Store the output directory chosen for conversion."""
    global convert_output_dir
    if e.path:
        convert_output_dir = e.path
        dialog_controls["convert_dir_display"].value = convert_output_dir
    else:
        convert_output_dir = None
        dialog_controls["convert_dir_display"].value = "No folder selected"
    e.page.update()


async def on_convert_file(e: ft.ControlEvent):
    """Convert the selected file using the chosen format."""
    global app_busy
    page = e.page

    if not convert_input_path or not convert_output_dir:
        dialog_controls["convert_status"].value = "Select input file and folder."
        page.update()
        return

    dialog_controls["convert_status"].value = "Converting..."
    app_busy = True
    page.update()

    try:
        loop = asyncio.get_running_loop()

        def progress_cb(p, m):
            asyncio.run_coroutine_threadsafe(update_progress(p, m, page), loop)

        await show_progress(True, page)

        output_file = await asyncio.to_thread(
            convert_file,
            convert_input_path,
            convert_output_dir,
            dialog_controls.get("convert_format", "csv"),
            progress_cb,
        )
        dialog_controls["convert_status"].value = f"Saved to {output_file}"
        await show_progress(False, page)
    except Exception as ex:
        dialog_controls["convert_status"].value = f"Error: {ex}"
        show_error(f"Conversion failed: {ex}", page)
        await show_progress(False, page)

    app_busy = False
    page.update()


# FILE HANDLER BLOCK END----------------------------------------------------------------------------------------
# SEAN FEATURE BUILDOUT BLOCK-----------------------------------------------------------------


async def analysis_handler(e: ft.ControlEvent):
    global app_busy
    page = e.page

    if not data_loaded:
        await write_output("[Error] Load data first.", page)
        return

    # Pull the widgets out of dialog_controls
    ad = dialog_controls["analysis_dropdown"]
    cd = dialog_controls["column_dropdown"]
    ri = dialog_controls["rows_input"]
    ss = dialog_controls["sort_switch"]

    # Read their values
    atype = ad.value
    col = cd.value if cd.value != "All Columns" else None

    try:
        num = int(ri.value)
    except ValueError:
        await write_output("[Error] Rows must be an integer.", page)
        return

    desc = ss.value

    # Run the analysis on a background thread
    app_busy = True
    result = await asyncio.to_thread(run_analysis, current_df, atype, col, num, desc)
    dialog_controls["analysis_text"] = result
    await write_output(result, page)
    
    # Switch to Data View tab when running analysis
    focus_dataview_tab(page)
    
    # If analysis returns tabular data, show it in the data table
    if atype in ["Data Preview", "Missing Values", "Duplicate Detection", "Special Character Analysis", "Placeholder Detection"]:
        if atype == "Data Preview":
            # Show preview of the data
            preview_df = current_df.head(num) if not desc else current_df.tail(num)
            if col and col != "All Columns":
                preview_df = preview_df[[col]]
            update_data_table(preview_df, page)
        elif atype == "Missing Values":
            # Show missing values summary as a table
            import pandas as pd
            missing_data = {
                'Column': current_df.columns.tolist(),
                'Missing Count': [current_df[col].isnull().sum() for col in current_df.columns],
                'Missing Percentage': [round((current_df[col].isnull().sum() / len(current_df)) * 100, 2) for col in current_df.columns],
                'Total Count': [len(current_df) for _ in current_df.columns],
                'Non-Missing Count': [current_df[col].count() for col in current_df.columns]
            }
            missing_df = pd.DataFrame(missing_data)
            # Sort by missing count if requested
            if desc:
                missing_df = missing_df.sort_values('Missing Count', ascending=False)
            update_data_table(missing_df, page)
        elif atype == "Placeholder Detection":
            # Show placeholder detection as a table
            import pandas as pd
            placeholders = ['N/A', 'NULL', 'null', 'None', 'none', 'nan', 'NaN', '-', '?', 'Unknown', 'unknown', '']
            placeholder_data = []
            for column in current_df.columns:
                if current_df[column].dtype == 'object':  # Only analyze text columns
                    placeholder_count = 0
                    found_placeholders = []
                    for placeholder in placeholders:
                        count = (current_df[column].astype(str) == placeholder).sum()
                        if count > 0:
                            placeholder_count += count
                            found_placeholders.append(f"{placeholder} ({count})")
                    
                    placeholder_data.append({
                        'Column': column,
                        'Placeholder Count': placeholder_count,
                        'Placeholders Found': ', '.join(found_placeholders[:5]) + ('...' if len(found_placeholders) > 5 else ''),
                        'Percentage': round((placeholder_count / len(current_df)) * 100, 2) if len(current_df) > 0 else 0
                    })
            
            if placeholder_data:
                placeholder_df = pd.DataFrame(placeholder_data)
                if desc:
                    placeholder_df = placeholder_df.sort_values('Placeholder Count', ascending=False)
                update_data_table(placeholder_df, page)
        elif atype == "Special Character Analysis":
            # Show special character analysis as a table with ASCII and Non-ASCII breakdown
            import pandas as pd
            char_data = []
            for column in current_df.columns:
                if current_df[column].dtype == 'object':  # Only analyze text columns
                    # Get all text from this column
                    all_text = ' '.join(current_df[column].astype(str).tolist())
                    
                    # Separate ASCII and Non-ASCII special characters
                    ascii_special = []
                    non_ascii_special = []
                    
                    for char in set(all_text):
                        if not char.isalnum() and not char.isspace():
                            if ord(char) < 128:  # ASCII range
                                ascii_special.append(char)
                            else:  # Non-ASCII
                                non_ascii_special.append(char)
                    
                    # Count total special characters
                    total_special = len(ascii_special) + len(non_ascii_special)
                    
                    # Get counts of each character type in the actual data
                    ascii_count = sum(all_text.count(char) for char in ascii_special)
                    non_ascii_count = sum(all_text.count(char) for char in non_ascii_special)
                    
                    char_data.append({
                        'Column': column,
                        'Total Special Chars': total_special,
                        'ASCII Special Count': len(ascii_special),
                        'Non-ASCII Count': len(non_ascii_special),
                        'ASCII Characters': ''.join(sorted(ascii_special)[:15]) + ('...' if len(ascii_special) > 15 else ''),
                        'Non-ASCII Characters': ''.join(sorted(non_ascii_special)[:10]) + ('...' if len(non_ascii_special) > 10 else ''),
                        'ASCII Frequency': ascii_count,
                        'Non-ASCII Frequency': non_ascii_count
                    })
            
            if char_data:
                char_df = pd.DataFrame(char_data)
                if desc:
                    char_df = char_df.sort_values('Total Special Chars', ascending=False)
                update_data_table(char_df, page)
        elif atype == "Duplicate Detection":
            # Show duplicate rows
            duplicates = current_df[current_df.duplicated(keep=False)]
            if not duplicates.empty:
                update_data_table(duplicates, page)
    
    app_busy = False


async def show_search_result(page: ft.Page):
    """Display the current search result in the console and data table."""
    results = dialog_controls.get("search_results")
    if not results:
        return
    idx = dialog_controls.get("search_index", 0)
    row = current_df.iloc[[results[idx]]]
    await write_output(row.to_string(index=False), page)
    dialog_controls["match_label"].value = f"{idx+1}/{len(results)}"
    
    # Show the search result row in the data table
    update_data_table(row, page)
    page.update()


async def on_search(e: ft.ControlEvent):
    """Execute a DataFrame search based on UI selections."""
    if current_df is None:
        show_error("Load data before searching", e.page)
        return

    term = dialog_controls["search_term"].value
    col_value = dialog_controls["search_column"].value
    column = None if col_value == "All Columns" else col_value
    case = dialog_controls["case_switch"].value
    whole = dialog_controls["whole_switch"].value

    results = search_dataframe(current_df, term, column, case, whole)
    dialog_controls["search_results"] = results
    dialog_controls["search_index"] = 0

    if not results:
        await write_output("No matches found.", e.page)
        dialog_controls["match_label"].value = "0/0"
        return

    # Show all search results in the data table
    search_results_df = current_df.iloc[results]
    update_data_table(search_results_df, e.page)
    
    await show_search_result(e.page)


async def on_prev_match(e: ft.ControlEvent):
    results = dialog_controls.get("search_results")
    if not results:
        return
    dialog_controls["search_index"] = (dialog_controls["search_index"] - 1) % len(results)
    await show_search_result(e.page)


async def on_next_match(e: ft.ControlEvent):
    results = dialog_controls.get("search_results")
    if not results:
        return
    dialog_controls["search_index"] = (dialog_controls["search_index"] + 1) % len(results)
    await show_search_result(e.page)


def clear_search(_: ft.ControlEvent):
    """Reset stored search results and UI label."""
    dialog_controls["search_results"] = None
    dialog_controls["search_index"] = 0
    if dialog_controls.get("match_label"):
        dialog_controls["match_label"].value = "0/0"


def export_picker_result(e: ft.FilePickerResultEvent):
    """Handle path selection from the export file picker."""
    global export_context
    if not e.path:
        return
    try:
        if export_context == "dataset" and current_df is not None:
            export_dataframe(current_df, e.path, dialog_controls.get("export_format", "csv"))
        elif export_context == "search" and dialog_controls.get("search_results"):
            df = current_df.iloc[dialog_controls["search_results"]]
            export_dataframe(df, e.path, dialog_controls.get("export_format", "csv"))
        elif export_context == "analysis":
            export_text(dialog_controls.get("analysis_text", ""), e.path)
        dialog_controls["status_label"].value = f"Saved: {e.path}"
    except Exception as ex:
        show_error(str(ex), e.page)
    finally:
        export_context = None
        e.page.update()


def export_dataset(e: ft.ControlEvent):
    global export_context
    export_context = "dataset"
    dialog_controls["export_picker"].save_file()


def export_search_results(e: ft.ControlEvent):
    if not dialog_controls.get("search_results"):
        show_error("Run a search first", e.page)
        return
    global export_context
    export_context = "search"
    dialog_controls["export_picker"].save_file()


def export_analysis_text(e: ft.ControlEvent):
    if not dialog_controls.get("analysis_text"):
        show_error("Run analysis first", e.page)
        return
    global export_context
    export_context = "analysis"
    dialog_controls["export_picker"].save_file()


# SEAN FEATURE BUILDOUT BLOCK END------------------------------------------------------------
def build_advanced_content() -> ft.Column:
    """Construct the Advanced tools tab and make it scrollable.

    The Advanced tools tab contains many widgets. Automatic scrolling allows
    all controls to remain accessible regardless of screen size.
    """

    logging.info("Building Advanced tools UI")
    print("[GUI] Building Advanced tools UI")

    advanced_content = ft.Column(
        [
            ft.Text("Analysis", style="titleMedium"),
            dialog_controls.get("analysis_dropdown"),
            dialog_controls.get("desc_text"),
            dialog_controls.get("column_dropdown"),
            ft.Row(
                [
                    dialog_controls.get("rows_input"),
                    dialog_controls.get("sort_switch"),
                ],
                spacing=20,
            ),
            dialog_controls.get("run_btn"),
            ft.Divider(),
            ft.Text("Load Options", weight=ft.FontWeight.BOLD),
            ft.Row([dialog_controls.get("enc_dropdown"), dialog_controls.get("delim_dropdown")], spacing=10),
            ft.Divider(),
            ft.Text("Search", style="titleMedium"),
            ft.Row([dialog_controls.get("search_term"), dialog_controls.get("search_column")], spacing=10),
            ft.Row(
                [
                    dialog_controls.get("case_switch"),
                    dialog_controls.get("whole_switch"),
                    dialog_controls.get("search_btn"),
                ],
                spacing=10,
            ),
            ft.Row(
                [
                    dialog_controls.get("prev_btn"),
                    dialog_controls.get("next_btn"),
                    dialog_controls.get("match_label"),
                ],
                spacing=5,
            ),
            ft.Divider(),
            ft.Text("Export", style="titleMedium"),
            ft.Row([dialog_controls.get("export_fmt"), dialog_controls.get("export_ds_btn")], spacing=10),
            ft.Row([dialog_controls.get("export_search_btn"), dialog_controls.get("export_analysis_btn")], spacing=10),
        ],
        spacing=10,
        alignment=ft.MainAxisAlignment.START,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    return advanced_content


# Synchronous theme toggle handler to avoid threading issues
def on_theme_toggle(e: ft.ControlEvent):
    page = e.page
    dark_mode = e.control.value
    global current_theme_mode

    # Define your light and dark seeds
    light_seed = "#00FF7F"  # Tech Green for Light Theme
    dark_seed = "#1E90FF"   # Tech Blue for Dark Theme

    # Apply theme mode
    page.theme_mode = ft.ThemeMode.DARK if dark_mode else ft.ThemeMode.LIGHT
    current_theme_mode = page.theme_mode

    # Set theme based on the selected mode
    if dark_mode:
        page.dark_theme = ft.Theme(color_scheme_seed=dark_seed)
    else:
        page.theme = ft.Theme(color_scheme_seed=light_seed)

    # Always update data table colors when theme changes
    apply_data_table_theme(page)

    save_theme_preference(dark_mode)
    page.update()



async def main(page: ft.Page):
    """Primary entry point for the Flet UI."""
    global data_loaded

    # Window appearance and behavior
    page.window.frameless = True
    page.window.title_bar_hidden = True
    page.window.resizable = True
    page.vertical_alignment = ft.CrossAxisAlignment.START

    # Window size
    page.window.width = 700
    page.window.height = 640

    # Center the window on screen
    page.window.center()

    # Set app metadata
    page.title = "Protexxa Datascope - Alpha"
    # Load saved theme preference
    dark_mode_enabled = load_theme_preference()
    page.theme_mode = ft.ThemeMode.DARK if dark_mode_enabled else ft.ThemeMode.LIGHT

    page.window.icon = "favicon.ico"

    # Default chunk size stored on page for reuse in handlers
    page.chunk_size = CHUNK_SIZE_DEFAULT

    page.update()

    # Start background task to flash the logo when busy
    asyncio.create_task(flash_logo(page))

    # FilePicker
    dialog_controls["file_picker"] = ft.FilePicker(on_result=load_data_result)
    page.overlay.append(dialog_controls["file_picker"])

    dialog_controls["convert_file_picker"] = ft.FilePicker(
        on_result=convert_file_result
    )
    page.overlay.append(dialog_controls["convert_file_picker"])

    dialog_controls["convert_dir_picker"] = ft.FilePicker(on_result=convert_dir_result)
    page.overlay.append(dialog_controls["convert_dir_picker"])

    dialog_controls["export_picker"] = ft.FilePicker(on_result=export_picker_result)
    page.overlay.append(dialog_controls["export_picker"])

    # Theme toggle switch
    dialog_controls["theme_switch"] = ft.Switch(
        label="Dark Mode", value=dark_mode_enabled, on_change=on_theme_toggle
    )

    # Frameless Splash screen
    splash_content = ft.Column(
        [
            ft.Text(
                "PROPERTY OF",
                font_family="Helvetica",
                size=10,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
            ),
            ft.Image(
                src="protexxa-logo.png",
                width=156,
                height=61,
                fit=ft.ImageFit.CONTAIN,
                error_content=ft.Text("Logo not found", color=ft.Colors.RED),
            ),
            ft.Text(
                "13.1°N 59.32°W → 43° 39' 11.6136'' N 79° 22' 59.4624'' W\n"
                "AICohort01: The Intelligence Migration\n"
                "Data Cleaning Division",
                font_family="Helvetica",
                size=10,
                color=ft.Colors.WHITE,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,  # <--- vertical centering
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # <--- horizontal centering
        expand=True,
    )
    splash_container = ft.Container(
        content=splash_content,
        expand=True,
        bgcolor="#1e1e2f",
        alignment=ft.alignment.center,
        on_click=transition_to_gui,
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        opacity=1.0,
    )
    dialog_controls["splash_container"] = splash_container

    page.add(splash_container)
    page.update()
    await asyncio.sleep(1)  # SPLASH SCREEN DELAY (CURRENTLY 1 SECOND FOR TESTING)
    await transition_to_gui(page)


async def transition_to_gui(page: ft.Page):
    # 1) Fade out splash screen
    splash = dialog_controls.get("splash_container")
    if splash:
        splash.opacity = 0
        page.update()
        await asyncio.sleep(0.3)

    # 2) Restore window chrome & clear splash
    page.window.frameless = False
    page.window.title_bar_hidden = False
    page.controls.clear()
    page.update()

    # 2) Header
    logo_ref = ft.Ref[ft.Image]()
    logo_img = ft.Image(
        src="protexxa_logo_cropped.png",
        width=40,
        height=40,
        fit=ft.ImageFit.CONTAIN,
        error_content=ft.Text("Logo missing", color=ft.Colors.RED),
        ref=logo_ref,
    )
    header = ft.WindowDragArea(
        content=ft.Row(
            controls=[
                ft.Text(
                    "Protexxa Datascope - 1.2",
                    font_family="Arial",
                    size=20,
                    weight=ft.FontWeight.NORMAL,
                ),
                logo_img,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            width=800,
        )
    )

    dialog_controls["logo_image"] = logo_ref

    # 3) Console & File‑ops UI (must come before Tabs)
    dialog_controls["output_text_field"] = ft.TextField(
        multiline=True,
        read_only=True,
        min_lines=20,
        max_lines=20,
        width=700,
        height=300,
        border_radius=20,
        border_color=ft.Colors.BLUE_GREY_200,
        content_padding=10,
        value="",
    )
    dialog_controls["progress_bar"] = ft.ProgressBar(
        width=700,
        height=10,
        bgcolor=ft.Colors.GREY_300,
        color=ft.Colors.BLUE,
        value=0,
        visible=False,
    )
    dialog_controls["progress_text"] = ft.Text(
        value="",
        size=12,
        color=ft.Colors.BLUE,
        text_align=ft.TextAlign.CENTER,
        visible=False,
        weight=ft.FontWeight.BOLD,
    )

    # load / test buttons (test buttons hidden when ``dev_mode`` is False)
    btn_load = ft.ElevatedButton(
        text="Load Data",
        on_click=load_data_handler,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    dialog_controls["btn_log"] = ft.ElevatedButton(
        text="Test Logging",
        on_click=logging_handler_test,
        disabled=True,
        visible=dev_mode,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    dialog_controls["btn_data"] = ft.ElevatedButton(
        text="Test Data Handling",
        on_click=data_handler_test,
        disabled=True,
        visible=dev_mode,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    dialog_controls["btn_visual"] = ft.ElevatedButton(
        text="Test Visual Analyst",
        on_click=visual_analyst_test,
        disabled=True,
        visible=dev_mode,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    
    # Add a button to manually switch to Data View for testing
    btn_dataview = ft.ElevatedButton(
        text="View Data Table",
        on_click=lambda e: focus_dataview_tab(e.page),
        disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
    )
    dialog_controls["btn_dataview"] = btn_dataview
    
    button_row = ft.Row(
        controls=[
            btn_load,
            dialog_controls["btn_log"],
            dialog_controls["btn_data"],
            dialog_controls["btn_visual"],
            dialog_controls["btn_dataview"],
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=10,
    )

    file_ops_frame = ft.Container(
        content=ft.Column(
            [ft.Text("(File save buttons will go here)", color=ft.Colors.GREY_600)]
        ),
        border_radius=10,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
        padding=10,
        width=700,
    )

    dialog_controls["status_label"] = ft.Text("Ready", color=ft.Colors.BLUE)

    # 4) Advanced Tab Widgets (SEAN FEATURE BUILDOUT)
    analysis_help = {
        "Data Preview": "Show sample rows and types.",
        "Missing Values": "Report null counts.",
        "Duplicate Detection": "Find duplicated rows.",
        "Placeholder Detection": "Check for placeholder tokens.",
        "Special Character Analysis": "Analyze ASCII and Non-ASCII special characters with frequencies.",
    }

    desc_text = ft.Text(value="", size=12, color=ft.Colors.BLUE_GREY_600)
    dialog_controls["desc_text"] = desc_text

    def on_analysis_change(e: ft.ControlEvent):
        desc_text.value = analysis_help.get(e.control.value, "")
        e.page.update()

    analysis_dropdown = ft.Dropdown(
        label="Analysis Type",
        width=200,
        options=[
            ft.dropdown.Option("Data Preview"),
            ft.dropdown.Option("Missing Values"),
            ft.dropdown.Option("Duplicate Detection"),
            ft.dropdown.Option("Placeholder Detection"),
            ft.dropdown.Option("Special Character Analysis"),
        ],
        on_change=on_analysis_change,
        tooltip="Choose analysis to run",
    )
    column_dropdown = ft.Dropdown(
        label="Column", width=200, options=[ft.dropdown.Option("All Columns")]
    )
    rows_input = ft.TextField(label="Rows to show", value="10", width=100)
    sort_switch = ft.Switch(label="Descending order", value=False)
    run_btn = ft.ElevatedButton("Run Analysis", on_click=analysis_handler)

    # stash for the handler
    dialog_controls["analysis_dropdown"] = analysis_dropdown
    dialog_controls["column_dropdown"] = column_dropdown
    dialog_controls["rows_input"] = rows_input
    dialog_controls["sort_switch"] = sort_switch
    dialog_controls["run_btn"] = run_btn
    dialog_controls["match_label"] = ft.Text("0/0")

    enc_dropdown = ft.Dropdown(
        label="Encoding",
        width=120,
        value="utf-8",
        options=[
            ft.dropdown.Option("utf-8"),
            ft.dropdown.Option("latin1"),
            ft.dropdown.Option("utf-16"),
        ],
        on_change=lambda e: dialog_controls.__setitem__("encoding", e.control.value),
        tooltip="File encoding",
    )
    dialog_controls["enc_dropdown"] = enc_dropdown

    def on_delim_change(e: ft.ControlEvent):
        dialog_controls["delimiter"] = None if e.control.value == "Auto" else e.control.value

    delim_dropdown = ft.Dropdown(
        label="Delimiter",
        width=120,
        value="Auto",
        options=[
            ft.dropdown.Option("Auto"),
            ft.dropdown.Option(","),
            ft.dropdown.Option("\t"),
            ft.dropdown.Option(";"),
            ft.dropdown.Option("|"),
        ],
        on_change=on_delim_change,
        tooltip="Field delimiter",
    )
    dialog_controls["delim_dropdown"] = delim_dropdown

    search_term = ft.TextField(label="Search term", width=200, tooltip="Enter text to search")
    search_column = ft.Dropdown(label="Search Column", width=150, options=[ft.dropdown.Option("All Columns")])
    case_switch = ft.Switch(label="Case", value=False)
    whole_switch = ft.Switch(label="Whole", value=False)
    search_btn = ft.ElevatedButton(text="Search", on_click=on_search)
    prev_btn = ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=on_prev_match, tooltip="Previous")
    next_btn = ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=on_next_match, tooltip="Next")

    dialog_controls["search_term"] = search_term
    dialog_controls["search_column"] = search_column
    dialog_controls["case_switch"] = case_switch
    dialog_controls["whole_switch"] = whole_switch
    dialog_controls["search_btn"] = search_btn
    dialog_controls["prev_btn"] = prev_btn
    dialog_controls["next_btn"] = next_btn

    export_fmt = ft.Dropdown(
        label="Format",
        width=120,
        value="csv",
        options=[ft.dropdown.Option("csv"), ft.dropdown.Option("xlsx")],
        on_change=lambda e: dialog_controls.__setitem__("export_format", e.control.value),
    )
    dialog_controls["export_fmt"] = export_fmt
    export_ds_btn = ft.ElevatedButton("Export Dataset", on_click=export_dataset, tooltip="Save full dataset")
    export_search_btn = ft.ElevatedButton("Export Search", on_click=export_search_results, tooltip="Save search matches")
    export_analysis_btn = ft.ElevatedButton("Export Analysis", on_click=export_analysis_text, tooltip="Save last analysis")

    dialog_controls["export_ds_btn"] = export_ds_btn
    dialog_controls["export_search_btn"] = export_search_btn
    dialog_controls["export_analysis_btn"] = export_analysis_btn
    
    # Create scrollable Advanced tools tab content
    advanced_content = build_advanced_content()

    # 5) Build Tabs in one shot
    dialog_controls["chunk_size_input"] = ft.TextField(
        label="Chunk size (MB)",
        width=200,
        value=str(page.chunk_size),
        on_change=lambda e: setattr(page, "chunk_size", int(e.control.value)),
    )
    dialog_controls["chunk_status"] = ft.Text(value="", color=ft.Colors.GREY_700)

    csv_chunker_card = ft.Card(
        elevation=3,
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("CSV Chunker", style="headlineSmall"),
                    ft.Row(
                        [
                            dialog_controls["chunk_size_input"],
                            ft.ElevatedButton(
                                text="Chunk CSV",
                                icon=SPLIT_CSV_ICON,
                                on_click=on_chunk_csv,
                            ),
                        ],
                        spacing=16,
                        alignment="start",
                    ),
                ]
            ),
        ),
    )

    dialog_controls["convert_status"] = ft.Text(value="", color=ft.Colors.GREY_700)
    dialog_controls["convert_file_display"] = ft.Text(
        "No file selected", color=ft.Colors.GREY_700
    )
    dialog_controls["convert_dir_display"] = ft.Text(
        "No folder selected", color=ft.Colors.GREY_700
    )

    convert_card = ft.Card(
        elevation=3,
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("File Converter", style="headlineSmall"),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                text="Select File",
                                # Using ``ft.Icons`` because ``ft`` exposes icons via this enumeration
                                # rather than ``ft.icons`` which does not exist.
                                icon=ft.Icons.UPLOAD_FILE,
                                on_click=lambda e: dialog_controls[
                                    "convert_file_picker"
                                ].pick_files(allow_multiple=False),
                            ),
                            dialog_controls["convert_file_display"],
                        ],
                        spacing=16,
                        alignment="start",
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                text="Choose Folder",
                                # Replace ``ft.icons`` with ``ft.Icons`` to prevent attribute errors
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=lambda e: dialog_controls[
                                    "convert_dir_picker"
                                ].get_directory_path(),
                            ),
                            dialog_controls["convert_dir_display"],
                        ],
                        spacing=16,
                        alignment="start",
                    ),
                    ft.Row(
                        [
                            ft.Dropdown(
                                width=100,
                                value="csv",
                                options=[ft.dropdown.Option("csv"), ft.dropdown.Option("xlsx")],
                                on_change=lambda e: dialog_controls.__setitem__("convert_format", e.control.value),
                                tooltip="Output format",
                            ),
                            ft.ElevatedButton(
                                text="Convert",
                                icon=ft.Icons.DOWNLOAD,
                                on_click=on_convert_file,
                            ),
                        ],
                        spacing=10,
                    ),
                    dialog_controls["convert_status"],
                ]
            ),
        ),
    )

    # Create the Data View tab controls
    dialog_controls["data_table"] = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("No Data"))],  # Default column to avoid error
        rows=[],
        border=ft.border.all(1, ft.Colors.GREY_400),
        border_radius=10,
        vertical_lines=ft.BorderSide(1, ft.Colors.GREY_300),
        horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_300),
        heading_row_color=ft.Colors.GREY_100,
        heading_row_height=50,
        data_row_min_height=30,
        data_row_max_height=60,
        show_checkbox_column=False,
        bgcolor=ft.Colors.WHITE,  # Ensure background is white
    )
    
    dialog_controls["data_table_info"] = ft.Text(
        "No data loaded",
        color=ft.Colors.GREY_600,
        size=12
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        expand=True,
        tabs=[
            ft.Tab(
                text="Console",
                content=ft.Column(
                    [
                        dialog_controls["output_text_field"],
                        dialog_controls["progress_bar"],
                        dialog_controls["progress_text"],
                        button_row,
                        file_ops_frame,
                        dialog_controls["status_label"],
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
            ),
            ft.Tab(
                text="Data View",
                content=ft.Column(
                    [
                        ft.Text("📊 Data View", style="titleMedium", color=ft.Colors.GREY_800),
                        dialog_controls["data_table_info"],
                        ft.Container(
                            content=dialog_controls["data_table"],
                            expand=True,
                            padding=10,
                            border_radius=10,
                            border=ft.border.all(1, ft.Colors.GREY_300),
                            # Remove bgcolor from container to let DataTable handle its own background
                        ),
                    ],
                    spacing=10,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            ft.Tab(
                text="Data Tools",
                content=ft.Column(
                    [
                        ft.Text(
                            "🔧 Data Tools",
                            style="titleMedium",
                            color=ft.Colors.GREY_800,
                        ),
                        csv_chunker_card,
                        dialog_controls["chunk_status"],
                        convert_card,
                    ]
                ),
            ),
            ft.Tab(text="Advanced tools", content=advanced_content),
            ft.Tab(
                text="Settings",
                content=ft.Column(
                    [
                        ft.Text("⚙️ Settings and preferences", color=ft.Colors.GREY_500),
                        dialog_controls["theme_switch"],
                    ]
                ),
            ),
        ],
    )
    dialog_controls["tabs"] = tabs

    # 6) Render with fade-in
    main_container = ft.Column(
        [header, tabs],
        expand=True,
        opacity=0.0,
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
    )
    page.add(main_container)
    page.update()
    main_container.opacity = 1.0
    page.update()


if __name__ == "__main__":
    ft.app(target=main, assets_dir=ASSETS_DIR)

