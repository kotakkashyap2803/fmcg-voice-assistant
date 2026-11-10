# FMCG Voice Assistant

An AI-powered voice and text assistant that helps FMCG retailers discover products, check prices and promotional schemes, create orders, and review previous interactions.

The prototype is built with Django REST Framework, React, TypeScript, MySQL, and Google Gemini.

## 1. Features

- Retailer authentication using JWT.
- Voice and text-based interaction.
- Product discovery and product variant resolution.
- Product pricing and inventory lookup.
- Promotional scheme discovery and deterministic offer calculation.
- Draft order creation, confirmation, and cancellation.
- Follow-up capture.
- Conversation completion with an automatically generated summary and outcome.
- Past interactions with transcript, summary, and outcome.
- Dashboard and analytics.

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, Django, Django REST Framework |
| Database | MySQL |
| AI | Google Gemini (`google-genai`) |
| Authentication | JWT |
| API communication | Axios |
| Voice input | Browser speech recognition |

## Technical Documentation

For details about the system architecture, technology stack,
application modules, implementation approach, and assumptions,
refer to:

[Technical Approach](docs/TECHNICAL_APPROACH.md)

## 3. Project Structure

```text
Marico/
│
├── README.md
│
├── fmcg-voice-assistant/
│   ├── src/
│   ├── package.json
│   └── ...
│
└── fmcg-voice-assistant-backend/
    ├── apps/
    │   ├── accounts/
    │   ├── analytics/
    │   ├── catalogue/
    │   ├── conversations/
    │   ├── followups/
    │   ├── orders/
    │   ├── retailers/
    │   └── schemes/
    │
    ├── config/
    ├── services/
    │   ├── ai/
    │   └── business/
    ├── manage.py
    ├── requirements.txt
    └── ...
```

## 4. Prerequisites

Install the following before running the application:

- Python 3.13
- Node.js and npm
- MySQL Server
- Google Gemini API key
- Git (if cloning the repository)

A Chromium-based browser such as Google Chrome or Microsoft Edge is recommended for voice input.

## 5. Backend Setup

Open Command Prompt and navigate to the backend directory:

```cmd
cd fmcg-voice-assistant-backend
```

### Create and activate a virtual environment

```cmd
python -m venv venv
venv\Scripts\activate
```

### Install Python dependencies

```cmd
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file in the backend root directory.

Use the following template and replace the placeholder values:

```dotenv
DJANGO_SECRET_KEY=replace-with-a-secure-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=fmcg_voice_assistant
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite

FRONTEND_URL=http://localhost:5173
```

Do not commit `.env` or expose API keys in source control.

### Create the MySQL database

Open MySQL and execute:

```sql
CREATE DATABASE fmcg_voice_assistant
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Ensure the database credentials in `.env` match your local MySQL configuration.

### Run migrations

```cmd
python manage.py migrate
```

### Load demo data

```cmd
python manage.py seed_demo_data
```

This command creates demo retailers, products, variants, inventory records, aliases, and promotional schemes.

It can be run again to update or create the demo records. Existing inventory quantities are preserved.

### Start the backend

```cmd
python manage.py runserver
```

Backend URL:

```text
http://127.0.0.1:8000/
```

API base URL:

```text
http://127.0.0.1:8000/api/v1/
```

## 6. Frontend Setup

Open a second Command Prompt window.

Navigate to the frontend directory:

```cmd
cd fmcg-voice-assistant
```

Install dependencies:

```cmd
npm install
```

The frontend uses the following default API URL:

```text
http://127.0.0.1:8000/api/v1
```

To override it, create a `.env` file in the frontend root:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Start the development server:

```cmd
npm run dev
```

Open the application:

```text
http://localhost:5173/
```

## 7. Demo Login

The seed command creates the following demo account if it does not already exist:

| Field | Value |
|---|---|
| Username | `demo_user` |
| Password | `Demo@12345` |

Use these credentials on the application's login screen.

If the account already exists, the seed command does not reset its password.

## 8. Suggested Demo Walkthrough

The following sequence demonstrates the main business workflow.

### Step 1: Discover products

Try:

- "Show me all available products."
- "What products do you have?"
- "Show me GoldDrop sunflower oil."

### Step 2: Check product pricing

Try:

- "What is the price of GoldDrop sunflower oil?"
- "Show me the 500 ml pack."
- "What is the price of the one litre pack?"

### Step 3: Discover promotional offers

Try:

- "Are there any offers on this product?"
- "What offers are available on GoldDrop?"

### Step 4: Create an order

Try:

- "I want 10 units of the 500 ml pack."
- "Okay, place my order."

Review the draft order and confirm it through the assistant.

For the seeded GoldDrop 500 ml variant:

| Calculation | Amount |
|---|---:|
| Quantity | 10 |
| Unit price | ₹82 |
| Subtotal | ₹820 |
| Scheme discount (5%) | ₹41 |
| Final amount | **₹779** |

### Step 5: Explore other schemes

The demo data also includes:

- Parachute 200 ml: Buy 5, Get 1 Free.
- Livon Hair Serum 100 ml: 10% discount.

### Step 6: Capture a follow-up

Try asking the assistant to arrange a follow-up or to contact you later.

### Step 7: Complete the conversation

End the conversation and review the generated summary and outcome.

### Step 8: Review past interactions

Navigate to Past Interactions to inspect previous conversations, including their summaries, outcomes, and transcripts.

## 9. Important Business Logic

The AI layer is responsible for interpreting natural-language requests and identifying the retailer's intent.

Business-critical calculations are handled by deterministic backend services.

For example:

- Product and variant resolution uses catalogue data.
- Prices come from the database.
- Inventory is checked by the backend.
- Promotional discounts are calculated by the scheme service.
- Order confirmation is handled by the order workflow.

This separation helps prevent the language model from inventing prices, stock quantities, or promotional discounts.

## 10. Current Prototype Scope and Limitations

- Demo retailers, products, inventory, and schemes are seeded sample data.
- Voice recognition depends on browser support and microphone permissions.
- Gemini API access requires a valid API key and network connectivity.
- The application is intended as a local demonstration, not a production deployment.
- Telephony integration and live ERP/distributor integrations are outside the current prototype scope.

## 11. Potential Production Enhancements

- Integrate with live ERP, inventory, and distributor systems.
- Add telephony and WhatsApp integration.
- Introduce role-based access control and audit logging.
- Add background processing, retry handling, and monitoring.
- Deploy using production-grade infrastructure with secure secret management.

---

**Project:** FMCG Voice Assistant
**Purpose:** Demonstrate an AI-assisted retailer ordering and engagement workflow for the FMCG domain.