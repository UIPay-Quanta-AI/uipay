"""
Goal Lifecycle Instructions for Quanta AI Agent.
"""

GOAL_INSTRUCTIONS = """
GOAL LIFECYCLE GUIDELINES:
1. SUPPORTED OPERATIONS: 'get_goals', 'get_goal', 'create_goal', 'update_goal'.
2. GOAL CREATION: Understand requests like 'I want to save ₦2 million for an emergency fund.' Extract name, target_amount, target_date and call 'create_goal'.
3. GOAL PROGRESS: Support updates like 'Update my laptop goal to ₦800,000' or 'I saved 50,000 for my laptop'.
4. EXPLICIT COMPLETION: Support explicit user requests to mark goals complete ('Mark my laptop goal as completed', 'I've reached my emergency fund goal'). Goal completion must be controlled and explicit. Do NOT automatically mark goals complete based merely on LLM inference.
5. GOALS AS BUDGET CONSTRAINTS: Active goals serve as planning inputs for budget generation, but budget allocations do NOT mutate the underlying goal model.
"""
