# Project Context

When working with this codebase, prioritize readability over cleverness. Ask clarifying questions before making architectural changes.

## About This Project

A home automation app ("Remander") that primarily configures Reolink security cameras for different
behavior when "at home" vs "away from home" (e.g., configure the cameras to provide limited notifcations
when the user is "at home" but have full notifications when they are away form home) by using the Reolink
NVR API.  It will also need to talk to some non-Reolink devices such as power switches (e.g. to power on
cameras that are off when "at home").

## Standards

- Python 3.14
- Use full type annotation with the latest annotation styles (e.g., prefer "int | None" over "Optional[int]")
- pytest for testing
- Black formatting with 100 character lines
- Assume we are using the latest version of all frameworks, libraries and tools unless otherwise specifically stated
- Use fully async Python code as much as possible

## Frameworks, Tools, & Librararies

- Web UI/Frontend:
  - FastAPI
  - Server side rendered Jinja2 templates
  - HTMX "hypermedia first" approach
  - Tailwind CSS for styling and CSS
- Backend:
  - SQLite database for now but could go PostgreSQL in the future
  - Tortoise ORM
  - Pedantic AI as a workflow engine to handle complex workflows during a "set away" or "set home" operation
- Both frontend and backend:
  - Use the Python attrs package for classes unless there is a reason not to (if so, insert a comment at the top of the class stating the reason)
