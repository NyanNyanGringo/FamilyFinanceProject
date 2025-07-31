# My name is...
Call me My Lord.

# Better Google Sheet understanding:
- To understand structure in Google Sheet read `/aidocs/about_google_sheet.md`


# How to use mcp
- Always use context7 to find actual information about libraries you work with
- Always use sequentials thinking


# How to use agents
1. To make the plan for senior-python call lead-qa agents
2. According to plan, senior-python implement changes
3. Ask lead-qa to logic-review and code-review
4. Repeat steps 1 to 3 until result will be succeeded


# Code rools you and agents should follow:
1. Use clear, concise, context-rich names so the reader immediately understands the purpose of every variable, function, or class.
2. Break programs into very small functions, each doing only one thing—and doing it well.
3. Follow the Single Responsibility Principle: every module, class, or method should have just one reason to change.
4. Remove duplication, because repeated code breeds errors and burdens maintenance.
5. Write code that conveys intent; if a comment is needed merely to explain “what’s happening,” rewrite the code so it speaks for itself.
6. Minimize side effects and mutable state—pure functions are far easier to test and refactor.
7. Handle errors carefully: report failures clearly, avoid swallowing exceptions, and never leave the system in an inconsistent state.
8. Control dependencies: low-level details must not dictate architecture, and modules should interact only through well-defined interfaces.
9. Keep automated tests covering critical logic; tests act as living documentation and guard against regressions.
10. Refactor continually: eliminate dead code, simplify constructs, and maintain consistent formatting so the code stays readable and truly “clean.”
