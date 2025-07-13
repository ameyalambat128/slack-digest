# Slack Digest AI

An intelligent Slack bot that generates concise, actionable digests of team conversations using OpenAI's GPT-4.1. Perfect for hardware engineering teams and cross-functional projects.

## Features

### 🔍 **Smart Message Digests**

- Generate AI-powered summaries of Slack conversations
- Configurable time ranges (1-168 hours)
- Custom keyword filtering
- Personalized analysis prompts

### 🚀 **Multi-Channel Project Tracking**

- Track project discussions across multiple channels simultaneously
- Cross-team coordination insights
- Project-specific keyword filtering
- Timeline and milestone progress tracking
- Channel activity breakdowns

### 🔧 **Technical Issue Threading**

- Automatic detection of bugs, failures, and technical problems
- Issue status tracking (open/investigating/resolved/closed)
- Priority classification (critical/high/medium/low)
- Search and filter tracked issues
- Link related messages and follow-up discussions
- Issue statistics and reporting

### ⚙️ **User Customization**

- Personal keyword filters
- Custom analysis prompts
- Configurable time ranges
- Individual user settings persistence

## Commands

### Basic Digest

```
/digest
```

Generates a digest of the current channel for the last 24 hours (or your configured default).

### Project Tracking Commands

#### Create a Project

```
/digest-project create [project-name] #channel1,#channel2,#channel3 [optional keywords]
```

**Example:**

```
/digest-project create hardware-v2 #hardware,#software,#mechanical PCB schematic firmware
```

#### Get Project Digest

```
/digest-project [project-name]
```

**Example:**

```
/digest-project hardware-v2
```

#### List Your Projects

```
/digest-project list
```

#### View Project Configuration

```
/digest-project config [project-name]
```

#### Project Management Interface

```
/digest-project
```

Shows all your projects and available commands.

### Issue Tracking Commands

#### Scan for Technical Issues

```
/digest-issues scan [hours]
```

**Example:**

```
/digest-issues scan 48
```

Automatically detects and tracks technical issues from recent messages.

#### List Tracked Issues

```
/digest-issues list [status]
```

**Examples:**

```
/digest-issues list
/digest-issues list open
/digest-issues list resolved
```

#### Search Issues

```
/digest-issues search [query]
```

**Example:**

```
/digest-issues search PCB thermal
```

#### View Issue Statistics

```
/digest-issues stats
```

#### Issue Dashboard

```
/digest-issues
```

Shows your issue dashboard with statistics and available commands.

### Configuration Commands

#### Set Custom Analysis Prompt

```
/digest-config prompt "Focus on technical risks and compliance issues for hardware projects"
```

#### Set Keyword Filters

```
/digest-config keywords PCB,schematic,firmware,test,compliance
```

#### Set Default Time Range

```
/digest-config hours 48
```

#### View Current Settings

```
/digest-config
```

#### Reset All Settings

```
/digest-config reset
```

## Use Cases

### For Hardware Engineering Teams

**Multi-Team Coordination:**

- Track discussions across #hardware, #software, #mechanical, #manufacturing
- Identify cross-team dependencies and blockers
- Monitor project milestones and progress

**Technical Issue Management:**

- Auto-detect issues with keywords: `bug`, `issue`, `failure`, `test`, `crash`
- Track problem resolution across teams
- Identify recurring issues and patterns
- Monitor critical issues requiring immediate attention

**Design Review Tracking:**

- Keywords: `design`, `review`, `CAD`, `schematic`, `approval`
- Monitor feedback and action items
- Track sign-off status

**Supply Chain Intelligence:**

- Keywords: `supplier`, `lead time`, `availability`, `cost`, `BOM`
- Stay updated on component status
- Track vendor communications

## Issue Detection & Classification

### Automatic Detection Patterns

The system automatically detects technical issues using these patterns:

- **Bugs**: `bug`, `bugs`, `buggy`, `defect`, `error`, `broken`
- **Failures**: `failure`, `failed`, `failing`, `crash`, `crashed`
- **Problems**: `problem`, `problems`, `issue`, `issues`, `trouble`, `wrong`
- **Malfunctions**: `malfunction`, `not working`, `doesn't work`, `stopped working`
- **Performance**: `slow`, `performance`, `lag`, `timeout`, `bottleneck`
- **Critical Issues**: `critical`, `urgent`, `emergency`, `blocker`, `show-stopper`
- **Hardware Issues**: `hardware issue`, `PCB`, `component failure`, `short circuit`, `thermal`
- **Firmware Issues**: `firmware bug`, `software issue`, `code problem`, `logic error`

### Priority Classification

Issues are automatically assigned priority levels:

- **🔴 Critical**: `critical`, `urgent`, `emergency`, `blocker`, `show-stopper`
- **🟠 High**: `high`, `important`, `ASAP`, `priority`
- **🟢 Low**: `low`, `minor`, `cosmetic`, `nice to have`
- **🟡 Medium**: Everything else (default)

### Status Tracking

Issues progress through these states:

- **🔴 Open**: Newly detected issues
- **🟡 Investigating**: Issues being actively worked on
- **🟢 Resolved**: Issues that have been fixed
- **⚫ Closed**: Issues that are resolved and verified

## Installation

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd slack-digest
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**

   ```bash
   export SLACK_BOT_TOKEN="xoxb-your-bot-token"
   export SLACK_SIGNING_SECRET="your-signing-secret"
   export OPENAI_API_KEY="sk-your-openai-key"
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

## Slack App Setup

1. Create a new Slack app at https://api.slack.com/apps
2. Configure OAuth & Permissions with these scopes:
   - `channels:history`
   - `channels:read`
   - `chat:write`
   - `commands`
   - `users:read`
3. Create slash commands:
   - `/digest` → `https://your-domain.com/slack/events`
   - `/digest-config` → `https://your-domain.com/slack/events`
   - `/digest-project` → `https://your-domain.com/slack/events`
   - `/digest-issues` → `https://your-domain.com/slack/events`
4. Enable Event Subscriptions (optional)
5. Install the app to your workspace

## Data Architecture

### Project Tracking Structure

```json
{
  "user_id": {
    "projects": {
      "project-name": {
        "channels": ["channel1", "channel2"],
        "keywords": ["keyword1", "keyword2"],
        "created_at": "2024-01-01T00:00:00",
        "active": true
      }
    }
  }
}
```

### Issue Tracking Structure

```json
{
  "user_id": {
    "issues": {
      "issue-id": {
        "id": "abc12345",
        "title": "PCB thermal issue",
        "description": "Generated description",
        "original_text": "Original message text",
        "channel": "hardware",
        "reporter": "user_name",
        "status": "open",
        "priority": "high",
        "tags": ["hardware", "thermal"],
        "related_messages": [],
        "status_history": [
          {
            "status": "open",
            "timestamp": "2024-01-01T00:00:00",
            "user": "user_id"
          }
        ],
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    }
  }
}
```

## Analysis Flow

### Project Analysis

1. **Multi-Channel Collection**: Fetch messages from all configured channels
2. **Keyword Filtering**: Apply project-specific keywords
3. **Cross-Channel Correlation**: Identify related discussions
4. **Project-Focused Analysis**: Generate insights on coordination, dependencies, and progress
5. **Structured Output**: Present findings with channel context and activity breakdown

### Issue Analysis

1. **Pattern Detection**: Scan messages for issue-related keywords
2. **Classification**: Determine issue type and priority
3. **Auto-Tracking**: Create issue records for detected problems
4. **Context Analysis**: Generate AI-powered insights about technical issues
5. **Status Management**: Track issue progression and resolution

## Configuration

### Environment Variables

- `SLACK_BOT_TOKEN`: Your Slack bot token
- `SLACK_SIGNING_SECRET`: Your Slack app signing secret
- `OPENAI_API_KEY`: Your OpenAI API key

### User Settings Storage

Settings are stored in `user_settings.json` with automatic persistence.

## API Endpoints

- `GET /` - Health check
- `POST /slack/events` - Slack events endpoint
- `GET /digest` - Information endpoint

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Test coverage includes:

- Basic digest functionality
- Project tracking operations
- Issue detection and management
- User settings management
- Error handling
- Integration scenarios

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request
