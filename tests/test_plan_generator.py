"""Tests for Plan Generator - Phase 5 Silver Tier."""

import pytest
import os
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path

from src.skills.plan_generator import PlanGenerator


class TestTriggerDetection:
    """Test plan trigger detection."""

    @pytest.fixture
    def generator(self):
        """Create plan generator."""
        vault_dir = tempfile.mkdtemp()
        generator = PlanGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_detect_plan_keyword(self, generator):
        """Test detection with 'plan' keyword."""
        content = "I need to plan the product launch for next month"
        should_trigger = generator.should_generate_plan(content)
        assert should_trigger is True

    def test_detect_organize_keyword(self, generator):
        """Test detection with 'organize' keyword."""
        content = "Help me organize the team offsite event"
        should_trigger = generator.should_generate_plan(content)
        assert should_trigger is True

    def test_detect_prepare_keyword(self, generator):
        """Test detection with 'prepare' keyword."""
        content = "I need to prepare for the investor meeting"
        should_trigger = generator.should_generate_plan(content)
        assert should_trigger is True

    def test_detect_research_keyword(self, generator):
        """Test detection with 'research' keyword."""
        content = "Research competitors and market trends"
        should_trigger = generator.should_generate_plan(content)
        assert should_trigger is True

    def test_detect_coordinate_keyword(self, generator):
        """Test detection with 'coordinate' keyword."""
        content = "Coordinate the marketing campaign launch"
        should_trigger = generator.should_generate_plan(content)
        assert should_trigger is True

    def test_no_trigger_casual_message(self, generator):
        """Test no trigger for casual message."""
        content = "Thanks for the update"
        should_trigger = generator.should_generate_plan(content)
        assert should_trigger is False


class TestMultiStepDetection:
    """Test multi-step task detection."""

    @pytest.fixture
    def generator(self):
        """Create plan generator."""
        vault_dir = tempfile.mkdtemp()
        generator = PlanGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_detect_high_value_task(self, generator):
        """Test detection of high-value task (>$500)."""
        task_data = {
            'description': 'Purchase new office equipment',
            'estimated_cost': 1000
        }
        should_trigger = generator.is_multi_step_task(task_data)
        assert should_trigger is True

    def test_detect_multi_step_task(self, generator):
        """Test detection of task with multiple steps."""
        task_data = {
            'description': 'Launch new product',
            'steps': ['Design', 'Develop', 'Test', 'Deploy']
        }
        should_trigger = generator.is_multi_step_task(task_data)
        assert should_trigger is True

    def test_simple_task_no_trigger(self, generator):
        """Test simple task doesn't trigger."""
        task_data = {
            'description': 'Send email to client',
            'estimated_cost': 0
        }
        should_trigger = generator.is_multi_step_task(task_data)
        assert should_trigger is False


class TestPlanTypeSelection:
    """Test plan type selection."""

    @pytest.fixture
    def generator(self):
        """Create plan generator."""
        vault_dir = tempfile.mkdtemp()
        generator = PlanGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_select_simple_plan(self, generator):
        """Test simple plan selection for quick tasks."""
        task_data = {
            'description': 'Organize team meeting',
            'estimated_hours': 1.5
        }
        plan_type = generator.determine_plan_type(task_data)
        assert plan_type == 'simple'

    def test_select_detailed_plan(self, generator):
        """Test detailed plan selection for complex tasks."""
        task_data = {
            'description': 'Launch new product line',
            'estimated_hours': 40,
            'estimated_cost': 5000
        }
        plan_type = generator.determine_plan_type(task_data)
        assert plan_type == 'detailed'


class TestSimplePlanGeneration:
    """Test simple plan generation."""

    @pytest.fixture
    def generator(self):
        """Create plan generator."""
        vault_dir = tempfile.mkdtemp()
        generator = PlanGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_generate_simple_plan(self, generator):
        """Test simple plan generation."""
        task_data = {
            'description': 'Organize team meeting',
            'estimated_hours': 1.5
        }
        plan = generator.generate_simple_plan(task_data)

        assert 'title' in plan
        assert 'type' in plan
        assert plan['type'] == 'simple'
        assert 'steps' in plan
        assert len(plan['steps']) >= 5
        assert len(plan['steps']) <= 10

    def test_simple_plan_has_checkboxes(self, generator):
        """Test simple plan has checkbox format."""
        task_data = {
            'description': 'Prepare presentation',
            'estimated_hours': 2
        }
        plan = generator.generate_simple_plan(task_data)

        # Check that steps are actionable
        for step in plan['steps']:
            assert 'description' in step
            assert 'completed' in step
            assert step['completed'] is False


class TestDetailedPlanGeneration:
    """Test detailed plan generation."""

    @pytest.fixture
    def generator(self):
        """Create plan generator."""
        vault_dir = tempfile.mkdtemp()
        generator = PlanGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_generate_detailed_plan(self, generator):
        """Test detailed plan generation."""
        task_data = {
            'description': 'Launch new product',
            'estimated_hours': 40,
            'estimated_cost': 5000
        }
        plan = generator.generate_detailed_plan(task_data)

        assert 'title' in plan
        assert 'type' in plan
        assert plan['type'] == 'detailed'
        assert 'phases' in plan
        assert len(plan['phases']) > 0

    def test_detailed_plan_has_phases(self, generator):
        """Test detailed plan has phases."""
        task_data = {
            'description': 'Implement new feature',
            'estimated_hours': 30
        }
        plan = generator.generate_detailed_plan(task_data)

        for phase in plan['phases']:
            assert 'name' in phase
            assert 'steps' in phase
            assert 'estimated_hours' in phase

    def test_detailed_plan_has_timeline(self, generator):
        """Test detailed plan has timeline."""
        task_data = {
            'description': 'Marketing campaign',
            'estimated_hours': 50
        }
        plan = generator.generate_detailed_plan(task_data)

        assert 'timeline' in plan
        assert 'start_date' in plan['timeline']
        assert 'estimated_completion' in plan['timeline']

    def test_detailed_plan_has_budget(self, generator):
        """Test detailed plan has budget."""
        task_data = {
            'description': 'Office renovation',
            'estimated_cost': 10000
        }
        plan = generator.generate_detailed_plan(task_data)

        assert 'budget' in plan
        assert 'estimated_cost' in plan['budget']

    def test_detailed_plan_has_approval_points(self, generator):
        """Test detailed plan has approval points."""
        task_data = {
            'description': 'Major system upgrade',
            'estimated_hours': 100,
            'estimated_cost': 20000
        }
        plan = generator.generate_detailed_plan(task_data)

        assert 'approval_points' in plan
        assert len(plan['approval_points']) > 0


class TestPlanStorage:
    """Test plan storage."""

    @pytest.fixture
    def generator(self):
        """Create plan generator."""
        vault_dir = tempfile.mkdtemp()
        generator = PlanGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_save_plan_to_active(self, generator):
        """Test saving plan to active folder."""
        plan = {
            'title': 'Test Plan',
            'type': 'simple',
            'status': 'active',
            'steps': []
        }
        filepath = generator.save_plan(plan)

        assert os.path.exists(filepath)
        assert 'Plans' in filepath
        assert 'active' in filepath

    def test_save_plan_to_pending_approval(self, generator):
        """Test saving plan to pending_approval folder."""
        plan = {
            'title': 'Test Plan',
            'type': 'detailed',
            'status': 'pending_approval',
            'phases': []
        }
        filepath = generator.save_plan(plan)

        assert os.path.exists(filepath)
        assert 'pending_approval' in filepath

    def test_plan_file_format(self, generator):
        """Test plan file is markdown format."""
        plan = {
            'title': 'Test Plan',
            'type': 'simple',
            'status': 'active',
            'steps': []
        }
        filepath = generator.save_plan(plan)

        assert filepath.endswith('.md')


class TestProgressTracking:
    """Test plan progress tracking."""

    @pytest.fixture
    def generator(self):
        """Create plan generator."""
        vault_dir = tempfile.mkdtemp()
        generator = PlanGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_calculate_simple_plan_progress(self, generator):
        """Test progress calculation for simple plan."""
        plan = {
            'type': 'simple',
            'steps': [
                {'description': 'Step 1', 'completed': True},
                {'description': 'Step 2', 'completed': True},
                {'description': 'Step 3', 'completed': False},
                {'description': 'Step 4', 'completed': False}
            ]
        }
        progress = generator.calculate_progress(plan)

        assert progress == 50  # 2 out of 4 completed

    def test_calculate_detailed_plan_progress(self, generator):
        """Test progress calculation for detailed plan."""
        plan = {
            'type': 'detailed',
            'phases': [
                {
                    'name': 'Phase 1',
                    'steps': [
                        {'description': 'Step 1', 'completed': True},
                        {'description': 'Step 2', 'completed': True}
                    ]
                },
                {
                    'name': 'Phase 2',
                    'steps': [
                        {'description': 'Step 3', 'completed': False},
                        {'description': 'Step 4', 'completed': False}
                    ]
                }
            ]
        }
        progress = generator.calculate_progress(plan)

        assert progress == 50  # 2 out of 4 total steps completed

    def test_update_step_status(self, generator):
        """Test updating step completion status."""
        plan = {
            'type': 'simple',
            'steps': [
                {'description': 'Step 1', 'completed': False},
                {'description': 'Step 2', 'completed': False}
            ]
        }
        updated_plan = generator.update_step_status(plan, 0, True)

        assert updated_plan['steps'][0]['completed'] is True
        assert updated_plan['steps'][1]['completed'] is False


class TestPlanStateManagement:
    """Test plan state management."""

    @pytest.fixture
    def generator(self):
        """Create plan generator."""
        vault_dir = tempfile.mkdtemp()
        generator = PlanGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_move_plan_to_completed(self, generator):
        """Test moving plan to completed folder."""
        # Create plan in active
        plan = {
            'title': 'Test Plan',
            'type': 'simple',
            'status': 'active',
            'steps': [
                {'description': 'Step 1', 'completed': True}
            ]
        }
        filepath = generator.save_plan(plan)

        # Move to completed
        new_filepath = generator.move_plan_to_completed(filepath)

        assert os.path.exists(new_filepath)
        assert 'completed' in new_filepath
        assert not os.path.exists(filepath)

    def test_approve_plan(self, generator):
        """Test approving pending plan."""
        # Create plan in pending_approval
        plan = {
            'title': 'Test Plan',
            'type': 'detailed',
            'status': 'pending_approval',
            'phases': []
        }
        filepath = generator.save_plan(plan)

        # Approve plan
        new_filepath = generator.approve_plan(filepath)

        assert os.path.exists(new_filepath)
        assert 'active' in new_filepath
        assert not os.path.exists(filepath)


class TestMarkdownGeneration:
    """Test markdown generation."""

    @pytest.fixture
    def generator(self):
        """Create plan generator."""
        vault_dir = tempfile.mkdtemp()
        generator = PlanGenerator(vault_dir)
        yield generator
        shutil.rmtree(vault_dir)

    def test_generate_simple_plan_markdown(self, generator):
        """Test markdown generation for simple plan."""
        plan = {
            'title': 'Team Meeting',
            'type': 'simple',
            'status': 'active',
            'description': 'Organize quarterly team meeting',
            'estimated_hours': 2,
            'steps': [
                {'description': 'Book conference room', 'completed': False},
                {'description': 'Send invites', 'completed': False}
            ]
        }
        markdown = generator.generate_plan_markdown(plan)

        assert '# Team Meeting' in markdown
        assert 'Type: Simple' in markdown or 'simple' in markdown.lower()
        assert '[ ]' in markdown  # Unchecked checkbox (numbered or bullet)

    def test_generate_detailed_plan_markdown(self, generator):
        """Test markdown generation for detailed plan."""
        plan = {
            'title': 'Product Launch',
            'type': 'detailed',
            'status': 'active',
            'description': 'Launch new product line',
            'phases': [
                {
                    'name': 'Planning',
                    'steps': [
                        {'description': 'Market research', 'completed': False}
                    ],
                    'estimated_hours': 10
                }
            ],
            'timeline': {
                'start_date': '2026-02-18',
                'estimated_completion': '2026-03-18'
            },
            'budget': {
                'estimated_cost': 5000
            }
        }
        markdown = generator.generate_plan_markdown(plan)

        assert '# Product Launch' in markdown
        assert 'Planning' in markdown
        assert 'Timeline' in markdown or 'timeline' in markdown.lower()
        assert 'Budget' in markdown or 'budget' in markdown.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
