import spacy
from spacy.matcher import Matcher
import re

# Load the small English model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Model 'en_core_web_sm' not found. Please run:\npython -m spacy download en_core_web_sm")
    exit()

# Initialize the Matcher
matcher = Matcher(nlp.vocab)

# --- Define our "Intents" ---
add_stock_pattern = [[{"LOWER": {"IN": ["add", "added", "received", "got", "insert"]}}], [{"LOWER": "put"}, {"LOWER": "in"}]]
check_stock_pattern = [[{"LOWER": {"IN": ["how", "many"]}}], [{"LOWER": "check"}, {"LOWER": "stock"}], [{"LOWER": "what's"}, {"LOWER": "the"}, {"LOWER": "count"}], [{"LOWER": "do"}, {"LOWER": "we"}, {"LOWER": "have"}]]
set_alert_pattern = [[{"LOWER": "alert"}], [{"LOWER": "notify"}, {"LOWER": "me"}], [{"LOWER": "set"}, {"LOWER": "reorder"}]]
report_pattern = [[{"LOWER": "report"}], [{"LOWER": "generate"}, {"LOWER": "list"}], [{"LOWER": "low"}, {"LOWER": "stock"}]]
sell_stock_pattern = [[{"LOWER": {"IN": ["sell", "sold", "remove", "bought"]}}]]
cancel_pattern = [[{"LOWER": {"IN": ["cancel", "stop", "nevermind", "forget", "quit"]}}]] # New cancel intent

# Add patterns to the matcher
matcher.add("ADD_STOCK", add_stock_pattern)
matcher.add("CHECK_STOCK", check_stock_pattern)
matcher.add("SET_ALERT", set_alert_pattern)
matcher.add("GET_REPORT", report_pattern)
matcher.add("SELL_STOCK", sell_stock_pattern)
matcher.add("CANCEL", cancel_pattern)


def parse_command(text: str) -> dict:
    """
    Parses raw text to find an intent and associated entities.
    NEW: Now also finds DATE entities.
    """
    doc = nlp(text)
    matches = matcher(doc)
    
    intent = None
    if matches:
        intent = nlp.vocab.strings[matches[0][0]]

    # --- Find "Entities" (Product, Quantity, Expiry Date) ---
    quantity = None
    product = None
    expiry_date = None # New variable

    # Find the first number (CARDINAL)
    for ent in doc.ents:
        if ent.label_ == "CARDINAL" and quantity is None:
            try:
                quantity = int(ent.text)
            except ValueError:
                pass 
        
        # --- NEW: Find DATE entity ---
        # spaCy finds dates like "today", "next Tuesday", "2025-12-31"
        if ent.label_ == "DATE" and expiry_date is None:
            # For simplicity, we'll try to parse a YYYY-MM-DD format
            # A more robust parser would be needed for "next Tuesday"
            match = re.search(r'(\d{4}-\d{2}-\d{2})', ent.text)
            if match:
                expiry_date = match.group(1)
            else:
                # Try to parse simple dates like "20 12 2025"
                nums = re.findall(r'\d+', ent.text)
                if len(nums) == 3: # e.g., [20, 12, 2025]
                    # This is a guess, needs better parsing
                    expiry_date = f"{nums[2]}-{nums[1]}-{nums[0]}"

    # Find the main product (Noun)
    for token in doc:
        if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop and token.text.lower() != 'date':
            product = token.text.lower()
            if quantity is not None:
                break
                
    if product is None and intent in ["ADD_STOCK", "SELL_STOCK"]:
         nouns = [token.text.lower() for token in doc if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop]
         if nouns:
             product = nouns[-1] 

    # --- NEW: Check text *just* for a date if no other intent found ---
    if intent is None and expiry_date is None:
        match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        if match:
            expiry_date = match.group(1)

    return {
        "intent": intent,
        "product": product,
        "quantity": quantity,
        "expiry_date": expiry_date # New return value
    }

# --- Quick Test ---
if __name__ == "__main__":
    print("--- Check Mate NLU Test (with Dates) ---")
    
    test_commands = [
        "add 20 apples expiring 2025-12-31",
        "how many apples",
        "sell 5 milk",
        "2025-10-20" # Test just a date
    ]
    
    for cmd in test_commands:
        parsed = parse_command(cmd)
        print(f"Text: '{cmd}'")
        print(f"Parsed: {parsed}\n")