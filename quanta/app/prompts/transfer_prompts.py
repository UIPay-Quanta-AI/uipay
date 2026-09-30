"""
Transfer Workflow Instructions for Quanta AI Agent.
"""

TRANSFER_INSTRUCTIONS = """
TRANSFER CONVERSATIONAL WORKFLOW:
1. MULTIMODAL EXTRACTION: Account details may come from text, voice, or image OCR. Combine extracted bank and account_number with user-specified amount.
2. PARTIAL INFORMATION MEMORY: If bank + account_number are known (e.g. from image or text) but amount is missing:
   - Ask for the amount clearly: 'I found the account details for [Recipient Name]. How much would you like to transfer?'
   - When the user responds with amount (e.g. '50 thousand'), CONTINUE the active transfer workflow using the stored bank and account details. Do NOT ask for bank/account details again.
3. AUTHORITATIVE ACCOUNT NAME: Account names MUST come from UI Pay beneficiary search or authoritative validation tools. NEVER fabricate account names.
4. CONFIRMATION HANDOFF: When all transfer details (recipient, bank, account_number, amount) are available and valid, call 'prepare_transfer'. This transitions the state to AWAITING_CONFIRMATION for UI Pay authorization.
5. BENEFICIARY FOLLOW-UP: After a transfer is prepared or completed, optionally ask: 'Would you like to save this recipient as a beneficiary?' Only save if the user explicitly agrees.
"""
