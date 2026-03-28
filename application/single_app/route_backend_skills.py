# route_backend_skills.py

import logging
from flask import request, jsonify, session

from swagger_wrapper import swagger_route, get_auth_security
from functions_settings import get_settings

logger = logging.getLogger(__name__)


def register_route_backend_skills(app):

    @app.route('/skills/marketplace', methods=['GET'])
    def skills_marketplace_page():
        """Render the skills marketplace page."""
        from flask import render_template
        settings = get_settings()
        if not settings.get("enable_skills_builder", False):
            from flask import redirect
            return redirect("/")
        from functions_settings import sanitize_settings_for_user
        public_settings = sanitize_settings_for_user(settings)
        return render_template('skills_marketplace.html', settings=public_settings)

    def _get_user():
        """Get current user from session."""
        user = session.get("user", {})
        user_id = user.get("oid")
        user_name = user.get("name", "Unknown")
        return user_id, user_name

    # ------------------------------------------------------------------
    # Skill CRUD
    # ------------------------------------------------------------------

    @app.route('/api/skills', methods=['POST'])
    @swagger_route(security=get_auth_security())
    def api_create_skill():
        """Create a new skill."""
        user_id, user_name = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        settings = get_settings()
        if not settings.get("enable_skills_builder", False):
            return jsonify({"error": "Skills Builder is disabled"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        # Set workspace_id based on scope
        scope = data.get("scope", "personal")
        if scope == "personal":
            data["workspace_id"] = user_id
        elif scope == "group":
            data["workspace_id"] = data.get("group_id", user_id)
            if not settings.get("allow_group_skills", True):
                return jsonify({"error": "Group skills are disabled"}), 400
        elif scope == "global":
            data["workspace_id"] = "global"

        try:
            from functions_skills import create_skill
            skill = create_skill(user_id, user_name, data)
            return jsonify(skill), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"Failed to create skill: {e}")
            return jsonify({"error": "Failed to create skill"}), 500

    @app.route('/api/skills', methods=['GET'])
    @swagger_route(security=get_auth_security())
    def api_list_skills():
        """List skills for the current user's workspaces."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        scope = request.args.get("scope")
        group_id = request.args.get("group_id")
        workspace_id = group_id if group_id else user_id

        try:
            from functions_skills import list_skills
            skills = list_skills(workspace_id, scope=scope)

            # Also include installed global skills
            from functions_skills import list_marketplace_skills
            installed_global = [s for s in list_marketplace_skills()
                               if user_id in s.get("installed_by", [])]

            return jsonify({"skills": skills, "installed_global": installed_global}), 200
        except Exception as e:
            logger.error(f"Failed to list skills: {e}")
            return jsonify({"error": "Failed to list skills"}), 500

    @app.route('/api/skills/<skill_id>', methods=['GET'])
    @swagger_route(security=get_auth_security())
    def api_get_skill(skill_id):
        """Get skill details."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        workspace_id = request.args.get("workspace_id", user_id)

        from functions_skills import get_skill
        skill = get_skill(skill_id, workspace_id)
        if not skill:
            # Try global
            skill = get_skill(skill_id, "global")
        if not skill:
            return jsonify({"error": "Skill not found"}), 404

        return jsonify(skill), 200

    @app.route('/api/skills/<skill_id>', methods=['PUT'])
    @swagger_route(security=get_auth_security())
    def api_update_skill(skill_id):
        """Update a skill."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        data = request.get_json()
        workspace_id = data.pop("workspace_id", user_id) if data else user_id

        try:
            from functions_skills import update_skill, get_skill
            skill = get_skill(skill_id, workspace_id)
            if not skill:
                return jsonify({"error": "Skill not found"}), 404
            if skill.get("author_id") != user_id:
                return jsonify({"error": "Not authorized to edit this skill"}), 403

            updated = update_skill(skill_id, workspace_id, data)
            return jsonify(updated), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"Failed to update skill: {e}")
            return jsonify({"error": "Failed to update skill"}), 500

    @app.route('/api/skills/<skill_id>', methods=['DELETE'])
    @swagger_route(security=get_auth_security())
    def api_delete_skill(skill_id):
        """Delete a skill."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        workspace_id = request.args.get("workspace_id", user_id)

        from functions_skills import get_skill, delete_skill
        skill = get_skill(skill_id, workspace_id)
        if not skill:
            return jsonify({"error": "Skill not found"}), 404
        if skill.get("author_id") != user_id:
            return jsonify({"error": "Not authorized"}), 403

        delete_skill(skill_id, workspace_id)
        return jsonify({"message": "Skill deleted"}), 200

    # ------------------------------------------------------------------
    # Skill Execution
    # ------------------------------------------------------------------

    @app.route('/api/skills/<skill_id>/execute', methods=['POST'])
    @swagger_route(security=get_auth_security())
    def api_execute_skill(skill_id):
        """Execute a skill with given input."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        settings = get_settings()
        if not settings.get("enable_skills_builder", False):
            return jsonify({"error": "Skills Builder is disabled"}), 400

        data = request.get_json() or {}
        user_input = data.get("input", "")
        workspace_id = data.get("workspace_id", user_id)

        from functions_skills import get_skill
        skill = get_skill(skill_id, workspace_id)
        if not skill:
            skill = get_skill(skill_id, "global")
        if not skill:
            return jsonify({"error": "Skill not found"}), 404

        try:
            from functions_skill_execution import execute_skill
            result = execute_skill(skill, user_input, user_id, settings)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Skill execution failed: {e}")
            return jsonify({"error": f"Execution failed: {str(e)}"}), 500

    @app.route('/api/skills/<skill_id>/executions', methods=['GET'])
    @swagger_route(security=get_auth_security())
    def api_skill_executions(skill_id):
        """Get execution history for a skill."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        from functions_skills import get_skill_executions
        executions = get_skill_executions(skill_id, user_id)
        return jsonify({"executions": executions}), 200

    # ------------------------------------------------------------------
    # Marketplace
    # ------------------------------------------------------------------

    @app.route('/api/skills/marketplace', methods=['GET'])
    @swagger_route(security=get_auth_security())
    def api_skills_marketplace():
        """Browse the skills marketplace."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        category = request.args.get("category")
        search = request.args.get("search")
        sort_by = request.args.get("sort", "usage_count")

        from functions_skills import list_marketplace_skills
        skills = list_marketplace_skills(category=category, search=search, sort_by=sort_by)

        # Add rating display
        for s in skills:
            count = s.get("rating_count", 0)
            s["rating_avg"] = round(s.get("rating_sum", 0) / count, 1) if count > 0 else 0

        return jsonify({"skills": skills}), 200

    @app.route('/api/skills/<skill_id>/publish', methods=['POST'])
    @swagger_route(security=get_auth_security())
    def api_publish_skill(skill_id):
        """Publish a skill to the marketplace."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        settings = get_settings()
        workspace_id = request.get_json().get("workspace_id", user_id) if request.get_json() else user_id
        require_approval = settings.get("skills_require_approval", True)

        try:
            from functions_skills import publish_skill, get_skill
            skill = get_skill(skill_id, workspace_id)
            if not skill:
                return jsonify({"error": "Skill not found"}), 404
            if skill.get("author_id") != user_id:
                return jsonify({"error": "Not authorized"}), 403

            updated = publish_skill(skill_id, workspace_id, require_approval)
            status_msg = "Submitted for approval" if require_approval else "Published to marketplace"
            return jsonify({"message": status_msg, "skill": updated}), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/api/skills/<skill_id>/install', methods=['POST'])
    @swagger_route(security=get_auth_security())
    def api_install_skill(skill_id):
        """Install a marketplace skill."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        try:
            from functions_skills import install_skill
            install_skill(skill_id, user_id)
            return jsonify({"message": "Skill installed"}), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/api/skills/<skill_id>/rate', methods=['POST'])
    @swagger_route(security=get_auth_security())
    def api_rate_skill(skill_id):
        """Rate a skill."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        data = request.get_json() or {}
        rating = data.get("rating", 0)

        try:
            from functions_skills import rate_skill
            skill = rate_skill(skill_id, user_id, rating)
            return jsonify({"message": "Rating saved", "skill": skill}), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    # ------------------------------------------------------------------
    # Admin: Approval
    # ------------------------------------------------------------------

    @app.route('/api/admin/skills/pending', methods=['GET'])
    @swagger_route(security=get_auth_security())
    def api_pending_skills():
        """List skills pending approval (admin only)."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        from functions_skills import list_pending_skills
        return jsonify({"skills": list_pending_skills()}), 200

    @app.route('/api/admin/skills/<skill_id>/approve', methods=['POST'])
    @swagger_route(security=get_auth_security())
    def api_approve_skill(skill_id):
        """Approve a pending skill (admin only)."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        data = request.get_json() or {}
        notes = data.get("notes", "")

        try:
            from functions_skills import approve_skill
            skill = approve_skill(skill_id, user_id, notes)
            return jsonify({"message": "Skill approved", "skill": skill}), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/api/admin/skills/<skill_id>/reject', methods=['POST'])
    @swagger_route(security=get_auth_security())
    def api_reject_skill(skill_id):
        """Reject a pending skill (admin only)."""
        user_id, _ = _get_user()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        data = request.get_json() or {}
        reason = data.get("reason", "")

        try:
            from functions_skills import reject_skill
            skill = reject_skill(skill_id, user_id, reason)
            return jsonify({"message": "Skill rejected", "skill": skill}), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
