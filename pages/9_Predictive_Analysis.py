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
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.svm import SVR, SVC
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score, precision_score, classification_report
import joblib

# Deep Learning Libraries
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, SimpleRNN
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping
    TENSORFLOW_AVAILABLE = True
except ImportError:
    # Define dummy classes for when TensorFlow is not available
    class Sequential:
        def __init__(self, *args, **kwargs):
            raise ImportError("TensorFlow is required for LSTM+RNN model")
    
    class LSTM:
        def __init__(self, *args, **kwargs):
            raise ImportError("TensorFlow is required for LSTM+RNN model")
    
    class Dense:
        def __init__(self, *args, **kwargs):
            raise ImportError("TensorFlow is required for LSTM+RNN model")
    
    class Dropout:
        def __init__(self, *args, **kwargs):
            raise ImportError("TensorFlow is required for LSTM+RNN model")
    
    class SimpleRNN:
        def __init__(self, *args, **kwargs):
            raise ImportError("TensorFlow is required for LSTM+RNN model")
    
    class Adam:
        def __init__(self, *args, **kwargs):
            raise ImportError("TensorFlow is required for LSTM+RNN model")
    
    class EarlyStopping:
        def __init__(self, *args, **kwargs):
            raise ImportError("TensorFlow is required for LSTM+RNN model")
    
    TENSORFLOW_AVAILABLE = False

from app_utils import setup_page, inject_css, init_session_state, create_sidebar, get_stock_data, format_currency
from auth_utils import show_user_menu


class PredictiveAnalysis:
    """Comprehensive predictive analysis using three ML approaches."""
    
    def __init__(self, data):
        """
        Initialize with price data.
        
        Args:
            data (pd.DataFrame): OHLCV data with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.prices = data['Close']
        self.volumes = data['Volume'] if 'Volume' in data.columns else None
        
    def prepare_features(self):
        """Create technical indicators and features for ML models."""
        df = self.data.copy()
        
        # Technical indicators
        df['SMA_5'] = df['Close'].rolling(window=5).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        df['RSI'] = self.calculate_rsi(df['Close'])
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Percent'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # Price ratios and volatility
        df['High_Low_Ratio'] = df['High'] / df['Low']
        df['Open_Close_Ratio'] = df['Open'] / df['Close']
        df['Volatility'] = df['Close'].rolling(window=10).std()
        df['Price_Change'] = df['Close'].pct_change()
        df['Volume_MA'] = df['Volume'].rolling(window=10).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # Momentum indicators
        df['Momentum'] = df['Close'] - df['Close'].shift(5)
        df['ROC'] = df['Close'].pct_change(periods=10) * 100
        
        # Targets
        df['Target_Price'] = df['Close'].shift(-1)  # Next day closing price
        df['Target_Class'] = (df['Close'].shift(-1) > df['Close']).astype(int)  # 1 if up, 0 if down
        df['Target_Change'] = df['Close'].shift(-1) / df['Close'] - 1  # Percentage change
        
        return df.dropna()
    
    def calculate_rsi(self, prices, window=14):
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        avg_gains = gains.ewm(span=window, min_periods=window).mean()
        avg_losses = losses.ewm(span=window, min_periods=window).mean()
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def prepare_lstm_data(self, data, lookback=60):
        """Prepare data for LSTM model."""
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(data)
        
        X, y = [], []
        for i in range(lookback, len(scaled_data)):
            X.append(scaled_data[i-lookback:i])
            y.append(scaled_data[i])
        
        return np.array(X), np.array(y), scaler


class LSTMRNNModel:
    """LSTM + RNN Hybrid Model for stock prediction."""
    
    def __init__(self, input_shape, lstm_units=50, rnn_units=30):
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required for LSTM+RNN model")
            
        self.model = Sequential([
            LSTM(lstm_units, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            SimpleRNN(rnn_units, return_sequences=True),
            Dropout(0.2),
            LSTM(lstm_units//2, return_sequences=False),
            Dropout(0.2),
            Dense(25, activation='relu'),
            Dense(1)
        ])
        
        self.model.compile(
            optimizer=Adam(learning_rate=0.001), 
            loss='mean_squared_error',
            metrics=['mae']
        )
    
    def fit(self, X_train, y_train, epochs=50, batch_size=32, validation_split=0.2):
        """Train the model with early stopping."""
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=0,
            shuffle=False,
            callbacks=[early_stopping]
        )
        return history
    
    def predict(self, X_test):
        return self.model.predict(X_test, verbose=0)


class RandomForestModel:
    """Random Forest + Decision Trees Ensemble Model."""
    
    def __init__(self, task='regression', n_estimators=100, max_depth=10):
        self.task = task
        if task == 'regression':
            self.rf_model = RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42,
                n_jobs=-1
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
                n_jobs=-1
            )
            self.dt_model = DecisionTreeClassifier(
                max_depth=max_depth,
                random_state=42
            )
    
    def fit(self, X_train, y_train):
        self.rf_model.fit(X_train, y_train)
        self.dt_model.fit(X_train, y_train)
    
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
        # Scale features for SVM
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_train_scaled, y_train)
    
    def predict(self, X_test):
        X_test_scaled = self.scaler.transform(X_test)
        return self.model.predict(X_test_scaled)


def evaluate_regression(y_true, y_pred, model_name):
    """Evaluate regression model performance."""
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    
    # Calculate directional accuracy
    true_direction = np.diff(y_true) > 0
    pred_direction = np.diff(y_pred) > 0
    directional_accuracy = np.mean(true_direction == pred_direction)
    
    return {
        'MSE': mse,
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


def create_prediction_chart(y_true, y_pred, title, dates=None):
    """Create prediction vs actual chart."""
    fig = go.Figure()
    
    if dates is not None:
        x_axis = dates
    else:
        x_axis = list(range(len(y_true)))
    
    # Actual values
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=y_true,
        mode='lines',
        name='Actual',
        line=dict(color='blue', width=2),
        opacity=0.8
    ))
    
    # Predicted values
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=y_pred,
        mode='lines',
        name='Predicted',
        line=dict(color='red', width=2),
        opacity=0.8
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Price",
        height=400,
        showlegend=True
    )
    
    return fig


def create_model_comparison_chart(results_df):
    """Create model comparison chart."""
    fig = go.Figure()
    
    # RMSE comparison
    fig.add_trace(go.Bar(
        x=results_df['Model'],
        y=results_df['RMSE'],
        name='RMSE',
        marker_color='lightblue',
        text=results_df['RMSE'].round(4),
        textposition='auto'
    ))
    
    fig.update_layout(
        title="Model Performance Comparison (RMSE)",
        xaxis_title="Model",
        yaxis_title="RMSE",
        height=400
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
        orientation='h',
        marker_color='lightgreen',
        text=sorted_importance.round(4),
        textposition='auto'
    ))
    
    fig.update_layout(
        title="Feature Importance (Random Forest)",
        xaxis_title="Importance Score",
        yaxis_title="Features",
        height=500
    )
    
    return fig


def main():
    """Main predictive analysis page."""
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
    
    # Show TensorFlow availability warning
    if not TENSORFLOW_AVAILABLE:
        st.warning("⚠️ TensorFlow not available. LSTM+RNN model will be disabled. Please install TensorFlow to use all features.")
    
    # Add explanation section
    with st.expander("📚 Machine Learning Models Guide", expanded=False):
        st.markdown("""
        ### Understanding Machine Learning for Stock Prediction
        
        This page implements three different machine learning approaches to predict stock prices:
        """)
        
        st.markdown("""
        #### 1. LSTM + RNN Hybrid Model 🧠
        **What it does:** Combines Long Short-Term Memory networks with Recurrent Neural Networks to capture both long-term dependencies and recent patterns.
        
        **Strengths:**
        - Excellent at capturing sequential patterns in time series data
        - Can learn complex non-linear relationships
        - Handles multiple input features simultaneously
        
        **Best for:** Short to medium-term predictions with complex patterns
        """)
        
        st.markdown("""
        #### 2. Random Forest + Decision Trees 🌳
        **What it does:** Uses an ensemble of decision trees to make predictions, combining Random Forest with individual Decision Trees.
        
        **Strengths:**
        - Robust to overfitting
        - Provides feature importance rankings
        - Works well with mixed data types
        - Handles missing values well
        
        **Best for:** Understanding which factors drive price movements
        """)
        
        st.markdown("""
        #### 3. Support Vector Machine (SVM) 📊
        **What it does:** Finds optimal boundaries between different classes/values using kernel functions.
        
        **Strengths:**
        - Effective in high-dimensional spaces
        - Memory efficient
        - Works well with small to medium datasets
        - Versatile (can handle both regression and classification)
        
        **Best for:** Finding clear patterns and boundaries in data
        """)
        
        st.markdown("""
        ### 🎯 How to Interpret Results
        
        **RMSE (Root Mean Square Error):** Lower is better - measures prediction accuracy
        **MAE (Mean Absolute Error):** Lower is better - average prediction error
        **Directional Accuracy:** Higher is better - percentage of correct direction predictions
        **Feature Importance:** Shows which technical indicators most influence predictions
        
        ### ⚠️ Important Disclaimers
        - **Past performance doesn't guarantee future results**
        - **Use predictions as one tool among many for decision making**
        - **Always consider fundamental analysis and market conditions**
        - **Practice with paper trading before using real money**
        """)
    
    # Get selected symbol from sidebar
    symbol = st.session_state.get("selected_stock", "AAPL")
    
    # Handle quick analyze from sidebar button
    if 'quick_analyze' in st.session_state:
        symbol = st.session_state.quick_analyze
        del st.session_state.quick_analyze
        st.session_state.auto_analyze = True
    
    # Handle quick predictive analysis from sidebar button
    if 'quick_predictive' in st.session_state:
        symbol = st.session_state.quick_predictive
        del st.session_state.quick_predictive
        st.session_state.auto_analyze = True
    
    # Analysis parameters
    st.subheader("Analysis Settings")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.info(f"**Selected Stock:** {symbol}")
    with col2:
        # Time period selection
        period_options = {
            "1 Year": "1y",
            "2 Years": "2y", 
            "3 Years": "3y",
            "5 Years": "5y"
        }
        selected_period = st.selectbox("Time Period", list(period_options.keys()))
        period = period_options[selected_period]
    with col3:
        prediction_days = st.slider("Prediction Horizon (days)", 1, 30, 5)
    
    # Model parameters
    st.subheader("Model Parameters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        lstm_units = st.slider("LSTM Units", 20, 100, 50)
        rnn_units = st.slider("RNN Units", 10, 50, 30)
    with col2:
        rf_estimators = st.slider("Random Forest Estimators", 50, 200, 100)
        rf_depth = st.slider("Max Depth", 5, 20, 10)
    with col3:
        svm_c = st.slider("SVM C Parameter", 0.1, 100.0, 1.0)
        svm_gamma = st.selectbox("SVM Gamma", ['scale', 'auto', 0.001, 0.01, 0.1, 1.0])
    with col4:
        lookback_days = st.slider("LSTM Lookback Days", 30, 120, 60)
        test_size = st.slider("Test Size %", 10, 40, 20)
    
    # Fetch data and run analysis
    analyze_clicked = st.button("🚀 Run Predictive Analysis", type="primary")
    auto_analyze = st.session_state.get('auto_analyze', False)
    
    if analyze_clicked or auto_analyze:
        if auto_analyze:
            del st.session_state.auto_analyze
            
        with st.spinner(f"Fetching data for {symbol} and training models..."):
            try:
                # Fetch stock data
                data, info = get_stock_data(symbol, period)
                
                if data is None or data.empty:
                    st.error(f"Could not fetch data for {symbol}. Please check the symbol and try again.")
                    return
                
                # Initialize predictive analysis
                pa = PredictiveAnalysis(data)
                
                # Prepare features
                df_with_features = pa.prepare_features()
                
                # Define feature columns
                feature_cols = [
                    'Open', 'High', 'Low', 'Volume', 'SMA_5', 'SMA_20', 'EMA_12', 'EMA_26',
                    'RSI', 'MACD', 'MACD_Signal', 'MACD_Histogram', 'BB_Upper', 'BB_Middle', 
                    'BB_Lower', 'BB_Percent', 'High_Low_Ratio', 'Open_Close_Ratio', 
                    'Volatility', 'Price_Change', 'Volume_Ratio', 'Momentum', 'ROC'
                ]
                
                # Prepare data for traditional ML models
                X = df_with_features[feature_cols].values
                y_regression = df_with_features['Target_Price'].values[:-1]
                y_classification = df_with_features['Target_Class'].values[:-1]
                X = X[:-1]
                
                # Split data
                split_idx = int((1 - test_size/100) * len(X))
                X_train, X_test = X[:split_idx], X[split_idx:]
                y_reg_train, y_reg_test = y_regression[:split_idx], y_regression[split_idx:]
                y_class_train, y_class_test = y_classification[:split_idx], y_classification[split_idx:]
                
                # Store results
                results = {}
                
                # =============================================================================
                # MODEL 1: LSTM + RNN
                # =============================================================================
                if TENSORFLOW_AVAILABLE:
                    st.subheader("🧠 LSTM + RNN Hybrid Model")
                    
                    try:
                        # Prepare LSTM data
                        lstm_data = df_with_features[['Open', 'High', 'Low', 'Close', 'Volume']].values
                        X_lstm, y_lstm, lstm_scaler = pa.prepare_lstm_data(lstm_data, lookback_days)
                        
                        # Split LSTM data
                        lstm_split = int((1 - test_size/100) * len(X_lstm))
                        X_lstm_train, X_lstm_test = X_lstm[:lstm_split], X_lstm[lstm_split:]
                        y_lstm_train, y_lstm_test = y_lstm[:lstm_split], y_lstm[lstm_split:]
                        
                        # Train LSTM+RNN model
                        lstm_rnn = LSTMRNNModel(
                            input_shape=(lookback_days, lstm_data.shape[1]),
                            lstm_units=lstm_units,
                            rnn_units=rnn_units
                        )
                        
                        with st.spinner("Training LSTM+RNN model..."):
                            history = lstm_rnn.fit(X_lstm_train, y_lstm_train, epochs=30, batch_size=32)
                        
                        # Predictions
                        lstm_pred = lstm_rnn.predict(X_lstm_test)
                        
                        # Inverse transform predictions (focusing on Close price - index 3)
                        lstm_pred_close = lstm_scaler.inverse_transform(lstm_pred)[:, 3]
                        actual_close = lstm_scaler.inverse_transform(y_lstm_test)[:, 3]
                        
                        # Evaluate LSTM+RNN
                        lstm_results = evaluate_regression(actual_close, lstm_pred_close, "LSTM+RNN")
                        results['LSTM+RNN'] = lstm_results
                        
                        # Display results
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("RMSE", f"{lstm_results['RMSE']:.4f}")
                        with col2:
                            st.metric("MAE", f"{lstm_results['MAE']:.4f}")
                        with col3:
                            st.metric("Directional Accuracy", f"{lstm_results['Directional_Accuracy']:.2%}")
                        with col4:
                            st.metric("Training Samples", len(X_lstm_train))
                        
                        # Plot predictions
                        dates = df_with_features.index[lstm_split + lookback_days:lstm_split + lookback_days + len(actual_close)]
                        st.plotly_chart(
                            create_prediction_chart(actual_close, lstm_pred_close, "LSTM+RNN Predictions vs Actual", dates),
                            use_container_width=True
                        )
                        
                    except Exception as e:
                        st.error(f"Error training LSTM+RNN model: {str(e)}")
                        results['LSTM+RNN'] = None
                else:
                    st.warning("LSTM+RNN model disabled - TensorFlow not available")
                    results['LSTM+RNN'] = None
                
                # =============================================================================
                # MODEL 2: RANDOM FOREST + DECISION TREES
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
                        st.metric("Classification Accuracy", f"{rf_class_results['Accuracy']:.2%}")
                    
                    # Plot predictions
                    dates = df_with_features.index[split_idx:split_idx + len(y_reg_test)]
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
                # MODEL 3: SUPPORT VECTOR MACHINE
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
                        st.metric("Classification Accuracy", f"{svm_class_results['Accuracy']:.2%}")
                    
                    # Plot predictions
                    st.plotly_chart(
                        create_prediction_chart(y_reg_test, svm_reg_pred, "SVM Predictions vs Actual", dates),
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Error training SVM model: {str(e)}")
                    results['SVM'] = None
                
                # =============================================================================
                # MODEL COMPARISON
                # =============================================================================
                st.subheader("📊 Model Comparison Summary")
                
                # Create comparison dataframe
                comparison_data = []
                for model_name, model_results in results.items():
                    if model_results is not None:
                        comparison_data.append({
                            'Model': model_name,
                            'RMSE': model_results['RMSE'],
                            'MAE': model_results['MAE'],
                            'Directional_Accuracy': model_results['Directional_Accuracy']
                        })
                
                if comparison_data:
                    comparison_df = pd.DataFrame(comparison_data)
                    
                    # Display comparison table
                    st.dataframe(comparison_df, use_container_width=True)
                    
                    # Plot comparison chart
                    st.plotly_chart(
                        create_model_comparison_chart(comparison_df),
                        use_container_width=True
                    )
                    
                    # Best model recommendation
                    best_model = comparison_df.loc[comparison_df['RMSE'].idxmin()]
                    st.success(f"🏆 **Best Performing Model:** {best_model['Model']} (RMSE: {best_model['RMSE']:.4f})")
                
                # Future predictions
                st.subheader("🔮 Future Predictions")
                
                # Use the best model for future predictions
                if comparison_data:
                    best_model_name = comparison_df.loc[comparison_df['RMSE'].idxmin(), 'Model']
                    
                    if best_model_name == 'Random Forest':
                        # Use Random Forest for future predictions
                        future_pred = rf_reg.predict(X[-prediction_days:])
                        st.write(f"**{best_model_name} predictions for next {prediction_days} days:**")
                        
                        future_dates = pd.date_range(
                            start=df_with_features.index[-1] + timedelta(days=1),
                            periods=prediction_days,
                            freq='D'
                        )
                        
                        future_df = pd.DataFrame({
                            'Date': future_dates,
                            'Predicted_Price': future_pred
                        })
                        
                        st.dataframe(future_df, use_container_width=True)
                        
                        # Plot future predictions
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=future_dates,
                            y=future_pred,
                            mode='lines+markers',
                            name='Future Predictions',
                            line=dict(color='red', width=3),
                            marker=dict(size=8)
                        ))
                        
                        fig.update_layout(
                            title=f"Future Price Predictions ({best_model_name})",
                            xaxis_title="Date",
                            yaxis_title="Predicted Price",
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                
                # Store results in session state
                st.session_state.pa_results = results
                st.session_state.pa_symbol = symbol
                st.session_state.pa_data = df_with_features
                
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.exception(e)
    
    # Display cached results if available
    elif 'pa_results' in st.session_state and st.session_state.pa_symbol == symbol:
        st.info("📊 Displaying cached results. Click 'Run Predictive Analysis' to refresh.")
        
        results = st.session_state.pa_results
        df_with_features = st.session_state.pa_data
        
        # Display summary of cached results
        st.subheader("📈 Cached Analysis Results")
        
        comparison_data = []
        for model_name, model_results in results.items():
            if model_results is not None:
                comparison_data.append({
                    'Model': model_name,
                    'RMSE': model_results['RMSE'],
                    'MAE': model_results['MAE'],
                    'Directional_Accuracy': model_results['Directional_Accuracy']
                })
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True)
            
            best_model = comparison_df.loc[comparison_df['RMSE'].idxmin()]
            st.success(f"🏆 **Best Model:** {best_model['Model']} (RMSE: {best_model['RMSE']:.4f})")
    
    else:
        st.info("👆 Click 'Run Predictive Analysis' to begin machine learning analysis")
        
        # Show sample of what the analysis will include
        st.subheader("🔍 What This Analysis Will Provide")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **🧠 LSTM+RNN Model**
            - Sequential pattern recognition
            - Long-term memory capabilities
            - Complex relationship modeling
            """)
        
        with col2:
            st.markdown("""
            **🌳 Random Forest**
            - Feature importance analysis
            - Robust ensemble predictions
            - Overfitting resistance
            """)
        
        with col3:
            st.markdown("""
            **📊 SVM Model**
            - Optimal boundary finding
            - High-dimensional effectiveness
            - Clear pattern recognition
            """)


if __name__ == "__main__":
    main()
