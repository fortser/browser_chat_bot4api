"""Task validator - validates task data."""

from typing import Optional
import logging

from ..core.types import TaskCard, TaskSequence

logger = logging.getLogger(__name__)


class TaskValidator:
    """
    Validates task cards and sequences.
    
    Checks for required fields, valid values, etc.
    """
    
    # Validation limits
    MAX_PROMPT_LENGTH = 100000
    MAX_CARDS_PER_SEQUENCE = 1000
    MAX_TIMEOUT = 3600  # 1 hour
    MAX_INTERVAL = 3600  # 1 hour
    
    def validate_card(self, card: TaskCard) -> list[str]:
        """
        Validate a task card.
        
        Args:
            card: Task card to validate
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not card.id:
            errors.append("Card ID is required")
        
        if not card.prompt:
            errors.append("Card prompt is required")
        elif len(card.prompt) > self.MAX_PROMPT_LENGTH:
            errors.append(f"Prompt exceeds maximum length ({self.MAX_PROMPT_LENGTH})")
        
        # Check numeric values
        if card.wait_before < 0:
            errors.append("wait_before cannot be negative")
        elif card.wait_before > self.MAX_INTERVAL:
            errors.append(f"wait_before exceeds maximum ({self.MAX_INTERVAL})")
        
        if card.wait_after < 0:
            errors.append("wait_after cannot be negative")
        elif card.wait_after > self.MAX_INTERVAL:
            errors.append(f"wait_after exceeds maximum ({self.MAX_INTERVAL})")
        
        if card.timeout <= 0:
            errors.append("timeout must be positive")
        elif card.timeout > self.MAX_TIMEOUT:
            errors.append(f"timeout exceeds maximum ({self.MAX_TIMEOUT})")
        
        return errors
    
    def validate_sequence(self, sequence: TaskSequence) -> list[str]:
        """
        Validate a task sequence.
        
        Args:
            sequence: Task sequence to validate
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not sequence.id:
            errors.append("Sequence ID is required")
        
        if not sequence.name:
            errors.append("Sequence name is required")
        
        # Check card count
        if len(sequence.cards) > self.MAX_CARDS_PER_SEQUENCE:
            errors.append(f"Too many cards ({len(sequence.cards)} > {self.MAX_CARDS_PER_SEQUENCE})")
        
        # Check default interval
        if sequence.default_interval < 0:
            errors.append("default_interval cannot be negative")
        elif sequence.default_interval > self.MAX_INTERVAL:
            errors.append(f"default_interval exceeds maximum ({self.MAX_INTERVAL})")
        
        # Validate each card
        card_ids = set()
        for i, card in enumerate(sequence.cards):
            card_errors = self.validate_card(card)
            for error in card_errors:
                errors.append(f"Card {i + 1} ({card.name or 'unnamed'}): {error}")
            
            # Check for duplicate IDs
            if card.id in card_ids:
                errors.append(f"Duplicate card ID: {card.id}")
            card_ids.add(card.id)
        
        return errors
    
    def is_valid_card(self, card: TaskCard) -> bool:
        """Check if a card is valid."""
        return len(self.validate_card(card)) == 0
    
    def is_valid_sequence(self, sequence: TaskSequence) -> bool:
        """Check if a sequence is valid."""
        return len(self.validate_sequence(sequence)) == 0
