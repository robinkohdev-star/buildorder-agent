# BuildOrder Agent

**Coding Agent** powered by Kimi k2.5 (planning) and Qwen 3.6 Plus (implementation) via OpenCode.

## Mission
Plans architecture with Kimi k2.5, implements code with Qwen 3.6 Plus on fresh branches, posts summaries to Discord for review.

## Models

### Planning Phase
- **Model**: Kimi k2.5 (`opencode-go/kimi-k2.5`)
- **Temperature**: 0.4
- **Role**: Architecture design, task breakdown, code review

### Implementation Phase
- **Model**: Qwen 3.6 Plus (`qwen/qwen3.6-plus`)
- **Temperature**: 0.2
- **Role**: Code generation, refactoring, bug fixes

## Workflow
1. Fetch pending tasks from task sources
2. **Plan** with Kimi k2.5 → Architecture & file structure
3. **Implement** with Qwen 3.6 Plus → Production code
4. Create fresh git branch (`buildorder/{task-id}`)
5. Write files and commit
6. Post summary to Discord

## Schedule
Runs every 6 hours.

## Setup

```bash
cp .env.example .env
pip install -r requirements.txt
python agent.py
```

## Output
Discord notification with:
- Task title and branch name
- Models used in pipeline
- Files modified
- Ready for review status
