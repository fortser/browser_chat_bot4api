"""Tests for adapters module."""

import pytest

from chatflow.adapters import get_adapter, list_adapters, register_adapter
from chatflow.adapters.base import ChatAdapter
from chatflow.adapters.generic import GenericAdapter, GenericSelectors


class TestAdapterRegistry:
    """Tests for adapter registry."""
    
    def test_list_adapters(self):
        """Test listing available adapters."""
        adapters = list_adapters()
        assert "generic" in adapters
    
    def test_get_adapter(self):
        """Test getting adapter by name."""
        adapter_class = get_adapter("generic")
        assert adapter_class == GenericAdapter
    
    def test_get_unknown_adapter(self):
        """Test getting unknown adapter raises error."""
        with pytest.raises(ValueError):
            get_adapter("nonexistent_adapter")


class TestGenericSelectors:
    """Tests for GenericSelectors."""
    
    def test_default_selectors(self):
        """Test default selector values."""
        selectors = GenericSelectors()
        assert selectors.input_field == "textarea"
        assert selectors.send_button == "button[type='submit']"
    
    def test_selectors_from_dict(self):
        """Test creating selectors from dict."""
        data = {
            "input_field": "#custom-input",
            "send_button": ".custom-send",
        }
        selectors = GenericSelectors.from_dict(data)
        
        assert selectors.input_field == "#custom-input"
        assert selectors.send_button == ".custom-send"
        # Default for unspecified
        assert selectors.stop_button == "button[aria-label='Stop']"
    
    def test_selectors_to_dict(self):
        """Test converting selectors to dict."""
        selectors = GenericSelectors()
        data = selectors.to_dict()
        
        assert "input_field" in data
        assert "send_button" in data
        assert "response_container" in data
