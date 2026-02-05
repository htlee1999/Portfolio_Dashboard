"""
Consolidated technical analysis indicators module.
Contains reusable classes for technical and predictive analysis.
"""

import pandas as pd
import numpy as np


class TechnicalAnalysis:
    """Comprehensive technical analysis class implementing the top 5 indicators."""

    def __init__(self, data):
        """
        Initialize with price data.

        Args:
            data (pd.DataFrame): OHLCV data with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.prices = data['Close']
        self.volumes = data['Volume'] if 'Volume' in data.columns else None

    def calculate_rsi(self, period=14):
        """
        Calculate Relative Strength Index (RSI).

        Args:
            period (int): RSI calculation period (default: 14)

        Returns:
            pd.Series: RSI values
        """
        delta = self.prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)

        avg_gains = gains.ewm(span=period, min_periods=period).mean()
        avg_losses = losses.ewm(span=period, min_periods=period).mean()

        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_macd(self, fast_period=12, slow_period=26, signal_period=9):
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            fast_period (int): Fast EMA period (default: 12)
            slow_period (int): Slow EMA period (default: 26)
            signal_period (int): Signal line EMA period (default: 9)

        Returns:
            tuple: (macd_line, signal_line, histogram)
        """
        ema_fast = self.prices.ewm(span=fast_period, min_periods=fast_period).mean()
        ema_slow = self.prices.ewm(span=slow_period, min_periods=slow_period).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, min_periods=signal_period).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def calculate_bollinger_bands(self, period=20, std_dev=2):
        """
        Calculate Bollinger Bands.

        Args:
            period (int): Moving average period (default: 20)
            std_dev (float): Standard deviation multiplier (default: 2)

        Returns:
            tuple: (upper_band, middle_band, lower_band, %B, band_width)
        """
        middle_band = self.prices.rolling(window=period).mean()
        rolling_std = self.prices.rolling(window=period).std()

        upper_band = middle_band + (rolling_std * std_dev)
        lower_band = middle_band - (rolling_std * std_dev)

        # Calculate %B (Bollinger Band percentage)
        bb_percent = (self.prices - lower_band) / (upper_band - lower_band)

        # Calculate Band Width (volatility measure)
        band_width = (upper_band - lower_band) / middle_band

        return upper_band, middle_band, lower_band, bb_percent, band_width

    def calculate_moving_averages(self, periods=[5, 10, 20, 50]):
        """
        Calculate Simple and Exponential Moving Averages.

        Args:
            periods (list): List of periods to calculate (default: [5, 10, 20, 50])

        Returns:
            dict: Dictionary with SMA and EMA for each period
        """
        mas = {}
        for period in periods:
            mas[f'SMA_{period}'] = self.prices.rolling(window=period).mean()
            mas[f'EMA_{period}'] = self.prices.ewm(span=period, min_periods=period).mean()
        return mas

    def calculate_obv(self):
        """
        Calculate On-Balance Volume (OBV).

        Returns:
            pd.Series: OBV values
        """
        if self.volumes is None:
            return pd.Series(index=self.prices.index, dtype=float)

        obv = [0]
        for i in range(1, len(self.prices)):
            if self.prices.iloc[i] > self.prices.iloc[i-1]:
                obv.append(obv[-1] + self.volumes.iloc[i])
            elif self.prices.iloc[i] < self.prices.iloc[i-1]:
                obv.append(obv[-1] - self.volumes.iloc[i])
            else:
                obv.append(obv[-1])

        return pd.Series(obv, index=self.prices.index)

    def get_signals(self, indicators=None):
        """
        Generate trading signals for specified indicators.

        Args:
            indicators (list): List of indicators to include.
                               Options: 'rsi', 'macd', 'bollinger', 'moving_averages', 'obv'
                               Default: all indicators

        Returns:
            dict: Dictionary with signals for each indicator
        """
        if indicators is None:
            indicators = ['rsi', 'macd', 'bollinger', 'moving_averages', 'obv']

        signals = {}

        # RSI Signals
        if 'rsi' in indicators:
            rsi = self.calculate_rsi()
            signals['rsi'] = {
                'overbought': rsi > 70,
                'oversold': rsi < 30,
                'neutral': (rsi >= 30) & (rsi <= 70),
                'current_value': rsi.iloc[-1] if not rsi.empty else None
            }

        # MACD Signals
        if 'macd' in indicators:
            macd_line, signal_line, histogram = self.calculate_macd()
            signals['macd'] = {
                'bullish_crossover': (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1)),
                'bearish_crossover': (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1)),
                'above_signal': macd_line > signal_line,
                'current_macd': macd_line.iloc[-1] if not macd_line.empty else None,
                'current_signal': signal_line.iloc[-1] if not signal_line.empty else None
            }

        # Bollinger Bands Signals
        if 'bollinger' in indicators:
            upper_bb, middle_bb, lower_bb, bb_percent, band_width = self.calculate_bollinger_bands()
            signals['bollinger'] = {
                'above_upper': self.prices > upper_bb,
                'below_lower': self.prices < lower_bb,
                'squeeze': band_width < band_width.rolling(20).mean() * 0.5,  # Low volatility
                'current_bb_percent': bb_percent.iloc[-1] if not bb_percent.empty else None,
                'current_band_width': band_width.iloc[-1] if not band_width.empty else None
            }

        # Moving Average Signals
        if 'moving_averages' in indicators:
            mas = self.calculate_moving_averages()
            signals['moving_averages'] = {}
            for name, ma in mas.items():
                signals['moving_averages'][name] = {
                    'price_above': self.prices > ma,
                    'current_value': ma.iloc[-1] if not ma.empty else None
                }

        # OBV Signals
        if 'obv' in indicators:
            obv = self.calculate_obv()
            obv_ema = obv.ewm(span=10).mean()
            signals['obv'] = {
                'rising': obv > obv_ema,
                'falling': obv < obv_ema,
                'current_value': obv.iloc[-1] if not obv.empty else None
            }

        return signals

    def add_all_indicators(self):
        """
        Add all technical indicators to the data DataFrame.

        Returns:
            pd.DataFrame: Data with all indicators added
        """
        data_with_indicators = self.data.copy()

        # RSI
        data_with_indicators['RSI'] = self.calculate_rsi()

        # MACD
        macd_line, signal_line, histogram = self.calculate_macd()
        data_with_indicators['MACD'] = macd_line
        data_with_indicators['MACD_Signal'] = signal_line
        data_with_indicators['MACD_Histogram'] = histogram

        # Bollinger Bands
        upper_bb, middle_bb, lower_bb, bb_percent, band_width = self.calculate_bollinger_bands()
        data_with_indicators['BB_Upper'] = upper_bb
        data_with_indicators['BB_Middle'] = middle_bb
        data_with_indicators['BB_Lower'] = lower_bb
        data_with_indicators['BB_Percent'] = bb_percent
        data_with_indicators['BB_Width'] = band_width

        # Moving Averages
        mas = self.calculate_moving_averages()
        for name, ma in mas.items():
            data_with_indicators[name] = ma

        # OBV
        data_with_indicators['OBV'] = self.calculate_obv()

        return data_with_indicators


class PredictiveAnalysis:
    """Predictive analysis class for ML feature preparation."""

    def __init__(self, data):
        """
        Initialize with price data.

        Args:
            data (pd.DataFrame): OHLCV data with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.prices = data['Close']
        self.volumes = data['Volume'] if 'Volume' in data.columns else None
        # Reuse TechnicalAnalysis for indicator calculations
        self._ta = TechnicalAnalysis(data)

    def prepare_features(self):
        """
        Create technical indicators and features for ML models.

        Returns:
            pd.DataFrame: DataFrame with all ML features, NaN rows dropped
        """
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

        # Momentum indicators (reuse TechnicalAnalysis RSI calculation)
        df['RSI'] = self._ta.calculate_rsi()

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
