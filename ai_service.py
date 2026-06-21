import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def clean_and_normalize(text):
    text = text.lower().strip()
    char_map = {
        'अ': 'a', 'आ': 'a', 'इ': 'i', 'ई': 'i', 'उ': 'u', 'ऊ': 'u', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'n',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'n',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
        'ा': 'a', 'ि': 'i', 'ी': 'i', 'ु': 'u', 'ू': 'u', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
        'ं': 'n', '्': '', 'ः': 'h'
    }
    res = []
    for char in text:
        res.append(char_map.get(char, char))
    return "".join(res)

def edit_dist(s1, s2):
    if len(s1) < len(s2):
        return edit_dist(s2, s1)
    if not s2:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def get_gemini_api_keys():
    """Retrieve all configured Gemini API keys from the environment for rotation pool"""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    keys_str = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    for i in range(2, 6):
        k = os.environ.get(f"GEMINI_API_KEY_{i}")
        if k and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    return keys

def is_name_match(part, word):
    part = "".join(c for c in part if c.isalnum())
    word = "".join(c for c in word if c.isalnum())
    if not part or not word:
        return False
    if part == word:
        return True
    if len(part) >= 3 and len(word) >= 3:
        if part in word or word in part:
            return True
    p_stripped = part.rstrip('aeiou')
    w_stripped = word.rstrip('aeiou')
    if p_stripped == w_stripped:
        return True
    if len(p_stripped) >= 3 and len(w_stripped) >= 3:
        if edit_dist(p_stripped, w_stripped) <= 1:
            return True
    return False


# Generative AI client is configured dynamically in parse_command using environment variables.


def get_system_prompt(lang_name):
    return f"""You are a smart billing assistant for Khata — a shop management app for Indian merchants. 
Your goal is to extract structured data from natural language to help navigate the application, query sales insights, create invoices, add customers, or add products.

CRITICAL REQUIREMENT:
- You must speak, write, and respond ONLY in {lang_name}. 
- The value for 'response_text' in your JSON output MUST be written entirely in {lang_name}. This is true regardless of the language of the user input. Even if the user inputs text in English, you MUST formulate the 'response_text' in {lang_name}.
- Translate all insights, navigation confirmations, product/customer details, and follow-up questions into fluent, natural-sounding {lang_name}.
- STRICTION ON HINGLISH: If the requested language is 'English', 'US English', or 'Indian English', you MUST respond in clean, grammatically correct English. DO NOT mix Hindi or Hinglish words (such as 'aapka', 'khata', 'bhai', 'udhaar', 'antar', 'beech', 'kya', 'hai', 'se', 'aane', 'wale', 'paisa', etc.) in your English responses. Use standard English terms (e.g., 'your ledger', 'your account', 'your revenue', 'customer balance').

You will be provided with:
1. User Input (Natural Language)
2. Current Database Context (List of existing products, customers, and business statistics)
3. Conversation History (if any)

About Scanned Bills (is_bill = True):
- Scanned bills with `[Acc. in Metrics: False]` are excluded/private records (just saved to not lose them). They should be IGNORED in any business expense summaries or total financial calculations unless the user explicitly asks about their "private" or "unaccommodated" bills.
- Only bills with `[Acc. in Metrics: True]` should be counted as business expenses/outflows in financial stats.

Output JSON format:
{{
    "intent": "create_invoice" | "add_customer" | "add_product" | "navigation" | "business_insights" | "business_education" | "db_operation" | "unknown",
    "data": {{ ... }},
    "missing_info": "Question to ask user if info is missing (written in {lang_name})" or null,
    "response_text": "Natural language response to speak back to the user (MUST be written in {lang_name})"
}}

For 'db_operation':
- Triggered when the user wants to update or delete existing records (e.g., delete an invoice, mark an invoice as paid/pending/cancelled, update the due date of an invoice, delete a product, or delete a customer).
- "data" should contain:
    - "operation": one of "update_invoice_status" | "update_invoice_due_date" | "delete_invoice" | "delete_product" | "delete_customer"
    - "invoice_no": string (e.g. "INV-001" or "INV-2025-001") or null if not applicable
    - "status": string (e.g. "paid", "pending", "cancelled", "overdue") or null
    - "due_date": string (YYYY-MM-DD format) or null
    - "product_name": string (the exact or similar product name to delete) or null
    - "customer_name": string (the exact or similar customer name to delete) or null
- "response_text": A clear, natural language confirmation in {lang_name} indicating what data will be updated or deleted.

For 'navigation':
- Triggered when the user asks to go to a specific page or dashboard.
- "data" should contain:
    - "target": one of "dashboard" | "products" | "invoices" | "customers" | "analytics" | "create_invoice" | "logout"
- "response_text": a brief confirmation message in {lang_name} (e.g. confirming you are redirecting them).

For 'business_insights':
- Triggered when the user asks for sales metrics, revenue, customers overview, best selling products, stock health, or a general business report.
- "data" should be empty: {{}}
- "response_text": A encouraging, modern business insight summary based on the provided "Business Stats" context, written entirely in {lang_name}. Speak about their revenue, top-selling products, and any low-stock warnings dynamically. Keep it engaging.

For 'business_education':
- Triggered when the user asks general business terms, definitions (like B2B, B2C, GST, profit, margins, credit), consumer rights, or business school questions.
- "data": {{}}
- "response_text": A simple, friendly, easy-to-understand explanation of the term or question, written entirely in {lang_name}. Keep it concise and tailor it for small shopkeepers/merchants.

For 'create_invoice':
- "data" should contain:
    - "customer_name": string (matched from context or new) or null if not yet provided
    - "is_new_customer": boolean
    - "items": list of objects {{ "product_name": string, "quantity": int, "is_new_product": boolean, "price": float (if mentioned), "discount": float (default 0) }}
    - "tax": float (default 0)
    - "due_date": string (YYYY-MM-DD) or null
- Product Validation Warning: If any product specified in the invoice is not present in the 'Seller Products Catalog' (e.g. a new item like Milk), you MUST explicitly state this in the 'response_text' (e.g., "I noticed Milk is not in your product inventory, but I've added it to the invoice. Should we proceed?").

For 'add_customer':
- "data": {{ "name": string or null, "email": string or null, "phone": string, "address": string }}

For 'add_product':
- "data": {{ "name": string or null, "price": float (default 0 if not mentioned), "stock": int (default 0 if not mentioned), "description": string (optional) }}

MULTI-TURN CONVERSATION & CONTEXT RETENTION RULES:
1. Analyze the Conversation History to understand the current context. If the user previously expressed an intent (e.g. creating an invoice, adding a product) and you asked a follow-up question (e.g. "Who is this invoice for?"), and the user's current input is the answer (e.g. "kushagra"), you MUST:
   - Keep the same 'intent' (e.g. 'create_invoice').
   - Retain the previously extracted items/details from the history and merge them with the new user input.
   - Set 'customer_name' (or product name, etc.) to the value they just provided.
2. If the conversation history shows that you just compiled an invoice (or showed its preview/details) and the user wants to adjust it (e.g., "add monitor", "remove keyboard", "change quantity of mouse to 2", "add 2 more", "uh just a minute add monitor"), you MUST:
   - Keep the intent as 'create_invoice' to modify the current invoice.
   - Do NOT treat this as 'add_product' (which is for adding a product to the catalog) or 'add_customer'.
   - Update the items list accordingly (fuzzy match the product, update quantity or append the new item).
3. If ANY required information is missing, you must set 'missing_info' to a direct question asking for the missing detail (e.g. "Who is this invoice for?" or "What items are they buying?"), and set 'response_text' to the same question.
4. If all required information is gathered, 'missing_info' MUST be set to null.

DATABASE QUERIES & NATURAL LANGUAGE LEDGER QUESTIONS:
- If the user asks database-related questions about their invoices, customer balances, payments, or purchase history (e.g. "How much is Anjali Patel pending?", "When did Arjun Mehta pay?", "What did Sneha buy?", "Show me Anjali's ledger"), you MUST:
  - Analyze the provided 'Invoices History' context carefully.
  - Formulate a friendly, natural, and accurate answer detailing dates, amounts, and items.
  - Set the 'intent' to 'unknown' and put your answer in the 'response_text' field.

Rules:
- Fuzzy match product names from the provided context. If a product sounds similar to an existing one, use the existing name.
- If a product is definitely new (not in context), mark is_new_product=true.
- If customer is not in context, mark is_new_customer=true.
- Be helpful and concise in 'response_text' (written in {lang_name}).
- If the user's intent is unclear and cannot be inferred from history, set intent to 'unknown' and ask for clarification in 'response_text' (written in {lang_name}).
- ALWAYS return valid JSON.
"""

def get_context_str(context):
    # Formatted Products List
    products_list = []
    for p in context.get('products', []):
        products_list.append(f"- {p['name']} (Price: INR {p['price']}, Stock: {p.get('stock', 0)})")
    products_str = "\n".join(products_list)
    
    # Formatted Customers List
    customers_list = []
    for c in context.get('customers', []):
        customers_list.append(f"- {c['name']} (Email: {c.get('email', 'N/A')}, Phone: {c.get('phone', 'N/A')})")
    customers_str = "\n".join(customers_list)
    
    # Formatted Invoices List
    invoices_list = []
    for inv in context.get('invoices', []):
        items_str = ", ".join([f"{item['name']} x{item['quantity']}" for item in inv['items']])
        type_str = "Bill" if inv.get('is_bill') else "Invoice"
        acc_str = ""
        if inv.get('is_bill'):
            acc_str = f" [Acc. in Metrics: {inv.get('accommodate_in_metrics', True)}]"
        invoices_list.append(
            f"- {type_str} {inv['invoice_no']} for {inv['customer_name']}: INR {inv['amount']:.2f} ({inv['status']}) on {inv['date']} (due: {inv['due_date']}){acc_str} - Items: [{items_str}]"
        )
    invoices_str = "\n".join(invoices_list)
    
    context_str = (
        f"Seller Products Catalog:\n{products_str}\n\n"
        f"Seller Customers:\n{customers_str}\n\n"
        f"Invoices History:\n{invoices_str}"
    )
    
    if 'stats' in context:
        s = context['stats']
        low_stock_str = ', '.join([f"{p['name']} (stock: {p['stock']})" for p in s.get('low_stock', [])]) or "None"
        top_selling_str = ', '.join([f"{p['name']} (sold: {p['quantity']})" for p in s.get('top_selling', [])]) or "None"
        stats_str = (
            f"\n\nBusiness Stats:\n"
            f"- Total Revenue: INR {s.get('revenue', 0.0):.2f}\n"
            f"- Total Invoices: {s.get('invoices_count', 0)}\n"
            f"- Total Customers: {s.get('customers_count', 0)}\n"
            f"- Total Products: {s.get('products_count', 0)}\n"
            f"- Low Stock Alerts: {low_stock_str}\n"
            f"- Top Selling Products: {top_selling_str}"
        )
        context_str += stats_str
    return context_str

def get_translated_nav(target, lang_code):
    names_en = {
        'dashboard': 'Dashboard',
        'products': 'Products Inventory',
        'invoices': 'Invoices List',
        'customers': 'Customer Management',
        'analytics': 'Analytics Center',
        'create_invoice': 'Invoice Creator',
        'logout': 'Secure Logout'
    }
    
    translations = {
        'hi-IN': {
            'prefix': 'ज़रूर, आपको {target} पेज पर ले जा रहा हूँ।',
            'dashboard': 'डैशबोर्ड',
            'products': 'उत्पाद सूची',
            'invoices': 'इनवॉइस सूची',
            'customers': 'ग्राहक प्रबंधन',
            'analytics': 'एनालिटिक्स केंद्र',
            'create_invoice': 'इनवॉइस निर्माता',
            'logout': 'लॉगआउट'
        },
        'fr-FR': {
            'prefix': 'Bien sûr, je vous emmène à la page {target}.',
            'dashboard': 'Tableau de bord',
            'products': 'Inventaire des produits',
            'invoices': 'Liste des factures',
            'customers': 'Gestion des clients',
            'analytics': 'Centre d\'analyse',
            'create_invoice': 'Créateur de facture',
            'logout': 'Déconnexion'
        },
        'es-ES': {
            'prefix': 'Por supuesto, te llevo a la página de {target}.',
            'dashboard': 'Tablero',
            'products': 'Inventario de productos',
            'invoices': 'Lista de facturas',
            'customers': 'Gestión de clientes',
            'analytics': 'Centro de análisis',
            'create_invoice': 'Creador de facturas',
            'logout': 'Cerrar sesión'
        },
        'de-DE': {
            'prefix': 'Sicher, ich bringe Sie zur Seite {target}.',
            'dashboard': 'Dashboard',
            'products': 'Produktinventar',
            'invoices': 'Rechnungsliste',
            'customers': 'Kundenverwaltung',
            'analytics': 'Analysenzentrum',
            'create_invoice': 'Rechnungsersteller',
            'logout': 'Abmelden'
        },
        'ja-JP': {
            'prefix': 'かしこまりました。{target}ページへ移動します。',
            'dashboard': 'ダッシュボード',
            'products': '商品一覧',
            'invoices': '請求書一覧',
            'customers': '顧客管理',
            'analytics': '分析センター',
            'create_invoice': '請求書作成',
            'logout': 'ログアウト'
        }
    }
    
    target_name = names_en.get(target, target.replace('_', ' ').title())
    if lang_code in translations:
        lang_trans = translations[lang_code]
        t_target = lang_trans.get(target, target_name)
        prefix_template = lang_trans.get('prefix', 'Sure, taking you to the {target} page.')
        return prefix_template.format(target=t_target)
        
    return f"Sure, taking you to the {target_name} page."

def get_translated_insights(stats, lang_code):
    revenue = stats.get('revenue', 0.0)
    invoices_count = stats.get('invoices_count', 0)
    customers_count = stats.get('customers_count', 0)
    products_count = stats.get('products_count', 0)
    low_stock = stats.get('low_stock', [])
    top_selling = stats.get('top_selling', [])
    
    # Format top selling products
    top_selling_parts = []
    for i, p in enumerate(top_selling[:3]):
        name = p['name']
        if i == 0 and not name[0].isupper():
            name = f"the {name}"
        top_selling_parts.append(f"{name} with {p['quantity']} units sold")
    
    if len(top_selling_parts) > 1:
        top_selling_str = ", ".join(top_selling_parts[:-1]) + f", and {top_selling_parts[-1]}"
    elif top_selling_parts:
        top_selling_str = top_selling_parts[0]
    else:
        top_selling_str = "no products"
        
    # Format low stock alerts
    if low_stock:
        p = low_stock[0]
        name = p['name']
        if not name[0].isupper():
            name = f"the {name}"
        low_stock_str = f"You have low stock alerts for {name} with only {p['stock']} units available."
    else:
        low_stock_str = "You have no low stock alerts."
        
    summary_en = f"You have a total of {customers_count} customers and {products_count} products in your inventory. Your top-selling products are {top_selling_str}. {low_stock_str}"
    
    if lang_code == 'hi-IN':
        top_selling_hi = []
        for p in top_selling[:3]:
            top_selling_hi.append(f"{p['name']} ({p['quantity']} बेचे गए)")
        top_selling_str_hi = ", ".join(top_selling_hi)
        low_stock_str_hi = f"{low_stock[0]['name']} के केवल {low_stock[0]['stock']} उपलब्ध हैं" if low_stock else "सभी उत्पाद पर्याप्त मात्रा में उपलब्ध हैं"
        return f"आपके पास कुल {customers_count} ग्राहक और {products_count} उत्पाद हैं। आपके सबसे अधिक बिकने वाले उत्पाद {top_selling_str_hi} हैं। आपके पास {low_stock_str_hi} के लिए कम स्टॉक चेतावनी है।"
        
    return summary_en

def parse_command(user_text, context, history=[], language='en-IN'):
    """
    Parses user text using a configured AI model (Groq or Gemini).
    """
    # Reload environment variables to pick up keys dynamically
    load_dotenv(override=True)
    
    # 1. Deterministic Heuristic Routing for Navigation and Insights
    text_lower = user_text.lower().strip()
    
    # 0. Deterministic Heuristic for Customer Outstanding Balance
    balance_keywords = [
        'balance', 'pending', 'outstanding', 'due', 'how much', 'amount', 
        'paisa', 'paise', 'rupay', 'rupee', 'rupees', 'lene', 'lena', 'dene', 'dena',
        'baki', 'baaki', 'bakaya', 'udhaar', 'udhar', 'hisab', 'hisaab', 'khata',
        'पैसे', 'पैसा', 'रुपये', 'रुपया', 'बाकी', 'बकाया', 'उधार', 'लेने', 'लेना', 'देने', 'देना', 'हिसाब', 'खाता',
        'कितने', 'कितना', 'बैलेंस', 'bailens'
    ]
    norm_text = clean_and_normalize(text_lower)
    is_balance_query = any(clean_and_normalize(keyword) in norm_text for keyword in balance_keywords)
    
    if is_balance_query:
        matched_customer = None
        best_match_len = 0
        words = norm_text.split()
        
        for customer in context.get('customers', []):
            name = customer['name']
            name_lower = name.lower()
            norm_name = clean_and_normalize(name_lower)
            
            # Match full name
            if norm_name in norm_text:
                if len(norm_name) > best_match_len:
                    matched_customer = customer
                    best_match_len = len(norm_name)
            else:
                # Match name parts
                name_parts = norm_name.split()
                for part in name_parts:
                    if len(part) > 2:
                        for word in words:
                            if is_name_match(part, word):
                                if len(part) > best_match_len:
                                    matched_customer = customer
                                    best_match_len = len(part)
                                    
        if matched_customer:
            cust_name = matched_customer['name']
            pending_sum = 0.0
            paid_sum = 0.0
            pending_count = 0
            paid_count = 0
            
            for inv in context.get('invoices', []):
                if inv['customer_name'].lower() == cust_name.lower():
                    status = inv['status'].lower()
                    amount = float(inv['amount'])
                    if status in ['pending', 'overdue']:
                        pending_sum += amount
                        pending_count += 1
                    elif status == 'paid':
                        paid_sum += amount
                        paid_count += 1
                        
            is_paid = 'paid' in text_lower or 'payment' in text_lower
            
            # Determine if Hindi/Hinglish query
            is_hindi = (language == 'hi-IN') or any(clean_and_normalize(word) in norm_text for word in ['paise', 'paisa', 'lene', 'lena', 'dene', 'dena', 'baki', 'baaki', 'bakaya', 'udhaar', 'udhar', 'hisab', 'hisaab', 'khata', 'पैसे', 'पैसा', 'रुपये', 'रुपया', 'बाकी', 'बकाया', 'उधार', 'लेने', 'लेना', 'देने', 'देना', 'हिसाब', 'खाता'])
            
            if is_hindi:
                if is_paid:
                    reply = f"{cust_name} के कुल {paid_count} भुगतान किए गए इनवॉइस हैं जिनका कुल मूल्य INR {paid_sum:.2f} है।"
                else:
                    if pending_count == 0:
                        reply = f"{cust_name} का कोई बकाया इनवॉइस नहीं है। वर्तमान बैलेंस INR 0.00 है।"
                    else:
                        reply = f"{cust_name} के कुल {pending_count} बकाया इनवॉइस हैं जिनका लंबित मूल्य INR {pending_sum:.2f} है।"
            elif language == 'fr-FR':
                if is_paid:
                    reply = f"{cust_name} a un total de {paid_count} factures payées avec un montant payé de INR {paid_sum:.2f}."
                else:
                    if pending_count == 0:
                        reply = f"{cust_name} n'a pas de factures impayées. Le solde actuel est de INR 0.00."
                    else:
                        reply = f"{cust_name} a un total de {pending_count} factures impayées avec un montant en attente de INR {pending_sum:.2f}."
            elif language == 'es-ES':
                if is_paid:
                    reply = f"{cust_name} tiene un total de {paid_count} facturas pagadas con un monto pagado de INR {paid_sum:.2f}."
                else:
                    if pending_count == 0:
                        reply = f"{cust_name} no tiene facturas pendientes. El saldo actual es de INR 0.00."
                    else:
                        reply = f"{cust_name} tiene un total de {pending_count} facturas pendientes con un monto pendiente de INR {pending_sum:.2f}."
            elif language == 'de-DE':
                if is_paid:
                    reply = f"{cust_name} hat insgesamt {paid_count} bezahlte Rechnungen mit einem bezahlten Betrag von INR {paid_sum:.2f}."
                else:
                    if pending_count == 0:
                        reply = f"{cust_name} hat keine ausstehenden Rechnungen. Der aktuelle Kontostand beträgt INR 0.00."
                    else:
                        reply = f"{cust_name} hat insgesamt {pending_count} ausstehende Rechnungen mit einem ausstehenden Betrag von INR {pending_sum:.2f}."
            elif language == 'ja-JP':
                if is_paid:
                    reply = f"{cust_name}は合計{paid_count}件の支払い済み請求書があり、支払い額は INR {paid_sum:.2f} です。"
                else:
                    if pending_count == 0:
                        reply = f"{cust_name}の未払いの請求書はありません。現在の残高は INR 0.00 です。"
                    else:
                        reply = f"{cust_name}は合計{pending_count}件の未払い請求書があり、保留額は INR {pending_sum:.2f} です。"
            else:
                if is_paid:
                    if paid_count == 1:
                        reply = f"{cust_name} has a total of 1 paid invoice with a total paid amount of INR {paid_sum:.2f}."
                    else:
                        reply = f"{cust_name} has a total of {paid_count} paid invoices with a total paid amount of INR {paid_sum:.2f}."
                else:
                    if pending_count == 0:
                        reply = f"{cust_name} has no outstanding invoices. Current balance is INR 0.00."
                    elif pending_count == 1:
                        reply = f"{cust_name} has a total of 1 outstanding invoice with a pending amount of INR {pending_sum:.2f}."
                    else:
                        reply = f"{cust_name} has a total of {pending_count} outstanding invoices with a pending amount of INR {pending_sum:.2f}."
                    
            return {
                "intent": "unknown",
                "data": {},
                "missing_info": None,
                "response_text": reply
            }


    
    # A. Navigation keywords mapping (multi-lingual)
    nav_targets = {
        'dashboard': [
            'go to dashboard', 'show dashboard', 'open dashboard', 'view dashboard', 'dashboard page',
            'डैशबोर्ड पर जाओ', 'डैशबोर्ड दिखाओ',
            'tableau de bord', 'aller au tableau de bord',
            'tablero', 'ir al tablero',
            'gehe zu dashboard',
            'ダッシュボードへ移動'
        ],
        'products': [
            'go to products', 'show products', 'open products', 'view products', 'products inventory', 'products page',
            'उत्पाद पर जाओ', 'उत्पाद सूची', 'उत्पाद दिखाओ', 'उत्पाद दिखाएं', 'प्रोडक्ट्स पर जाएं',
            'aller aux produits', 'inventaire des produits',
            'ir a productos', 'inventario de productos',
            'gehe zu produkten', 'produktinventar',
            '商品一覧', '商品一覧へ移動'
        ],
        'invoices': [
            'go to invoices', 'show invoices', 'open invoices', 'view invoices', 'invoices list', 'invoices page',
            'इनवॉइस पर जाओ', 'इनवॉइस सूची', 'इनवॉइस दिखाओ', 'इनवॉइस दिखाएं',
            'aller aux factures', 'liste des factures',
            'ir a facturas', 'lista de facturas',
            'gehe zu rechnungen', 'rechnungsliste',
            '請求書一覧', '請求書一覧へ移動'
        ],
        'customers': [
            'go to customers', 'show customers', 'open customers', 'view customers', 'customer list', 'customers page',
            'ग्राहक पर जाओ', 'ग्राहक सूची', 'ग्राहक दिखाओ', 'ग्राहक दिखाएं', 'ग्राहक प्रबंधन',
            'aller aux clients', 'gestion des clients',
            'ir a clientes', 'gestión de clientes',
            'gehe zu kunden', 'kundenverwaltung',
            '顧客管理', '顧客管理へ移動'
        ],
        'analytics': [
            'go to analytics', 'show analytics', 'open analytics', 'view analytics', 'analytics page',
            'एनालिटिक्स पर जाओ', 'एनालिटिक्स दिखाओ', 'एनालिटिक्स दिखाएं', 'एनालिटिक्स केंद्र',
            'afficher les analyses', 'centre d\'analyse',
            'mostrar análisis', 'centro de análisis',
            'analysen anzeigen', 'analysenzentrum',
            '分析を見せて', '分析センター'
        ],
        'create_invoice': [
            'create invoice', 'create an invoice', 'new invoice',
            'इनवॉइस बनाएं', 'नया इनवॉइस', 'इनवॉइस बनाओ',
            'créer une facture', 'créer facture', 'nouvelle facture',
            'crear factura', 'nueva factura',
            'rechnung erstellen', 'neue rechnung',
            '請求書作成', '新しい請求書'
        ],
        'logout': [
            'log out', 'logout', 'sign out',
            'लॉगआउट', 'लॉग आउट', 'साइन आउट',
            'déconnexion', 'se déconnecter',
            'cerrar sesión', 'desconectarse',
            'abmelden', 'ausloggen',
            'ログアウト', 'サインアウト'
        ]
    }
    
    for target, phrases in nav_targets.items():
        if any(phrase in text_lower for phrase in phrases):
            # If it is a create_invoice request but contains additional details,
            # fall through to the LLM to parse items and customer details.
            if target == 'create_invoice':
                if len(text_lower.split()) > 3:
                    continue
                    
            return {
                "intent": "navigation",
                "data": {"target": target},
                "missing_info": None,
                "response_text": get_translated_nav(target, language)
            }
            
    # B. Business Insights keywords mapping (multi-lingual)
    insight_phrases = [
        'insights', 'insight', 'business insights', 'show insights', 'view insights', 'sales metrics', 'business stats', 'view statistics', 'how is business', 'how is the business doing',
        'व्यापार रिपोर्ट', 'व्यापार रिपोर्ट दिखाएं', 'बिजनेस कैसा है', 'बिजनेस कैसा चल रहा है',
        'perspectives commerciales', 'comment vont les affaires', 'rapport d\'activité',
        'información comercial', 'cómo va el negocio', 'estado del negocio',
        'geschäftszahlen', 'wie läuft das geschäft', 'geschäftseinblicke',
        'ビジネス分析', '業績はどう', 'ビジネスレポート'
    ]
    if any(phrase in text_lower for phrase in insight_phrases):
        s = context.get('stats', {})
        summary = get_translated_insights(s, language)
        return {
            "intent": "business_insights",
            "data": {},
            "missing_info": None,
            "response_text": summary
        }

    # C. Basic Greetings mapping (multi-lingual)
    greeting_words = [
        'hi', 'hello', 'hey', 'namaste', 'hola', 'bonjour', 'hallo', 'konnichiwa', 
        'good morning', 'good afternoon', 'good evening', 'hi there', 'hello there',
        'नमस्ते', 'हेलो', 'हाय'
    ]
    if text_lower in greeting_words or any(text_lower == word for word in greeting_words):
        greetings = {
            'hi-IN': 'नमस्ते! मैं आपकी इनवॉइस बनाने या व्यावसायिक जानकारी प्राप्त करने में कैसे सहायता कर सकता हूँ?',
            'fr-FR': "Bonjour ! Comment puis-je vous aider avec vos factures ou vos perspectives commerciales aujourd'hui ?",
            'es-ES': "¡Hola! ¿Cómo puedo ayudarte con tus facturas o estadísticas comerciales hoy?",
            'de-DE': "Hallo! Wie kann ich Ihnen heute bei Ihren Rechnungen oder Geschäftsdaten helfen?",
            'ja-JP': "こんにちは！本日は請求書の作成やビジネス分析など、どのようなお手伝いをいたしましょうか？"
        }
        reply = greetings.get(language, "Hi! How can I help you with your invoices or business stats today?")
        return {
            "intent": "unknown",
            "data": {},
            "missing_info": None,
            "response_text": reply
        }

    # 2. Call Generative AI fallback for natural language commands with bidirectional error failover
    groq_api_key = os.environ.get("GROQ_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    # 1. Try Groq first if available
    if groq_api_key and groq_api_key.strip():
        try:
            print("Attempting command parsing via Groq...")
            return parse_command_groq(user_text, context, history, groq_api_key.strip(), language)
        except Exception as groq_err:
            print(f"Groq parse failed: {groq_err}. Falling back to Gemini...")
            if gemini_api_key and gemini_api_key.strip():
                try:
                    return parse_command_gemini(user_text, context, history, gemini_api_key.strip(), language)
                except Exception as gemini_err:
                    return {
                        "intent": "unknown",
                        "data": {},
                        "missing_info": None,
                        "response_text": f"⚠️ Both Groq and Gemini services failed. (Groq: {groq_err}, Gemini: {gemini_err})"
                    }
            else:
                return {
                    "intent": "unknown",
                    "data": {},
                    "missing_info": None,
                    "response_text": f"🛑 Groq failed and no Gemini API key is configured. Error: {groq_err}"
                }
                
    # 2. Try Gemini fallback if Groq not configured
    if gemini_api_key and gemini_api_key.strip():
        try:
            print("Attempting command parsing via Gemini...")
            return parse_command_gemini(user_text, context, history, gemini_api_key.strip(), language)
        except Exception as gemini_err:
            print(f"Gemini parse failed: {gemini_err}. Trying Groq as fallback if configured...")
            if groq_api_key and groq_api_key.strip():
                try:
                    return parse_command_groq(user_text, context, history, groq_api_key.strip(), language)
                except Exception as groq_err:
                    return {
                        "intent": "unknown",
                        "data": {},
                        "missing_info": None,
                        "response_text": f"⚠️ Both Gemini and Groq services failed. (Gemini: {gemini_err}, Groq: {groq_err})"
                    }
            else:
                return {
                    "intent": "unknown",
                    "data": {},
                    "missing_info": None,
                    "response_text": f"🛑 Gemini failed and no Groq API key is configured. Error: {gemini_err}"
                }

    return {
        "intent": "unknown",
        "data": {},
        "missing_info": None,
        "response_text": "⚠️ No AI API key found. Please configure `GROQ_API_KEY` or `GEMINI_API_KEY` in your `.env` file."
    }

def parse_command_groq(user_text, context, history, api_key, language):
    import requests
    
    context_str = get_context_str(context)
    
    lang_names = {
        'en-IN': 'English',
        'en-US': 'English',
        'hi-IN': 'Hindi',
        'fr-FR': 'French',
        'es-ES': 'Spanish',
        'de-DE': 'German',
        'ja-JP': 'Japanese'
    }
    lang_name = lang_names.get(language, 'English')
    system_prompt = get_system_prompt(lang_name)
    
    # Format conversation messages for Groq API
    messages = [{"role": "system", "content": system_prompt}]
    clean_history = history
    if history and (history[-1].get('content') == user_text or history[-1].get('text') == user_text):
        clean_history = history[:-1]
        
    if clean_history:
        for msg in clean_history:
            role = "user" if msg.get('role') == 'user' or msg.get('sender') == 'user' else "assistant"
            messages.append({"role": role, "content": msg.get('content') or msg.get('text', '')})
    
    messages.append({"role": "user", "content": f"Context:\n{context_str}\n\nUser Input:\n{user_text}"})
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    
    # Call Groq serverless completions API
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=10
    )
    
    if response.status_code == 429 or response.status_code == 401 or response.status_code != 200:
        # Try a quick fallback model in Groq first
        payload["model"] = "llama-3.3-70b-versatile"
        fallback_resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        if fallback_resp.status_code == 200:
            response = fallback_resp
            
    if response.status_code != 200:
        raise Exception(f"Groq API Error {response.status_code}: {response.text}")
        
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    return json.loads(content)

def parse_command_gemini(user_text, context, history, api_key, language):
    # Setup key pool with primary key first
    keys = [api_key] if api_key else []
    for k in get_gemini_api_keys():
        if k not in keys:
            keys.append(k)
            
    if not keys:
        raise Exception("No Gemini API key configured.")
        
    context_str = get_context_str(context)
    
    clean_history = history
    if history and (history[-1].get('content') == user_text or history[-1].get('text') == user_text):
        clean_history = history[:-1]
        
    history_str = ""
    if clean_history:
        history_str = "Conversation History:\n"
        for msg in clean_history:
            role = "User" if msg.get('role') == 'user' or msg.get('sender') == 'user' else "Assistant"
            history_str += f"{role}: {msg.get('content') or msg.get('text', '')}\n"
    
    lang_names = {
        'en-IN': 'English',
        'en-US': 'English',
        'hi-IN': 'Hindi',
        'fr-FR': 'French',
        'es-ES': 'Spanish',
        'de-DE': 'German',
        'ja-JP': 'Japanese'
    }
    lang_name = lang_names.get(language, 'English')
    system_prompt = get_system_prompt(lang_name)
    prompt = f"{system_prompt}\n\nContext:\n{context_str}\n\n{history_str}\nUser Input:\n{user_text}\n\nResponse (JSON):"
    
    response = None
    last_err = None
    
    # Try gemini-2.0-flash on all keys first
    for key in keys:
        try:
            print(f"Calling Gemini 2.0 Flash (Assistant) with key: {key[:8]}...")
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            break
        except Exception as err:
            last_err = err
            print(f"Key {key[:8]} failed for Assistant gemini-2.0-flash: {err}")
            
    # Try gemini-1.5-flash fallback on all keys if 2.0-flash failed
    if not response:
        print("Assistant gemini-2.0-flash failed on all keys. Attempting gemini-1.5-flash fallback across keys...")
        for key in keys:
            try:
                print(f"Calling Gemini 1.5 Flash (Assistant) with key: {key[:8]}...")
                genai.configure(api_key=key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                break
            except Exception as err:
                last_err = err
                print(f"Key {key[:8]} failed for Assistant gemini-1.5-flash: {err}")
                
    if not response:
        raise last_err
    
    content = response.text
    if content.startswith("```json"):
        content = content[7:-3]
    elif content.startswith("```"):
        content = content[3:-3]
        
    return json.loads(content)
