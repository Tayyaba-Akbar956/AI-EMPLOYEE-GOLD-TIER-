"""Plan Generator for AI Employee Silver Tier.

Generates AI-powered execution plans for complex tasks.
Supports simple checklists and detailed phase-based plans.
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class PlanGenerator:
    """Generates and manages execution plans for tasks.

    Handles trigger detection, plan type selection, plan generation,
    progress tracking, and state management.
    """

    def __init__(self, vault_path: str, config: Optional[Dict] = None):
        """Initialize plan generator.

        Args:
            vault_path: Path to AI_Employee_Vault
            config: Optional configuration overrides
        """
        self.vault_path = Path(vault_path)

        # Default configuration
        self.config = {
            'trigger_keywords': [
                'plan', 'organize', 'prepare', 'research', 'coordinate'
            ],
            'high_value_threshold': 500,  # $500
            'multi_step_threshold': 3,  # 3+ steps
            'simple_plan_max_hours': 2,
            'simple_plan_steps': (5, 10),  # min, max steps
            'detailed_plan_min_hours': 2
        }

        if config:
            self.config.update(config)

        # Ensure folders exist
        self._ensure_folders()

    def _ensure_folders(self):
        """Ensure required folders exist."""
        folders = [
            'Plans/active',
            'Plans/pending_approval',
            'Plans/completed'
        ]

        for folder in folders:
            folder_path = self.vault_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)

    def should_generate_plan(self, content: str) -> bool:
        """Detect if content should trigger plan generation.

        Args:
            content: Text content to analyze

        Returns:
            True if plan should be generated, False otherwise
        """
        content_lower = content.lower()

        # Check for trigger keywords
        for keyword in self.config['trigger_keywords']:
            if keyword in content_lower:
                return True

        return False

    def is_multi_step_task(self, task_data: Dict[str, Any]) -> bool:
        """Detect if task is multi-step and requires planning.

        Args:
            task_data: Task information dictionary

        Returns:
            True if multi-step task, False otherwise
        """
        # Check estimated cost
        estimated_cost = task_data.get('estimated_cost', 0)
        if estimated_cost > self.config['high_value_threshold']:
            return True

        # Check number of steps
        steps = task_data.get('steps', [])
        if len(steps) > self.config['multi_step_threshold']:
            return True

        return False

    def determine_plan_type(self, task_data: Dict[str, Any]) -> str:
        """Determine plan type based on task complexity.

        Args:
            task_data: Task information dictionary

        Returns:
            'simple' or 'detailed'
        """
        estimated_hours = task_data.get('estimated_hours', 0)
        estimated_cost = task_data.get('estimated_cost', 0)

        # Detailed plan for complex/expensive tasks
        if estimated_hours > self.config['simple_plan_max_hours']:
            return 'detailed'

        if estimated_cost > self.config['high_value_threshold']:
            return 'detailed'

        # Simple plan for quick tasks
        return 'simple'

    def generate_simple_plan(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate simple checklist plan.

        Args:
            task_data: Task information dictionary

        Returns:
            Simple plan dictionary
        """
        description = task_data.get('description', 'Task')
        estimated_hours = task_data.get('estimated_hours', 1)

        # Generate steps based on task description
        steps = self._generate_simple_steps(description)

        plan = {
            'title': description,
            'type': 'simple',
            'status': 'active',
            'description': description,
            'estimated_hours': estimated_hours,
            'steps': steps,
            'created_at': datetime.now().isoformat(),
            'progress': 0
        }

        return plan

    def _generate_simple_steps(self, description: str) -> List[Dict[str, Any]]:
        """Generate simple steps for a task.

        Args:
            description: Task description

        Returns:
            List of step dictionaries
        """
        # Generic steps that apply to most tasks
        steps = [
            {'description': 'Define objectives and requirements', 'completed': False},
            {'description': 'Gather necessary resources and information', 'completed': False},
            {'description': 'Create initial draft or prototype', 'completed': False},
            {'description': 'Review and refine approach', 'completed': False},
            {'description': 'Execute main task', 'completed': False},
            {'description': 'Test and validate results', 'completed': False},
            {'description': 'Document outcomes', 'completed': False},
            {'description': 'Share with stakeholders', 'completed': False}
        ]

        # Return 5-10 steps
        min_steps, max_steps = self.config['simple_plan_steps']
        return steps[:max_steps]

    def generate_detailed_plan(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed phase-based plan.

        Args:
            task_data: Task information dictionary

        Returns:
            Detailed plan dictionary
        """
        description = task_data.get('description', 'Task')
        estimated_hours = task_data.get('estimated_hours', 10)
        estimated_cost = task_data.get('estimated_cost', 0)

        # Generate phases
        phases = self._generate_phases(description, estimated_hours)

        # Calculate timeline
        start_date = datetime.now()
        estimated_completion = start_date + timedelta(hours=estimated_hours)

        # Determine approval points
        approval_points = self._generate_approval_points(phases, estimated_cost)

        plan = {
            'title': description,
            'type': 'detailed',
            'status': 'pending_approval' if estimated_cost > 1000 else 'active',
            'description': description,
            'phases': phases,
            'timeline': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'estimated_completion': estimated_completion.strftime('%Y-%m-%d')
            },
            'budget': {
                'estimated_cost': estimated_cost
            },
            'approval_points': approval_points,
            'created_at': datetime.now().isoformat(),
            'progress': 0
        }

        return plan

    def _generate_phases(self, description: str, estimated_hours: float) -> List[Dict[str, Any]]:
        """Generate phases for detailed plan.

        Args:
            description: Task description
            estimated_hours: Estimated hours for task

        Returns:
            List of phase dictionaries
        """
        # Standard phases for most projects
        phases = [
            {
                'name': 'Planning & Research',
                'steps': [
                    {'description': 'Define project scope and objectives', 'completed': False},
                    {'description': 'Research requirements and constraints', 'completed': False},
                    {'description': 'Identify stakeholders and resources', 'completed': False}
                ],
                'estimated_hours': estimated_hours * 0.2
            },
            {
                'name': 'Design & Preparation',
                'steps': [
                    {'description': 'Create detailed design or plan', 'completed': False},
                    {'description': 'Gather necessary tools and materials', 'completed': False},
                    {'description': 'Set up environment or workspace', 'completed': False}
                ],
                'estimated_hours': estimated_hours * 0.2
            },
            {
                'name': 'Implementation',
                'steps': [
                    {'description': 'Execute core tasks', 'completed': False},
                    {'description': 'Monitor progress and adjust as needed', 'completed': False},
                    {'description': 'Address issues and blockers', 'completed': False}
                ],
                'estimated_hours': estimated_hours * 0.4
            },
            {
                'name': 'Review & Completion',
                'steps': [
                    {'description': 'Test and validate results', 'completed': False},
                    {'description': 'Document outcomes and learnings', 'completed': False},
                    {'description': 'Present to stakeholders', 'completed': False}
                ],
                'estimated_hours': estimated_hours * 0.2
            }
        ]

        return phases

    def _generate_approval_points(self, phases: List[Dict[str, Any]], estimated_cost: float) -> List[str]:
        """Generate approval points for detailed plan.

        Args:
            phases: List of phases
            estimated_cost: Estimated cost

        Returns:
            List of approval point descriptions
        """
        approval_points = []

        # Always require approval before starting
        approval_points.append('Before starting: Review and approve plan')

        # Approval after planning phase
        if len(phases) > 0:
            approval_points.append('After Planning & Research: Approve scope and approach')

        # Approval for high-cost projects before implementation
        if estimated_cost > 5000:
            approval_points.append('Before Implementation: Approve budget and resources')

        # Final approval before completion
        approval_points.append('Before completion: Review and approve deliverables')

        return approval_points

    def save_plan(self, plan: Dict[str, Any]) -> str:
        """Save plan to vault.

        Args:
            plan: Plan dictionary

        Returns:
            Path to saved file
        """
        # Determine folder based on status
        status = plan.get('status', 'active')
        folder_map = {
            'active': 'Plans/active',
            'pending_approval': 'Plans/pending_approval',
            'completed': 'Plans/completed'
        }
        folder = folder_map.get(status, 'Plans/active')

        # Generate filename
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        title = plan.get('title', 'Plan')
        # Clean title for filename
        clean_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
        clean_title = clean_title[:50]  # Limit length
        filename = f"{timestamp}_plan_{clean_title}.md"

        # Generate markdown
        markdown = self.generate_plan_markdown(plan)

        # Save file
        filepath = self.vault_path / folder / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)

        logger.info(f"Saved plan to {filepath}")

        return str(filepath)

    def generate_plan_markdown(self, plan: Dict[str, Any]) -> str:
        """Generate markdown for plan.

        Args:
            plan: Plan dictionary

        Returns:
            Markdown string
        """
        plan_type = plan.get('type', 'simple')
        title = plan.get('title', 'Plan')
        description = plan.get('description', '')
        status = plan.get('status', 'active')

        # Header
        markdown = f"# {title}\n\n"
        markdown += f"**Type:** {plan_type.title()}\n"
        markdown += f"**Status:** {status.replace('_', ' ').title()}\n"
        markdown += f"**Created:** {plan.get('created_at', datetime.now().isoformat())}\n\n"

        if description:
            markdown += f"## Description\n\n{description}\n\n"

        # Simple plan
        if plan_type == 'simple':
            markdown += "## Steps\n\n"
            steps = plan.get('steps', [])
            for i, step in enumerate(steps, 1):
                checkbox = '[x]' if step.get('completed', False) else '[ ]'
                markdown += f"{i}. {checkbox} {step['description']}\n"

            estimated_hours = plan.get('estimated_hours', 0)
            if estimated_hours:
                markdown += f"\n**Estimated Time:** {estimated_hours} hours\n"

        # Detailed plan
        elif plan_type == 'detailed':
            # Timeline
            timeline = plan.get('timeline', {})
            if timeline:
                markdown += "## Timeline\n\n"
                markdown += f"**Start Date:** {timeline.get('start_date', 'TBD')}\n"
                markdown += f"**Estimated Completion:** {timeline.get('estimated_completion', 'TBD')}\n\n"

            # Budget
            budget = plan.get('budget', {})
            if budget and budget.get('estimated_cost', 0) > 0:
                markdown += "## Budget\n\n"
                markdown += f"**Estimated Cost:** ${budget['estimated_cost']:,.2f}\n\n"

            # Phases
            phases = plan.get('phases', [])
            if phases:
                markdown += "## Phases\n\n"
                for phase in phases:
                    markdown += f"### {phase['name']}\n\n"
                    markdown += f"**Estimated Time:** {phase.get('estimated_hours', 0):.1f} hours\n\n"
                    markdown += "**Steps:**\n\n"
                    for step in phase.get('steps', []):
                        checkbox = '[x]' if step.get('completed', False) else '[ ]'
                        markdown += f"- {checkbox} {step['description']}\n"
                    markdown += "\n"

            # Approval points
            approval_points = plan.get('approval_points', [])
            if approval_points:
                markdown += "## Approval Points\n\n"
                for point in approval_points:
                    markdown += f"- [ ] {point}\n"
                markdown += "\n"

        # Progress
        progress = plan.get('progress', 0)
        markdown += f"\n---\n\n**Progress:** {progress}%\n"

        return markdown

    def calculate_progress(self, plan: Dict[str, Any]) -> int:
        """Calculate plan progress percentage.

        Args:
            plan: Plan dictionary

        Returns:
            Progress percentage (0-100)
        """
        plan_type = plan.get('type', 'simple')

        if plan_type == 'simple':
            steps = plan.get('steps', [])
            if not steps:
                return 0

            completed = sum(1 for step in steps if step.get('completed', False))
            return int((completed / len(steps)) * 100)

        elif plan_type == 'detailed':
            phases = plan.get('phases', [])
            if not phases:
                return 0

            total_steps = 0
            completed_steps = 0

            for phase in phases:
                steps = phase.get('steps', [])
                total_steps += len(steps)
                completed_steps += sum(1 for step in steps if step.get('completed', False))

            if total_steps == 0:
                return 0

            return int((completed_steps / total_steps) * 100)

        return 0

    def update_step_status(self, plan: Dict[str, Any], step_index: int, completed: bool) -> Dict[str, Any]:
        """Update step completion status.

        Args:
            plan: Plan dictionary
            step_index: Index of step to update
            completed: New completion status

        Returns:
            Updated plan dictionary
        """
        plan_type = plan.get('type', 'simple')

        if plan_type == 'simple':
            steps = plan.get('steps', [])
            if 0 <= step_index < len(steps):
                steps[step_index]['completed'] = completed

        # Recalculate progress
        plan['progress'] = self.calculate_progress(plan)

        return plan

    def move_plan_to_completed(self, filepath: str) -> str:
        """Move plan to completed folder.

        Args:
            filepath: Current plan file path

        Returns:
            New file path
        """
        filepath = Path(filepath)
        filename = filepath.name

        # New path in completed folder
        new_path = self.vault_path / 'Plans' / 'completed' / filename

        # Move file
        if filepath.exists():
            filepath.rename(new_path)
            logger.info(f"Moved plan to completed: {new_path}")

        return str(new_path)

    def approve_plan(self, filepath: str) -> str:
        """Approve pending plan and move to active.

        Args:
            filepath: Current plan file path

        Returns:
            New file path
        """
        filepath = Path(filepath)
        filename = filepath.name

        # New path in active folder
        new_path = self.vault_path / 'Plans' / 'active' / filename

        # Move file
        if filepath.exists():
            filepath.rename(new_path)
            logger.info(f"Approved plan: {new_path}")

        return str(new_path)
