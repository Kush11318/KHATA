# KHATA - Invoice Management & AI Assistant

A smart, modern billing, inventory, and customer management system built for small-to-medium businesses. Powered by Flask, SQLAlchemy, Google Gemini, and Cloudinary, this application features an interactive dashboard, role-based portals, and a state-of-the-art AI Billing Assistant supporting natural language voice/text commands, scanned bill OCR digitization, canvas markup annotations, and persistent notes.

* **Live Demo**: [https://invoice-system-ai.onrender.com](https://invoice-system-ai.onrender.com)
* **Developer Portfolio**: [github.com/Kush11318](https://github.com/Kush11318)

---

## Live Case Study: AI Chatbot Capabilities

This repository showcases the core engine of the **KHATA AI Assistant**, demonstrating:
- **Natural Language Parsing**: High-accuracy information extraction from free-form conversations.
- **Workflow Automation**: Dynamic database updates (inventory levels, customer records) triggered via chat.
- **Document Intelligence**: Interactive canvas viewer for scanned bills, including drawing tools, image manipulation, and database-stored notes.
- **System Stability**: Connection pool recycling and unicode-safe stream routing.

---

## Architecture Overview

```mermaid
graph TD
    User([Sellers & Customers]) <-->|HTTP Requests| Flask[Flask Server: app.py]
    Flask <-->|SQLAlchemy ORM| DB[(SQLite / MySQL Database)]
    Flask <-->|Google GenAI SDK| Gemini[Gemini 1.5 Flash AI Engine]
    Flask <-->|Cloudinary API| Cloudinary[Cloudinary Cloud Storage]
    Flask <-->|Pillow Pipeline| PIL[Pillow Processing Engine]
```

### System Architecture Flow
* **Routing & Middleware**: The Flask backend serves role-based routes with login/session middleware protection.
* **SQLAlchemy Database Layer**: Models include relationships between Sellers, Customers, Products, Invoices, and Activity Logs.
* **External Integrations**: Gemini 1.5 Flash processes structured invoice schemas and natural language queries, while Cloudinary stores compressed digitized documents.

---

## Technical Deep-Dive & Code Map

### 1. Backend Application Controller (app.py)
* **Location**: `app.py`
* **Core Responsibilities**:
  * **Routing & Access Control**: Implements `@login_required` and `@role_required` decorators to segregate seller, customer, and administrator views.
  * **Database Lifecycle**: Manages database migrations dynamically using SQLAlchemy (`migrate_database()`), checking for missing columns like `is_bill`, `accommodate_in_metrics`, `is_synced`, `s_logo`, `s_theme`, and `bill_buyer_name`.
  * **File Upload & Compression**: Handles scanned bill uploads under `/seller/invoices/upload_bill`. Coordinates file validation, runs Pillow-based resizing/compression to reduce payload size by 90% (capped at 1600px width/height, compressed to quality=75 JPEG), and manages Cloudinary API transactions with a secure local filesystem fallback path (`static/uploads/bills/`).
  * **Ajax & Data Syncing**: Contains REST endpoints to dynamically update scanned bill notes (`/seller/invoices/update_notes/<id>`) and toggle business metrics inclusion (`/seller/bills/<id>/toggle_accommodation`).

### 2. Google Gemini AI Engine (ai_service.py)
* **Location**: `ai_service.py`
* **Core Responsibilities**:
  * **Structured Bill Digitization (OCR)**: Uses `google.generativeai` structures (`genai.GenerativeModel`) to analyze images/PDFs. Uses a strict JSON schema representation (`BillData`) to extract total amount, vendor name, invoice date, line items (with quantities, units, and unit prices), and the buyer's name.
  * **Natural Language Processing**: Translates Hinglish commands, matches voice intents (e.g., "Add product...", "Bill for..."), and handles Hindi balance checks (e.g., *"mujhe shyam se kitne paise lene hai"*) using Levenshtein fuzzy string-matching routines.
  * **Database Seeding & Automation**: Automatically maps extracted OCR data to SQL columns, creates missing items in the Products catalog, and tracks stock depletion.

### 3. Database Schemas (models.py)
* **Location**: `models.py`
* **Core Model Relationships**:
```mermaid
erDiagram
    SELLER ||--o{ CUSTOMER : "manages"
    SELLER ||--o{ PRODUCT : "owns"
    SELLER ||--o{ INVOICE : "issues"
    CUSTOMER ||--o{ INVOICE : "receives"
    INVOICE ||--|{ INVOICE_ITEM : "contains"
    SELLER ||--o{ ACTIVITY : "triggers"
```
* **Key Fields**:
  * **Invoice**: `is_bill` (boolean to isolate expenses from sales), `original_file` (URL to digital copy), `accommodate_in_metrics` (boolean to filter dashboard KPIs), and `notes` (persisted text annotations).
  * **Customer / Product**: `is_synced` flags to control whether AI-digitized entities should populate the primary sales ledger or remain isolated.

### 4. Interactive Drawing Canvas & Document Viewer
* **Location**: `templates/base.html` (Modal & Canvas logic)
* **Core Interactivity**:
  * **Drawing Canvas Markup**: A HTML5 `<canvas>` handles user annotations. Click-and-drag actions capture coordinate lines mapped from viewport client scales (`clientX`, `clientY`) directly into drawing coordinates (`offsetX`, `offsetY`).
  * **Pan, Zoom, and Rotate Tools**: Implements coordinate space transformations. Zoom scales the viewer up to 500% dynamically, and rotation pivots the image canvas in 90-degree increments.
  * **Export & Download**: Extracts the annotated canvas as a base64 Data URL and bundles it into a JPEG file trigger, letting users download their marked-up documents instantly.
  * **Namespace Protection**: All viewer JavaScript is encapsulated in an Immediately Invoked Function Expression (IIFE) to completely prevent naming collisions with global components (like the dashboard background shader canvas).

### 5. Client Voice & Dashboard Router (ai_assistant.js)
* **Location**: `static/js/ai_assistant.js`
* **Core Responsibilities**:
  * **Voice Processing**: Uses `webkitSpeechRecognition` to capture live user audio streams, process them into transcripts, and feed them to the `/seller/assistant/message` handler.
  * **TTS (Text-to-Speech)**: Synthesizes responses using `speechSynthesis` voices.
  * **Navigation Engine**: Executes action directives sent by the backend (e.g., navigation redirects, showing insights panels, auto-filling invoice fields).

---

## Detailed Data Flows

### Scanned Bills Digitization Flow

```mermaid
sequenceDiagram
    autonumber
    actor Seller
    participant UI as Browser (invoices.html)
    participant Server as Flask Server (app.py)
    participant PIL as Pillow Engine
    participant Cloud as Cloudinary / Local
    participant AI as Gemini 1.5 Flash
    participant DB as SQLite / MySQL Database

    Seller->>UI: Select Bill file & Click Upload
    UI->>Server: POST /seller/invoices/upload_bill
    Server->>PIL: Compress & Resize image to max 1600px
    PIL-->>Server: Return compressed image bytes (JPEG, Q=75)
    Server->>Cloud: Upload compressed file
    Cloud-->>Server: Return Cloud URL / Local path
    Server->>AI: Send image bytes for OCR analysis (schema: BillData)
    AI-->>Server: Return structured JSON (Items, Vendor, Total)
    Server->>DB: Check & Register Vendor and Products
    Server->>DB: Insert Invoice record (is_bill=True, is_synced=True)
    DB-->>Server: Confirm SQL Commit
    Server-->>UI: Redirect to invoices?tab=bills with success flash
```

---

## Installation & Local Execution

### Prerequisites
* Python 3.10+
* SQLite (default) or MySQL
* Google Gemini API Key
* Cloudinary Account (optional, falls back to local storage automatically)

### 1. Setup Environment
```bash
# Clone the repository
git clone https://github.com/Kush11318/Invoice-Management-System-with-AI-Assistant.git
cd Invoice-Management-System-with-AI-Assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # MacOS/Linux
# Or on Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Flask Setup
SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Cloudinary Setup (Optional - omit to use local storage)
CLOUDINARY_URL=cloudinary://your_api_key:your_api_secret@your_cloud_name
```

### 3. Initialize Database
Create tables, run migrations, and seed initial demo data:
```bash
python seed_db.py
```

### 4. Run Flask Server
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

---

## Credentials

* **Seller Account** (Full access to AI Assistant, Dashboard, and Invoices):
  * **Email**: `demo@invoiceai.com`
  * **Password**: `demo123`
* **Admin Account**:
  * **Email**: `admin@admin.com`
  * **Password**: `admin`
* **Customer Account**:
  * **Email**: `customer@example.com`
  * **Password**: `password`

---

## Feature Comparison Matrix

| Feature | Sales Invoices | Scanned Bills (Expenses) |
| :--- | :--- | :--- |
| **Tab Placement** | Invoices Tab (Sales) | Invoices Tab (Scanned Bills) |
| **Creation Method** | Manual Wizard / AI Voice | OCR Image Upload & Auto-Digitization |
| **Business Direction** | Income (Generates Revenue) | Expense (Tracks Purchases) |
| **Stock Modification** | Depletes Product Inventory | Increments Product Inventory |
| **Accommodation** | Always included in metrics | Optional (Toggleable switch on each bill) |
| **File Annotations** | N/A | Supported (Interactive Drawing Canvas) |
| **Persistent Notes** | N/A | Supported (Sidebar Editor & DB Storage) |
