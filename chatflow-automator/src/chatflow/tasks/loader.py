"""Task loader - loading tasks from various formats."""

import json
from pathlib import Path
from typing import Union
import logging

import yaml

from ..core.types import TaskCard, TaskSequence, generate_id
from ..core.exceptions import StorageError, ValidationError
from .validator import TaskValidator

logger = logging.getLogger(__name__)


class TaskLoader:
    """
    Loads task sequences from various file formats.
    
    Supports JSON, YAML, and plain text (prompt lists).
    """
    
    def __init__(self):
        self.validator = TaskValidator()
    
    def load_from_file(self, file_path: Union[str, Path]) -> TaskSequence:
        """
        Load a task sequence from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            TaskSequence object
            
        Raises:
            StorageError: If file cannot be read
            ValidationError: If content is invalid
        """
        path = Path(file_path)
        
        if not path.exists():
            raise StorageError(f"File not found: {path}")
        
        suffix = path.suffix.lower()
        
        if suffix == ".json":
            return self._load_json(path)
        elif suffix in (".yaml", ".yml"):
            return self._load_yaml(path)
        elif suffix == ".txt":
            return self._load_prompts_txt(path)
        else:
            raise StorageError(f"Unsupported file format: {suffix}")
    
    def _load_json(self, path: Path) -> TaskSequence:
        """Load from JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return self._parse_sequence_data(data, path.stem)
            
        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON: {e}")
    
    def _load_yaml(self, path: Path) -> TaskSequence:
        """Load from YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            return self._parse_sequence_data(data, path.stem)
            
        except yaml.YAMLError as e:
            raise StorageError(f"Invalid YAML: {e}")
    
    def _load_prompts_txt(self, path: Path) -> TaskSequence:
        """
        Load from plain text file.
        
        Each non-empty line becomes a task card.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            cards = []
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith("#"):  # Skip empty and comments
                    cards.append(TaskCard(
                        id=generate_id("card"),
                        name=f"Prompt {i}",
                        prompt=line,
                    ))
            
            sequence = TaskSequence(
                id=generate_id("seq"),
                name=path.stem,
                description=f"Loaded from {path.name}",
                cards=cards,
            )
            
            logger.info(f"Loaded {len(cards)} prompts from {path}")
            return sequence
            
        except Exception as e:
            raise StorageError(f"Failed to read file: {e}")
    
    def _parse_sequence_data(self, data: dict, default_name: str) -> TaskSequence:
        """Parse sequence data from dict."""
        # Handle both flat and nested formats
        if "sequence" in data:
            seq_data = data["sequence"]
        else:
            seq_data = data
        
        # Create sequence
        sequence = TaskSequence.from_dict(seq_data)
        
        # Set name if not present
        if not sequence.name:
            sequence.name = default_name
        
        # Validate
        errors = self.validator.validate_sequence(sequence)
        if errors:
            raise ValidationError(f"Invalid sequence: {errors}")
        
        logger.info(f"Loaded sequence '{sequence.name}' with {len(sequence.cards)} cards")
        return sequence
    
    def save_to_file(
        self,
        sequence: TaskSequence,
        file_path: Union[str, Path],
        format: str = "json"
    ) -> None:
        """
        Save a task sequence to a file.
        
        Args:
            sequence: TaskSequence to save
            file_path: Path to save to
            format: Output format (json, yaml)
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "version": "1.0",
            "sequence": sequence.to_dict(),
        }
        
        if format == "json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif format in ("yaml", "yml"):
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        else:
            raise StorageError(f"Unsupported format: {format}")
        
        logger.info(f"Saved sequence to {path}")
    
    def create_from_prompts(
        self,
        prompts: list[str],
        name: str = "Prompt Sequence",
        default_interval: int = 15
    ) -> TaskSequence:
        """
        Create a sequence from a list of prompt strings.
        
        Args:
            prompts: List of prompt texts
            name: Sequence name
            default_interval: Default wait_after value
            
        Returns:
            TaskSequence object
        """
        cards = []
        for i, prompt in enumerate(prompts, 1):
            if prompt.strip():
                cards.append(TaskCard(
                    id=generate_id("card"),
                    name=f"Task {i}",
                    prompt=prompt.strip(),
                    wait_after=default_interval,
                ))
        
        return TaskSequence(
            id=generate_id("seq"),
            name=name,
            cards=cards,
            default_interval=default_interval,
        )
