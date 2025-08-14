#!/usr/bin/env python3
"""
Template for Python files in SRT Translator project.
Copy this template and modify as needed for new files.
"""

import logging
import sys
from typing import Any

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger for this module
logger = logging.getLogger(__name__)


class ExampleClass:
    """Example class demonstrating proper logging usage."""
    
    def __init__(self, name: str):
        """Initialize the example class.
        
        Args:
            name: The name for this instance
        """
        self.name = name
        logger.info(f"Initialized {self.__class__.__name__} with name: {name}")
    
    def do_something(self, value: Any) -> bool:
        """Example method showing logging usage.
        
        Args:
            value: Some value to process
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If value is invalid
        """
        logger.debug(f"Processing value: {value}")
        
        try:
            if value is None:
                logger.warning("Received None value, using default")
                value = "default"
            
            # Do some work
            result = self._process_value(value)
            logger.info(f"Successfully processed value: {value} -> {result}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process value {value}: {e}")
            return False
    
    def _process_value(self, value: Any) -> str:
        """Private method example.
        
        Args:
            value: Value to process
            
        Returns:
            Processed string value
        """
        logger.debug(f"Processing value in private method: {value}")
        return str(value).upper()


def example_function(param: str) -> str:
    """Example function demonstrating logging.
    
    Args:
        param: Input parameter
        
    Returns:
        Processed result
        
    Raises:
        ValueError: If param is empty
    """
    logger.info(f"Function called with param: {param}")
    
    if not param:
        logger.error("Empty parameter provided")
        raise ValueError("Parameter cannot be empty")
    
    result = f"Processed: {param}"
    logger.info(f"Function completed successfully: {result}")
    return result


def main() -> int:
    """Main function example.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("Starting example application")
    
    try:
        # Example usage
        example = ExampleClass("TestInstance")
        success = example.do_something("hello")
        
        if success:
            result = example_function("world")
            logger.info(f"Application completed successfully: {result}")
            return 0
        else:
            logger.error("Application failed during processing")
            return 1
            
    except Exception as e:
        logger.error(f"Application failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
