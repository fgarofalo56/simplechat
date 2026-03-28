// workspace-skills.js
// Skills Builder UI for creating, managing, and testing custom AI skills

(function () {
    'use strict';

    let currentStep = 1;
    const totalSteps = 4;
    let editingSkillId = null;

    // DOM Elements
    const skillsCardsRow = document.getElementById('skills-cards-row');
    const skillsLoading = document.getElementById('skills-loading');
    const skillsEmpty = document.getElementById('skills-empty');
    const skillsSearch = document.getElementById('skills-search');

    // Modal Elements
    const prevBtn = document.getElementById('skill-prev-btn');
    const nextBtn = document.getElementById('skill-next-btn');
    const saveBtn = document.getElementById('skill-save-btn');
    const testBtn = document.getElementById('skill-test-btn');
    const tempSlider = document.getElementById('skill-temperature');
    const tempValue = document.getElementById('skill-temp-value');

    if (!skillsCardsRow) return; // Not on workspace page or skills disabled

    // ---------------------------------------------------------------
    // Skills List
    // ---------------------------------------------------------------

    async function loadSkills() {
        if (skillsLoading) skillsLoading.classList.remove('d-none');
        if (skillsEmpty) skillsEmpty.classList.add('d-none');
        if (skillsCardsRow) skillsCardsRow.innerHTML = '';

        try {
            const resp = await fetch('/api/skills');
            if (!resp.ok) throw new Error('Failed to load skills');
            const data = await resp.json();

            const allSkills = [...(data.skills || []), ...(data.installed_global || [])];

            if (skillsLoading) skillsLoading.classList.add('d-none');

            if (allSkills.length === 0) {
                if (skillsEmpty) skillsEmpty.classList.remove('d-none');
                return;
            }

            allSkills.forEach(skill => {
                const card = createSkillCard(skill);
                skillsCardsRow.appendChild(card);
            });
        } catch (err) {
            console.error('Failed to load skills:', err);
            if (window.scTelemetry) window.scTelemetry.logError('Failed to load skills: ' + err.message, 'workspace-skills');
            if (skillsLoading) skillsLoading.innerHTML = '<div class="alert alert-danger">Failed to load skills</div>';
        }
    }

    function createSkillCard(skill) {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 mb-3';

        const categoryBadge = {
            productivity: 'bg-primary',
            data: 'bg-info',
            integration: 'bg-warning',
            analysis: 'bg-success',
            other: 'bg-secondary'
        }[skill.category] || 'bg-secondary';

        const typeBadge = {
            prompt_skill: 'Prompt',
            tool_skill: 'Tool',
            chain_skill: 'Chain'
        }[skill.type] || 'Prompt';

        const command = (skill.commands && skill.commands[0]) || ('/' + skill.name);
        const ratingCount = skill.rating_count || 0;
        const ratingAvg = ratingCount > 0 ? (skill.rating_sum / ratingCount).toFixed(1) : '-';

        col.innerHTML = `
            <div class="card h-100 skill-card" data-skill-id="${skill.id}" data-workspace-id="${skill.workspace_id}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="card-title mb-0">${escapeHtml(skill.display_name)}</h6>
                        <span class="badge ${categoryBadge}">${escapeHtml(skill.category)}</span>
                    </div>
                    <p class="card-text text-muted small mb-2">${escapeHtml(skill.description || '')}</p>
                    <div class="d-flex gap-2 mb-2">
                        <span class="badge bg-light text-dark border"><code>${escapeHtml(command)}</code></span>
                        <span class="badge bg-light text-dark border">${typeBadge}</span>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">
                            <i class="bi bi-play-circle"></i> ${skill.usage_count || 0} uses
                            ${ratingCount > 0 ? `&middot; <i class="bi bi-star-fill text-warning"></i> ${ratingAvg}` : ''}
                        </small>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary skill-execute-btn" title="Execute">
                                <i class="bi bi-play-fill"></i>
                            </button>
                            <button class="btn btn-outline-secondary skill-edit-btn" title="Edit">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-outline-danger skill-delete-btn" title="Delete">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Event listeners
        col.querySelector('.skill-execute-btn').addEventListener('click', () => executeSkillQuick(skill));
        col.querySelector('.skill-edit-btn').addEventListener('click', () => editSkill(skill));
        col.querySelector('.skill-delete-btn').addEventListener('click', () => deleteSkill(skill));

        return col;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    // ---------------------------------------------------------------
    // Skill Builder Modal - Step Navigation
    // ---------------------------------------------------------------

    function showStep(step) {
        currentStep = step;
        document.querySelectorAll('.skill-step').forEach(el => el.classList.add('d-none'));
        const stepEl = document.getElementById(`skill-step-${step}`);
        if (stepEl) stepEl.classList.remove('d-none');

        // Update step badges
        document.querySelectorAll('.skill-step-badge').forEach(badge => {
            const badgeStep = parseInt(badge.dataset.step);
            badge.className = `badge ${badgeStep <= step ? 'bg-primary' : 'bg-secondary'} rounded-pill skill-step-badge`;
        });

        // Update buttons
        if (prevBtn) prevBtn.disabled = step === 1;
        if (nextBtn) nextBtn.classList.toggle('d-none', step === totalSteps);
        if (saveBtn) saveBtn.classList.toggle('d-none', step !== totalSteps);
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (currentStep < totalSteps) showStep(currentStep + 1);
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentStep > 1) showStep(currentStep - 1);
        });
    }

    if (tempSlider && tempValue) {
        tempSlider.addEventListener('input', () => {
            tempValue.textContent = tempSlider.value;
        });
    }

    // Auto-generate command name from display name
    const displayNameInput = document.getElementById('skill-display-name');
    const nameInput = document.getElementById('skill-name');
    if (displayNameInput && nameInput) {
        displayNameInput.addEventListener('input', () => {
            if (!editingSkillId) {
                nameInput.value = displayNameInput.value
                    .toLowerCase()
                    .replace(/[^a-z0-9\s-]/g, '')
                    .replace(/\s+/g, '-')
                    .substring(0, 50);
            }
        });
    }

    // ---------------------------------------------------------------
    // Save Skill
    // ---------------------------------------------------------------

    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            const payload = collectSkillData();
            if (!payload) return;

            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

            try {
                const url = editingSkillId ? `/api/skills/${editingSkillId}` : '/api/skills';
                const method = editingSkillId ? 'PUT' : 'POST';

                const resp = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });

                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || 'Failed to save skill');

                // Close modal and reload
                const modal = bootstrap.Modal.getInstance(document.getElementById('skillBuilderModal'));
                if (modal) modal.hide();
                resetBuilder();
                loadSkills();
            } catch (err) {
                alert('Error saving skill: ' + err.message);
            } finally {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Save Skill';
            }
        });
    }

    function collectSkillData() {
        const displayName = document.getElementById('skill-display-name')?.value?.trim();
        const name = document.getElementById('skill-name')?.value?.trim();
        const description = document.getElementById('skill-description')?.value?.trim();

        if (!displayName || !name || !description) {
            alert('Please fill in all required fields (name, command, description)');
            showStep(1);
            return null;
        }

        const triggers = (document.getElementById('skill-trigger-phrases')?.value || '')
            .split(',').map(t => t.trim()).filter(Boolean);

        return {
            name,
            display_name: displayName,
            description,
            type: document.getElementById('skill-type')?.value || 'prompt_skill',
            category: document.getElementById('skill-category')?.value || 'other',
            scope: 'personal',
            config: {
                system_prompt: document.getElementById('skill-system-prompt')?.value || '',
                model: document.getElementById('skill-model')?.value || 'gpt-4o',
                temperature: parseFloat(document.getElementById('skill-temperature')?.value || '0.3'),
                max_tokens: parseInt(document.getElementById('skill-max-tokens')?.value || '2000'),
                output_format: document.getElementById('skill-output-format')?.value || 'markdown',
                trigger_phrases: triggers,
                tools: [],
                input_schema: { type: 'object', properties: {} },
            },
            workspace_id: editingSkillId ? undefined : undefined, // Set by backend
        };
    }

    // ---------------------------------------------------------------
    // Test Skill
    // ---------------------------------------------------------------

    if (testBtn) {
        testBtn.addEventListener('click', async () => {
            const input = document.getElementById('skill-test-input')?.value?.trim();
            if (!input) {
                alert('Please enter sample input to test');
                return;
            }

            const payload = collectSkillData();
            if (!payload) return;

            testBtn.disabled = true;
            testBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Testing...';

            const resultDiv = document.getElementById('skill-test-result');
            const outputDiv = document.getElementById('skill-test-output');
            const timingDiv = document.getElementById('skill-test-timing');

            try {
                // If skill exists, use execute endpoint; otherwise use a temp test
                let resp;
                if (editingSkillId) {
                    resp = await fetch(`/api/skills/${editingSkillId}/execute`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ input }),
                    });
                } else {
                    // Save as draft first, execute, then we have the ID
                    const saveResp = await fetch('/api/skills', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    });
                    const saveData = await saveResp.json();
                    if (!saveResp.ok) throw new Error(saveData.error || 'Failed to save draft');

                    editingSkillId = saveData.id;
                    resp = await fetch(`/api/skills/${saveData.id}/execute`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ input, workspace_id: saveData.workspace_id }),
                    });
                }

                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || 'Execution failed');

                if (resultDiv) resultDiv.classList.remove('d-none');
                if (outputDiv) outputDiv.textContent = data.output || 'No output';
                if (timingDiv) timingDiv.textContent = `Completed in ${data.duration_ms}ms`;
            } catch (err) {
                if (resultDiv) resultDiv.classList.remove('d-none');
                if (outputDiv) outputDiv.textContent = 'Error: ' + err.message;
                if (timingDiv) timingDiv.textContent = '';
            } finally {
                testBtn.disabled = false;
                testBtn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Test Skill';
            }
        });
    }

    // ---------------------------------------------------------------
    // Edit / Delete / Execute
    // ---------------------------------------------------------------

    function editSkill(skill) {
        editingSkillId = skill.id;
        document.getElementById('skill-display-name').value = skill.display_name || '';
        document.getElementById('skill-name').value = skill.name || '';
        document.getElementById('skill-description').value = skill.description || '';
        document.getElementById('skill-type').value = skill.type || 'prompt_skill';
        document.getElementById('skill-category').value = skill.category || 'other';

        const config = skill.config || {};
        document.getElementById('skill-system-prompt').value = config.system_prompt || '';
        document.getElementById('skill-model').value = config.model || 'gpt-4o';
        document.getElementById('skill-temperature').value = config.temperature || 0.3;
        document.getElementById('skill-temp-value').textContent = config.temperature || 0.3;
        document.getElementById('skill-max-tokens').value = config.max_tokens || 2000;
        document.getElementById('skill-output-format').value = config.output_format || 'markdown';
        document.getElementById('skill-trigger-phrases').value = (config.trigger_phrases || []).join(', ');

        showStep(1);
        const modal = new bootstrap.Modal(document.getElementById('skillBuilderModal'));
        modal.show();
    }

    async function deleteSkill(skill) {
        if (!confirm(`Delete skill "${skill.display_name}"? This cannot be undone.`)) return;

        try {
            const resp = await fetch(`/api/skills/${skill.id}?workspace_id=${skill.workspace_id}`, {
                method: 'DELETE',
            });
            if (!resp.ok) {
                const data = await resp.json();
                throw new Error(data.error || 'Delete failed');
            }
            loadSkills();
        } catch (err) {
            alert('Error deleting skill: ' + err.message);
        }
    }

    function executeSkillQuick(skill) {
        const command = (skill.commands && skill.commands[0]) || ('/' + skill.name);
        // Navigate to chat and pre-fill with the skill command
        window.location.href = `/chats?prefill=${encodeURIComponent(command + ' ')}`;
    }

    function resetBuilder() {
        editingSkillId = null;
        document.querySelectorAll('#skillBuilderModal input, #skillBuilderModal textarea, #skillBuilderModal select').forEach(el => {
            if (el.type === 'range') el.value = 0.3;
            else if (el.tagName === 'SELECT') el.selectedIndex = 0;
            else el.value = '';
        });
        if (tempValue) tempValue.textContent = '0.3';
        document.getElementById('skill-test-result')?.classList.add('d-none');
        showStep(1);
    }

    // Reset on modal close
    const builderModal = document.getElementById('skillBuilderModal');
    if (builderModal) {
        builderModal.addEventListener('hidden.bs.modal', resetBuilder);
    }

    // Search
    if (skillsSearch) {
        skillsSearch.addEventListener('input', () => {
            const query = skillsSearch.value.toLowerCase();
            document.querySelectorAll('.skill-card').forEach(card => {
                const name = card.querySelector('.card-title')?.textContent?.toLowerCase() || '';
                const desc = card.querySelector('.card-text')?.textContent?.toLowerCase() || '';
                const match = name.includes(query) || desc.includes(query);
                card.closest('.col-md-6').style.display = match ? '' : 'none';
            });
        });
    }

    // ---------------------------------------------------------------
    // Initialize
    // ---------------------------------------------------------------

    loadSkills();
})();
