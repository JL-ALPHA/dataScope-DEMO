"""
Enhanced recommendation display for DataScope UI
"""

import flet as ft
from typing import List
from recommendation_engine import Recommendation, recommendation_engine


def get_theme_colors(page: ft.Page):
    """Get theme-appropriate colors based on current mode."""
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    
    if is_dark:
        return {
            'panel_bg': ft.Colors.GREY_900,
            'panel_border': ft.Colors.GREY_700,
            'content_bg': ft.Colors.GREY_800,
            'content_border': ft.Colors.GREY_600,
            'text_primary': ft.Colors.WHITE,
            'text_secondary': ft.Colors.GREY_300,
            'text_muted': ft.Colors.GREY_400,
            'card_high_bg': ft.Colors.RED_900,
            'card_high_border': ft.Colors.RED_700,
            'card_medium_bg': ft.Colors.ORANGE_900,
            'card_medium_border': ft.Colors.ORANGE_700,
            'card_low_bg': ft.Colors.BLUE_900,
            'card_low_border': ft.Colors.BLUE_700,
            'card_critical_bg': ft.Colors.RED_900,
            'button_bg': ft.Colors.BLUE_700,
            'accent_color': ft.Colors.AMBER_600
        }
    else:
        return {
            'panel_bg': ft.Colors.WHITE,
            'panel_border': ft.Colors.GREY_300,
            'content_bg': ft.Colors.BLUE_50,
            'content_border': ft.Colors.BLUE_200,
            'text_primary': ft.Colors.BLACK,
            'text_secondary': ft.Colors.GREY_700,
            'text_muted': ft.Colors.BLUE_GREY_600,
            'card_high_bg': ft.Colors.RED_50,
            'card_high_border': ft.Colors.RED_300,
            'card_medium_bg': ft.Colors.ORANGE_50,
            'card_medium_border': ft.Colors.ORANGE_300,
            'card_low_bg': ft.Colors.BLUE_50,
            'card_low_border': ft.Colors.BLUE_300,
            'card_critical_bg': ft.Colors.RED_100,
            'button_bg': ft.Colors.BLUE_600,
            'accent_color': ft.Colors.AMBER_600
        }


def create_interactive_recommendation_card(rec: Recommendation, on_click_handler, on_dismiss_handler, theme_colors) -> ft.Container:
    """Create an interactive recommendation card with click and dismiss functionality."""
    
    # Determine card styling based on urgency
    urgency_styles = {
        'critical': {
            'bg_color': theme_colors['card_critical_bg'] if 'card_critical_bg' in theme_colors else ft.Colors.RED_100,
            'border_color': ft.Colors.RED_500,
            'icon_color': ft.Colors.RED_700
        },
        'high': {
            'bg_color': theme_colors['card_high_bg'],
            'border_color': theme_colors['card_high_border'],
            'icon_color': ft.Colors.ORANGE_700
        },
        'normal': {
            'bg_color': theme_colors['card_medium_bg'],
            'border_color': theme_colors['card_medium_border'],
            'icon_color': ft.Colors.BLUE_700
        },
        'low': {
            'bg_color': theme_colors['card_low_bg'],
            'border_color': theme_colors['card_low_border'],
            'icon_color': ft.Colors.GREY_600
        }
    }
    
    style = urgency_styles.get(rec.urgency, urgency_styles['normal'])
    
    # Create action button
    action_button = ft.ElevatedButton(
        text=f"Run {rec.action}",
        icon=ft.Icons.PLAY_ARROW,
        on_click=lambda e: on_click_handler(rec.action, rec.parameters),
        style=ft.ButtonStyle(
            bgcolor=theme_colors['button_bg'],
            color=ft.Colors.WHITE,
            padding=ft.Padding(10, 5, 10, 5)
        ),
        tooltip=f"Click to run {rec.action} analysis"
    ) if rec.interactive else None
    
    # Create info button for explanation
    info_button = ft.IconButton(
        icon=ft.Icons.INFO_OUTLINE,
        icon_color=style['icon_color'],
        tooltip=rec.explanation,
        icon_size=16
    ) if rec.explanation else None
    
    # Create dismiss button
    dismiss_button = ft.IconButton(
        icon=ft.Icons.CLOSE,
        icon_color=ft.Colors.GREY_600,
        tooltip="Dismiss this recommendation",
        on_click=lambda e: on_dismiss_handler(f"{rec.action}_{rec.title}"),
        icon_size=16
    )
    
    # Build button row
    button_row_controls = []
    if action_button:
        button_row_controls.append(action_button)
    if info_button:
        button_row_controls.append(info_button)
    button_row_controls.append(dismiss_button)
    
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text(rec.icon, size=20),
                ft.Column([
                    ft.Text(
                        rec.title,
                        weight=ft.FontWeight.BOLD,
                        color=theme_colors['text_primary'],
                        size=14
                    ),
                    ft.Text(
                        rec.message,
                        color=theme_colors['text_secondary'],
                        size=12,
                        expand=True
                    )
                ], expand=True, spacing=2),
            ], spacing=10),
            ft.Row(
                button_row_controls,
                alignment=ft.MainAxisAlignment.END,
                spacing=5
            ) if button_row_controls else ft.Container()
        ], spacing=8),
        bgcolor=style['bg_color'],
        border=ft.Border.all(1, style['border_color']),
        border_radius=8,
        padding=ft.Padding(12, 8, 12, 8),
        margin=ft.Margin(0, 0, 0, 8)
    )


def create_recommendations_panel(page: ft.Page = None) -> tuple[ft.Container, ft.Column]:
    """Create a collapsible recommendations panel for the UI.
    
    Returns
    -------
    tuple[ft.Container, ft.Column]
        The panel container and the content column for updates
    """
    
    # Get theme colors
    colors = get_theme_colors(page) if page else get_theme_colors(type('Page', (), {'theme_mode': ft.ThemeMode.LIGHT})())
    
    # Recommendations content (initially empty)
    recommendations_content = ft.Column(
        [
            ft.Text(
                "💡 Load a dataset to get intelligent recommendations!",
                size=14,
                color=colors['text_muted'],
                italic=True
            )
        ],
        spacing=5
    )
    
    # Expandable recommendations panel
    recommendations_panel = ft.ExpansionTile(
        title=ft.Text("🤖 Smart Recommendations", weight=ft.FontWeight.BOLD, color=colors['text_primary']),
        subtitle=ft.Text("AI-powered insights for your data analysis", size=12, color=colors['text_secondary']),
        leading=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=colors['accent_color']),
        controls=[
            ft.Container(
                content=recommendations_content,
                padding=ft.padding.all(10),
                margin=ft.margin.only(left=10, right=10, bottom=10),
                border_radius=8,
                bgcolor=colors['content_bg'],
                border=ft.border.all(1, colors['content_border'])
            )
        ],
        initially_expanded=True,
    )
    
    panel_container = ft.Container(
        content=recommendations_panel,
        margin=ft.margin.only(bottom=10),
        border_radius=8,
        border=ft.border.all(1, colors['panel_border']),
        bgcolor=colors['panel_bg']
    )
    
    return panel_container, recommendations_content


def update_recommendations_panel(recommendations: List[Recommendation], panel_content: ft.Column, page: ft.Page, global_data_loaded=None, global_current_df=None, trigger_function=None):
    """Update the recommendations panel with new recommendations."""
    
    # Clear existing content
    panel_content.controls.clear()
    
    # Get theme colors
    colors = get_theme_colors(page)
    
    if not recommendations:
        panel_content.controls.append(
            ft.Text(
                "✅ Your data looks great! No immediate issues detected.",
                size=14,
                color=ft.Colors.GREEN_600 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREEN_400,
                weight=ft.FontWeight.W_500
            )
        )
    else:
        # Group recommendations by priority
        high_priority = [r for r in recommendations if r.priority == 1]
        medium_priority = [r for r in recommendations if r.priority == 2]
        low_priority = [r for r in recommendations if r.priority == 3]
        
        # Add high priority recommendations
        if high_priority:
            panel_content.controls.append(
                ft.Text("🔥 High Priority", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.RED_400)
            )
            for rec in high_priority:
                panel_content.controls.append(create_recommendation_card(rec, page, global_data_loaded, global_current_df, trigger_function))
        
        # Add medium priority recommendations
        if medium_priority:
            if high_priority:  # Add spacing if there were high priority items
                panel_content.controls.append(ft.Divider(height=10, color=colors['content_border']))
            panel_content.controls.append(
                ft.Text("📋 Recommended Actions", weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.ORANGE_400)
            )
            for rec in medium_priority:
                panel_content.controls.append(create_recommendation_card(rec, page, global_data_loaded, global_current_df, trigger_function))
        
        # Add low priority recommendations
        if low_priority:
            if high_priority or medium_priority:  # Add spacing
                panel_content.controls.append(ft.Divider(height=10, color=colors['content_border']))
            panel_content.controls.append(
                ft.Text("💡 Tips & Insights", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.BLUE_400)
            )
            for rec in low_priority:
                panel_content.controls.append(create_recommendation_card(rec, page, global_data_loaded, global_current_df, trigger_function))
    
    # Update the UI
    page.update()


def create_recommendation_card(rec: Recommendation, page: ft.Page, global_data_loaded=None, global_current_df=None, trigger_function=None) -> ft.Container:
    """Create a clickable recommendation card."""
    
    # Get theme colors
    colors = get_theme_colors(page)
    
    # Color scheme based on priority and theme
    if rec.priority == 1:
        border_color = colors['card_high_border']
        bg_color = colors['card_high_bg']
    elif rec.priority == 2:
        border_color = colors['card_medium_border']
        bg_color = colors['card_medium_bg']
    else:
        border_color = colors['card_low_border']
        bg_color = colors['card_low_bg']
    
    # Action button
    action_button = None
    if rec.action and rec.action != "export" and rec.action != "search":
        action_button = ft.ElevatedButton(
            text=f"Run {rec.action}",
            icon=ft.Icons.PLAY_ARROW,
            on_click=lambda e: execute_recommendation_action(rec.action, page, global_data_loaded, global_current_df, trigger_function),
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=colors['button_bg'],
            ),
            height=32,
        )
    
    card_content = ft.Column([
        ft.Row([
            ft.Text(rec.icon, size=16),
            ft.Text(rec.title, weight=ft.FontWeight.BOLD, size=14, expand=True, color=colors['text_primary']),
        ], spacing=8),
        ft.Text(rec.message, size=12, color=colors['text_secondary']),
        action_button if action_button else ft.Container(height=5),
    ], spacing=5, tight=True)
    
    return ft.Container(
        content=card_content,
        padding=ft.padding.all(8),
        margin=ft.margin.only(bottom=5),
        border_radius=6,
        bgcolor=bg_color,
        border=ft.border.all(1, border_color),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )


def execute_recommendation_action(action: str, page: ft.Page, global_data_loaded=None, global_current_df=None, trigger_function=None):
    """Execute the recommended action by triggering the appropriate analysis."""
    print(f"[Recommendations] Executing action: {action}")
    
    # Use passed global state instead of importing (which creates separate module instances)
    if global_data_loaded is None or global_current_df is None or trigger_function is None:
        print(f"[Recommendations] ERROR: Missing required global state parameters")
        return
    
    print(f"[Recommendations] Using passed global state: data_loaded={global_data_loaded}, current_df is not None: {global_current_df is not None}")
    
    # Check data state directly from passed globals
    if not global_data_loaded or global_current_df is None:
        print(f"[Recommendation] Please load data first before running analysis.")
        return
    
    # Call the trigger function with the correct data
    try:
        trigger_function(action, page, global_current_df)
        print(f"[Recommendations] Successfully triggered analysis: {action}")
    except Exception as e:
        print(f"[Recommendations] Error executing {action}: {e}")
        import traceback
        traceback.print_exc()


def refresh_recommendations_theme(panel_container: ft.Container, panel_content: ft.Column, page: ft.Page):
    """Refresh the recommendations panel theme when the theme changes."""
    try:
        # Get the new theme colors
        colors = get_theme_colors(page)
        
        # Update panel container colors
        panel_container.bgcolor = colors['panel_bg']
        panel_container.border = ft.border.all(1, colors['panel_border'])
        
        # Find and update the expansion tile content container
        if hasattr(panel_container.content, 'controls') and panel_container.content.controls:
            for control in panel_container.content.controls:
                if isinstance(control, ft.Container):
                    control.bgcolor = colors['content_bg']
                    control.border = ft.border.all(1, colors['content_border'])
        
        # Update all text colors in recommendations
        for control in panel_content.controls:
            if isinstance(control, ft.Text):
                # Update text colors based on content
                if "Load a dataset" in str(control.value):
                    control.color = colors['text_muted']
                elif "Your data looks great" in str(control.value):
                    control.color = ft.Colors.GREEN_600 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREEN_400
                elif "High Priority" in str(control.value):
                    control.color = ft.Colors.RED_700 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.RED_400
                elif "Recommended Actions" in str(control.value):
                    control.color = ft.Colors.ORANGE_700 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.ORANGE_400
                elif "Tips & Insights" in str(control.value):
                    control.color = ft.Colors.BLUE_700 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.BLUE_400
            elif isinstance(control, ft.Container):
                # Update recommendation cards
                _update_card_theme(control, page)
            elif isinstance(control, ft.Divider):
                control.color = colors['content_border']
        
        print(f"[Recommendations] Theme updated to {'dark' if page.theme_mode == ft.ThemeMode.DARK else 'light'} mode")
        
    except Exception as e:
        print(f"[Recommendations] Error updating theme: {e}")
        import traceback
        traceback.print_exc()


def _update_card_theme(card: ft.Container, page: ft.Page):
    """Update a single recommendation card's theme."""
    try:
        colors = get_theme_colors(page)
        
        # Update card background and border based on current colors
        if card.bgcolor == ft.Colors.RED_50 or card.bgcolor == ft.Colors.RED_900:
            card.bgcolor = colors['card_high_bg']
            card.border = ft.border.all(1, colors['card_high_border'])
        elif card.bgcolor == ft.Colors.ORANGE_50 or card.bgcolor == ft.Colors.ORANGE_900:
            card.bgcolor = colors['card_medium_bg']
            card.border = ft.border.all(1, colors['card_medium_border'])
        else:
            card.bgcolor = colors['card_low_bg']
            card.border = ft.border.all(1, colors['card_low_border'])
        
        # Update text colors within the card
        if hasattr(card.content, 'controls'):
            for control in card.content.controls:
                if isinstance(control, ft.Row) and hasattr(control, 'controls'):
                    for row_control in control.controls:
                        if isinstance(row_control, ft.Text) and row_control.weight == ft.FontWeight.BOLD:
                            row_control.color = colors['text_primary']
                elif isinstance(control, ft.Text):
                    control.color = colors['text_secondary']
                elif isinstance(control, ft.ElevatedButton):
                    control.style.bgcolor = colors['button_bg']
                    
    except Exception as e:
        print(f"[Recommendations] Error updating card theme: {e}")
