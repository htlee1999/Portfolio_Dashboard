## Portfolio Analysis Dashboard

Interactive Streamlit app for building a stock portfolio, fetching live market data from Yahoo Finance, and visualizing performance with Plotly.

### Features
- **🔐 User Authentication**: Secure login system with password protection and user management
- **📈 Portfolio Builder**: Add holdings manually or via CSV upload with multi-currency support
- **📊 Dashboard Overview**: Key metrics, allocation pie chart, gain/loss bar chart
- **🔍 Detailed Analysis**: Compare vs S&P 500, risk metrics, sector breakdown
- **📈 Technical Analysis**: Advanced technical indicators, charting tools, and market analysis
- **📋 Fundamental Analysis**: Company fundamentals, financial ratios, and valuation metrics
- **🎯 AI Investment Assessment**: AI-powered investment recommendations using Google Gemini
- **💾 Data Management**: JSON editor, backup/restore, CSV export/import, portfolio statistics
- **📊 Usage Monitoring**: Track API usage, costs, and system performance
- **🌍 Multi-Currency Support**: Automatic currency conversion for global portfolios

### Requirements
- Python 3.9+ (recommended 3.9–3.12)
- macOS/Linux/Windows supported
- Internet connection for real-time market data
- Google Gemini API key (optional, for AI features)
- Hugging Face API key (optional, for additional AI features)

### Fresh Setup 
```bash
git clone <your-repo-url> portfolio
cd portfolio
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you don't have `requirements.txt` yet, install the core dependencies:
```bash
pip install streamlit yfinance pandas numpy plotly requests cryptography google-genai python-dotenv
```

### Configuration
1. **Copy the environment template**:
   ```bash
   cp config.env.example .env
   ```

2. **Configure API keys** (optional):
   - Edit `.env` file and add your API keys:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     HUGGINGFACE_API_KEY=your_huggingface_api_key_here
     ```
   - See [Gemini Setup Guide](documentations/GEMINI_SETUP.md) for detailed instructions

3. **Start the application**:
   ```bash
   streamlit run Portfolio.py
   ```

### CSV Template
The CSV upload expects columns: `Symbol, Quantity, Purchase_Price, Purchase_Date, Currency`.
You can click "Download CSV Template" in the app, or create one like:
```csv
Symbol,Quantity,Purchase_Price,Purchase_Date,Currency
AAPL,10,150.00,2024-01-01,USD
GOOGL,5,2500.00,2024-01-15,SGD
MSFT,15,300.00,2024-02-01,USD
```

**Supported Currencies**: USD, SGD, EUR, GBP, JPY, CAD, AUD, HKD, CNY, INR, KRW, THB, MYR, IDR, PHP, VND

### How It Works
- **🔐 Authentication**: Secure user management with encrypted password storage
- **📊 Data**: Pulled via `yfinance` (Yahoo Finance). Data may be delayed and is for informational purposes only.
- **⚡ Caching**: Streamlit `@st.cache_data` is used to avoid redundant API calls.
- **📈 Visuals**: Built with Plotly (`px` and `graph_objects`) for interactive charts.
- **🌍 Multi-Currency**: Automatic currency conversion using Yahoo Finance exchange rates.
- **💾 Data Storage**: Local JSON files in `data/` directory with automatic backups.
- **🤖 AI Features**: Google Gemini integration for intelligent investment analysis and recommendations.
- **📊 Technical Analysis**: Advanced charting with multiple technical indicators and overlays.
- **🔍 Fundamental Analysis**: Company financial metrics and valuation analysis.
- **📱 Navigation**: Clean sidebar with custom title above default Streamlit navigation.

### Project Structure (Multipage)
```
portfolio/
  Portfolio.py                 # Home page
  app_utils.py                 # Shared utilities (data, metrics, styling)
  auth_utils.py                # Authentication and user management
  data_utils.py                # Data persistence and management functions
  gemini_monitor.py            # AI usage monitoring and cost tracking
  config.env.example          # Environment configuration template
  pages/
    0_Sign_Up.py              # User registration
    1_Portfolio_Builder.py    # Portfolio management
    2_Dashboard_Overview.py   # Performance dashboard
    3_Detailed_Analysis.py    # Advanced analytics
    4_Data_Management.py      # Data tools and JSON editor
    5_Technical_Analysis.py   # Technical analysis tools
    6_Fundamental_Analysis.py # Fundamental analysis
    7_Investment_Assessment.py # AI-powered investment assessment
    8_Usage_Monitoring.py     # Usage monitoring dashboard
  data/                        # Local data storage
    portfolio_*.json          # User portfolio holdings
    settings.json             # App settings
    users.json                # User authentication data
    gemini_usage.json         # AI usage tracking
    backups/                  # Automatic backups
  documentations/              # Documentation files
    README.md                 # Documentation index
    DATA_README.md            # Data structure documentation
    GEMINI_SETUP.md          # Gemini API setup guide
    GEMINI_MONITORING_SETUP.md # Gemini monitoring setup
    HUGGINGFACE_SETUP.md     # Hugging Face setup guide
    LOGIN_SETUP.md           # Authentication setup guide
    TECHNICAL_ANALYSIS_README.md # Technical analysis documentation
  requirements.txt
  README.md                   # This file
  .gitignore                  # Git ignore rules
  .venv/                      # Local virtual environment (not required to commit)
```

You can also run a specific page directly (Streamlit will mount it as the only page):
```bash
streamlit run pages/2_Dashboard_Overview.py
```

### Troubleshooting
- **🔐 Authentication Issues**: 
  - If login fails, check that `users.json` exists in the `data/` directory
  - Reset password using the "Change Password" option in the user menu
  - See [Authentication Setup Guide](documentations/LOGIN_SETUP.md) for detailed help

- **📊 Data Issues**: 
  - If `yfinance` fails to fetch data, check your internet connection and try again
  - Some tickers may be unavailable or delisted
  - Try using different ticker symbols or check Yahoo Finance directly

- **🤖 AI Features Not Working**:
  - Ensure your `.env` file contains valid API keys
  - Check [Gemini Setup Guide](documentations/GEMINI_SETUP.md) for configuration help
  - Monitor usage in the Usage Monitoring page to track API limits

- **🔧 Technical Issues**:
  - **SSL/Cert Errors**: Upgrade `certifi` and `requests`:
    ```bash
    pip install --upgrade certifi requests
    ```
  - **Streamlit Won't Start**: Confirm you're using the project venv:
    ```bash
    source .venv/bin/activate
    python --version
    which streamlit
    ```
  - **Currency Conversion**: If exchange rates fail, the app will fallback to 1:1 conversion and show a warning
  - **Data Storage**: If you encounter JSON errors, check the `data/` directory permissions and try creating a backup

### Updating Dependencies
```bash
source .venv/bin/activate
pip install -U pip
pip install -U -r requirements.txt
```

To re-freeze (pin) dependencies after updates:
```bash
pip freeze --exclude-editable > requirements.txt
```

### 🚀 Quick Start Guide
1. **Install dependencies**: `pip install -r requirements.txt`
2. **Configure environment**: `cp config.env.example .env`
3. **Start the app**: `streamlit run Portfolio.py`
4. **Create account**: Use the Sign Up page to create your first user account
5. **Build portfolio**: Add stocks using the Portfolio Builder page
6. **Explore features**: Try Technical Analysis, Fundamental Analysis, and AI Investment Assessment

### Documentation
📖 **[Complete Documentation Index](documentations/README.md)** - Start here for all setup guides and feature documentation

Quick links to key setup guides:
- **[Authentication Setup](documentations/LOGIN_SETUP.md)** - User authentication and login system configuration
- **[Gemini API Setup](documentations/GEMINI_SETUP.md)** - Google Gemini API integration for AI features
- **[Technical Analysis](documentations/TECHNICAL_ANALYSIS_README.md)** - Technical analysis features and indicators
- **[Data Structure](documentations/DATA_README.md)** - Data storage and structure documentation

### License
Personal/educational use. Add your preferred license here if distributing.


