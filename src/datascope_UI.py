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
import re
import time
import traceback

# Add src directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import data_handler
from data_handler import (
    create_dataset_environment,
    load_data,
    convert_file,
    search_dataframe,
    export_dataframe,
    export_text,
    get_paginated_data,
    analyze_placeholder_data,
    analyze_special_characters,
    analyze_missing_values,
    get_duplicate_rows,
    analyze_duplicates_advanced,
    analyze_duplicates_by_column,
    get_data_preview,
    save_filepath,
    get_data_stats,
    split_into_chunks,
)
from data_view import DataViewWidget
from enhanced_data_view import EnhancedDataView
from recommendation_engine import recommendation_engine
from recommendation_ui import create_recommendations_panel, update_recommendations_panel, refresh_recommendations_theme

dev_mode = False  # Set to True for development mode, False for production

# Global variable to store the DF (SEAN FEATURE BUILDOUT)
current_df = None
current_theme_mode = ft.ThemeMode.LIGHT

# Global data view widget instance
data_view_widget = None
enhanced_data_view = None  # New enhanced data view widget

# Global recommendations panel references
recommendations_panel = None
recommendations_content = None

# Global variable to store the last project folder path
last_project_folder = None
last_chunk_folder = None

# Global variable for custom data root folder
custom_data_root = None  # User-selected root folder for datasets (None = use default)


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
    "recommendations_panel": None,
    "recommendations_content": None,
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


def update_data_view_status(status_type, **kwargs):
    """Update status message in the active data view widget."""
    global enhanced_data_view, data_view_widget
    
    if enhanced_data_view:
        enhanced_data_view.update_status_message(status_type, **kwargs)
    elif data_view_widget:
        data_view_widget.update_status_message(status_type, **kwargs)


def focus_dataview_tab(page: ft.Page):
    """Switch to the Data View tab if the tab control exists."""
    tabs = dialog_controls.get("tabs")
    if tabs:
        tabs.selected_index = 1  # Data View tab is at index 1
        page.update()


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


def update_data_table(df, page: ft.Page, max_rows=None, highlight_term=None, highlight_column=None, is_paginated=False, disable_pagination=False):
    """Simplified function that delegates to the EnhancedDataView with performance optimization.
    
    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to display
    page : ft.Page
        The page instance
    max_rows : int, optional
        Maximum rows to show (deprecated, use disable_pagination instead)
    highlight_term : str, optional
        Term to highlight
    highlight_column : str, optional
        Column to restrict highlighting to
    is_paginated : bool, optional
        Whether this is a paginated call
    disable_pagination : bool, optional
        If True, show all rows without pagination (useful for data previews)
    """
    global current_df, enhanced_data_view
    
    # PERFORMANCE OPTIMIZATION: Add update throttling to prevent redundant calls
    import time
    current_time = time.time()
    
    if not hasattr(update_data_table, '_last_update'):
        update_data_table._last_update = 0
        update_data_table._last_shape = None
    
    # Check if this is a duplicate call with same data
    time_since_last = current_time - update_data_table._last_update
    same_shape = update_data_table._last_shape == df.shape if df is not None else False
    
    if time_since_last < 0.1 and same_shape and not is_paginated:
        print(f"[DEBUG] update_data_table: Skipping duplicate call (last update {time_since_last:.2f}s ago)")
        return
    
    update_data_table._last_update = current_time
    update_data_table._last_shape = df.shape if df is not None else None
    
    print(f"[DEBUG] update_data_table called with:")
    print(f"[DEBUG]   df shape: {df.shape if df is not None else 'None'}")
    print(f"[DEBUG]   df columns: {list(df.columns) if df is not None else 'None'}")
    print(f"[DEBUG]   is_paginated: {is_paginated}")
    print(f"[DEBUG]   disable_pagination: {disable_pagination}")
    print(f"[DEBUG]   enhanced_data_view exists: {enhanced_data_view is not None}")
    
    if df is None or df.empty:
        print("[DEBUG] update_data_table: DataFrame is None or empty, returning")
        return

    # Store the DataFrame globally for other functions that may need it
    if not is_paginated:
        current_df = df
        print(f"[DEBUG] update_data_table: Stored DataFrame globally (shape: {df.shape})")
    else:
        print(f"[DEBUG] update_data_table: Not storing globally (is_paginated=True)")

    # PERFORMANCE OPTIMIZATION: Delegate to the enhanced data view widget with error handling
    if enhanced_data_view:
        try:
            display_df = df if max_rows is None else df.head(max_rows)
            print(f"[DEBUG] update_data_table: About to call enhanced_data_view.load_data")
            print(f"[DEBUG] update_data_table: display_df shape: {display_df.shape}")
            
            enhanced_data_view.load_data(
                display_df, 
                highlight_term=highlight_term, 
                highlight_column=highlight_column,
                disable_pagination=disable_pagination
            )
            print(f"[DEBUG] update_data_table: enhanced_data_view.load_data completed successfully")
        except Exception as e:
            print(f"[ERROR] EnhancedDataView update failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # PERFORMANCE OPTIMIZATION: Minimize UI refresh calls
        try:
            if hasattr(enhanced_data_view, 'refresh'):
                enhanced_data_view.refresh()
            page.update()
        except Exception as e:
            print(f"[ERROR] UI refresh failed: {e}")
    
    # Switch to dataview tab for instant feedback
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


def open_data_folder(e):
    """Open the data folder in Windows Explorer."""
    global last_project_folder
    
    if last_project_folder and os.path.exists(last_project_folder):
        try:
            # Use subprocess to open Explorer and bring it to front
            import subprocess
            subprocess.Popen(f'explorer "{last_project_folder}"')
        except Exception as ex:
            show_error(f"Could not open folder: {str(ex)}", e.page)
    else:
        show_error("❌ No data folder found. Load data first.", e.page)
        show_error("💡 Try this instead: Click 'Load Data' button to import a file first", e.page)


def open_chunk_folder(e):
    """Open the chunk folder in Windows Explorer."""
    global last_chunk_folder
    
    if last_chunk_folder and os.path.exists(last_chunk_folder):
        try:
            # Use subprocess to open Explorer and bring it to front
            import subprocess
            subprocess.Popen(f'explorer "{last_chunk_folder}"')
        except Exception as ex:
            show_error(f"Could not open chunks folder: {str(ex)}", e.page)
    else:
        show_error("❌ No chunks folder found. Chunk a CSV file first.", e.page)
        show_error("💡 Try this instead: Load a CSV file and select 'Chunk Large CSV' to create chunks first", e.page)


def set_custom_data_root(e):
    """Set custom data root folder."""
    global custom_data_root
    if e.path:
        custom_data_root = e.path
        display_path = f"{custom_data_root}\\ProtexxaDatascope"
        dialog_controls["data_root_label"].value = f"Default data folder: {display_path}"
        print(f"[Settings] Custom data root set to: {custom_data_root}")
        e.page.update()


def reset_custom_data_root(page):
    """Reset to default data root folder."""
    global custom_data_root
    custom_data_root = None
    default_path = str(Path.home() / "ProtexxaDatascope")
    dialog_controls["data_root_label"].value = f"Default data folder: {default_path}"
    print(f"[Settings] Data root reset to default: {default_path}")
    page.update()


async def reset_app_state(page: ft.Page, force_reset: bool = False):
    """Return the UI to a safe baseline after an error.

    This helper clears global flags, resets dropdown options and updates
    the status label so that the user can attempt the operation again
    without stale state lingering.
    
    Parameters
    ----------
    force_reset : bool
        If True, force reset even if data is currently loaded
    """
    global current_df, data_loaded, app_busy
    
    # Don't reset if data is successfully loaded unless explicitly forced
    if data_loaded and current_df is not None and not force_reset:
        print(f"[DEBUG] Skipping reset_app_state - data is successfully loaded")
        return
        
    logging.error("Resetting application state due to error")
    print("[GUI] Resetting application state due to error")
    
    import traceback
    print(f"[DEBUG] RESET CALLED - Stack trace:")
    for line in traceback.format_stack()[-10:]:  # Show last 10 stack frames
        print(f"[DEBUG]   {line.strip()}")
    
    current_df = None
    data_loaded = False
    print(f"[DEBUG] RESET COMPLETED - data_loaded={data_loaded}, current_df is None: {current_df is None}")
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
# Functions imported at top of file: save_filepath, get_data_stats, split_into_chunks

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
    global current_df, data_loaded, app_busy, last_project_folder
    page = e.page

    if e.files:
        file_path = e.files[0].path
        save_filepath(file_path)
        dialog_controls["loaded_file"] = file_path

        dataset_name = Path(file_path).stem
        app_busy = True
        
        # Update status to loading
        update_data_view_status('loading')
            
        project_paths = create_dataset_environment(dataset_name, custom_data_root)
        last_project_folder = project_paths['project']  # Store folder path for later use
        await write_output(f"[Environment] Folders created at: {project_paths['project']}", page)
        dialog_controls["status_label"].value = "Working..."
        dialog_controls["status_label"].color = ft.Colors.AMBER
        page.update()
        await asyncio.sleep(0.1)

        loop = asyncio.get_running_loop()
        def progress_cb(p, m):
            asyncio.run_coroutine_threadsafe(update_progress(p, m, page), loop)

        await show_progress(True, page)

        # Fallback encoding/delimiter logic
        encodings_to_try = [dialog_controls.get("encoding", "auto"), "utf-8", "utf-8-sig", "latin1", "cp1252"]
        delimiters_to_try = [dialog_controls.get("delimiter"), ",", "\t", ";", "|", None]
        load_success = False
        last_exception = None
        attempt_logs = []
        df = None
        validation_results = {}
        for enc in encodings_to_try:
            for delim in delimiters_to_try:
                try:
                    result = await asyncio.to_thread(
                        load_data,
                        file_path,
                        progress_cb,
                        enc,
                        delim,
                    )
                    if isinstance(result, tuple):
                        df, validation_results = result
                    else:
                        df = result
                        validation_results = {}
                    if df is not None:
                        attempt_logs.append(f"Success: encoding={enc}, delimiter={repr(delim)}")
                        load_success = True
                        break
                    else:
                        attempt_logs.append(f"Failed: encoding={enc}, delimiter={repr(delim)} (no data)")
                except Exception as ex:
                    attempt_logs.append(f"Exception: encoding={enc}, delimiter={repr(delim)} - {ex}")
                    last_exception = ex
            if load_success:
                break

        await show_progress(False, page)

        # Log all attempts
        for log_msg in attempt_logs:
            await write_output(f"[Loader Attempt] {log_msg}", page)

        if not load_success or df is None:
            await write_output("[Error] Failed to load dataset after all fallback attempts.", page)
            
            # Update status to error
            update_data_view_status('error', message="Failed to load dataset")
                
            if last_exception:
                show_error(f"Failed to load dataset: {last_exception}", page)
            else:
                show_error("Failed to load dataset", page)
            await reset_app_state(page)
            return

        current_df = df
        print(f"[DEBUG] Set current_df with shape: {current_df.shape}")
        print(f"[DEBUG] Global data_loaded before setting: {data_loaded}")
        if validation_results:
            await display_validation_results(validation_results, page)

        cd = dialog_controls["column_dropdown"]
        options = [ft.dropdown.Option("All Columns")] + [ft.dropdown.Option(c) for c in current_df.columns]
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
        
        # Debug: Check if data_view_container exists before calling update_data_table
        dvc = dialog_controls.get("data_view_container")
        print(f"[DEBUG] Before update_data_table call: data_view_container exists = {dvc is not None}")
        print(f"[DEBUG] DataFrame shape: {df.shape}")
        print(f"[DEBUG] DataFrame columns: {list(df.columns)}")
        
        update_data_table(df, page)
        print(f"[DEBUG] After update_data_table call completed")
        
        # Update data view status with filename and stats
        filename = Path(file_path).name
        update_data_view_status('loaded', 
                               filename=filename, 
                               rows=len(df), 
                               cols=len(df.columns))
        
        # Set data_loaded to True BEFORE updating recommendations panel
        data_loaded = True
        print(f"[DEBUG] Set data_loaded = {data_loaded} (global variable) BEFORE recommendations")
        
        # Generate intelligent recommendations for the loaded dataset
        try:
            recommendations = recommendation_engine.analyze_dataset(df, filename)
            if recommendations:
                # Display in console
                rec_text = recommendation_engine.format_recommendations_for_ui(recommendations)
                await write_output("\n" + rec_text, page)
                await write_output("\n" + "="*50, page)
                
                # Update recommendations panel if it exists
                rec_content = dialog_controls.get("recommendations_content")
                if rec_content:
                    update_recommendations_panel(recommendations, rec_content, page, data_loaded, current_df, trigger_recommended_analysis_sync)
        except Exception as e:
            print(f"[DEBUG] Recommendation generation failed: {e}")
        
        if len(df) > dialog_controls.get("rows_per_page", 25):
            await write_output(f"[Info] Dataset has {len(df)} rows. Using pagination for display.", page)

        # Additional debug logging after recommendations update
        print(f"[DEBUG] current_df is None after setting data_loaded: {current_df is None}")
        print(f"[DEBUG] Global variable IDs after setting: data_loaded={id(data_loaded)}, current_df={id(current_df)}")
        
        # Test immediate global state after setting
        debug_global_state()
        
        dialog_controls["btn_log"].disabled = False
        dialog_controls["btn_data"].disabled = False
        dialog_controls["btn_visual"].disabled = False
        dialog_controls["btn_dataview"].disabled = False
        dialog_controls["status_label"].value = "Ready"
        dialog_controls["status_label"].color = ft.Colors.GREEN
        dialog_controls["status_label"].weight = ft.FontWeight.BOLD
        app_busy = False
        
        print(f"[DEBUG] Set app_busy=False and status='Ready'")
        
        # Force final page update to ensure UI reflects the changes
        page.update()
        print(f"[DEBUG] Final page update completed - load process finished")
        
        # Test global state again after page update
        print(f"[DEBUG] Testing global state after page.update():")
        debug_global_state()
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
    global last_chunk_folder
    
    try:
        if not save_filepath:
            await write_output("[Error] No file loaded to chunk.", e.page)
            return

        dataset_name = Path(save_filepath).stem
        paths = create_dataset_environment(dataset_name)
        chunks_dir = str(paths["chunks"])
        last_chunk_folder = chunks_dir  # Store chunk folder path for later use

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
    global app_busy, last_chunk_folder
    page = e.page

    file_path = data_handler.saved_filepath  # ✅ get latest saved path

    if not file_path or not isinstance(file_path, (str, Path)):
        dialog_controls["chunk_status"].value = "Please load a file first."
        page.update()
        return

    dataset_name = Path(file_path).stem
    
    # Create dataset environment and store chunks folder path
    paths = create_dataset_environment(dataset_name, custom_data_root)
    last_chunk_folder = str(paths["chunks"])

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
async def trigger_recommended_analysis(action: str, page: ft.Page):
    """Trigger an analysis from a recommendation."""
    print(f"[Recommendations] Triggering analysis: {action}")
    
    # Map recommendation actions to dropdown values
    action_mapping = {
        "Data Preview": "Data Preview",
        "Missing Values": "Missing Values", 
        "Duplicate Detection": "Duplicate Detection",
        "Special Character Analysis": "Special Character Analysis",
        "Placeholder Detection": "Placeholder Detection"
    }
    
    if action in action_mapping and data_loaded:
        # Set the analysis dropdown value
        analysis_dropdown = dialog_controls.get("analysis_dropdown")
        if analysis_dropdown:
            analysis_dropdown.value = action_mapping[action]
            page.update()
            
            # Create a mock event to trigger the analysis
            from types import SimpleNamespace
            mock_event = SimpleNamespace()
            mock_event.page = page
            
            # Trigger the analysis
            await analysis_handler(mock_event)
    else:
        if not data_loaded:
            await write_output("[Recommendation] Please load data first before running analysis.", page)
    
    # Log the action for the recommendation engine
    recommendation_engine.log_user_action(action)


def trigger_recommended_analysis_sync(action: str, page: ft.Page, data_df=None, is_data_loaded=None):
    """Synchronous version of trigger_recommended_analysis for recommendation clicks."""
    global data_loaded, current_df, dialog_controls, analysis_handler, recommendation_engine, app_busy
    
    # Add debouncing to prevent rapid successive clicks
    import time
    current_time = time.time()
    
    # Check if we have a recent timestamp for this action
    if not hasattr(trigger_recommended_analysis_sync, '_last_execution'):
        trigger_recommended_analysis_sync._last_execution = {}
    
    last_time = trigger_recommended_analysis_sync._last_execution.get(action, 0)
    cooldown_period = 2.0  # 2 seconds cooldown between same action executions
    
    if current_time - last_time < cooldown_period:
        print(f"[Recommendations] Debouncing {action} - too soon after last execution ({current_time - last_time:.1f}s ago)")
        return
    
    # Update timestamp for this action
    trigger_recommended_analysis_sync._last_execution[action] = current_time
    
    # Check if app is already busy with another analysis
    if app_busy:
        print(f"[Recommendations] Skipping {action} - app is busy with another operation")
        return
    
    # Use passed parameters if provided, otherwise fall back to globals
    actual_data_loaded = is_data_loaded if is_data_loaded is not None else data_loaded
    actual_current_df = data_df if data_df is not None else current_df
    
    print(f"[Recommendations] Triggering sync analysis: {action}")
    print(f"[Recommendations] data_loaded = {actual_data_loaded} (type: {type(actual_data_loaded)})")
    print(f"[Recommendations] current_df is None: {actual_current_df is None}")
    print(f"[Recommendations] current_df type: {type(actual_current_df)}")
    
    # Map recommendation actions to dropdown values
    action_mapping = {
        "Data Preview": "Data Preview",
        "Missing Values": "Missing Values", 
        "Duplicate Detection": "Duplicate Detection",
        "Special Character Analysis": "Special Character Analysis",
        "Placeholder Detection": "Placeholder Detection"
    }
    
    if action in action_mapping and actual_data_loaded:
        # Set the analysis dropdown value
        analysis_dropdown = dialog_controls.get("analysis_dropdown")
        if analysis_dropdown:
            analysis_dropdown.value = action_mapping[action]
            page.update()
            
            # Create a mock event to trigger the analysis
            from types import SimpleNamespace
            mock_event = SimpleNamespace()
            mock_event.page = page
            
            # Trigger the analysis using page.run_task for async handler
            async def run_analysis_async():
                return await analysis_handler(mock_event)
            
            page.run_task(run_analysis_async)
            print(f"[Recommendations] Successfully triggered analysis: {action}")
    else:
        if not actual_data_loaded:
            # Use synchronous output writing
            print("[Recommendation] Please load data first before running analysis.")
        else:
            print(f"[Recommendation] Action '{action}' not found in mapping or other issue")


def get_current_data_state():
    """Get the current data state for cross-module access."""
    global data_loaded, current_df
    print(f"[DEBUG] get_current_data_state called: data_loaded={data_loaded}, current_df is None: {current_df is None}")
    if current_df is not None:
        print(f"[DEBUG] current_df shape: {current_df.shape}")
    return {
        'data_loaded': data_loaded,
        'current_df': current_df
    }


def debug_global_state():
    """Debug function to check global state."""
    import traceback
    global data_loaded, current_df
    print(f"[DEBUG] Global State Check:")
    print(f"[DEBUG]   data_loaded = {data_loaded} (type: {type(data_loaded)})")
    print(f"[DEBUG]   current_df is None = {current_df is None}")
    if current_df is not None:
        print(f"[DEBUG]   current_df shape = {current_df.shape}")
    print(f"[DEBUG]   id(data_loaded) = {id(data_loaded)}")
    print(f"[DEBUG]   id(current_df) = {id(current_df)}")
    print(f"[DEBUG] Call stack:")
    for line in traceback.format_stack()[-5:]:  # Show last 5 stack frames
        print(f"[DEBUG]   {line.strip()}")
    return data_loaded, current_df
    
    # Log the action for the recommendation engine
    recommendation_engine.log_user_action(action)


async def register_analysis_function(name: str, func, description: str):
    """Helper function to register new analysis types easily.
    
    This makes it super easy to add new analysis types in the future!
    Just call this function with your analysis name, function, and description.
    """
    # Add to the analysis help dictionary
    if hasattr(register_analysis_function, 'analysis_help'):
        register_analysis_function.analysis_help[name] = description
    else:
        register_analysis_function.analysis_help = {name: description}
    
    # Add to the analysis functions dictionary  
    if hasattr(register_analysis_function, 'analysis_functions'):
        register_analysis_function.analysis_functions[name] = func
    else:
        register_analysis_function.analysis_functions = {name: func}
    
    print(f"[Registry] Registered analysis type: {name}")


# ENHANCED ANALYSIS FUNCTIONS - Clean Function-Based Architecture
# Each analysis type gets its own dedicated function for better maintainability

async def handle_data_preview_analysis(current_df, num, desc, col, page):
    """Handle Data Preview analysis with enhanced validation and performance guidance."""
    try:
        print(f"[DEBUG] handle_data_preview_analysis called with: num={num}, desc={desc}, col={col}")
        print(f"[DEBUG] current_df shape: {current_df.shape if current_df is not None else 'None'}")
        
        # Enhanced validation and smart defaults
        total_dataset_rows = len(current_df)
        show_all = False
        disable_pagination = False
        
        # Handle "Show All" case
        if num == -1:
            # PERFORMANCE OPTIMIZATION: Cap "Show All" for very large datasets
            if total_dataset_rows > 50000:
                # For huge datasets, show a large sample instead of everything
                num = min(10000, total_dataset_rows)
                await write_output(f"[Data Preview] ⚡ Performance Optimization: Showing {num:,} rows instead of all {total_dataset_rows:,} rows for better performance", page)
                await write_output(f"[Data Preview] 💡 Tip: Use smaller preview sizes (100-1000) for faster analysis of large datasets", page)
                disable_pagination = False  # Keep pagination for large samples
            else:
                num = total_dataset_rows
                show_all = True
                disable_pagination = True
                await write_output(f"[Data Preview] 🔍 Showing ALL {num:,} rows from dataset", page)
        else:
            # Validate and adjust row count for specific numbers
            if num <= 0:
                num = 50  # Default fallback
                await write_output(f"[Data Preview] Invalid row count, using default: {num}", page)
            elif num > 1000000:
                num = 1000000  # Maximum safety limit
                await write_output(f"[Data Preview] Row count too large, limited to: {num:,}", page)
            
            # Handle large requests intelligently
            if num >= total_dataset_rows:
                if total_dataset_rows > 50000:
                    # Same optimization for large datasets
                    num = min(10000, total_dataset_rows)
                    await write_output(f"[Data Preview] ⚡ Performance: Showing {num:,} sample rows from {total_dataset_rows:,} total", page)
                else:
                    num = total_dataset_rows
                    show_all = True
                    disable_pagination = True
                    await write_output(f"[Data Preview] 📊 Showing all available {num:,} rows", page)
        
        # Performance guidance based on row count
        if num <= 100:
            performance_level = "🟢 Instant"
        elif num <= 1000:
            performance_level = "🟡 Fast"
        elif num <= 5000:
            performance_level = "🟠 Quick"
        else:
            performance_level = "🔴 Loading..."
            
        display_mode = " (All rows)" if show_all else " (Paginated)"
        await write_output(f"[Data Preview] Performance: {performance_level} - Loading {num:,} rows{display_mode}", page)
        
        # PERFORMANCE OPTIMIZATION: Add timing for slow operations
        import time
        start_time = time.time()
        
        # Get preview data with proper parameter mapping
        preview_df = get_data_preview(current_df, num_rows=num, sort_desc=desc, column=col)
        
        processing_time = time.time() - start_time
        print(f"[DEBUG] Data Preview: Processing took {processing_time:.2f}s for {preview_df.shape[0]:,} rows")
        
        # Only show processing time for slower operations
        if processing_time > 0.5:
            await write_output(f"[Performance] ⏱️ Processing completed in {processing_time:.1f}s", page)
        print(f"[DEBUG] Data Preview: got preview_df with shape {preview_df.shape}")
        print(f"[DEBUG] Data Preview: columns = {list(preview_df.columns)}")
        
        # Memory usage estimation for large displays
        if num > 5000:
            estimated_mb = (num * len(preview_df.columns) * 8) / (1024 * 1024)  # Rough estimate
            await write_output(f"[Performance] Estimated memory usage: ~{estimated_mb:.1f}MB", page)
        
        # PERFORMANCE OPTIMIZATION: Reduce redundant page updates
        print(f"[DEBUG] Data Preview: About to call update_data_table with DataFrame:")
        print(f"[DEBUG] Data Preview: Columns: {list(preview_df.columns)}")
        print(f"[DEBUG] Data Preview: Shape: {preview_df.shape}")
        print(f"[DEBUG] Data Preview: disable_pagination: {disable_pagination}")
        
        # Update data table efficiently
        update_data_table(preview_df, page, is_paginated=True, disable_pagination=disable_pagination)

        # Update status with detailed context (single status update)
        if data_view_widget:
            data_view_widget.update_status_message('analysis', 
                                                 analysis_type="Data Preview", 
                                                 context=f"Showing {len(preview_df):,} rows × {len(preview_df.columns)} columns")
        
        # PERFORMANCE OPTIMIZATION: Batch output messages for efficiency
        actual_rows_shown = len(preview_df)
        output_messages = []
        
        if actual_rows_shown < num:
            output_messages.append(f"[Data Preview] ✅ Showing all {actual_rows_shown:,} available rows (requested {num:,}) × {len(preview_df.columns)} columns")
        else:
            output_messages.append(f"[Data Preview] ✅ Displaying {actual_rows_shown:,} rows × {len(preview_df.columns)} columns from {total_dataset_rows:,} total rows")
            
        if col:
            output_messages.append(f"[Data Preview] 🔍 Filtered to column: {col}")
            
        if desc:
            output_messages.append(f"[Data Preview] 🔄 Sorted in descending order")
            
        # Smart performance recommendations
        if actual_rows_shown < 100 and total_dataset_rows > 1000:
            output_messages.append(f"💡 Tip: Try viewing more rows (500-1000) for better data understanding")
        elif actual_rows_shown == total_dataset_rows and total_dataset_rows > 10000:
            output_messages.append(f"💡 Tip: For large datasets, consider using smaller previews (1000-5000 rows) for better performance")
        
        # Send all messages at once to reduce UI update overhead
        for msg in output_messages:
            await write_output(msg, page)
        
        # PERFORMANCE OPTIMIZATION: Single page update at the end
        page.update()
        print(f"[DEBUG] Data Preview: page.update() called")
        
        return {
            'success': True,
            'message': f"Data preview completed: {len(preview_df):,} rows displayed",
            'data_df': preview_df
        }
    except Exception as e:
        error_msg = f"Data Preview analysis failed: {str(e)}"
        print(f"[DEBUG] Data Preview ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        await write_output(f"[Error] {error_msg}", page)
        if data_view_widget:
            data_view_widget.update_status_message('error', context=error_msg)
        return {'success': False, 'message': error_msg, 'error': str(e)}


async def handle_missing_values_analysis(current_df, col, desc, page):
    """Handle Missing Values analysis with performance optimization and comprehensive error handling."""
    try:
        print(f"[DEBUG] Missing Values: analyzing column='{col}', desc={desc}")
        print(f"[DEBUG] current_df shape: {current_df.shape if current_df is not None else 'None'}")
        
        # Performance estimation for user guidance
        total_rows = len(current_df)
        total_cols = len(current_df.columns) if col is None else 1
        
        # PERFORMANCE OPTIMIZATION: Add timing and progress feedback
        import time
        start_time = time.time()
        
        if total_rows > 100000:
            await write_output(f"[Missing Values] 🔍 Analyzing large dataset ({total_rows:,} rows, {total_cols} columns) - this may take a moment...", page)
        elif total_rows > 10000:
            await write_output(f"[Missing Values] 🔍 Analyzing {total_rows:,} rows across {total_cols} columns...", page)
        
        # Get missing values data with optimized processing
        missing_df = analyze_missing_values(current_df, col)
        
        processing_time = time.time() - start_time
        print(f"[DEBUG] Missing Values: Processing took {processing_time:.2f}s for {missing_df.shape[0]:,} columns")
        
        # Show processing time for slower operations
        if processing_time > 1.0:
            await write_output(f"[Performance] ⏱️ Analysis completed in {processing_time:.1f}s", page)
        print(f"[DEBUG] Missing Values: got result with shape {missing_df.shape}")
        print(f"[DEBUG] Missing Values: columns = {list(missing_df.columns)}")
        
        if desc:
            missing_df = missing_df.sort_values('Missing Count', ascending=False)
        
        # Update the data table with analysis results
        print(f"[DEBUG] Missing Values: About to call update_data_table with DataFrame:")
        print(f"[DEBUG] Missing Values: Columns: {list(missing_df.columns)}")
        print(f"[DEBUG] Missing Values: Shape: {missing_df.shape}")
        print(f"[DEBUG] Missing Values: Sample data:\n{missing_df.head(2)}")
        update_data_table(missing_df, page, is_paginated=True)
        
        # Update status with detailed context
        if enhanced_data_view or data_view_widget:
            if not missing_df.empty:
                total_missing = missing_df['Missing Count'].sum()
                affected_columns = len(missing_df[missing_df['Missing Count'] > 0])
                context = f"Found {total_missing:,} missing values in {affected_columns} columns"
            else:
                context = "No missing values found"
            
            update_data_view_status('analysis', 
                                   analysis_type="Missing Values", 
                                   context=context)
        
        # Enhanced output summary to console
        total_missing = missing_df['Missing Count'].sum()
        affected_columns = len(missing_df[missing_df['Missing Count'] > 0])
        total_columns_analyzed = len(missing_df)
        
        await write_output(f"[Missing Values] ✅ Analyzed {total_columns_analyzed} columns - {total_missing:,} missing values found", page)
        
        if affected_columns > 0:
            # Calculate severity levels
            high_missing = missing_df[missing_df['Missing Percentage'] > 50]
            medium_missing = missing_df[(missing_df['Missing Percentage'] > 10) & (missing_df['Missing Percentage'] <= 50)]
            low_missing = missing_df[(missing_df['Missing Percentage'] > 0) & (missing_df['Missing Percentage'] <= 10)]
            
            if len(high_missing) > 0:
                await write_output(f"🔴 Critical: {len(high_missing)} columns with >50% missing data", page)
            if len(medium_missing) > 0:
                await write_output(f"🟡 Moderate: {len(medium_missing)} columns with 10-50% missing data", page)
            if len(low_missing) > 0:
                await write_output(f"🟢 Minor: {len(low_missing)} columns with <10% missing data", page)
            
            # Show top columns with missing values (enhanced details)
            top_missing = missing_df[missing_df['Missing Count'] > 0].head(5)  # Show top 5 instead of 3
            await write_output(f"[Top Missing Columns]", page)
            for _, row in top_missing.iterrows():
                severity = "🔴 Critical" if row['Missing Percentage'] > 50 else "🟡 Moderate" if row['Missing Percentage'] > 10 else "🟢 Minor"
                await write_output(f"  {severity} | {row['Column']}: {row['Missing Count']:,} missing ({row['Missing Percentage']:.1f}%) - {row['Non-Missing Count']:,} valid values", page)
            
            # Data quality recommendations
            if total_missing / total_rows > 0.3:
                await write_output(f"💡 Data Quality Alert: High missing data rate ({total_missing/total_rows*100:.1f}%). Consider data cleaning strategies.", page)
            elif affected_columns > total_columns_analyzed * 0.5:
                await write_output(f"💡 Tip: Missing values found in {affected_columns}/{total_columns_analyzed} columns. Consider imputation strategies.", page)
            else:
                await write_output(f"💡 Data Quality: Overall good data completeness - only {affected_columns}/{total_columns_analyzed} columns affected.", page)
        else:
            await write_output("✅ Excellent! No missing values detected in any columns", page)
            await write_output("💡 Your dataset has complete data coverage - ready for analysis", page)
        
        return {
            'success': True,
            'message': f"Missing values analysis completed: {len(missing_df)} columns analyzed",
            'data_df': missing_df
        }
    except Exception as e:
        error_msg = f"Missing Values analysis failed: {str(e)}"
        import traceback
        traceback.print_exc()
        await write_output(f"[Error] {error_msg}", page)
        update_data_view_status('error', context=error_msg)
        return {'success': False, 'message': error_msg, 'error': str(e)}


async def handle_placeholder_detection_analysis(current_df, col, desc, page):
    """Handle Placeholder Detection analysis with optimized performance and detailed output."""
    try:
        print(f"[DEBUG] Placeholder Detection: analyzing column='{col}', desc={desc}")
        print(f"[DEBUG] current_df shape: {current_df.shape if current_df is not None else 'None'}")
        
        # Performance estimation for user guidance
        total_rows = len(current_df)
        total_cols = len(current_df.columns) if col is None else 1
        
        # PERFORMANCE OPTIMIZATION: Add timing and progress feedback
        import time
        start_time = time.time()
        
        if total_rows > 100000:
            await write_output(f"[Placeholder Detection] 🔍 Analyzing large dataset ({total_rows:,} rows, {total_cols} columns) - this may take a moment...", page)
        elif total_rows > 10000:
            await write_output(f"[Placeholder Detection] 🔍 Analyzing {total_rows:,} rows across {total_cols} columns...", page)
        
        # Get placeholder data with optimized processing
        placeholder_df = analyze_placeholder_data(current_df, col)
        
        processing_time = time.time() - start_time
        print(f"[DEBUG] Placeholder Detection: Processing took {processing_time:.2f}s for {placeholder_df.shape[0]:,} columns")
        
        # Show processing time for slower operations
        if processing_time > 1.0:
            await write_output(f"[Performance] ⏱️ Analysis completed in {processing_time:.1f}s", page)
        print(f"[DEBUG] Placeholder Detection: got result with shape {placeholder_df.shape}")
        print(f"[DEBUG] Placeholder Detection: columns = {list(placeholder_df.columns)}")
        
        if desc:
            placeholder_df = placeholder_df.sort_values('Total Placeholder Count', ascending=False)
        
        # Update the data table with analysis results
        update_data_table(placeholder_df, page, is_paginated=True)
        
        # Calculate status with comprehensive reporting
        if data_view_widget:
            if not placeholder_df.empty:
                total_columns = len(placeholder_df)
                total_placeholders = placeholder_df['Total Placeholder Count'].sum()
                total_clean_types = placeholder_df['Unique Clean Types'].sum()
                total_dirty_types = placeholder_df['Unique Dirty Types'].sum()
                
                context = f"Found {total_placeholders:,} placeholders ({total_clean_types + total_dirty_types} unique types) across {total_columns} columns"
            else:
                context = "No placeholders found in any columns"
                
            data_view_widget.update_status_message('analysis', 
                                                 analysis_type="Placeholder Detection", 
                                                 context=context)
        
        # Enhanced output summary to console
        if not placeholder_df.empty:
            total_placeholders = placeholder_df['Total Placeholder Count'].sum()
            total_clean_placeholders = placeholder_df['Clean Placeholders Count'].sum()
            total_dirty_placeholders = placeholder_df['Dirty Placeholders Count'].sum()
            affected_columns = len(placeholder_df[placeholder_df['Total Placeholder Count'] > 0])
            total_columns_analyzed = len(placeholder_df)
            
            await write_output(f"[Placeholder Detection] ✅ Analyzed {total_columns_analyzed} columns - {total_placeholders:,} placeholders found", page)
            await write_output(f"[Breakdown] Clean: {total_clean_placeholders:,} | Dirty: {total_dirty_placeholders:,} | Affected columns: {affected_columns}", page)
            
            if total_placeholders > 0:
                # Calculate severity levels for placeholders
                high_placeholder = placeholder_df[placeholder_df['Total Percentage'] > 25]
                medium_placeholder = placeholder_df[(placeholder_df['Total Percentage'] > 5) & (placeholder_df['Total Percentage'] <= 25)]
                low_placeholder = placeholder_df[(placeholder_df['Total Percentage'] > 0) & (placeholder_df['Total Percentage'] <= 5)]
                
                if len(high_placeholder) > 0:
                    await write_output(f"🔴 High: {len(high_placeholder)} columns with >25% placeholders", page)
                if len(medium_placeholder) > 0:
                    await write_output(f"🟡 Medium: {len(medium_placeholder)} columns with 5-25% placeholders", page)
                if len(low_placeholder) > 0:
                    await write_output(f"🟢 Low: {len(low_placeholder)} columns with <5% placeholders", page)
                
                # Show top columns with placeholders (enhanced details)
                top_columns = placeholder_df[placeholder_df['Total Placeholder Count'] > 0].head(5)  # Show top 5
                await write_output(f"[Top Placeholder Columns]", page)
                for _, row in top_columns.iterrows():
                    severity = "🔴 High" if row['Total Percentage'] > 25 else "🟡 Medium" if row['Total Percentage'] > 5 else "🟢 Low"
                    await write_output(f"  {severity} | {row['Column']}: {row['Total Placeholder Count']:,} placeholders ({row['Total Percentage']:.1f}%)", page)
                    
                    # Show breakdown of clean vs dirty placeholders
                    if row['Clean Placeholders Count'] > 0:
                        await write_output(f"    Clean: {row['Clean Placeholders Count']:,} ({row['Clean Percentage']:.1f}%) | Types: {row['Unique Clean Types']}", page)
                    if row['Dirty Placeholders Count'] > 0:
                        await write_output(f"    Dirty: {row['Dirty Placeholders Count']:,} ({row['Dirty Percentage']:.1f}%) | Types: {row['Unique Dirty Types']}", page)
                    
                    # Show sample placeholders (limited for readability)
                    if row['Clean Placeholders'] != "None":
                        clean_preview = row['Clean Placeholders'][:80] + ("..." if len(row['Clean Placeholders']) > 80 else "")
                        await write_output(f"    Clean samples: {clean_preview}", page)
                    
                # Data quality recommendations
                placeholder_rate = total_placeholders / total_rows
                if placeholder_rate > 0.2:
                    await write_output(f"💡 Data Quality Alert: High placeholder rate ({placeholder_rate*100:.1f}%). Consider data cleaning.", page)
                elif total_dirty_placeholders > total_clean_placeholders:
                    await write_output(f"💡 Tip: More dirty ({total_dirty_placeholders:,}) than clean ({total_clean_placeholders:,}) placeholders. Consider data standardization.", page)
                else:
                    await write_output(f"💡 Data Quality: Placeholder usage appears controlled - mostly clean standard formats.", page)
            
        else:
            await write_output("✅ Excellent! No placeholders detected in any columns", page)
            await write_output("💡 Your dataset uses consistent, meaningful values throughout", page)
        
        return {
            'success': True,
            'message': f"Placeholder detection completed: {len(placeholder_df)} columns analyzed",
            'data_df': placeholder_df
        }
    except Exception as e:
        error_msg = f"Placeholder Detection analysis failed: {str(e)}"
        import traceback
        traceback.print_exc()
        await write_output(f"[Error] {error_msg}", page)
        if data_view_widget:
            data_view_widget.update_status_message('error', context=error_msg)
        return {'success': False, 'message': error_msg, 'error': str(e)}


async def handle_special_character_analysis(current_df, col, desc, page):
    """Handle Special Character Analysis with optimized performance and detailed output."""
    try:
        print(f"[DEBUG] Special Character Analysis: analyzing column='{col}', desc={desc}")
        print(f"[DEBUG] current_df shape: {current_df.shape if current_df is not None else 'None'}")
        
        # Performance estimation for user guidance
        total_rows = len(current_df)
        total_cols = len(current_df.columns) if col is None else 1
        
        # PERFORMANCE OPTIMIZATION: Add timing and progress feedback
        import time
        start_time = time.time()
        
        if total_rows > 50000:
            await write_output(f"[Special Character Analysis] 🔍 Analyzing large dataset ({total_rows:,} rows) - this may take a moment...", page)
        elif total_rows > 10000:
            await write_output(f"[Special Character Analysis] 🔍 Analyzing {total_rows:,} rows...", page)
        
        # Get special character data with optimized processing
        char_df = analyze_special_characters(current_df, col)
        
        processing_time = time.time() - start_time
        print(f"[DEBUG] Special Character Analysis: Processing took {processing_time:.2f}s for {char_df.shape[0]:,} columns")
        
        # Show processing time for slower operations
        if processing_time > 1.0:
            await write_output(f"[Performance] ⏱️ Analysis completed in {processing_time:.1f}s", page)
        print(f"[DEBUG] Special Character Analysis: got result with shape {char_df.shape}")
        print(f"[DEBUG] Special Character Analysis: columns = {list(char_df.columns)}")
        
        if desc:
            char_df = char_df.sort_values('Total Unique Special Chars', ascending=False)
        
        # Quick data table update
        update_data_table(char_df, page, is_paginated=True)
        
        # Calculate status with detailed reporting
        if data_view_widget:
            if not char_df.empty:
                total_columns = len(char_df)
                total_unique_chars = char_df['Total Unique Special Chars'].sum()
                total_instances = char_df['Total Special Char Instances'].sum()
                ascii_chars_found = char_df['ASCII Special Count'].sum()
                non_ascii_chars_found = char_df['Non-ASCII Special Count'].sum()
                control_chars_found = char_df['ASCII Control Count'].sum()
                
                context = f"Found {total_unique_chars} unique special characters ({total_instances:,} total instances) across {total_columns} columns"
                
                # Enhanced console output with more details
                await write_output(f"[Special Character Analysis] ✅ {context}", page)
                await write_output(f"[Character Breakdown] ASCII: {ascii_chars_found}, Non-ASCII: {non_ascii_chars_found}, Control: {control_chars_found}", page)
                
                # Show top 3 columns with special characters for better insights
                top_columns = char_df.nlargest(3, 'Total Unique Special Chars')
                for _, row in top_columns.iterrows():
                    if row['Total Unique Special Chars'] > 0:
                        await write_output(f"[Column: {row['Column']}] {row['Total Unique Special Chars']} unique chars, {row['Rows with Special Characters']:,} rows affected ({row['Percentage Rows with Specials']:.1f}%)", page)
                        
                        # Show most frequent character for context
                        if row['Most Frequent Special Char'] != "None":
                            await write_output(f"  Most frequent: {row['Most Frequent Special Char']}", page)
                        
                        # Show character breakdown for this column (limited for readability)
                        if row['ASCII Special Characters'] != "None":
                            ascii_preview = row['ASCII Special Characters'][:50] + ("..." if len(row['ASCII Special Characters']) > 50 else "")
                            await write_output(f"  ASCII Special: {ascii_preview}", page)
                        if row['Non-ASCII Special Characters'] != "None":
                            non_ascii_preview = row['Non-ASCII Special Characters'][:50] + ("..." if len(row['Non-ASCII Special Characters']) > 50 else "")
                            await write_output(f"  Non-ASCII: {non_ascii_preview}", page)
                            
                # Performance tip for large datasets
                if total_instances > 10000:
                    await write_output(f"💡 Performance Tip: Large number of special characters detected. Consider data cleaning for better performance.", page)
                    
            else:
                context = "No special characters found in any columns"
                await write_output("[Special Character Analysis] ✅ No special characters detected in any columns", page)
                await write_output("💡 Data appears to be using standard ASCII characters only", page)
                
            data_view_widget.update_status_message('analysis', 
                                                 analysis_type="Special Character Analysis", 
                                                 context=context)
        
        return {
            'success': True,
            'message': f"Special character analysis completed: {len(char_df)} columns analyzed",
            'data_df': char_df
        }
    except Exception as e:
        error_msg = f"Special Character Analysis failed: {str(e)}"
        import traceback
        traceback.print_exc()
        await write_output(f"[Error] {error_msg}", page)
        if data_view_widget:
            data_view_widget.update_status_message('error', context=error_msg)
        return {'success': False, 'message': error_msg, 'error': str(e)}


async def handle_duplicate_detection_analysis(current_df, col, desc, page):
    """Handle Duplicate Detection analysis with performance optimization and comprehensive error handling."""
    try:
        print(f"[DEBUG] Duplicate Detection: analyzing column='{col}', desc={desc}")
        print(f"[DEBUG] current_df shape: {current_df.shape if current_df is not None else 'None'}")
        
        # Performance estimation for user guidance
        total_rows = len(current_df)
        total_cols = len(current_df.columns) if col is None else 1
        
        # PERFORMANCE OPTIMIZATION: Add timing and progress feedback
        import time
        start_time = time.time()
        
        if total_rows > 100000:
            await write_output(f"[Duplicate Detection] 🔍 Analyzing large dataset ({total_rows:,} rows, {total_cols} columns) - this may take a moment...", page)
        elif total_rows > 10000:
            await write_output(f"[Duplicate Detection] 🔍 Analyzing {total_rows:,} rows across {total_cols} columns...", page)
        
        # Get duplicate data with optimized processing
        duplicates_df = analyze_duplicates_by_column(current_df, col)
        
        processing_time = time.time() - start_time
        print(f"[DEBUG] Duplicate Detection: Processing took {processing_time:.2f}s for {duplicates_df.shape[0]:,} columns")
        
        # Show processing time for slower operations
        if processing_time > 1.0:
            await write_output(f"[Performance] ⏱️ Analysis completed in {processing_time:.1f}s", page)
        print(f"[DEBUG] Duplicate Detection: got result with shape {duplicates_df.shape}")
        print(f"[DEBUG] Duplicate Detection: columns = {list(duplicates_df.columns)}")
        
        if desc:
            duplicates_df = duplicates_df.sort_values('Total Duplicate Count', ascending=False)
        
        # Update the data table with analysis results
        update_data_table(duplicates_df, page, is_paginated=True)
        
        # Calculate and update status with detailed context
        if data_view_widget:
            if not duplicates_df.empty:
                total_columns = len(duplicates_df)
                total_duplicates = duplicates_df['Total Duplicate Count'].sum()
                total_unique_patterns = duplicates_df['Unique Duplicate Patterns'].sum()
                context = f"Found {total_duplicates:,} duplicates ({total_unique_patterns} unique patterns) across {total_columns} columns"
            else:
                context = "No duplicates found in any columns"
                
            data_view_widget.update_status_message('analysis', 
                                                 analysis_type="Duplicate Detection", 
                                                 context=context)
        
        # Enhanced output summary to console
        if not duplicates_df.empty:
            total_duplicates = duplicates_df['Total Duplicate Count'].sum()
            total_patterns = duplicates_df['Unique Duplicate Patterns'].sum()
            affected_columns = len(duplicates_df[duplicates_df['Total Duplicate Count'] > 0])
            total_columns_analyzed = len(duplicates_df)
            total_unique_values = duplicates_df['Unique Values'].sum()
            
            await write_output(f"[Duplicate Detection] ✅ Analyzed {total_columns_analyzed} columns - {total_duplicates:,} duplicates found", page)
            await write_output(f"[Summary] Patterns: {total_patterns:,} | Affected columns: {affected_columns} | Total unique values: {total_unique_values:,}", page)
            
            if total_duplicates > 0:
                # Calculate severity levels for duplicates
                high_duplicate = duplicates_df[duplicates_df['Duplicate Percentage'] > 50]
                medium_duplicate = duplicates_df[(duplicates_df['Duplicate Percentage'] > 10) & (duplicates_df['Duplicate Percentage'] <= 50)]
                low_duplicate = duplicates_df[(duplicates_df['Duplicate Percentage'] > 0) & (duplicates_df['Duplicate Percentage'] <= 10)]
                
                if len(high_duplicate) > 0:
                    await write_output(f"🔴 High: {len(high_duplicate)} columns with >50% duplicates", page)
                if len(medium_duplicate) > 0:
                    await write_output(f"🟡 Medium: {len(medium_duplicate)} columns with 10-50% duplicates", page)
                if len(low_duplicate) > 0:
                    await write_output(f"🟢 Low: {len(low_duplicate)} columns with <10% duplicates", page)
                
                # Show top columns with duplicates (enhanced details)
                top_columns = duplicates_df[duplicates_df['Total Duplicate Count'] > 0].head(5)  # Show top 5
                await write_output(f"[Top Duplicate Columns]", page)
                for _, row in top_columns.iterrows():
                    severity = "🔴 High" if row['Duplicate Percentage'] > 50 else "🟡 Medium" if row['Duplicate Percentage'] > 10 else "🟢 Low"
                    uniqueness_ratio = row['Unique Values'] / row['Total Rows Analyzed'] * 100
                    await write_output(f"  {severity} | {row['Column']}: {row['Total Duplicate Count']:,} duplicates ({row['Duplicate Percentage']:.1f}%)", page)
                    await write_output(f"    Patterns: {row['Unique Duplicate Patterns']:,} | Uniqueness: {uniqueness_ratio:.1f}% | Non-duplicate: {row['Non-Duplicate Rows']:,}", page)
                    
                    # Show sample duplicates (limited for readability)
                    if row['Sample Duplicates'] != "None" and len(row['Sample Duplicates']) > 0:
                        sample_preview = row['Sample Duplicates'][:100] + ("..." if len(row['Sample Duplicates']) > 100 else "")
                        await write_output(f"    Samples: {sample_preview}", page)
                
                # Data quality recommendations
                duplicate_rate = total_duplicates / total_rows
                if duplicate_rate > 0.3:
                    await write_output(f"💡 Data Quality Alert: High duplication rate ({duplicate_rate*100:.1f}%). Consider deduplication strategies.", page)
                elif affected_columns > total_columns_analyzed * 0.5:
                    await write_output(f"💡 Tip: Duplicates found in {affected_columns}/{total_columns_analyzed} columns. Review data collection processes.", page)
                else:
                    await write_output(f"💡 Data Quality: Acceptable duplication levels - only {affected_columns}/{total_columns_analyzed} columns affected.", page)
                    
                # Uniqueness insights
                avg_uniqueness = (duplicates_df['Unique Values'] / duplicates_df['Total Rows Analyzed']).mean() * 100
                await write_output(f"📊 Dataset Uniqueness: Average {avg_uniqueness:.1f}% unique values per column", page)
                
        else:
            await write_output("✅ Excellent! No duplicates detected in any columns", page)
            await write_output("💡 Your dataset has perfect uniqueness - no duplicate values found", page)
        
        return {
            'success': True,
            'message': f"Duplicate detection completed: {len(duplicates_df)} columns analyzed",
            'data_df': duplicates_df
        }
    except Exception as e:
        error_msg = f"Duplicate Detection analysis failed: {str(e)}"
        import traceback
        traceback.print_exc()
        await write_output(f"[Error] {error_msg}", page)
        if data_view_widget:
            data_view_widget.update_status_message('error', context=error_msg)
        return {'success': False, 'message': error_msg, 'error': str(e)}


# SEAN FEATURE BUILDOUT BLOCK-----------------------------------------------------------------


async def analysis_handler(e: ft.ControlEvent):
    global app_busy, data_loaded, current_df  # Enhanced global declarations
    page = e.page
    
    print(f"[DEBUG] analysis_handler called: data_loaded={data_loaded}")

    # Enhanced data validation with helpful suggestions
    if not data_loaded:
        await write_output("❌ [Error] Load data first before running analysis.", page)
        await write_output("💡 Try this instead: Click the 'Load Data' button to import your CSV, Excel, or TXT file", page)
        await write_output("📁 Supported formats: .csv, .xlsx, .xls, .txt (tab-separated)", page)
        return

    if current_df is None or current_df.empty:
        await write_output("❌ [Error] No valid data loaded. Please load a dataset first.", page)
        await write_output("💡 Try this instead: Use 'Load Data' button and select a file with actual data", page)
        await write_output("🔍 Make sure your file isn't empty and has proper headers", page)
        return

    # Add debouncing for regular analysis button clicks
    current_time = time.time()
    
    if not hasattr(analysis_handler, '_last_execution'):
        analysis_handler._last_execution = 0
    
    last_time = analysis_handler._last_execution
    cooldown_period = 1.0  # 1 second cooldown for regular analysis
    
    if current_time - last_time < cooldown_period:
        await write_output(f"[Info] ⏱️ Please wait {cooldown_period - (current_time - last_time):.1f}s before running another analysis.", page)
        return
    
    analysis_handler._last_execution = current_time

    # Check if app is already busy with another analysis
    if app_busy:
        await write_output("[Info] ⏳ Analysis already in progress. Please wait...", page)
        return

    # Enhanced dataset validation
    try:
        dataset_rows, dataset_cols = current_df.shape
        await write_output(f"[Analysis] 🚀 Starting analysis on dataset: {dataset_rows:,} rows × {dataset_cols} columns", page)
    except Exception as validation_error:
        await write_output(f"[Error] Failed to validate dataset: {str(validation_error)}", page)
        return

    # Pull the widgets out of dialog_controls
    ad = dialog_controls["analysis_dropdown"]
    cd = dialog_controls["column_dropdown"]
    ri = dialog_controls["rows_input"]
    ss = dialog_controls["sort_switch"]

    # Read their values with enhanced validation
    atype = ad.value
    col = cd.value if cd.value != "All Columns" else None

    # Validate analysis type with suggestions
    if not atype:
        await write_output("❌ [Error] Please select an analysis type.", page)
        await write_output("💡 Try this instead: Use the 'Analysis Type' dropdown to choose what you want to analyze", page)
        await write_output("📋 Recommended for beginners: Start with 'Data Preview' to see your data structure", page)
        return

    # Validate column selection for single-column analyses with helpful guidance
    if col and col not in current_df.columns:
        available_cols = list(current_df.columns)[:5]  # Show first 5 columns
        await write_output(f"❌ [Error] Column '{col}' not found in dataset.", page)
        await write_output(f"💡 Try this instead: Choose from available columns: {available_cols}{'...' if len(current_df.columns) > 5 else ''}", page)
        await write_output("🔍 Tip: Use 'All Columns' to analyze the entire dataset", page)
        return

    try:
        # Try to get the value from the text field first
        field_value = ri.value
        print(f"[DEBUG] Analysis handler: rows_input.value = '{field_value}'")
        
        # Also check our tracking variable as a fallback
        current_row_count = dialog_controls.get("current_row_count", {"value": 50})
        tracked_value = current_row_count["value"]
        print(f"[DEBUG] Analysis handler: tracked row count = {tracked_value}")
        
        # Handle "Show All" cases
        if field_value and field_value.strip().lower() in ["show all", "all", "showall"]:
            num = -1  # Special value for "show all"
            print(f"[DEBUG] Analysis handler: Show All requested")
        elif tracked_value == -1:
            num = -1
            print(f"[DEBUG] Analysis handler: Show All from tracking variable")
        elif field_value and field_value.strip():
            num = int(field_value)
        else:
            print(f"[DEBUG] Analysis handler: Using tracked value as fallback")
            num = tracked_value
            
        print(f"[DEBUG] Analysis handler: Final parsed num = {num}")
        
        # Validation for normal row counts (skip validation for "Show All") with helpful suggestions
        if num != -1:
            if num <= 0:
                await write_output("❌ [Error] Number of rows must be a positive integer (1 or greater).", page)
                await write_output("💡 Try this instead: Enter a positive number like 10, 100, 500, or 1000", page)
                await write_output("🎯 Quick fix: Use the preset buttons below the input field (10, 100, 500, 1K, 5K, All)", page)
                return
            if num > 1000000:  # 1 million row limit for safety
                await write_output("❌ [Error] Maximum 1,000,000 rows allowed for performance reasons.", page)
                await write_output("💡 Try this instead: Use a smaller number like 10000 or 50000 for large datasets", page)
                await write_output("🚀 Alternative: Use 'Show All' button for complete dataset analysis (may be slow)", page)
                return
            
            # Smart validation warnings
            if num > 50000:
                await write_output(f"⚠️ Large preview requested ({num:,} rows) - this may take time to load", page)
            elif num > 10000:
                await write_output(f"ℹ️ Medium preview requested ({num:,} rows) - loading...", page)
        else:
            # "Show All" case
            await write_output("🔍 Showing ALL rows - this may take time for large datasets", page)
            
    except ValueError as ve:
        print(f"[DEBUG] Analysis handler: Failed to parse rows_input value = '{field_value}', error: {ve}")
        await write_output("❌ [Error] Rows must be a valid number (e.g., 10, 100, 1000).", page)
        await write_output("💡 Try this instead: Enter a whole number like 50, 100, or 500", page)
        await write_output("🎯 Quick fix: Use the preset buttons for common values: 10, 100, 500, 1K, 5K, All", page)
        await write_output("📝 Or type 'Show All' to display the entire dataset", page)
        return

    desc = ss.value

    # Run the analysis on a background thread with performance timing
    app_busy = True
    analysis_start_time = time.time()
    
    # PERFORMANCE OPTIMIZATION: Reduce UI update frequency during analysis
    print(f"[DEBUG] Analysis handler: Starting {atype} analysis at {analysis_start_time}")
    
    # Log user action for recommendation engine
    recommendation_engine.log_user_action(atype)
    
    # PERFORMANCE OPTIMIZATION: Single status update instead of multiple
    if enhanced_data_view or data_view_widget:
        progress_messages = {
            "Data Preview": "🔍 Generating enhanced data preview...",
            "Missing Values": "🔍 Analyzing missing values...",
            "Duplicate Detection": "🔍 Detecting duplicates...",
            "Placeholder Detection": "🔍 Scanning for placeholders...",
            "Special Character Analysis": "🔍 Analyzing special characters..."
        }
        progress_msg = progress_messages.get(atype, f"🔍 Running {atype}...")
        update_data_view_status('processing', operation=progress_msg)
    
    # Switch to Data View tab when running analysis (single tab switch)
    focus_dataview_tab(page)
    
    # Function-based analysis dispatcher - Clean and maintainable with enhanced error handling!
    analysis_functions = {
        "Data Preview": handle_data_preview_analysis,
        "Missing Values": handle_missing_values_analysis,
        "Placeholder Detection": handle_placeholder_detection_analysis,
        "Special Character Analysis": handle_special_character_analysis,
        "Duplicate Detection": handle_duplicate_detection_analysis,
    }
    
    # Execute the appropriate analysis function with enhanced error handling
    if atype in analysis_functions:
        try:
            # PERFORMANCE OPTIMIZATION: Minimize console output during analysis
            analysis_func = analysis_functions[atype]
            print(f"[{atype}] Analysis started at {time.time()}")
            
            if atype == "Data Preview":
                result = await analysis_func(current_df, num, desc, col, page)
            else:
                result = await analysis_func(current_df, col, desc, page)
            
            # PERFORMANCE OPTIMIZATION: Calculate and report performance efficiently
            analysis_duration = time.time() - analysis_start_time
            
            if analysis_duration < 1.0:
                performance_icon = "🟢"
                performance_level = "Fast"
            elif analysis_duration < 3.0:
                performance_icon = "🟡"
                performance_level = "Good"
            else:
                performance_icon = "🔴"
                performance_level = "Slow"
            
            # PERFORMANCE OPTIMIZATION: Single consolidated result message
            if result['success']:
                await write_output(f"[{atype}] ✅ {result['message']} | {performance_icon} {performance_level} ({analysis_duration:.1f}s)", page)
            else:
                await write_output(f"[{atype}] ❌ {result['message']} | Time: {analysis_duration:.1f}s", page)
                
        except Exception as e:
            analysis_duration = time.time() - analysis_start_time
            error_msg = f"Analysis failed: {str(e)}"
            print(f"[ERROR] {atype} analysis failed after {analysis_duration:.1f}s: {e}")
            import traceback
            traceback.print_exc()
            await write_output(f"[Error] ❌ {error_msg} | Time: {analysis_duration:.1f}s", page)
            update_data_view_status('error', context=error_msg)
            error_msg = f"Analysis function failed for {atype}: {str(e)}"
            import traceback
            traceback.print_exc()
            await write_output(f"[Error] ❌ {error_msg} | Failed after {analysis_duration:.2f}s", page)
            update_data_view_status('error', context=error_msg)
    else:
        await write_output(f"[Error] ❌ Unknown analysis type: '{atype}' | Available: {list(analysis_functions.keys())}", page)
    
    # Get enhanced contextual recommendations after analysis with error handling
    try:
        # Pass current data for better context awareness
        contextual_recs = recommendation_engine.get_contextual_recommendations(atype, current_df)
        if contextual_recs:
            rec_text = recommendation_engine.format_recommendations_for_ui(contextual_recs)
            await write_output("\n" + rec_text, page)
            
            # Update recommendations panel if it exists with interactive features
            rec_content = dialog_controls.get("recommendations_content")
            if rec_content:
                update_recommendations_panel(contextual_recs, rec_content, page, data_loaded, current_df, trigger_recommended_analysis_sync)
                print(f"[Recommendations] Updated panel with {len(contextual_recs)} context-aware recommendations")
        else:
            print(f"[Recommendations] No contextual recommendations for {atype}")
    except Exception as e:
        print(f"[DEBUG] Contextual recommendation generation failed: {e}")
        import traceback
        traceback.print_exc()
        # Don't let recommendation failures break the main analysis flow
    
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
        show_error("❌ Load data before searching", e.page)
        show_error("💡 Try this instead: Click 'Load Data' to import a file first", e.page)
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
        show_error("❌ Run a search first", e.page)
        show_error("💡 Try this instead: Use the search box above to find data, then try exporting", e.page)
        return
    global export_context
    export_context = "search"
    dialog_controls["export_picker"].save_file()


def export_analysis_text(e: ft.ControlEvent):
    if not dialog_controls.get("analysis_text"):
        show_error("❌ Run analysis first", e.page)
        show_error("💡 Try this instead: Select analysis type and click 'Analyze' to generate results first", e.page)
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
    global current_theme_mode, data_view_widget

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

    # Update Enhanced DataViewWidget theme
    if enhanced_data_view:
        enhanced_data_view.update_theme()
    elif data_view_widget:
        data_view_widget.update_theme()

    # Update recommendations panel theme
    try:
        recommendations_panel = dialog_controls.get("recommendations_panel")
        recommendations_content = dialog_controls.get("recommendations_content")
        if recommendations_panel and recommendations_content:
            refresh_recommendations_theme(recommendations_panel, recommendations_content, page)
            print(f"[Theme] Recommendations panel theme updated")
    except Exception as ex:
        print(f"[Theme] Error updating recommendations theme: {ex}")

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

    # Data root folder picker for Settings
    dialog_controls["data_root_picker"] = ft.FilePicker(on_result=set_custom_data_root)
    page.overlay.append(dialog_controls["data_root_picker"])
    
    # Initialize data root label and reset button
    default_data_path = str(Path.home() / "ProtexxaDatascope")
    dialog_controls["data_root_label"] = ft.Text(
        f"Default data folder: {default_data_path}",
        color=ft.Colors.GREY_700,
        size=12,
    )
    dialog_controls["reset_data_root_btn"] = ft.TextButton(
        "Reset to Default",
        on_click=lambda e: reset_custom_data_root(e.page),
        style=ft.ButtonStyle(color=ft.Colors.RED),
        tooltip="Use the default data folder location"
    )

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
    welcome_message = """🎉 Welcome to Protexxa DataScope v1.2! 

📋 QUICK START GUIDE:
1. Click "Load Data" to import your CSV, Excel, or TXT file
2. Choose an analysis type from the dropdown (Data Preview is great to start!)
3. Click "Run Analysis" to get insights about your data
4. Use the "Data View" tab to see results in multiple formats
5. Check the "Recommendations" panel for suggested next steps

💡 TIPS FOR BEGINNERS:
• Start with "Data Preview" to see your data structure
• Use "Missing Values" to check data quality
• Try the quick preset buttons (10, 100, 500 rows) for faster analysis
• Switch between themes using the "Settings" tab

❓ NEED HELP?
• Hover over any button or dropdown for helpful tooltips
• Error messages include "Try this instead" suggestions
• Each analysis type shows a description when selected

Ready to explore your data? Click "Load Data" to begin! ✨
"""
    
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
        value=welcome_message,
        tooltip="Console output - shows analysis results, progress updates, and helpful messages"
    )
    dialog_controls["progress_bar"] = ft.ProgressBar(
        width=700,
        height=10,
        bgcolor=ft.Colors.GREY_300,
        color=ft.Colors.BLUE,
        value=0,
        visible=False,
        tooltip="Shows progress for data loading and processing operations"
    )
    dialog_controls["progress_text"] = ft.Text(
        value="",
        size=12,
        color=ft.Colors.BLUE,
        text_align=ft.TextAlign.CENTER,
        visible=False,
        weight=ft.FontWeight.BOLD,
        tooltip="Displays current operation status and progress percentage"
    )

    # load / test buttons with enhanced tooltips
    btn_load = ft.ElevatedButton(
        text="Load Data",
        on_click=load_data_handler,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
        tooltip="📁 Load CSV, Excel, or TXT files for analysis\n• Supports auto-detection of encoding and delimiters\n• Shows file size warnings for large datasets\n• Creates backup and validation reports"
    )
    dialog_controls["btn_log"] = ft.ElevatedButton(
        text="Test Logging",
        on_click=logging_handler_test,
        disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
        tooltip="🔍 Test the logging system functionality\n• Validates log file creation\n• Checks error handling\n• Available after loading data"
    )
    dialog_controls["btn_data"] = ft.ElevatedButton(
        text="Test Data Handling",
        on_click=data_handler_test,
        disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
        tooltip="⚙️ Test data processing capabilities\n• Validates data integrity\n• Checks memory usage\n• Tests performance metrics\n• Available after loading data"
    )
    dialog_controls["btn_visual"] = ft.ElevatedButton(
        text="Test Visual Analyst",
        on_click=visual_analyst_test,
        disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
        tooltip="📊 Test data visualization features\n• Generates sample charts\n• Tests visualization engine\n• Validates chart exports\n• Available after loading data"
    )
    
    # Add a button to manually switch to Data View for testing
    btn_dataview = ft.ElevatedButton(
        text="View Data Table",
        on_click=lambda e: focus_dataview_tab(e.page),
        disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
        tooltip="📋 Switch to Data View tab to see analysis results\n• Shows data in table, text, and syntax-highlighted formats\n• Includes pagination and search features\n• Available after loading data"
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

    # 4) Advanced Tab Widgets (SEAN FEATURE BUILDOUT) - Enhanced with detailed help
    analysis_help = {
        "Data Preview": "📋 Show sample rows and data types.\n💡 What does this do? Displays the first N rows of your dataset so you can see the structure, column names, and data types. Perfect for getting familiar with your data!",
        "Missing Values": "🔍 Report null/empty value counts by column.\n💡 What does this do? Scans every column to find missing data (blanks, NaN, null values). Shows which columns need attention for data quality.",
        "Duplicate Detection": "🔄 Advanced duplicate analysis with statistics and insights.\n💡 What does this do? Finds duplicate values within each column and provides detailed statistics. Helps identify data quality issues and potential data entry errors.",
        "Placeholder Detection": "🏷️ Check for placeholder tokens and dummy data.\n💡 What does this do? Searches for common placeholder values like 'N/A', 'TBD', 'TODO', '-', etc. Helps identify incomplete or temporary data entries.",
        "Special Character Analysis": "🔤 Analyze ASCII and Non-ASCII special characters with frequencies.\n💡 What does this do? Examines text columns for special characters, symbols, and non-standard text. Useful for data cleaning and encoding issues.",
    }

    desc_text = ft.Text(
        value=analysis_help.get("Data Preview", ""), 
        size=12, 
        color=ft.Colors.BLUE_GREY_600,
        selectable=True,
        tooltip="Click to select this help text - it updates when you change analysis types"
    )
    dialog_controls["desc_text"] = desc_text

    def on_analysis_change(e: ft.ControlEvent):
        desc_text.value = analysis_help.get(e.control.value, "")
        e.page.update()

    analysis_dropdown = ft.Dropdown(
        label="Analysis Type",
        width=200,
        value="Data Preview",  # Set default value
        options=[
            ft.dropdown.Option("Data Preview"),
            ft.dropdown.Option("Missing Values"),
            ft.dropdown.Option("Duplicate Detection"),
            ft.dropdown.Option("Placeholder Detection"),
            ft.dropdown.Option("Special Character Analysis"),
        ],
        on_change=on_analysis_change,
        tooltip="🎯 Choose what type of analysis to run on your data\n• Each analysis provides different insights\n• Descriptions update when you change selections\n• Start with 'Data Preview' if you're new to your dataset",
    )
    column_dropdown = ft.Dropdown(
        label="Column", 
        width=200, 
        value="All Columns", 
        options=[ft.dropdown.Option("All Columns")],
        tooltip="📊 Select specific column to analyze\n• 'All Columns': Analyze the entire dataset\n• Specific column: Focus analysis on one column\n• Options populate after loading data"
    )
    
    # Quick preset buttons for common row counts - Enhanced approach
    # Store current row count in a shared variable to ensure consistency
    current_row_count = {"value": 50}  # Use a dict to make it mutable
    
    def on_rows_input_change(e):
        """Handle manual changes to the rows input field"""
        global data_loaded  # Add global declaration
        try:
            input_value = e.control.value.strip()
            
            # Handle "Show All" text input
            if input_value.lower() in ["show all", "all", "showall"]:
                new_value = -1
                print(f"[DEBUG] Manual input change: Show All rows")
            else:
                new_value = int(input_value)
                print(f"[DEBUG] Manual input change: Set rows to {new_value}")
                
            current_row_count["value"] = new_value
            print(f"[DEBUG] data_loaded = {data_loaded}")
            
            # Auto-trigger analysis if data is loaded - Fixed async handling
            if data_loaded and (new_value > 0 or new_value == -1):
                if new_value == -1:
                    print(f"[DEBUG] Auto-triggering analysis to show ALL rows")
                else:
                    print(f"[DEBUG] Auto-triggering analysis with {new_value} rows")
                # Use page's run_task method with proper async handling
                async def trigger_analysis():
                    await asyncio.sleep(0.1)  # 100ms delay
                    await analysis_handler(e)
                
                try:
                    e.page.run_task(trigger_analysis)
                except Exception as ex:
                    print(f"[DEBUG] Failed to trigger analysis: {ex}")
                    # Fallback: try direct call without delay
                    try:
                        asyncio.create_task(analysis_handler(e))
                    except:
                        print(f"[DEBUG] Fallback also failed, analysis not triggered")
            else:
                if not data_loaded:
                    print(f"[DEBUG] Cannot auto-trigger: No data loaded yet")
                else:
                    print(f"[DEBUG] Cannot auto-trigger: Invalid row count {new_value}")
                
        except (ValueError, TypeError) as ex:
            # Invalid input, keep the old value
            print(f"[DEBUG] Invalid input in rows field: '{e.control.value}' - {ex}")
            pass
    
    rows_input = ft.TextField(
        label="Rows to show", 
        value="50", 
        width=150, 
        hint_text="Enter number or 'Show All'",
        tooltip="📝 How many rows to display in the analysis\n• Enter any number (e.g., 10, 100, 1000)\n• Type 'Show All' to display entire dataset\n• Use preset buttons below for common values\n• Larger numbers may take longer to process",
        suffix_text="rows",
        on_change=on_rows_input_change,  # Triggers on every keystroke/change
        on_submit=on_rows_input_change,  # Triggers when Enter is pressed
    )
    
    def set_rows_preset(count):
        def handler(e):
            global data_loaded  # Add global declaration
            # Update both the UI and our tracking variable
            current_row_count["value"] = count
            
            # Handle "Show All" case
            if count == -1:
                rows_input.value = "Show All"
                print(f"[DEBUG] Preset button clicked: Show All rows")
            else:
                rows_input.value = str(count)
                print(f"[DEBUG] Preset button clicked: Set rows to {count}")
                
            print(f"[DEBUG] current_row_count is now: {current_row_count['value']}")
            print(f"[DEBUG] rows_input.value is now: '{rows_input.value}'")
            print(f"[DEBUG] data_loaded = {data_loaded}")
            
            # Force complete page refresh to ensure UI updates
            e.page.update()
            
            # Auto-trigger analysis if data is loaded - Fixed async handling
            if data_loaded:
                if count == -1:
                    print(f"[DEBUG] Auto-triggering analysis to show ALL rows")
                else:
                    print(f"[DEBUG] Auto-triggering analysis with {count} rows")
                # Use page's run_task method with proper async handling
                async def trigger_analysis():
                    await asyncio.sleep(0.1)  # 100ms delay
                    await analysis_handler(e)
                
                try:
                    e.page.run_task(trigger_analysis)
                except Exception as ex:
                    print(f"[DEBUG] Failed to trigger analysis: {ex}")
                    # Fallback: try direct call without delay
                    try:
                        asyncio.create_task(analysis_handler(e))
                    except:
                        print(f"[DEBUG] Fallback also failed, analysis not triggered")
            else:
                print(f"[DEBUG] Data not loaded, skipping auto-trigger")
            
        return handler
    
    # Store the current_row_count reference for the analysis handler to use
    dialog_controls["current_row_count"] = current_row_count
    
    preset_buttons = ft.Row([
        ft.TextButton("10", on_click=set_rows_preset(10), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), tooltip="📊 Quick view - Show 10 rows\n• Perfect for initial data exploration\n• Fast loading time\n• Good for checking data structure"),
        ft.TextButton("100", on_click=set_rows_preset(100), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), tooltip="📋 Standard view - Show 100 rows\n• Most common analysis size\n• Good balance of detail and speed\n• Recommended for most analyses"),
        ft.TextButton("500", on_click=set_rows_preset(500), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), tooltip="📈 Detailed view - Show 500 rows\n• More comprehensive analysis\n• Good for pattern detection\n• May take a moment to load"),
        ft.TextButton("1K", on_click=set_rows_preset(1000), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), tooltip="🔍 Large view - Show 1,000 rows\n• Thorough analysis\n• Good for statistical reliability\n• Processing time may increase"),
        ft.TextButton("5K", on_click=set_rows_preset(5000), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), tooltip="🚀 Extended view - Show 5,000 rows\n• Comprehensive analysis\n• Good for large dataset insights\n• Longer processing time expected"),
        ft.TextButton("Show All", on_click=set_rows_preset(-1), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), color=ft.Colors.GREEN), tooltip="🌟 Complete view - Show ALL rows\n• Analyzes entire dataset\n• No row limits applied\n• May take significant time for large files\n• Best for complete data assessment")
    ], spacing=5)
    
    rows_container = ft.Column([
        rows_input,
        ft.Text("Quick presets:", size=10, color=ft.Colors.BLUE_GREY_600, tooltip="Click any preset button to instantly set the number of rows to analyze"),
        preset_buttons
    ], spacing=5)
    sort_switch = ft.Switch(label="Descending order", value=False, tooltip="⬇️ Sort results in descending order\n• ON: Shows largest/newest values first\n• OFF: Shows smallest/oldest values first\n• Applies to Data Preview analysis")
    run_btn = ft.ElevatedButton("Run Analysis", on_click=analysis_handler, tooltip="▶️ Execute the selected analysis\n• Processes your data based on current settings\n• Results appear in Data View tab\n• Check console for progress updates\n• Switch to Data View automatically when done")

    # stash for the handler
    dialog_controls["analysis_dropdown"] = analysis_dropdown
    dialog_controls["column_dropdown"] = column_dropdown
    dialog_controls["rows_input"] = rows_input
    dialog_controls["sort_switch"] = sort_switch
    dialog_controls["run_btn"] = run_btn
    dialog_controls["match_label"] = ft.Text("0/0", tooltip="Shows current search match position (e.g., '3 of 15 matches')")

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
        tooltip="🔤 File text encoding\n• Auto-Detect: Automatically determines encoding (recommended)\n• UTF-8: Standard for most modern files\n• Latin1: Common for older files\n• Use Auto-Detect unless you have encoding issues",
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
        tooltip="📋 Field separator character\n• Auto: Automatically detects delimiter (recommended)\n• , (comma): Most common CSV delimiter\n• \\t (tab): Tab-separated values\n• ; (semicolon): European CSV files\n• | (pipe): Alternative separator",
    )
    dialog_controls["delim_dropdown"] = delim_dropdown

    search_term = ft.TextField(
        label="Search term", 
        width=200, 
        tooltip="🔍 Enter text to find in your data\n• Search across all columns or specific column\n• Press Enter to start search\n• Case-sensitive option available\n• Supports partial and whole word matching",
        on_submit=on_search,  # Allow search on Enter key
    )
    search_column = ft.Dropdown(
        label="Search Column", 
        width=150, 
        options=[ft.dropdown.Option("All Columns")],
        tooltip="📊 Choose where to search\n• All Columns: Search entire dataset\n• Specific column: Focus search on one column\n• Options update after loading data"
    )
    case_switch = ft.Switch(
        label="Case", 
        value=False,
        tooltip="🔤 Case-sensitive search\n• ON: 'Apple' ≠ 'apple'\n• OFF: 'Apple' = 'apple'\n• Default: OFF (case-insensitive)"
    )
    whole_switch = ft.Switch(
        label="Whole", 
        value=False,
        tooltip="🎯 Whole word matching\n• ON: 'cat' won't match 'category'\n• OFF: 'cat' will match 'category'\n• Default: OFF (partial matching)"
    )
    search_btn = ft.ElevatedButton(
        text="Search", 
        on_click=on_search,
        tooltip="▶️ Start searching your data\n• Results show in Data View tab\n• Matching rows are highlighted\n• Use navigation buttons to browse results"
    )
    prev_btn = ft.IconButton(
        icon=ft.Icons.ARROW_BACK, 
        on_click=on_prev_match, 
        tooltip="⬅️ Go to previous search result\n• Navigate through found matches\n• Wraps to last result when at first"
    )
    next_btn = ft.IconButton(
        icon=ft.Icons.ARROW_FORWARD, 
        on_click=on_next_match, 
        tooltip="➡️ Go to next search result\n• Navigate through found matches\n• Wraps to first result when at last"
    )

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
        tooltip="💾 Choose export file format\n• CSV: Comma-separated values (universal)\n• XLSX: Excel format (preserves formatting)\n• CSV recommended for compatibility"
    )
    dialog_controls["export_fmt"] = export_fmt
    export_ds_btn = ft.ElevatedButton(
        "Export Dataset", 
        on_click=export_dataset, 
        tooltip="💾 Save the complete dataset\n• Exports all loaded data\n• Choose location and format\n• Preserves original data structure"
    )
    export_search_btn = ft.ElevatedButton(
        "Export Search", 
        on_click=export_search_results, 
        tooltip="🔍 Save search results\n• Exports only matching rows\n• Must run a search first\n• Includes highlighted matches"
    )
    export_analysis_btn = ft.ElevatedButton(
        "Export Analysis", 
        on_click=export_analysis_text, 
        tooltip="📊 Save analysis output\n• Exports console text results\n• Includes all analysis summaries\n• Saves as text file"
    )

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
                            ft.ElevatedButton(
                                text="📁 Open Chunks Folder",
                                on_click=open_chunk_folder,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
                                tooltip="Open the chunks folder in Windows Explorer"
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

    # Initialize the Enhanced DataViewWidget for clean data display
    global data_view_widget, enhanced_data_view, recommendations_panel, recommendations_content
    
    # Initialize both data view widgets for backward compatibility
    data_view_widget = DataViewWidget(page)
    enhanced_data_view = EnhancedDataView(page)
    
    # Initialize the recommendations panel
    recommendations_panel, recommendations_content = create_recommendations_panel(page)
    dialog_controls["recommendations_panel"] = recommendations_panel
    dialog_controls["recommendations_content"] = recommendations_content
    
    # Keep the container reference for compatibility during transition
    data_view_container = enhanced_data_view.get_widget()
    dialog_controls["data_view_container"] = data_view_container

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
                        ft.Row([
                            ft.Text("📊 Data View", style="titleMedium", color=ft.Colors.GREY_800),
                            ft.ElevatedButton(
                                text="📁 Open Data Folder",
                                on_click=open_data_folder,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)),
                                tooltip="Open the dataset project folder in Windows Explorer"
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        # --- Analysis Controls (added here) ---
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("🧮 Analysis Type", style="titleSmall", weight=ft.FontWeight.BOLD),
                                    ft.Row(
                                        [
                                            dialog_controls.get("analysis_dropdown"),
                                            dialog_controls.get("column_dropdown"),
                                            rows_container,
                                            dialog_controls.get("sort_switch"),
                                            dialog_controls.get("run_btn"),
                                        ],
                                        spacing=10,
                                        alignment=ft.MainAxisAlignment.START,
                                    ),
                                    dialog_controls.get("desc_text"),
                                ]
                            ),
                            padding=10,
                            border_radius=8,
                            margin=ft.margin.only(bottom=10),
                        ),
                        # --- End Analysis Controls ---
                        
                        # --- Smart Recommendations Panel ---
                        dialog_controls["recommendations_panel"],
                        
                        # Enhanced DataViewWidget - Multi-mode data display with table, text, and unstructured views (NO AI ASSISTANT)
                        enhanced_data_view.get_widget(),
                    ],
                    spacing=10,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,  # Enable vertical scrolling (CLEAN DATA VIEW - NO AI ASSISTANT)
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
                        ft.Divider(),
                        ft.Text("📁 Data Folder Location", weight=ft.FontWeight.BOLD, style=ft.TextThemeStyle.TITLE_SMALL),
                        dialog_controls["data_root_label"],
                        ft.Row([
                            ft.ElevatedButton(
                                "Choose Data Folder...",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=lambda e: dialog_controls["data_root_picker"].get_directory_path(),
                                tooltip="Select a custom folder for all datasets",
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                            ),
                            dialog_controls["reset_data_root_btn"],
                        ], spacing=10),
                        ft.Text(
                            "💡 Choose a custom folder to store all dataset environments and chunks.",
                            color=ft.Colors.GREY_600,
                            size=11,
                            italic=True,
                        ),
                    ],
                    spacing=10,
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
    
    # Ensure Enhanced Data View theme consistency after adding to page
    try:
        enhanced_data_view.ensure_theme_consistency()
    except Exception as e:
        print(f"[GUI] Enhanced Data View theme consistency error: {e}")
    main_container.opacity = 1.0
    
    # Set initial status message now that the widget is on the page
    update_data_view_status('ready')
    
    # Apply initial theme colors to containers
    apply_data_table_theme(page)
    
    page.update()


if __name__ == "__main__":
    ft.app(target=main, assets_dir=ASSETS_DIR)


