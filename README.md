# HouSmart 🏠

**AI-Driven Real Estate Location Intelligence MVP**

HouSmart is a Python-based location analysis tool built with Streamlit. It leverages Generative AI (Google Gemini) and real-time data APIs (e.g., Geoapify, US Census Bureau, Rentcast, etc.) to provide comprehensive investment insights for any US address. 

Just enter an address, and HouSmart evaluates the neighborhood's potential, risks, and demographic suitability in seconds.

---

## 🌟 Features

*   **📍 Smart Geocoding & POI Analysis**:
    *   Integrates **Geoapify Places API** to identify key amenities (commercial, education, leisure) within a 1 km radius.
    *   Interactive map visualization using **PyDeck** (MapBox compatible).
*   **📊 Real Demographic Data**:
    *   Automatic **FIPS Code Lookup** via FCC API.
    *   Fetches real-time population and business statistics from the **US Census Bureau API** (2024 Demographics & Business Patterns).
*   **🤖 Generative AI Insights**:
    *   Powered by **Google Gemini 2.5 Flash**.
    *   Synthesizes raw data into actionable reports:
        *   **Highlights**: Key selling points of the location.
        *   **Risks**: Potential downsides (e.g., low business density, high vacancy).
        *   **Investment Strategy**: Tailored advice for investors.
        *   **Location Score**: Quantified 0-100 rating.
        *   **Memorize User's preference**: LLM will integrate your earlier input preference for the analysis. For example, it will remind you if a house is close to highway, but you told LLM that you dont want noise.
*   **🛡️ Robust Fallbacks**:
    *   Smartly falls back to AI-estimated demographics if official Census data is unavailable for a specific block.

---

## 🛠️ Technology Stack

*   **Frontend**: [Streamlit](https://streamlit.io/)
*   **AI Engine**: [Google Gemini API](https://ai.google.dev/)
*   **Mapping**: [PyDeck](https://pydeck.gl/)
*   **Data Sources**:
    *   [Geoapify](https://www.geoapify.com/) (Geocoding & Places)
    *   [US Census Bureau](https://www.census.gov/data/developers/data-sets.html) (Demographics & Economics)
    *   [FCC](https://geo.fcc.gov/) (Block & FIPS Conversion)

---

## 🚀 Getting Started

### Prerequisites

*   Python 3.9+
*   API Keys:
    *   **Google Gemini API Key** (Required for analysis)
    *   **Geoapify API Key** (Recommended for accurate POI data)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/tanshuai2008/HouSmart-OPC.git
    cd HouSmart-OPC/HouSmart
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Google Sheets Setup (Optional for Persistence)**:
    *   Create a Google Cloud Project and enable **Google Sheets API**.
    *   Create a **Service Account** and download the JSON key.
    *   Create a Google Sheet named `HouSmart_Logs` and share it with the Service Account email.
    *   Add the JSON content to your `secrets.toml` (or Streamlit Cloud Secrets) under a `[gcp_service_account]` section.

4.  **Configure Environment**:
    Create a `.streamlit/secrets.toml` file in the `HouSmart` directory for local development, or add these to your [Streamlit Cloud Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management):
    ```toml
    # .streamlit/secrets.toml
    GEMINI_API_KEY = "your_primary_key"
    GEMINI_API_KEY_2 = "your_backup_key_1" # Optional: Auto-rotation
    GEMINI_API_KEY_3 = "your_backup_key_2"
    GEOAPIFY_API_KEY = "your_geoapify_key_here"
    ```
    *Note: The application calls these keys directly from `st.secrets`.*

### Running the App

```bash
streamlit run app.py
```

Open your browser to `http://localhost:8501`.

---

## 📖 Usage Guide

1.  **Enter Credentials**: If not set in `.env`, paste your Gemini and Geoapify keys in the sidebar.
2.  **Select Model**: Choose your preferred Gemini model (e.g., `gemini-1.5-flash`) from the dropdown.
3.  **Analyze**: Type a US address (e.g., "123 Main St, Springfield, IL") and click **Analyze Location**.
4.  **Review Report**:
    *   **Left Panel**: Interactive map showing the location and nearby amenities.
    *   **Right Panel**: AI-generated investment report, risk assessment, and raw census data card.

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
