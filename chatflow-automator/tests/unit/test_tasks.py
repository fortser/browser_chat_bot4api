"""Tests for tasks module."""

import pytest
from pathlib import Path

from chatflow.core.types import TaskCard, TaskSequence, generate_id
from chatflow.tasks.loader import TaskLoader
from chatflow.tasks.validator import TaskValidator


class TestTaskCard:
    """Tests for TaskCard."""
    
    def test_create_card(self):
        """Test creating a task card."""
        card = TaskCard(name="Test", prompt="Hello")
        assert card.name == "Test"
        assert card.prompt == "Hello"
        assert card.enabled is True
        assert card.id.startswith("card_")
    
    def test_card_to_dict(self, sample_task_card):
        """Test converting card to dict."""
        data = sample_task_card.to_dict()
        assert data["name"] == "Test Card"
        assert data["prompt"] == "Hello, how are you?"
        assert data["enabled"] is True
    
    def test_card_from_dict(self):
        """Test creating card from dict."""
        data = {
            "id": "card_123",
            "name": "From Dict",
            "prompt": "Test prompt",
            "wait_after": 10,
        }
        card = TaskCard.from_dict(data)
        assert card.id == "card_123"
        assert card.name == "From Dict"
        assert card.wait_after == 10


class TestTaskSequence:
    """Tests for TaskSequence."""
    
    def test_create_sequence(self):
        """Test creating a sequence."""
        seq = TaskSequence(name="Test Sequence")
        assert seq.name == "Test Sequence"
        assert len(seq.cards) == 0
    
    def test_add_card(self, sample_sequence, sample_task_card):
        """Test adding a card."""
        initial_count = len(sample_sequence.cards)
        new_card = TaskCard(name="New", prompt="New prompt")
        sample_sequence.add_card(new_card)
        assert len(sample_sequence.cards) == initial_count + 1
    
    def test_remove_card(self, sample_sequence):
        """Test removing a card."""
        initial_count = len(sample_sequence.cards)
        card_id = sample_sequence.cards[0].id
        result = sample_sequence.remove_card(card_id)
        assert result is True
        assert len(sample_sequence.cards) == initial_count - 1
    
    def test_enabled_cards(self, sample_sequence):
        """Test getting enabled cards."""
        enabled = sample_sequence.enabled_cards
        assert len(enabled) == 2  # One card is disabled
    
    def test_move_card(self, sample_sequence):
        """Test moving a card."""
        first_id = sample_sequence.cards[0].id
        second_id = sample_sequence.cards[1].id
        
        sample_sequence.move_card(first_id, 1)  # Move down
        
        assert sample_sequence.cards[0].id == second_id
        assert sample_sequence.cards[1].id == first_id


class TestTaskLoader:
    """Tests for TaskLoader."""
    
    def test_create_from_prompts(self):
        """Test creating sequence from prompts."""
        loader = TaskLoader()
        prompts = ["First prompt", "Second prompt", "Third prompt"]
        seq = loader.create_from_prompts(prompts, name="Test")
        
        assert seq.name == "Test"
        assert len(seq.cards) == 3
        assert seq.cards[0].prompt == "First prompt"
    
    def test_load_from_json(self, temp_dir):
        """Test loading from JSON file."""
        import json
        
        data = {
            "sequence": {
                "name": "JSON Sequence",
                "cards": [
                    {"name": "Card 1", "prompt": "Prompt 1"},
                    {"name": "Card 2", "prompt": "Prompt 2"},
                ]
            }
        }
        
        file_path = temp_dir / "test.json"
        with open(file_path, "w") as f:
            json.dump(data, f)
        
        loader = TaskLoader()
        seq = loader.load_from_file(file_path)
        
        assert seq.name == "JSON Sequence"
        assert len(seq.cards) == 2
    
    def test_load_from_txt(self, temp_dir):
        """Test loading from text file."""
        file_path = temp_dir / "prompts.txt"
        with open(file_path, "w") as f:
            f.write("First prompt\n")
            f.write("Second prompt\n")
            f.write("# This is a comment\n")
            f.write("Third prompt\n")
        
        loader = TaskLoader()
        seq = loader.load_from_file(file_path)
        
        assert len(seq.cards) == 3


class TestTaskValidator:
    """Tests for TaskValidator."""
    
    def test_valid_card(self, sample_task_card):
        """Test validating a valid card."""
        validator = TaskValidator()
        errors = validator.validate_card(sample_task_card)
        assert len(errors) == 0
    
    def test_invalid_card_no_prompt(self):
        """Test validating card without prompt."""
        validator = TaskValidator()
        card = TaskCard(name="Test", prompt="")
        errors = validator.validate_card(card)
        assert len(errors) > 0
        assert any("prompt" in e.lower() for e in errors)
    
    def test_invalid_card_negative_timeout(self):
        """Test validating card with negative timeout."""
        validator = TaskValidator()
        card = TaskCard(name="Test", prompt="Hello", timeout=-1)
        errors = validator.validate_card(card)
        assert len(errors) > 0
    
    def test_valid_sequence(self, sample_sequence):
        """Test validating a valid sequence."""
        validator = TaskValidator()
        errors = validator.validate_sequence(sample_sequence)
        assert len(errors) == 0
