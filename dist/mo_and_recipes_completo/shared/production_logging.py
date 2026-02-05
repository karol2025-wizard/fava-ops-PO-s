"""
Production Logging & Safety Module

This module provides logging and retry logic for MRPeasy updates.

Requirements:
- Log all updates: Lot Code, MO Number, Quantity, Status change
- Add retry logic if MRPeasy is temporarily unavailable
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Tuple
from shared.json_storage import JSONStorage

logger = logging.getLogger(__name__)


class ProductionLogger:
    """Log production updates and operations"""
    
    def __init__(self, storage: Optional[JSONStorage] = None):
        self.storage = storage or JSONStorage()
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Ensure logger has a handler
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
    
    def log_production_update(
        self,
        lot_code: str,
        mo_number: str,
        mo_id: int,
        quantity: float,
        status_before: Optional[int] = None,
        status_after: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Log a production update operation.
        
        Args:
            lot_code: Lot Code
            mo_number: MO Number
            mo_id: MO ID
            quantity: Produced quantity
            status_before: Status before update (optional)
            status_after: Status after update (optional)
            success: Whether the update was successful
            error_message: Error message if update failed
            timestamp: Timestamp of the update (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'lot_code': lot_code,
            'mo_number': mo_number,
            'mo_id': mo_id,
            'quantity': quantity,
            'status_before': status_before,
            'status_after': status_after,
            'success': success,
            'error_message': error_message
        }
        
        if success:
            status_change = ""
            if status_before is not None and status_after is not None:
                status_change = f" (Status: {status_before} → {status_after})"
            
            log_message = (
                f"Production update SUCCESS - "
                f"Lot: {lot_code}, MO: {mo_number} (ID: {mo_id}), "
                f"Quantity: {quantity}{status_change}"
            )
            logger.info(log_message)
        else:
            log_message = (
                f"Production update FAILED - "
                f"Lot: {lot_code}, MO: {mo_number} (ID: {mo_id}), "
                f"Quantity: {quantity}, Error: {error_message}"
            )
            logger.error(log_message)
        
        # Store in JSON file for audit trail
        self.storage.save_production_log(
            lot_code=lot_code,
            mo_number=mo_number,
            mo_id=mo_id,
            quantity=quantity,
            status_before=status_before,
            status_after=status_after,
            success=success,
            error_message=error_message
        )
        
        return log_entry


class RetryHandler:
    """Handle retries for MRPeasy API calls"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0
    ):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries (seconds)
            backoff_factor: Multiplier for delay between retries
            max_delay: Maximum delay between retries (seconds)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        
        Returns:
            Tuple of (success, result, error_message)
        """
        last_exception = None
        delay = self.initial_delay
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                # If result is a tuple (success, data, message), check success
                if isinstance(result, tuple) and len(result) >= 1:
                    success = result[0]
                    if success:
                        logger.info(f"Operation succeeded on attempt {attempt + 1}")
                        return result
                    else:
                        # Function returned failure but no exception
                        # Check if it's a retryable error
                        error_msg = result[2] if len(result) > 2 else "Unknown error"
                        if self._is_retryable_error(error_msg):
                            if attempt < self.max_retries:
                                logger.warning(
                                    f"Retryable error on attempt {attempt + 1}: {error_msg}. "
                                    f"Retrying in {delay:.1f} seconds..."
                                )
                                time.sleep(delay)
                                delay = min(delay * self.backoff_factor, self.max_delay)
                                continue
                        # Non-retryable error or max retries reached
                        return result
                else:
                    # Function returned success (no tuple)
                    logger.info(f"Operation succeeded on attempt {attempt + 1}")
                    return True, result, None
                    
            except Exception as e:
                last_exception = e
                error_msg = str(e)
                
                if self._is_retryable_error(error_msg):
                    if attempt < self.max_retries:
                        logger.warning(
                            f"Retryable exception on attempt {attempt + 1}: {error_msg}. "
                            f"Retrying in {delay:.1f} seconds..."
                        )
                        time.sleep(delay)
                        delay = min(delay * self.backoff_factor, self.max_delay)
                    else:
                        logger.error(
                            f"Max retries ({self.max_retries}) reached. "
                            f"Final error: {error_msg}"
                        )
                        return False, None, error_msg
                else:
                    # Non-retryable error
                    logger.error(f"Non-retryable error: {error_msg}")
                    return False, None, error_msg
        
        # Should not reach here, but handle it anyway
        final_error = str(last_exception) if last_exception else "Unknown error"
        return False, None, final_error
    
    def _is_retryable_error(self, error_message: str) -> bool:
        """
        Determine if an error is retryable (temporary/unavailable).
        
        Args:
            error_message: Error message to check
        
        Returns:
            True if error is retryable, False otherwise
        """
        if not error_message:
            return False
        
        error_lower = error_message.lower()
        
        # Retryable errors (temporary issues)
        retryable_patterns = [
            'timeout',
            'connection',
            'unavailable',
            'temporary',
            '503',  # Service Unavailable
            '504',  # Gateway Timeout
            '502',  # Bad Gateway
            '500',  # Internal Server Error (might be temporary)
            'network',
            'dns',
            'refused'
        ]
        
        # Non-retryable errors (permanent issues)
        non_retryable_patterns = [
            'not found',
            '404',  # Not Found
            '401',  # Unauthorized
            '403',  # Forbidden
            '400',  # Bad Request
            'invalid',
            'validation',
            'authentication',
            'authorization'
        ]
        
        # Check non-retryable first
        for pattern in non_retryable_patterns:
            if pattern in error_lower:
                return False
        
        # Check retryable
        for pattern in retryable_patterns:
            if pattern in error_lower:
                return True
        
        # Default: assume retryable for unknown errors
        # (better to retry than fail immediately)
        return True

