"""
Gemini API Token Usage Monitoring System

This module provides comprehensive monitoring and tracking of Gemini API token usage
for the Portfolio Dashboard application.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import streamlit as st


@dataclass
class TokenUsage:
    """Data class to track individual API call token usage."""
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    operation: str
    symbol: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


class GeminiUsageMonitor:
    """Monitor and track Gemini API token usage."""
    
    def __init__(self, data_file: str = "data/gemini_usage.json"):
        self.data_file = data_file
        self.usage_data: List[TokenUsage] = []
        self.load_usage_data()
        
        # Token pricing (as of 2024 - update as needed)
        self.pricing = {
            "gemini-2.5-flash": {
                "input": 0.000075,  # per 1K tokens
                "output": 0.0003    # per 1K tokens
            }
        }
    
    def load_usage_data(self) -> None:
        """Load usage data from JSON file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.usage_data = [TokenUsage(**item) for item in data]
            else:
                self.usage_data = []
        except Exception as e:
            st.warning(f"Could not load usage data: {e}")
            self.usage_data = []
    
    def save_usage_data(self) -> None:
        """Save usage data to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w') as f:
                data = [asdict(usage) for usage in self.usage_data]
                json.dump(data, f, indent=2)
        except Exception as e:
            st.error(f"Could not save usage data: {e}")
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        if model not in self.pricing:
            return 0.0
        
        pricing = self.pricing[model]
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost
    
    def estimate_tokens(self, text: str) -> int:
        """Rough estimation of token count (1 token ≈ 4 characters for English)."""
        return max(1, len(text) // 4)
    
    def log_api_call(self, 
                    model: str, 
                    prompt: str, 
                    response: str, 
                    operation: str,
                    symbol: Optional[str] = None,
                    success: bool = True,
                    error_message: Optional[str] = None) -> None:
        """Log an API call with token usage."""
        input_tokens = self.estimate_tokens(prompt)
        output_tokens = self.estimate_tokens(response) if success else 0
        total_tokens = input_tokens + output_tokens
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        usage = TokenUsage(
            timestamp=datetime.now().isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            operation=operation,
            symbol=symbol,
            success=success,
            error_message=error_message
        )
        
        self.usage_data.append(usage)
        self.save_usage_data()
    
    def get_usage_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get usage summary for the specified number of days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_usage = [
            usage for usage in self.usage_data 
            if datetime.fromisoformat(usage.timestamp) >= cutoff_date
        ]
        
        if not recent_usage:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "successful_calls": 0,
                "failed_calls": 0,
                "avg_tokens_per_call": 0,
                "daily_usage": [],
                "operations": {},
                "symbols": {}
            }
        
        total_calls = len(recent_usage)
        total_tokens = sum(usage.total_tokens for usage in recent_usage)
        total_cost = sum(usage.cost_usd for usage in recent_usage)
        successful_calls = sum(1 for usage in recent_usage if usage.success)
        failed_calls = total_calls - successful_calls
        
        # Daily usage breakdown
        daily_usage = {}
        for usage in recent_usage:
            date = usage.timestamp[:10]  # YYYY-MM-DD
            if date not in daily_usage:
                daily_usage[date] = {"tokens": 0, "cost": 0.0, "calls": 0}
            daily_usage[date]["tokens"] += usage.total_tokens
            daily_usage[date]["cost"] += usage.cost_usd
            daily_usage[date]["calls"] += 1
        
        # Operations breakdown
        operations = {}
        for usage in recent_usage:
            op = usage.operation
            if op not in operations:
                operations[op] = {"calls": 0, "tokens": 0, "cost": 0.0}
            operations[op]["calls"] += 1
            operations[op]["tokens"] += usage.total_tokens
            operations[op]["cost"] += usage.cost_usd
        
        # Symbols breakdown
        symbols = {}
        for usage in recent_usage:
            if usage.symbol:
                sym = usage.symbol
                if sym not in symbols:
                    symbols[sym] = {"calls": 0, "tokens": 0, "cost": 0.0}
                symbols[sym]["calls"] += 1
                symbols[sym]["tokens"] += usage.total_tokens
                symbols[sym]["cost"] += usage.cost_usd
        
        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "avg_tokens_per_call": total_tokens / total_calls if total_calls > 0 else 0,
            "daily_usage": daily_usage,
            "operations": operations,
            "symbols": symbols
        }
    
    def get_usage_trends(self, days: int = 7) -> Dict[str, List]:
        """Get usage trends for visualization."""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_usage = [
            usage for usage in self.usage_data 
            if datetime.fromisoformat(usage.timestamp) >= cutoff_date
        ]
        
        # Group by day
        daily_data = {}
        for usage in recent_usage:
            date = usage.timestamp[:10]
            if date not in daily_data:
                daily_data[date] = {"tokens": 0, "cost": 0.0, "calls": 0}
            daily_data[date]["tokens"] += usage.total_tokens
            daily_data[date]["cost"] += usage.cost_usd
            daily_data[date]["calls"] += 1
        
        # Sort by date
        sorted_dates = sorted(daily_data.keys())
        
        return {
            "dates": sorted_dates,
            "tokens": [daily_data[date]["tokens"] for date in sorted_dates],
            "costs": [daily_data[date]["cost"] for date in sorted_dates],
            "calls": [daily_data[date]["calls"] for date in sorted_dates]
        }
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Check current rate limit status."""
        now = datetime.now()
        
        # Check last minute
        last_minute = now - timedelta(minutes=1)
        recent_calls = [
            usage for usage in self.usage_data
            if datetime.fromisoformat(usage.timestamp) >= last_minute
        ]
        
        # Check last hour
        last_hour = now - timedelta(hours=1)
        hourly_calls = [
            usage for usage in self.usage_data
            if datetime.fromisoformat(usage.timestamp) >= last_hour
        ]
        
        # Check today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_calls = [
            usage for usage in self.usage_data
            if datetime.fromisoformat(usage.timestamp) >= today_start
        ]
        
        return {
            "last_minute": len(recent_calls),
            "last_hour": len(hourly_calls),
            "today": len(daily_calls),
            "minute_limit": 15,  # Gemini free tier limit
            "hour_limit": 900,   # 15 * 60
            "daily_limit": 1000000  # 1M tokens per day
        }
    
    def clear_old_data(self, days_to_keep: int = 90) -> None:
        """Clear usage data older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        self.usage_data = [
            usage for usage in self.usage_data
            if datetime.fromisoformat(usage.timestamp) >= cutoff_date
        ]
        self.save_usage_data()


# Global monitor instance
monitor = GeminiUsageMonitor()


def get_monitor() -> GeminiUsageMonitor:
    """Get the global monitor instance."""
    return monitor


def log_gemini_call(model: str, 
                   prompt: str, 
                   response: str, 
                   operation: str,
                   symbol: Optional[str] = None,
                   success: bool = True,
                   error_message: Optional[str] = None) -> None:
    """Convenience function to log a Gemini API call."""
    monitor.log_api_call(model, prompt, response, operation, symbol, success, error_message)


def get_usage_summary(days: int = 30) -> Dict[str, Any]:
    """Convenience function to get usage summary."""
    return monitor.get_usage_summary(days)


def get_usage_trends(days: int = 7) -> Dict[str, List]:
    """Convenience function to get usage trends."""
    return monitor.get_usage_trends(days)


def get_rate_limit_status() -> Dict[str, Any]:
    """Convenience function to get rate limit status."""
    return monitor.get_rate_limit_status()
