# plan-subagents2

First, **read the CLAUDE subagent documentation**: [link](https://docs.anthropic.com/en/docs/claude-code/sub-agents). Extract key information about CLAUDE sub-agents: what they are, how to create them, best practices, and usage patterns.

Second, **analyze current project**:
- read all the documentation,
- search files structure,
- read code in certain files (if it needs),
- analyze `/.claude/agents` folder to study agents that already in production.

Third, **add, modify, or delete CLAUDE sub‑agents** so they exactly match the project’s needs. Select sub‑agents only from the list below. Each sub‑agent is created EXCLUSIVELY for this project:
```
# name: senior-frontend
# communicates_with: senior-backend, lead-qa, lead-devops
# responsibilities: javascript, typescript, react, vue, angular, nodejs
# usage: engage for front‑end tasks
# usage_example: “When a React component needs refactoring, contact senior-frontend”

# name: senior-backend
# communicates_with: senior-frontend, lead-qa, lead-devops
# responsibilities: architecture, server logic, API, databases
# usage: engage for back‑end tasks
# usage_example: “To optimize the REST API, use senior-backend”

# name: senior-python/ruby/c/cpp/csh/go/java/etc
# communicates_with: senior-frontend, senior-backend, lead-qa
# responsibilities: programming in the specified language
# usage: engage when expertise in a specific language is required
# usage_example: “For a Python script, consult senior-python”

# name: senior-uiux
# communicates_with: senior-frontend, senior-backend
# responsibilities: user‑experience research, interface design
# usage: engage for UX/UI tasks
# usage_example: “To prototype a new screen, involve senior-uiux”

# name: lead-qa
# communicates_with: senior-frontend, senior-backend, senior-python/…, lead-devops
# responsibilities: testing, code review, quality control, infrastructure checks
# usage: engage for QA processes
# usage_example: “Before release, ask lead-qa to run regression testing”

# name: lead-devops
# communicates_with: senior-frontend, senior-backend, lead-qa
# responsibilities: CI/CD, Docker, security
# usage: engage for DevOps processes
# usage_example: “To configure the CI pipeline, use lead-devops”

```

Finally, **make a TODO list plan and ask** user to add/edit/delete (update) CLAUDE subagents.

IMPORTANT: to create CLAUDE subagents call meta agent! All the agents should be strictly created by meta-agent.
