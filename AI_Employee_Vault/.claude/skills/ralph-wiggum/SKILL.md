---
name: ralph-wiggum
description: Stop hook that prevents Claude Code from exiting until task is in /Done/. Re-injects prompt if incomplete. Max 10 iterations before FAILED alert.
version: 1.0.0
trigger: Automatic - intercepts Claude Code exit signal
---

# Ralph Wiggum Stop Hook

## Purpose

Named after Ralph Wiggum's persistence, this stop hook ensures Claude Code doesn't exit until a task is truly complete. It intercepts the exit signal and checks if the current task file has been moved to `/Done/`. If not, it blocks the exit and re-injects the original prompt with previous output context.

## How It Works

1. **Exit Interception**: Hooks into Claude Code's exit signal
2. **Completion Check**: Verifies task file exists in `/Done/`
3. **Re-injection**: If not done, blocks exit and re-runs with context
4. **Iteration Tracking**: Counts attempts, stops at `RALPH_MAX_ITERATIONS` (default: 10)
5. **Failure Handling**: On max iterations, moves task to `/Needs_Action/FAILED_<task>.md` and writes `SYSTEM_ALERT_*.md`

## State File Format

The orchestrator creates a state file for each task:

```json
{
  "task_id": "TASK_abc123",
  "original_prompt": "Process this email and draft a response",
  "task_file": "/In_Progress/EMAIL_xyz.md",
  "done_file": "/Done/EMAIL_xyz.md",
  "iteration": 1,
  "max_iterations": 10,
  "started": "2026-01-07T10:00:00Z",
  "previous_outputs": [
    "Iteration 1: Analyzed email, need approval for response",
    "Iteration 2: Waiting for approval..."
  ]
}
```

## Exit Logic

```python
if task_file_exists_in_done():
    allow_exit()
else:
    if iteration < max_iterations:
        increment_iteration()
        reinject_prompt_with_context()
        block_exit()
    else:
        move_to_failed()
        create_system_alert()
        allow_exit()
```

## Configuration

Environment variables:
- `RALPH_MAX_ITERATIONS`: Maximum iterations before failure (default: 10)
- `RALPH_STATE_PATH`: Path to state files (default: `/tmp/ralph_state/`)

## Integration with Orchestrator

The orchestrator creates the state file when triggering Claude Code:

```python
state = {
    "task_id": generate_task_id(),
    "original_prompt": skill_content + "\n\n" + task_content,
    "task_file": str(in_progress_path / task_filename),
    "done_file": str(done_path / task_filename),
    "iteration": 1,
    "max_iterations": int(os.getenv("RALPH_MAX_ITERATIONS", "10")),
    "started": datetime.now().isoformat(),
    "previous_outputs": []
}
```

## Failure Alert Format

When max iterations reached:

```markdown
---
type: system_alert
service: ralph_wiggum
error: Max iterations reached
timestamp: 2026-01-07T12:00:00Z
action_required: true
task_id: TASK_abc123
---

## Alert

Task TASK_abc123 failed to complete after 10 iterations.

**Original Task**: EMAIL_xyz.md
**Started**: 2026-01-07T10:00:00Z
**Duration**: 2 hours

## What Happened

Claude Code was unable to complete this task within the maximum iteration limit. The task has been moved to `/Needs_Action/FAILED_EMAIL_xyz.md` for manual review.

## Previous Attempts

1. Iteration 1: Analyzed email, need approval for response
2. Iteration 2: Waiting for approval...
3. Iteration 3: Still waiting...
...
10. Iteration 10: Timeout

## What to Do

1. Review the failed task file: `/Needs_Action/FAILED_EMAIL_xyz.md`
2. Check if there's a blocker (missing approval, external dependency)
3. Either:
   - Manually complete the task
   - Fix the blocker and move back to `/Needs_Action/`
   - Archive if no longer needed
```

## Testing

Unit tests verify:
- Exit blocked when task not in `/Done/`
- Exit allowed when task in `/Done/`
- Iteration count increments correctly
- Max iterations triggers failure alert
- State file persists across iterations
- Previous outputs accumulate

## Safety Features

1. **Iteration Limit**: Prevents infinite loops
2. **State Persistence**: Survives crashes/restarts
3. **Failure Logging**: All failures logged to SQLite + JSON
4. **Manual Override**: Can force exit via state file deletion
5. **Timeout Protection**: Each iteration has timeout

## Example Flow

```
Orchestrator: Claims EMAIL_001.md, creates state file, triggers Claude
Claude: Processes email, creates approval file, exits
Ralph Hook: Checks /Done/ → not found → blocks exit
Ralph Hook: Re-injects prompt: "Continue from: created approval file"
Claude: Waits for approval, exits
Ralph Hook: Checks /Done/ → not found → blocks exit (iteration 2)
...
Human: Approves via CLI
Claude: Sends email, moves to /Done/, exits
Ralph Hook: Checks /Done/ → found → allows exit ✓
```

## Notes

- Named after Ralph Wiggum because "I'm helping!" even when things go wrong
- The stop hook is the safety net that ensures no task is abandoned mid-flight
- Critical for unattended operation - prevents partial completions
- Works with all task types (email, LinkedIn, WhatsApp, file, etc.)
