## Portfolio Analysis Dashboard

Interactive Streamlit app for building a stock portfolio, fetching live market data from Yahoo Finance, and visualizing performance with Plotly.

### Features
- **Portfolio Builder**: Add holdings manually or via CSV upload with multi-currency support
- **Dashboard Overview**: Key metrics, allocation pie chart, gain/loss bar chart
- **Detailed Analysis**: Compare vs S&P 500, risk metrics, sector breakdown
- **Data Management**: JSON editor, backup/restore, CSV export/import, portfolio statistics

### Requirements
- Python 3.9+ (recommended 3.9–3.12)
- macOS/Linux/Windows supported

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
pip install streamlit yfinance pandas numpy plotly requests
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
- **Data**: Pulled via `yfinance` (Yahoo Finance). Data may be delayed and is for informational purposes only.
- **Caching**: Streamlit `@st.cache_data` is used to avoid redundant API calls.
- **Visuals**: Built with Plotly (`px` and `graph_objects`).
- **Multi-Currency**: Automatic currency conversion using Yahoo Finance exchange rates.
- **Data Storage**: Local JSON files in `data/` directory with automatic backups.
- **Navigation**: Clean sidebar with custom title above default Streamlit navigation.

### Project Structure (Multipage)
```
portfolio/
  Portfolio.py                 # Home page
  app_utils.py                 # Shared utilities (data, metrics, styling)
  data_utils.py                # Data persistence and management functions
  pages/
    1_Portfolio_Builder.py    # Portfolio management
    2_Dashboard_Overview.py   # Performance dashboard
    3_Detailed_Analysis.py    # Advanced analytics
    4_Data_Management.py      # Data tools and JSON editor
  data/                        # Local data storage
    portfolio.json            # Portfolio holdings
    settings.json             # App settings
    backups/                  # Automatic backups
    exports/                  # CSV exports
  requirements.txt
  README.md
  .gitignore                  # Git ignore rules
  .venv/                      # Local virtual environment (not required to commit)
```

You can also run a specific page directly (Streamlit will mount it as the only page):
```bash
streamlit run pages/2_Dashboard_Overview.py
```

### Troubleshooting
- **Data Issues**: If `yfinance` fails to fetch data, check your internet connection and try again; some tickers may be unavailable.
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
- **Currency Conversion**: If exchange rates fail, the app will fallback to 1:1 conversion and show a warning.
- **Data Storage**: If you encounter JSON errors, check the `data/` directory permissions and try creating a backup.

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

### License
Personal/educational use. Add your preferred license here if distributing.


