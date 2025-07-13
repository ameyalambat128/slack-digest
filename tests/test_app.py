import pytest
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Set up dummy environment variables for testing
os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"
os.environ["SLACK_SIGNING_SECRET"] = "test-signing-secret"
os.environ["OPENAI_API_KEY"] = "sk-test-key"

from app import summarize

def test_summarize_returns_well_formed_json():
    """Test that summarize() returns well-formed JSON with the expected structure"""
    
    # Mock OpenAI response
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = json.dumps({
        "bullets": [
            {"text": "Motor driver testing showed 15% efficiency improvement", "link": ""},
            {"text": "Thermal testing revealed optimal operating range 45-65°C", "link": ""},
            {"text": "Firmware update v2.1 fixes critical boot sequence bug", "link": ""},
            {"text": "New thermal management algorithm reduces heat by 20%", "link": ""},
            {"text": "Motor driver integration tests passed all benchmarks", "link": ""}
        ]
    })
    
    # Sample messages to test with
    test_messages = [
        "[Alice] The motor-driver tests are showing great results!",
        "[Bob] Thermal-test data indicates we need better cooling",
        "[Charlie] Firmware update is ready for deployment"
    ]
    
    # Mock the OpenAI client
    with patch('app.client.chat.completions.create', return_value=mock_response):
        result = summarize(test_messages, "test_user_123")
    
    # Assertions
    assert isinstance(result, dict)
    assert "bullets" in result
    assert isinstance(result["bullets"], list)
    assert len(result["bullets"]) == 5
    
    # Check each bullet has the required structure
    for bullet in result["bullets"]:
        assert isinstance(bullet, dict)
        assert "text" in bullet
        assert "link" in bullet
        assert isinstance(bullet["text"], str)
        assert isinstance(bullet["link"], str)
        assert len(bullet["text"]) <= 30 * 2  # Allow some flexibility for word count
    
    # Verify the content makes sense for hardware team
    bullet_texts = [bullet["text"].lower() for bullet in result["bullets"]]
    hardware_keywords = ["motor", "thermal", "firmware", "test", "driver"]
    
    # At least some bullets should contain hardware-related terms
    found_keywords = sum(1 for text in bullet_texts if any(keyword in text for keyword in hardware_keywords))
    assert found_keywords >= 2, "Summary should contain hardware-related terms"

def test_summarize_handles_openai_error():
    """Test that summarize() handles OpenAI API errors gracefully"""
    
    test_messages = [
        "[Alice] Motor-driver issue needs attention",
        "[Bob] Thermal-test results are concerning"
    ]
    
    # Mock an OpenAI API error
    with patch('app.client.chat.completions.create', side_effect=Exception("API Error")):
        result = summarize(test_messages, "test_user_123")
    
    # Should return fallback response
    assert isinstance(result, dict)
    assert "bullets" in result
    assert len(result["bullets"]) == 1
    assert "Error generating summary" in result["bullets"][0]["text"]

def test_summarize_with_empty_messages():
    """Test that summarize() handles empty message list"""
    
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = json.dumps({
        "bullets": [
            {"text": "No recent hardware discussions found", "link": ""}
        ]
    })
    
    with patch('app.client.chat.completions.create', return_value=mock_response):
        result = summarize([], "test_user_123")
    
    assert isinstance(result, dict)
    assert "bullets" in result 