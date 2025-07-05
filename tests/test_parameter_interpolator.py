"""Tests for ParameterInterpolator class."""

import pytest
import json
from unittest.mock import patch
from modules.eventbus.parameter_interpolator import ParameterInterpolator, create_interpolator


class TestParameterInterpolator:
    """Test cases for ParameterInterpolator class."""
    
    def test_init_with_context(self):
        """Test initialization with context."""
        context = {"key": "value"}
        interpolator = ParameterInterpolator(context)
        assert interpolator.context == context
    
    def test_interpolate_primitive_values(self):
        """Test interpolation of primitive values (no change)."""
        interpolator = ParameterInterpolator({})
        
        # Test primitive values pass through unchanged
        assert interpolator.interpolate(42) == 42
        assert interpolator.interpolate(3.14) == 3.14
        assert interpolator.interpolate(True) is True
        assert interpolator.interpolate(None) is None
    
    def test_interpolate_string_without_expressions(self):
        """Test interpolation of strings without expressions."""
        interpolator = ParameterInterpolator({})
        
        text = "Hello world"
        assert interpolator.interpolate(text) == text
    
    def test_interpolate_single_expression_string(self):
        """Test interpolation of string that is entirely a single expression."""
        context = {
            "tools": {
                "now": {"result": "2023-01-01T00:00:00Z"}
            }
        }
        interpolator = ParameterInterpolator(context)
        
        # Single expression returns actual value
        result = interpolator.interpolate("{tools.now.result}")
        assert result == "2023-01-01T00:00:00Z"
        
        # Test with complex data
        context["data"] = {"result": {"key": "value", "list": [1, 2, 3]}}
        result = interpolator.interpolate("{data.result}")
        assert result == {"key": "value", "list": [1, 2, 3]}
    
    def test_interpolate_multiple_expressions_in_string(self):
        """Test interpolation of strings with multiple expressions."""
        context = {
            "user": {"result": "John"},
            "age": {"result": 30}
        }
        interpolator = ParameterInterpolator(context)
        
        text = "Hello {user.result}, you are {age.result} years old"
        result = interpolator.interpolate(text)
        assert result == "Hello John, you are 30 years old"
    
    def test_interpolate_dict(self):
        """Test interpolation of dictionary values."""
        context = {
            "name": {"result": "Alice"},
            "settings": {"result": {"theme": "dark"}}
        }
        interpolator = ParameterInterpolator(context)
        
        data = {
            "greeting": "Hello {name.result}",
            "config": "{settings.result}",
            "static": "unchanged"
        }
        
        result = interpolator.interpolate(data)
        expected = {
            "greeting": "Hello Alice",
            "config": {"theme": "dark"},
            "static": "unchanged"
        }
        assert result == expected
    
    def test_interpolate_list(self):
        """Test interpolation of list values."""
        context = {
            "first": {"result": "item1"},
            "second": {"result": "item2"}
        }
        interpolator = ParameterInterpolator(context)
        
        data = ["{first.result}", "{second.result}", "static"]
        result = interpolator.interpolate(data)
        assert result == ["item1", "item2", "static"]
    
    def test_interpolate_nested_structures(self):
        """Test interpolation of nested dict/list structures."""
        context = {
            "user": {"result": {"name": "Bob", "id": 123}},
            "count": {"result": 5}
        }
        interpolator = ParameterInterpolator(context)
        
        data = {
            "user_info": {
                "name": "{user.result.name}",
                "details": ["{user.result.id}", "{count.result}"]
            }
        }
        
        result = interpolator.interpolate(data)
        expected = {
            "user_info": {
                "name": "Bob",
                "details": [123, 5]
            }
        }
        assert result == expected
    
    def test_resolve_path_simple(self):
        """Test resolving simple dot notation paths."""
        context = {
            "tools": {
                "now": {"result": "2023-01-01"}
            }
        }
        interpolator = ParameterInterpolator(context)
        
        result = interpolator._resolve_path("tools.now.result")
        assert result == "2023-01-01"
    
    def test_resolve_path_with_array_index(self):
        """Test resolving paths with array indices."""
        context = {
            "team": {
                "members": [
                    {"name": "Alice", "role": "dev"},
                    {"name": "Bob", "role": "admin"}
                ]
            }
        }
        interpolator = ParameterInterpolator(context)
        
        assert interpolator._resolve_path("team.members[0].name") == "Alice"
        assert interpolator._resolve_path("team.members[1].role") == "admin"
    
    def test_resolve_path_complex_arrays(self):
        """Test resolving complex array paths."""
        context = {
            "data": [
                {"items": [{"value": "first"}, {"value": "second"}]},
                {"items": [{"value": "third"}]}
            ]
        }
        interpolator = ParameterInterpolator(context)
        
        assert interpolator._resolve_path("data[0].items[1].value") == "second"
        assert interpolator._resolve_path("data[1].items[0].value") == "third"
    
    def test_resolve_path_key_error(self):
        """Test path resolution with missing keys."""
        context = {"existing": {"key": "value"}}
        interpolator = ParameterInterpolator(context)
        
        with pytest.raises(KeyError):
            interpolator._resolve_path("missing.key")
        
        with pytest.raises(KeyError):
            interpolator._resolve_path("existing.missing")
    
    def test_resolve_path_array_index_error(self):
        """Test path resolution with invalid array indices."""
        context = {"array": [1, 2, 3]}
        interpolator = ParameterInterpolator(context)
        
        with pytest.raises(KeyError):
            interpolator._resolve_path("array[5]")
        
        # Test that negative indices work (Python standard behavior)
        assert interpolator._resolve_path("array[-1]") == 3
    
    def test_parse_path_simple(self):
        """Test parsing simple dot notation paths."""
        interpolator = ParameterInterpolator({})
        
        result = interpolator._parse_path("tools.now.result")
        assert result == ["tools", "now", "result"]
    
    def test_parse_path_with_arrays(self):
        """Test parsing paths with array indices."""
        interpolator = ParameterInterpolator({})
        
        result = interpolator._parse_path("team.members[0].name")
        assert result == ["team", "members", 0, "name"]
        
        result = interpolator._parse_path("data[0].items[1].value")
        assert result == ["data", 0, "items", 1, "value"]
    
    def test_parse_path_array_only(self):
        """Test parsing paths that start with array index."""
        interpolator = ParameterInterpolator({})
        
        result = interpolator._parse_path("items[0]")
        assert result == ["items", 0]
    
    def test_parse_path_invalid_bracket(self):
        """Test parsing paths with invalid bracket syntax."""
        interpolator = ParameterInterpolator({})
        
        with pytest.raises(ValueError, match="Unmatched"):
            interpolator._parse_path("array[0")
        
        with pytest.raises(ValueError, match="Invalid array index"):
            interpolator._parse_path("array[abc]")
    
    def test_add_result_simple(self):
        """Test adding simple event results."""
        interpolator = ParameterInterpolator({})
        
        interpolator.add_result("tools.now", "2023-01-01")
        assert interpolator.context["tools"]["now"]["result"] == "2023-01-01"
    
    def test_add_result_nested(self):
        """Test adding nested event results."""
        interpolator = ParameterInterpolator({})
        
        interpolator.add_result("email.search", [{"id": 1}, {"id": 2}])
        assert interpolator.context["email"]["search"]["result"] == [{"id": 1}, {"id": 2}]
    
    def test_add_result_overwrites_existing(self):
        """Test that adding results overwrites existing values."""
        interpolator = ParameterInterpolator({})
        
        interpolator.add_result("service.api", "old_value")
        interpolator.add_result("service.api", "new_value")
        assert interpolator.context["service"]["api"]["result"] == "new_value"
    
    def test_has_interpolations_true(self):
        """Test detecting interpolations in various data types."""
        interpolator = ParameterInterpolator({})
        
        # String with interpolation
        assert interpolator.has_interpolations("Hello {name}")
        
        # Dict with interpolation
        assert interpolator.has_interpolations({"key": "value {ref}"})
        
        # List with interpolation
        assert interpolator.has_interpolations(["item", "{ref}"])
        
        # Nested structures
        assert interpolator.has_interpolations({
            "nested": {
                "list": ["item", "{ref}"]
            }
        })
    
    def test_has_interpolations_false(self):
        """Test detecting no interpolations in various data types."""
        interpolator = ParameterInterpolator({})
        
        # String without interpolation
        assert not interpolator.has_interpolations("Hello world")
        
        # Dict without interpolation
        assert not interpolator.has_interpolations({"key": "value"})
        
        # List without interpolation
        assert not interpolator.has_interpolations(["item1", "item2"])
        
        # Primitive types
        assert not interpolator.has_interpolations(42)
        assert not interpolator.has_interpolations(True)
        assert not interpolator.has_interpolations(None)
    
    def test_interpolation_with_complex_json_embedding(self):
        """Test interpolation that embeds complex objects as JSON."""
        context = {
            "config": {"result": {"theme": "dark", "lang": "en"}},
            "user": {"result": "John"}
        }
        interpolator = ParameterInterpolator(context)
        
        # Complex object gets JSON-stringified when embedded
        text = "User {user.result} has config: {config.result}"
        result = interpolator.interpolate(text)
        expected = 'User John has config: {"theme": "dark", "lang": "en"}'
        assert result == expected
    
    def test_interpolation_error_handling(self):
        """Test error handling during interpolation."""
        interpolator = ParameterInterpolator({})
        
        # Missing reference should log warning and keep original
        with patch('modules.eventbus.parameter_interpolator.logger.warning') as mock_warning:
            result = interpolator.interpolate("Hello {missing.ref}")
            assert result == "Hello {missing.ref}"
            mock_warning.assert_called_once()
    
    def test_interpolation_pattern_regex(self):
        """Test the interpolation pattern regex."""
        pattern = ParameterInterpolator.INTERPOLATION_PATTERN
        
        # Should match valid expressions
        assert pattern.search("{simple}")
        assert pattern.search("{path.to.value}")
        assert pattern.search("{array[0]}")
        assert pattern.search("{complex.array[0].field}")
        
        # Should not match invalid expressions
        assert not pattern.search("no_braces")
        assert not pattern.search("{unclosed")
        assert not pattern.search("closed}")


class TestCreateInterpolator:
    """Test cases for create_interpolator function."""
    
    def test_create_interpolator_with_context(self):
        """Test creating interpolator with context."""
        context = {"key": "value"}
        interpolator = create_interpolator(context)
        
        assert isinstance(interpolator, ParameterInterpolator)
        assert interpolator.context == context
    
    def test_create_interpolator_without_context(self):
        """Test creating interpolator without context."""
        interpolator = create_interpolator()
        
        assert isinstance(interpolator, ParameterInterpolator)
        assert interpolator.context == {}
    
    def test_create_interpolator_with_none_context(self):
        """Test creating interpolator with None context."""
        interpolator = create_interpolator(None)
        
        assert isinstance(interpolator, ParameterInterpolator)
        assert interpolator.context == {}