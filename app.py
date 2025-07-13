import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

import openai
from fastapi import FastAPI, Request
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from dotenv import load_dotenv
from user_settings import (
    UserSettings, create_combined_prompt, create_project_prompt, create_issue_prompt,
    detect_issue_keywords, extract_issue_priority, generate_issue_title
)

load_dotenv()

user_settings = UserSettings()

slack_app = AsyncApp(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Initialize OpenAI client
from openai import OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


DEFAULT_KEYWORDS = []

def summarize(msgs: List[str], user_id: str) -> Dict[str, Any]:
    """
    Summarize Slack messages using OpenAI GPT-4.1-2025-04-14
    
    Args:
        msgs: List of formatted message strings
        user_id: The user ID who requested the digest
    
    Returns:
        Dict containing bullets with text and link fields
    """
    # Get user's custom prompt and create combined prompt
    user_custom_prompt = user_settings.get_user_prompt(user_id)
    system_prompt = create_combined_prompt(user_custom_prompt)
    
    # Concatenate messages
    messages_text = "\n".join(msgs)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Summarize these Slack team messages:\n\n{messages_text}"}
            ],
            max_tokens=256,
            response_format={"type": "json_object"}
        )
        
        summary = json.loads(response.choices[0].message.content)
        return summary
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Return fallback response
        return {
            "bullets": [
                {"text": "Error generating summary. Please try again later.", "link": ""}
            ]
        }

def summarize_project(msgs: List[str], project_name: str, channels: List[str], user_id: str) -> Dict[str, Any]:
    """
    Summarize Slack messages for a specific project across multiple channels
    
    Args:
        msgs: List of formatted message strings with channel context
        project_name: Name of the project being tracked
        channels: List of channel names being monitored
        user_id: The user ID who requested the digest
    
    Returns:
        Dict containing bullets with text and link fields
    """
    # Get user's custom prompt and create project-specific prompt
    user_custom_prompt = user_settings.get_user_prompt(user_id)
    system_prompt = create_project_prompt(project_name, channels, user_custom_prompt)
    
    # Concatenate messages
    messages_text = "\n".join(msgs)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze these project messages from multiple channels:\n\n{messages_text}"}
            ],
            max_tokens=400,  # Slightly more tokens for project summaries
            response_format={"type": "json_object"}
        )
        
        summary = json.loads(response.choices[0].message.content)
        return summary
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Return fallback response
        return {
            "bullets": [
                {"text": "Error generating project summary. Please try again later.", "link": ""}
            ]
        }

def summarize_issues(msgs: List[str], user_id: str, detected_issues: List[Dict] = None) -> Dict[str, Any]:
    """
    Summarize messages with focus on technical issues and problems
    
    Args:
        msgs: List of formatted message strings
        user_id: The user ID who requested the digest
        detected_issues: List of pre-detected issues with metadata
    
    Returns:
        Dict containing bullets with text and link fields focused on issues
    """
    # Get user's custom prompt and create issue-specific prompt
    user_custom_prompt = user_settings.get_user_prompt(user_id)
    system_prompt = create_issue_prompt(user_custom_prompt)
    
    # Concatenate messages
    messages_text = "\n".join(msgs)
    
    # Add context about detected issues if available
    context_info = ""
    if detected_issues:
        issue_types = set()
        priorities = set()
        for issue in detected_issues:
            issue_types.update(issue.get("types", []))
            priorities.add(issue.get("priority", "medium"))
        
        context_info = f"\n\nDETECTED ISSUE CONTEXT:\n- Issue types found: {', '.join(issue_types)}\n- Priority levels: {', '.join(priorities)}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze these messages for technical issues and problems:\n\n{messages_text}{context_info}"}
            ],
            max_tokens=500,  # More tokens for detailed issue analysis
            response_format={"type": "json_object"}
        )
        
        summary = json.loads(response.choices[0].message.content)
        return summary
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Return fallback response
        return {
            "bullets": [
                {"text": "Error generating issue summary. Please try again later.", "link": ""}
            ]
        }

def detect_and_track_issues(messages: List[Dict], user_id: str) -> List[Dict]:
    """
    Detect technical issues in messages and optionally track them
    
    Args:
        messages: List of message objects with text, user, channel, timestamp
        user_id: User ID for tracking issues
    
    Returns:
        List of detected issues with metadata
    """
    detected_issues = []
    
    for message in messages:
        message_text = message.get("text", "")
        issue_types = detect_issue_keywords(message_text)
        
        if issue_types:
            # This message contains issue-related keywords
            priority = extract_issue_priority(message_text)
            title = generate_issue_title(message_text)
            
            issue_data = {
                "title": title,
                "original_text": message_text,
                "channel": message.get("channel", ""),
                "reporter": message.get("user", ""),
                "timestamp": message.get("ts", ""),
                "message_ts": message.get("ts", ""),
                "types": issue_types,
                "priority": priority,
                "tags": issue_types  # Use detected types as tags
            }
            
            detected_issues.append(issue_data)
            
            # Optionally auto-track critical issues
            if priority == "critical":
                print(f"🚨 Critical issue detected: {title}")
                # You could auto-create the issue here:
                # issue_id = user_settings.create_issue(user_id, issue_data)
                # print(f"🆔 Auto-tracked as issue ID: {issue_id}")
    
    return detected_issues

@slack_app.command("/digest")
async def handle_digest_command(ack, respond, command, client):
    """Handle the /digest slash command"""
    # Acknowledge the command immediately
    await ack("Crunching the latest threads…")
    
    try:
        # Get channel ID and user ID
        channel_id = command["channel_id"]
        user_id = command["user_id"]
        
        # Get user's saved settings
        keywords = user_settings.get_user_keywords(user_id) or DEFAULT_KEYWORDS
        hours = user_settings.get_user_hours(user_id)
        include_own_messages = True  # Default to include own messages for better testing
        
        print(f"📋 User settings: keywords={keywords}, hours={hours}, include_own={include_own_messages}")
        
        # Calculate timestamp based on custom hours
        time_ago = datetime.now() - timedelta(hours=hours)
        oldest_timestamp = str(time_ago.timestamp())
        
        # Fetch channel messages from specified time range
        response = await client.conversations_history(
            channel=channel_id,
            oldest=oldest_timestamp,
            limit=200  # Adjust as needed
        )
        
        messages = response["messages"]
        
        # Debug: Print message info
        print(f"📊 DEBUG: Found {len(messages)} total messages in last {hours}h")
        
        # Filter messages
        filtered_messages = []
        for message in messages:
            # Debug: Print each message info
            msg_text = message.get("text", "")
            msg_user = message.get("user", "unknown")
            has_subtype = "subtype" in message
            print(f"🔍 DEBUG: Message from {msg_user}: '{msg_text[:50]}...' (subtype: {has_subtype})")
            
            # Skip messages with subtypes (bot messages, etc.)
            if "subtype" in message:
                print(f"⏭️  Skipping message with subtype: {message.get('subtype')}")
                continue
            
            # Skip messages from the invoking user (if not including own messages)
            if not include_own_messages and message.get("user") == user_id:
                print(f"⏭️  Skipping message from invoking user: {user_id}")
                continue
            
            # Check if message contains any keywords (case-insensitive)
            # If no keywords are set, include all messages
            message_text = message.get("text", "").lower()
            if keywords:
                keyword_match = any(keyword.lower() in message_text for keyword in keywords)
                print(f"🔎 Keywords check: '{message_text[:30]}...' -> Match: {keyword_match}")
            else:
                keyword_match = True
                print(f"🔎 No keywords set - including all messages")
            
            if keyword_match:
                # Get user info for display name
                try:
                    user_info = await client.users_info(user=message["user"])
                    username = user_info["user"]["display_name"] or user_info["user"]["real_name"] or message["user"]
                except:
                    username = message["user"]
                
                formatted_message = f"[{username}] {message.get('text', '')}"
                filtered_messages.append({
                    "formatted": formatted_message,
                    "ts": message["ts"],
                    "text": message.get("text", "")
                })
        
        if not filtered_messages:
            if keywords:
                await respond(f"No relevant messages found in the last {hours} hours matching the keywords: {', '.join(keywords)}")
            else:
                await respond(f"No messages found in the last {hours} hours")
            return
        
        # Summarize messages
        message_texts = [msg["formatted"] for msg in filtered_messages]
        summary = summarize(message_texts, user_id)
        
        # Create Slack blocks for the response
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Your Slack Digest (Last {hours}h)!"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Add each bullet point as a section block
        for i, bullet in enumerate(summary.get("bullets", [])):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {bullet['text']}"
                }
            })
            
            # Add a button to view original thread if we have matching messages
            if i < len(filtered_messages):
                blocks.append({
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Thread"
                            },
                            "url": f"https://slack.com/app_redirect?channel={channel_id}&message_ts={filtered_messages[i]['ts']}"
                        }
                    ]
                })
        
        # Add footer
        footer_text = f"_Analyzed {len(filtered_messages)} relevant messages"
        if keywords:
            footer_text += f" • Keywords: {', '.join(keywords)}"
        else:
            footer_text += " • No keyword filtering"
        footer_text += "_"
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": footer_text
                }
            ]
        })
        
        # Send the digest
        await respond(blocks=blocks)
        
    except Exception as e:
        print(f"Error processing digest command: {e}")
        await respond("Sorry, there was an error generating the digest. Please try again.")

@slack_app.command("/digest-config")
async def handle_config_command(ack, respond, command, client):
    """Handle the /digest-config command for user customization"""
    await ack("⚙️ Processing configuration...")
    
    try:
        user_id = command["user_id"]
        command_text = command.get("text", "").strip()
        
        if not command_text:
            # Show current settings using Block Kit
            user_prompt = user_settings.get_user_prompt(user_id)
            user_keywords = user_settings.get_user_keywords(user_id) or DEFAULT_KEYWORDS
            user_hours = user_settings.get_user_hours(user_id)
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "⚙️ Your Current Digest Settings"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Custom Prompt:*\n{user_prompt if user_prompt else '_using default_'}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Default Hours:*\n{user_hours}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Keywords:*\n{', '.join(user_keywords)}"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "• `/digest-config prompt \"Your custom analysis style here\"`\n• `/digest-config keywords word1,word2,word3`\n• `/digest-config hours 48`\n• `/digest-config reset` - Clear all custom settings"
                    }
                }
            ]
            
            await respond(blocks=blocks, delete_original=True)
            return
        
        # Parse configuration command
        print(f"🔧 DEBUG: Command text received: '{command_text}'")
        parts = command_text.split()
        print(f"🔧 DEBUG: Split parts: {parts}")
        
        if len(parts) < 1:
            await respond("❌ Invalid format. Use: `/digest-config prompt \"your prompt\"`, `/digest-config keywords word1,word2`, or `/digest-config reset`", delete_original=True)
            return
        
        config_type = parts[0].lower()
        print(f"🔧 DEBUG: Config type: '{config_type}'")
        
        # Handle single-word commands like "reset"
        if config_type == "reset":
            print(f"🔄 DEBUG: Resetting settings for user {user_id}")
            user_settings.clear_user_settings(user_id)
            print(f"🔄 DEBUG: Settings cleared, current settings: {user_settings.get_user_settings(user_id)}")
            await respond("✅ All custom settings cleared. Using defaults now.", delete_original=True)
            return
        
        # For other commands, we need a value - rejoin the rest as the value
        if len(parts) < 2:
            await respond("❌ Invalid format. Use: `/digest-config prompt \"your prompt\"`, `/digest-config keywords word1,word2`, or `/digest-config reset`", delete_original=True)
            return
        
        config_value = " ".join(parts[1:]).strip().strip('"')
        print(f"🔧 DEBUG: Config value: '{config_value}'")
        
        if config_type == "prompt":
            user_settings.set_user_prompt(user_id, config_value)
            await respond(f"✅ Custom prompt set! Your digests will now use this additional context:\n\n*{config_value}*", delete_original=True)
        
        elif config_type == "keywords":
            keywords = [k.strip() for k in config_value.split(",") if k.strip()]
            if keywords:
                user_settings.set_user_keywords(user_id, keywords)
                await respond(f"✅ Keywords updated: {', '.join(keywords)}", delete_original=True)
            else:
                await respond("❌ Please provide valid keywords separated by commas", delete_original=True)
        
        elif config_type == "hours":
            try:
                hours = int(config_value)
                if 1 <= hours <= 168:  # 1 hour to 1 week
                    user_settings.set_user_hours(user_id, hours)
                    await respond(f"✅ Default time range set to {hours} hours", delete_original=True)
                else:
                    await respond("❌ Hours must be between 1 and 168 (1 week)", delete_original=True)
            except ValueError:
                await respond("❌ Please provide a valid number for hours", delete_original=True)
        
        else:
            await respond(f"❌ Unknown config type: {config_type}. Use: prompt, keywords, hours, or reset", delete_original=True)
    
    except Exception as e:
        print(f"Error processing config command: {e}")
        await respond("Sorry, there was an error processing your configuration.", delete_original=True)

@slack_app.command("/digest-project")
async def handle_project_command(ack, respond, command, client):
    """Handle the /digest-project command for multi-channel project tracking"""
    await ack("🔍 Analyzing project across channels...")
    
    try:
        user_id = command["user_id"]
        command_text = command.get("text", "").strip()
        
        if not command_text:
            # Show project management interface
            user_projects = user_settings.get_user_projects(user_id)
            
            if not user_projects:
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🚀 Project Tracking"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "No projects configured yet. Create your first project to track discussions across multiple channels!"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Commands:*\n• `/digest-project create [name] #channel1,#channel2 [keywords]`\n• `/digest-project [name]` - Get project digest\n• `/digest-project list` - Show all projects\n• `/digest-project config [name]` - Configure project"
                        }
                    }
                ]
            else:
                # Show existing projects
                project_list = []
                for name, config in user_projects.items():
                    status = "🟢 Active" if config.get("active", True) else "🔴 Inactive"
                    channels = ", ".join([f"#{ch}" for ch in config.get("channels", [])])
                    project_list.append(f"*{name}* - {status}\n  Channels: {channels}")
                
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🚀 Your Projects"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "\n\n".join(project_list)
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Commands:*\n• `/digest-project [name]` - Get project digest\n• `/digest-project create [name] #channel1,#channel2`\n• `/digest-project config [name]` - Configure project"
                        }
                    }
                ]
            
            await respond(blocks=blocks, delete_original=True)
            return
        
        # Parse command
        parts = command_text.split()
        subcommand = parts[0].lower()
        
        if subcommand == "create":
            if len(parts) < 3:
                await respond("❌ Usage: `/digest-project create [project-name] #channel1,#channel2 [optional-keywords]`", delete_original=True)
                return
            
            project_name = parts[1]
            channels_str = parts[2]
            keywords = parts[3:] if len(parts) > 3 else []
            
            # Parse channels (remove # and split by comma)
            channels = []
            for ch in channels_str.split(","):
                ch = ch.strip().lstrip("#")
                if ch:
                    channels.append(ch)
            
            if not channels:
                await respond("❌ Please specify at least one channel", delete_original=True)
                return
            
            # Validate channels exist (optional - you might want to skip this for simplicity)
            user_settings.create_project(user_id, project_name, channels, keywords)
            
            channels_display = ", ".join([f"#{ch}" for ch in channels])
            keywords_display = f" with keywords: {', '.join(keywords)}" if keywords else ""
            
            await respond(f"✅ Project '{project_name}' created!\n📍 Tracking channels: {channels_display}{keywords_display}", delete_original=True)
            return
        
        elif subcommand == "list":
            user_projects = user_settings.get_user_projects(user_id)
            if not user_projects:
                await respond("No projects configured. Use `/digest-project create` to get started!", delete_original=True)
                return
            
            project_list = []
            for name, config in user_projects.items():
                status = "🟢" if config.get("active", True) else "🔴"
                channels = ", ".join([f"#{ch}" for ch in config.get("channels", [])])
                keywords = config.get("keywords", [])
                keyword_text = f" | Keywords: {', '.join(keywords)}" if keywords else ""
                project_list.append(f"{status} *{name}* - {channels}{keyword_text}")
            
            await respond(f"📋 Your Projects:\n\n" + "\n".join(project_list), delete_original=True)
            return
        
        elif subcommand == "config":
            if len(parts) < 2:
                await respond("❌ Usage: `/digest-project config [project-name]`", delete_original=True)
                return
            
            project_name = parts[1]
            project = user_settings.get_project(user_id, project_name)
            
            if not project:
                await respond(f"❌ Project '{project_name}' not found", delete_original=True)
                return
            
            status = "Active" if project.get("active", True) else "Inactive"
            channels = ", ".join([f"#{ch}" for ch in project.get("channels", [])])
            keywords = ", ".join(project.get("keywords", [])) or "None"
            created = project.get("created_at", "Unknown")
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"⚙️ Project: {project_name}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Status:* {status}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Created:* {created[:10]}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Channels:* {channels}\n*Keywords:* {keywords}"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available actions:*\n• `/digest-project {project_name}` - Get digest\n• Contact admin to modify channels/keywords"
                    }
                }
            ]
            
            await respond(blocks=blocks, delete_original=True)
            return
        
        else:
            # Treat as project name for digest generation
            project_name = subcommand
            project = user_settings.get_project(user_id, project_name)
            
            if not project:
                await respond(f"❌ Project '{project_name}' not found. Use `/digest-project list` to see available projects.", delete_original=True)
                return
            
            if not project.get("active", True):
                await respond(f"❌ Project '{project_name}' is inactive. Contact admin to reactivate.", delete_original=True)
                return
            
            # Get project configuration
            channels = project.get("channels", [])
            project_keywords = project.get("keywords", [])
            
            # Get user's default time range
            hours = user_settings.get_user_hours(user_id)
            time_ago = datetime.now() - timedelta(hours=hours)
            oldest_timestamp = str(time_ago.timestamp())
            
            print(f"🚀 PROJECT DIGEST: {project_name} across {len(channels)} channels: {channels}")
            
            # Collect messages from all channels
            all_messages = []
            channel_message_counts = {}
            
            for channel in channels:
                try:
                    # Get channel info to convert name to ID if needed
                    if not channel.startswith('C'):  # If it's a channel name, not ID
                        try:
                            channel_info = await client.conversations_list()
                            channel_id = None
                            for ch in channel_info["channels"]:
                                if ch["name"] == channel:
                                    channel_id = ch["id"]
                                    break
                            if not channel_id:
                                print(f"⚠️ Channel #{channel} not found, skipping")
                                continue
                        except Exception as e:
                            print(f"⚠️ Error finding channel #{channel}: {e}")
                            continue
                    else:
                        channel_id = channel
                    
                    # Fetch messages from this channel
                    response = await client.conversations_history(
                        channel=channel_id,
                        oldest=oldest_timestamp,
                        limit=100
                    )
                    
                    messages = response["messages"]
                    channel_message_counts[channel] = len(messages)
                    
                    # Filter and format messages
                    for message in messages:
                        # Skip bot messages
                        if "subtype" in message:
                            continue
                        
                        message_text = message.get("text", "").lower()
                        
                        # Check project keywords
                        if project_keywords:
                            keyword_match = any(keyword.lower() in message_text for keyword in project_keywords)
                            if not keyword_match:
                                continue
                        
                        # Get user info
                        try:
                            user_info = await client.users_info(user=message["user"])
                            username = user_info["user"]["display_name"] or user_info["user"]["real_name"] or message["user"]
                        except:
                            username = message["user"]
                        
                        # Format message with channel context
                        formatted_message = f"[#{channel}] [{username}] {message.get('text', '')}"
                        all_messages.append({
                            "formatted": formatted_message,
                            "ts": message["ts"],
                            "channel": channel,
                            "channel_id": channel_id,
                            "text": message.get("text", "")
                        })
                
                except Exception as e:
                    print(f"Error fetching from channel #{channel}: {e}")
                    continue
            
            if not all_messages:
                keyword_text = f" matching keywords: {', '.join(project_keywords)}" if project_keywords else ""
                await respond(f"No messages found for project '{project_name}' in the last {hours} hours{keyword_text}", delete_original=True)
                return
            
            # Sort messages by timestamp
            all_messages.sort(key=lambda x: float(x["ts"]))
            
            # Generate project summary
            message_texts = [msg["formatted"] for msg in all_messages]
            summary = summarize_project(message_texts, project_name, channels, user_id)
            
            # Create response blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚀 Project Digest: {project_name}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📊 {len(all_messages)} messages across {len(channels)} channels • Last {hours}h"
                        }
                    ]
                },
                {
                    "type": "divider"
                }
            ]
            
            # Add bullet points
            for i, bullet in enumerate(summary.get("bullets", [])):
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• {bullet['text']}"
                    }
                })
            
            # Add channel breakdown
            channel_breakdown = []
            for channel, count in channel_message_counts.items():
                if count > 0:
                    channel_breakdown.append(f"#{channel}: {count}")
            
            if channel_breakdown:
                blocks.append({
                    "type": "divider"
                })
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📈 Channel activity: {' | '.join(channel_breakdown)}"
                        }
                    ]
                })
            
            await respond(blocks=blocks, delete_original=True)
    
    except Exception as e:
        print(f"Error processing project command: {e}")
        await respond("Sorry, there was an error processing your project request.", delete_original=True)

@slack_app.command("/digest-issues")
async def handle_issues_command(ack, respond, command, client):
    """Handle the /digest-issues command for technical issue tracking"""
    await ack("🔍 Analyzing technical issues...")
    
    try:
        user_id = command["user_id"]
        command_text = command.get("text", "").strip()
        channel_id = command["channel_id"]
        
        if not command_text:
            # Show issue dashboard
            user_issues = user_settings.get_user_issues(user_id)
            stats = user_settings.get_issue_statistics(user_id)
            
            if not user_issues:
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🔧 Technical Issue Tracking"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "No issues tracked yet. Use `/digest-issues scan` to analyze recent messages for technical problems."
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Commands:*\n• `/digest-issues scan [hours]` - Scan for new issues\n• `/digest-issues list [status]` - List tracked issues\n• `/digest-issues stats` - View issue statistics\n• `/digest-issues search [query]` - Search issues"
                        }
                    }
                ]
            else:
                # Show issue dashboard
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🔧 Issue Dashboard"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Total Issues:* {stats['total']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Recent Activity:* {stats['recent_activity']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Open:* {stats['open']} | *Investigating:* {stats['investigating']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Resolved:* {stats['resolved']} | *Closed:* {stats['closed']}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Priority Breakdown:* Critical: {stats['by_priority']['critical']} | High: {stats['by_priority']['high']} | Medium: {stats['by_priority']['medium']} | Low: {stats['by_priority']['low']}"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Commands:*\n• `/digest-issues scan` - Scan for new issues\n• `/digest-issues list open` - List open issues\n• `/digest-issues search [query]` - Search issues"
                        }
                    }
                ]
            
            await respond(blocks=blocks, delete_original=True)
            return
        
        # Parse command
        parts = command_text.split()
        subcommand = parts[0].lower()
        
        if subcommand == "scan":
            # Scan for issues in recent messages
            hours = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else user_settings.get_user_hours(user_id)
            
            # Calculate timestamp
            time_ago = datetime.now() - timedelta(hours=hours)
            oldest_timestamp = str(time_ago.timestamp())
            
            print(f"🔍 ISSUE SCAN: Analyzing last {hours}h for technical issues")
            
            # Fetch channel messages
            response = await client.conversations_history(
                channel=channel_id,
                oldest=oldest_timestamp,
                limit=200
            )
            
            messages = response["messages"]
            
            # Convert to format needed for issue detection
            formatted_messages = []
            for message in messages:
                if "subtype" in message:  # Skip bot messages
                    continue
                
                # Get user info
                try:
                    user_info = await client.users_info(user=message["user"])
                    username = user_info["user"]["display_name"] or user_info["user"]["real_name"] or message["user"]
                except:
                    username = message["user"]
                
                formatted_messages.append({
                    "text": message.get("text", ""),
                    "user": username,
                    "user_id": message.get("user", ""),
                    "channel": channel_id,
                    "ts": message.get("ts", ""),
                    "formatted": f"[{username}] {message.get('text', '')}"
                })
            
            # Detect issues
            detected_issues = detect_and_track_issues(formatted_messages, user_id)
            
            if not detected_issues:
                await respond(f"✅ No technical issues detected in the last {hours} hours.", delete_original=True)
                return
            
            # Auto-track detected issues
            new_issues = []
            for issue_data in detected_issues:
                issue_id = user_settings.create_issue(user_id, issue_data)
                issue_data["id"] = issue_id
                new_issues.append(issue_data)
                print(f"📝 Created issue {issue_id}: {issue_data['title']}")
            
            # Generate issue-focused summary
            message_texts = [msg["formatted"] for msg in formatted_messages if any(kw in msg["text"].lower() for kw in ["bug", "issue", "problem", "failure", "error", "broken", "crash"])]
            
            if message_texts:
                summary = summarize_issues(message_texts, user_id, detected_issues)
            else:
                summary = {"bullets": [{"text": f"Found {len(detected_issues)} potential issues", "link": ""}]}
            
            # Create response
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔍 Issue Scan Results ({hours}h)"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🆕 {len(new_issues)} new issues detected and tracked"
                        }
                    ]
                },
                {
                    "type": "divider"
                }
            ]
            
            # Add AI summary
            for bullet in summary.get("bullets", []):
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• {bullet['text']}"
                    }
                })
            
            # Add detected issues list
            if new_issues:
                blocks.append({"type": "divider"})
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🆕 New Issues Detected:*"
                    }
                })
                
                for issue in new_issues[:5]:  # Show first 5
                    priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(issue["priority"], "🟡")
                    types_text = ", ".join(issue["types"][:3])  # Show first 3 types
                    
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{priority_emoji} *{issue['id']}* - {issue['title']}\n_{types_text}_"
                        }
                    })
                
                if len(new_issues) > 5:
                    blocks.append({
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"_+{len(new_issues) - 5} more issues. Use `/digest-issues list` to see all._"
                            }
                        ]
                    })
            
            await respond(blocks=blocks, delete_original=True)
        
        elif subcommand == "list":
            # List issues with optional status filter
            status_filter = parts[1] if len(parts) > 1 else None
            issues = user_settings.get_user_issues(user_id, status_filter)
            
            if not issues:
                status_text = f" with status '{status_filter}'" if status_filter else ""
                await respond(f"No issues found{status_text}.", delete_original=True)
                return
            
            # Create blocks for issue list
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📋 Issues List {f'({status_filter})' if status_filter else ''}"
                    }
                }
            ]
            
            # Sort by priority and date
            sorted_issues = sorted(issues.values(), 
                                 key=lambda x: (
                                     {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.get("priority", "medium"), 2),
                                     x.get("updated_at", "")
                                 ), reverse=True)
            
            for issue in sorted_issues[:10]:  # Show first 10
                priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(issue["priority"], "🟡")
                status_emoji = {"open": "🔴", "investigating": "🟡", "resolved": "🟢", "closed": "⚫"}.get(issue["status"], "🔴")
                
                created_date = issue.get("created_at", "")[:10]  # Just the date part
                channel_name = issue.get("channel", "").replace("C", "#")
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{priority_emoji}{status_emoji} *{issue['id']}* - {issue['title']}\n_{channel_name} • {created_date} • {issue.get('priority', 'medium')} priority_"
                    }
                })
            
            if len(sorted_issues) > 10:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_Showing 10 of {len(sorted_issues)} issues._"
                        }
                    ]
                })
            
            await respond(blocks=blocks, delete_original=True)
        
        elif subcommand == "stats":
            # Show detailed statistics
            stats = user_settings.get_issue_statistics(user_id)
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Issue Statistics"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Issues:*\n{stats['total']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Recent Activity (24h):*\n{stats['recent_activity']}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*By Status:*\n🔴 Open: {stats['open']}\n🟡 Investigating: {stats['investigating']}\n🟢 Resolved: {stats['resolved']}\n⚫ Closed: {stats['closed']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*By Priority:*\n🔴 Critical: {stats['by_priority']['critical']}\n🟠 High: {stats['by_priority']['high']}\n🟡 Medium: {stats['by_priority']['medium']}\n🟢 Low: {stats['by_priority']['low']}"
                    }
                }
            ]
            
            await respond(blocks=blocks, delete_original=True)
        
        elif subcommand == "search":
            # Search issues
            if len(parts) < 2:
                await respond("❌ Usage: `/digest-issues search [query]`", delete_original=True)
                return
            
            query = " ".join(parts[1:])
            results = user_settings.search_issues(user_id, query)
            
            if not results:
                await respond(f"No issues found matching '{query}'.", delete_original=True)
                return
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔍 Search Results: '{query}'"
                    }
                }
            ]
            
            for issue in results[:8]:  # Show first 8 results
                priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(issue["priority"], "🟡")
                status_emoji = {"open": "🔴", "investigating": "🟡", "resolved": "🟢", "closed": "⚫"}.get(issue["status"], "🔴")
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{priority_emoji}{status_emoji} *{issue['id']}* - {issue['title']}\n_{issue.get('channel', '')} • {issue.get('status', 'open')} • {issue.get('priority', 'medium')}_"
                    }
                })
            
            if len(results) > 8:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_Showing 8 of {len(results)} results._"
                        }
                    ]
                })
            
            await respond(blocks=blocks, delete_original=True)
        
        else:
            await respond(f"❌ Unknown command: {subcommand}. Use `/digest-issues` to see available commands.", delete_original=True)
    
    except Exception as e:
        print(f"Error processing issues command: {e}")
        await respond("Sorry, there was an error processing your issue request.", delete_original=True)

# Initialize FastAPI app
app = FastAPI()
handler = AsyncSlackRequestHandler(slack_app)

@app.post("/slack/events")
async def endpoint(req: Request):
    """FastAPI endpoint to receive Slack events"""
    return await handler.handle(req)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "Slack Digest AI is running!"}

@app.get("/digest")
async def digest_endpoint():
    """Alternative endpoint info"""
    return {"message": "Use the /digest slash command in Slack to generate digests"}

if __name__ == "__main__":
    import uvicorn
    # TODO: Replace with your actual domain/ngrok URL for production
    uvicorn.run(app, host="0.0.0.0", port=3000)
