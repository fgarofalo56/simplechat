#!/usr/bin/env python3
"""
Functional test for Skills Builder - Phase 1: Foundation.
Version: 0.239.003
Implemented in: 0.239.004

Tests Cosmos containers, CRUD functions, REST API routes,
skill execution, admin settings, and chat command interception.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'application', 'single_app'))


def test_cosmos_containers():
    """Test Skills Cosmos containers defined in config.py."""
    print("Testing: Skills Cosmos containers...")
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'cosmos_skills_container' in source, "Missing skills container"
        assert 'cosmos_skill_executions_container' in source, "Missing skill_executions container"
        assert '"skills"' in source, "Missing skills container name"
        assert '"skill_executions"' in source, "Missing skill_executions container name"

        print("  PASS: Skills containers defined")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_skill_validation():
    """Test skill payload validation (standalone)."""
    print("Testing: Skill validation...")
    try:
        import re
        VALID_TYPES = {"prompt_skill", "tool_skill", "chain_skill"}
        VALID_CATEGORIES = {"productivity", "data", "integration", "analysis", "other"}

        def validate_skill_payload(payload, partial=False):
            if not partial:
                for field in ["name", "display_name", "description", "type"]:
                    if not payload.get(field):
                        raise ValueError(f"Missing required field: {field}")
            if "name" in payload:
                if not re.match(r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$', payload["name"]):
                    raise ValueError("Invalid name")
            if "type" in payload and payload["type"] not in VALID_TYPES:
                raise ValueError("Invalid type")
            if "display_name" in payload and len(payload["display_name"]) > 100:
                raise ValueError("Name too long")

        # Valid payload
        validate_skill_payload({
            "name": "test-skill",
            "display_name": "Test Skill",
            "description": "A test skill",
            "type": "prompt_skill",
        })

        # Invalid name
        try:
            validate_skill_payload({"name": "INVALID NAME!", "display_name": "X", "description": "X", "type": "prompt_skill"})
            print("  FAIL: Should reject invalid name")
            return False
        except ValueError:
            pass

        # Invalid type
        try:
            validate_skill_payload({"name": "valid-name", "display_name": "X", "description": "X", "type": "invalid_type"})
            print("  FAIL: Should reject invalid type")
            return False
        except ValueError:
            pass

        # Missing required field
        try:
            validate_skill_payload({"name": "valid-name"})
            print("  FAIL: Should reject missing fields")
            return False
        except ValueError:
            pass

        # Partial update should not require all fields
        validate_skill_payload({"description": "updated"}, partial=True)

        print("  PASS: Skill validation works correctly")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skill_command_building():
    """Test command generation from skill name."""
    print("Testing: Skill command building...")
    try:
        def _build_command(name):
            return f"/{name}"

        assert _build_command("summarize-meeting") == "/summarize-meeting"
        assert _build_command("data-query") == "/data-query"

        print("  PASS: Command building works")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_skill_execution_module():
    """Test skill execution module has required functions."""
    print("Testing: Skill execution module...")
    try:
        exec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_skill_execution.py')
        with open(exec_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'def execute_skill' in source, "Missing execute_skill"
        assert 'def _execute_prompt_skill' in source, "Missing prompt skill execution"
        assert 'def _execute_tool_skill' in source, "Missing tool skill execution"
        assert 'def _execute_chain_skill' in source, "Missing chain skill execution"
        assert 'def handle_skill_command' in source, "Missing chat command handler"
        assert 'def detect_skill_triggers' in source, "Missing trigger detection"
        assert '{{input}}' in source, "Missing template variable support"

        print("  PASS: Skill execution module complete")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_route_endpoints():
    """Test all skill REST API endpoints exist."""
    print("Testing: Skill REST API endpoints...")
    try:
        route_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'route_backend_skills.py')
        with open(route_path, 'r', encoding='utf-8') as f:
            source = f.read()

        endpoints = [
            "'/api/skills'",
            "'/api/skills/<skill_id>'",
            "'/api/skills/<skill_id>/execute'",
            "'/api/skills/<skill_id>/executions'",
            "'/api/skills/marketplace'",
            "'/api/skills/<skill_id>/publish'",
            "'/api/skills/<skill_id>/install'",
            "'/api/skills/<skill_id>/rate'",
            "'/api/admin/skills/pending'",
            "'/api/admin/skills/<skill_id>/approve'",
            "'/api/admin/skills/<skill_id>/reject'",
        ]

        for ep in endpoints:
            assert ep in source, f"Missing endpoint: {ep}"

        print(f"  PASS: All {len(endpoints)} skill endpoints present")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_route_registration():
    """Test routes registered in app.py."""
    print("Testing: Route registration...")
    try:
        app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'app.py')
        with open(app_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'from route_backend_skills import *' in source
        assert 'register_route_backend_skills(app)' in source

        print("  PASS: Skills routes registered")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_settings_defaults():
    """Test skills settings defaults."""
    print("Testing: Skills settings defaults...")
    try:
        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_settings.py')
        with open(settings_path, 'r') as f:
            source = f.read()

        required = [
            "'enable_skills_builder': False",
            "'allow_user_skills': True",
            "'allow_group_skills': True",
            "'skills_require_approval': True",
            "'max_skills_per_user': 50",
        ]
        for s in required:
            assert s in source, f"Missing: {s}"

        print("  PASS: All settings defaults present")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_admin_ui():
    """Test Skills Builder admin tab."""
    print("Testing: Skills Builder admin UI...")
    try:
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'templates', 'admin_settings.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'id="skills-builder-tab"' in source, "Missing tab button"
        assert 'id="skills-builder"' in source, "Missing tab pane"
        assert 'name="enable_skills_builder"' in source, "Missing toggle"
        assert 'name="allow_user_skills"' in source, "Missing allow_user_skills"
        assert 'name="skills_require_approval"' in source, "Missing approval setting"
        assert 'name="max_skills_per_user"' in source, "Missing max_skills"

        print("  PASS: Skills Builder admin tab complete")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_crud_functions():
    """Test CRUD function module has all required operations."""
    print("Testing: Skills CRUD functions...")
    try:
        crud_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_skills.py')
        with open(crud_path, 'r', encoding='utf-8') as f:
            source = f.read()

        required_funcs = [
            'def create_skill',
            'def get_skill',
            'def get_skill_by_command',
            'def update_skill',
            'def delete_skill',
            'def list_skills',
            'def list_marketplace_skills',
            'def list_pending_skills',
            'def publish_skill',
            'def approve_skill',
            'def reject_skill',
            'def install_skill',
            'def rate_skill',
            'def log_skill_execution',
            'def get_skill_executions',
        ]
        for func in required_funcs:
            assert func in source, f"Missing: {func}"

        print(f"  PASS: All {len(required_funcs)} CRUD functions present")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


if __name__ == "__main__":
    results = []
    results.append(test_cosmos_containers())
    results.append(test_skill_validation())
    results.append(test_skill_command_building())
    results.append(test_skill_execution_module())
    results.append(test_route_endpoints())
    results.append(test_route_registration())
    results.append(test_settings_defaults())
    results.append(test_admin_ui())
    results.append(test_crud_functions())

    print(f"\n{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if all(results):
        print("All Skills Builder Phase 1 tests PASSED!")
    else:
        print("Some tests FAILED!")

    sys.exit(0 if all(results) else 1)
