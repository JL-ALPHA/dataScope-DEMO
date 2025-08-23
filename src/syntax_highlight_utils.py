"""
Syntax Highlighting Utilities for DataScope Enhanced Data View

Provides real syntax highlighting with line numbers using Pygments.
Supports multiple languages and themes with automatic detection.
"""

import pygments
from pygments.lexers import get_lexer_by_name, guess_lexer, JsonLexer, XmlLexer, YamlLexer, PythonLexer
from pygments.formatters import HtmlFormatter
from typing import Tuple, Optional
import pandas as pd
import json
import re


def detect_language(text: str, filename: str = "") -> str:
    """
    Auto-detect the language/format of the given text.
    
    Args:
        text: The text content to analyze
        filename: Optional filename for extension-based detection
        
    Returns:
        Language identifier for Pygments
    """
    # Check file extension first
    if filename:
        if filename.endswith('.json'):
            return 'json'
        elif filename.endswith('.csv'):
            return 'csv'
        elif filename.endswith('.xml'):
            return 'xml'
        elif filename.endswith('.yaml') or filename.endswith('.yml'):
            return 'yaml'
        elif filename.endswith('.py'):
            return 'python'
    
    # Content-based detection
    text_sample = text.strip()[:1000]  # First 1000 chars
    
    # JSON detection
    if text_sample.startswith(('{', '[')):
        try:
            json.loads(text_sample[:500])
            return 'json'
        except:
            pass
    
    # CSV detection - look for common patterns
    if ',' in text_sample and '\n' in text_sample:
        lines = text_sample.split('\n')[:3]
        if len(lines) >= 2:
            # Check if first few lines have similar comma counts
            comma_counts = [line.count(',') for line in lines if line.strip()]
            if len(set(comma_counts)) <= 2 and comma_counts[0] > 0:
                return 'csv'
    
    # XML detection
    if text_sample.startswith('<?xml') or ('<' in text_sample and '>' in text_sample):
        return 'xml'
    
    # YAML detection
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', text_sample, re.MULTILINE):
        return 'yaml'
    
    # Python detection
    python_keywords = ['def ', 'class ', 'import ', 'from ', 'if __name__']
    if any(keyword in text_sample for keyword in python_keywords):
        return 'python'
    
    # Default to text
    return 'text'


def get_theme_style(dark_mode: bool = True) -> str:
    """
    Get appropriate Pygments style based on theme mode.
    
    Args:
        dark_mode: Whether to use dark theme
        
    Returns:
        Pygments style name
    """
    if dark_mode:
        return 'monokai'  # Dark theme
    else:
        return 'default'  # Light theme


def highlight_code_with_lines(code: str, lang: str = None, dark_mode: bool = True, 
                            filename: str = "") -> Tuple[str, str]:
    """
    Return HTML with syntax highlighting and line numbers.
    
    Args:
        code: The code/text to highlight
        lang: Language identifier (auto-detected if None)
        dark_mode: Whether to use dark theme
        filename: Optional filename for better detection
        
    Returns:
        Tuple of (highlighted_html, detected_language)
    """
    # Auto-detect language if not provided
    if not lang:
        lang = detect_language(code, filename)
    
    # Get appropriate lexer
    try:
        if lang == 'csv':
            # Custom CSV highlighting (treat as text with basic formatting)
            lexer = get_lexer_by_name('text')
        else:
            lexer = get_lexer_by_name(lang)
    except Exception:
        try:
            # Fallback to guess_lexer
            lexer = guess_lexer(code)
        except:
            # Ultimate fallback to text
            lexer = get_lexer_by_name('text')
    
    # Configure formatter with line numbers and theme
    style = get_theme_style(dark_mode)
    formatter = HtmlFormatter(
        linenos='table',  # Line numbers in a table
        style=style,
        noclasses=True,  # Inline CSS
        cssclass='highlight',
        linenostart=1,
        hl_lines=[],  # Can be used to highlight specific lines
        wrapcode=True,
    )
    
    # Generate highlighted HTML
    try:
        highlighted = pygments.highlight(code, lexer, formatter)
        return highlighted, lang
    except Exception as e:
        # Fallback to plain text if highlighting fails
        text_lexer = get_lexer_by_name('text')
        highlighted = pygments.highlight(code, text_lexer, formatter)
        return highlighted, 'text'


def highlight_dataframe_as_csv(df: pd.DataFrame, max_rows: int = 100, 
                              dark_mode: bool = True) -> Tuple[str, str]:
    """
    Convert DataFrame to CSV format and apply syntax highlighting.
    
    Args:
        df: Pandas DataFrame to highlight
        max_rows: Maximum rows to include
        dark_mode: Whether to use dark theme
        
    Returns:
        Tuple of (highlighted_html, 'csv')
    """
    # Convert DataFrame to CSV string
    if len(df) > max_rows:
        csv_text = df.head(max_rows).to_csv(index=True)
        csv_text += f"\n... ({len(df) - max_rows} more rows)"
    else:
        csv_text = df.to_csv(index=True)
    
    # Apply highlighting
    return highlight_code_with_lines(csv_text, 'csv', dark_mode)


def create_highlighted_html_wrapper(highlighted_html: str, dark_mode: bool = True) -> str:
    """
    Wrap highlighted HTML with proper styling and container.
    
    Args:
        highlighted_html: The Pygments-generated HTML
        dark_mode: Whether to use dark theme
        
    Returns:
        Complete HTML with styling
    """
    # Additional CSS for better appearance
    bg_color = "#272822" if dark_mode else "#ffffff"
    text_color = "#f8f8f2" if dark_mode else "#000000"
    border_color = "#49483e" if dark_mode else "#cccccc"
    
    wrapper = f"""
    <div style="
        background-color: {bg_color};
        color: {text_color};
        border: 1px solid {border_color};
        border-radius: 8px;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 12px;
        line-height: 1.4;
        overflow: auto;
        max-height: 500px;
        padding: 0;
        margin: 0;
    ">
        {highlighted_html}
    </div>
    """
    
    return wrapper


# Language mappings for dropdown
SUPPORTED_LANGUAGES = {
    'auto': 'Auto-Detect',
    'csv': 'CSV',
    'json': 'JSON',
    'xml': 'XML',
    'yaml': 'YAML',
    'python': 'Python',
    'javascript': 'JavaScript',
    'sql': 'SQL',
    'text': 'Plain Text'
}


def get_language_options():
    """Get list of supported language options for dropdown."""
    return [(key, value) for key, value in SUPPORTED_LANGUAGES.items()]
