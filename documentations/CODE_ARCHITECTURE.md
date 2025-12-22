# Code Architecture

This document describes the modular architecture of the Portfolio Dashboard application, including utility modules, design patterns, and code organization.

## Overview

The codebase is organized into reusable utility modules that provide shared functionality across all pages. This architecture eliminates code duplication and ensures consistent behavior throughout the application.

## Utility Modules

### 1. `technical_indicators.py`

Consolidated technical analysis module containing reusable classes for market analysis.

#### Classes

**`TechnicalAnalysis`** - Comprehensive technical analysis with the top 5 indicators:

```python
from technical_indicators import TechnicalAnalysis

# Initialize with OHLCV data
ta = TechnicalAnalysis(data)

# Calculate individual indicators
rsi = ta.calculate_rsi(period=14)
macd_line, signal_line, histogram = ta.calculate_macd(fast_period=12, slow_period=26, signal_period=9)
upper_bb, middle_bb, lower_bb, bb_percent, band_width = ta.calculate_bollinger_bands(period=20, std_dev=2)
mas = ta.calculate_moving_averages(periods=[5, 10, 20, 50])
obv = ta.calculate_obv()

# Get trading signals for all or specific indicators
signals = ta.get_signals(indicators=['rsi', 'macd', 'bollinger', 'moving_averages', 'obv'])

# Add all indicators to DataFrame
data_with_indicators = ta.add_all_indicators()
```

**`PredictiveAnalysis`** - ML feature preparation for predictive models:

```python
from technical_indicators import PredictiveAnalysis

pa = PredictiveAnalysis(data)
features_df = pa.prepare_features()  # Returns DataFrame with all ML features
```

#### Used By
- `pages/5_Technical_Analysis.py`
- `pages/7_Investment_Assessment.py`
- `pages/9_Predictive_Analysis.py`

---

### 2. `page_utils.py`

Page initialization utilities that consolidate common setup patterns.

#### Functions

**`init_protected_page(show_login_form: bool = False) -> bool`**

Initializes a protected page requiring authentication. Handles:
1. Authentication session initialization
2. Authentication check (stops execution if not authenticated)
3. Page configuration setup
4. CSS injection
5. Session state initialization
6. Sidebar creation
7. User menu display

```python
from page_utils import init_protected_page

# At the start of any protected page
init_protected_page()  # Returns True if authenticated, calls st.stop() if not
```

**`init_public_page() -> None`**

Initializes a public page (like signup) without requiring authentication:

```python
from page_utils import init_public_page

# At the start of public pages
init_public_page()
```

#### Used By
All 11 page files in the `pages/` directory.

---

### 3. `config.py`

Centralized configuration module for API keys, feature flags, and shared constants.

#### API Key Functions

```python
from config import (
    get_serp_api_key,
    get_gemini_api_key,
    is_serp_api_configured,
    is_gemini_api_configured
)

# Get API keys
serp_key = get_serp_api_key()
gemini_key = get_gemini_api_key()

# Check if keys are properly configured
if is_gemini_api_configured():
    # Enable AI features
    pass
```

#### Feature Availability Flags

```python
from config import GEMINI_AVAILABLE, ML_AVAILABLE, SENTIMENT_AVAILABLE, SENTIMENT_ENABLED

# Check if Google Gemini library is installed
if GEMINI_AVAILABLE:
    from google import genai

# Check if ML libraries are installed
if ML_AVAILABLE:
    from sklearn.ensemble import RandomForestRegressor

# Check if sentiment analysis is fully enabled (library + API key)
if SENTIMENT_ENABLED:
    # Run sentiment analysis
    pass
```

#### Period Constants

```python
from config import PERIOD_OPTIONS, PERIOD_LIST, DEFAULT_PERIOD_INDEX

# For labeled dropdowns
selected = st.selectbox("Period", list(PERIOD_OPTIONS.keys()))
period_code = PERIOD_OPTIONS[selected]  # e.g., "1y"

# For simple dropdowns
period = st.selectbox("Period", PERIOD_LIST, index=DEFAULT_PERIOD_INDEX)
```

#### Used By
All pages that use API features, ML models, or period selection.

---

### 4. `file_utils.py`

File and JSON operations utilities with error handling.

#### Functions

```python
from file_utils import (
    ensure_directory,
    ensure_parent_directory,
    load_json,
    save_json,
    file_exists,
    get_file_size,
    get_file_modified_time
)

# Directory operations
ensure_directory("data/backups")
ensure_parent_directory("data/users.json")

# JSON operations with safe defaults
data = load_json("data/portfolio.json", default={})
success = save_json("data/settings.json", settings_dict)

# File checks
if file_exists("data/cache.json"):
    size = get_file_size("data/cache.json")
    modified = get_file_modified_time("data/cache.json")
```

#### Used By
- `auth_utils.py` - User data management
- `gemini_monitor.py` - Usage tracking
- `data_utils.py` - Portfolio data persistence

---

### 5. `app_utils.py` (Enhanced)

Shared utilities for data, metrics, styling, and UI components.

#### Currency Selection

```python
from app_utils import SUPPORTED_CURRENCIES, create_currency_selector

# List of all supported currencies
print(SUPPORTED_CURRENCIES)
# ["USD", "SGD", "EUR", "GBP", "JPY", "CAD", "AUD", "HKD", "CNY", "INR", "KRW", "THB", "MYR", "IDR", "PHP", "VND"]

# Create a reusable currency dropdown
selected_currency = create_currency_selector(
    label="Select base currency:",
    show_subheader=True,
    subheader_text="Base Currency",
    auto_save=True  # Automatically saves selection
)
```

#### Chart Styling

```python
from app_utils import apply_chart_style
import plotly.graph_objects as go

fig = go.Figure()
# ... add traces ...

apply_chart_style(
    fig,
    title="Price Chart",
    height=500,
    xaxis_title="Date",
    yaxis_title="Price ($)",
    show_legend=True
)

st.plotly_chart(fig, use_container_width=True)
```

#### Used By
All pages for data fetching, metrics calculation, and UI components.

---

### 6. `auth_utils.py` (Enhanced)

Authentication and user management with password validation.

#### Password Validation

```python
from auth_utils import validate_password, MIN_PASSWORD_LENGTH

# Validate password alone
is_valid, error_msg = validate_password(password)

# Validate password with confirmation
is_valid, error_msg = validate_password(password, confirm_password)

if not is_valid:
    st.error(error_msg)
```

#### Used By
- `pages/0_Sign_Up.py` - User registration
- `auth_utils.py` - Password change functionality
- User management forms

---

## Module Dependency Graph

```
Portfolio.py (main entry)
    |
    +-- app_utils.py (data, metrics, currency, chart styling)
    |       |
    |       +-- config.py (API keys, feature flags)
    |
    +-- auth_utils.py (authentication)
    |       |
    |       +-- file_utils.py (JSON operations)
    |
    +-- page_utils.py (page initialization)
    |       |
    |       +-- app_utils.py
    |       +-- auth_utils.py
    |
    +-- technical_indicators.py (analysis)
    |
    +-- gemini_monitor.py (AI usage tracking)
            |
            +-- file_utils.py
```

## Design Patterns

### 1. Single Source of Truth

All shared constants and configurations are defined in one place:
- API keys and feature flags in `config.py`
- Currencies in `app_utils.py`
- Password requirements in `auth_utils.py`

### 2. Lazy Import

Heavy dependencies are checked at module level but imported only when needed:

```python
# In config.py - check availability once
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# In pages - use the flag to conditionally import
if GEMINI_AVAILABLE:
    from google import genai
```

### 3. Graceful Degradation

Features degrade gracefully when dependencies are missing:
- AI features disabled when Gemini API unavailable
- ML predictions disabled when sklearn not installed
- Sentiment analysis disabled when API key not configured

### 4. Standardized Initialization

All pages follow the same initialization pattern:

```python
from page_utils import init_protected_page

def main():
    init_protected_page()
    # Page content here

if __name__ == "__main__":
    main()
```

## Adding New Features

### Adding a New Utility Function

1. Identify the appropriate module based on functionality
2. Add the function with proper docstrings
3. Export if needed (add to module-level imports)
4. Update this documentation

### Adding a New Technical Indicator

1. Add method to `TechnicalAnalysis` class in `technical_indicators.py`
2. Add to `get_signals()` if it generates signals
3. Add to `add_all_indicators()` for batch processing
4. Update `TECHNICAL_ANALYSIS_README.md`

### Adding a New Page

1. Create page file in `pages/` directory
2. Use `init_protected_page()` or `init_public_page()` for initialization
3. Import from utility modules as needed
4. Use `config.py` flags for feature availability

## Testing

When modifying utility modules, ensure:
1. All pages still initialize correctly
2. Feature flags work as expected
3. JSON operations handle edge cases
4. Authentication flow is not broken

## Performance Considerations

- **Caching**: All utility modules use `@st.cache_data` for expensive operations
- **Lazy Loading**: Heavy imports are deferred until actually needed
- **Shared Instances**: Global instances (like `GeminiUsageMonitor`) are reused

---

*This architecture documentation was created during the code consolidation effort that removed ~600+ lines of duplicate code and established consistent patterns across the application.*
