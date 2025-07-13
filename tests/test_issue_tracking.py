import pytest
import json
import os
from user_settings import (
    UserSettings, detect_issue_keywords, extract_issue_priority, 
    generate_issue_title, create_issue_prompt
)

class TestIssueTracking:
    def setup_method(self):
        """Setup test environment"""
        self.test_settings_file = "test_issue_settings.json"
        self.user_settings = UserSettings(self.test_settings_file)
        self.test_user_id = "U12345TEST"
        
    def teardown_method(self):
        """Clean up test files"""
        if os.path.exists(self.test_settings_file):
            os.remove(self.test_settings_file)
    
    def test_detect_issue_keywords(self):
        """Test issue keyword detection"""
        test_cases = [
            ("The PCB has a bug in the power circuit", ["bug", "hardware"]),
            ("System crashed during thermal test", ["failure", "hardware"]),
            ("Hardware not working properly", ["malfunction"]),
            ("Performance is really slow", ["performance"]),
            ("Critical blocker - firmware fails to boot", ["critical", "failure"]),
            ("This is a regular message about lunch", []),
            ("The motor driver component failed", ["failure"]),
            ("Software issue with the control logic", ["problem", "firmware"]),
        ]
        
        for message, expected_types in test_cases:
            detected = detect_issue_keywords(message)
            for expected_type in expected_types:
                assert expected_type in detected, f"Expected '{expected_type}' in detected types for: {message}"
    
    def test_extract_issue_priority(self):
        """Test priority extraction from text"""
        test_cases = [
            ("Critical system failure", "critical"),
            ("Urgent fix needed ASAP", "critical"),
            ("High priority bug", "high"),
            ("Important issue to resolve", "high"),
            ("Minor cosmetic problem", "low"),
            ("Nice to have feature", "low"),
            ("Regular bug report", "medium"),
            ("Some issue we found", "medium"),
        ]
        
        for message, expected_priority in test_cases:
            priority = extract_issue_priority(message)
            assert priority == expected_priority, f"Expected '{expected_priority}' for: {message}"
    
    def test_generate_issue_title(self):
        """Test issue title generation"""
        test_cases = [
            ("The motor driver PCB has a short circuit in the power section", "motor driver PCB short circuit power section"),
            ("Critical bug: firmware crashes when loading configuration file", "Critical bug firmware crashes loading configuration file"),
            ("@john please look at this thermal issue with the new board", "please look thermal issue new board"),
            ("https://example.com/link - component failure during stress test", "component failure during stress test"),
        ]
        
        for message, expected_words in test_cases:
            title = generate_issue_title(message)
            # Check that key words are preserved
            for word in expected_words.split():
                if len(word) > 2:  # Skip short words
                    assert word.lower() in title.lower(), f"Expected '{word}' in title: {title}"
    
    def test_create_issue(self):
        """Test issue creation"""
        issue_data = {
            "title": "PCB short circuit",
            "description": "Power section has short circuit",
            "original_text": "The PCB has a short circuit in the power section",
            "channel": "hardware",
            "reporter": "john_doe",
            "timestamp": "1234567890",
            "message_ts": "1234567890.123",
            "priority": "high",
            "tags": ["hardware", "bug"]
        }
        
        issue_id = self.user_settings.create_issue(self.test_user_id, issue_data)
        
        # Verify issue was created
        assert issue_id is not None
        assert len(issue_id) == 8  # MD5 hash truncated to 8 chars
        
        # Verify issue can be retrieved
        created_issue = self.user_settings.get_issue(self.test_user_id, issue_id)
        assert created_issue is not None
        assert created_issue["title"] == issue_data["title"]
        assert created_issue["priority"] == issue_data["priority"]
        assert created_issue["status"] == "open"  # Default status
        assert "created_at" in created_issue
        assert len(created_issue["status_history"]) == 1
    
    def test_get_user_issues(self):
        """Test retrieving user issues"""
        # Create multiple issues
        issue1_data = {
            "title": "Bug 1",
            "original_text": "First bug",
            "channel": "ch1",
            "reporter": "user1",
            "timestamp": "1000000000",
            "status": "open"
        }
        
        issue2_data = {
            "title": "Bug 2", 
            "original_text": "Second bug",
            "channel": "ch2",
            "reporter": "user2",
            "timestamp": "2000000000",
            "status": "resolved"
        }
        
        id1 = self.user_settings.create_issue(self.test_user_id, issue1_data)
        id2 = self.user_settings.create_issue(self.test_user_id, issue2_data)
        
        # Update second issue status
        self.user_settings.update_issue_status(self.test_user_id, id2, "resolved")
        
        # Test getting all issues
        all_issues = self.user_settings.get_user_issues(self.test_user_id)
        assert len(all_issues) == 2
        
        # Test filtering by status
        open_issues = self.user_settings.get_user_issues(self.test_user_id, "open")
        assert len(open_issues) == 1
        assert id1 in open_issues
        
        resolved_issues = self.user_settings.get_user_issues(self.test_user_id, "resolved")
        assert len(resolved_issues) == 1
        assert id2 in resolved_issues
    
    def test_update_issue_status(self):
        """Test updating issue status"""
        issue_data = {
            "title": "Test issue",
            "original_text": "Test issue text",
            "channel": "test",
            "reporter": "tester",
            "timestamp": "1000000000"
        }
        
        issue_id = self.user_settings.create_issue(self.test_user_id, issue_data)
        
        # Update status
        success = self.user_settings.update_issue_status(self.test_user_id, issue_id, "investigating", "other_user")
        assert success == True
        
        # Verify status was updated
        issue = self.user_settings.get_issue(self.test_user_id, issue_id)
        assert issue["status"] == "investigating"
        assert len(issue["status_history"]) == 2
        assert issue["status_history"][1]["status"] == "investigating"
        assert issue["status_history"][1]["user"] == "other_user"
        assert issue["status_history"][1]["previous_status"] == "open"
    
    def test_add_related_message(self):
        """Test adding related messages to issues"""
        issue_data = {
            "title": "Test issue",
            "original_text": "Original issue",
            "channel": "test",
            "reporter": "tester",
            "timestamp": "1000000000"
        }
        
        issue_id = self.user_settings.create_issue(self.test_user_id, issue_data)
        
        # Add related message
        message_data = {
            "text": "I'm seeing the same problem",
            "user": "another_user",
            "channel": "test",
            "timestamp": "2000000000",
            "message_ts": "2000000000.123"
        }
        
        success = self.user_settings.add_related_message(self.test_user_id, issue_id, message_data)
        assert success == True
        
        # Verify message was added
        issue = self.user_settings.get_issue(self.test_user_id, issue_id)
        assert len(issue["related_messages"]) == 1
        assert issue["related_messages"][0]["text"] == message_data["text"]
        assert issue["related_messages"][0]["user"] == message_data["user"]
        assert "added_at" in issue["related_messages"][0]
    
    def test_search_issues(self):
        """Test issue searching"""
        # Create issues with different content
        issues_data = [
            {
                "title": "PCB thermal problem",
                "description": "Overheating in power section",
                "original_text": "The PCB gets too hot during operation",
                "channel": "hardware",
                "reporter": "user1",
                "timestamp": "1000000000"
            },
            {
                "title": "Software crash bug",
                "description": "Application crashes on startup",
                "original_text": "Firmware crashes when loading config",
                "channel": "software",
                "reporter": "user2", 
                "timestamp": "2000000000"
            },
            {
                "title": "Motor controller issue",
                "description": "Motor not responding",
                "original_text": "Motor driver not working properly",
                "channel": "hardware",
                "reporter": "user3",
                "timestamp": "3000000000"
            }
        ]
        
        for issue_data in issues_data:
            self.user_settings.create_issue(self.test_user_id, issue_data)
        
        # Test searches
        pcb_results = self.user_settings.search_issues(self.test_user_id, "PCB")
        assert len(pcb_results) == 1
        assert "thermal" in pcb_results[0]["title"]
        
        crash_results = self.user_settings.search_issues(self.test_user_id, "crash")
        assert len(crash_results) == 1  # Should match "crash" in title and description
        
        motor_results = self.user_settings.search_issues(self.test_user_id, "motor")
        assert len(motor_results) == 1
        assert "controller" in motor_results[0]["title"]
        
        no_results = self.user_settings.search_issues(self.test_user_id, "nonexistent")
        assert len(no_results) == 0
    
    def test_get_issue_statistics(self):
        """Test issue statistics calculation"""
        # Create issues with different statuses and priorities
        issues_data = [
            {"title": "Issue 1", "status": "open", "priority": "high"},
            {"title": "Issue 2", "status": "investigating", "priority": "medium"},
            {"title": "Issue 3", "status": "resolved", "priority": "low"},
            {"title": "Issue 4", "status": "open", "priority": "critical"},
            {"title": "Issue 5", "status": "closed", "priority": "medium"}
        ]
        
        for i, issue_data in enumerate(issues_data):
            base_data = {
                "original_text": f"Issue {i+1} text",
                "channel": "test",
                "reporter": "tester",
                "timestamp": str(1000000000 + i)
            }
            base_data.update(issue_data)
            
            issue_id = self.user_settings.create_issue(self.test_user_id, base_data)
            
            # Update status if not default
            if issue_data["status"] != "open":
                self.user_settings.update_issue_status(self.test_user_id, issue_id, issue_data["status"])
        
        # Get statistics
        stats = self.user_settings.get_issue_statistics(self.test_user_id)
        
        assert stats["total"] == 5
        assert stats["open"] == 2
        assert stats["investigating"] == 1
        assert stats["resolved"] == 1
        assert stats["closed"] == 1
        assert stats["by_priority"]["critical"] == 1
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["medium"] == 2
        assert stats["by_priority"]["low"] == 1
        assert stats["recent_activity"] == 5  # All created recently
    
    def test_create_issue_prompt(self):
        """Test issue-specific prompt creation"""
        prompt = create_issue_prompt()
        
        assert "technical issue analyzer" in prompt
        assert "Issue identification" in prompt
        assert "severity and impact" in prompt
        assert "6 bullet points" in prompt
        assert "🔴 New, 🟡 Investigating, 🟢 Resolved" in prompt
        assert "json" in prompt.lower()
        
    def test_create_issue_prompt_with_custom_prompt(self):
        """Test issue prompt with user customization"""
        custom_prompt = "Focus on hardware-specific problems and component failures"
        
        prompt = create_issue_prompt(custom_prompt)
        
        assert custom_prompt in prompt
        assert "ADDITIONAL CONTEXT FOR ISSUE ANALYSIS" in prompt
        assert "technical issue analyzer" in prompt  # Base prompt still there 