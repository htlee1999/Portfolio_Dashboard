#!/usr/bin/env python3
"""
Sentiment Analysis Setup Script

This script helps you set up and test the Sentiment Analysis feature for the Portfolio Dashboard.
It will:
1. Check for required packages
2. Download necessary NLTK data
3. Test your SERPapi connection
4. Verify the .env configuration

Usage:
    python setup_sentiment.py
"""

import sys
import os
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def print_success(text):
    """Print a success message."""
    print(f"✅ {text}")

def print_error(text):
    """Print an error message."""
    print(f"❌ {text}")

def print_warning(text):
    """Print a warning message."""
    print(f"⚠️  {text}")

def print_info(text):
    """Print an info message."""
    print(f"ℹ️  {text}")

def check_package(package_name, import_name=None):
    """Check if a package is installed."""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def install_package(package_name):
    """Install a package using pip."""
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """Main setup function."""
    print_header("Sentiment Analysis Setup")
    
    # Step 1: Check Python version
    print_info(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print_error("Python 3.8 or higher is required!")
        print_info("Please upgrade your Python installation.")
        return False
    print_success("Python version is compatible")
    
    # Step 2: Check for required packages
    print_header("Checking Required Packages")
    
    packages = {
        "google-search-results": "serpapi",
        "nltk": "nltk",
        "textblob": "textblob",
        "vaderSentiment": "vaderSentiment",
        "python-dotenv": "dotenv"
    }
    
    missing_packages = []
    
    for package, import_name in packages.items():
        print(f"Checking {package}...", end=" ")
        if check_package(package, import_name):
            print_success("Installed")
        else:
            print_error("Not installed")
            missing_packages.append(package)
    
    if missing_packages:
        print_warning(f"Missing packages: {', '.join(missing_packages)}")
        print_info("Installing missing packages...")
        
        for package in missing_packages:
            print(f"Installing {package}...", end=" ")
            if install_package(package):
                print_success("Done")
            else:
                print_error("Failed")
                print_info("Please run: pip install -r requirements.txt")
                return False
    
    print_success("All required packages are installed!")
    
    # Step 3: Download NLTK data
    print_header("Downloading NLTK Data")
    
    try:
        import nltk
        
        # Download VADER lexicon
        print("Downloading VADER lexicon...", end=" ")
        nltk.download('vader_lexicon', quiet=True)
        print_success("Done")
        
        # Download Punkt tokenizer
        print("Downloading Punkt tokenizer...", end=" ")
        nltk.download('punkt', quiet=True)
        print_success("Done")
        
        # Verify VADER is accessible
        print("Verifying VADER...", end=" ")
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        test_result = sia.polarity_scores("This is a great stock!")
        print_success("Working correctly")
        print_info(f"Test sentiment: {test_result}")
        
    except Exception as e:
        print_error(f"NLTK setup failed: {str(e)}")
        return False
    
    print_success("NLTK data downloaded and verified!")
    
    # Step 4: Test TextBlob
    print_header("Testing TextBlob")
    
    try:
        from textblob import TextBlob
        
        # Download TextBlob corpora if needed
        print("Downloading TextBlob data (this may take a moment)...", end=" ")
        try:
            import textblob
            textblob.download_corpora()
        except:
            pass  # May already be downloaded
        
        # Test TextBlob
        print("Testing TextBlob...", end=" ")
        blob = TextBlob("This is a great stock!")
        sentiment = blob.sentiment
        print_success("Working correctly")
        print_info(f"Test sentiment - Polarity: {sentiment.polarity}, Subjectivity: {sentiment.subjectivity}")
        
    except Exception as e:
        print_error(f"TextBlob test failed: {str(e)}")
        return False
    
    print_success("TextBlob is working correctly!")
    
    # Step 5: Check .env file
    print_header("Checking Environment Configuration")
    
    env_path = Path(__file__).parent / ".env"
    
    if not env_path.exists():
        print_warning(".env file not found!")
        print_info("Creating .env file from template...")
        
        template_path = Path(__file__).parent / "config.env.example"
        if template_path.exists():
            import shutil
            shutil.copy(template_path, env_path)
            print_success(".env file created")
            print_warning("Please edit .env and add your SERP_API_KEY")
        else:
            print_error("config.env.example not found!")
            print_info("Please manually create a .env file with SERP_API_KEY=your_key")
            return False
    else:
        print_success(".env file exists")
    
    # Step 6: Check SERP_API_KEY
    print_header("Checking SERPapi Configuration")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        serp_api_key = os.getenv("SERP_API_KEY")
        
        if not serp_api_key:
            print_error("SERP_API_KEY not found in .env file!")
            print_info("Please add your SERPapi key to the .env file:")
            print_info("  SERP_API_KEY=your_actual_key_here")
            print_info("\nGet your free API key at: https://serpapi.com/")
            return False
        
        if serp_api_key == "your_serpapi_key_here":
            print_error("SERP_API_KEY is set to the default placeholder value!")
            print_info("Please update your .env file with your actual SERPapi key")
            print_info("Get your free API key at: https://serpapi.com/")
            return False
        
        print_success("SERP_API_KEY is configured")
        print_info(f"API Key: {serp_api_key[:8]}...")
        
    except Exception as e:
        print_error(f"Error checking .env file: {str(e)}")
        return False
    
    # Step 7: Test SERPapi connection
    print_header("Testing SERPapi Connection")
    
    try:
        from serpapi import GoogleSearch
        
        print("Testing API connection with a sample search...", end=" ")
        
        params = {
            "api_key": serp_api_key,
            "engine": "google_finance",
            "q": "AAPL:NASDAQ"
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            print_error("API Error")
            print_info(f"Error: {results['error']}")
            print_info("Please check your API key and account status")
            return False
        
        print_success("Connection successful!")
        
        # Check for news results
        if "news_results" in results:
            num_articles = len(results["news_results"])
            print_success(f"Successfully fetched {num_articles} news articles for AAPL")
            
            # Show first article as example
            if num_articles > 0:
                first_article = results["news_results"][0]
                print_info("Sample article:")
                print(f"   Title: {first_article.get('title', 'N/A')[:60]}...")
                print(f"   Source: {first_article.get('source', 'N/A')}")
        else:
            print_warning("No news results found, but API connection is working")
        
        # Check account info
        if "search_metadata" in results:
            print_info("API search completed successfully")
        
    except Exception as e:
        print_error(f"SERPapi test failed: {str(e)}")
        print_info("Please verify your API key and network connection")
        return False
    
    print_success("SERPapi is working correctly!")
    
    # Step 8: Final summary
    print_header("Setup Complete!")
    
    print_success("All components are installed and configured!")
    print_info("\nNext steps:")
    print("  1. Run the Streamlit app: streamlit run Portfolio.py")
    print("  2. Navigate to 'Sentiment Analysis' in the sidebar")
    print("  3. Enter a stock symbol and click 'Analyze Sentiment'")
    print("\n📚 For more information, see:")
    print("  - documentations/SENTIMENT_ANALYSIS_README.md")
    print("  - https://serpapi.com/google-finance-api")
    
    print("\n💡 Tip: Free SERPapi accounts have a limit of 100 searches/month")
    print("   Each sentiment analysis uses 1-2 API calls depending on sources selected")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n" + "=" * 60)
            print("  ✅ Setup completed successfully!")
            print("=" * 60 + "\n")
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("  ❌ Setup encountered errors. Please address them and try again.")
            print("=" * 60 + "\n")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

