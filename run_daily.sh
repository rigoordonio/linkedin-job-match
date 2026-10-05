#!/bin/zsh
# Daily: find new remote jobs matching a saved CV profile and email them.
# Triggered by a launchd agent (see launchd/linkedin-job-match.plist.example)
cd "$HOME/.claude/skills/linkedin-job-match" || exit 1
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
mkdir -p state
today=$(date +%F)
# launchd also fires on wake if the Mac was asleep; skip if today's run already succeeded
[[ -f state/last_run && "$(cat state/last_run)" == "$today" ]] && exit 0
# only one run at a time
mkdir state/run.lock 2>/dev/null || exit 0
trap 'rmdir state/run.lock' EXIT

# a run succeeded if it logged a line for today that isn't a fetch failure
finished_today() {
  grep "^$today " state/log.txt 2>/dev/null | grep -qv "fetch failed"
}

for attempt in 1 2 3; do
  echo "=== attempt $attempt $(date +%T)" >> "state/run_$today.log"
  claude -p "Run the linkedin-job-match skill in Daily mode for the profile set in ~/.claude/skills/linkedin-job-match/config.local.md. Follow the 'Daily mode' section of ~/.claude/skills/linkedin-job-match/SKILL.md exactly, without asking questions." \
    --allowedTools "Bash Read Write Edit Skill ToolSearch mcp__claude_ai_composio_for_you__COMPOSIO_SEARCH_TOOLS mcp__claude_ai_composio_for_you__COMPOSIO_GET_TOOL_SCHEMAS mcp__claude_ai_composio_for_you__COMPOSIO_MULTI_EXECUTE_TOOL" \
    >> "state/run_$today.log" 2>&1
  if finished_today; then
    echo "$today" > state/last_run
    exit 0
  fi
  # no log line, or "fetch failed": wait 30 minutes and try again
  # (already-sent jobs are skipped via the sent-jobs file, so a retry won't resend them)
  [[ $attempt -lt 3 ]] && sleep 1800
done
echo "$today | jobs found: ? | jobs sent: 0 | status: gave up after 3 attempts" >> state/log.txt
echo "$today" > state/last_run
exit 1
