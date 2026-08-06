---
name: start
description: Initialize session and load context
---

Execute the mandatory startup checklist before we begin.

Run the Startup Protocol from CLAUDE.md:

1. Load or Create Project Configuration - Read .claude/config.yaml
2. Load Project Context Files - Read all .claude/*.md files
3. Check in-flight work: git status, git log --oneline -10, gh pr list / gh issue list --state open
4. Review Git History & Existing Tools - Check what changed
5. Check References & Credentials - Verify docs and .env files
6. Review Tool Registry - Inventory all tools by status
7. Project Status Briefing - Output the full briefing with recommended next steps

Actually execute the commands, don't just describe them.

End with the PROJECT STATUS BRIEFING and RECOMMENDED NEXT STEPS so I can choose what to work on.
