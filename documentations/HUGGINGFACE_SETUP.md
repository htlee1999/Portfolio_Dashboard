# Google Gemini API Setup for Investment Assessment

This guide will help you set up the Google Gemini 2.5 Flash API for AI-powered investment recommendations in your Portfolio Dashboard.

## Prerequisites

1. **Install Required Packages:**
   ```bash
   pip install google-genai python-dotenv
   ```

2. **Get a Free Google Gemini API Token:**
   - Go to [https://aistudio.google.com/](https://aistudio.google.com/)
   - Sign in with your Google account
   - Click "Get API key"
   - Create a new API key
   - Give it a name (e.g., "Portfolio Dashboard")
   - Copy the generated token

## Setup Steps

### Option 1: Using .env File (Recommended)

1. **Create a `.env` file in your project root directory:**
   ```bash
   touch .env
   ```

2. **Add your API token to the `.env` file:**
   ```
   GEMINI_API_KEY=your_actual_api_token_here
   ```
   Replace `your_actual_api_token_here` with the token you copied from Google AI Studio.

3. **The `.env` file is already included in `.gitignore`** so your API key won't be committed to version control.

### Option 2: Using Environment Variables

If you prefer not to use a `.env` file, you can set the environment variable directly:

**On macOS/Linux:**
```bash
export GEMINI_API_KEY="your_actual_api_token_here"
```

**On Windows:**
```cmd
set GEMINI_API_KEY=your_actual_api_token_here
```

## Usage

1. **Start your Portfolio Dashboard:**
   ```bash
   streamlit run Portfolio.py
   ```

2. **Navigate to the Investment Assessment page** (page 7 in the sidebar)

3. **Select a stock symbol** and click "Run Assessment"

4. **Click "Generate AI Assessment"** to get AI-powered buy/sell/hold recommendations

## Free Tier Limits

- **Free Tier:** 15 requests per minute, 1 million tokens per day
- **Paid Tier:** Higher rate limits and additional features available

## Troubleshooting

### "API key not found" Error
- Make sure your `.env` file is in the project root directory
- Verify the token is correctly formatted: `GEMINI_API_KEY=your_token_here`
- Restart your Streamlit application after creating the `.env` file

### "Required packages not installed" Error
- Run: `pip install google-genai python-dotenv`
- Make sure you're in the correct Python environment

### API Rate Limit Exceeded
- You've exceeded the free tier limits (15 requests per minute)
- Wait a minute before making more requests
- Consider upgrading to a paid plan for higher limits

## Security Notes

- Never commit your `.env` file to version control
- Keep your API token secure and don't share it
- The `.env` file is already included in `.gitignore` for security

## Features

The AI Assessment page provides:
- **Technical Analysis:** RSI, MACD, Bollinger Bands, Moving Averages, OBV
- **Fundamental Analysis:** P/E ratios, financial metrics, growth rates
- **AI Recommendations:** BUY/SELL/HOLD with confidence levels and reasoning
- **Combined Analysis:** Radar chart showing overall assessment

Enjoy your AI-powered investment analysis! 🚀
