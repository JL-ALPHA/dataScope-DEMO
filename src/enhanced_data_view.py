"""
Enhanced Data View Module

Provides alternative view modes for data display including:
- Standard DataTable View (existing functionality)
- Plain Text View 
- Syntax Highlighted View

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
from syntax_highlight_utils import detect_language, highlight_code_with_lines, get_language_options


class EnhancedDataView:
    """Enhanced data view widget with multiple display modes."""
    
    def __init__(self, page: ft.Page, accessibility_manager=None):
        self.page = page
        self.accessibility_manager = accessibility_manager
        self.current_df: Optional[pd.DataFrame] = None
        self.current_view_mode: Literal["table", "plain_text", "syntax_highlighted"] = "table"
        self.raw_syntax_content: str = ""  # Store raw content for copying
        
        # Magnification settings
        self.magnification_level = 100  # Percentage
        self.magnification_enabled = False
        self.min_magnification = 50
        self.max_magnification = 300
        self.magnification_dropdown = None
        
        # Initialize the original DataViewWidget for table mode
        self.table_widget = DataViewWidget(page)
        
        # View mode containers
        self.plain_text_view: Optional[ft.Container] = None
        self.syntax_highlighted_view: Optional[ft.Container] = None
        
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
                
                # Initialize magnification dropdown with current setting
                if hasattr(self, 'magnification_dropdown') and self.accessibility_manager:
                    current_mag = self.accessibility_manager.magnification_level
                    self.magnification_dropdown.value = f"{current_mag}%"
                    
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
            ],
            on_change=self._on_view_mode_change,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.GREY_800 if is_dark_mode else ft.Colors.WHITE,
                color=title_color,
            ),
        )
        
        # Create magnification dropdown with accessibility features
        self.magnification_dropdown = ft.Dropdown(
            label="🔍 Magnification",
            value="100%",
            options=[
                ft.dropdown.Option("50%", "50% - Extra Small"),
                ft.dropdown.Option("75%", "75% - Small"),
                ft.dropdown.Option("100%", "100% - Normal"),
                ft.dropdown.Option("125%", "125% - Large"),
                ft.dropdown.Option("150%", "150% - Extra Large"),
                ft.dropdown.Option("200%", "200% - Double"),
                ft.dropdown.Option("250%", "250% - Large Scale"),
                ft.dropdown.Option("300%", "300% - Maximum"),
            ],
            width=220,
            on_change=self._on_magnification_change,
            tooltip="Adjust view magnification for better visibility",
            text_style=ft.TextStyle(
                size=14,
                color=title_color
            ),
            border_color=ft.Colors.GREY_600 if is_dark_mode else ft.Colors.BLUE_GREY_300,
            focused_border_color=ft.Colors.BLUE_400,
            bgcolor=ft.Colors.GREY_800 if is_dark_mode else ft.Colors.WHITE,
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
                    content=ft.Row([
                        ft.Container(
                            content=self.view_mode_selector,
                            expand=True,
                        ),
                        ft.Container(
                            content=self.magnification_dropdown,
                            padding=ft.padding.only(left=10),
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
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
        
        # Syntax Highlighted View - using Pygments with real syntax highlighting
        self.syntax_highlighted_field = ft.Markdown(
            value="",
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            code_theme=ft.MarkdownCodeTheme.ATOM_ONE_DARK if is_dark_mode else ft.MarkdownCodeTheme.ATOM_ONE_LIGHT,
        )
        
        self.syntax_highlighted_view = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("🎨 Real Syntax Highlighting", 
                           style=ft.TextThemeStyle.TITLE_SMALL, 
                           weight=ft.FontWeight.BOLD,
                           color=title_color),
                    self._create_syntax_controls(),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(
                    content=ft.Column([
                        self.syntax_highlighted_field,
                    ], scroll=ft.ScrollMode.AUTO),
                    expand=True,
                    bgcolor=text_bg if is_dark_mode else None,
                    border=ft.border.all(1, border_color),
                    border_radius=10,
                    padding=10,
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
        # Get supported languages from syntax highlighting utils
        supported_langs = get_language_options()
        
        self.syntax_format_dropdown = ft.Dropdown(
            label="Language",
            width=140,
            value="auto",
            options=[
                ft.dropdown.Option("auto", "Auto-detect"),
            ] + [
                ft.dropdown.Option(lang_code, lang_name) 
                for lang_code, lang_name in supported_langs
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
        
        # Update the page
        self.page.update()
    
    def _on_magnification_change(self, e: ft.ControlEvent):
        """Handle magnification level changes."""
        print(f"[EnhancedDataView] Magnification dropdown changed to: {e.control.value}")
        try:
            # Extract percentage value from dropdown selection
            mag_value = e.control.value
            if mag_value:
                # Convert "100%" to 100
                percentage = int(mag_value.replace('%', ''))
                print(f"[EnhancedDataView] Setting magnification to {percentage}%")
                
                # If accessibility manager is available, use it
                if self.accessibility_manager:
                    print(f"[EnhancedDataView] Using accessibility manager for magnification")
                    # Update accessibility manager
                    success = self.accessibility_manager.set_magnification_level(percentage)
                    
                    if success:
                        # Apply magnification to this enhanced data view
                        self._apply_magnification(percentage)
                        
                        # Announce change for screen reader users
                        if self.accessibility_manager.screen_reader_enabled:
                            announcement = f"Magnification set to {mag_value}"
                            self.accessibility_manager.announce_change(announcement)
                            
                        # Log the change
                        self.accessibility_manager.logger.info(f"Enhanced data view magnification changed to {mag_value}")
                        print(f"[EnhancedDataView] Successfully applied magnification {percentage}%")
                    else:
                        print(f"[EnhancedDataView] Failed to set magnification via accessibility manager")
                        # Reset dropdown to previous value on failure
                        self.magnification_dropdown.value = f"{self.accessibility_manager.magnification_level}%"
                        self.page.update()
                else:
                    # No accessibility manager - apply magnification directly
                    print(f"[EnhancedDataView] Applying magnification {percentage}% directly (no accessibility manager)")
                    self._apply_magnification(percentage)
                    
        except Exception as e:
            error_msg = f"Error changing magnification: {str(e)}"
            print(f"[EnhancedDataView] {error_msg}")
            if self.accessibility_manager:
                self.accessibility_manager.logger.error(error_msg)
            else:
                print(f"[EnhancedDataView] {error_msg}")
            
            # Reset dropdown to safe value
            self.magnification_dropdown.value = "100%"
            self.page.update()
    
    def _apply_magnification(self, percentage: int):
        """Apply magnification scaling to enhanced data view components."""
        print(f"[EnhancedDataView] Applying magnification {percentage}% to components")
        try:
            scale_factor = percentage / 100.0
            print(f"[EnhancedDataView] Scale factor: {scale_factor}")
            
            # Update text sizes based on scale factor
            base_font_size = 14
            scaled_font_size = max(8, int(base_font_size * scale_factor))
            print(f"[EnhancedDataView] Scaled font size: {scaled_font_size}")
            
            # Apply to header title
            if hasattr(self, 'header_container') and self.header_container.content:
                title_row = self.header_container.content.controls[0]
                if title_row.controls:
                    title_text = title_row.controls[0]
                    if hasattr(title_text, 'size'):
                        title_text.size = max(16, int(20 * scale_factor))
                        print(f"[EnhancedDataView] Updated header title size to {title_text.size}")
            
            # Apply to plain text view
            if hasattr(self, 'plain_text_field'):
                self.plain_text_field.text_size = scaled_font_size
                print(f"[EnhancedDataView] Updated plain text field size to {scaled_font_size}")
            
            # Apply to syntax highlighted view
            if hasattr(self, 'syntax_text_field'):
                self.syntax_text_field.text_size = scaled_font_size
                print(f"[EnhancedDataView] Updated syntax text field size to {scaled_font_size}")
            
            # Apply to table widget if it supports magnification
            if hasattr(self.table_widget, 'apply_magnification'):
                print(f"[EnhancedDataView] Applying magnification to table widget")
                self.table_widget.apply_magnification(percentage)
            else:
                print(f"[EnhancedDataView] Table widget does not support magnification")
            
            # Update dropdown styling
            if hasattr(self, 'magnification_dropdown'):
                self.magnification_dropdown.text_size = scaled_font_size
                print(f"[EnhancedDataView] Updated dropdown text size to {scaled_font_size}")
                
            # Update view mode selector
            if hasattr(self, 'view_mode_selector'):
                for segment in self.view_mode_selector.segments:
                    if hasattr(segment.label, 'size'):
                        segment.label.size = scaled_font_size
                print(f"[EnhancedDataView] Updated view mode selector sizes")
            
            # Update the page
            print(f"[EnhancedDataView] Updating page to reflect magnification changes")
            self.page.update()
            print(f"[EnhancedDataView] Magnification {percentage}% applied successfully")
            
        except Exception as e:
            error_msg = f"Error applying magnification to enhanced data view: {str(e)}"
            if self.accessibility_manager:
                self.accessibility_manager.logger.error(error_msg)
            else:
                print(f"[EnhancedDataView] {error_msg}")
    
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
        """Update the syntax highlighted view with current data using real Pygments highlighting."""
        if self.current_df is None:
            self.syntax_highlighted_field.value = "```\nNo data loaded\n```"
            self.raw_syntax_content = "No data loaded"
            return
        
        try:
            # Get the selected language/format
            selected_format = getattr(self.syntax_format_dropdown, 'value', 'auto')
            
            # Convert DataFrame to appropriate format based on selection
            if selected_format == "auto":
                # Auto-detect based on data structure - default to JSON for DataFrames
                json_data = self.current_df.head(100).to_dict('records')
                raw_content = json.dumps(json_data, indent=2, default=str)
                detected_language = detect_language(raw_content)
                language = detected_language if detected_language != "text" else "json"
            
            elif selected_format == "json":
                json_data = self.current_df.head(100).to_dict('records')
                raw_content = json.dumps(json_data, indent=2, default=str)
                language = "json"
                
            elif selected_format == "csv":
                buffer = StringIO()
                self.current_df.head(100).to_csv(buffer, index=False)
                raw_content = buffer.getvalue()
                language = "csv"
                
            elif selected_format == "xml":
                raw_content = self._dataframe_to_xml()
                language = "xml"
                
            elif selected_format == "yaml":
                raw_content = self._dataframe_to_yaml()
                language = "yaml"
                
            elif selected_format == "python":
                # Show DataFrame as Python code
                raw_content = f"import pandas as pd\n\n# DataFrame with {len(self.current_df)} rows and {len(self.current_df.columns)} columns\ndf = pd.DataFrame({{\n"
                for col in self.current_df.columns[:10]:  # Show first 10 columns
                    sample_values = self.current_df[col].head(3).tolist()
                    raw_content += f"    '{col}': {sample_values},\n"
                raw_content += "})"
                language = "python"
            
            else:
                # Use the selected language directly
                if selected_format == "csv":
                    buffer = StringIO()
                    self.current_df.head(100).to_csv(buffer, index=False)
                    raw_content = buffer.getvalue()
                else:
                    json_data = self.current_df.head(100).to_dict('records')
                    raw_content = json.dumps(json_data, indent=2, default=str)
                language = selected_format
            
            # Limit content size for performance
            if len(raw_content) > 50000:
                raw_content = raw_content[:50000] + "\n\n... (Content truncated for performance)"
            
            # Get theme based on current page theme
            is_dark_mode = getattr(self.page, 'theme_mode', ft.ThemeMode.LIGHT) == ft.ThemeMode.DARK
            
            # Generate syntax highlighted content with line numbers
            highlighted_content = highlight_code_with_lines(
                code=raw_content,
                lang=language,
                dark_mode=is_dark_mode
            )
            
            # Set the highlighted content in markdown format
            self.syntax_highlighted_field.value = f"```{language}\n{raw_content}\n```"
            
            # Store raw content for copying
            self.raw_syntax_content = raw_content
            
            # Update the code theme based on current theme
            self.syntax_highlighted_field.code_theme = (
                ft.MarkdownCodeTheme.ATOM_ONE_DARK if is_dark_mode 
                else ft.MarkdownCodeTheme.ATOM_ONE_LIGHT
            )
            
            print(f"[EnhancedDataView] Applied {language} syntax highlighting with line numbers")
            
        except Exception as e:
            error_msg = f"Error generating syntax highlighted view: {str(e)}"
            self.syntax_highlighted_field.value = f"```\n{error_msg}\n```"
            self.raw_syntax_content = error_msg
            print(f"[EnhancedDataView] Syntax highlighting error: {str(e)}")
        
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
    
    # Event handlers for controls
    def _copy_plain_text(self, e):
        """Copy plain text to clipboard."""
        if self.plain_text_field.value:
            self.page.set_clipboard(self.plain_text_field.value)
            self._show_copy_notification()
    
    def _copy_syntax_text(self, e):
        """Copy syntax highlighted text to clipboard (raw content without markdown formatting)."""
        if self.raw_syntax_content:
            self.page.set_clipboard(self.raw_syntax_content)
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
    
    def _on_syntax_format_change(self, e):
        """Handle syntax format changes."""
        self._update_syntax_highlighted_view()
    
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
        
        # Update magnification dropdown theme
        if hasattr(self, 'magnification_dropdown'):
            try:
                self.magnification_dropdown.bgcolor = text_bg
                self.magnification_dropdown.border_color = border_color
                self.magnification_dropdown.focused_border_color = ft.Colors.BLUE_400
                self.magnification_dropdown.text_style = ft.TextStyle(
                    size=14,
                    color=text_color
                )
            except Exception:
                pass
        
        # Update text field and markdown themes
        text_fields = []
        if hasattr(self, 'plain_text_field'):
            text_fields.append(self.plain_text_field)
            
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
        
        # Update syntax highlighted field (Markdown) theme
        if hasattr(self, 'syntax_highlighted_field'):
            self.syntax_highlighted_field.code_theme = (
                ft.MarkdownCodeTheme.ATOM_ONE_DARK if is_dark_mode 
                else ft.MarkdownCodeTheme.ATOM_ONE_LIGHT
            )
        
        # Update view containers background and text colors
        view_containers = []
        if hasattr(self, 'plain_text_view'):
            view_containers.append(('plain_text_view', self.plain_text_view, "📄 Plain Text View"))
        if hasattr(self, 'syntax_highlighted_view'):
            view_containers.append(('syntax_highlighted_view', self.syntax_highlighted_view, "🎨 Real Syntax Highlighting"))
            
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
