# Plan Generator Skill

**Version:** 1.0.0
**Type:** Skill
**Category:** Planning & Organization

---

## Overview

The Plan Generator skill creates AI-powered execution plans for complex tasks. It automatically detects when planning is needed, selects the appropriate plan type, and generates structured plans with progress tracking.

## When to Use

Use this skill when:
- User mentions keywords: **plan**, **organize**, **prepare**, **research**, **coordinate**
- Task has high value (>$500)
- Task has multiple steps (>3 steps)
- Task requires structured approach
- User explicitly requests a plan

## Capabilities

### 1. Trigger Detection
- Keyword-based detection (plan, organize, prepare, research, coordinate)
- Multi-step task detection (>$500 or >3 steps)
- Automatic plan type selection

### 2. Plan Types

#### Simple Plan
- **Use Case:** Quick tasks, <2 hours
- **Structure:** 5-10 step checklist
- **Features:** Checkbox tracking, estimated time, progress percentage

#### Detailed Plan
- **Use Case:** Complex tasks, >2 hours, high-value (>$500)
- **Structure:** Phase-based with timeline, budget, approval points
- **Features:** Multiple phases, step-by-step breakdown, approval workflow

### 3. Plan Storage
- **Active Plans:** Plans/active/ - Currently executing
- **Pending Approval:** Plans/pending_approval/ - Awaiting user approval
- **Completed Plans:** Plans/completed/ - Finished plans

### 4. Progress Tracking
- Automatic progress calculation (percentage)
- Step completion tracking
- Phase completion tracking (detailed plans)

### 5. State Management
- Move plans between folders
- Approve pending plans
- Mark plans as completed

---

**Status:** Production Ready
**Last Updated:** 2026-02-18
