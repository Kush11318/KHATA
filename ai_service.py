import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Generative AI client is configured dynamically in parse_command using environment variables.


def get_system_prompt(lang_name):
    return f"""You are a smart billing assistant for an Invoice Management System. 
Your goal is to extract structured data from natural language to help navigate the application, query sales insights, create invoices, add customers, or add products.

CRITICAL REQUIREMENT:
- You must speak, write, and respond ONLY in {lang_name}. 
- The value for 'response_text' in your JSON output MUST be written entirely in {lang_name}. This is true regardless of the language of the user input. Even if the user inputs text in English, you MUST formulate the 'response_text' in {lang_name}.
- Translate all insights, navigation confirmations, product/customer details, and follow-up questions into fluent, natural-sounding {lang_name}.

You will be provided with:
1. User Input (Natural Language)
2. Current Database Context (List of existing products, customers, and business statistics)

Output JSON format:
{{
    "intent": "create_invoice" | "add_customer" | "add_product" | "navigation" | "business_insights" | "unknown",
    "data": {{ ... }},
    "missing_info": "Question to ask user if info is missing (written in {lang_name})",
    "response_text": "Natural language response to speak back to the user (MUST be written in {lang_name})"
}}

For 'navigation':
- Triggered when the user asks to go to a specific page or dashboard.
- "data" should contain:
    - "target": one of "dashboard" | "products" | "invoices" | "customers" | "analytics" | "create_invoice" | "logout"
- "response_text": a brief confirmation message in {lang_name} (e.g. confirming you are redirecting them).

For 'business_insights':
- Triggered when the user asks for sales metrics, revenue, customers overview, best selling products, stock health, or a general business report.
- "data" should be empty: {{}}
- "response_text": A encouraging, modern business insight summary based on the provided "Business Stats" context, written entirely in {lang_name}. Speak about their revenue, top-selling products, and any low-stock warnings dynamically. Keep it engaging.

For 'create_invoice':
- "data" should contain:
    - "customer_name": string (matched from context or new)
    - "is_new_customer": boolean
    - "items": list of objects {{ "product_name": string, "quantity": int, "is_new_product": boolean, "price": float (if mentioned), "discount": float (default 0) }}
    - "tax": float (default 0)
    - "due_date": string (YYYY-MM-DD) or null

For 'add_customer':
- "data": {{ "name": string, "email": string, "phone": string, "address": string }}

For 'add_product':
- "data": {{ "name": string (REQUIRED - must extract from user input), "price": float (default 0 if not mentioned), "stock": int (default 0 if not mentioned), "description": string (optional) }}
- IMPORTANT: Always extract the product name from the user's input. If the user says "add product Milk", the name should be "Milk". If they say "add product called Laptop", the name should be "Laptop".

Rules:
- Fuzzy match product names from the provided context. If a product sounds similar to an existing one, use the existing name.
- If a product is definitely new (not in context), mark is_new_product=true.
- If customer is not in context, mark is_new_customer=true.
- Be helpful and concise in 'response_text' (written in {lang_name}).
- If the user's intent is unclear, set intent to 'unknown' and ask for clarification in 'response_text' (written in {lang_name}).
- ALWAYS return valid JSON.
"""

def get_context_str(context):
    product_names = [p['name'] for p in context.get('products', [])]
    customer_names = [c['name'] for c in context.get('customers', [])]
    context_str = f"Existing Products: {', '.join(product_names)}\nExisting Customers: {', '.join(customer_names)}"
    
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
    
    best_seller = top_selling[0]['name'] if top_selling else None
    low_names = [p['name'] for p in low_stock[:2]] if low_stock else []
    
    if lang_code == 'hi-IN':
        summary = f"यहाँ आपकी वास्तविक समय की व्यापार रिपोर्ट है। आपने {invoices_count} इनवॉइस में कुल ₹{revenue:.2f} का राजस्व अर्जित किया है। "
        summary += f"आपके पास {customers_count} ग्राहकों की सेवा करने वाले {products_count} सक्रिय उत्पाद हैं। "
        if best_seller:
            summary += f"आपका सबसे अधिक बिकने वाला उत्पाद {best_seller} है। "
        if low_stock:
            summary += f"आपके पास {len(low_stock)} उत्पाद हैं जिनका स्टॉक कम है, जिसमें {', '.join(low_names)} शामिल हैं। आपको जल्द ही स्टॉक अपडेट करना चाहिए!"
        else:
            summary += "आपके सभी उत्पाद पर्याप्त मात्रा में उपलब्ध हैं!"
        return summary
        
    elif lang_code == 'fr-FR':
        summary = f"Voici votre rapport d'activité en temps réel. Vous avez généré un chiffre d'affaires total de INR {revenue:.2f} sur {invoices_count} factures. "
        summary += f"Votre inventaire contient {products_count} produits actifs pour {customers_count} clients enregistrés. "
        if best_seller:
            summary += f"Votre produit le plus vendu est {best_seller}. "
        if low_stock:
            summary += f"Vous avez {len(low_stock)} articles en rupture de stock, notamment {', '.join(low_names)}. Vous devriez vous réapprovisionner bientôt !"
        else:
            summary += "Les niveaux de stock de vos produits sont excellents !"
        return summary

    elif lang_code == 'es-ES':
        summary = f"Aquí está su informe comercial en tiempo real. Ha obtenido un ingreso total de INR {revenue:.2f} a través de {invoices_count} facturas. "
        summary += f"Su inventario cuenta con {products_count} productos activos para {customers_count} clientes registrados. "
        if best_seller:
            summary += f"Su producto más vendido es {best_seller}. "
        if low_stock:
            summary += f"Tiene {len(low_stock)} artículos con stock bajo, incluyendo {', '.join(low_names)}. ¡Debería reabastecerse pronto!"
        else:
            summary += "¡Los niveles de stock de sus productos están en perfecto estado!"
        return summary

    elif lang_code == 'de-DE':
        summary = f"Hier ist Ihr Echtzeit-Geschäftsbericht. Sie haben einen Gesamtumsatz von INR {revenue:.2f} aus {invoices_count} Rechnungen erzielt. "
        summary += f"Ihr Inventar umfasst {products_count} aktive Produkte für {customers_count} registrierte Kunden. "
        if best_seller:
            summary += f"Ihr meistverkauftes Produkt ist {best_seller}. "
        if low_stock:
            summary += f"Sie haben {len(low_stock)} Artikel mit geringem Lagerbestand, darunter {', '.join(low_names)}. Sie sollten bald nachbestellen!"
        else:
            summary += "Ihre Lagerbestände sind im grünen Bereich!"
        return summary

    elif lang_code == 'ja-JP':
        summary = f"リアルタイムのビジネスレポートです。現在までに{invoices_count}件の請求書から、合計 {revenue:.2f} インドルピーの売上を達成しています。 "
        summary += f"登録顧客数は{customers_count}名、取り扱い商品数は{products_count}点です。 "
        if best_seller:
            summary += f"最も売れている商品は{best_seller}です。 "
        if low_stock:
            summary += f"在庫数が残り少ない商品が{len(low_stock)}点（{', '.join(low_names)}など）あります。お早めに補充してください。"
        else:
            summary += "商品の在庫状況はすべて良好です！"
        return summary
        
    summary = f"Here is your real-time business health report. You have earned a total revenue of INR {revenue:.2f} across {invoices_count} invoices. "
    summary += f"Your inventory has {products_count} active products serving {customers_count} registered customers. "
    if best_seller:
        summary += f"Your top-performing product is {best_seller}. "
    if low_stock:
        summary += f"You have {len(low_stock)} items running low in stock, including {', '.join(low_names)}. You should restock soon!"
    else:
        summary += "Your product stock levels are fully healthy!"
    return summary

def parse_command(user_text, context, history=[], language='en-IN'):
    """
    Parses user text using a configured AI model (Groq or Gemini).
    """
    # Reload environment variables to pick up keys dynamically
    load_dotenv(override=True)
    
    # 1. Deterministic Heuristic Routing for Navigation and Insights
    text_lower = user_text.lower().strip()
    
    # A. Navigation keywords mapping (multi-lingual)
    nav_targets = {
        'dashboard': [
            'go to dashboard', 'show dashboard', 'open dashboard', 'view dashboard', 'dashboard page',
            'डैशबोर्ड', 'डैशबोर्ड पर जाओ', 'डैशबोर्ड दिखाओ',
            'tableau de bord', 'aller au tableau de bord',
            'tablero', 'ir al tablero',
            'dashboard', 'gehe zu dashboard',
            'ダッシュボード', 'ダッシュボードへ移動'
        ],
        'products': [
            'go to products', 'show products', 'open products', 'view products', 'products inventory', 'products page',
            'उत्पाद', 'उत्पाद पर जाओ', 'उत्पाद सूची', 'उत्पाद दिखाओ', 'उत्पाद दिखाएं', 'प्रोडक्ट्स पर जाएं',
            'produits', 'aller aux produits', 'inventaire des produits',
            'productos', 'ir a productos', 'inventario de productos',
            'produkte', 'gehe zu produkten', 'produktinventar',
            '商品一覧', '商品一覧へ移動', '商品'
        ],
        'invoices': [
            'go to invoices', 'show invoices', 'open invoices', 'view invoices', 'invoices list', 'invoices page',
            'इनवॉइस', 'इनवॉइस पर जाओ', 'इनवॉइस सूची', 'इनवॉइस दिखाओ', 'इनवॉइस दिखाएं',
            'factures', 'aller aux factures', 'liste des factures',
            'facturas', 'ir a facturas', 'lista de facturas',
            'rechnungen', 'gehe zu rechnungen', 'rechnungsliste',
            '請求書一覧', '請求書一覧へ移動', '請求書'
        ],
        'customers': [
            'go to customers', 'show customers', 'open customers', 'view customers', 'customer list', 'customers page',
            'ग्राहक', 'ग्राहक पर जाओ', 'ग्राहक सूची', 'ग्राहक दिखाओ', 'ग्राहक दिखाएं', 'ग्राहक प्रबंधन',
            'clients', 'aller aux clients', 'gestion des clients',
            'clientes', 'ir a clientes', 'gestión de clientes',
            'kunden', 'gehe zu kunden', 'kundenverwaltung',
            '顧客管理', '顧客管理へ移動', '顧客'
        ],
        'analytics': [
            'go to analytics', 'show analytics', 'open analytics', 'view analytics', 'analytics page',
            'एनालिटिक्स', 'एनालिटिक्स पर जाओ', 'एनालिटिक्स दिखाओ', 'एनालिटिक्स दिखाएं', 'एनालिटिक्स केंद्र',
            'analyses', 'afficher les analyses', 'centre d\'analyse',
            'análisis', 'mostrar análisis', 'centro de análisis',
            'analysen', 'analysen anzeigen', 'analysenzentrum',
            '分析', '分析を見せて', '分析センター'
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
            return {
                "intent": "navigation",
                "data": {"target": target},
                "missing_info": None,
                "response_text": get_translated_nav(target, language)
            }
            
    # B. Business Insights keywords mapping (multi-lingual)
    insight_phrases = [
        'business insights', 'show insights', 'view insights', 'sales metrics', 'business stats', 'view statistics', 'how is business', 'how is the business doing', 'insights',
        'व्यापार रिपोर्ट', 'व्यापार रिपोर्ट दिखाएं', 'बिजनेस कैसा है', 'बिजनेस कैसा चल रहा है', 'इनसाइट्स',
        'perspectives commerciales', 'comment vont les affaires', 'rapport d\'activité', 'statistiques',
        'información comercial', 'cómo va el negocio', 'estado del negocio', 'estadísticas',
        'geschäftszahlen', 'wie läuft das geschäft', 'geschäftseinblicke', 'statistiken',
        'ビジネス分析', '業績はどう', 'ビジネスレポート', 'インサイト'
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

    # 2. Call Generative AI fallback for natural language commands
    groq_api_key = os.environ.get("GROQ_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    # 1. Prioritize Groq if config is present (generous free quotas)
    if groq_api_key and groq_api_key.strip():
        return parse_command_groq(user_text, context, history, groq_api_key.strip(), language)
        
    # 2. Fallback to Gemini
    if gemini_api_key and gemini_api_key.strip():
        return parse_command_gemini(user_text, context, history, gemini_api_key.strip(), language)
        
    return {
        "intent": "unknown",
        "data": {},
        "missing_info": None,
        "response_text": "⚠️ No AI API key found. Please configure `GROQ_API_KEY` or `GEMINI_API_KEY` in your `.env` file."
    }

def parse_command_groq(user_text, context, history, api_key, language):
    try:
        import requests
        
        context_str = get_context_str(context)
        
        lang_names = {
            'en-IN': 'Indian English',
            'en-US': 'US English',
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
        if history:
            for msg in history:
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
        
        if response.status_code == 401:
            return {
                "intent": "unknown",
                "data": {},
                "missing_info": None,
                "response_text": "🛑 **Groq Authorization Failed**: Please verify that your `GROQ_API_KEY` in the `.env` file is valid."
            }
            
        if response.status_code == 429:
            return {
                "intent": "unknown",
                "data": {},
                "missing_info": None,
                "response_text": "🛑 **Groq Rate Limit Exceeded (429)**: Free rate limits reached. Please try again in a moment."
            }
            
        if response.status_code != 200:
            # Fallback to llama-3.3-70b-versatile
            payload["model"] = "llama-3.3-70b-versatile"
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            
        if response.status_code != 200:
            return {
                "intent": "unknown",
                "data": {},
                "missing_info": None,
                "response_text": f"🛑 **Groq API Error ({response.status_code})**: {response.text}"
            }
            
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)
        
    except Exception as e:
        import traceback
        with open('error.log', 'w') as f:
            f.write(traceback.format_exc())
        return {
            "intent": "unknown",
            "data": {},
            "missing_info": None,
            "response_text": f"Sorry, Groq encountered an error: {str(e)}"
        }

def parse_command_gemini(user_text, context, history, api_key, language):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        context_str = get_context_str(context)
        
        history_str = ""
        if history:
            history_str = "Conversation History:\n"
            for msg in history:
                role = "User" if msg.get('role') == 'user' or msg.get('sender') == 'user' else "Assistant"
                history_str += f"{role}: {msg.get('content') or msg.get('text', '')}\n"
        
        lang_names = {
            'en-IN': 'Indian English',
            'en-US': 'US English',
            'hi-IN': 'Hindi',
            'fr-FR': 'French',
            'es-ES': 'Spanish',
            'de-DE': 'German',
            'ja-JP': 'Japanese'
        }
        lang_name = lang_names.get(language, 'English')
        system_prompt = get_system_prompt(lang_name)
        prompt = f"{system_prompt}\n\nContext:\n{context_str}\n\n{history_str}\nUser Input:\n{user_text}\n\nResponse (JSON):"
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        content = response.text
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        return json.loads(content)
        
    except Exception as e:
        import traceback
        with open('error.log', 'w') as f:
            f.write(traceback.format_exc())
        print(f"AI Service Error: {e}")
        
        error_name = type(e).__name__
        if "ResourceExhausted" in error_name or "429" in str(e):
            return {
                "intent": "unknown",
                "data": {},
                "missing_info": None,
                "response_text": "🛑 **Gemini API Quota Exceeded (429)**: You have exceeded your Gemini free quota. Please wait 1–2 minutes, or configure a `GROQ_API_KEY` in your `.env` file for higher free limits."
            }
            
        return {
            "intent": "unknown",
            "data": {},
            "missing_info": None,
            "response_text": f"Sorry, Gemini encountered an error: {str(e)}"
        }
