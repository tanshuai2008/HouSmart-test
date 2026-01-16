# HouSmart 🏠 | AI-Native Real Estate Intelligence

**HouSmart** is a vertical AI platform designed to automate real estate due diligence. Unlike generic LLM wrappers, HouSmart combines deterministic scoring models with generative reasoning to provide actionable, data-backed investment insights.

它不仅是“聊天”，而是**计算**。它将来自 US Census、FCC 和 Geoapify 的硬数据与用户的投资偏好（长期记忆）相结合，生成具有可解释性的投资备忘录。

---

## 🚀 Core Philosophy: Why HouSmart?

Generic models (like ChatGPT) are prone to hallucinations when dealing with specific real estate metrics. HouSmart solves this by implementing a **"System of Record + System of Intelligence"** architecture:
1.  **Deterministic Data Layer**: We use verified data sources (Census Bureau, Geoapify) for objective metrics (Crime, Schools, ROI).
2.  **Hard Logic Scoring**: A Python-based normalization engine calculates stability scores *before* the AI sees the data.
3.  **Contextual Reasoning**: The LLM (Gemini) acts as an analyst, interpreting the pre-calculated scores rather than inventing them.
---

## 🌟 Key Features
### 1. Multi-Source Data Fusion (The "Truth" Layer)
Aggregates fragmented data into a unified property profile:
* **Demographics**: Real-time population, income, and housing vacancy data via **US Census Bureau API**.
* **Hyper-Local Amenities**: 1km-radius POI analysis (Schools, Transit, Leisure) using **Geoapify**.
* **FIPS Precision**: Automatic block-level geolocation conversion via **FCC API**.
### 2. Context-Aware Memory (The "Moat")
* **Stateful User Profiles**: Powered by **Supabase (PostgreSQL)**, HouSmart remembers user preferences (e.g., "I avoid high-traffic areas" or "I need cash-flow focus").
* **Adaptive Analysis**: The system automatically adjusts its recommendations based on historical user interactions stored in the `logs/` and database.
### 3. Investment Logic Engine
* **Visualization**: Interactive hex-layer maps using **PyDeck** for intuitive location understanding.
* **Risk Assessment**: Automated "Red Flag" detection for vacancy rates and economic downturn trends.
* **Smart Fallbacks**: Robust error handling that estimates demographics when official block-level data is missing.
---

## 🛠️ Technical Architecture
```mermaid
graph TD
    User[User Input] --> App[Streamlit Frontend]
    App --> DataLayer[Data Aggregation Layer]
    
    subgraph "Data Fusion"
        DataLayer --> Geo[Geoapify API]
        DataLayer --> Census[US Census API]
        DataLayer --> DB[(Supabase Memory)]
    end
    
    DataLayer --> Logic[Normalization Engine]
    Logic --> LLM[Google Gemini 2.0]
    
    LLM --> Report[Investment Memo]
    Report --> UI[Interactive Dashboard]

Directory Structure
Home.py: Application entry point and UI orchestration.
llm.py: The Generative AI logic, handling prompt engineering and reasoning.
data.py: Core data fetchers for Census and third-party APIs.
map.py: Geospatial visualization logic (PyDeck).
supabase_utils.py: Database connection for state management and user memory.
components.py: Reusable UI widgets.

⚡ Getting Started
Prerequisites
Python 3.9+

API Keys for Google Gemini, Geoapify, and Supabase.

Installation
1. Clone the repository
git clone [https://github.com/tanshuai2008/HouSmart-test.git](https://github.com/tanshuai2008/HouSmart-test.git)
cd HouSmart-test
2. Install Dependencies
pip install -r requirements.txt
3. Configuration Create a .streamlit/secrets.toml file with your credentials:
# AI & Maps
GEMINI_API_KEY = "your_google_ai_key"
GEOAPIFY_API_KEY = "your_geoapify_key"

# Database (Supabase)
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_anon_key"

# Optional: Google Sheets for legacy logging
[gcp_service_account]
# ... your GCP credentials
4.Run the Application
streamlit run Home.py

Roadmap
Phase 1 (MVP): Streamlit prototype with basic data fetching and AI summary. ✅
Phase 2 (Hard Logic): Implement the custom StabilityScoringModel (Python-based weighted scoring) to reduce AI dependence. 🚧
Phase 3 (Platform): Migrate frontend to React/Next.js for consumer-grade experience.
Phase 4 (RAG): Ingest historical transaction data into Supabase Vector Store for comparable market analysis (Comps).

📄 License
Distributed under the MIT License. See LICENSE for more information.

Built with ❤️ by tanshuai2008 - Transforming Real Estate with Contextual AI.
