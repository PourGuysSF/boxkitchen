---
name: ship
description: Plan, implement, and verify a boxkitchen feature end to end
---
1. Read CLAUDE.md and git log -10 to reload project context.
2. Restate the feature in plain language and ask me to confirm before writing code.
3. If this needs a database change, give me the SQL as a separate block FIRST. I run it in Supabase and confirm it landed before you write any code.
4. Branch from current main: git checkout -b <name> origin/main. Never commit on main.
5. Implement in small commits; never touch prod data without asking. State "MODIFIED: <files>" and touch nothing else.
6. Verify the change actually saves to Supabase, then check RLS policies on any new table.
7. Stop before pushing. Pushing rebuilds the live site — I approve that separately, every time.
8. Summarize what shipped in non-technical language.
