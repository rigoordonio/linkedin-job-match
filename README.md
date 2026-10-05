# LinkedIn Remote Job Match

A Claude Code skill that finds fresh remote LinkedIn jobs matching a friend's CV, ranks them by fit, and either drafts a ready-to-paste message or emails the best matches every morning.

## What it does

**On demand** (`/linkedin-job-match`)
1. Reads the person's CV (PDF) and pulls out role, experience, tools, industries and location.
2. Fetches recent remote job postings from LinkedIn's public job search (no login).
3. Checks each description to confirm the job is actually remote; LinkedIn's remote filter is noisy.
4. Ranks the top 5–8 by fit: role, years of experience, tools, industry, schedule and pay.
5. Shows a ranked table with fit notes and skill gaps, plus a short, friendly message to paste into LinkedIn chat.

**Daily mode** (unattended, every morning at 8:00)
1. Fetches remote jobs from the past 7 days, skipping any already sent.
2. Verifies and ranks them, keeping up to 20 genuine matches.
3. Emails them through Gmail (Composio), with the sender BCC'd.
4. Records the sent job IDs and logs the run. If there are no good new matches, it sends nothing.

## Files

| File | Purpose |
| --- | --- |
| `SKILL.md` | The skill instructions Claude follows |
| `scripts/fetch_jobs.py` | Fetches remote jobs from LinkedIn's public guest endpoints (standard library only) |
| `run_daily.sh` | Runs daily mode headlessly with `claude -p` |
| `launchd/linkedin-job-match.plist.example` | macOS launchd schedule (daily at 8:00) |
| `config.example.md` | Template for sender settings |
| `profiles/example.md` | Template for a person's CV profile |
| `config.local.md`, `profiles/*.local.md`, `state/` | Your personal data and run history (git-ignored) |

## Requirements

- macOS (for the launchd schedule) and Python 3
- [Claude Code](https://claude.com/claude-code)
- [Composio](https://composio.dev) with **Gmail** connected (daily mode only)

## Setup

```bash
git clone https://github.com/rigoordonio/linkedin-job-match.git ~/.claude/skills/linkedin-job-match
cd ~/.claude/skills/linkedin-job-match
cp config.example.md config.local.md                 # sender name and Gmail
cp profiles/example.md profiles/<name>.local.md      # fill in from the person's CV
mkdir -p state
```

**Daily schedule (optional)**

```bash
sed "s/YOUR_USER/$USER/g" launchd/linkedin-job-match.plist.example \
  > ~/Library/LaunchAgents/com.$USER.linkedin-job-match.plist
launchctl load ~/Library/LaunchAgents/com.$USER.linkedin-job-match.plist
```

The job runs at 8:00 every day. If the Mac was asleep, it runs on wake. Once a run succeeds, it won't run again that day.

**Error handling**
- If LinkedIn returns "Too Many Requests" (HTTP 429) or a server error, `fetch_jobs.py` waits 30, 60, then 120 seconds and tries again.
- If LinkedIn still refuses, the run switches to Composio web search in the same run.
- If the whole run fails, `run_daily.sh` tries again up to 3 times, 30 minutes apart. After that it logs "gave up after 3 attempts".
- Every run writes one line to `state/log.txt`: sent, no new matches, fetch failed, or gave up.
- A lock stops two runs from overlapping, and already-sent jobs are never resent.

## Usage

In Claude Code:

```
/linkedin-job-match
```

Or ask: *"Find remote jobs that match this CV for my friend."*

Test the daily run by hand: `./run_daily.sh` (it skips if it has already run today; delete `state/last_run` to force a run).

## Guardrails

- Never sends LinkedIn DMs. LinkedIn's API doesn't allow it, and automating it breaks LinkedIn's terms. You paste the message yourself.
- Daily emails go only to someone who has agreed to receive them.
- Uses only LinkedIn's public job pages, with pauses between requests. If LinkedIn rate-limits it, it waits and retries before falling back to web search.
- No API keys are stored in this repo. Gmail access is handled by your Composio account.
- CVs, emails and sent-job history stay in git-ignored local files.
