# 🚀 Invoice Management System with AI Billing Assistant

A smart, modern billing, inventory, and customer management system built for small-to-medium businesses. Powered by **Flask**, **SQLAlchemy**, and **Google Gemini**, this application features an interactive dashboard, PDF invoice generation, role-based portals, and a state-of-the-art **AI Billing Assistant** supporting natural language voice and text commands.

---

## ✨ Key Features

### 🤖 Smart AI Billing Assistant
* **Natural Language Processing**: Control the billing dashboard, navigate the portal, or create entities using plain English or Hinglish commands.
* **Voice-Activated Commands**: Full speech-to-text integration using the Web Speech API (`webkitSpeechRecognition`), enabling hands-free operation.
* **Auto-Intent Mapping**:
  * **Interactive Billing**: Speak a command like *"Bill for Alice: 1 Wireless Mouse and 2 Mechanical Keyboards"* to instantly parse products, match stocks, and construct a draft invoice preview.
  * **Inventory Automation**: Create products instantly (e.g. *"Add product USB Hub price 1200 stock 25"*).
  * **Customer Registration**: Save customers (e.g. *"Add customer John Doe email john@example.com"*).
  * **Real-time Business Insights**: Speak queries like *"How is business?"* to fetch instant KPI stats (Revenue, Low Stock, Total Invoices) inside a visual chart-card.
* **Voice Feedback**: Responsive audio synthesis feedback using the Web Speech Synthesis API.
* **Premium Glassmorphic Interface**: Sleek translucent panels with slide-up transitions, customized purple scrollbars, micro-animations, and mobile viewport responsive layout.

### 📊 Comprehensive Business Management
* **Role-Based Access**: Specialized portals and control privileges for **Admins**, **Sellers**, and **Customers**.
* **Billing Center**: Generate dynamic invoices, track unpaid balances, and compute sales taxes.
* **PDF Exporter**: Single-click PDF rendering using ReportLab, ready for downloads or direct printing.
* **Inventory Management**: Fully interactive catalog editor featuring real-time stock-depletion tracking and low-stock indicators.
* **Customer Analytics**: Detailed order logs and visual statistics tracking total lifetime value and buyer behavior.

---

## 🛠️ Tech Stack

* **Backend**: Python 3, Flask, Flask-SQLAlchemy (Relational ORM)
* **Database**: SQLite (default / development) or MySQL (scalable production)
* **AI Engine**: Google Gemini API via `google-generativeai` SDK
* **Frontend**: HTML5, Vanilla CSS3 (Custom Grid Layouts & Animations), JavaScript ES6 (DOM Manipulation, Web Speech API)
* **PDF Engine**: ReportLab

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Kush11318/Invoice-Management-System-with-AI-Assistant.git
cd Invoice-Management-System-with-AI-Assistant
```

### 2. Create a Virtual Environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the example environment template and configure your API Keys:
```bash
cp .env.example .env
```
Open the `.env` file and insert your **Google Gemini API Key**:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(By default, the application runs on SQLite. If you prefer MySQL, you can uncomment and edit the database connection variables inside `.env`)*

### 5. Initialize and Seed the Database
Run the helper script to create the schema and seed sample products, customers, invoices, and activity history:
```bash
python seed_db.py
```

### 6. Run the Application
```bash
python app.py
```
Open your web browser and navigate to `http://127.0.0.1:5000`.

---

## 🔑 Demo Credentials

* **Seller Account** (Has access to AI Assistant & Dashboard):
  * **Email**: `seller@example.com`
  * **Password**: `seller`
* **Customer Account**:
  * **Email**: `customer@example.com`
  * **Password**: `password`

---

## 🗣️ AI Assistant Voice & Text Commands Guide

Launch the AI Assistant modal using the glowing purple robotic orb in the bottom-right corner of the seller screen. Speak or type these phrases:

| Action Category | Example Phrase | Output |
| :--- | :--- | :--- |
| **Business Insights** | *"Show business insights"* / *"How is business?"* | Displays interactive metrics grid, top sellers chart, and warehouse stock alerts |
| **Voice Navigation** | *"Go to products"* / *"Show analytics"* | Triggers a fullscreen transition overlay and redirects to the requested route |
| **Add Products** | *"Add product Gaming Mouse price 1500 stock 30"* | Generates a preview card; confirms and appends Gaming Mouse to your inventory |
| **Add Customers** | *"Add customer Robert email robert@example.com"* | Formulates a preview; registers Robert into the customer directory |
| **Create Invoices** | *"Bill for Alice Smith: 2 mechanical keyboards and 1 wireless mouse"* | Auto-fills items, computes tax, and redirects to the invoice creation wizard |

---

## 📂 Project Structure

```
├── static/
│   ├── css/
│   │   ├── style.css           # Core dashboard styling
│   │   └── ai_assistant.css    # Premium glassmorphic AI panel styles
│   └── js/
│       ├── main.js             # General app interactivity
│       └── ai_assistant.js     # Speech recognition and AI action handlers
├── templates/                  # Jinja2 HTML templates
├── ai_service.py               # Google Gemini API connector & prompt parsing logic
├── app.py                      # Main Flask application and server routing
├── config.py                   # Environment and database configuration loader
├── database.py                 # SQLite/MySQL engine setups
├── models.py                   # SQLAlchemy ORM schemas (Sellers, Products, Invoices...)
├── queries.py                  # Helper queries for statistics & analytics
├── seed_db.py                  # Database recreator and mock data seeder
└── requirements.txt            # Python packages manifest
```
