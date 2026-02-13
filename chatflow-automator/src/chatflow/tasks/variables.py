"""Variable system for prompt templates."""

import re
from typing import Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VariableProcessor:
    """
    Processes variables in prompt templates.
    
    Supports:
    - {variable_name} syntax
    - Built-in variables (date, time, etc.)
    - Custom variables
    """
    
    # Pattern for variable placeholders
    VARIABLE_PATTERN = re.compile(r'\{(\w+)\}')
    
    def __init__(self):
        self.custom_variables: dict[str, str] = {}
    
    def set_variable(self, name: str, value: str) -> None:
        """Set a custom variable."""
        self.custom_variables[name] = value
    
    def set_variables(self, variables: dict[str, str]) -> None:
        """Set multiple custom variables."""
        self.custom_variables.update(variables)
    
    def clear_variables(self) -> None:
        """Clear all custom variables."""
        self.custom_variables.clear()
    
    def get_builtin_variables(self) -> dict[str, str]:
        """Get built-in variables with current values."""
        now = datetime.now()
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "year": now.strftime("%Y"),
            "month": now.strftime("%m"),
            "day": now.strftime("%d"),
            "hour": now.strftime("%H"),
            "minute": now.strftime("%M"),
        }
    
    def process(self, text: str) -> str:
        """
        Process variables in text.
        
        Args:
            text: Text with variable placeholders
            
        Returns:
            Text with variables replaced
        """
        # Combine all variables
        all_vars = {
            **self.get_builtin_variables(),
            **self.custom_variables,
        }
        
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name in all_vars:
                return all_vars[var_name]
            else:
                logger.warning(f"Unknown variable: {var_name}")
                return match.group(0)  # Keep original
        
        return self.VARIABLE_PATTERN.sub(replace_var, text)
    
    def find_variables(self, text: str) -> list[str]:
        """
        Find all variable names in text.
        
        Args:
            text: Text to search
            
        Returns:
            List of variable names
        """
        matches = self.VARIABLE_PATTERN.findall(text)
        return list(set(matches))
    
    def validate_variables(self, text: str) -> list[str]:
        """
        Find undefined variables in text.
        
        Args:
            text: Text to check
            
        Returns:
            List of undefined variable names
        """
        all_vars = {
            **self.get_builtin_variables(),
            **self.custom_variables,
        }
        
        used_vars = self.find_variables(text)
        undefined = [v for v in used_vars if v not in all_vars]
        
        return undefined
