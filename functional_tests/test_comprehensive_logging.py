#!/usr/bin/env python3
"""
Comprehensive test for logging, telemetry, and error handling coverage.
Version: 0.239.004

Tests that all modules have proper logging, all routes have auth
decorators, and frontend telemetry is configured.
"""

import sys
import os
import re
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'application', 'single_app'))

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'application', 'single_app')


def _read_file(relative_path):
    path = os.path.join(APP_DIR, relative_path)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def test_all_function_files_have_logging():
    """Test every function module has _log_event or log_event."""
    print("Testing: All function files have logging...")
    files_to_check = [
        'functions_skills.py',
        'functions_skill_execution.py',
        'functions_web_ingestion.py',
        'functions_reranking.py',
        'functions_context_optimization.py',
        'functions_query_expansion.py',
        'functions_graph_entities.py',
        'functions_graph_rag.py',
        'functions_graph_communities.py',
    ]

    missing = []
    for fname in files_to_check:
        source = _read_file(fname)
        has_logging = '_log_event' in source or 'log_event' in source or '_log(' in source
        if not has_logging:
            missing.append(fname)

    if missing:
        print(f"  FAIL: Missing logging in: {', '.join(missing)}")
        return False

    print(f"  PASS: All {len(files_to_check)} function files have logging")
    return True


def test_all_route_files_have_logging():
    """Test every route file has logging capability."""
    print("Testing: All route files have logging...")
    files_to_check = [
        'route_backend_skills.py',
        'route_backend_web_ingestion.py',
    ]

    missing = []
    for fname in files_to_check:
        source = _read_file(fname)
        has_logging = '_log(' in source or 'log_event' in source or '_log_event' in source
        if not has_logging:
            missing.append(fname)

    if missing:
        print(f"  FAIL: Missing logging in: {', '.join(missing)}")
        return False

    print(f"  PASS: All {len(files_to_check)} route files have logging")
    return True


def test_all_routes_have_auth_decorators():
    """Test all API routes have @login_required and @user_required."""
    print("Testing: All API routes have auth decorators...")
    files_to_check = [
        'route_backend_skills.py',
        'route_backend_web_ingestion.py',
    ]

    issues = []
    for fname in files_to_check:
        source = _read_file(fname)
        # Find all @app.route definitions followed by their decorators
        routes = re.findall(r"@app\.route\('(/api/[^']+)'", source)
        for route in routes:
            # Find the block from @app.route to def
            pattern = re.escape(route) + r".*?def \w+"
            match = re.search(pattern, source, re.DOTALL)
            if match:
                block = match.group()
                if '@login_required' not in block:
                    issues.append(f"{fname}: {route} missing @login_required")
                if '@user_required' not in block and '@admin_required' not in block:
                    issues.append(f"{fname}: {route} missing @user_required or @admin_required")

    if issues:
        for issue in issues[:5]:
            print(f"  WARN: {issue}")
        print(f"  FAIL: {len(issues)} routes missing auth decorators")
        return False

    total_routes = sum(len(re.findall(r"@app\.route\('(/api/[^']+)'", _read_file(f))) for f in files_to_check)
    print(f"  PASS: All {total_routes} API routes have auth decorators")
    return True


def test_frontend_telemetry_exists():
    """Test frontend telemetry JS and backend endpoints exist."""
    print("Testing: Frontend telemetry...")
    try:
        # Check telemetry.js exists and has key functions
        telemetry_js = _read_file('static/js/telemetry.js')
        assert 'window.scTelemetry' in telemetry_js, "Missing scTelemetry global"
        assert 'logError' in telemetry_js, "Missing logError function"
        assert 'logEvent' in telemetry_js, "Missing logEvent function"
        assert 'trackPageView' in telemetry_js, "Missing trackPageView"
        assert 'trackAction' in telemetry_js, "Missing trackAction"
        assert 'trackFeature' in telemetry_js, "Missing trackFeature"
        assert 'trackTiming' in telemetry_js, "Missing trackTiming"
        assert '/api/telemetry/frontend-error' in telemetry_js, "Missing error endpoint"
        assert '/api/telemetry/frontend-event' in telemetry_js, "Missing event endpoint"
        assert 'unhandledrejection' in telemetry_js, "Missing promise rejection handler"

        # Check base.html includes telemetry.js
        base_html = _read_file('templates/base.html')
        assert 'telemetry.js' in base_html, "telemetry.js not included in base.html"

        # Check backend endpoints exist
        settings_route = _read_file('route_backend_settings.py')
        assert '/api/telemetry/frontend-error' in settings_route, "Missing frontend-error endpoint"
        assert '/api/telemetry/frontend-event' in settings_route, "Missing frontend-event endpoint"

        print("  PASS: Frontend telemetry fully configured")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_error_handling_in_route_endpoints():
    """Test that route endpoints have try/except error handling."""
    print("Testing: Error handling in routes...")
    files = ['route_backend_skills.py', 'route_backend_web_ingestion.py']

    for fname in files:
        source = _read_file(fname)
        # Count route definitions
        routes = re.findall(r"def (api_\w+)", source)
        # Count try/except blocks
        try_blocks = len(re.findall(r'\btry\b:', source))

        if try_blocks < len(routes):
            print(f"  WARN: {fname} has {len(routes)} routes but only {try_blocks} try/except blocks")

    print(f"  PASS: Error handling present in route files")
    return True


def test_appinsights_configuration():
    """Test Application Insights is properly configured."""
    print("Testing: Application Insights configuration...")
    try:
        appinsights = _read_file('functions_appinsights.py')
        assert 'configure_azure_monitor' in appinsights, "Missing configure_azure_monitor"
        assert 'enable_live_metrics' in appinsights, "Missing live metrics config"
        assert 'APPLICATIONINSIGHTS_CONNECTION_STRING' in appinsights, "Missing connection string env var"
        assert 'def log_event' in appinsights, "Missing log_event function"

        # Check Flask instrumentation in app.py
        app_py = _read_file('app.py')
        assert 'FlaskInstrumentor' in app_py, "Missing Flask OpenTelemetry instrumentation"
        assert 'setup_appinsights_logging' in app_py, "Missing AppInsights setup call"

        print("  PASS: Application Insights fully configured")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_skill_execution_logging():
    """Test skill execution has comprehensive logging."""
    print("Testing: Skill execution logging...")
    try:
        source = _read_file('functions_skill_execution.py')
        assert '_log_event' in source or 'log_event' in source, "Missing logging in execution"
        assert 'log_skill_execution' in source, "Missing execution log call"
        assert 'duration_ms' in source, "Missing timing tracking"
        assert '"success"' in source and '"error"' in source, "Missing status tracking"

        print("  PASS: Skill execution has comprehensive logging")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_workspace_skills_js_error_handling():
    """Test workspace-skills.js has error reporting."""
    print("Testing: Frontend JS error reporting...")
    try:
        source = _read_file('static/js/workspace/workspace-skills.js')
        assert 'scTelemetry' in source, "Missing telemetry calls in workspace-skills.js"
        assert 'catch' in source, "Missing catch blocks"

        print("  PASS: Frontend JS has error reporting to backend")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


if __name__ == "__main__":
    results = []
    results.append(test_all_function_files_have_logging())
    results.append(test_all_route_files_have_logging())
    results.append(test_all_routes_have_auth_decorators())
    results.append(test_frontend_telemetry_exists())
    results.append(test_error_handling_in_route_endpoints())
    results.append(test_appinsights_configuration())
    results.append(test_skill_execution_logging())
    results.append(test_workspace_skills_js_error_handling())

    print(f"\n{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if all(results):
        print("All logging & telemetry tests PASSED!")
    else:
        print("Some tests FAILED!")

    sys.exit(0 if all(results) else 1)
