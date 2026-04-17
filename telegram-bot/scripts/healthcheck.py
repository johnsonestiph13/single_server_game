#!/usr/bin/env python3
# telegram-bot/scripts/healthcheck.py
# Estif Bingo 24/7 - Health Check Script
# Monitors application health and reports status

import os
import sys
import json
import time
import asyncio
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import aiohttp
import asyncpg

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import config, but don't fail if not available
try:
    from bot.config import config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False
    # Fallback configuration
    class Config:
        DATABASE_URL = os.getenv('DATABASE_URL', '')
        BASE_URL = os.getenv('BASE_URL', 'http://localhost:10000')
        BOT_TOKEN = os.getenv('BOT_TOKEN', '')
        ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', '')
    
    config = Config()


# ==================== CONFIGURATION ====================

HEALTH_CONFIG = {
    'timeout': 10,  # seconds
    'retries': 3,
    'retry_delay': 2,  # seconds
    'db_timeout': 5,
    'api_timeout': 10,
    'ws_timeout': 5,
    'alert_threshold': 3,  # consecutive failures before alert
    'log_file': 'logs/healthcheck.log'
}

# ==================== LOGGING ====================

def log_message(message: str, level: str = "INFO"):
    """Log message to console and file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    
    try:
        with open(HEALTH_CONFIG['log_file'], 'a') as f:
            f.write(log_line + '\n')
    except Exception:
        pass


# ==================== HEALTH CHECKS ====================

class HealthChecker:
    """Performs various health checks on the application."""
    
    def __init__(self):
        self.consecutive_failures = 0
        self.last_status = {}
        self.results = {}
    
    async def check_database(self) -> Tuple[bool, str, float]:
        """Check database connectivity."""
        start_time = time.time()
        
        if not config.DATABASE_URL:
            return False, "DATABASE_URL not configured", 0
        
        try:
            conn = await asyncpg.connect(config.DATABASE_URL, timeout=HEALTH_CONFIG['db_timeout'])
            result = await conn.fetchval("SELECT 1 as connected")
            await conn.close()
            
            duration = (time.time() - start_time) * 1000
            
            if result == 1:
                return True, f"Database connected ({duration:.0f}ms)", duration
            else:
                return False, "Database returned unexpected result", duration
                
        except asyncpg.exceptions.InvalidPasswordError:
            duration = (time.time() - start_time) * 1000
            return False, "Database authentication failed", duration
        except asyncpg.exceptions.CannotConnectNowError:
            duration = (time.time() - start_time) * 1000
            return False, "Database connection refused", duration
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, f"Database error: {str(e)[:100]}", duration
    
    async def check_api(self) -> Tuple[bool, str, float]:
        """Check API endpoint health."""
        start_time = time.time()
        
        api_url = f"{config.BASE_URL}/api/health"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=HEALTH_CONFIG['api_timeout']) as response:
                    duration = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        return True, f"API healthy ({duration:.0f}ms)", duration
                    else:
                        return False, f"API returned status {response.status}", duration
                        
        except aiohttp.ClientConnectorError:
            duration = (time.time() - start_time) * 1000
            return False, "API connection refused", duration
        except asyncio.TimeoutError:
            duration = (time.time() - start_time) * 1000
            return False, f"API timeout after {HEALTH_CONFIG['api_timeout']}s", duration
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, f"API error: {str(e)[:100]}", duration
    
    async def check_websocket(self) -> Tuple[bool, str, float]:
        """Check WebSocket endpoint health."""
        start_time = time.time()
        
        ws_url = f"{config.BASE_URL.replace('http', 'ws')}/socket.io/?EIO=4&transport=websocket"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url, timeout=HEALTH_CONFIG['ws_timeout']) as ws:
                    duration = (time.time() - start_time) * 1000
                    await ws.close()
                    return True, f"WebSocket healthy ({duration:.0f}ms)", duration
                    
        except aiohttp.ClientConnectorError:
            duration = (time.time() - start_time) * 1000
            return False, "WebSocket connection refused", duration
        except asyncio.TimeoutError:
            duration = (time.time() - start_time) * 1000
            return False, f"WebSocket timeout after {HEALTH_CONFIG['ws_timeout']}s", duration
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, f"WebSocket error: {str(e)[:100]}", duration
    
    async def check_bot(self) -> Tuple[bool, str, float]:
        """Check if bot is running (via getMe API)."""
        start_time = time.time()
        
        if not config.BOT_TOKEN:
            return False, "BOT_TOKEN not configured", 0
        
        api_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getMe"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=HEALTH_CONFIG['api_timeout']) as response:
                    duration = (time.time() - start_time) * 1000
                    data = await response.json()
                    
                    if data.get('ok'):
                        bot_name = data.get('result', {}).get('username', 'Unknown')
                        return True, f"Bot @{bot_name} is running ({duration:.0f}ms)", duration
                    else:
                        return False, f"Bot API error: {data.get('description', 'Unknown error')}", duration
                        
        except aiohttp.ClientConnectorError:
            duration = (time.time() - start_time) * 1000
            return False, "Telegram API connection refused", duration
        except asyncio.TimeoutError:
            duration = (time.time() - start_time) * 1000
            return False, f"Telegram API timeout after {HEALTH_CONFIG['api_timeout']}s", duration
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, f"Bot check error: {str(e)[:100]}", duration
    
    async def check_disk_space(self) -> Tuple[bool, str, float]:
        """Check available disk space."""
        start_time = time.time()
        
        try:
            import shutil
            usage = shutil.disk_usage('/')
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            percent_free = (usage.free / usage.total) * 100
            
            duration = (time.time() - start_time) * 1000
            
            if percent_free < 10:
                return False, f"Low disk space: {free_gb:.1f}GB free ({percent_free:.1f}%)", duration
            else:
                return True, f"Disk space: {free_gb:.1f}GB free ({percent_free:.1f}%)", duration
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, f"Disk check error: {str(e)[:100]}", duration
    
    async def check_memory(self) -> Tuple[bool, str, float]:
        """Check memory usage."""
        start_time = time.time()
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            used_percent = memory.percent
            available_gb = memory.available / (1024 ** 3)
            
            duration = (time.time() - start_time) * 1000
            
            if used_percent > 90:
                return False, f"High memory usage: {used_percent:.1f}% used", duration
            else:
                return True, f"Memory: {used_percent:.1f}% used ({available_gb:.1f}GB available)", duration
                
        except ImportError:
            duration = (time.time() - start_time) * 1000
            return True, "Memory check skipped (psutil not installed)", duration
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, f"Memory check error: {str(e)[:100]}", duration
    
    async def check_cpu(self) -> Tuple[bool, str, float]:
        """Check CPU usage."""
        start_time = time.time()
        
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            
            duration = (time.time() - start_time) * 1000
            
            if cpu_percent > 90:
                return False, f"High CPU usage: {cpu_percent:.1f}%", duration
            else:
                return True, f"CPU usage: {cpu_percent:.1f}%", duration
                
        except ImportError:
            duration = (time.time() - start_time) * 1000
            return True, "CPU check skipped (psutil not installed)", duration
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return False, f"CPU check error: {str(e)[:100]}", duration
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        checks = {
            'database': self.check_database(),
            'api': self.check_api(),
            'websocket': self.check_websocket(),
            'bot': self.check_bot(),
            'disk': self.check_disk_space(),
            'memory': self.check_memory(),
            'cpu': self.check_cpu(),
        }
        
        results = {}
        overall_healthy = True
        
        for name, check in checks.items():
            try:
                healthy, message, duration = await check
                results[name] = {
                    'healthy': healthy,
                    'message': message,
                    'duration_ms': round(duration, 2)
                }
                if not healthy:
                    overall_healthy = False
            except Exception as e:
                results[name] = {
                    'healthy': False,
                    'message': f"Check failed: {str(e)[:100]}",
                    'duration_ms': 0
                }
                overall_healthy = False
        
        self.results = results
        self.last_status = {
            'healthy': overall_healthy,
            'timestamp': datetime.now().isoformat(),
            'checks': results
        }
        
        return self.last_status
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of health check results."""
        if not self.last_status:
            return {'status': 'unknown', 'message': 'No health checks performed'}
        
        healthy = self.last_status['healthy']
        total_checks = len(self.last_status['checks'])
        failed_checks = sum(1 for c in self.last_status['checks'].values() if not c['healthy'])
        
        return {
            'status': 'healthy' if healthy else 'unhealthy',
            'message': f"{total_checks - failed_checks}/{total_checks} checks passed",
            'failed_checks': failed_checks,
            'timestamp': self.last_status['timestamp']
        }


# ==================== ALERTING ====================

async def send_alert(message: str, severity: str = "WARNING"):
    """Send alert notification (Telegram)."""
    if not config.ADMIN_CHAT_ID or not config.BOT_TOKEN:
        log_message("Alert not sent: Missing bot token or admin chat ID", "WARNING")
        return
    
    emoji = {
        "CRITICAL": "🔴",
        "WARNING": "🟡",
        "INFO": "🔵",
        "SUCCESS": "🟢"
    }.get(severity, "📢")
    
    alert_text = f"{emoji} *Health Alert - {severity}*\n\n{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        api_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        async with aiohttp.ClientSession() as session:
            await session.post(api_url, json={
                'chat_id': config.ADMIN_CHAT_ID,
                'text': alert_text,
                'parse_mode': 'Markdown'
            })
        log_message(f"Alert sent: {severity} - {message[:100]}", "INFO")
    except Exception as e:
        log_message(f"Failed to send alert: {e}", "ERROR")


# ==================== MAIN FUNCTION ====================

async def main():
    """Main entry point for health check script."""
    parser = argparse.ArgumentParser(description='Health check for Estif Bingo 24/7')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')
    parser.add_argument('--alert', '-a', action='store_true', help='Send alert on failure')
    parser.add_argument('--check', '-c', choices=['database', 'api', 'websocket', 'bot', 'all'], 
                        default='all', help='Specific check to run')
    
    args = parser.parse_args()
    
    checker = HealthChecker()
    
    # Run checks
    if args.check == 'all':
        results = await checker.run_all_checks()
    else:
        # Run single check
        check_func = getattr(checker, f"check_{args.check}")
        healthy, message, duration = await check_func()
        results = {
            'healthy': healthy,
            'timestamp': datetime.now().isoformat(),
            'checks': {
                args.check: {
                    'healthy': healthy,
                    'message': message,
                    'duration_ms': round(duration, 2)
                }
            }
        }
    
    # Update consecutive failures
    if results['healthy']:
        checker.consecutive_failures = 0
    else:
        checker.consecutive_failures += 1
    
    # Send alert if needed
    if args.alert and not results['healthy']:
        if checker.consecutive_failures >= HEALTH_CONFIG['alert_threshold']:
            summary = checker.get_summary()
            await send_alert(f"Health check failed!\n\n{summary['message']}\n\nDetails:\n" + 
                           "\n".join([f"- {k}: {v['message']}" for k, v in results['checks'].items() if not v['healthy']]),
                           severity="CRITICAL" if checker.consecutive_failures > 5 else "WARNING")
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    elif not args.quiet:
        print("\n" + "=" * 50)
        print("HEALTH CHECK RESULTS")
        print("=" * 50)
        print(f"Status: {'✅ HEALTHY' if results['healthy'] else '❌ UNHEALTHY'}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        for name, check in results['checks'].items():
            icon = "✅" if check['healthy'] else "❌"
            print(f"{icon} {name.upper()}: {check['message']} ({check['duration_ms']}ms)")
        
        print("=" * 50)
    
    # Exit with appropriate code
    sys.exit(0 if results['healthy'] else 1)


if __name__ == "__main__":
    asyncio.run(main())