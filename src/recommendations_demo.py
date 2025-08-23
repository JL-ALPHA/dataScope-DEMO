"""
Dynamic Recommendations Demo for DataScope
Shows examples of intelligent recommendations for different dataset scenarios
"""

from recommendation_engine import RecommendationEngine, Recommendation
import pandas as pd
import numpy as np

def create_sample_datasets():
    """Create sample datasets to demonstrate recommendations."""
    
    # Dataset 1: High missing values
    messy_data = {
        'customer_id': range(1, 1001),
        'name': ['Customer ' + str(i) if i % 3 != 0 else None for i in range(1, 1001)],
        'email': ['user' + str(i) + '@email.com' if i % 4 != 0 else None for i in range(1, 1001)],
        'age': [25 + (i % 50) if i % 5 != 0 else None for i in range(1, 1001)],
        'purchase_amount': [100.0 + (i * 1.5) if i % 7 != 0 else None for i in range(1, 1001)]
    }
    messy_df = pd.DataFrame(messy_data)
    
    # Dataset 2: With duplicates
    clean_data = {
        'product_id': [1, 2, 3, 4, 5, 3, 4, 6, 7, 8],  # Duplicates: 3, 4
        'product_name': ['Widget A', 'Widget B', 'Widget C', 'Widget D', 'Widget E', 
                        'Widget C', 'Widget D', 'Widget F', 'Widget G', 'Widget H'],
        'price': [10.99, 15.50, 8.75, 22.00, 13.25, 8.75, 22.00, 18.99, 12.50, 16.75],
        'category': ['Electronics', 'Home', 'Electronics', 'Books', 'Home',
                    'Electronics', 'Books', 'Sports', 'Home', 'Books']
    }
    duplicate_df = pd.DataFrame(clean_data)
    
    # Dataset 3: Large dataset
    large_data = {
        'id': range(1, 150001),
        'value': np.random.randn(150000),
        'category': np.random.choice(['A', 'B', 'C', 'D'], 150000),
        'timestamp': pd.date_range('2020-01-01', periods=150000, freq='1min')
    }
    large_df = pd.DataFrame(large_data)
    
    # Dataset 4: Text data with special characters
    text_data = {
        'id': range(1, 101),
        'description': ['Product #' + str(i) + ' with @special chars & symbols!' for i in range(1, 101)],
        'notes': ['Note: Item ' + str(i) + ' has été tested (100% success)' for i in range(1, 101)],
        'tags': ['tag1,tag2,tag3' for _ in range(100)]
    }
    text_df = pd.DataFrame(text_data)
    
    return {
        'messy_dataset.csv': messy_df,
        'products_with_duplicates.csv': duplicate_df,
        'large_dataset.csv': large_df,
        'text_analysis_data.csv': text_df
    }

def demo_recommendations():
    """Demonstrate the recommendation engine with different datasets."""
    
    engine = RecommendationEngine()
    datasets = create_sample_datasets()
    
    print("=" * 80)
    print("🤖 DATASCOPE DYNAMIC RECOMMENDATIONS DEMO")
    print("=" * 80)
    
    for filename, df in datasets.items():
        print(f"\n📊 ANALYZING: {filename}")
        print(f"   Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
        print("-" * 60)
        
        # Generate recommendations
        recommendations = engine.analyze_dataset(df, filename)
        
        if recommendations:
            print("💡 SMART RECOMMENDATIONS:")
            print()
            
            # Group by priority
            high_priority = [r for r in recommendations if r.priority == 1]
            medium_priority = [r for r in recommendations if r.priority == 2]
            low_priority = [r for r in recommendations if r.priority == 3]
            
            if high_priority:
                print("🔥 HIGH PRIORITY:")
                for rec in high_priority:
                    print(f"   {rec}")
                print()
            
            if medium_priority:
                print("📋 RECOMMENDED ACTIONS:")
                for rec in medium_priority:
                    print(f"   {rec}")
                print()
            
            if low_priority:
                print("💡 TIPS & INSIGHTS:")
                for rec in low_priority:
                    print(f"   {rec}")
                print()
        else:
            print("✅ No issues detected - your data looks great!")
        
        print("=" * 60)

def demo_contextual_recommendations():
    """Demonstrate contextual recommendations after analysis."""
    
    engine = RecommendationEngine()
    
    print("\n🔄 CONTEXTUAL RECOMMENDATIONS DEMO")
    print("=" * 60)
    
    # Simulate different analysis scenarios
    scenarios = [
        "Missing Values",
        "Duplicate Detection", 
        "Data Preview",
        "Special Character Analysis"
    ]
    
    for analysis in scenarios:
        print(f"\n📈 After running: {analysis}")
        contextual_recs = engine.get_contextual_recommendations(analysis)
        
        if contextual_recs:
            for rec in contextual_recs:
                print(f"   💡 {rec}")
        else:
            print("   ✅ No additional recommendations")

def show_ui_integration_example():
    """Show how recommendations integrate with the UI."""
    
    print("\n🎨 UI INTEGRATION EXAMPLE")
    print("=" * 60)
    
    example_recommendations = [
        Recommendation(
            title="Critical Missing Data",
            message="Columns 'email', 'age' have >30% missing values. Consider data cleaning.",
            action="Missing Values",
            priority=1,
            category="quality",
            icon="🚨"
        ),
        Recommendation(
            title="Start Here",
            message="Begin with Data Preview to understand your dataset structure and content.",
            action="Data Preview",
            priority=1,
            category="workflow",
            icon="🚀"
        ),
        Recommendation(
            title="Duplicate Rows Found",
            message="Found 2 duplicate rows (20.0% of data).",
            action="Duplicate Detection",
            priority=2,
            category="quality",
            icon="🔄"
        )
    ]
    
    print("🔥 HIGH PRIORITY RECOMMENDATIONS:")
    for rec in [r for r in example_recommendations if r.priority == 1]:
        print(f"   [{rec.icon}] {rec.title}")
        print(f"       {rec.message}")
        print(f"       → Action: Run '{rec.action}' analysis")
        print()
    
    print("📋 SUGGESTED ACTIONS:")
    for rec in [r for r in example_recommendations if r.priority == 2]:
        print(f"   [{rec.icon}] {rec.title}")
        print(f"       {rec.message}")
        print(f"       → Action: Run '{rec.action}' analysis")
        print()

if __name__ == "__main__":
    # Run the demonstration
    demo_recommendations()
    demo_contextual_recommendations()
    show_ui_integration_example()
    
    print("\n🎯 SUMMARY: Dynamic Recommendations Benefits")
    print("=" * 60)
    print("✅ Beginner-friendly: Guides users step-by-step")
    print("✅ Proactive: Detects issues automatically")
    print("✅ Context-aware: Suggests next logical steps")
    print("✅ Time-saving: No need to guess what to analyze")
    print("✅ Educational: Explains why each recommendation matters")
    print("✅ Integrated: One-click execution of recommendations")
    print("\n🚀 Ready to transform DataScope into an intelligent assistant!")
