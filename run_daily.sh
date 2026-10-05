#!/bin/zsh
# Daily: find new remote jobs matching a saved CV profile and email them.
# Triggered by a launchd agent (see launchd/linkedin-job-match.plist.example)
cd "$HOME/.claude/skills/linkedin-job-match" || exit 1
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
# launchd also fires on wake if the Mac was asleep; skip if today's run already happened
today=$(date +%F)
[[ -f state/last_run && "$(cat state/last_run)" == "$today" ]] && exit 0
echo "$today" > state/last_run
claude -p "Run the linkedin-job-match skill in Daily mode for the profile set in ~/.claude/skills/linkedin-job-match/config.local.md. Follow the 'Daily mode' section of ~/.claude/skills/linkedin-job-match/SKILL.md exactly, without asking questions." \
  --allowedTools "Bash Read Write Edit Skill ToolSearch mcp__claude_ai_composio_for_you__COMPOSIO_SEARCH_TOOLS mcp__claude_ai_composio_for_you__COMPOSIO_GET_TOOL_SCHEMAS mcp__claude_ai_composio_for_you__COMPOSIO_MULTI_EXECUTE_TOOL" \
  >> "state/run_$today.log" 2>&1
