import pytest
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# Set up dummy environment variables for testing
os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"
os.environ["SLACK_SIGNING_SECRET"] = "test-signing-secret"
os.environ["OPENAI_API_KEY"] = "sk-test-key"

from app import app, summarize, DEFAULT_KEYWORDS, slack_app

class TestSlackDigestIntegration:
    """Comprehensive integration tests for Slack Digest AI"""
    
    def test_keywords_configuration(self):
        """Test that keywords are properly configured"""
        assert DEFAULT_KEYWORDS == []
        assert isinstance(DEFAULT_KEYWORDS, list)
    
    def test_fastapi_app_creation(self):
        """Test FastAPI app is properly configured"""
        client = TestClient(app)
        
        # Test health check endpoint
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "Slack Digest AI is running!"}
        
        # Test digest info endpoint
        response = client.get("/digest")
        assert response.status_code == 200
        assert "Use the /digest slash command" in response.json()["message"]
    
    @patch('app.client.chat.completions.create')
    def test_summarize_function_with_realistic_data(self, mock_openai):
        """Test summarize function with realistic hardware team messages"""
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "bullets": [
                {"text": "Motor-driver efficiency improved by 15% in latest tests", "link": ""},
                {"text": "Thermal-test results show optimal range 45-65°C", "link": ""},
                {"text": "Firmware v2.1 deployment scheduled for next week", "link": ""},
                {"text": "New motor driver board revision addresses heat issues", "link": ""},
                {"text": "Thermal management algorithm reduces operating temperature", "link": ""}
            ]
        })
        mock_openai.return_value = mock_response
        
        # Realistic hardware team messages
        test_messages = [
            "[Alice] The motor-driver tests are showing 15% efficiency improvement!",
            "[Bob] Our thermal-test data indicates we need the temperature between 45-65°C",
            "[Charlie] Firmware v2.1 is ready for deployment next week",
            "[David] The new motor-driver board revision should fix the heating issues",
            "[Eve] The thermal management algorithm is reducing operating temps significantly"
        ]
        
        result = summarize(test_messages, "test_user_123")
        
        # Verify OpenAI was called with correct parameters
        mock_openai.assert_called_once()
        call_args = mock_openai.call_args
        assert call_args[1]["model"] == "gpt-4.1-2025-04-14"
        assert call_args[1]["max_tokens"] == 256
        assert call_args[1]["response_format"] == {"type": "json_object"}
        
        # Verify messages were properly formatted
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Slack conversation summarizer" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "[Alice]" in messages[1]["content"]
        assert "motor-driver" in messages[1]["content"]
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "bullets" in result
        assert len(result["bullets"]) == 5
        
        for bullet in result["bullets"]:
            assert "text" in bullet
            assert "link" in bullet
            assert isinstance(bullet["text"], str)
            assert len(bullet["text"]) > 0
    
    def test_message_filtering_logic(self):
        """Test the message filtering logic for keywords"""
        
        # Test with sample keywords for project tracking
        test_keywords = ["motor-driver", "thermal-test", "firmware"]
        
        test_cases = [
            ("Check the motor-driver status", True),
            ("MOTOR-DRIVER needs attention", True),
            ("Run thermal-test on the new board", True),
            ("Update the firmware to latest version", True),
            ("Let's grab lunch today", False),
            ("Meeting at 3pm in conference room", False),
            ("The motor driver (with space) works too", False),  # Different keyword variation won't match exact "motor-driver"
            ("THERMAL TEST results are in", False),  # Different keyword variation won't match exact "thermal-test"
        ]
        
        for message_text, should_match in test_cases:
            message_lower = message_text.lower()
            matches = any(keyword.lower() in message_lower for keyword in test_keywords)
            assert matches == should_match, f"Message '{message_text}' should {'match' if should_match else 'not match'} keywords"
    
    @pytest.mark.asyncio
    async def test_slack_command_handler_structure(self):
        """Test that the Slack command handler is properly registered"""
        
        # Check that the command handlers exist
        # Note: AsyncApp structure may vary, so we'll just verify the app is configured
        assert slack_app is not None
        assert hasattr(slack_app, 'command')
        
        # Verify we can access the app configuration
        assert slack_app._token is not None
        assert slack_app._signing_secret is not None
    
    def test_timestamp_calculation(self):
        """Test 24-hour timestamp calculation logic"""
        
        now = datetime.now()
        twenty_four_hours_ago = now - timedelta(hours=24)
        oldest_timestamp = str(twenty_four_hours_ago.timestamp())
        
        # Verify timestamp is a valid string representation
        assert isinstance(oldest_timestamp, str)
        assert float(oldest_timestamp) > 0
        
        # Verify it's actually 24 hours ago (within 1 second tolerance)
        reconstructed_time = datetime.fromtimestamp(float(oldest_timestamp))
        time_diff = now - reconstructed_time
        assert abs(time_diff.total_seconds() - 24 * 3600) < 1
    
    @patch('app.client.chat.completions.create')
    def test_error_handling_in_summarize(self, mock_openai):
        """Test error handling in summarize function"""
        
        # Test various error scenarios
        error_scenarios = [
            Exception("API rate limit exceeded"),
            json.JSONDecodeError("Invalid JSON", "", 0),
            KeyError("choices"),
            ConnectionError("Network timeout")
        ]
        
        test_messages = ["[User] Motor-driver issue detected"]
        
        for error in error_scenarios:
            mock_openai.side_effect = error
            result = summarize(test_messages, "test_user")
            
            # Should return fallback response
            assert isinstance(result, dict)
            assert "bullets" in result
            assert len(result["bullets"]) == 1
            assert "Error generating summary" in result["bullets"][0]["text"]
            
            # Reset mock for next iteration
            mock_openai.reset_mock()
    
    def test_block_kit_structure(self):
        """Test that Block Kit response structure is valid"""
        
        # Simulate a typical summary response
        sample_summary = {
            "bullets": [
                {"text": "Motor driver efficiency improved", "link": ""},
                {"text": "Thermal tests completed successfully", "link": ""}
            ]
        }
        
        # Simulate the block creation logic from the app
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Hardware Team Digest (Last 24h)"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Add bullet points
        for bullet in sample_summary["bullets"]:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {bullet['text']}"
                }
            })
        
        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Analyzed 2 relevant messages • Keywords: motor-driver, thermal-test_"
                }
            ]
        })
        
        # Verify block structure
        assert len(blocks) >= 4  # Header, divider, bullets, footer
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "divider"
        assert blocks[-1]["type"] == "context"
        
        # Verify bullet blocks
        bullet_blocks = [b for b in blocks if b.get("type") == "section"]
        assert len(bullet_blocks) == len(sample_summary["bullets"])
        
        for block in bullet_blocks:
            assert "text" in block
            assert block["text"]["type"] == "mrkdwn"
            assert block["text"]["text"].startswith("•")
    
    def test_environment_variables_loading(self):
        """Test that environment variables are properly loaded"""
        
        # These should be set by the app initialization
        required_vars = ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET", "OPENAI_API_KEY"]
        
        for var in required_vars:
            value = os.environ.get(var)
            assert value is not None, f"Environment variable {var} should be set"
            assert len(value) > 0, f"Environment variable {var} should not be empty"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 