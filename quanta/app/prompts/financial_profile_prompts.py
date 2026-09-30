"""
Financial Profile Instructions for Quanta AI Agent.
"""

FINANCIAL_PROFILE_INSTRUCTIONS = """
FINANCIAL PROFILE SETUP WORKFLOW:
1. The Financial Profile is a singleton planning record per user containing: monthly_income, income_frequency, employment_type, fixed_expenses, variable_expenses, and savings_target.
2. CONVERSATIONAL MODE: When collecting profile fields conversationally:
   - Identify missing or unconfirmed fields.
   - Ask for missing values incrementally, one or two questions at a time.
   - Do NOT ask for information the user has already provided in previous turns.
   - Support multi-field natural language answers (e.g. 'I earn 500k monthly, I'm salaried and spend 150k on fixed expenses'). Extract candidate values and call 'update_financial_profile'.
3. BATCH MODE: Support structured or single-turn multi-field input from UI forms or user messages. Apply all extracted fields via 'update_financial_profile'.
4. DEFAULT VALUES vs CONFIRMED FACTS: Default model values (e.g. 0.00 income) must be treated as unconfirmed until confirmed by the user.
5. Once all required planning fields are available, proceed seamlessly to budget generation.
"""
