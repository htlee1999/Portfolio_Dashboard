import os
# CRITICAL: Set threading environment variables BEFORE any other imports
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMBA_NUM_THREADS'] = '1'
os.environ['NUMBA_THREADING_LAYER'] = 'safe'

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Machine Learning Libraries
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.svm import SVR, SVC
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score, precision_score, classification_report

# TensorFlow/LSTM functionality removed for stability

from app_utils import setup_page, inject_css, init_session_state, create_sidebar, get_stock_data, format_currency
from auth_utils import show_user_menu


class PredictiveAnalysis:
    """Comprehensive predictive analysis using scikit-learn models."""
    
    def __init__(self, data):
        """
        Initialize with price data.
        
        Args:
            data (pd.DataFrame): OHLCV data with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.prices = data['Close']
        self.volumes = data['Volume'] if 'Volume' in data.columns else None
        
    def calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def prepare_features(self):
        """Create technical indicators and features for ML models."""
        df = self.data.copy()
        
        # Price-based indicators
        df['SMA_5'] = df['Close'].rolling(window=5).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Percent'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # Price ratios
        df['High_Low_Ratio'] = df['High'] / df['Low']
        df['Open_Close_Ratio'] = df['Open'] / df['Close']
        
        # Momentum indicators
        df['RSI'] = self.calculate_rsi(df['Close'])
        
        # MACD
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Volume indicators
        if self.volumes is not None:
            df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        else:
            df['Volume_SMA'] = 1
            df['Volume_Ratio'] = 1
        
        # Price change indicators
        df['Price_Change_1d'] = df['Close'].pct_change(1)
        df['Price_Change_5d'] = df['Close'].pct_change(5)
        df['Price_Change_20d'] = df['Close'].pct_change(20)
        
        # Volatility
        df['Volatility'] = df['Close'].rolling(window=20).std()
        
        # Drop rows with NaN values
        df = df.dropna()
        
        return df


class RandomForestModel:
    """Random Forest + Decision Trees Ensemble Model."""
    
    def __init__(self, task='regression', n_estimators=100, max_depth=10):
        self.task = task
        if task == 'regression':
            self.rf_model = RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42,
                n_jobs=1  # Changed from -1 to avoid threading conflicts in Streamlit
            )
            self.dt_model = DecisionTreeRegressor(
                max_depth=max_depth,
                random_state=42
            )
        else:
            self.rf_model = RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42,
                n_jobs=1  # Changed from -1 to avoid threading conflicts in Streamlit
            )
            self.dt_model = DecisionTreeClassifier(
                max_depth=max_depth,
                random_state=42
            )
    
    def fit(self, X_train, y_train):
        try:
            self.rf_model.fit(X_train, y_train)
            self.dt_model.fit(X_train, y_train)
        except Exception as e:
            st.error(f"Error training Random Forest model: {e}")
            raise
    
    def predict(self, X_test):
        rf_pred = self.rf_model.predict(X_test)
        dt_pred = self.dt_model.predict(X_test)
        
        # Ensemble prediction (average)
        if self.task == 'regression':
            return (rf_pred + dt_pred) / 2
        else:
            # Majority voting for classification
            combined_pred = []
            for rf, dt in zip(rf_pred, dt_pred):
                combined_pred.append(1 if (rf + dt) >= 1 else 0)
            return np.array(combined_pred)
    
    def get_feature_importance(self):
        return self.rf_model.feature_importances_


class SVMModel:
    """Support Vector Machine Model."""
    
    def __init__(self, task='regression', kernel='rbf', C=1.0, gamma='scale'):
        self.task = task
        if task == 'regression':
            self.model = SVR(kernel=kernel, C=C, gamma=gamma)
        else:
            self.model = SVC(kernel=kernel, C=C, gamma=gamma, probability=True)
    
    def fit(self, X_train, y_train):
        try:
            # Scale features for SVM
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            self.model.fit(X_train_scaled, y_train)
        except Exception as e:
            st.error(f"Error training SVM model: {e}")
            raise
    
    def predict(self, X_test):
        X_test_scaled = self.scaler.transform(X_test)
        return self.model.predict(X_test_scaled)


def evaluate_regression(y_true, y_pred, model_name):
    """Evaluate regression model performance."""
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    
    # Directional accuracy
    actual_direction = np.diff(y_true) > 0
    pred_direction = np.diff(y_pred) > 0
    directional_accuracy = accuracy_score(actual_direction, pred_direction)
    
    return {
        'RMSE': rmse,
        'MAE': mae,
        'Directional_Accuracy': directional_accuracy
    }


def evaluate_classification(y_true, y_pred, model_name):
    """Evaluate classification model performance."""
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average='weighted')
    
    return {
        'Accuracy': accuracy,
        'Precision': precision
    }


def create_prediction_chart(actual, predicted, title, dates):
    """Create interactive prediction chart."""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=actual,
        mode='lines',
        name='Actual',
        line=dict(color='blue')
    ))
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=predicted,
        mode='lines',
        name='Predicted',
        line=dict(color='red')
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Price',
        hovermode='x unified'
    )
    
    return fig


def create_feature_importance_chart(feature_names, importance_scores):
    """Create feature importance chart."""
    # Sort features by importance
    sorted_indices = np.argsort(importance_scores)[::-1]
    sorted_features = [feature_names[i] for i in sorted_indices]
    sorted_importance = importance_scores[sorted_indices]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=sorted_importance,
        y=sorted_features,
        orientation='h'
    ))
    
    fig.update_layout(
        title='Feature Importance',
        xaxis_title='Importance Score',
        yaxis_title='Features'
    )
    
    return fig


def main():
    """Main predictive analysis page."""
    try:
        setup_page()
        inject_css()
        init_session_state()
        create_sidebar()
        show_user_menu()
        
        # Check authentication
        if not st.session_state.get("authenticated", False):
            st.warning("🔐 Please log in to access the Predictive Analysis page")
            st.info("Use the Login page in the sidebar to authenticate")
            return
        
        st.markdown('<h1 class="main-header">🤖 Predictive Analysis</h1>', unsafe_allow_html=True)
        
        # Add explanation section
        with st.expander("📚 Machine Learning Models Guide", expanded=False):
            st.markdown("""
            ### Understanding Machine Learning for Stock Prediction
            
            This page implements two proven machine learning approaches for stock prediction:
            """)
            
            st.markdown("""
            #### 1. Random Forest + Decision Trees 🌳
            **What it does:** Uses an ensemble of decision trees to make predictions, combining Random Forest with individual Decision Trees.
            
            **Strengths:**
            - Robust to overfitting
            - Provides feature importance rankings
            - Works well with mixed data types
            - Handles missing values well
            
            **Best for:** Understanding which factors drive price movements
            """)
            
            st.markdown("""
            #### 2. Support Vector Machine (SVM) 📊
            **What it does:** Finds optimal boundaries between different classes/values using kernel functions.
            
            **Strengths:**
            - Effective in high-dimensional spaces
            - Memory efficient
            - Works well with small to medium datasets
            - Versatile (can handle both regression and classification)
            
            **Best for:** Finding clear patterns and boundaries in data
            """)
            
            st.markdown("""
            ### 🎛️ Model Parameters Guide
            
            Understanding and adjusting these parameters can significantly improve prediction accuracy:
            
            #### Random Forest Estimators (50-200, default: 100)
            - **What it is:** Number of decision trees in the Random Forest ensemble
            - **Higher values (150-200):**
              - ✅ More stable and accurate predictions
              - ✅ Better generalization
              - ❌ Slower training time
              - **Use when:** You have plenty of data and want maximum accuracy
            - **Lower values (50-80):**
              - ✅ Faster training
              - ❌ May be less stable
              - **Use when:** You need quick results or have limited data
            - **Recommendation:** Start with 100, increase to 150-200 for important decisions
            
            #### Max Depth (5-20, default: 10)
            - **What it is:** Maximum depth of each decision tree
            - **Higher depth (15-20):**
              - ✅ Can capture complex patterns
              - ❌ Risk of overfitting (memorizing noise)
              - **Use when:** Stock has complex, volatile patterns
            - **Lower depth (5-8):**
              - ✅ Prevents overfitting
              - ✅ More generalizable
              - ❌ May miss subtle patterns
              - **Use when:** Stock has stable, predictable trends
            - **Recommendation:** Start with 10, reduce to 7-8 if you see overfitting (perfect train, poor test results)
            
            #### SVM C Parameter (0.1-100, default: 1.0)
            - **What it is:** Regularization parameter controlling the trade-off between smooth decision boundary and classifying training points correctly
            - **Higher C (10-100):**
              - ✅ Tries to classify all training points correctly
              - ❌ May overfit to training data
              - **Use when:** You have high-quality, clean data
            - **Lower C (0.1-1.0):**
              - ✅ More tolerant to misclassifications
              - ✅ Better generalization
              - **Use when:** Data is noisy or you want robust predictions
            - **Recommendation:** Start with 1.0, increase cautiously if underfitting
            
            #### SVM Gamma (scale/auto/0.001-1.0, default: scale)
            - **What it is:** Defines how far the influence of a single training example reaches
            - **'scale' (Recommended):** 1 / (n_features * X.var()) - automatic scaling
            - **'auto':** 1 / n_features - simpler automatic scaling
            - **High gamma (0.1-1.0):**
              - ✅ Close fit to training data
              - ❌ May overfit
              - **Use when:** Decision boundary should be very specific
            - **Low gamma (0.001-0.01):**
              - ✅ Smoother decision boundary
              - ✅ Better generalization
              - **Use when:** You want robust, stable predictions
            - **Recommendation:** Use 'scale' for most cases, try 'auto' if 'scale' doesn't work well
            
            #### Test Size % (10-40, default: 20)
            - **What it is:** Percentage of data reserved for testing (not used in training)
            - **Larger test size (30-40%):**
              - ✅ More reliable evaluation
              - ✅ Better estimate of real-world performance
              - ❌ Less data for training
              - **Use when:** You have lots of data (2+ years)
            - **Smaller test size (10-20%):**
              - ✅ More data for training
              - ❌ Less reliable evaluation
              - **Use when:** You have limited data (< 6 months)
            - **Recommendation:** Use 20% as standard, increase to 30% if you have 2+ years of data
            
            ### 📊 Recommended Parameter Combinations
            
            #### For Stable, Blue-Chip Stocks (e.g., AAPL, MSFT)
            ```
            Random Forest Estimators: 100-150
            Max Depth: 8-10
            SVM C: 1.0
            SVM Gamma: scale
            Test Size: 20%
            ```
            
            #### For Volatile Tech Stocks (e.g., TSLA, NVDA)
            ```
            Random Forest Estimators: 150-200
            Max Depth: 12-15
            SVM C: 0.5-1.0
            SVM Gamma: scale or auto
            Test Size: 25-30%
            ```
            
            #### For Limited Data (< 6 months)
            ```
            Random Forest Estimators: 80-100
            Max Depth: 6-8
            SVM C: 0.5
            SVM Gamma: scale
            Test Size: 15%
            ```
            
            #### For Maximum Accuracy (with plenty of data)
            ```
            Random Forest Estimators: 180-200
            Max Depth: 10-12
            SVM C: 1.0
            SVM Gamma: scale
            Test Size: 30%
            ```
            
            ### 🔍 How to Tune Parameters
            
            1. **Start with defaults** - Run analysis with default parameters
            2. **Check for overfitting:**
               - If Directional Accuracy is very high (>80%) but predictions look unrealistic → Reduce Max Depth or C
               - If predictions follow training data too closely → Reduce complexity
            3. **Check for underfitting:**
               - If Directional Accuracy is very low (<50%) → Increase Max Depth or estimators
               - If model seems too simple → Increase complexity
            4. **Compare models:**
               - If Random Forest >> SVM → Complex patterns, keep higher complexity
               - If SVM >> Random Forest → Clear boundaries, linear patterns
            5. **Iterate:**
               - Adjust one parameter at a time
               - Compare RMSE and Directional Accuracy
               - Keep the configuration with best test performance
            
            ### 🎯 How to Interpret Results
            
            **RMSE (Root Mean Square Error):** Lower is better - measures prediction accuracy in price units
            - < 2% of stock price: Excellent
            - 2-5% of stock price: Good
            - > 5% of stock price: Fair, consider adjusting parameters
            
            **MAE (Mean Absolute Error):** Lower is better - average prediction error
            - Easier to interpret than RMSE (in actual dollars)
            - Should be lower than RMSE
            
            **Directional Accuracy:** Higher is better - percentage of correct direction predictions
            - > 60%: Good (better than random)
            - > 70%: Excellent
            - > 80%: Be cautious - may be overfitting
            
            **Feature Importance:** Shows which technical indicators most influence predictions
            - High importance (> 0.1): Primary drivers
            - Use this to understand what moves the stock
            
            ### ⚠️ Important Disclaimers
            - **Past performance doesn't guarantee future results**
            - **Use predictions as one tool among many for decision making**
            - **Always consider fundamental analysis and market conditions**
            - **Practice with paper trading before using real money**
            - **Higher complexity doesn't always mean better predictions**
            - **Watch for overfitting - models that are too perfect on training data**
            """)
        
        # Stock selection
        st.subheader("📈 Stock Selection")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbol = st.session_state.get("selected_stock", "AAPL")
            symbol = st.text_input("Stock Symbol", value=symbol, help="Enter a valid stock symbol (e.g., AAPL, MSFT, GOOGL)")
        
        with col2:
            period_options = {
                "1 Month": "1mo",
                "3 Months": "3mo", 
                "6 Months": "6mo",
                "1 Year": "1y",
                "2 Years": "2y",
                "5 Years": "5y"
            }
            selected_period = st.selectbox("Data Period", list(period_options.keys()), index=3)
            period = period_options[selected_period]
        
        with col3:
            prediction_days = st.slider("Prediction Horizon (days)", 1, 30, 5)
        
        # Model parameters
        st.subheader("Model Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rf_estimators = st.slider("Random Forest Estimators", 50, 200, 100)
            rf_depth = st.slider("Max Depth", 5, 20, 10)
        with col2:
            svm_c = st.slider("SVM C Parameter", 0.1, 100.0, 1.0)
            svm_gamma = st.selectbox("SVM Gamma", ['scale', 'auto', 0.001, 0.01, 0.1, 1.0])
        with col3:
            test_size = st.slider("Test Size %", 10, 40, 20)
        
        # Fetch data and run analysis
        analyze_clicked = st.button("🚀 Run Predictive Analysis", type="primary")
        auto_analyze = st.session_state.get('auto_analyze', False)
        
        if analyze_clicked or auto_analyze:
            if not symbol:
                st.error("Please enter a stock symbol")
                return
            
            with st.spinner("Fetching stock data..."):
                try:
                    data, info = get_stock_data(symbol, period)
                    if data is None or data.empty:
                        st.error(f"Could not fetch data for {symbol}")
                        return
                except Exception as e:
                    st.error(f"Error fetching data: {str(e)}")
                    return
            
            # Initialize predictive analysis
            pa = PredictiveAnalysis(data)
            
            with st.spinner("Preparing features..."):
                df_with_features = pa.prepare_features()
            
            if df_with_features.empty:
                st.error("Not enough data to perform analysis")
                return
            
            st.success(f"✅ Analysis ready for {symbol}")
            st.info(f"📊 Dataset: {len(df_with_features)} samples with {len(df_with_features.columns)} features")
            
            # Prepare features and targets together to ensure matching indices
            feature_cols = [col for col in df_with_features.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']]
            
            # Create a working dataframe with features and targets
            df_ml = df_with_features.copy()
            
            # Add target columns
            df_ml['Target_Price'] = df_ml['Close'].shift(-1)  # Next day's price
            df_ml['Target_Direction'] = (df_ml['Close'].shift(-1) > df_ml['Close']).astype(int)  # Price up/down
            
            # Drop rows with NaN in targets (last row will have NaN)
            df_ml = df_ml.dropna(subset=['Target_Price', 'Target_Direction'])
            
            # Now extract X and y with guaranteed matching lengths
            X = df_ml[feature_cols].values
            y_regression = df_ml['Target_Price'].values
            y_classification = df_ml['Target_Direction'].values
            
            # Verify lengths match
            assert len(X) == len(y_regression) == len(y_classification), \
                f"Length mismatch: X={len(X)}, y_reg={len(y_regression)}, y_class={len(y_classification)}"
            
            # Split data
            split_idx = int((1 - test_size/100) * len(X))
            
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_reg_train, y_reg_test = y_regression[:split_idx], y_regression[split_idx:]
            y_class_train, y_class_test = y_classification[:split_idx], y_classification[split_idx:]
            
            # Store results
            results = {}
            
            # Prepare dates for plotting (use test set dates)
            dates = df_ml.index[split_idx:split_idx + len(y_reg_test)]
            
            # =============================================================================
            # MODEL 1: RANDOM FOREST + DECISION TREES
            # =============================================================================
            st.subheader("🌳 Random Forest + Decision Trees")
            
            try:
                # Regression task
                rf_reg = RandomForestModel(task='regression', n_estimators=rf_estimators, max_depth=rf_depth)
                
                with st.spinner("Training Random Forest model..."):
                    rf_reg.fit(X_train, y_reg_train)
                
                rf_reg_pred = rf_reg.predict(X_test)
                
                # Classification task
                rf_class = RandomForestModel(task='classification', n_estimators=rf_estimators, max_depth=rf_depth)
                rf_class.fit(X_train, y_class_train)
                rf_class_pred = rf_class.predict(X_test)
                
                # Evaluate Random Forest
                rf_reg_results = evaluate_regression(y_reg_test, rf_reg_pred, "Random Forest")
                rf_class_results = evaluate_classification(y_class_test, rf_class_pred, "Random Forest")
                results['Random Forest'] = rf_reg_results
                
                # Display results
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("RMSE", f"{rf_reg_results['RMSE']:.4f}")
                with col2:
                    st.metric("MAE", f"{rf_reg_results['MAE']:.4f}")
                with col3:
                    st.metric("Directional Accuracy", f"{rf_reg_results['Directional_Accuracy']:.2%}")
                with col4:
                    st.metric("Training Samples", len(X_train))
                
                # Plot predictions
                st.plotly_chart(
                    create_prediction_chart(y_reg_test, rf_reg_pred, "Random Forest Predictions vs Actual", dates),
                    use_container_width=True
                )
                
                # Feature importance
                importance = rf_reg.get_feature_importance()
                st.plotly_chart(
                    create_feature_importance_chart(feature_cols, importance),
                    use_container_width=True
                )
                
                # Feature importance table
                feature_importance_df = pd.DataFrame({
                    'Feature': feature_cols,
                    'Importance': importance
                }).sort_values('Importance', ascending=False)
                
                st.write("**Feature Importance Ranking:**")
                st.dataframe(feature_importance_df.head(10), use_container_width=True)
                
            except Exception as e:
                st.error(f"Error training Random Forest model: {str(e)}")
                results['Random Forest'] = None
            
            # =============================================================================
            # MODEL 2: SUPPORT VECTOR MACHINE
            # =============================================================================
            st.subheader("📊 Support Vector Machine")
            
            try:
                # Regression task
                svm_reg = SVMModel(task='regression', kernel='rbf', C=svm_c, gamma=svm_gamma)
                
                with st.spinner("Training SVM model..."):
                    svm_reg.fit(X_train, y_reg_train)
                
                svm_reg_pred = svm_reg.predict(X_test)
                
                # Classification task
                svm_class = SVMModel(task='classification', kernel='rbf', C=svm_c, gamma=svm_gamma)
                svm_class.fit(X_train, y_class_train)
                svm_class_pred = svm_class.predict(X_test)
                
                # Evaluate SVM
                svm_reg_results = evaluate_regression(y_reg_test, svm_reg_pred, "SVM")
                svm_class_results = evaluate_classification(y_class_test, svm_class_pred, "SVM")
                results['SVM'] = svm_reg_results
                
                # Display results
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("RMSE", f"{svm_reg_results['RMSE']:.4f}")
                with col2:
                    st.metric("MAE", f"{svm_reg_results['MAE']:.4f}")
                with col3:
                    st.metric("Directional Accuracy", f"{svm_reg_results['Directional_Accuracy']:.2%}")
                with col4:
                    st.metric("Training Samples", len(X_train))
                
                # Plot predictions
                st.plotly_chart(
                    create_prediction_chart(y_reg_test, svm_reg_pred, "SVM Predictions vs Actual", dates),
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Error training SVM model: {str(e)}")
                results['SVM'] = None
            
            # =============================================================================
            # RESULTS SUMMARY
            # =============================================================================
            st.subheader("📊 Model Comparison")
            
            if results:
                comparison_data = []
                for model_name, result in results.items():
                    if result:
                        comparison_data.append({
                            'Model': model_name,
                            'RMSE': result['RMSE'],
                            'MAE': result['MAE'],
                            'Directional Accuracy': result['Directional_Accuracy']
                        })
                
                if comparison_data:
                    comparison_df = pd.DataFrame(comparison_data)
                    st.dataframe(comparison_df, use_container_width=True)
                    
                    # Find best model
                    best_model = comparison_df.loc[comparison_df['RMSE'].idxmin()]
                    st.success(f"🏆 Best performing model: **{best_model['Model']}** (RMSE: {best_model['RMSE']:.4f})")
        
        else:
            st.info("👆 Click 'Run Predictive Analysis' to begin machine learning analysis")
            
            # Show sample of what the analysis will include
            st.subheader("🔍 What This Analysis Will Provide")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **🌳 Random Forest**
                - Feature importance analysis
                - Robust ensemble predictions
                - Overfitting resistance
                """)
            
            with col2:
                st.markdown("""
                **📊 SVM Model**
                - Optimal boundary finding
                - High-dimensional effectiveness
                - Clear pattern recognition
                """)

    except Exception as e:
        st.error(f"❌ Error in Predictive Analysis: {str(e)}")
        st.error("This might be due to threading conflicts. Please try refreshing the page.")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()