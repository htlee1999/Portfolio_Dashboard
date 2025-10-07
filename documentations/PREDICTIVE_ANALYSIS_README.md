# Predictive Analysis Documentation

## Overview

The Predictive Analysis page (`9_Predictive_Analysis.py`) implements three different machine learning approaches to predict stock prices and movements. This comprehensive ML framework provides both regression (price prediction) and classification (direction prediction) capabilities.

## Features

### 🤖 Three ML Models Implemented

#### 1. LSTM + RNN Hybrid Model 🧠
- **Architecture**: Combines Long Short-Term Memory networks with Recurrent Neural Networks
- **Strengths**: 
  - Excellent at capturing sequential patterns in time series data
  - Can learn complex non-linear relationships
  - Handles multiple input features simultaneously
- **Best for**: Short to medium-term predictions with complex patterns
- **Requirements**: TensorFlow installation

#### 2. Random Forest + Decision Trees 🌳
- **Architecture**: Ensemble of decision trees with individual Decision Tree backup
- **Strengths**:
  - Robust to overfitting
  - Provides feature importance rankings
  - Works well with mixed data types
  - Handles missing values well
- **Best for**: Understanding which factors drive price movements
- **Requirements**: scikit-learn (included in requirements.txt)

#### 3. Support Vector Machine (SVM) 📊
- **Architecture**: Finds optimal boundaries using kernel functions
- **Strengths**:
  - Effective in high-dimensional spaces
  - Memory efficient
  - Works well with small to medium datasets
  - Versatile (handles both regression and classification)
- **Best for**: Finding clear patterns and boundaries in data
- **Requirements**: scikit-learn (included in requirements.txt)

### 📊 Technical Indicators Used

The models utilize 23+ technical indicators:

**Price-based Indicators:**
- Simple Moving Averages (SMA_5, SMA_20)
- Exponential Moving Averages (EMA_12, EMA_26)
- Bollinger Bands (Upper, Middle, Lower, Percent)
- Price ratios (High/Low, Open/Close)

**Momentum Indicators:**
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- MACD Signal and Histogram
- Momentum and Rate of Change (ROC)

**Volume Indicators:**
- Volume Moving Average
- Volume Ratio
- On-Balance Volume patterns

**Volatility Indicators:**
- Price volatility (rolling standard deviation)
- Price change percentage

### 🎯 Model Evaluation Metrics

**Regression Metrics:**
- **RMSE (Root Mean Square Error)**: Lower is better - measures prediction accuracy
- **MAE (Mean Absolute Error)**: Lower is better - average prediction error
- **Directional Accuracy**: Higher is better - percentage of correct direction predictions

**Classification Metrics:**
- **Accuracy**: Percentage of correct predictions
- **Precision**: Weighted precision score

### 🔮 Future Predictions

The system automatically selects the best-performing model (lowest RMSE) and uses it to generate future price predictions for the specified number of days.

## Usage Instructions

### 1. Access the Page
- Navigate to "Predictive Analysis" in the sidebar
- Ensure you're logged in (authentication required)

### 2. Configure Analysis
- **Stock Symbol**: Select from sidebar or use default (AAPL)
- **Time Period**: Choose from 1 year to 5 years of historical data
- **Prediction Horizon**: Set how many days ahead to predict (1-30 days)

### 3. Adjust Model Parameters
- **LSTM Parameters**: Units for LSTM and RNN layers
- **Random Forest**: Number of estimators and max depth
- **SVM**: C parameter and gamma settings
- **General**: Lookback days for LSTM, test size percentage

### 4. Run Analysis
- Click "🚀 Run Predictive Analysis"
- Wait for models to train (progress indicators shown)
- View results and comparisons

### 5. Interpret Results
- **Model Comparison**: See which model performs best
- **Feature Importance**: Understand which indicators matter most
- **Future Predictions**: Get price forecasts from the best model
- **Visualizations**: Charts showing actual vs predicted values

## Technical Implementation

### Data Preparation
```python
def prepare_features(self):
    """Create technical indicators and features for ML models."""
    # 23+ technical indicators created
    # Targets: next day price, direction, percentage change
    # Returns clean dataset with all features
```

### Model Classes
```python
class LSTMRNNModel:
    """LSTM + RNN Hybrid Model for stock prediction."""
    # Sequential model with LSTM -> RNN -> LSTM -> Dense layers
    # Early stopping and dropout for regularization

class RandomForestModel:
    """Random Forest + Decision Trees Ensemble Model."""
    # Ensemble of RF and DT models
    # Majority voting for classification, averaging for regression

class SVMModel:
    """Support Vector Machine Model."""
    # RBF kernel with feature scaling
    # Supports both regression and classification
```

### Evaluation Functions
```python
def evaluate_regression(y_true, y_pred, model_name):
    """Comprehensive regression evaluation."""
    # RMSE, MAE, Directional Accuracy

def evaluate_classification(y_true, y_pred, model_name):
    """Classification performance metrics."""
    # Accuracy, Precision
```

## Dependencies

### Required Libraries
- **scikit-learn**: Random Forest, SVM, evaluation metrics
- **pandas**: Data manipulation
- **numpy**: Numerical operations
- **yfinance**: Stock data fetching
- **plotly**: Interactive visualizations
- **streamlit**: Web interface

### Optional Libraries
- **tensorflow**: Required for LSTM+RNN model
- **keras**: High-level neural network API

### Installation
```bash
pip install -r requirements.txt
```

## Performance Considerations

### Model Training Time
- **Random Forest**: Fastest (~5-10 seconds)
- **SVM**: Medium (~10-30 seconds)
- **LSTM+RNN**: Slowest (~30-60 seconds)

### Memory Usage
- **Random Forest**: Low memory usage
- **SVM**: Medium memory usage
- **LSTM+RNN**: Higher memory usage (GPU recommended)

### Accuracy Expectations
- **Random Forest**: Typically best for feature importance and general accuracy
- **SVM**: Good for clear pattern recognition
- **LSTM+RNN**: Best for complex sequential patterns (when TensorFlow available)

## Troubleshooting

### Common Issues

1. **TensorFlow Import Errors**
   - Solution: Install TensorFlow or use Random Forest/SVM only
   - The system gracefully handles missing TensorFlow

2. **Memory Issues with LSTM**
   - Solution: Reduce lookback days or batch size
   - Use smaller datasets for testing

3. **Poor Prediction Accuracy**
   - Solution: Try different time periods
   - Adjust model parameters
   - Check data quality

4. **Slow Performance**
   - Solution: Reduce test size percentage
   - Use fewer Random Forest estimators
   - Consider shorter time periods

### Error Handling
- All models include comprehensive error handling
- Graceful degradation when dependencies are missing
- Clear error messages for debugging

## Best Practices

### Model Selection
1. **Start with Random Forest** for baseline performance
2. **Use SVM** for pattern recognition tasks
3. **Try LSTM+RNN** for complex sequential data (if TensorFlow available)

### Parameter Tuning
1. **Random Forest**: Start with 100 estimators, depth 10
2. **SVM**: Use C=1.0, gamma='scale' as defaults
3. **LSTM+RNN**: Start with 50 LSTM units, 30 RNN units

### Data Quality
1. **Use at least 1 year** of historical data
2. **Check for missing values** in technical indicators
3. **Validate stock symbols** before analysis

## Future Enhancements

### Planned Features
- **More ML Models**: XGBoost, LightGBM, ARIMA
- **Ensemble Methods**: Voting, stacking, blending
- **Real-time Predictions**: Live data integration
- **Model Persistence**: Save/load trained models
- **Hyperparameter Optimization**: Automated tuning
- **Cross-validation**: More robust evaluation

### Advanced Features
- **Multi-timeframe Analysis**: Different prediction horizons
- **Sector Analysis**: Industry-specific models
- **Risk Metrics**: VaR, Sharpe ratio integration
- **Portfolio Optimization**: ML-driven allocation

## Disclaimer

⚠️ **Important**: This predictive analysis is for educational and research purposes only. Past performance does not guarantee future results. Always consider fundamental analysis, market conditions, and risk management. Never rely solely on ML predictions for investment decisions. Practice with paper trading before using real money.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all dependencies are installed
3. Test with the provided sample data
4. Review the model parameters and settings

---

*Last updated: January 2025*
