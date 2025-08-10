"""
Dynamic Recommendation Engine for DataScope
Provides intelligent, context-aware suggestions for data analysis workflows
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
import logging


@dataclass
class Recommendation:
    """A single recommendation for the user."""
    title: str
    message: str
    action: str
    priority: int  # 1=high, 2=medium, 3=low
    category: str  # 'quality', 'workflow', 'performance', 'insight'
    icon: str = "💡"
    
    def __str__(self):
        return f"[{self.icon}] {self.title}: {self.message} → {self.action}"


class RecommendationEngine:
    """
    Intelligent recommendation engine that analyzes datasets and user behavior
    to provide contextual suggestions for data analysis workflows.
    """
    
    def __init__(self):
        self.user_actions = []
        self.dataset_cache = {}
        
    def analyze_dataset(self, df: pd.DataFrame, filename: str) -> List[Recommendation]:
        """
        Analyze a dataset and generate intelligent recommendations.
        
        Parameters
        ----------
        df : pd.DataFrame
            The dataset to analyze
        filename : str
            Name of the file for context
            
        Returns
        -------
        List[Recommendation]
            List of recommendations sorted by priority
        """
        recommendations = []
        
        if df is None or df.empty:
            return recommendations
            
        # Cache dataset info for future contextual recommendations
        self.dataset_cache[filename] = {
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'dtypes': df.dtypes.to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
            'analyzed_at': time.time()
        }
        
        # 1. Always recommend starting with Data Preview for new datasets
        if not self._has_user_done_action("Data Preview"):
            recommendations.append(Recommendation(
                title="Start Here",
                message="Begin with Data Preview to understand your dataset structure and content.",
                action="Data Preview",
                priority=1,
                category="workflow",
                icon="🚀"
            ))
        
        # 2. Check for critical missing values
        missing_analysis = self._analyze_missing_values(df)
        if missing_analysis:
            recommendations.extend(missing_analysis)
            
        # 3. Check for duplicates (only for smaller datasets to avoid performance issues)
        if len(df) <= 50000:
            duplicate_analysis = self._analyze_duplicates(df)
            if duplicate_analysis:
                recommendations.extend(duplicate_analysis)
        
        # 4. Check for special characters in text columns
        special_char_analysis = self._analyze_special_characters(df)
        if special_char_analysis:
            recommendations.extend(special_char_analysis)
            
        # 5. Check for placeholder values
        placeholder_analysis = self._analyze_placeholders(df)
        if placeholder_analysis:
            recommendations.extend(placeholder_analysis)
            
        # 6. Performance recommendations for large datasets
        performance_recs = self._analyze_performance(df)
        if performance_recs:
            recommendations.extend(performance_recs)
            
        # Sort by priority (1=highest, 3=lowest)
        recommendations.sort(key=lambda x: (x.priority, x.category))
        
        return recommendations
    
    def get_contextual_recommendations(self, last_analysis: str) -> List[Recommendation]:
        """
        Get recommendations based on the last analysis performed.
        
        Parameters
        ----------
        last_analysis : str
            The type of analysis just completed
            
        Returns
        -------
        List[Recommendation]
            Context-aware follow-up recommendations
        """
        recommendations = []
        
        context_map = {
            "Data Preview": [
                Recommendation(
                    title="Next: Check Data Quality",
                    message="Now that you've seen the data structure, check for missing values.",
                    action="Missing Values",
                    priority=2,
                    category="workflow",
                    icon="🔍"
                )
            ],
            "Missing Values": [
                Recommendation(
                    title="Check for Duplicates",
                    message="After handling missing data, look for duplicate records.",
                    action="Duplicate Detection",
                    priority=2,
                    category="quality",
                    icon="🔄"
                )
            ],
            "Duplicate Detection": [
                Recommendation(
                    title="Analyze Text Quality",
                    message="Check for special characters and encoding issues in text fields.",
                    action="Special Character Analysis",
                    priority=2,
                    category="quality",
                    icon="📝"
                )
            ],
            "Special Character Analysis": [
                Recommendation(
                    title="Detect Placeholders",
                    message="Look for placeholder values like 'N/A', 'TBD', etc.",
                    action="Placeholder Detection",
                    priority=2,
                    category="quality",
                    icon="🏷️"
                )
            ]
        }
        
        return context_map.get(last_analysis, [])
    
    def log_user_action(self, action: str):
        """Log a user action for learning user behavior patterns."""
        self.user_actions.append({
            'action': action,
            'timestamp': time.time()
        })
        
        # Keep only recent actions (last 100)
        if len(self.user_actions) > 100:
            self.user_actions = self.user_actions[-100:]
    
    def format_recommendations_for_ui(self, recommendations: List[Recommendation]) -> str:
        """Format recommendations for display in the UI console."""
        if not recommendations:
            return "✅ No issues detected - your data looks great!"
            
        output = []
        output.append("🤖 SMART RECOMMENDATIONS:")
        output.append("")
        
        # Group by priority
        high_priority = [r for r in recommendations if r.priority == 1]
        medium_priority = [r for r in recommendations if r.priority == 2]
        low_priority = [r for r in recommendations if r.priority == 3]
        
        if high_priority:
            output.append("🔥 HIGH PRIORITY:")
            for rec in high_priority:
                output.append(f"   {rec}")
            output.append("")
        
        if medium_priority:
            output.append("📋 RECOMMENDED ACTIONS:")
            for rec in medium_priority:
                output.append(f"   {rec}")
            output.append("")
        
        if low_priority:
            output.append("💡 TIPS & INSIGHTS:")
            for rec in low_priority:
                output.append(f"   {rec}")
            output.append("")
        
        return "\n".join(output)
    
    def _has_user_done_action(self, action: str) -> bool:
        """Check if user has performed a specific action recently."""
        recent_actions = [a['action'] for a in self.user_actions[-10:]]
        return action in recent_actions
    
    def _analyze_missing_values(self, df: pd.DataFrame) -> List[Recommendation]:
        """Analyze missing values and generate recommendations."""
        recommendations = []
        missing_counts = df.isnull().sum()
        total_rows = len(df)
        
        # Find columns with significant missing values
        high_missing = missing_counts[missing_counts > total_rows * 0.3]
        medium_missing = missing_counts[(missing_counts > total_rows * 0.1) & 
                                       (missing_counts <= total_rows * 0.3)]
        
        if len(high_missing) > 0:
            cols = ', '.join(high_missing.index[:3])
            if len(high_missing) > 3:
                cols += f" and {len(high_missing)-3} others"
            recommendations.append(Recommendation(
                title="Critical Missing Data",
                message=f"Columns '{cols}' have >30% missing values. Consider data cleaning.",
                action="Missing Values",
                priority=1,
                category="quality",
                icon="🚨"
            ))
        elif len(medium_missing) > 0:
            recommendations.append(Recommendation(
                title="Missing Values Detected",
                message=f"{len(medium_missing)} columns have >10% missing values.",
                action="Missing Values",
                priority=2,
                category="quality",
                icon="⚠️"
            ))
            
        return recommendations
    
    def _analyze_duplicates(self, df: pd.DataFrame) -> List[Recommendation]:
        """Analyze duplicate rows and generate recommendations."""
        recommendations = []
        
        try:
            duplicate_count = df.duplicated().sum()
            if duplicate_count > 0:
                percentage = (duplicate_count / len(df)) * 100
                if percentage > 10:
                    priority = 1
                    icon = "🚨"
                    title = "High Duplicate Rate"
                else:
                    priority = 2
                    icon = "🔄"
                    title = "Duplicate Rows Found"
                    
                recommendations.append(Recommendation(
                    title=title,
                    message=f"Found {duplicate_count} duplicate rows ({percentage:.1f}% of data).",
                    action="Duplicate Detection",
                    priority=priority,
                    category="quality",
                    icon=icon
                ))
        except Exception as e:
            # Skip duplicate analysis if it fails (e.g., unhashable types)
            pass
            
        return recommendations
    
    def _analyze_special_characters(self, df: pd.DataFrame) -> List[Recommendation]:
        """Analyze special characters in text columns."""
        recommendations = []
        
        text_columns = df.select_dtypes(include=['object']).columns
        if len(text_columns) > 0:
            # Check for common special character patterns
            has_special_chars = False
            for col in text_columns[:5]:  # Check first 5 text columns
                sample = df[col].dropna().astype(str).head(100)
                if any(any(ord(char) > 127 for char in str(val)) for val in sample):
                    has_special_chars = True
                    break
            
            if has_special_chars:
                recommendations.append(Recommendation(
                    title="Special Characters Detected",
                    message="Text columns contain non-ASCII characters. Check encoding quality.",
                    action="Special Character Analysis",
                    priority=2,
                    category="quality",
                    icon="📝"
                ))
                
        return recommendations
    
    def _analyze_placeholders(self, df: pd.DataFrame) -> List[Recommendation]:
        """Analyze potential placeholder values."""
        recommendations = []
        
        # Common placeholder patterns
        placeholder_patterns = ['n/a', 'na', 'null', 'none', 'tbd', 'todo', 
                               'xxx', '???', 'unknown', 'missing', 'pending']
        
        text_columns = df.select_dtypes(include=['object']).columns
        placeholder_found = False
        
        for col in text_columns[:5]:  # Check first 5 text columns
            col_values = df[col].dropna().astype(str).str.lower()
            if any(pattern in col_values.values for pattern in placeholder_patterns):
                placeholder_found = True
                break
        
        if placeholder_found:
            recommendations.append(Recommendation(
                title="Placeholder Values Found",
                message="Detected potential placeholder text (N/A, TBD, etc.) in data.",
                action="Placeholder Detection",
                priority=2,
                category="quality",
                icon="🏷️"
            ))
            
        return recommendations
    
    def _analyze_performance(self, df: pd.DataFrame) -> List[Recommendation]:
        """Analyze dataset size and performance considerations."""
        recommendations = []
        
        rows, cols = df.shape
        
        # Large dataset recommendations
        if rows > 100000:
            recommendations.append(Recommendation(
                title="Large Dataset Detected",
                message=f"Dataset has {rows:,} rows. Consider using data sampling for faster analysis.",
                action="Data Preview",
                priority=3,
                category="performance",
                icon="⚡"
            ))
        
        # Wide dataset recommendations  
        if cols > 50:
            recommendations.append(Recommendation(
                title="Many Columns Detected",
                message=f"Dataset has {cols} columns. Focus on key columns first.",
                action="Data Preview",
                priority=3,
                category="performance",
                icon="📊"
            ))
            
        return recommendations


# Create a global instance for the application to use
recommendation_engine = RecommendationEngine()
