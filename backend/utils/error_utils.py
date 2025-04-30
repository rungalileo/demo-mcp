from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

class GongAPIError(Exception):
    """Base exception for Gong API related errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

class ValidationError(Exception):
    """Exception for input validation errors"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class AnalysisError(Exception):
    """Exception for analysis related errors"""
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

def handle_api_error(response, operation: str) -> None:
    """Handle API response errors consistently"""
    if not response.ok:
        status_code = response.status_code
        logger.error(f"API Error during {operation}: {status_code}")
        raise GongAPIError(
            message=f"Failed to {operation} (Status: {status_code})",
            status_code=status_code
        )

def validate_input(value: Any, field_name: str, validation_func: callable, error_message: str) -> None:
    """Validate input values consistently"""
    if not validation_func(value):
        logger.error(f"Validation error for {field_name}: {error_message}")
        raise ValidationError(f"{field_name}: {error_message}")

def log_and_raise_error(error: Exception, operation: str, include_details: bool = False) -> None:
    """Log and raise errors consistently"""
    if include_details:
        logger.error(f"Error during {operation}: {str(error)}", exc_info=True)
    else:
        logger.error(f"Error during {operation}")
    
    if isinstance(error, (ValidationError, GongAPIError, AnalysisError)):
        raise error
    else:
        raise Exception(f"An error occurred during {operation}") 