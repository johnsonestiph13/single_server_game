# telegram-bot/bot/utils/metrics.py
# Estif Bingo 24/7 - Metrics and Monitoring Utilities
# Tracks system metrics, performance counters, and analytics

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

from bot.utils.logger import logger


# ==================== METRIC TYPES ====================

class MetricType(Enum):
    """Types of metrics that can be tracked"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class MetricUnit(Enum):
    """Units for metrics"""
    BYTES = "bytes"
    MILLISECONDS = "ms"
    SECONDS = "s"
    PERCENT = "%"
    COUNT = "count"
    REQUESTS = "requests"
    ITEMS = "items"


# ==================== DATA CLASSES ====================

@dataclass
class Metric:
    """Single metric data point"""
    name: str
    type: MetricType
    value: float
    unit: MetricUnit = MetricUnit.COUNT
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class HistogramBucket:
    """Histogram bucket for distribution tracking"""
    upper_bound: float
    count: int = 0


# ==================== METRICS COLLECTOR ====================

class MetricsCollector:
    """
    Collects and stores system metrics.
    Thread-safe singleton for tracking various metrics.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._counters: Dict[str, int] = defaultdict(int)
            self._gauges: Dict[str, float] = {}
            self._histograms: Dict[str, List[float]] = defaultdict(list)
            self._timers: Dict[str, List[float]] = defaultdict(list)
            self._lock = threading.Lock()
            self._max_histogram_samples = 1000
            self._max_timer_samples = 1000
            logger.info("MetricsCollector initialized")
    
    # ==================== COUNTERS ====================
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            value: Value to increment by
            tags: Optional tags for the metric
        """
        with self._lock:
            key = self._build_key(name, tags)
            self._counters[key] += value
    
    def decrement_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Decrement a counter metric.
        
        Args:
            name: Counter name
            value: Value to decrement by
            tags: Optional tags for the metric
        """
        with self._lock:
            key = self._build_key(name, tags)
            self._counters[key] -= value
    
    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """
        Get counter value.
        
        Args:
            name: Counter name
            tags: Optional tags
        
        Returns:
            int: Counter value
        """
        key = self._build_key(name, tags)
        return self._counters.get(key, 0)
    
    # ==================== GAUGES ====================
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric.
        
        Args:
            name: Gauge name
            value: Value to set
            tags: Optional tags
        """
        with self._lock:
            key = self._build_key(name, tags)
            self._gauges[key] = value
    
    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[float]:
        """
        Get gauge value.
        
        Args:
            name: Gauge name
            tags: Optional tags
        
        Returns:
            float: Gauge value or None
        """
        key = self._build_key(name, tags)
        return self._gauges.get(key)
    
    # ==================== HISTOGRAMS ====================
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a value in a histogram.
        
        Args:
            name: Histogram name
            value: Value to record
            tags: Optional tags
        """
        with self._lock:
            key = self._build_key(name, tags)
            self._histograms[key].append(value)
            
            # Trim to max samples
            if len(self._histograms[key]) > self._max_histogram_samples:
                self._histograms[key] = self._histograms[key][-self._max_histogram_samples:]
    
    def get_histogram_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Get histogram statistics.
        
        Args:
            name: Histogram name
            tags: Optional tags
        
        Returns:
            dict: Statistics including count, min, max, mean, p50, p90, p99
        """
        key = self._build_key(name, tags)
        values = self._histograms.get(key, [])
        
        if not values:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'mean': 0,
                'p50': 0,
                'p90': 0,
                'p99': 0
            }
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            'count': count,
            'min': sorted_values[0],
            'max': sorted_values[-1],
            'mean': sum(sorted_values) / count,
            'p50': self._percentile(sorted_values, 50),
            'p90': self._percentile(sorted_values, 90),
            'p99': self._percentile(sorted_values, 99)
        }
    
    # ==================== TIMERS ====================
    
    def record_timer(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timer duration.
        
        Args:
            name: Timer name
            duration_ms: Duration in milliseconds
            tags: Optional tags
        """
        with self._lock:
            key = self._build_key(name, tags)
            self._timers[key].append(duration_ms)
            
            if len(self._timers[key]) > self._max_timer_samples:
                self._timers[key] = self._timers[key][-self._max_timer_samples:]
    
    def get_timer_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Get timer statistics.
        
        Args:
            name: Timer name
            tags: Optional tags
        
        Returns:
            dict: Statistics including count, min, max, mean, p50, p90, p99
        """
        key = self._build_key(name, tags)
        values = self._timers.get(key, [])
        
        if not values:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'mean': 0,
                'p50': 0,
                'p90': 0,
                'p99': 0
            }
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            'count': count,
            'min': sorted_values[0],
            'max': sorted_values[-1],
            'mean': sum(sorted_values) / count,
            'p50': self._percentile(sorted_values, 50),
            'p90': self._percentile(sorted_values, 90),
            'p99': self._percentile(sorted_values, 99)
        }
    
    # ==================== TIMER CONTEXT MANAGER ====================
    
    class TimerContext:
        """Context manager for timing operations"""
        def __init__(self, collector: 'MetricsCollector', name: str, tags: Optional[Dict[str, str]] = None):
            self.collector = collector
            self.name = name
            self.tags = tags
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration_ms = (time.time() - self.start_time) * 1000
            self.collector.record_timer(self.name, duration_ms, self.tags)
    
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None) -> 'TimerContext':
        """
        Create a timer context manager for measuring operation duration.
        
        Args:
            name: Timer name
            tags: Optional tags
        
        Returns:
            TimerContext: Timer context manager
        """
        return self.TimerContext(self, name, tags)
    
    # ==================== UTILITY METHODS ====================
    
    def _build_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Build a unique key from name and tags"""
        if not tags:
            return name
        
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}|{tag_str}"
    
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0
        
        index = (percentile / 100) * (len(sorted_values) - 1)
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(sorted_values):
            return sorted_values[-1]
        
        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
    
    def reset(self) -> None:
        """Reset all metrics"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
        logger.info("MetricsCollector reset")
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all current metrics.
        
        Returns:
            dict: All metrics
        """
        with self._lock:
            return {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'histograms': {
                    key: self.get_histogram_stats(key.split('|')[0])
                    for key in self._histograms
                },
                'timers': {
                    key: self.get_timer_stats(key.split('|')[0])
                    for key in self._timers
                }
            }


# ==================== PERFORMANCE MONITOR ====================

class PerformanceMonitor:
    """Monitors system performance including CPU, memory, and response times"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self._start_time = time.time()
        self._request_counts = defaultdict(int)
        self._error_counts = defaultdict(int)
    
    def record_request(self, endpoint: str, status_code: int, duration_ms: float) -> None:
        """
        Record an API request.
        
        Args:
            endpoint: API endpoint
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
        """
        self.metrics.increment_counter(f"api.requests", tags={'endpoint': endpoint})
        self.metrics.record_timer(f"api.duration", duration_ms, tags={'endpoint': endpoint})
        self._request_counts[endpoint] += 1
        
        if status_code >= 400:
            self.metrics.increment_counter(f"api.errors", tags={'endpoint': endpoint, 'status': str(status_code)})
            self._error_counts[endpoint] += 1
    
    def record_game_action(self, action: str, user_id: int, success: bool) -> None:
        """
        Record a game action.
        
        Args:
            action: Action name (select, draw, win)
            user_id: User ID
            success: Whether action was successful
        """
        self.metrics.increment_counter(f"game.{action}", tags={'success': str(success)})
    
    def record_database_query(self, query_name: str, duration_ms: float) -> None:
        """
        Record a database query.
        
        Args:
            query_name: Query name
            duration_ms: Query duration in milliseconds
        """
        self.metrics.record_timer(f"db.query.{query_name}", duration_ms)
    
    def get_uptime(self) -> float:
        """
        Get system uptime in seconds.
        
        Returns:
            float: Uptime in seconds
        """
        return time.time() - self._start_time
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            dict: Performance statistics
        """
        return {
            'uptime_seconds': self.get_uptime(),
            'total_requests': sum(self._request_counts.values()),
            'total_errors': sum(self._error_counts.values()),
            'error_rate': (sum(self._error_counts.values()) / max(1, sum(self._request_counts.values()))) * 100,
            'requests_by_endpoint': dict(self._request_counts),
            'errors_by_endpoint': dict(self._error_counts)
        }


# ==================== HEALTH CHECKER ====================

class HealthChecker:
    """Checks health of various system components"""
    
    def __init__(self):
        self._checks: Dict[str, callable] = {}
        self._last_results: Dict[str, Tuple[bool, str, float]] = {}
    
    def register_check(self, name: str, check_func: callable) -> None:
        """
        Register a health check function.
        
        Args:
            name: Check name
            check_func: Async function that returns (is_healthy, message)
        """
        self._checks[name] = check_func
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all registered health checks.
        
        Returns:
            dict: Health check results
        """
        results = {}
        overall_healthy = True
        
        for name, check_func in self._checks.items():
            try:
                start = time.time()
                is_healthy, message = await check_func()
                duration = (time.time() - start) * 1000
                
                results[name] = {
                    'healthy': is_healthy,
                    'message': message,
                    'duration_ms': duration
                }
                
                if not is_healthy:
                    overall_healthy = False
                
                self._last_results[name] = (is_healthy, message, duration)
                
            except Exception as e:
                results[name] = {
                    'healthy': False,
                    'message': str(e),
                    'duration_ms': 0
                }
                overall_healthy = False
        
        return {
            'healthy': overall_healthy,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': results
        }
    
    def get_last_results(self) -> Dict[str, Any]:
        """
        Get last health check results.
        
        Returns:
            dict: Last health check results
        """
        results = {}
        for name, (is_healthy, message, duration) in self._last_results.items():
            results[name] = {
                'healthy': is_healthy,
                'message': message,
                'duration_ms': duration
            }
        
        return {
            'healthy': all(r[0] for r in self._last_results.values()),
            'checks': results
        }


# ==================== BUSINESS METRICS ====================

class BusinessMetrics:
    """Tracks business-specific metrics like user activity, game statistics, etc."""
    
    def __init__(self):
        self.metrics = MetricsCollector()
    
    def record_user_registration(self) -> None:
        """Record a new user registration"""
        self.metrics.increment_counter("business.users.registered")
    
    def record_user_login(self, user_id: int) -> None:
        """Record a user login"""
        self.metrics.increment_counter("business.users.active")
        self.metrics.set_gauge("business.users.last_active", time.time(), tags={'user_id': str(user_id)})
    
    def record_deposit(self, amount: float, method: str) -> None:
        """
        Record a deposit.
        
        Args:
            amount: Deposit amount
            method: Payment method
        """
        self.metrics.increment_counter("business.deposits.count", tags={'method': method})
        self.metrics.increment_counter("business.deposits.amount", value=amount, tags={'method': method})
    
    def record_withdrawal(self, amount: float, method: str) -> None:
        """
        Record a withdrawal.
        
        Args:
            amount: Withdrawal amount
            method: Withdrawal method
        """
        self.metrics.increment_counter("business.withdrawals.count", tags={'method': method})
        self.metrics.increment_counter("business.withdrawals.amount", value=amount, tags={'method': method})
    
    def record_game_round(self, total_cartelas: int, total_bets: float, prize_pool: float) -> None:
        """
        Record a game round.
        
        Args:
            total_cartelas: Total cartelas sold
            total_bets: Total bets amount
            prize_pool: Prize pool amount
        """
        self.metrics.increment_counter("business.games.rounds")
        self.metrics.increment_counter("business.games.cartelas", value=total_cartelas)
        self.metrics.increment_counter("business.games.bets", value=total_bets)
        self.metrics.increment_counter("business.games.prizes", value=prize_pool)
    
    def record_win(self, user_id: int, amount: float, pattern: str) -> None:
        """
        Record a win.
        
        Args:
            user_id: User ID
            amount: Win amount
            pattern: Winning pattern
        """
        self.metrics.increment_counter("business.wins.count", tags={'pattern': pattern})
        self.metrics.increment_counter("business.wins.amount", value=amount, tags={'pattern': pattern})
    
    def record_cartela_selection(self, user_id: int, cartela_count: int) -> None:
        """
        Record cartela selection.
        
        Args:
            user_id: User ID
            cartela_count: Number of cartelas selected
        """
        self.metrics.increment_counter("business.cartelas.selected", value=cartela_count)
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """
        Get daily business statistics.
        
        Returns:
            dict: Daily statistics
        """
        return {
            'users': {
                'registered': self.metrics.get_counter("business.users.registered"),
                'active': self.metrics.get_counter("business.users.active")
            },
            'deposits': {
                'count': self.metrics.get_counter("business.deposits.count"),
                'amount': self.metrics.get_counter("business.deposits.amount")
            },
            'withdrawals': {
                'count': self.metrics.get_counter("business.withdrawals.count"),
                'amount': self.metrics.get_counter("business.withdrawals.amount")
            },
            'games': {
                'rounds': self.metrics.get_counter("business.games.rounds"),
                'cartelas': self.metrics.get_counter("business.games.cartelas"),
                'bets': self.metrics.get_counter("business.games.bets"),
                'prizes': self.metrics.get_counter("business.games.prizes")
            },
            'wins': {
                'count': self.metrics.get_counter("business.wins.count"),
                'amount': self.metrics.get_counter("business.wins.amount")
            }
        }


# ==================== SINGLETON INSTANCES ====================

metrics_collector = MetricsCollector()
performance_monitor = PerformanceMonitor()
health_checker = HealthChecker()
business_metrics = BusinessMetrics()


# ==================== DECORATORS ====================

def track_time(name: str):
    """
    Decorator to track function execution time.
    
    Args:
        name: Metric name for the timer
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with metrics_collector.timer(name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def track_request(endpoint: str):
    """
    Decorator to track API requests.
    
    Args:
        endpoint: API endpoint name
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                performance_monitor.record_request(endpoint, 200, duration)
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                performance_monitor.record_request(endpoint, 500, duration)
                raise
        return wrapper
    return decorator


# ==================== EXPORTS ====================

__all__ = [
    # Classes
    'MetricsCollector',
    'PerformanceMonitor',
    'HealthChecker',
    'BusinessMetrics',
    'MetricType',
    'MetricUnit',
    
    # Singleton instances
    'metrics_collector',
    'performance_monitor',
    'health_checker',
    'business_metrics',
    
    # Decorators
    'track_time',
    'track_request',
]