# functions_skill_execution.py

import json
import logging
import time

logger = logging.getLogger(__name__)


def _log_event(message, level=logging.INFO, extra=None):
    try:
        from functions_appinsights import log_event
        log_event(message, level=level, extra=extra)
    except ImportError:
        logger.log(level, message, extra=extra)


def execute_skill(skill: dict, user_input: str, user_id: str, settings: dict) -> dict:
    """Execute a skill and return the result.

    Routes to the appropriate execution method based on skill type.

    Returns dict with: output, type, duration_ms, skill_name, status
    """
    skill_type = skill.get("type", "prompt_skill")
    skill_name = skill.get("name", "unknown")
    start_time = time.time()

    try:
        if skill_type == "prompt_skill":
            output = _execute_prompt_skill(skill, user_input, settings)
        elif skill_type == "tool_skill":
            output = _execute_tool_skill(skill, user_input, settings)
        elif skill_type == "chain_skill":
            output = _execute_chain_skill(skill, user_input, user_id, settings)
        else:
            output = _execute_prompt_skill(skill, user_input, settings)

        duration_ms = int((time.time() - start_time) * 1000)

        # Log execution
        from functions_skills import log_skill_execution
        log_skill_execution(
            skill_id=skill["id"],
            skill_name=skill_name,
            user_id=user_id,
            input_text=user_input,
            output_text=output,
            duration_ms=duration_ms,
            status="success",
        )

        # Increment usage count
        _increment_usage(skill)

        _log_event("skill_executed", extra={
            "skill_id": skill["id"], "skill_name": skill_name,
            "type": skill_type, "duration_ms": duration_ms,
        })

        return {
            "output": output,
            "type": skill.get("config", {}).get("output_format", "markdown"),
            "duration_ms": duration_ms,
            "skill_name": skill_name,
            "skill_display_name": skill.get("display_name", skill_name),
            "status": "success",
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        from functions_skills import log_skill_execution
        log_skill_execution(
            skill_id=skill.get("id", ""),
            skill_name=skill_name,
            user_id=user_id,
            input_text=user_input,
            output_text=str(e),
            duration_ms=duration_ms,
            status="error",
        )

        logger.error(f"Skill execution failed for {skill_name}: {e}")
        return {
            "output": f"Skill execution failed: {str(e)}",
            "type": "error",
            "duration_ms": duration_ms,
            "skill_name": skill_name,
            "status": "error",
        }


def _execute_prompt_skill(skill: dict, user_input: str, settings: dict) -> str:
    """Execute a prompt-based skill (direct GPT call)."""
    config = skill.get("config", {})
    system_prompt = config.get("system_prompt", "")
    model = config.get("model", "gpt-4o")
    max_tokens = config.get("max_tokens", 2000)
    temperature = config.get("temperature", 0.3)

    # Render template variables
    rendered_prompt = system_prompt.replace("{{input}}", user_input)

    try:
        from config import gpt_client
        response = gpt_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": rendered_prompt},
                {"role": "user", "content": user_input},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"GPT call failed: {e}")


def _execute_tool_skill(skill: dict, user_input: str, settings: dict) -> str:
    """Execute a tool-based skill (SK with plugins)."""
    config = skill.get("config", {})
    system_prompt = config.get("system_prompt", "")
    tools = config.get("tools", [])

    if not tools:
        # No tools configured — fall back to prompt skill
        return _execute_prompt_skill(skill, user_input, settings)

    # For tool skills, use Semantic Kernel with specified plugins
    try:
        from config import gpt_client
        model = config.get("model", "gpt-4o")

        # Build messages with tool context
        rendered_prompt = system_prompt.replace("{{input}}", user_input)
        messages = [
            {"role": "system", "content": f"{rendered_prompt}\n\nAvailable tools: {', '.join(tools)}"},
            {"role": "user", "content": user_input},
        ]

        response = gpt_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=config.get("max_tokens", 2000),
            temperature=config.get("temperature", 0.3),
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Tool skill execution failed: {e}")


def _execute_chain_skill(skill: dict, user_input: str, user_id: str, settings: dict) -> str:
    """Execute a chain skill (sequence of sub-skills)."""
    config = skill.get("config", {})
    chain_steps = config.get("chain_steps", [])

    if not chain_steps:
        return _execute_prompt_skill(skill, user_input, settings)

    current_output = user_input
    from functions_skills import get_skill

    for step in chain_steps:
        step_skill_id = step.get("skill_id")
        step_workspace = step.get("workspace_id", skill.get("workspace_id"))

        sub_skill = get_skill(step_skill_id, step_workspace)
        if not sub_skill:
            sub_skill = get_skill(step_skill_id, "global")

        if sub_skill:
            result = execute_skill(sub_skill, current_output, user_id, settings)
            current_output = result.get("output", current_output)
        else:
            logger.warning(f"Chain step skill not found: {step_skill_id}")

    return current_output


def _increment_usage(skill: dict):
    """Increment skill usage count."""
    try:
        from config import cosmos_skills_container
        skill["usage_count"] = skill.get("usage_count", 0) + 1
        cosmos_skills_container.upsert_item(skill)
    except Exception as e:
        logger.warning(f"Failed to increment usage count for skill {skill.get('id', 'unknown')}: {e}")


def handle_skill_command(message: str, user_id: str, settings: dict,
                         group_id: str = None) -> dict:
    """Handle a /skill-name command from chat.

    Returns execution result dict or None if not a skill command.
    """
    if not message.startswith('/'):
        return None

    # Parse command and arguments
    parts = message.split(None, 1)
    command = parts[0].lower()
    arguments = parts[1] if len(parts) > 1 else ""

    # Look up skill by command
    from functions_skills import get_skill_by_command
    skill = get_skill_by_command(command, user_id, group_id)

    if not skill:
        return None  # Not a recognized skill command

    return execute_skill(skill, arguments, user_id, settings)


def detect_skill_triggers(message: str, user_id: str, group_id: str = None) -> list:
    """Detect if a message matches any skill's trigger phrases.

    Returns list of matching skills with confidence scores.
    """
    from functions_skills import list_skills

    matches = []
    message_lower = message.lower()

    # Check personal skills
    for skill in list_skills(user_id):
        triggers = skill.get("config", {}).get("trigger_phrases", [])
        for trigger in triggers:
            if trigger.lower() in message_lower:
                matches.append({
                    "skill": skill,
                    "trigger": trigger,
                    "confidence": 0.8,
                })

    # Check group skills
    if group_id:
        for skill in list_skills(group_id):
            triggers = skill.get("config", {}).get("trigger_phrases", [])
            for trigger in triggers:
                if trigger.lower() in message_lower:
                    matches.append({
                        "skill": skill,
                        "trigger": trigger,
                        "confidence": 0.7,
                    })

    return sorted(matches, key=lambda x: -x["confidence"])[:5]
