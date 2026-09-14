# Dynamic Pricing and Fraud Detection System for E-Commerce Flash Sales

A full-stack web application featuring an **AI Dynamic Pricing Engine** (XGBoost Regressor) with cost-floor constraints, an **AI Real-Time Fraud Defense Shield** (XGBoost Classifier + Explainable Rules), a modern **Customer Storefront**, and an **Admin Command Center** (Stripe/Linear-inspired SaaS UI).

---

## 📑 Table of Contents
1. [Prerequisites](#-prerequisites)
2. [Step-by-Step Setup & Running Guide](#-step-by-step-setup--running-guide)
   - [Step 1: Clone / Open Project](#step-1-open-project-directory)
   - [Step 2: Create & Activate Virtual Environment](#step-2-create--activate-virtual-environment)
   - [Step 3: Install Dependencies](#step-3-install-dependencies)
   - [Step 4: Localize Dataset (Indian E-Commerce)](#step-4-optional-localize-dataset)
   - [Step 5: Import Data into SQLite Database](#step-5-import-data-into-sqlite-database)
   - [Step 6: Train Machine Learning Models](#step-6-train-machine-learning-models)
   - [Step 7: Run Automated Tests](#step-7-run-automated-tests)
   - [Step 8: Start the Web Application](#step-8-start-the-web-application)
3. [Portal URLs & Default Credentials](#-portal-urls--default-credentials)
4. [Architecture & Folder Structure](#-architecture--folder-structure)
5. [Machine Learning Models & Metrics](#-machine-learning-models--metrics)
6. [Demo Scenarios to Try](#-demo-scenarios-to-try)

---

## 🛠️ Prerequisites
- **Python**: Python 3.9 or higher (Python 3.10, 3.11, 3.12, 3.13 supported)
- **pip**: Python package manager
- **Git** (optional, for cloning)

---

## 🚀 Step-by-Step Setup & Running Guide

Follow these commands in order in your terminal / command prompt from the project root:

### Step 1: Open Project Directory
```bash
cd idealab
```

---

### Step 2: Create & Activate Virtual Environment

**On macOS / Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

**On Windows (Command Prompt / PowerShell):**
```cmd
# Create virtual environment
python -m venv venv

# Activate (Command Prompt)
venv\Scripts\activate

# Or Activate (PowerShell)
.\venv\Scripts\Activate.ps1
```

---

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

*(Packages installed include: `Flask`, `Flask-SQLAlchemy`, `Flask-Login`, `SQLAlchemy`, `xgboost`, `scikit-learn`, `pandas`, `numpy`, `joblib`)*

---

### Step 4: Localize Dataset (Indian Customers & Products)
```bash
python data/localize_indian_dataset.py
```
This formats the 5 raw CSVs with Indian customer names, authentic products (Smartphones, boAt Earphones, Smart TVs, Levi's Jeans, Kurtis, Books, etc.), Indian competitor pricing (Flipkart, Amazon India, Meesho), and realistic INR prices.

---

### Step 5: Import Data into SQLite Database
```bash
python data/import_data.py
```
- Creates SQLite database at `instance/ecommerce.db`.
- Loads all 5 tables (`products`, `customers`, `orders`, `fraud_labels`, `competitor_prices`).
- Seeds default Admin account (`admin@idealab.com`) and sample customer account (`customer@idealab.com`).
- Performs automated **Foreign Key Referential Integrity Checks** (confirms 0 orphaned rows).

---

### Step 6: Train Machine Learning Models
Train both AI models offline and generate serialized model artifacts in `ml/saved_models/`:

```bash
# 1. Train Fraud Detection Classifier (XGBoost)
python ml/train_fraud_model.py

# 2. Train Dynamic Pricing Regressor (XGBoost)
python ml/train_pricing_model.py

# 3. Output consolidated evaluation report
python ml/evaluate_models.py
```

---

### Step 7: Run Automated Tests
Verify that all routes, dynamic pricing calculations, checkout screening, and admin APIs pass tests:

```bash
python tests_e2e.py
```
*(All 5 test suites should return `OK`)*

---

### Step 8: Start the Web Application
```bash
python run.py
```
The server will start on port `5001`.

---

## 🌐 Portal URLs & Default Credentials

| Portal | URL | Demo Credentials | Notes |
| :--- | :--- | :--- | :--- |
| **🛍️ Customer Storefront** | [http://127.0.0.1:5001/](http://127.0.0.1:5001/) | `customer@idealab.com` / `customer123` | Browse flash sales, shopping cart, checkout |
| **🛡️ Admin Command Center** | [http://127.0.0.1:5001/admin](http://127.0.0.1:5001/admin) | `admin@idealab.com` / `admin123` | Dynamic pricing matrix, fraud alerts, metrics |
| **🔐 Admin Login Page** | [http://127.0.0.1:5001/admin/login](http://127.0.0.1:5001/admin/login) | `admin@idealab.com` / `admin123` | Separate secure admin login |
| **👤 Customer Sign In** | [http://127.0.0.1:5001/login](http://127.0.0.1:5001/login) | `customer@idealab.com` / `customer123` | Customer login with 1-click Auto-Fill |

*(Any customer from `customers.csv` can also log in using their email and default password `password123`)*

---

## 🏗️ Architecture & Folder Structure

```
idealab/
├── app/
│   ├── __init__.py                # Flask app factory, LoginManager, Jinja filters & Blueprints
│   ├── models.py                  # SQLAlchemy models (Products, Customers, Orders, FraudAlerts, etc.)
│   ├── auth/                      # Authentication routes (Customer & Admin)
│   ├── products/                  # Storefront catalog & Product detail views
│   ├── orders/                    # Shopping Cart, Checkout, and Fraud screening triggers
│   ├── pricing/                   # Dynamic pricing engine (XGBoost inference + Cost safety floor)
│   ├── fraud/                     # Real-time fraud defense engine (ML probabilities + Rules)
│   ├── dashboard/                 # Admin Dashboard views & Analytics APIs
│   ├── static/                    # Custom modern SaaS CSS and JS
│   └── templates/                 # Storefront & Admin templates (Tailwind CSS + Chart.js)
├── ml/
│   ├── train_fraud_model.py       # Fraud classifier training with engineered features
│   ├── train_pricing_model.py     # Dynamic pricing XGBoost regressor
│   ├── evaluate_models.py         # Consolidated ML evaluation metrics script
│   └── saved_models/              # Serialized joblib models & JSON telemetry
├── data/
│   ├── raw/                       # Source CSVs (products, customers, orders, fraud_labels, competitor_prices)
│   ├── import_data.py             # SQLite ETL importer & foreign key integrity validator
│   └── localize_indian_dataset.py # Indian e-commerce catalog & customer name localization
├── requirements.txt
├── README.md
├── tests_e2e.py                   # Automated end-to-end test suite
└── run.py                         # Application entrypoint
```

---

## 🤖 Machine Learning Models & Metrics

### 1. Dynamic Pricing Regressor (XGBoost)
- **Features**: `base_price`, `cost_price`, `stock_quantity`, `popularity_score`, `stock_depletion_ratio`, `demand_rate`, `competitor_delta_ratio`, `margin_room`, `avg_competitor_price`, `min_competitor_price`, `category`.
- **Hard Safety Constraint**: $P_{recommended} \ge \text{cost\_price} \times 1.03$ (guaranteed zero selling-at-a-loss).
- **Performance**:
  - $R^2$ Score: **`0.9825`**
  - MAE: **`₹732.94`**
  - RMSE: **`₹2,560.63`**
  - Simulated Revenue Uplift: **`+42.63%`** vs flat discount.

### 2. Real-Time Fraud Classifier (XGBoost + Explainability Shield)
- **Features**: `orders_last_min_device`, `orders_last_min_ip`, `account_age_days`, `days_since_signup`, `coupon_reuse_count`, `quantity`, `price_paid`, `discount_applied`, `payment_method`.
- **Explainable Rules**:
  - Device/IP Velocity Surge ($>5$ orders/60s) &rarr; `bot_purchase` tag + score boost.
  - Coupon Code Recycling &rarr; `coupon_abuse` tag + score boost.
  - Fresh account immediate high-ticket order &rarr; `fake_account` tag.
- **Threshold Routing**:
  - Score $\ge 0.80$: **Auto-Block** (Threat stopped).
  - $0.40 \le$ Score $< 0.80$: **Flag for Manual Review** (Held in Admin Queue).
  - Score $< 0.40$: **Auto-Approve**.
- **Performance**:
  - Accuracy: **`0.8848`**
  - Precision: **`0.8637`**
  - Recall: **`0.8902`**
  - F1-Score: **`0.8769`**

---

## 🎯 Demo Scenarios to Try

1. **Place a Normal Order**:
   - Go to [Storefront](http://127.0.0.1:5001/), add an item to cart, proceed to checkout with coupon `FLASH20`.
   - Result: Instantly **Approved** with low risk score and order confirmed.

2. **Trigger Fraud Detection (Bot Burst / Coupon Abuse)**:
   - On checkout, use coupon code `SPAM_EXPLOIT_BOT` or simulate rapid orders.
   - Result: AI Shield intercepts threat with risk score $>80\%$, flags as **Blocked / Under Review**, and logs explainable signals.

3. **Admin Dynamic Price Adjustment**:
   - Go to [Admin Pricing Matrix](http://127.0.0.1:5001/admin/pricing).
   - Review AI recommended prices, click on any SKU to view historical price trajectory, and click **"Apply"** or **"Apply All"** to update store prices.

4. **Live Threat Simulator**:
   - Go to [Admin Fraud Alerts](http://127.0.0.1:5001/admin/fraud-alerts) and click **"Simulate Attack"**.
   - Result: Live traffic is screened through the AI model and intercepted in real-time.
