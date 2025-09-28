"""
Performance monitoring and health checks for Local Radar
Provides metrics collection, resource monitoring, and system health validation
"""

import os
import time
import psutil
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
import threading
from collections import deque

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    cpu_percent: float
    memory_used_mb: float
    memory_percent: float
    disk_used_gb: float
    disk_percent: float
    process_count: int
    open_files: int
    network_connections: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_used_mb': self.memory_used_mb,
            'memory_percent': self.memory_percent,
            'disk_used_gb': self.disk_used_gb,
            'disk_percent': self.disk_percent,
            'process_count': self.process_count,
            'open_files': self.open_files,
            'network_connections': self.network_connections
        }


@dataclass
class OperationMetrics:
    """Metrics for specific operations"""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def finish(self, success: bool = True, error_message: str = None):
        """Mark operation as finished"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'operation_name': self.operation_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.metadata
        }


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self, max_metrics_history: int = 1000):
        self.max_metrics_history = max_metrics_history
        self.metrics_history = deque(maxlen=max_metrics_history)
        self.operation_metrics = deque(maxlen=max_metrics_history)
        self._lock = threading.RLock()
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_interval = 30  # seconds
        
        # Thresholds for alerts
        self.cpu_threshold = 80.0  # percent
        self.memory_threshold = 85.0  # percent
        self.disk_threshold = 90.0  # percent
        
    def start_monitoring(self, interval: int = 30):
        """Start background performance monitoring"""
        with self._lock:
            if self.monitoring_active:
                return
            
            self.monitoring_interval = interval
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            logger.info(f"Performance monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop background performance monitoring"""
        with self._lock:
            self.monitoring_active = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=5)
            logger.info("Performance monitoring stopped")
    
    def collect_system_metrics(self) -> PerformanceMetrics:
        """Collect current system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_used_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_percent = (disk.used / disk.total) * 100
            
            # Process metrics
            process_count = len(psutil.pids())
            
            # File and network metrics
            try:
                current_process = psutil.Process()
                open_files = len(current_process.open_files()) if current_process.open_files() else 0
                network_connections = len(current_process.connections()) if current_process.connections() else 0
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                open_files = 0
                network_connections = 0
            
            return PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_used_mb=memory_used_mb,
                memory_percent=memory_percent,
                disk_used_gb=disk_used_gb,
                disk_percent=disk_percent,
                process_count=process_count,
                open_files=open_files,
                network_connections=network_connections
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return None
    
    def record_metrics(self, metrics: PerformanceMetrics):
        """Record performance metrics"""
        with self._lock:
            self.metrics_history.append(metrics)
            
            # Check for threshold violations
            self._check_thresholds(metrics)
    
    def start_operation(self, operation_name: str, metadata: Dict[str, Any] = None) -> OperationMetrics:
        """Start tracking an operation"""
        operation = OperationMetrics(
            operation_name=operation_name,
            start_time=datetime.now(),
            metadata=metadata or {}
        )
        return operation
    
    def finish_operation(self, operation: OperationMetrics, success: bool = True, error_message: str = None):
        """Finish tracking an operation"""
        operation.finish(success, error_message)
        
        with self._lock:
            self.operation_metrics.append(operation)
        
        # Log slow operations
        if operation.duration_ms and operation.duration_ms > 5000:  # 5 seconds
            logger.warning(f"Slow operation detected: {operation.operation_name} took {operation.duration_ms:.1f}ms")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current system health status"""
        with self._lock:
            if not self.metrics_history:
                return {'status': 'unknown', 'message': 'No metrics available'}
            
            latest_metrics = self.metrics_history[-1]
            issues = []
            
            # Check system resources
            if latest_metrics.cpu_percent > self.cpu_threshold:
                issues.append(f"High CPU usage: {latest_metrics.cpu_percent:.1f}%")
            
            if latest_metrics.memory_percent > self.memory_threshold:
                issues.append(f"High memory usage: {latest_metrics.memory_percent:.1f}%")
            
            if latest_metrics.disk_percent > self.disk_threshold:
                issues.append(f"High disk usage: {latest_metrics.disk_percent:.1f}%")
            
            # Check recent operation failures
            recent_ops = [op for op in self.operation_metrics if 
                         op.end_time and op.end_time > datetime.now() - timedelta(minutes=10)]
            
            failed_ops = [op for op in recent_ops if not op.success]
            if len(failed_ops) > len(recent_ops) * 0.2:  # More than 20% failures
                issues.append(f"High operation failure rate: {len(failed_ops)}/{len(recent_ops)}")
            
            if issues:
                return {
                    'status': 'warning' if len(issues) <= 2 else 'critical',
                    'issues': issues,
                    'metrics': latest_metrics.to_dict()
                }
            else:
                return {
                    'status': 'healthy',
                    'message': 'All systems operating normally',
                    'metrics': latest_metrics.to_dict()
                }
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the specified time period"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
            recent_operations = [op for op in self.operation_metrics if 
                               op.start_time > cutoff_time and op.end_time is not None]
            
            if not recent_metrics:
                return {'error': 'No metrics available for the specified period'}
            
            # Calculate averages
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            avg_disk = sum(m.disk_percent for m in recent_metrics) / len(recent_metrics)
            
            # Calculate operation statistics
            successful_ops = [op for op in recent_operations if op.success]
            failed_ops = [op for op in recent_operations if not op.success]
            
            op_durations = [op.duration_ms for op in successful_ops if op.duration_ms is not None]
            avg_duration = sum(op_durations) / len(op_durations) if op_durations else 0
            
            return {
                'period_hours': hours,
                'metrics_count': len(recent_metrics),
                'system_averages': {
                    'cpu_percent': round(avg_cpu, 2),
                    'memory_percent': round(avg_memory, 2),
                    'disk_percent': round(avg_disk, 2)
                },
                'operations': {
                    'total': len(recent_operations),
                    'successful': len(successful_ops),
                    'failed': len(failed_ops),
                    'success_rate': round(len(successful_ops) / len(recent_operations) * 100, 2) if recent_operations else 0,
                    'avg_duration_ms': round(avg_duration, 2)
                }
            }
    
    def export_metrics(self, output_file: str = None) -> str:
        """Export metrics to JSON file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"local_radar_metrics_{timestamp}.json"
        
        output_path = Path(config.report.output_dir) / output_file
        
        with self._lock:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'metrics_count': len(self.metrics_history),
                'operations_count': len(self.operation_metrics),
                'health_status': self.get_health_status(),
                'performance_summary': self.get_performance_summary(),
                'metrics': [m.to_dict() for m in self.metrics_history],
                'operations': [op.to_dict() for op in self.operation_metrics]
            }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Metrics exported to {output_path}")
        return str(output_path)
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                metrics = self.collect_system_metrics()
                if metrics:
                    self.record_metrics(metrics)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Brief pause before retrying
    
    def _check_thresholds(self, metrics: PerformanceMetrics):
        """Check if metrics exceed thresholds and log warnings"""
        if metrics.cpu_percent > self.cpu_threshold:
            logger.warning(f"High CPU usage detected: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_percent > self.memory_threshold:
            logger.warning(f"High memory usage detected: {metrics.memory_percent:.1f}%")
        
        if metrics.disk_percent > self.disk_threshold:
            logger.warning(f"High disk usage detected: {metrics.disk_percent:.1f}%")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_operation(operation_name: str):
    """Decorator to monitor operation performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            operation = performance_monitor.start_operation(operation_name, {
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_count': len(kwargs)
            })
            
            try:
                result = func(*args, **kwargs)
                performance_monitor.finish_operation(operation, success=True)
                return result
            except Exception as e:
                performance_monitor.finish_operation(operation, success=False, error_message=str(e))
                raise
        return wrapper
    return decorator


class HealthChecker:
    """System health checking utilities"""
    
    @staticmethod
    def check_dependencies() -> Dict[str, Any]:
        """Check availability of optional dependencies"""
        dependencies = {
            'sentence_transformers': False,
            'faiss': False,
            'sklearn': False,
            'nltk': False,
            'tesseract': False,
            'pymupdf': False,
            'pillow': False
        }
        
        try:
            import sentence_transformers
            dependencies['sentence_transformers'] = True
        except ImportError:
            pass
        
        try:
            import faiss
            dependencies['faiss'] = True
        except ImportError:
            pass
        
        try:
            import sklearn
            dependencies['sklearn'] = True
        except ImportError:
            pass
        
        try:
            import nltk
            dependencies['nltk'] = True
        except ImportError:
            pass
        
        try:
            import pytesseract
            dependencies['tesseract'] = True
        except ImportError:
            pass
        
        try:
            import fitz
            dependencies['pymupdf'] = True
        except ImportError:
            pass
        
        try:
            import PIL
            dependencies['pillow'] = True
        except ImportError:
            pass
        
        return dependencies
    
    @staticmethod
    def check_directories() -> Dict[str, Any]:
        """Check if required directories exist and are writable"""
        directories = {
            'reports': config.report.output_dir,
            'templates': config.report.template_dir,
            'static': config.report.static_dir,
            'pdf_output': config.pdf.output_dir,
            'vector_index': config.vector.index_dir
        }
        
        results = {}
        for name, path in directories.items():
            path_obj = Path(path)
            results[name] = {
                'path': str(path),
                'exists': path_obj.exists(),
                'is_directory': path_obj.is_dir() if path_obj.exists() else False,
                'writable': os.access(path, os.W_OK) if path_obj.exists() else False
            }
        
        return results
    
    @staticmethod
    def check_disk_space() -> Dict[str, Any]:
        """Check available disk space"""
        try:
            usage = psutil.disk_usage('/')
            return {
                'total_gb': round(usage.total / (1024**3), 2),
                'used_gb': round(usage.used / (1024**3), 2),
                'free_gb': round(usage.free / (1024**3), 2),
                'percent_used': round((usage.used / usage.total) * 100, 2)
            }
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def run_full_health_check() -> Dict[str, Any]:
        """Run comprehensive health check"""
        return {
            'timestamp': datetime.now().isoformat(),
            'dependencies': HealthChecker.check_dependencies(),
            'directories': HealthChecker.check_directories(),
            'disk_space': HealthChecker.check_disk_space(),
            'performance': performance_monitor.get_health_status(),
            'config_valid': True  # Add config validation if needed
        }