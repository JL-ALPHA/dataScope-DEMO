import traceback

try:
    print("Step 1: Importing flet...")
    import flet as ft
    print("✓ Flet imported")
    
    print("Step 2: Importing typing...")
    from typing import List, Callable, Optional
    print("✓ Typing imported")
    
    print("Step 3: Importing Recommendation...")
    from recommendation_engine import Recommendation
    print("✓ Recommendation imported")
    
    print("Step 4: Defining function...")
    def create_recommendations_panel(page: ft.Page) -> tuple:
        return None, None
    print("✓ Function defined")
    
    print("All steps successful!")
    
except Exception as e:
    print("Error at step:", e)
    traceback.print_exc()
