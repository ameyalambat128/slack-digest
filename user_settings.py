import json
import os
from typing import Dict, Optional, List
from datetime import datetime
import hashlib

class UserSettings:
    """Manage user-specific settings for Slack Digest AI"""
    
    def __init__(self, settings_file: str = "user_settings.json"):
        self.settings_file = settings_file
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict:
        """Load settings from file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except IOError:
            print(f"Warning: Could not save settings to {self.settings_file}")
    
    def get_user_settings(self, user_id: str) -> Dict:
        """Get settings for a specific user"""
        return self.settings.get(user_id, {})
    
    def set_user_prompt(self, user_id: str, custom_prompt: str):
        """Set custom system prompt for a user"""
        if user_id not in self.settings:
            self.settings[user_id] = {}
        
        self.settings[user_id]["custom_prompt"] = custom_prompt
        self._save_settings()
    
    def get_user_prompt(self, user_id: str) -> Optional[str]:
        """Get custom system prompt for a user"""
        user_settings = self.get_user_settings(user_id)
        return user_settings.get("custom_prompt")
    
    def set_user_keywords(self, user_id: str, keywords: list):
        """Set custom keywords for a user"""
        if user_id not in self.settings:
            self.settings[user_id] = {}
        
        self.settings[user_id]["keywords"] = keywords
        self._save_settings()
    
    def get_user_keywords(self, user_id: str) -> Optional[list]:
        """Get custom keywords for a user"""
        user_settings = self.get_user_settings(user_id)
        return user_settings.get("keywords")
    
    def set_user_hours(self, user_id: str, hours: int):
        """Set default time range for a user"""
        if user_id not in self.settings:
            self.settings[user_id] = {}
        
        self.settings[user_id]["default_hours"] = hours
        self._save_settings()
    
    def get_user_hours(self, user_id: str) -> int:
        """Get default time range for a user"""
        user_settings = self.get_user_settings(user_id)
        return user_settings.get("default_hours", 24)
    
    def clear_user_settings(self, user_id: str):
        """Clear all settings for a user"""
        print(f"🗑️ DEBUG: Clearing settings for user {user_id}")
        print(f"🗑️ DEBUG: Before clear - settings: {self.settings}")
        if user_id in self.settings:
            del self.settings[user_id]
            print(f"🗑️ DEBUG: After delete - settings: {self.settings}")
            self._save_settings()
            print(f"🗑️ DEBUG: Settings saved to file")
        else:
            print(f"🗑️ DEBUG: User {user_id} not found in settings")

    # Project tracking methods
    def create_project(self, user_id: str, project_name: str, channels: List[str], keywords: List[str] = None):
        """Create a new project configuration"""
        if user_id not in self.settings:
            self.settings[user_id] = {}
        
        if "projects" not in self.settings[user_id]:
            self.settings[user_id]["projects"] = {}
        
        self.settings[user_id]["projects"][project_name] = {
            "channels": channels,
            "keywords": keywords or [],
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        self._save_settings()
    
    def get_user_projects(self, user_id: str) -> Dict:
        """Get all projects for a user"""
        user_settings = self.get_user_settings(user_id)
        return user_settings.get("projects", {})
    
    def get_project(self, user_id: str, project_name: str) -> Optional[Dict]:
        """Get specific project configuration"""
        projects = self.get_user_projects(user_id)
        return projects.get(project_name)
    
    def update_project_channels(self, user_id: str, project_name: str, channels: List[str]):
        """Update channels for a project"""
        if user_id in self.settings and "projects" in self.settings[user_id]:
            if project_name in self.settings[user_id]["projects"]:
                self.settings[user_id]["projects"][project_name]["channels"] = channels
                self._save_settings()
    
    def update_project_keywords(self, user_id: str, project_name: str, keywords: List[str]):
        """Update keywords for a project"""
        if user_id in self.settings and "projects" in self.settings[user_id]:
            if project_name in self.settings[user_id]["projects"]:
                self.settings[user_id]["projects"][project_name]["keywords"] = keywords
                self._save_settings()
    
    def delete_project(self, user_id: str, project_name: str):
        """Delete a project"""
        if user_id in self.settings and "projects" in self.settings[user_id]:
            if project_name in self.settings[user_id]["projects"]:
                del self.settings[user_id]["projects"][project_name]
                self._save_settings()
    
    def toggle_project_status(self, user_id: str, project_name: str):
        """Toggle project active/inactive status"""
        if user_id in self.settings and "projects" in self.settings[user_id]:
            if project_name in self.settings[user_id]["projects"]:
                current_status = self.settings[user_id]["projects"][project_name].get("active", True)
                self.settings[user_id]["projects"][project_name]["active"] = not current_status
                self._save_settings()
                return not current_status
        return None

    # Issue tracking methods
    def _generate_issue_id(self, message_text: str, channel: str, timestamp: str) -> str:
        """Generate a unique issue ID based on content and context"""
        content = f"{message_text[:100]}{channel}{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def create_issue(self, user_id: str, issue_data: Dict) -> str:
        """Create a new tracked issue"""
        if user_id not in self.settings:
            self.settings[user_id] = {}
        
        if "issues" not in self.settings[user_id]:
            self.settings[user_id]["issues"] = {}
        
        issue_id = self._generate_issue_id(
            issue_data.get("original_text", ""),
            issue_data.get("channel", ""),
            issue_data.get("timestamp", "")
        )
        
        self.settings[user_id]["issues"][issue_id] = {
            "id": issue_id,
            "title": issue_data.get("title", ""),
            "description": issue_data.get("description", ""),
            "original_text": issue_data.get("original_text", ""),
            "channel": issue_data.get("channel", ""),
            "reporter": issue_data.get("reporter", ""),
            "timestamp": issue_data.get("timestamp", ""),
            "message_ts": issue_data.get("message_ts", ""),
            "status": issue_data.get("status", "open"),
            "priority": issue_data.get("priority", "medium"),
            "tags": issue_data.get("tags", []),
            "related_messages": [],
            "status_history": [
                {
                    "status": "open",
                    "timestamp": datetime.now().isoformat(),
                    "user": user_id
                }
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self._save_settings()
        return issue_id
    
    def get_user_issues(self, user_id: str, status: str = None) -> Dict:
        """Get all issues for a user, optionally filtered by status"""
        user_settings = self.get_user_settings(user_id)
        issues = user_settings.get("issues", {})
        
        if status:
            return {k: v for k, v in issues.items() if v.get("status") == status}
        return issues
    
    def get_issue(self, user_id: str, issue_id: str) -> Optional[Dict]:
        """Get specific issue by ID"""
        issues = self.get_user_issues(user_id)
        return issues.get(issue_id)
    
    def update_issue_status(self, user_id: str, issue_id: str, new_status: str, updated_by: str = None):
        """Update issue status and track history"""
        if user_id in self.settings and "issues" in self.settings[user_id]:
            if issue_id in self.settings[user_id]["issues"]:
                issue = self.settings[user_id]["issues"][issue_id]
                old_status = issue.get("status", "open")
                
                issue["status"] = new_status
                issue["updated_at"] = datetime.now().isoformat()
                
                # Add to status history
                issue["status_history"].append({
                    "status": new_status,
                    "timestamp": datetime.now().isoformat(),
                    "user": updated_by or user_id,
                    "previous_status": old_status
                })
                
                self._save_settings()
                return True
        return False
    
    def add_related_message(self, user_id: str, issue_id: str, message_data: Dict):
        """Add a related message to an issue thread"""
        if user_id in self.settings and "issues" in self.settings[user_id]:
            if issue_id in self.settings[user_id]["issues"]:
                issue = self.settings[user_id]["issues"][issue_id]
                
                related_message = {
                    "text": message_data.get("text", ""),
                    "user": message_data.get("user", ""),
                    "channel": message_data.get("channel", ""),
                    "timestamp": message_data.get("timestamp", ""),
                    "message_ts": message_data.get("message_ts", ""),
                    "added_at": datetime.now().isoformat()
                }
                
                issue["related_messages"].append(related_message)
                issue["updated_at"] = datetime.now().isoformat()
                
                self._save_settings()
                return True
        return False
    
    def search_issues(self, user_id: str, query: str) -> List[Dict]:
        """Search issues by text content"""
        issues = self.get_user_issues(user_id)
        results = []
        
        query_lower = query.lower()
        
        for issue_id, issue in issues.items():
            searchable_text = f"{issue.get('title', '')} {issue.get('description', '')} {issue.get('original_text', '')}".lower()
            if query_lower in searchable_text:
                results.append(issue)
        
        # Sort by most recent first
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results
    
    def get_issue_statistics(self, user_id: str) -> Dict:
        """Get issue statistics for a user"""
        issues = self.get_user_issues(user_id)
        
        stats = {
            "total": len(issues),
            "open": 0,
            "investigating": 0,
            "resolved": 0,
            "closed": 0,
            "by_priority": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "recent_activity": 0  # Issues updated in last 24h
        }
        
        twenty_four_hours_ago = datetime.now().timestamp() - (24 * 3600)
        
        for issue in issues.values():
            status = issue.get("status", "open")
            priority = issue.get("priority", "medium")
            
            # Count by status
            if status in stats:
                stats[status] += 1
            
            # Count by priority
            if priority in stats["by_priority"]:
                stats["by_priority"][priority] += 1
            
            # Count recent activity
            updated_at = issue.get("updated_at", "")
            try:
                if updated_at:
                    updated_timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).timestamp()
                    if updated_timestamp > twenty_four_hours_ago:
                        stats["recent_activity"] += 1
            except:
                pass
        
        return stats

def create_combined_prompt(user_prompt: Optional[str] = None) -> str:
    """
    Create a combined system prompt that merges our specialized Slack digest prompt
    with the user's custom prompt
    """
    
    # Our specialized base prompt for Slack digests
    base_prompt = """You are an expert Slack conversation summarizer.

Your task is to analyze Slack messages and create concise, actionable digests.

CORE RULES:
- Return exactly 5 bullet points
- Each bullet must be ≤30 words
- Focus on key decisions, updates, issues, and action items
- Use clear, professional language
- Maintain context about who said what when relevant

RESPONSE FORMAT:
Return ONLY valid JSON in this exact schema:
{"bullets":[{"text":"bullet content","link":""},...]}

ANALYSIS PRIORITIES:
1. Decisions made or needed
2. Technical updates or issues
3. Project progress or blockers
4. Action items or deadlines
5. Important announcements"""

    # If user has custom prompt, combine them
    if user_prompt:
        combined_prompt = f"""{base_prompt}

ADDITIONAL CONTEXT & CUSTOMIZATION:
{user_prompt}

Apply the above customization while maintaining the core response format and rules."""
    else:
        combined_prompt = base_prompt
    
    return combined_prompt

def create_project_prompt(project_name: str, channels: List[str], user_prompt: Optional[str] = None) -> str:
    """
    Create a specialized prompt for project tracking across multiple channels
    """
    
    base_prompt = f"""You are analyzing messages for PROJECT: {project_name} across multiple Slack channels.

CONTEXT: These messages come from {len(channels)} different channels: {', '.join([f'#{ch}' for ch in channels])}

Your task is to create a PROJECT-FOCUSED digest that shows:
1. Cross-team coordination and dependencies
2. Project milestones, progress, and blockers  
3. Technical decisions affecting the project
4. Resource needs or bottlenecks
5. Timeline updates or schedule changes

CORE RULES:
- Return exactly 6 bullet points (one extra for project overview)
- Each bullet must be ≤35 words
- Include channel context when relevant (e.g., "[#hardware] PCB design approved")
- Focus on project impact, not individual tasks
- Highlight cross-team dependencies and coordination

RESPONSE FORMAT:
Return ONLY valid JSON in this exact schema:
{{"bullets":[{{"text":"bullet content","link":""}},...]}}

ANALYSIS PRIORITIES FOR PROJECT TRACKING:
1. Project status and milestone progress
2. Cross-team dependencies and coordination
3. Technical decisions and design changes
4. Resource allocation and bottlenecks  
5. Schedule updates and deadline changes
6. Risk identification and mitigation"""

    # If user has custom prompt, combine them
    if user_prompt:
        combined_prompt = f"""{base_prompt}

ADDITIONAL PROJECT CONTEXT:
{user_prompt}

Apply the above customization while maintaining the core response format and project focus."""
    else:
        combined_prompt = base_prompt
    
    return combined_prompt

def detect_issue_keywords(text: str) -> List[str]:
    """
    Detect issue-related keywords in message text
    Returns list of detected issue types
    """
    issue_patterns = {
        "bug": ["bug", "bugs", "buggy", "defect", "error", "broken"],
        "failure": ["failure", "failed", "failing", "fails", "crash", "crashed", "crashing"],
        "problem": ["problem", "problems", "issue", "issues", "trouble", "wrong"],
        "malfunction": ["malfunction", "not working", "doesn't work", "stopped working"],
        "performance": ["slow", "performance", "lag", "timeout", "bottleneck"],
        "critical": ["critical", "urgent", "emergency", "blocker", "show-stopper", "showstopper"],
        "regression": ["regression", "broke", "used to work", "was working"],
        "hardware": ["hardware issue", "pcb", "component failure", "short circuit", "thermal"],
        "firmware": ["firmware bug", "software issue", "code problem", "logic error"]
    }
    
    text_lower = text.lower()
    detected_types = []
    
    for issue_type, keywords in issue_patterns.items():
        if any(keyword in text_lower for keyword in keywords):
            detected_types.append(issue_type)
    
    return detected_types

def extract_issue_priority(text: str) -> str:
    """Extract priority level from message text"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["critical", "urgent", "emergency", "blocker", "show-stopper", "showstopper"]):
        return "critical"
    elif any(word in text_lower for word in ["high", "important", "asap", "priority"]):
        return "high"
    elif any(word in text_lower for word in ["low", "minor", "cosmetic", "nice to have"]):
        return "low"
    else:
        return "medium"

def generate_issue_title(text: str, max_length: int = 80) -> str:
    """Generate a concise title for an issue from message text"""
    # Remove common filler words and extract key information
    import re
    
    # Remove mentions, channels, and URLs
    cleaned = re.sub(r'<[@#!][^>]+>', '', text)
    cleaned = re.sub(r'http[s]?://\S+', '', cleaned)
    
    # Split into words and filter
    words = cleaned.split()
    filtered_words = []
    
    skip_words = {"the", "a", "an", "is", "was", "are", "were", "i", "we", "you", "they", "it", "this", "that"}
    
    for word in words:
        if word.lower() not in skip_words and len(word) > 2:
            filtered_words.append(word)
    
    # Take first part of meaningful content
    title = " ".join(filtered_words[:12])
    
    if len(title) > max_length:
        title = title[:max_length-3] + "..."
    
    return title.strip()

def create_issue_prompt(user_prompt: Optional[str] = None) -> str:
    """
    Create a specialized prompt for technical issue analysis
    """
    
    base_prompt = """You are an expert technical issue analyzer for hardware and software engineering teams.

Your task is to analyze messages that potentially contain technical issues, bugs, or problems and create actionable summaries.

FOCUS AREAS:
1. Issue identification and classification
2. Problem severity and impact assessment  
3. Root cause analysis hints
4. Resolution progress tracking
5. Related discussions and follow-ups

CORE RULES:
- Return exactly 6 bullet points focused on technical issues
- Each bullet must be ≤40 words
- Classify issues by type (bug, failure, performance, etc.)
- Include status indicators (🔴 New, 🟡 Investigating, 🟢 Resolved)
- Highlight critical/blocking issues
- Track resolution attempts and outcomes

RESPONSE FORMAT:
Return ONLY valid JSON in this exact schema:
{"bullets":[{"text":"bullet content","link":""},...]}

ANALYSIS PRIORITIES FOR ISSUE TRACKING:
1. New issues and problem reports
2. Investigation progress and findings
3. Attempted solutions and results
4. Cross-team coordination for fixes
5. Resolution confirmations and testing
6. Related issues and patterns"""

    # If user has custom prompt, combine them
    if user_prompt:
        combined_prompt = f"""{base_prompt}

ADDITIONAL CONTEXT FOR ISSUE ANALYSIS:
{user_prompt}

Apply the above customization while maintaining the core response format and issue focus."""
    else:
        combined_prompt = base_prompt
    
    return combined_prompt 