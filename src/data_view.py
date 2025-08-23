"""
Data View Widget Module

Clean separation of data display functionality from the main UI.
Handles DataTable creation, pagination, search, and all data view logic.
"""

import flet as ft
import pandas as pd
import threading
import time
import hashlib
from typing import Optional, Tuple, Any, Callable, Dict
from data_handler import get_paginated_data


class DataViewWidget:
    """Encapsulates all data view functionality in a clean, self-contained widget."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.current_df: Optional[pd.DataFrame] = None
        self.original_df: Optional[pd.DataFrame] = None  # Store original data for search restore
        self.current_page = 1
        self.rows_per_page = 25
        self.total_pages = 1
        self.search_term = ""
        self.search_column = "All Columns"
        self.search_results = None
        self.search_index = 0
        self.highlight_term: Optional[str] = None
        self.highlight_column: Optional[str] = None
        self.disable_pagination = False  # New flag to disable pagination for data previews
        
        # Real-time search settings
        self.is_searching = False
        
        # Enhanced performance optimization settings
        self.search_timer: Optional[threading.Timer] = None
        self.search_debounce_delay = 0.2  # Reduced to 200ms for faster response
        self.max_search_results = 1000  # Limit search results for performance
        self.search_visible_only = False  # Search only visible data by default
        self.last_search_time = 0
        self.min_search_length = 1  # Minimum characters to trigger search
        
        # Advanced caching for ultra-fast repeated searches
        self.search_cache: Dict[str, Tuple[list, int, float]] = {}  # {cache_key: (results, total_count, timestamp)}
        self.cache_max_age = 30.0  # Cache valid for 30 seconds
        self.cache_max_size = 100  # Maximum cached searches
        
        # Magnification support - dynamic font sizes
        self.current_magnification = 100  # Default 100%
        self.scaled_font_sizes = self._calculate_scaled_fonts(100)
        
        # Intelligent search optimization
        self.last_search_term = ""
        self.last_search_column = ""
        self.incremental_search = True  # Use previous results for incremental search
        self.search_performance_stats = {"fast_searches": 0, "cached_searches": 0, "total_searches": 0}
        
        # UI Components
        self.data_table: Optional[ft.DataTable] = None
        self.data_table_info: Optional[ft.Text] = None
        self.pagination_info: Optional[ft.Text] = None
        self.search_term_field: Optional[ft.TextField] = None
        self.search_column_dropdown: Optional[ft.Dropdown] = None
        self.match_label: Optional[ft.Text] = None
        self.search_status: Optional[ft.Text] = None  # New status indicator
        self.dynamic_status: Optional[ft.Text] = None  # Dynamic status message widget
        self.search_progress: Optional[ft.ProgressRing] = None  # Loading indicator
        
        # Main container
        self.container = self._create_container()
        
        print("[DataView] Widget initialized with real-time search and performance optimizations")
    
    def _create_container(self) -> ft.Container:
        """Create the main container with all data view components."""
        
        # Create info labels
        self.data_table_info = ft.Text(
            "No data loaded",
            style=ft.TextStyle(size=14, color=ft.Colors.GREY_600),
            weight=ft.FontWeight.NORMAL,
        )
        
        self.pagination_info = ft.Text(
            "",
            style=ft.TextStyle(size=14, color=ft.Colors.GREY_600),
            weight=ft.FontWeight.NORMAL,
        )
        
        # Create search components
        self.search_term_field = ft.TextField(
            label="Search term",
            width=200,
            height=40,
            on_change=self._on_search_change,
            hint_text="Type to search instantly...",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=10,
        )
        
        self.search_column_dropdown = ft.Dropdown(
            label="Column",
            width=150,
            options=[ft.dropdown.Option("All Columns")],
            value="All Columns",
            on_change=self._on_column_change,
        )
        
        # Add search option switches
        self.case_sensitive_switch = ft.Switch(
            label="Case sensitive",
            value=False,
            on_change=self._on_search_option_change,
            tooltip="Match exact case (A ≠ a)",
        )
        
        self.whole_word_switch = ft.Switch(
            label="Whole words",
            value=False,
            on_change=self._on_search_option_change,
            tooltip="Match complete words only",
        )
        
        self.match_label = ft.Text("0/0", size=12, color=ft.Colors.GREY_600)
        
        # Add search progress indicator
        self.search_progress = ft.ProgressRing(
            width=16,
            height=16,
            stroke_width=2,
            visible=False,
        )
        
        # Add search status indicator
        self.search_status = ft.Text(
            "",
            size=11,
            color=ft.Colors.BLUE_600,
            italic=True,
        )
        
        # Add search on visible data switch
        self.search_visible_only_switch = ft.Switch(
            label="Search visible only",
            value=self.search_visible_only,
            on_change=self._on_search_scope_change,
            tooltip="Search only currently visible data for faster results",
            scale=0.8,
        )
        
        # Create search container with theme-aware colors and store reference
        self.search_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("🔍 Real-time Search", size=16, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        self.search_progress,
                        self.search_status,
                    ], spacing=5),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    self.search_term_field,
                    self.search_column_dropdown,
                    ft.ElevatedButton("Clear", on_click=self._on_clear_search, icon=ft.Icons.CLEAR),
                    self.match_label,
                ], spacing=10),
                ft.Row([
                    self.case_sensitive_switch,
                    self.whole_word_switch,
                    self.search_visible_only_switch,
                ], spacing=20),
            ], spacing=8),
            padding=10,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
            bgcolor=ft.Colors.GREY_50,
        )
        
        # Create pagination components
        pagination_container = self._create_pagination_container()
        
        # Create dynamic status message
        self.dynamic_status = ft.Text(
            "🚀 DataScope Ready • Load a dataset to begin your analysis",
            size=14,
            color=ft.Colors.BLUE_600,
            text_align=ft.TextAlign.CENTER,
            weight=ft.FontWeight.W_500,
        )
        
        # Create main data container with pagination at the top
        data_container = ft.Column(
            [
                self.search_container,  # Use self reference
                pagination_container,  # Moved pagination to top
                self.data_table_info,
                self.pagination_info,
                ft.Container(
                    content=self.dynamic_status,
                    alignment=ft.alignment.center,
                    height=200,
                ),
            ],
            spacing=10,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        
        return ft.Container(
            content=data_container,
            expand=True,
            padding=10,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.GREY_300),
        )
    
    def _create_pagination_container(self) -> ft.Container:
        """Create pagination controls."""
        
        prev_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Previous page",
            disabled=True,
            on_click=self._on_prev_page,
        )
        
        next_btn = ft.IconButton(
            icon=ft.Icons.ARROW_FORWARD,
            tooltip="Next page",
            disabled=True,
            on_click=self._on_next_page,
        )
        
        first_btn = ft.IconButton(
            icon=ft.Icons.FIRST_PAGE,
            tooltip="First page",
            disabled=True,
            on_click=self._on_first_page,
        )
        
        last_btn = ft.IconButton(
            icon=ft.Icons.LAST_PAGE,
            tooltip="Last page",
            disabled=True,
            on_click=self._on_last_page,
        )
        
        page_size_dropdown = ft.Dropdown(
            label="Rows per page",
            width=120,
            options=[
                ft.dropdown.Option("10"),
                ft.dropdown.Option("25"),
                ft.dropdown.Option("50"),
                ft.dropdown.Option("100"),
            ],
            value="25",
            on_change=self._on_page_size_change,
        )
        
        # Store references for later updates
        self.prev_btn = prev_btn
        self.next_btn = next_btn
        self.first_btn = first_btn
        self.last_btn = last_btn
        self.page_size_dropdown = page_size_dropdown
        
        # Create the pagination container with theme-aware colors
        self.pagination_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    first_btn,
                    prev_btn,
                    ft.Container(width=20),  # Spacer
                    next_btn,
                    last_btn,
                    ft.Container(width=50),  # Spacer
                    page_size_dropdown,
                ], alignment=ft.MainAxisAlignment.CENTER),
            ]),
            padding=10,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
            bgcolor=ft.Colors.GREY_50,
        )
        
        return self.pagination_container
    
    def load_data(self, df: pd.DataFrame, highlight_term: str = None, highlight_column: str = None, disable_pagination: bool = False) -> None:
        """Load new data and refresh the display.
        
        Parameters
        ----------
        df : pd.DataFrame
            The DataFrame to display
        highlight_term : str, optional
            Term to highlight in the display
        highlight_column : str, optional 
            Column to restrict highlighting to
        disable_pagination : bool, optional
            If True, show all rows without pagination (useful for data previews)
        """
        if df is None or df.empty:
            print("[DataView] Empty DataFrame passed to load_data")
            return
        
        print(f"[DataView] Loading new data: {df.shape}, disable_pagination={disable_pagination}")
        print(f"[DataView] Previous pagination state: {getattr(self, 'disable_pagination', 'not set')}")
        
        # Store original data for search restore
        self.original_df = df.copy()
        self.current_df = df
        self.current_page = 1
        self.highlight_term = highlight_term
        self.highlight_column = highlight_column
        self.disable_pagination = disable_pagination  # Store pagination preference
        
        print(f"[DataView] New pagination state set to: {self.disable_pagination}")
        
        # Reset search state
        self.search_results = None
        self.search_term = ""
        if self.search_term_field:
            self.search_term_field.value = ""
        if self.match_label:
            self.match_label.value = "0/0"
        if self.search_status:
            self.search_status.value = ""
        if self.case_sensitive_switch:
            self.case_sensitive_switch.value = False
        if self.whole_word_switch:
            self.whole_word_switch.value = False
        
        # Update status message based on data type
        if disable_pagination:
            self.update_status_message('preview', rows=len(df))
        else:
            self.update_status_message('loaded', 
                                     filename="Dataset", 
                                     rows=len(df), 
                                     cols=len(df.columns))
            
        self._update_search_columns()
        self._refresh_display()
        
        print(f"[DataView] Data loaded successfully with real-time search ready")
    
    def _update_search_columns(self) -> None:
        """Update search column dropdown with current DataFrame columns."""
        if self.current_df is not None:
            options = [ft.dropdown.Option("All Columns")]
            options.extend([ft.dropdown.Option(col) for col in self.current_df.columns])
            self.search_column_dropdown.options = options
            self.search_column_dropdown.value = "All Columns"
    
    def _refresh_display(self) -> None:
        """Refresh the data table display."""
        if self.current_df is None:
            print("[DataView] _refresh_display called but current_df is None")
            return
        
        print(f"[DataView] _refresh_display: disable_pagination={self.disable_pagination}, df_shape={self.current_df.shape}")
        
        # Calculate pagination - skip if disabled (for data previews)
        if self.disable_pagination or len(self.current_df) <= self.rows_per_page:
            display_df = self.current_df
            self.total_pages = 1
            print(f"[DataView] Showing all {len(self.current_df)} rows (pagination disabled or data fits on one page)")
        else:
            display_df, total_rows, total_pages = get_paginated_data(
                self.current_df, self.current_page, self.rows_per_page
            )
            self.total_pages = total_pages
            print(f"[DataView] Showing page {self.current_page}/{total_pages} with {len(display_df)} rows")
        
        # Create new data table
        self._create_data_table(display_df)
        
        # Update info labels
        self._update_info_labels()
        
        # Update pagination controls
        self._update_pagination_controls()
        
        # Replace the placeholder with the actual table with optimized scrolling
        container_content = self.container.content
        if len(container_content.controls) >= 3:
            # Create a row for horizontal scrolling that contains the data table
            horizontal_scroll_row = ft.Row(
                controls=[self.data_table],
                scroll=ft.ScrollMode.ALWAYS,  # Enable horizontal scrolling
                expand=True,
                spacing=0,  # No extra spacing
            )
            
            # Wrap in vertical container for overall layout with optimized scrolling
            table_container = ft.Container(
                content=ft.Column([horizontal_scroll_row], 
                                scroll=ft.ScrollMode.AUTO,  # Vertical scroll as needed
                                expand=True, 
                                spacing=0),
                expand=True,
                border_radius=10,
                border=ft.border.all(1, ft.Colors.GREY_300),
                bgcolor=ft.Colors.TRANSPARENT,
                padding=ft.padding.all(5),  # Small padding for better appearance
            )
            container_content.controls[2] = table_container
        
        # Apply theme
        self._apply_theme()
        
        # Update the UI
        self.container.update()
        
        # Force page refresh to ensure changes are visible
        if hasattr(self.page, 'update'):
            self.page.update()
        
        print(f"[DataView] Display refreshed - page {self.current_page}/{self.total_pages}")
    
    def _create_data_table(self, df: pd.DataFrame) -> None:
        """Create a new DataTable from the DataFrame."""
        if df is None or df.empty:
            return
        
        # Determine if we're in dark mode for proper text colors
        is_dark_mode = self.page.theme_mode == ft.ThemeMode.DARK
        text_color = ft.Colors.WHITE if is_dark_mode else ft.Colors.BLACK
        header_text_color = ft.Colors.WHITE if is_dark_mode else ft.Colors.BLACK
        
        # Create columns with proper text colors and sizing
        columns = [ft.DataColumn(
            ft.Text("#", color=header_text_color, weight=ft.FontWeight.BOLD, size=self.scaled_font_sizes['header_text']),
            numeric=True
        )]  # Row number column with larger font
        
        # Add data columns - show FULL column names with proper wrapping
        for col in df.columns:
            columns.append(ft.DataColumn(
                ft.Text(
                    col,  # Show complete column name
                    color=header_text_color,
                    weight=ft.FontWeight.BOLD,
                    size=self.scaled_font_sizes['header_text'],  # Use scaled font size
                    text_align=ft.TextAlign.CENTER,
                    max_lines=2,  # Allow up to 2 lines for column names
                    overflow=ft.TextOverflow.ELLIPSIS,  # Use ellipsis for very long names
                ),
                tooltip=col  # Full column name on hover
            ))
        
        # Create rows with sequential row numbers
        rows = []
        for row_num, (idx, row) in enumerate(df.iterrows(), 1):
            cells = [ft.DataCell(ft.Text(
                str(row_num), 
                color=text_color,
                size=self.scaled_font_sizes['row_number'],  # Use scaled font for row numbers
                text_align=ft.TextAlign.CENTER
            ))]  # Sequential row number starting from 1
            
            for col_name in df.columns:
                value = row.get(col_name, "")
                cell_text = str(value)
                
                # Show full cell text with proper formatting for readability
                display_text = cell_text
                
                # Apply highlighting if parameters were provided
                if (self.highlight_term and 
                    self.highlight_term.lower() in cell_text.lower() and
                    (self.highlight_column is None or self.highlight_column == col_name)):
                    
                    cell_content = ft.Container(
                        content=ft.Text(
                            display_text, 
                            color=ft.Colors.BLACK,
                            size=self.scaled_font_sizes['cell_text'],  # Use scaled font for cell content
                            text_align=ft.TextAlign.LEFT,
                            max_lines=3,  # Allow up to 3 lines
                            overflow=ft.TextOverflow.ELLIPSIS,  # Truncate with ellipsis if too long
                        ),
                        bgcolor=ft.Colors.AMBER_700 if is_dark_mode else ft.Colors.YELLOW_300,
                        padding=ft.padding.all(3),  # Reduced padding
                        border_radius=3,
                        tooltip=cell_text if len(cell_text) > 100 else None,  # Tooltip for very long content
                    )
                    cells.append(ft.DataCell(cell_content))
                else:
                    cells.append(ft.DataCell(ft.Text(
                        display_text,
                        color=text_color,
                        size=self.scaled_font_sizes['cell_text'],  # Use scaled font for cell content
                        text_align=ft.TextAlign.LEFT,
                        max_lines=3,  # Allow up to 3 lines
                        overflow=ft.TextOverflow.ELLIPSIS,  # Truncate with ellipsis if too long
                        tooltip=cell_text if len(cell_text) > 100 else None,  # Tooltip for very long content
                    )))
            
            rows.append(ft.DataRow(cells=cells))
        
        # Create the DataTable with optimized layout for better text fitting
        if is_dark_mode:
            self.data_table = ft.DataTable(
                columns=columns,
                rows=rows,
                heading_row_color=ft.Colors.GREY_700,
                border=ft.border.all(1, ft.Colors.GREY_600),
                vertical_lines=ft.BorderSide(1, ft.Colors.GREY_600),
                horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_600),
                bgcolor=ft.Colors.GREY_900,
                column_spacing=12,  # Balanced spacing for readability
                data_row_min_height=45,  # Adequate height for multi-line text
                data_row_max_height=100,  # Reasonable max height
                divider_thickness=1,
                heading_row_height=50,  # Increased header height for wrapped column names
            )
        else:
            self.data_table = ft.DataTable(
                columns=columns,
                rows=rows,
                heading_row_color=ft.Colors.GREY_100,
                border=ft.border.all(1, ft.Colors.GREY_400),
                vertical_lines=ft.BorderSide(1, ft.Colors.GREY_300),
                horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_300),
                bgcolor=ft.Colors.WHITE,
                column_spacing=12,  # Balanced spacing for readability
                data_row_min_height=45,  # Adequate height for multi-line text
                data_row_max_height=100,  # Reasonable max height
                divider_thickness=1,
                heading_row_height=50,  # Increased header height for wrapped column names
            )
        
        print(f"[DataView] Created DataTable with {len(columns)} columns and {len(rows)} rows")
    
    def _update_info_labels(self) -> None:
        """Update the info labels with current data information."""
        if self.current_df is None:
            return
        
        total_rows = len(self.current_df)
        
        if self.total_pages > 1:
            start_row = (self.current_page - 1) * self.rows_per_page + 1
            end_row = min(self.current_page * self.rows_per_page, total_rows)
            self.data_table_info.value = f"Showing rows {start_row}-{end_row} of {total_rows} total"
            self.pagination_info.value = f"Page {self.current_page} of {self.total_pages}"
        else:
            self.data_table_info.value = f"Showing all {total_rows} rows"
            self.pagination_info.value = ""
    
    def _update_pagination_controls(self) -> None:
        """Update pagination button states."""
        self.prev_btn.disabled = self.current_page <= 1
        self.next_btn.disabled = self.current_page >= self.total_pages
        self.first_btn.disabled = self.current_page <= 1
        self.last_btn.disabled = self.current_page >= self.total_pages
    
    def _apply_theme(self) -> None:
        """Apply current theme to the data table and other components."""
        if not self.data_table:
            return
        
        # Theme is now applied during table creation, but we need to update
        # the search and pagination containers
        is_dark_mode = self.page.theme_mode == ft.ThemeMode.DARK
        
        # Define theme colors
        container_bg = ft.Colors.GREY_800 if is_dark_mode else ft.Colors.GREY_50
        container_border = ft.Colors.GREY_600 if is_dark_mode else ft.Colors.BLUE_GREY_200
        info_color = ft.Colors.GREY_300 if is_dark_mode else ft.Colors.GREY_600
        
        # Update search container theme
        if hasattr(self, 'search_container') and self.search_container:
            self.search_container.bgcolor = container_bg
            self.search_container.border = ft.border.all(1, container_border)
        
        # Update pagination container theme
        if hasattr(self, 'pagination_container') and self.pagination_container:
            self.pagination_container.bgcolor = container_bg
            self.pagination_container.border = ft.border.all(1, container_border)
        
        # Update info labels
        if self.data_table_info:
            self.data_table_info.color = info_color
        if self.pagination_info:
            self.pagination_info.color = info_color
        if self.match_label:
            self.match_label.color = info_color
        
        # Update search option switches (they automatically adapt to theme)
        if self.case_sensitive_switch:
            self.case_sensitive_switch.update()
        if self.whole_word_switch:
            self.whole_word_switch.update()
    
    # Event handlers
    def _on_prev_page(self, e: ft.ControlEvent) -> None:
        """Handle previous page navigation."""
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh_display()
    
    def _on_next_page(self, e: ft.ControlEvent) -> None:
        """Handle next page navigation."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._refresh_display()
    
    def _on_first_page(self, e: ft.ControlEvent) -> None:
        """Handle first page navigation."""
        if self.current_page > 1:
            self.current_page = 1
            self._refresh_display()
    
    def _on_last_page(self, e: ft.ControlEvent) -> None:
        """Handle last page navigation."""
        if self.current_page < self.total_pages:
            self.current_page = self.total_pages
            self._refresh_display()
    
    def _on_page_size_change(self, e: ft.ControlEvent) -> None:
        """Handle page size change."""
        try:
            self.rows_per_page = int(e.control.value)
            self.current_page = 1  # Reset to first page
            self._refresh_display()
        except ValueError:
            pass

    # Advanced Cache Management for Ultra-Fast Search
    def _generate_cache_key(self, term: str, column: str, case_sensitive: bool, whole_word: bool) -> str:
        """Generate a unique cache key for search parameters."""
        key_components = [
            term.strip(),
            column or "ALL",
            str(case_sensitive),
            str(whole_word),
            str(id(self.original_df))  # Include DataFrame identity to invalidate on data change
        ]
        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_search(self, cache_key: str) -> Optional[Tuple[list, int]]:
        """Retrieve cached search results if valid."""
        if cache_key in self.search_cache:
            results, total_count, timestamp = self.search_cache[cache_key]
            # Check if cache is still valid
            if time.time() - timestamp < self.cache_max_age:
                self.search_performance_stats["cached_searches"] += 1
                print(f"[DataView] Using cached search results: {total_count} matches")
                return results, total_count
            else:
                # Remove expired cache entry
                del self.search_cache[cache_key]
        return None
    
    def _cache_search_results(self, cache_key: str, results: list, total_count: int):
        """Cache search results with automatic cleanup."""
        # Clean old cache entries if we're at max size
        if len(self.search_cache) >= self.cache_max_size:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self.search_cache.keys())[:len(self.search_cache) - self.cache_max_size + 1]
            for old_key in oldest_keys:
                del self.search_cache[old_key]
        
        # Cache the new results
        self.search_cache[cache_key] = (results, total_count, time.time())
        print(f"[DataView] Cached search results for future use")
    
    def _clear_search_cache(self):
        """Clear all search cache entries."""
        self.search_cache.clear()
        print(f"[DataView] Search cache cleared")
    
    def _log_search_performance(self):
        """Log search performance statistics."""
        stats = self.search_performance_stats
        if stats["total_searches"] > 0:
            cache_rate = (stats["cached_searches"] / stats["total_searches"]) * 100
            fast_rate = (stats["fast_searches"] / stats["total_searches"]) * 100
            print(f"[DataView] Search Performance - Cache Hit Rate: {cache_rate:.1f}%, Fast Searches: {fast_rate:.1f}%")
    
    def _on_search_change(self, e: ft.ControlEvent) -> None:
        """Handle search term change with ultra-fast debounced search."""
        self.search_term = e.control.value
        
        # Clear search if term is empty
        if not self.search_term.strip():
            self._clear_search_internal()
            return
        
        # Cancel any existing search timer
        if self.search_timer:
            self.search_timer.cancel()
            
        # Check minimum search length
        if len(self.search_term.strip()) < self.min_search_length:
            if self.search_status:
                self.search_status.value = f"Type at least {self.min_search_length} character{'s' if self.min_search_length > 1 else ''} to search"
                self.search_status.color = ft.Colors.GREY_600
                self.search_status.update()
            return
        
        # Show loading indicator
        self._show_search_loading()
        
        # Create debounced search timer
        self.search_timer = threading.Timer(
            self.search_debounce_delay, 
            self._perform_debounced_search
        )
        self.search_timer.start()
    
    def _show_search_loading(self):
        """Show search loading state."""
        if self.search_progress:
            self.search_progress.visible = True
            self.search_progress.update()
        
        if self.search_status:
            self.search_status.value = "Searching..."
            self.search_status.color = ft.Colors.ORANGE_600
            self.search_status.update()
    
    def _hide_search_loading(self):
        """Hide search loading state."""
        if self.search_progress:
            self.search_progress.visible = False
            self.search_progress.update()
    
    def _perform_debounced_search(self):
        """Perform the debounced search operation."""
        # Record search start time for performance monitoring
        self.last_search_time = time.time()
        
        # Perform the actual search
        self._perform_real_time_search()
    
    def _on_search_scope_change(self, e: ft.ControlEvent) -> None:
        """Handle search scope change (visible only vs all data)."""
        self.search_visible_only = e.control.value
        
        # If we have a search term, trigger immediate search
        if self.search_term.strip():
            self._show_search_loading()
            self._perform_real_time_search()
    
    def _on_column_change(self, e: ft.ControlEvent) -> None:
        """Handle search column change - trigger debounced search if term exists."""
        self.search_column = e.control.value
        
        # If we have a search term, trigger debounced search
        if self.search_term.strip() and len(self.search_term.strip()) >= self.min_search_length:
            # Cancel any existing search timer
            if self.search_timer:
                self.search_timer.cancel()
            
            self._show_search_loading()
            
            # Create new debounced search timer
            self.search_timer = threading.Timer(
                self.search_debounce_delay * 0.5,  # Shorter delay for option changes
                self._perform_debounced_search
            )
            self.search_timer.start()
    
    def _on_search_option_change(self, e: ft.ControlEvent) -> None:
        """Handle case sensitive or whole word option change - trigger debounced search if term exists."""
        # If we have a search term, trigger debounced search
        if self.search_term.strip() and len(self.search_term.strip()) >= self.min_search_length:
            # Cancel any existing search timer
            if self.search_timer:
                self.search_timer.cancel()
            
            self._show_search_loading()
            
            # Create new debounced search timer
            self.search_timer = threading.Timer(
                self.search_debounce_delay * 0.5,  # Shorter delay for option changes
                self._perform_debounced_search
            )
            self.search_timer.start()
    
    def _perform_real_time_search(self) -> None:
        """Perform ultra-fast search with caching and performance optimizations."""
        if self.original_df is None or not self.search_term.strip():
            self._hide_search_loading()
            return
        
        try:
            self.is_searching = True
            search_start_time = time.time()
            self.search_performance_stats["total_searches"] += 1
            
            # Get search parameters
            column = None if self.search_column == "All Columns" else self.search_column
            case_sensitive = self.case_sensitive_switch.value if self.case_sensitive_switch else False
            whole_word = self.whole_word_switch.value if self.whole_word_switch else False
            
            # Generate cache key
            cache_key = self._generate_cache_key(self.search_term, column, case_sensitive, whole_word)
            
            # Try to get cached results first
            cached_result = self._get_cached_search(cache_key)
            if cached_result:
                results, total_count = cached_result
                search_duration = time.time() - search_start_time
                
                # Use cached results
                if results:
                    search_result_df = self.original_df.iloc[results[:self.max_search_results]]
                    self.current_df = search_result_df
                    self.current_page = 1
                    self.search_results = results
                    
                    # Update display
                    self._refresh_display()
                    
                    # Update search status
                    if self.search_status:
                        showing_count = min(len(results), self.max_search_results)
                        self.search_status.value = f"⚡ Found {total_count} matches (showing {showing_count}) - CACHED"
                        self.search_status.color = ft.Colors.GREEN_600
                        self.search_status.update()
                    
                    # Update match label with cached result count
                    if self.match_label:
                        showing_count = min(len(results), self.max_search_results)
                        if total_count > self.max_search_results:
                            self.match_label.value = f"{showing_count}/{total_count}+ (cached)"
                        else:
                            self.match_label.value = f"{showing_count}/{total_count} (cached)"
                        self.match_label.color = ft.Colors.BLUE_600
                        self.match_label.update()
                    
                    # Set up highlighting for cached search terms
                    self.highlight_term = self.search_term
                    self.highlight_column = column
                        
                    print(f"[DataView] Cached search completed in {search_duration:.3f}s")
                else:
                    self._clear_search_internal()
                    if self.search_status:
                        self.search_status.value = "No matches found - CACHED"
                        self.search_status.color = ft.Colors.RED_600
                        self.search_status.update()
                    
                    # Update match label for cached no results
                    if self.match_label:
                        self.match_label.value = "0/0 (cached)"
                        self.match_label.color = ft.Colors.RED_600
                        self.match_label.update()
                
                self._hide_search_loading()
                self.is_searching = False
                return
            
            # Determine search dataset
            search_df = self.original_df
            if self.search_visible_only and self.current_df is not None and not self.search_results:
                # Search only in currently visible data if option is enabled
                start_idx = (self.current_page - 1) * self.rows_per_page
                end_idx = start_idx + self.rows_per_page
                search_df = self.original_df.iloc[start_idx:end_idx]
                print(f"[DataView] Searching in visible data only ({len(search_df)} rows)")
            
            # Import search function (avoiding circular import)
            from data_handler import search_dataframe_optimized
            
            # Perform ultra-fast optimized search
            search_result = search_dataframe_optimized(
                search_df, 
                self.search_term, 
                column, 
                case_sensitive, 
                whole_word,
                max_results=self.max_search_results
            )
            
            # Handle tuple return (matches, total_count)
            if isinstance(search_result, tuple):
                results, total_count = search_result
            else:
                # Fallback for backward compatibility
                results = search_result
                total_count = len(results)
            
            search_duration = time.time() - search_start_time
            
            # Cache the results for future use
            self._cache_search_results(cache_key, results, total_count)
            
            # Track fast search performance
            if search_duration < 0.1:
                self.search_performance_stats["fast_searches"] += 1
            
            if results:
                # Handle result limiting
                limited_results = results[:self.max_search_results] if len(results) > self.max_search_results else results
                
                # Adjust indices if searching visible data only
                if self.search_visible_only and not self.search_results:
                    start_idx = (self.current_page - 1) * self.rows_per_page
                    limited_results = [idx + start_idx for idx in limited_results]
                
                # Show search results
                search_result_df = self.original_df.iloc[limited_results]
                self.current_df = search_result_df
                self.current_page = 1
                self.search_results = limited_results
                
                # Update display
                self._refresh_display()
                
                # Update search status with performance info
                if self.search_status:
                    showing_count = len(limited_results)
                    speed_indicator = "⚡" if search_duration < 0.05 else "🔍"
                    self.search_status.value = f"{speed_indicator} Found {total_count} matches (showing {showing_count}) in {search_duration:.3f}s"
                    self.search_status.color = ft.Colors.GREEN_600
                    self.search_status.update()
                
                # Update match label with result count
                if self.match_label:
                    showing_count = len(limited_results)
                    if total_count > self.max_search_results:
                        self.match_label.value = f"{showing_count}/{total_count}+"
                    else:
                        self.match_label.value = f"{showing_count}/{total_count}"
                    self.match_label.color = ft.Colors.GREEN_600
                    self.match_label.update()
                
                # Set up highlighting for search terms
                self.highlight_term = self.search_term
                self.highlight_column = column
                    
                print(f"[DataView] Search completed: {total_count} matches in {search_duration:.3f}s")
            else:
                # No results found
                self._clear_search_internal()
                if self.search_status:
                    self.search_status.value = f"No matches found in {search_duration:.3f}s"
                    self.search_status.color = ft.Colors.RED_600
                    self.search_status.update()
                
                # Update match label for no results
                if self.match_label:
                    self.match_label.value = "0/0"
                    self.match_label.color = ft.Colors.RED_600
                    self.match_label.update()
                    
        except Exception as e:
            print(f"[DataView] Search error: {e}")
            if self.search_status:
                self.search_status.value = f"Search error: {str(e)}"
                self.search_status.color = ft.Colors.RED_600
                self.search_status.update()
        finally:
            self._hide_search_loading()
            self.is_searching = False
            
            # Log performance statistics periodically
            if self.search_performance_stats["total_searches"] % 10 == 0:
                self._log_search_performance()
    
    def _on_search(self, e: ft.ControlEvent) -> None:
        """Handle manual search button click (kept for compatibility)."""
        if self.search_term_field and self.search_term_field.value:
            self.search_term = self.search_term_field.value
            self._perform_real_time_search()
    
    def _clear_search_internal(self) -> None:
        """Internal method to clear search without UI updates."""
        # Cancel any pending search timer
        if self.search_timer:
            self.search_timer.cancel()
            self.search_timer = None
        
        # Hide loading indicator
        self._hide_search_loading()
        
        if self.original_df is not None:
            self.current_df = self.original_df.copy()
            self.current_page = 1
            self.search_results = None
            self.highlight_term = None
            self.highlight_column = None
            
            # Update UI feedback
            if self.match_label:
                self.match_label.value = "0/0"
                self.match_label.color = ft.Colors.GREY_600
                self.match_label.update()
            
            if self.search_status:
                self.search_status.value = ""
                self.search_status.update()
            
            # Reset status to loaded state
            if self.original_df is not None:
                self.update_status_message('loaded', 
                                         filename="Dataset", 
                                         rows=len(self.original_df), 
                                         cols=len(self.original_df.columns))
            
            self._refresh_display()
    
    def _on_clear_search(self, e: ft.ControlEvent) -> None:
        """Handle search clear button click."""
        # Cancel any pending search timer
        if self.search_timer:
            self.search_timer.cancel()
            self.search_timer = None
        
        # Clear search term
        self.search_term = ""
        if self.search_term_field:
            self.search_term_field.value = ""
            self.search_term_field.update()
        
        # Reset search options
        if self.case_sensitive_switch:
            self.case_sensitive_switch.value = False
            self.case_sensitive_switch.update()
        if self.whole_word_switch:
            self.whole_word_switch.value = False
            self.whole_word_switch.update()
        
        # Clear search results
        self._clear_search_internal()
        print("[DataView] Search cleared with options reset")
    
    def update_status_message(self, status_type: str, **kwargs) -> None:
        """Update the dynamic status message based on application state.
        
        Parameters
        ----------
        status_type : str
            Type of status: 'ready', 'loading', 'loaded', 'analysis', 'error', 'search', 'preview'
        **kwargs : dict
            Additional context data (rows, columns, filename, analysis_type, etc.)
        """
        if not self.dynamic_status:
            return
            
        # Define status messages with emojis and context
        status_messages = {
            'ready': "🚀 DataScope Ready • Load a dataset to begin your analysis",
            'loading': f"⏳ Loading data • Please wait...",
            'loaded': "📊 Dataset: {filename} • {rows:,} rows × {cols} columns • Ready for analysis",
            'analysis': "🔍 Analysis: {analysis_type} • {context}",
            'preview': "👁️ Data Preview • Showing {rows} rows with sequential indexing",
            'search': "🔍 Search Results • {matches} matches found for '{term}'",
            'error': "❌ Error • {message}",
            'pagination': "📄 Viewing page {page} of {total_pages} • {start_row}-{end_row} of {total_rows} rows",
            'export': "💾 Export Complete • Data saved successfully",
            'processing': "⚙️ Processing • {operation} in progress..."
        }
        
        # Get the base message
        message = status_messages.get(status_type, "📊 DataScope • Ready")
        
        # Format with provided context
        try:
            formatted_message = message.format(**kwargs)
        except (KeyError, ValueError):
            # Fallback if formatting fails
            formatted_message = message
        
        # Update colors based on status type
        status_colors = {
            'ready': ft.Colors.BLUE_600,
            'loading': ft.Colors.ORANGE_600,
            'loaded': ft.Colors.GREEN_600,
            'analysis': ft.Colors.PURPLE_600,
            'preview': ft.Colors.TEAL_600,
            'search': ft.Colors.INDIGO_600,
            'error': ft.Colors.RED_600,
            'pagination': ft.Colors.BLUE_GREY_600,
            'export': ft.Colors.GREEN_700,
            'processing': ft.Colors.AMBER_600
        }
        
        # Update the status message
        self.dynamic_status.value = formatted_message
        self.dynamic_status.color = status_colors.get(status_type, ft.Colors.BLUE_600)
        
        # Add slight animation effect for certain status types
        if status_type in ['loading', 'processing']:
            self.dynamic_status.weight = ft.FontWeight.BOLD
        else:
            self.dynamic_status.weight = ft.FontWeight.W_500
            
        # Update the UI only if the control is properly added to the page
        try:
            if hasattr(self.dynamic_status, 'update') and hasattr(self.dynamic_status, 'page') and self.dynamic_status.page:
                self.dynamic_status.update()
        except Exception as e:
            # Control might not be added to page yet, which is fine
            print(f"[DataView] Status update deferred (control not on page yet): {e}")
        
        print(f"[DataView] Status updated: {status_type} -> {formatted_message}")
    
    def _calculate_scaled_fonts(self, percentage: int) -> dict:
        """Calculate scaled font sizes based on magnification percentage."""
        scale_factor = percentage / 100.0
        base_sizes = {
            'info_text': 14,
            'pagination_text': 14,
            'search_text': 16,
            'status_text': 14,
            'match_label': 12,
            'search_status': 11,
            'header_text': 12,
            'cell_text': 12,
            'row_number': 11
        }
        
        return {key: max(8, int(size * scale_factor)) for key, size in base_sizes.items()}
    
    def apply_magnification(self, percentage: int) -> bool:
        """Apply magnification scaling to all text elements in the data view."""
        try:
            # Update current magnification and calculate new font sizes
            self.current_magnification = percentage
            self.scaled_font_sizes = self._calculate_scaled_fonts(percentage)
            
            # Apply scaling to info texts
            if hasattr(self, 'data_table_info') and self.data_table_info:
                self.data_table_info.style = ft.TextStyle(
                    size=self.scaled_font_sizes['info_text'], 
                    color=self.data_table_info.style.color if self.data_table_info.style else ft.Colors.GREY_600
                )
            
            if hasattr(self, 'pagination_info') and self.pagination_info:
                self.pagination_info.style = ft.TextStyle(
                    size=self.scaled_font_sizes['pagination_text'],
                    color=self.pagination_info.style.color if self.pagination_info.style else ft.Colors.GREY_600
                )
            
            # Apply scaling to search components
            if hasattr(self, 'match_label') and self.match_label:
                self.match_label.size = self.scaled_font_sizes['match_label']
            
            if hasattr(self, 'search_status') and self.search_status:
                self.search_status.size = self.scaled_font_sizes['search_status']
            
            if hasattr(self, 'dynamic_status') and self.dynamic_status:
                self.dynamic_status.size = self.scaled_font_sizes['status_text']
            
            # Apply scaling to search title if it exists
            try:
                if hasattr(self, 'search_controls') and self.search_controls:
                    # Find the search title text in the search controls
                    for control in self.search_controls.content.controls:
                        if hasattr(control, 'controls'):
                            for subcontrol in control.controls:
                                if isinstance(subcontrol, ft.Text) and "Search" in str(subcontrol.value):
                                    subcontrol.size = self.scaled_font_sizes['search_text']
            except Exception:
                pass  # Search controls might not be structured as expected
                
            # Refresh the data table with new font sizes - this will recreate all cells
            if self.current_df is not None:
                self._refresh_display()
            
            # Update the page to reflect changes
            if self.page:
                self.page.update()
            
            return True
            
        except Exception as e:
            print(f"[DataView] Error applying magnification: {str(e)}")
            return False
    
    def get_widget(self) -> ft.Container:
        """Get the main widget container."""
        return self.container
    
    def update_theme(self) -> None:
        """Update theme for all components and recreate the data table."""
        if self.current_df is not None:
            # Recreate the data table with the new theme
            self._refresh_display()
        else:
            # Just update the theme for existing components
            self._apply_theme()
        
        if self.container:
            self.container.update()
