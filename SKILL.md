---
name: linkedin-job-match
description: Find the latest remote LinkedIn job postings that match someone's CV/resume, rank them by fit, and draft a ready-to-paste LinkedIn message with the links. Use when the user wants to send job leads to a friend or asks for remote jobs matching a CV.
---

# LinkedIn remote job match

Finds fresh remote LinkedIn jobs for a person, ranks them against their CV, and writes a
friendly LinkedIn message the user pastes into their chat with that person.

**Do not send the LinkedIn DM yourself.** LinkedIn's API (and the Composio LinkedIn
toolkit) cannot send direct messages, and browser-automated messaging breaks LinkedIn's
terms. The deliverable is a message for the user to copy-paste.

## Local files (read first)

All in `~/.claude/skills/linkedin-job-match/`, git-ignored:
- `config.local.md`: sender name, sender Gmail account, BCC, and which profile daily mode uses.
- `profiles/<name>.local.md`: one per person: recipient email, CV path, experience, tools,
  location, strengths, gaps, search keywords, industry weighting, email subject, sent-jobs file.

For a new person: read their CV first, then create `profiles/<name>.local.md` from
`profiles/example.md`.

## Steps

1. **Read the CV** (PDF via Read tool). Extract role, years, tools, industries, location.
2. **Fetch jobs** (public LinkedIn guest endpoints, remote filter, no login needed), using the
   profile's quick-run keywords and location:
   ```bash
   python3 ~/.claude/skills/linkedin-job-match/scripts/fetch_jobs.py \
     --keywords "<keyword>" "<keyword>" \
     --location <country> --days 14 --out "$SCRATCH/jobs.json"
   ```
   If it returns 0 jobs or errors (LinkedIn may rate-limit), fall back to Composio
   `COMPOSIO_SEARCH_WEB` with queries like `site:linkedin.com/jobs/view remote <role> <country>`.
3. **Verify remote.** LinkedIn's remote filter is noisy. Read each description: keep jobs that
   say Remote / WFH / Work from home; drop ones that say onsite, hybrid, or "amenable to
   work in <city>". If silent, keep only if strong fit and label "listed as remote — confirm".
4. **Rank by fit** (top 5–8): role match, required years vs. CV, tools overlap, industry
   overlap (use the profile's industry weighting), schedule (day shift / local time preferred),
   pay if stated. Skip roles that are mainly a different job.
5. **Draft the message**: warm, short, from the user to the friend. Per job: title — company,
   one-line "why it fits you", schedule/pay if known, link. Use short `linkedin.com/jobs/view/<id>`
   URLs. End with an offer to help. Keep under ~1,500 characters if possible.
6. **Show the user**: the ranked table (with fit notes and gaps), then the message in a code
   block for easy copying. Save a copy to `~/Downloads/job-leads-<name>-<date>.txt`.

## Daily mode — runs unattended every morning via launchd

The user authorized a daily automatic email to the person named in `config.local.md`
(2026-10-02). In daily mode do NOT ask questions; run start to finish.

**Finish in one turn.** This runs headless (`claude -p`), which exits the moment you end
your turn. Never use `run_in_background`, never say you will "wait" or "check back", and
never end with a step still pending. Every run must end with a line appended to
`state/log.txt` for today.

Files:
- The profile's sent-jobs file (e.g. `state/<name>_sent.json`) — job IDs already emailed. Never resend these.
- `state/log.txt` — append one line per run: date, jobs found, jobs sent, status.

Steps:
1. Fetch, excluding already-sent jobs, using the profile's daily-mode keywords:
   ```bash
   cd ~/.claude/skills/linkedin-job-match && python3 scripts/fetch_jobs.py \
     --keywords <daily-mode keywords from the profile> \
     --location <country> --days 7 --pages 2 \
     --exclude <sent-jobs file> --out state/today.json
   ```
   The script already waits and retries when LinkedIn rate-limits (up to ~4 minutes; use a
   Bash timeout of 600000 ms). Do not retry it yourself. If it exits with an error or returns
   0 jobs, go straight to the Composio `COMPOSIO_SEARCH_WEB` fallback in this same run
   (queries like `site:linkedin.com/jobs/view remote <keyword> <country>`), skip IDs already in
   the sent-jobs file, and read each job page with `COMPOSIO_SEARCH_FETCH_URL_CONTENT` before ranking.
2. Verify remote and rank exactly as in steps 3–4 above. Pick **up to 20** genuine matches.
   Quality over count: never pad with onsite/hybrid jobs or unrelated roles.
3. If 0 good new matches: send nothing, log "no new matches", stop. If both LinkedIn and the
   fallback failed, log "fetch failed: <reason>" (not "no new matches") and stop.
4. Send ONE email with Composio `GMAIL_SEND_EMAIL` (from the sender Gmail account in config):
   - `recipient_email`: the profile's recipient email
   - `bcc`: [the BCC address in config] (so the user sees what was sent)
   - `subject`: the profile's daily email subject (e.g. "Remote design jobs for you – Oct 3")
   - `is_html`: true. Body: short warm greeting from the sender, then a numbered list, each item:
     **bold job title – company** (linked to `https://www.linkedin.com/jobs/view/<id>`),
     one line on why it fits them, setup/schedule/pay if stated. Mark uncertain ones
     "listed as remote, please confirm". One closing line, signed with the sender name.
     Simple inline styles only, no images.
5. Only after the send succeeds: add the sent IDs to the sent-jobs file, append to
   the log. If the send fails, log the error and do not update the sent list.
