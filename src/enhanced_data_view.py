"""
Enhanced Data View Module

Provides alternative view modes for data display including:
- Standard DataTable View (existing functionality)
- Plain Text View 
- Syntax Highlighted View
- Unstructured Data View

Maintains performance standards while providing flexible display options.
"""

import flet as ft
import pandas as pd
import json
import csv
from typing import Optional, Dict, Any, Literal
from io import StringIO
import re
from data_view import DataViewWidget


class EnhancedDataView:
    """Enhanced data view widget with multiple display modes."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.current_df: Optional[pd.DataFrame] = None
        self.current_view_mode: Literal["table", "plain_text", "syntax_highlighted", "unstructured"] = "table"
        
        # Initialize the original DataViewWidget for table mode
        self.table_widget = DataViewWidget(page)
        
        # View mode containers
        self.plain_text_view: Optional[ft.Container] = None
        self.syntax_highlighted_view: Optional[ft.Container] = None
        self.unstructured_view: Optional[ft.Container] = None
        
        # Main container that will switch between different views
        self.main_container = self._create_main_container()
        
        # Apply initial theme after all components are created
        self._apply_initial_theme()
        
        print("[EnhancedDataView] Initialized with multiple view modes")
    
    def _apply_initial_theme(self):
        """Apply initial theme based on current page theme mode."""
        try:
            # Ensure all components are created before applying theme
            if hasattr(self, 'header_container') and hasattr(self, 'view_mode_selector'):
                self.update_theme()
                print("[EnhancedDataView] Initial theme applied successfully")
            else:
                # If components aren't ready, set a delayed theme update
                print("[EnhancedDataView] Deferring initial theme application")
        except Exception as e:
            print(f"[EnhancedDataView] Initial theme application failed: {e}")
            pass
    
    def ensure_theme_consistency(self):
        """Ensure theme consistency after component is added to page."""
        try:
            self.update_theme()
            print("[EnhancedDataView] Theme consistency ensured")
        except Exception as e:
            print(f"[EnhancedDataView] Theme consistency check failed: {e}")
            pass
    
    def _create_main_container(self) -> ft.Container:
        """Create the main container that holds all view modes."""
        
        # Determine current theme mode for initial styling
        is_dark_mode = self.page.theme_mode == ft.ThemeMode.DARK
        
        # Define initial colors based on theme
        if is_dark_mode:
            header_bg = ft.Colors.GREY_800
            header_border = ft.Colors.GREY_600
            title_color = ft.Colors.WHITE
        else:
            header_bg = ft.Colors.GREY_50
            header_border = ft.Colors.BLUE_GREY_200
            title_color = ft.Colors.BLACK
        
        # View mode selector
        self.view_mode_selector = ft.SegmentedButton(
            selected={"table"},
            allow_empty_selection=False,
            allow_multiple_selection=False,
            segments=[
                ft.Segment(
                    value="table",
                    label=ft.Text("📊 Table View", color=title_color),
                    tooltip="Standard structured data table"
                ),
                ft.Segment(
                    value="plain_text",
                    label=ft.Text("📄 Plain Text", color=title_color),
                    tooltip="Raw text representation"
                ),
                ft.Segment(
                    value="syntax_highlighted",
                    label=ft.Text("🎨 Syntax Highlighted", color=title_color),
                    tooltip="Formatted text with syntax highlighting"
                ),
                ft.Segment(
                    value="unstructured",
                    label=ft.Text("🔍 Unstructured", color=title_color),
                    tooltip="Raw unstructured data view"
                ),
            ],
            on_change=self._on_view_mode_change,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.GREY_800 if is_dark_mode else ft.Colors.WHITE,
                color=title_color,
            ),
        )
        
        # Create view containers
        self._create_text_views()
        
        # Main content container that will switch between views
        self.content_container = ft.Container(
            content=self.table_widget.container,
            expand=True,
        )
        
        # Create header container with initial theme-aware styling
        self.header_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📊 Enhanced Data View", 
                           style=ft.TextThemeStyle.TITLE_MEDIUM, 
                           weight=ft.FontWeight.BOLD,
                           color=title_color),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(
                    content=self.view_mode_selector,
                    padding=ft.padding.symmetric(vertical=10),
                ),
            ]),
            padding=10,
            border_radius=10,
            border=ft.border.all(1, header_border),
            bgcolor=header_bg,
            margin=ft.margin.only(bottom=10),
        )
        
        return ft.Container(
            content=ft.Column([
                self.header_container,
                self.content_container,
            ]),
            expand=True,
        )
    
    def _create_text_views(self):
        """Create the text-based view containers."""
        
        # Determine current theme for initial styling
        is_dark_mode = self.page.theme_mode == ft.ThemeMode.DARK
        text_bg = ft.Colors.GREY_900 if is_dark_mode else ft.Colors.WHITE
        text_color = ft.Colors.WHITE if is_dark_mode else ft.Colors.BLACK
        border_color = ft.Colors.GREY_600 if is_dark_mode else ft.Colors.GREY_300
        title_color = ft.Colors.WHITE if is_dark_mode else ft.Colors.BLACK
        
        # Plain Text View
        self.plain_text_field = ft.TextField(
            multiline=True,
            read_only=True,
            min_lines=20,
            max_lines=20,
            expand=True,
            border_radius=10,
            content_padding=15,
            bgcolor=text_bg,
            color=text_color,
            border_color=border_color,
            focused_border_color=border_color,
            text_style=ft.TextStyle(
                font_family="Consolas, 'Courier New', monospace",
                size=12,
                color=text_color,
            ),
        )
        
        self.plain_text_view = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📄 Plain Text View", 
                           style=ft.TextThemeStyle.TITLE_SMALL, 
                           weight=ft.FontWeight.BOLD,
                           color=title_color),
                    self._create_text_controls(),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(
                    content=self.plain_text_field,
                    expand=True,
                ),
            ]),
            expand=True,
            padding=10,
            bgcolor=text_bg if is_dark_mode else None,
            border=ft.border.all(1, border_color) if is_dark_mode else None,
            border_radius=10 if is_dark_mode else None,
        )
        
        # Syntax Highlighted View
        self.syntax_highlighted_field = ft.TextField(
            multiline=True,
            read_only=True,
            min_lines=20,
            max_lines=20,
            expand=True,
            border_radius=10,
            content_padding=15,
            bgcolor=text_bg,
            color=text_color,
            border_color=border_color,
            focused_border_color=border_color,
            text_style=ft.TextStyle(
                font_family="Consolas, 'Courier New', monospace",
                size=12,
                color=text_color,
            ),
        )
        
        self.syntax_highlighted_view = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("🎨 Syntax Highlighted View", 
                           style=ft.TextThemeStyle.TITLE_SMALL, 
                           weight=ft.FontWeight.BOLD,
                           color=title_color),
                    self._create_syntax_controls(),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(
                    content=self.syntax_highlighted_field,
                    expand=True,
                ),
            ]),
            expand=True,
            padding=10,
            bgcolor=text_bg if is_dark_mode else None,
            border=ft.border.all(1, border_color) if is_dark_mode else None,
            border_radius=10 if is_dark_mode else None,
        )
        
        # Unstructured View
        self.unstructured_field = ft.TextField(
            multiline=True,
            read_only=True,
            min_lines=20,
            max_lines=20,
            expand=True,
            border_radius=10,
            content_padding=15,
            bgcolor=text_bg,
            color=text_color,
            border_color=border_color,
            focused_border_color=border_color,
            text_style=ft.TextStyle(
                font_family="Consolas, 'Courier New', monospace",
                size=12,
                color=text_color,
            ),
        )
        
        self.unstructured_view = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("🔍 Unstructured Data View", 
                           style=ft.TextThemeStyle.TITLE_SMALL, 
                           weight=ft.FontWeight.BOLD,
                           color=title_color),
                    self._create_unstructured_controls(),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(
                    content=self.unstructured_field,
                    expand=True,
                ),
            ]),
            expand=True,
            padding=10,
            bgcolor=text_bg if is_dark_mode else None,
            border=ft.border.all(1, border_color) if is_dark_mode else None,
            border_radius=10 if is_dark_mode else None,
        )
    
    def _create_text_controls(self) -> ft.Row:
        """Create controls for plain text view."""
        return ft.Row([
            ft.IconButton(
                icon=ft.Icons.COPY,
                tooltip="Copy to clipboard",
                on_click=self._copy_plain_text,
            ),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                tooltip="Refresh view",
                on_click=self._refresh_plain_text,
            ),
        ], spacing=5)
    
    def _create_syntax_controls(self) -> ft.Row:
        """Create controls for syntax highlighted view."""
        self.syntax_format_dropdown = ft.Dropdown(
            label="Format",
            width=120,
            value="json",
            options=[
                ft.dropdown.Option("json", "JSON"),
                ft.dropdown.Option("csv", "CSV"),
                ft.dropdown.Option("xml", "XML"),
                ft.dropdown.Option("yaml", "YAML"),
            ],
            on_change=self._on_syntax_format_change,
        )
        
        return ft.Row([
            self.syntax_format_dropdown,
            ft.IconButton(
                icon=ft.Icons.COPY,
                tooltip="Copy to clipboard",
                on_click=self._copy_syntax_text,
            ),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                tooltip="Refresh view",
                on_click=self._refresh_syntax_text,
            ),
        ], spacing=5)
    
    def _create_unstructured_controls(self) -> ft.Row:
        """Create controls for unstructured view."""
        self.unstructured_format_dropdown = ft.Dropdown(
            label="Format",
            width=120,
            value="raw",
            options=[
                ft.dropdown.Option("raw", "Raw Data"),
                ft.dropdown.Option("delimited", "Delimited"),
                ft.dropdown.Option("key_value", "Key-Value Pairs"),
            ],
            on_change=self._on_unstructured_format_change,
        )
        
        return ft.Row([
            self.unstructured_format_dropdown,
            ft.IconButton(
                icon=ft.Icons.COPY,
                tooltip="Copy to clipboard",
                on_click=self._copy_unstructured_text,
            ),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                tooltip="Refresh view",
                on_click=self._refresh_unstructured_text,
            ),
        ], spacing=5)
    
    def _on_view_mode_change(self, e: ft.ControlEvent):
        """Handle view mode changes."""
        selected_modes = e.control.selected
        if selected_modes:
            new_mode = list(selected_modes)[0]
            self._switch_view_mode(new_mode)
    
    def _switch_view_mode(self, mode: str):
        """Switch to the specified view mode."""
        print(f"[EnhancedDataView] Switching to {mode} view")
        
        self.current_view_mode = mode
        
        # Update the content container based on mode
        if mode == "table":
            self.content_container.content = self.table_widget.container
        elif mode == "plain_text":
            self.content_container.content = self.plain_text_view
            self._update_plain_text_view()
        elif mode == "syntax_highlighted":
            self.content_container.content = self.syntax_highlighted_view
            self._update_syntax_highlighted_view()
        elif mode == "unstructured":
            self.content_container.content = self.unstructured_view
            self._update_unstructured_view()
        
        # Update the page
        self.page.update()
    
    def load_data(self, df: pd.DataFrame, **kwargs):
        """Load data into all views."""
        self.current_df = df
        
        # Always update the table view
        self.table_widget.load_data(df, **kwargs)
        
        # Update the current active view if it's not table
        if self.current_view_mode == "plain_text":
            self._update_plain_text_view()
        elif self.current_view_mode == "syntax_highlighted":
            self._update_syntax_highlighted_view()
        elif self.current_view_mode == "unstructured":
            self._update_unstructured_view()
    
    def _update_plain_text_view(self):
        """Update the plain text view with current data."""
        if self.current_df is None:
            self.plain_text_field.value = "No data loaded"
            return
        
        try:
            # Convert DataFrame to plain text representation
            buffer = StringIO()
            self.current_df.to_string(buf=buffer, index=True, max_rows=1000)
            text_content = buffer.getvalue()
            
            # Limit content size for performance
            if len(text_content) > 50000:
                text_content = text_content[:50000] + "\n\n... (Content truncated for performance)"
            
            self.plain_text_field.value = text_content
            
        except Exception as e:
            self.plain_text_field.value = f"Error generating plain text view: {str(e)}"
        
        if hasattr(self, 'page'):
            self.page.update()
    
    def _update_syntax_highlighted_view(self):
        """Update the syntax highlighted view with current data."""
        if self.current_df is None:
            self.syntax_highlighted_field.value = "No data loaded"
            return
        
        try:
            format_type = getattr(self.syntax_format_dropdown, 'value', 'json')
            
            if format_type == "json":
                # Convert to JSON with proper formatting
                json_data = self.current_df.head(100).to_dict('records')
                formatted_content = json.dumps(json_data, indent=2, default=str)
                
            elif format_type == "csv":
                # Convert to CSV format
                buffer = StringIO()
                self.current_df.head(100).to_csv(buffer, index=False)
                formatted_content = buffer.getvalue()
                
            elif format_type == "xml":
                # Convert to XML-like format
                formatted_content = self._dataframe_to_xml()
                
            elif format_type == "yaml":
                # Convert to YAML-like format
                formatted_content = self._dataframe_to_yaml()
            
            else:
                formatted_content = str(self.current_df.head(100))
            
            # Limit content size for performance
            if len(formatted_content) > 50000:
                formatted_content = formatted_content[:50000] + "\n\n... (Content truncated for performance)"
            
            self.syntax_highlighted_field.value = formatted_content
            
        except Exception as e:
            self.syntax_highlighted_field.value = f"Error generating syntax highlighted view: {str(e)}"
        
        if hasattr(self, 'page'):
            self.page.update()
    
    def _update_unstructured_view(self):
        """Update the unstructured view with current data."""
        if self.current_df is None:
            self.unstructured_field.value = "No data loaded"
            return
        
        try:
            format_type = getattr(self.unstructured_format_dropdown, 'value', 'raw')
            
            if format_type == "raw":
                # Show raw data without structure
                formatted_content = self._dataframe_to_raw()
                
            elif format_type == "delimited":
                # Show as delimited text with custom separators
                formatted_content = self._dataframe_to_delimited()
                
            elif format_type == "key_value":
                # Show as key-value pairs
                formatted_content = self._dataframe_to_key_value()
            
            else:
                formatted_content = str(self.current_df.head(100))
            
            # Limit content size for performance
            if len(formatted_content) > 50000:
                formatted_content = formatted_content[:50000] + "\n\n... (Content truncated for performance)"
            
            self.unstructured_field.value = formatted_content
            
        except Exception as e:
            self.unstructured_field.value = f"Error generating unstructured view: {str(e)}"
        
        if hasattr(self, 'page'):
            self.page.update()
    
    def _dataframe_to_xml(self) -> str:
        """Convert DataFrame to XML-like format."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<dataset>']
        
        for idx, row in self.current_df.head(50).iterrows():
            lines.append(f'  <record id="{idx}">')
            for col, value in row.items():
                clean_col = re.sub(r'[^a-zA-Z0-9_]', '_', str(col))
                lines.append(f'    <{clean_col}>{str(value)}</{clean_col}>')
            lines.append('  </record>')
        
        lines.append('</dataset>')
        return '\n'.join(lines)
    
    def _dataframe_to_yaml(self) -> str:
        """Convert DataFrame to YAML-like format."""
        lines = ['dataset:']
        
        for idx, row in self.current_df.head(50).iterrows():
            lines.append(f'  record_{idx}:')
            for col, value in row.items():
                lines.append(f'    {col}: "{str(value)}"')
        
        return '\n'.join(lines)
    
    def _dataframe_to_raw(self) -> str:
        """Convert DataFrame to raw unstructured format."""
        lines = []
        
        for idx, row in self.current_df.head(100).iterrows():
            row_data = []
            for col, value in row.items():
                row_data.append(f"{col}={value}")
            lines.append(" | ".join(row_data))
        
        return '\n'.join(lines)
    
    def _dataframe_to_delimited(self) -> str:
        """Convert DataFrame to custom delimited format."""
        lines = []
        delimiter = " :: "
        
        # Header
        lines.append(delimiter.join(self.current_df.columns))
        lines.append("=" * 80)
        
        # Data rows
        for idx, row in self.current_df.head(100).iterrows():
            lines.append(delimiter.join(str(val) for val in row.values))
        
        return '\n'.join(lines)
    
    def _dataframe_to_key_value(self) -> str:
        """Convert DataFrame to key-value pairs format."""
        lines = []
        
        for idx, row in self.current_df.head(50).iterrows():
            lines.append(f"RECORD {idx + 1}:")
            lines.append("-" * 40)
            for col, value in row.items():
                lines.append(f"{col}: {value}")
            lines.append("")  # Empty line between records
        
        return '\n'.join(lines)
    
    # Event handlers for controls
    def _copy_plain_text(self, e):
        """Copy plain text to clipboard."""
        if self.plain_text_field.value:
            self.page.set_clipboard(self.plain_text_field.value)
            self._show_copy_notification()
    
    def _copy_syntax_text(self, e):
        """Copy syntax highlighted text to clipboard."""
        if self.syntax_highlighted_field.value:
            self.page.set_clipboard(self.syntax_highlighted_field.value)
            self._show_copy_notification()
    
    def _copy_unstructured_text(self, e):
        """Copy unstructured text to clipboard."""
        if self.unstructured_field.value:
            self.page.set_clipboard(self.unstructured_field.value)
            self._show_copy_notification()
    
    def _show_copy_notification(self):
        """Show a brief notification that content was copied."""
        # You could implement a snackbar or temporary message here
        print("[EnhancedDataView] Content copied to clipboard")
    
    def _refresh_plain_text(self, e):
        """Refresh plain text view."""
        self._update_plain_text_view()
    
    def _refresh_syntax_text(self, e):
        """Refresh syntax highlighted view."""
        self._update_syntax_highlighted_view()
    
    def _refresh_unstructured_text(self, e):
        """Refresh unstructured view."""
        self._update_unstructured_view()
    
    def _on_syntax_format_change(self, e):
        """Handle syntax format changes."""
        self._update_syntax_highlighted_view()
    
    def _on_unstructured_format_change(self, e):
        """Handle unstructured format changes."""
        self._update_unstructured_view()
    
    def get_widget(self) -> ft.Container:
        """Get the main widget container."""
        return self.main_container
    
    def update_status_message(self, *args, **kwargs):
        """Delegate status updates to the table widget."""
        self.table_widget.update_status_message(*args, **kwargs)
    
    def update_theme(self):
        """Update theme for all views."""
        self.table_widget.update_theme()
        
        # Update theme for text views based on current theme mode
        is_dark_mode = self.page.theme_mode == ft.ThemeMode.DARK
        
        # Define color schemes for both themes
        if is_dark_mode:
            # Dark mode colors
            text_bg = ft.Colors.GREY_900
            text_color = ft.Colors.WHITE
            border_color = ft.Colors.GREY_600
            header_bg = ft.Colors.GREY_800
            header_border = ft.Colors.GREY_600
            segment_bg = ft.Colors.GREY_700
        else:
            # Light mode colors
            text_bg = ft.Colors.WHITE
            text_color = ft.Colors.BLACK
            border_color = ft.Colors.GREY_300
            header_bg = ft.Colors.GREY_50
            header_border = ft.Colors.BLUE_GREY_200
            segment_bg = ft.Colors.WHITE
        
        # Update header container theme
        if hasattr(self, 'header_container'):
            self.header_container.bgcolor = header_bg
            self.header_container.border = ft.border.all(1, header_border)
            
            # Update the title text color for better visibility
            try:
                # Find and update the title text
                title_text = self.header_container.content.controls[0].controls[0]
                if hasattr(title_text, 'color'):
                    title_text.color = text_color
            except Exception:
                pass
        
        # Update segmented button theme
        if hasattr(self, 'view_mode_selector'):
            try:
                # Update segment styling for dark mode
                for segment in self.view_mode_selector.segments:
                    if hasattr(segment, 'label') and hasattr(segment.label, 'color'):
                        segment.label.color = text_color
                        
                # Update the segmented button style
                if is_dark_mode:
                    self.view_mode_selector.style = ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        bgcolor=ft.Colors.GREY_800,
                        color=text_color,
                    )
                else:
                    self.view_mode_selector.style = ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        bgcolor=ft.Colors.WHITE,
                        color=text_color,
                    )
            except Exception:
                pass
        
        # Update text field themes
        text_fields = []
        if hasattr(self, 'plain_text_field'):
            text_fields.append(self.plain_text_field)
        if hasattr(self, 'syntax_highlighted_field'):
            text_fields.append(self.syntax_highlighted_field)
        if hasattr(self, 'unstructured_field'):
            text_fields.append(self.unstructured_field)
            
        for field in text_fields:
            if field:
                field.bgcolor = text_bg
                field.color = text_color
                field.border_color = border_color
                field.focused_border_color = border_color
                
                # Update text style for better visibility
                field.text_style = ft.TextStyle(
                    font_family="Consolas, 'Courier New', monospace",
                    size=12,
                    color=text_color,
                )
        
        # Update view containers background and text colors
        view_containers = []
        if hasattr(self, 'plain_text_view'):
            view_containers.append(('plain_text_view', self.plain_text_view, "📄 Plain Text View"))
        if hasattr(self, 'syntax_highlighted_view'):
            view_containers.append(('syntax_highlighted_view', self.syntax_highlighted_view, "🎨 Syntax Highlighted View"))
        if hasattr(self, 'unstructured_view'):
            view_containers.append(('unstructured_view', self.unstructured_view, "🔍 Unstructured Data View"))
            
        for view_name, container, title_text in view_containers:
            if container:
                container.bgcolor = text_bg if is_dark_mode else None
                container.border = ft.border.all(1, border_color) if is_dark_mode else None
                container.border_radius = 10 if is_dark_mode else None
                
                # Update the title text color in each view
                try:
                    title_row = container.content.controls[0]  # First row contains title
                    title_element = title_row.controls[0]  # First element is the title text
                    if hasattr(title_element, 'color'):
                        title_element.color = text_color
                except Exception:
                    pass
        
        # Force update the page
        try:
            self.page.update()
        except Exception as e:
            print(f"[EnhancedDataView] Theme update error: {e}")
            pass
    
    def refresh(self):
        """Refresh the current view."""
        if self.current_view_mode == "table":
            if hasattr(self.table_widget, 'refresh'):
                self.table_widget.refresh()
        else:
            # Refresh the current text view
            if self.current_view_mode == "plain_text":
                self._update_plain_text_view()
            elif self.current_view_mode == "syntax_highlighted":
                self._update_syntax_highlighted_view()
            elif self.current_view_mode == "unstructured":
                self._update_unstructured_view()
