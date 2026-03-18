/** RedThread — Main Application Controller */

function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

class RedThreadApp {
    constructor() {
        this.graph = null;
        this.currentEntity = null;
        this.pathSource = null;
        this.pathTarget = null;
        this.mode = 'explore'; // explore, pathfind, analyze
    }

    async init() {
        this.graph = new GraphViz('graph-canvas');
        this._bindEvents();
        await this._loadStats();
        await this._loadSidebar();
        toast('RedThread loaded. Double-click nodes to expand.', 'info');
    }

    // === Event Binding ===
    _bindEvents() {
        // Search
        const searchInput = document.getElementById('search-input');
        let searchTimeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => this._onSearch(searchInput.value), 300);
        });
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.length >= 2) this._onSearch(searchInput.value);
        });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#search-box')) {
                document.getElementById('search-results').classList.remove('open');
            }
        });

        // Toolbar buttons
        document.getElementById('btn-fit').addEventListener('click', () => this.graph.fitView());
        document.getElementById('btn-clear').addEventListener('click', () => this._clearGraph());
        document.getElementById('btn-analyze').addEventListener('click', () => this._toggleAnalysis());
        document.getElementById('btn-patterns').addEventListener('click', () => this._runPatterns());
        document.getElementById('btn-temporal').addEventListener('click', () => this.openTimeline());
        document.getElementById('btn-nlq').addEventListener('click', () => this.openNLQ());
        document.getElementById('btn-timeline-changes').addEventListener('click', () => this._showTimelineChanges());
        document.getElementById('btn-nlq-run').addEventListener('click', () => this._runNLQuery());
        document.getElementById('nlq-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this._runNLQuery();
        });
        document.getElementById('nlq-modal').addEventListener('click', (e) => {
            if (e.target.id === 'nlq-modal') this.closeNLQ();
        });
        document.getElementById('timeline-slider').addEventListener('change', () => this._loadGraphAtTime());

        // Sidebar tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(btn.dataset.tab).classList.add('active');
            });
        });
    }

    // === Search ===
    async _onSearch(query) {
        const resultsEl = document.getElementById('search-results');
        if (query.length < 2) {
            resultsEl.classList.remove('open');
            return;
        }

        try {
            const data = await API.searchEntities(query);
            resultsEl.innerHTML = '';
            if (data.entities.length === 0) {
                resultsEl.innerHTML = '<div class="search-result">No results found</div>';
            } else {
                data.entities.forEach(entity => {
                    const div = document.createElement('div');
                    div.className = 'search-result';
                    div.innerHTML = `
                        <span class="entity-badge badge-${entity.label.toLowerCase()}">${entity.label[0]}</span>
                        <span>${entity.name || entity.account_number || entity.full_address || entity.id}</span>
                    `;
                    div.addEventListener('click', () => {
                        this._focusEntity(entity);
                        resultsEl.classList.remove('open');
                        document.getElementById('search-input').value = '';
                    });
                    resultsEl.appendChild(div);
                });
            }
            resultsEl.classList.add('open');
        } catch (e) {
            console.error('Search failed:', e);
        }
    }

    // === Node Interactions ===
    async onNodeSelect(nodeId) {
        const entity = this.graph.getNodeData(nodeId);
        if (!entity) {
            try {
                const data = await API.getEntity(nodeId);
                this._showDetail(data);
            } catch { return; }
        } else {
            this._showDetail(entity);
        }

        // If in pathfind mode, set source/target
        if (this.mode === 'pathfind') {
            if (!this.pathSource) {
                this.pathSource = nodeId;
                toast(`Path source set: ${nodeId}. Click another node for target.`, 'info');
            } else if (!this.pathTarget) {
                this.pathTarget = nodeId;
                this._findPath(this.pathSource, this.pathTarget);
            }
        } else if (this.mode === 'shared') {
            this._runSharedConnections(this._sharedSource, nodeId);
        } else if (this.mode === 'hidden') {
            this._runHiddenConnections(this._hiddenSource, nodeId);
        }
    }

    onNodeDeselect() {
        // Keep panel open — user can close manually
    }

    async expandNode(nodeId) {
        try {
            const data = await API.getNeighborhood(nodeId, 1, 30);
            this.graph.loadNeighborhood(data);
            toast(`Expanded: ${data.nodes.length} nodes, ${data.edges.length} edges`, 'info');
        } catch (e) {
            toast('Failed to expand node', 'error');
        }
    }

    async _focusEntity(entity) {
        this.graph.addNode(entity);
        const data = await API.getNeighborhood(entity.id, 1, 30);
        this.graph.loadNeighborhood(data);
        this._showDetail(entity);
        this.graph.network.focus(entity.id, { scale: 1.2, animation: true });
    }

    // === Detail Panel ===
    _showDetail(entity) {
        this.currentEntity = entity;
        const panel = document.getElementById('detail-panel');
        panel.classList.add('open');

        const header = panel.querySelector('.detail-header h2');
        header.textContent = entity.name || entity.account_number || entity.full_address || entity.id;

        const badge = panel.querySelector('.detail-header .entity-badge');
        badge.textContent = entity.label[0];
        badge.className = `entity-badge badge-${entity.label.toLowerCase()}`;

        // Properties
        const propsEl = document.getElementById('detail-props');
        propsEl.innerHTML = '';
        const skipFields = ['label', 'created_at', 'updated_at', 'aliases'];
        for (const [key, val] of Object.entries(entity)) {
            if (skipFields.includes(key) || val === '' || val === null || val === undefined) continue;
            propsEl.innerHTML += `
                <span class="prop-label">${key.replace(/_/g, ' ')}</span>
                <span class="prop-value">${key === 'risk_score' ? this._riskBadge(val) : val}</span>
            `;
        }

        // Load relationships and tags
        this._loadRelationships(entity.id);
        this._loadEntityTags(entity.id);
    }

    async _loadRelationships(entityId) {
        const relsEl = document.getElementById('detail-rels');
        relsEl.innerHTML = '<div class="spinner"></div>';
        try {
            const rels = await API.getRelationships(entityId);
            relsEl.innerHTML = '';
            if (rels.length === 0) {
                relsEl.innerHTML = '<p style="color:var(--text-secondary);font-size:12px">No relationships</p>';
                return;
            }
            rels.forEach(rel => {
                const otherId = rel.source_id === entityId ? rel.target_id : rel.source_id;
                const direction = rel.source_id === entityId ? '→' : '←';
                const div = document.createElement('div');
                div.className = 'rel-item';
                div.innerHTML = `
                    <span class="rel-type">${rel.rel_type.replace(/_/g, ' ')}</span>
                    <span>${direction} ${otherId}</span>
                    ${rel.properties?.amount ? `<br><small>$${Number(rel.properties.amount).toLocaleString()}</small>` : ''}
                `;
                div.addEventListener('click', () => this._focusEntityById(otherId));
                relsEl.appendChild(div);
            });
        } catch {
            relsEl.innerHTML = '<p style="color:var(--accent);font-size:12px">Failed to load</p>';
        }
    }

    async _focusEntityById(entityId) {
        try {
            const entity = await API.getEntity(entityId);
            await this._focusEntity(entity);
        } catch (e) {
            toast('Entity not found', 'error');
        }
    }

    _riskBadge(score) {
        const level = score >= 60 ? 'high' : score >= 30 ? 'medium' : 'low';
        return `<span class="risk-indicator risk-${level}" style="display:inline-block;margin-right:4px"></span>${score}`;
    }

    closeDetail() {
        document.getElementById('detail-panel').classList.remove('open');
    }

    // === Sidebar ===
    async _loadSidebar() {
        const labels = ['Person', 'Organization', 'Account'];
        for (const label of labels) {
            try {
                const data = await API.listEntities(label, 0, 20);
                const listEl = document.getElementById(`list-${label.toLowerCase()}`);
                if (!listEl) continue;
                listEl.innerHTML = '';
                data.entities.forEach(entity => {
                    const li = document.createElement('li');
                    li.className = 'entity-item';
                    const name = entity.name || entity.account_number || entity.id;
                    const risk = entity.risk_score || 0;
                    const riskClass = risk >= 60 ? 'high' : risk >= 30 ? 'medium' : 'low';
                    li.innerHTML = `
                        <span class="entity-badge badge-${label.toLowerCase()}">${label[0]}</span>
                        <span class="entity-name">${name}</span>
                        <span class="risk-indicator risk-${riskClass}"></span>
                    `;
                    li.addEventListener('click', () => this._focusEntity(entity));
                    listEl.appendChild(li);
                });
            } catch (e) { console.error(`Failed to load ${label}:`, e); }
        }
    }

    async _loadStats() {
        try {
            const stats = await API.stats();
            document.getElementById('stat-nodes').textContent = stats.total_nodes || 0;
            document.getElementById('stat-rels').textContent = stats.total_relationships || 0;
        } catch {}
    }

    // === Analysis Tools ===
    _toggleAnalysis() {
        const panel = document.getElementById('analysis-panel');
        panel.classList.toggle('open');
    }

    async _findPath(sourceId, targetId) {
        toast(`Finding paths: ${sourceId} → ${targetId}...`, 'info');
        try {
            const data = await API.findPaths(sourceId, targetId);
            if (data.paths.length === 0) {
                toast('No paths found between these entities', 'warning');
            } else {
                this.graph.clearHighlights();
                data.paths.slice(0, 5).forEach(p => this.graph.highlightPath(p));
                toast(`Found ${data.count} paths (showing top 5)`, 'success');
                this._showPathResults(data.paths);
            }
        } catch (e) {
            toast('Path finding failed', 'error');
        }
        this.pathSource = null;
        this.pathTarget = null;
        this.mode = 'explore';
    }

    _showPathResults(paths) {
        const panel = document.getElementById('analysis-panel');
        panel.classList.add('open');
        const content = document.getElementById('analysis-content');
        content.innerHTML = `<h3>🔗 ${paths.length} Paths Found</h3>`;
        paths.slice(0, 10).forEach((path, i) => {
            const div = document.createElement('div');
            div.className = 'path-result';
            const nodeNames = path.nodes.map(n =>
                n.name || n.account_number || n.full_address || n.id
            );
            div.innerHTML = `
                <div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px">
                    Path ${i + 1} (${path.length} hops)
                    ${path.total_flow ? `· $${Number(path.total_flow).toLocaleString()} total flow` : ''}
                </div>
                <div class="path-nodes">${nodeNames.join(' <span class="path-arrow">→</span> ')}</div>
            `;
            div.addEventListener('click', () => {
                this.graph.clearHighlights();
                this.graph.highlightPath(path);
            });
            content.appendChild(div);
        });
    }

    startPathfind() {
        this.mode = 'pathfind';
        this.pathSource = null;
        this.pathTarget = null;
        toast('Click two nodes to find paths between them', 'info');
    }

    async findPathBetween() {
        if (!this.currentEntity) {
            toast('Select an entity first', 'warning');
            return;
        }
        this.pathSource = this.currentEntity.id;
        this.mode = 'pathfind';
        toast(`Source: ${this.currentEntity.name || this.currentEntity.id}. Click target node.`, 'info');
    }

    async runMoneyFlow() {
        if (!this.currentEntity) {
            toast('Select an account entity first', 'warning');
            return;
        }
        toast('Tracing money flow...', 'info');
        try {
            const data = await API.moneyFlow(this.currentEntity.id);
            if (data.flows.length === 0) {
                toast('No money flows found from this entity', 'warning');
                return;
            }
            this.graph.clearHighlights();
            data.flows.forEach(f => this.graph.highlightPath(f));
            toast(`Found ${data.count} money flow paths`, 'success');
            this._showPathResults(data.flows);
        } catch {
            toast('Money flow tracing failed', 'error');
        }
    }

    async computeRisk() {
        if (!this.currentEntity) {
            toast('Select an entity first', 'warning');
            return;
        }
        try {
            const risk = await API.computeRisk(this.currentEntity.id);
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');
            content.innerHTML = `
                <h3>⚠️ Risk Assessment</h3>
                <div style="font-size:24px;font-weight:700;color:${risk.risk_score >= 60 ? '#ef4444' : risk.risk_score >= 30 ? '#f59e0b' : '#22c55e'};margin:12px 0">
                    ${risk.risk_score} / 100
                </div>
                <div style="font-size:12px;color:var(--text-secondary);margin-bottom:12px">
                    Base: ${risk.base_risk} | Propagated: ${risk.propagated_risk}
                </div>
                <h4 style="font-size:11px;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px">Risk Factors</h4>
                ${risk.factors.map(f => `
                    <div style="padding:4px 8px;background:var(--bg-tertiary);border-radius:4px;margin-bottom:4px;font-size:12px">
                        <strong>${f.factor}</strong>: ${f.detail} (+${f.score})
                    </div>
                `).join('')}
            `;
            toast(`Risk score: ${risk.risk_score}`, risk.risk_score >= 60 ? 'error' : 'info');
        } catch {
            toast('Risk computation failed', 'error');
        }
    }

    async _runPatterns() {
        toast('Running pattern detection...', 'info');
        try {
            const data = await API.detectPatterns();
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');

            let html = '<h3>🔍 Pattern Detection Results</h3>';
            const sections = [
                { key: 'circular_flows', title: '🔄 Circular Money Flows', icon: '🔄' },
                { key: 'shell_company_chains', title: '🏢 Shell Company Chains', icon: '🏢' },
                { key: 'structuring', title: '💰 Structuring (Smurfing)', icon: '💰' },
                { key: 'rapid_passthrough', title: '⚡ Rapid Pass-Through', icon: '⚡' },
            ];

            for (const section of sections) {
                const items = data[section.key] || [];
                html += `<div style="margin-top:12px">
                    <h4 style="font-size:12px;margin-bottom:6px">${section.title} (${items.length})</h4>`;
                if (items.length === 0) {
                    html += '<p style="font-size:11px;color:var(--text-secondary)">None detected</p>';
                }
                items.slice(0, 5).forEach(item => {
                    if (section.key === 'circular_flows') {
                        html += `<div class="path-result"><small>Account ${item.start_account}: cycle of ${item.cycle_length} hops, $${Number(item.cycle_total).toLocaleString()}</small></div>`;
                    } else if (section.key === 'shell_company_chains') {
                        html += `<div class="path-result"><small>${item.controller} → ${item.first_entity} (${item.first_jurisdiction}) → ... → ${item.terminal_entity} (${item.terminal_jurisdiction})</small></div>`;
                    } else if (section.key === 'structuring') {
                        html += `<div class="path-result"><small>Account ${item.source_account}: ${item.num_transactions} txns just below threshold, $${Number(item.total_amount).toLocaleString()} total</small></div>`;
                    } else if (section.key === 'rapid_passthrough') {
                        html += `<div class="path-result"><small>${item.source} → ${item.passthrough_account} → ${item.destination}: $${Number(item.amount_in).toLocaleString()} in, $${Number(item.amount_out).toLocaleString()} out</small></div>`;
                    }
                });
                html += '</div>';
            }
            content.innerHTML = html;
            toast('Pattern detection complete', 'success');
        } catch (e) {
            toast('Pattern detection failed', 'error');
        }
    }

    async showHighestRisk() {
        try {
            const entities = await API.highestRisk();
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');
            content.innerHTML = '<h3>⚠️ Highest Risk Entities</h3>';
            entities.forEach(e => {
                const div = document.createElement('div');
                div.className = 'entity-item';
                div.style.marginBottom = '4px';
                div.innerHTML = `
                    <span class="entity-badge badge-${(e.label || 'unknown').toLowerCase()}">${(e.label || '?')[0]}</span>
                    <span class="entity-name">${e.name || e.account_number || e.id}</span>
                    <span style="color:${e.risk_score >= 60 ? '#ef4444' : '#f59e0b'};font-size:12px;font-weight:600">${e.risk_score}</span>
                `;
                div.addEventListener('click', () => this._focusEntity(e));
                content.appendChild(div);
            });
        } catch { toast('Failed to load risk data', 'error'); }
    }

    async showCentrality() {
        try {
            const entities = await API.centrality();
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');
            content.innerHTML = '<h3>🎯 Most Connected Entities</h3>';
            entities.forEach(e => {
                const div = document.createElement('div');
                div.className = 'entity-item';
                div.style.marginBottom = '4px';
                div.innerHTML = `
                    <span class="entity-badge badge-${(e.label || 'unknown').toLowerCase()}">${(e.label || '?')[0]}</span>
                    <span class="entity-name">${e.name || e.account_number || e.id}</span>
                    <span style="color:var(--info);font-size:12px">${e.degree} links</span>
                `;
                div.addEventListener('click', () => this._focusEntity(e));
                content.appendChild(div);
            });
        } catch { toast('Failed to load centrality data', 'error'); }
    }

    async showEntityReach() {
        if (!this.currentEntity) {
            toast('Select an entity first', 'warning');
            return;
        }
        toast('Computing entity reach...', 'info');
        try {
            const data = await API.entityReach(this.currentEntity.id, 3);
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');
            const name = this.currentEntity.name || this.currentEntity.account_number || this.currentEntity.id;
            let html = `<h3>🌐 Reach from ${escapeHtml(name)}</h3>
                <p style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">
                    ${data.total_reached} entities reachable within ${data.max_depth} hops
                </p>`;
            if (data.by_distance) {
                for (const [dist, entities] of Object.entries(data.by_distance)) {
                    html += `<div style="margin-top:8px"><h4 style="font-size:11px;text-transform:uppercase;color:var(--text-secondary);margin-bottom:4px">Depth ${escapeHtml(dist)} (${entities.length} entities)</h4>`;
                    entities.slice(0, 10).forEach(e => {
                        html += `<div class="entity-item" style="margin-bottom:3px;cursor:pointer" data-id="${escapeHtml(e.id)}">
                            <span class="entity-badge badge-${(e.label || 'unknown').toLowerCase()}">${(e.label || '?')[0]}</span>
                            <span class="entity-name">${escapeHtml(e.name || e.account_number || e.id)}</span>
                        </div>`;
                    });
                    if (entities.length > 10) {
                        html += `<p style="font-size:10px;color:var(--text-secondary)">...and ${entities.length - 10} more</p>`;
                    }
                    html += '</div>';
                }
            }
            content.innerHTML = html;
            content.querySelectorAll('.entity-item[data-id]').forEach(el => {
                el.addEventListener('click', () => this._focusEntityById(el.dataset.id));
            });
            toast(`${data.total_reached} reachable entities`, 'success');
        } catch {
            toast('Entity reach analysis failed', 'error');
        }
    }

    async showBridges() {
        toast('Finding bridge entities...', 'info');
        try {
            const bridges = await API.bridges();
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');

            let html = `<h3>🌉 Bridge Entities</h3>
                <p style="font-size:12px;color:var(--text-secondary);margin-bottom:12px">
                    Entities that connect otherwise separate groups — removing them would disconnect the network.
                </p>`;

            if (!bridges || bridges.length === 0) {
                html += '<p style="color:var(--text-secondary);font-size:12px">No bridge entities detected.</p>';
            } else {
                bridges.forEach(b => {
                    html += `<div class="entity-item" style="margin-bottom:4px;cursor:pointer" data-id="${escapeHtml(b.id)}">
                        <span class="entity-badge badge-${(b.label || 'unknown').toLowerCase()}">${(b.label || '?')[0]}</span>
                        <span class="entity-name">${escapeHtml(b.name || b.account_number || b.id)}</span>
                        <span style="color:var(--warning);font-size:11px">${b.degree ? b.degree + ' links' : ''}</span>
                    </div>`;
                });
            }
            content.innerHTML = html;
            content.querySelectorAll('.entity-item[data-id]').forEach(el => {
                el.addEventListener('click', () => this._focusEntityById(el.dataset.id));
            });
            toast(`${(bridges || []).length} bridge entities found`, 'success');
        } catch {
            toast('Bridge detection failed', 'error');
        }
    }

    async detectCommunities() {
        toast('Detecting communities...', 'info');
        try {
            const data = await API.detectCommunities();
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');

            let html = `<h3>🏘️ Community Detection</h3>
                <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
                    <span style="background:var(--bg-tertiary);padding:3px 8px;border-radius:4px;font-size:12px"><strong>${data.total_communities}</strong> communities</span>
                    <span style="background:var(--bg-tertiary);padding:3px 8px;border-radius:4px;font-size:12px"><strong>${data.cross_community_edges || 0}</strong> cross-links</span>
                    <span style="background:var(--bg-tertiary);padding:3px 8px;border-radius:4px;font-size:12px">modularity: <strong>${data.modularity_estimate || 0}</strong></span>
                </div>`;

            if (data.communities.length === 0) {
                html += '<p style="color:var(--text-secondary);font-size:12px">No communities detected (graph may be too sparse).</p>';
            } else {
                const colors = ['#3b82f6', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];
                data.communities.forEach((comm, i) => {
                    const color = colors[i % colors.length];
                    html += `<div style="margin-top:10px;border-left:3px solid ${color};padding-left:8px">
                        <h4 style="font-size:12px;margin-bottom:4px">${escapeHtml(comm.id)} — ${comm.size} members (density: ${comm.density})</h4>`;
                    if (comm.member_details) {
                        comm.member_details.slice(0, 10).forEach(m => {
                            html += `<div class="entity-item" style="margin-bottom:2px;cursor:pointer" data-id="${escapeHtml(m.id)}">
                                <span class="entity-badge badge-${(m.label || 'unknown').toLowerCase()}">${(m.label || '?')[0]}</span>
                                <span class="entity-name">${escapeHtml(m.name || m.id)}</span>
                            </div>`;
                        });
                        if (comm.size > 10) {
                            html += `<p style="font-size:10px;color:var(--text-secondary)">...and ${comm.size - 10} more</p>`;
                        }
                    }
                    html += '</div>';
                });
            }

            content.innerHTML = html;
            content.querySelectorAll('.entity-item[data-id]').forEach(el => {
                el.addEventListener('click', () => this._focusEntityById(el.dataset.id));
            });
            toast(`${data.total_communities} communities detected`, 'success');
        } catch {
            toast('Community detection failed', 'error');
        }
    }

    startSharedConnections() {
        if (!this.currentEntity) {
            toast('Select a first entity, then click "Shared Connections" again', 'warning');
            return;
        }
        this._sharedSource = this.currentEntity.id;
        this._sharedSourceName = this.currentEntity.name || this.currentEntity.account_number || this.currentEntity.id;
        this.mode = 'shared';
        toast(`Source: ${this._sharedSourceName}. Click another node to find shared connections.`, 'info');
    }

    async _runSharedConnections(id1, id2) {
        toast('Finding shared connections...', 'info');
        try {
            const shared = await API.sharedConnections(id1, id2);
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');

            let html = `<h3>🤝 Shared Connections</h3>`;
            if (!shared || shared.length === 0) {
                html += '<p style="color:var(--text-secondary);font-size:12px">No shared connections found.</p>';
            } else {
                html += `<p style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">${shared.length} mutual connections</p>`;
                shared.forEach(s => {
                    html += `<div class="entity-item" style="margin-bottom:4px;cursor:pointer" data-id="${escapeHtml(s.id)}">
                        <span class="entity-badge badge-${(s.label || 'unknown').toLowerCase()}">${(s.label || '?')[0]}</span>
                        <span class="entity-name">${escapeHtml(s.name || s.account_number || s.id)}</span>
                    </div>`;
                });
            }
            content.innerHTML = html;
            content.querySelectorAll('.entity-item[data-id]').forEach(el => {
                el.addEventListener('click', () => this._focusEntityById(el.dataset.id));
            });
            toast(`${(shared || []).length} shared connections`, 'success');
        } catch {
            toast('Shared connections analysis failed', 'error');
        }
        this.mode = 'explore';
    }

    startHiddenConnections() {
        if (!this.currentEntity) {
            toast('Select a first entity, then click "Hidden Connections" again', 'warning');
            return;
        }
        this._hiddenSource = this.currentEntity.id;
        this._hiddenSourceName = this.currentEntity.name || this.currentEntity.account_number || this.currentEntity.id;
        this.mode = 'hidden';
        toast(`Source: ${this._hiddenSourceName}. Click another node to find hidden connections.`, 'info');
    }

    async _runHiddenConnections(id1, id2) {
        toast('Discovering hidden connections...', 'info');
        try {
            const data = await API.hiddenConnections(id1, id2);
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');

            const connections = data.connections || [];
            let html = `<h3>🕵️ Hidden Connections</h3>`;
            if (connections.length === 0) {
                html += '<p style="color:var(--text-secondary);font-size:12px">No hidden connections found between these entities.</p>';
            } else {
                html += `<p style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">${connections.length} indirect connections discovered</p>`;
                connections.slice(0, 10).forEach((conn, i) => {
                    const nodes = conn.path ? conn.path.nodes : [];
                    const names = nodes.map(n => escapeHtml(n.name || n.account_number || n.id));
                    html += `<div class="path-result">
                        <div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px">Connection ${i + 1} (${conn.hops} hops)</div>
                        <div class="path-nodes">${names.join(' <span class="path-arrow">→</span> ')}</div>
                    </div>`;
                });
            }
            content.innerHTML = html;
            toast(`${connections.length} hidden connections found`, 'success');
        } catch {
            toast('Hidden connection analysis failed', 'error');
        }
        this.mode = 'explore';
    }

    async validateGraph() {
        toast('Validating graph data quality...', 'info');
        try {
            const data = await API.get('/api/analysis/validate');
            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');

            let html = `<h3>🩺 Data Quality Report</h3>`;

            const checks = [
                { key: 'orphaned_nodes', title: '🔵 Orphaned Nodes', desc: 'Entities with no relationships' },
                { key: 'missing_names', title: '🟡 Missing Names', desc: 'Entities without a name property' },
                { key: 'duplicate_ids', title: '🔴 Duplicate IDs', desc: 'Multiple entities sharing an ID' },
                { key: 'self_references', title: '🟠 Self-References', desc: 'Entities with relationships to themselves' },
            ];

            let totalIssues = 0;
            for (const check of checks) {
                const items = data[check.key] || [];
                totalIssues += items.length;
                html += `<div style="margin-top:10px">
                    <h4 style="font-size:12px;margin-bottom:4px">${check.title} (${items.length})</h4>
                    <p style="font-size:10px;color:var(--text-secondary);margin-bottom:4px">${check.desc}</p>`;
                if (items.length === 0) {
                    html += '<p style="font-size:11px;color:var(--success)">✓ None found</p>';
                } else {
                    items.slice(0, 8).forEach(item => {
                        html += `<div style="font-size:11px;padding:2px 4px;background:var(--bg-tertiary);border-radius:3px;margin-bottom:2px">
                            ${escapeHtml(item.label || '')} ${escapeHtml(item.name || item.id || JSON.stringify(item))}
                        </div>`;
                    });
                    if (items.length > 8) {
                        html += `<p style="font-size:10px;color:var(--text-secondary)">...and ${items.length - 8} more</p>`;
                    }
                }
                html += '</div>';
            }

            const status = totalIssues === 0 ? '✅ All checks passed!' : `⚠️ ${totalIssues} issues found`;
            html = html.replace('</h3>', `</h3><p style="font-size:13px;margin-bottom:8px;font-weight:600">${status}</p>`);
            content.innerHTML = html;
            toast(status, totalIssues === 0 ? 'success' : 'warning');
        } catch {
            toast('Validation failed', 'error');
        }
    }

    _clearGraph() {
        this.graph.clear();
        toast('Graph cleared', 'info');
    }

    async exportReport() {
        if (!this.currentEntity) {
            toast('Select an entity first', 'warning');
            return;
        }
        try {
            const report = await API.generateReport(this.currentEntity.id);
            const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `redthread-report-${this.currentEntity.id}.json`;
            a.click();
            URL.revokeObjectURL(url);
            toast('Report exported', 'success');
        } catch { toast('Export failed', 'error'); }
    }

    // === Temporal Analysis ===
    async openTimeline() {
        const panel = document.getElementById('timeline-panel');
        if (panel.classList.contains('open')) {
            this.closeTimeline();
            return;
        }

        toast('Loading timeline data...', 'info');
        try {
            const range = await API.temporalDateRange();
            if (!range.earliest || !range.latest) {
                toast('No temporal data available', 'warning');
                return;
            }

            this._timelineRange = range;
            this._timelineDates = this._generateDateList(range.earliest, range.latest);

            document.getElementById('timeline-start').textContent = range.earliest;
            document.getElementById('timeline-end').textContent = range.latest;

            const slider = document.getElementById('timeline-slider');
            slider.max = this._timelineDates.length - 1;
            slider.value = slider.max;

            this._updateTimelineDisplay(this._timelineDates.length - 1);
            panel.classList.add('open');

            slider.oninput = () => this._updateTimelineDisplay(parseInt(slider.value));
        } catch {
            toast('Failed to load timeline', 'error');
        }
    }

    _generateDateList(start, end) {
        const dates = [];
        // Parse as YYYY-MM-DD components to avoid timezone issues
        const [sy, sm] = start.split('-').map(Number);
        const [ey, em, ed] = end.split('-').map(Number);
        let year = sy, month = sm;
        while (year < ey || (year === ey && month <= em)) {
            dates.push(`${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-01`);
            month++;
            if (month > 12) { month = 1; year++; }
        }
        // Always include the exact end date
        const endStr = end;
        if (dates.length === 0 || dates[dates.length - 1] !== endStr) dates.push(endStr);
        return dates;
    }

    _updateTimelineDisplay(index) {
        const date = this._timelineDates[index];
        document.getElementById('timeline-date-display').textContent = date;
        document.getElementById('timeline-info').textContent = `${index + 1} / ${this._timelineDates.length}`;
    }

    async _loadGraphAtTime() {
        const slider = document.getElementById('timeline-slider');
        const date = this._timelineDates[parseInt(slider.value)];
        toast(`Loading graph at ${date}...`, 'info');
        try {
            const data = await API.graphAtTime(date);
            this.graph.clear();
            if (data.nodes.length === 0) {
                toast(`No active relationships at ${date}`, 'warning');
                return;
            }
            for (const node of data.nodes) {
                this.graph.addNode(node);
            }
            for (const edge of data.edges) {
                this.graph.addEdge(edge);
            }
            this.graph.fitView();
            toast(`${date}: ${data.node_count} entities, ${data.edge_count} relationships`, 'success');
        } catch {
            toast('Failed to load temporal graph', 'error');
        }
    }

    async _showTimelineChanges() {
        const slider = document.getElementById('timeline-slider');
        const idx = parseInt(slider.value);
        if (idx === 0) {
            toast('No prior date to compare against', 'warning');
            return;
        }

        const startDate = this._timelineDates[Math.max(0, idx - 1)];
        const endDate = this._timelineDates[idx];

        try {
            const data = await API.temporalChanges(startDate, endDate);
            const container = document.getElementById('timeline-changes');
            container.innerHTML = '';

            if (data.total_changes === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);font-size:11px">No changes in this period</p>';
                return;
            }

            data.appeared.forEach(c => {
                const div = document.createElement('div');
                div.className = 'change-item change-appeared';
                const strong = document.createElement('strong');
                strong.textContent = '+';
                div.appendChild(strong);
                div.appendChild(document.createTextNode(` ${c.source_name || c.source_id} `));
                const span = document.createElement('span');
                span.style.color = 'var(--text-secondary)';
                span.textContent = (c.rel_type || '').replace(/_/g, ' ');
                div.appendChild(span);
                div.appendChild(document.createTextNode(` → ${c.target_name || c.target_id}`));
                container.appendChild(div);
            });

            data.disappeared.forEach(c => {
                const div = document.createElement('div');
                div.className = 'change-item change-disappeared';
                const strong = document.createElement('strong');
                strong.textContent = '−';
                div.appendChild(strong);
                div.appendChild(document.createTextNode(` ${c.source_name || c.source_id} `));
                const span = document.createElement('span');
                span.style.color = 'var(--text-secondary)';
                span.textContent = (c.rel_type || '').replace(/_/g, ' ');
                div.appendChild(span);
                div.appendChild(document.createTextNode(` → ${c.target_name || c.target_id}`));
                container.appendChild(div);
            });

            toast(`${data.total_changes} changes found`, 'info');
        } catch {
            toast('Failed to load changes', 'error');
        }
    }

    closeTimeline() {
        document.getElementById('timeline-panel').classList.remove('open');
    }

    // === Snapshots & Diff ===
    async takeSnapshot() {
        const name = prompt('Snapshot name:', `Snapshot ${new Date().toISOString().slice(0, 16)}`);
        if (!name) return;

        try {
            // Use a default investigation or create one
            const investigations = await API.listInvestigations();
            let invId;
            if (investigations.length > 0) {
                invId = investigations[0].id;
            } else {
                const inv = await API.createInvestigation({ name: 'Default Investigation', description: 'Auto-created for snapshots' });
                invId = inv.id;
            }
            const result = await API.createSnapshot(invId, name);
            toast(`Snapshot saved: ${result.node_count} nodes, ${result.relationship_count} relationships`, 'success');
        } catch {
            toast('Failed to save snapshot', 'error');
        }
    }

    async openDiffView() {
        try {
            const snapshots = await API.listSnapshots();
            if (snapshots.length < 1) {
                toast('No snapshots found. Take a snapshot first.', 'warning');
                return;
            }

            const panel = document.getElementById('analysis-panel');
            panel.classList.add('open');
            const content = document.getElementById('analysis-content');

            if (snapshots.length === 1) {
                // Compare against current
                content.innerHTML = '<h3>🔀 Comparing snapshot vs current graph...</h3><div class="spinner"></div>';
                const diff = await API.diffCurrent(snapshots[0].id);
                this._renderDiff(content, diff, `"${snapshots[0].name}" → Current`);
            } else {
                // Compare the two most recent snapshots
                content.innerHTML = '<h3>🔀 Comparing most recent snapshots...</h3><div class="spinner"></div>';
                const diff = await API.diffSnapshots(snapshots[1].id, snapshots[0].id);
                this._renderDiff(content, diff, `"${snapshots[1].name}" → "${snapshots[0].name}"`);
            }
        } catch (e) {
            toast('Diff failed: ' + e.message, 'error');
        }
    }

    _renderDiff(container, diff, title) {
        const s = diff.summary;
        let html = `<h3>🔀 Graph Diff</h3>
            <p style="font-size:11px;color:var(--text-secondary);margin-bottom:8px">${title}</p>
            <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
                <span style="background:rgba(34,197,94,0.1);color:var(--success);padding:3px 8px;border-radius:4px;font-size:12px">+${s.nodes_added} nodes</span>
                <span style="background:rgba(239,68,68,0.1);color:var(--accent);padding:3px 8px;border-radius:4px;font-size:12px">−${s.nodes_removed} nodes</span>
                <span style="background:rgba(245,158,11,0.1);color:var(--warning);padding:3px 8px;border-radius:4px;font-size:12px">~${s.nodes_modified} modified</span>
                <span style="background:rgba(34,197,94,0.1);color:var(--success);padding:3px 8px;border-radius:4px;font-size:12px">+${s.relationships_added} rels</span>
                <span style="background:rgba(239,68,68,0.1);color:var(--accent);padding:3px 8px;border-radius:4px;font-size:12px">−${s.relationships_removed} rels</span>
            </div>`;

        if (s.total_changes === 0) {
            html += '<p style="color:var(--text-secondary);font-size:12px">No differences found.</p>';
        }

        if (diff.added_nodes.length > 0) {
            html += '<div class="diff-section"><h4>🟢 New Entities</h4>';
            diff.added_nodes.forEach(n => {
                html += `<div class="diff-item diff-added">${escapeHtml(n._label || 'Unknown')}: ${escapeHtml(n.name || n.account_number || n.id)}</div>`;
            });
            html += '</div>';
        }

        if (diff.removed_nodes.length > 0) {
            html += '<div class="diff-section"><h4>🔴 Removed Entities</h4>';
            diff.removed_nodes.forEach(n => {
                html += `<div class="diff-item diff-removed">${escapeHtml(n._label || 'Unknown')}: ${escapeHtml(n.name || n.account_number || n.id)}</div>`;
            });
            html += '</div>';
        }

        if (diff.modified_nodes.length > 0) {
            html += '<div class="diff-section"><h4>🟡 Modified Entities</h4>';
            diff.modified_nodes.forEach(n => {
                const changeStr = Object.entries(n.changes).map(([k, v]) => `${escapeHtml(k)}: ${escapeHtml(v.old)} → ${escapeHtml(v.new)}`).join(', ');
                html += `<div class="diff-item diff-modified">${escapeHtml(n.label)}: ${escapeHtml(n.name)} — ${changeStr}</div>`;
            });
            html += '</div>';
        }

        if (diff.added_relationships.length > 0) {
            html += '<div class="diff-section"><h4>🟢 New Relationships</h4>';
            diff.added_relationships.forEach(r => {
                html += `<div class="diff-item diff-added">${escapeHtml(r.source_id)} → ${escapeHtml((r.rel_type || '').replace(/_/g, ' '))} → ${escapeHtml(r.target_id)}</div>`;
            });
            html += '</div>';
        }

        if (diff.removed_relationships.length > 0) {
            html += '<div class="diff-section"><h4>🔴 Removed Relationships</h4>';
            diff.removed_relationships.forEach(r => {
                html += `<div class="diff-item diff-removed">${escapeHtml(r.source_id)} → ${escapeHtml((r.rel_type || '').replace(/_/g, ' '))} → ${escapeHtml(r.target_id)}</div>`;
            });
            html += '</div>';
        }

        container.innerHTML = html;
        toast(`Diff complete: ${s.total_changes} changes`, 'info');
    }

    // === Natural Language Query ===
    async openNLQ() {
        const modal = document.getElementById('nlq-modal');
        modal.classList.add('open');

        // Reset state
        document.getElementById('nlq-result').style.display = 'none';
        document.getElementById('nlq-error').style.display = 'none';
        document.getElementById('nlq-input').value = '';

        // Load examples
        try {
            const examples = await API.nlExamples();
            const container = document.getElementById('nlq-examples');
            container.innerHTML = '<span style="font-size:10px;text-transform:uppercase;color:var(--text-secondary);display:block;margin-bottom:4px">Try these:</span>';
            examples.slice(0, 6).forEach(ex => {
                const span = document.createElement('span');
                span.className = 'nlq-example';
                span.textContent = ex;
                span.addEventListener('click', () => {
                    document.getElementById('nlq-input').value = ex;
                    this._runNLQuery(ex);
                });
                container.appendChild(span);
            });
        } catch {}

        document.getElementById('nlq-input').focus();
    }

    // === Tags ===
    async _loadEntityTags(entityId) {
        const container = document.getElementById('detail-tags');
        container.innerHTML = '';
        try {
            const tags = await API.getEntityTags(entityId);
            tags.forEach(tag => {
                const chip = document.createElement('span');
                chip.style.cssText = `display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:12px;font-size:11px;background:${escapeHtml(tag.color)}33;color:${escapeHtml(tag.color)};border:1px solid ${escapeHtml(tag.color)}66`;
                chip.innerHTML = `${escapeHtml(tag.name)} <span style="cursor:pointer;font-weight:bold" onclick="app.removeTagFromEntity('${tag.id}')">&times;</span>`;
                container.appendChild(chip);
            });
            if (tags.length === 0) {
                container.innerHTML = '<span style="color:var(--text-secondary);font-size:11px">No tags</span>';
            }
        } catch {
            container.innerHTML = '<span style="color:var(--text-secondary);font-size:11px">—</span>';
        }
        this._loadTagSelect();
    }

    async _loadTagSelect() {
        const select = document.getElementById('tag-select');
        select.innerHTML = '<option value="">Add tag…</option>';
        try {
            const tags = await API.listTags();
            tags.forEach(tag => {
                const opt = document.createElement('option');
                opt.value = tag.id;
                opt.textContent = tag.name;
                opt.style.color = tag.color;
                select.appendChild(opt);
            });
        } catch { /* ignore */ }
    }

    async addTagToEntity() {
        const select = document.getElementById('tag-select');
        const tagId = select.value;
        if (!tagId || !this.currentEntity) return;
        try {
            await API.tagEntity(this.currentEntity.id, tagId);
            toast('Tag added', 'success');
            this._loadEntityTags(this.currentEntity.id);
        } catch {
            toast('Failed to add tag', 'error');
        }
    }

    async removeTagFromEntity(tagId) {
        if (!this.currentEntity) return;
        try {
            await API.untagEntity(this.currentEntity.id, tagId);
            toast('Tag removed', 'success');
            this._loadEntityTags(this.currentEntity.id);
        } catch {
            toast('Failed to remove tag', 'error');
        }
    }

    async manageTags() {
        const panel = document.getElementById('analysis-panel');
        panel.classList.add('open');
        const content = document.getElementById('analysis-content');
        content.innerHTML = '<div class="spinner"></div>';
        try {
            const tags = await API.listTags();
            let html = `<h3>🏷️ Manage Tags</h3>
                <div style="display:flex;gap:4px;margin-bottom:12px">
                    <input id="new-tag-name" placeholder="Tag name" style="flex:1;font-size:12px;padding:4px 8px;background:var(--bg-elevated);color:var(--text-primary);border:1px solid var(--border);border-radius:4px">
                    <input id="new-tag-color" type="color" value="#6366f1" style="width:32px;height:28px;padding:0;border:none;cursor:pointer">
                    <button class="btn btn-primary" onclick="app._createTag()" style="font-size:11px;padding:4px 8px">Create</button>
                </div>
                <div id="tag-list">`;
            if (tags.length === 0) {
                html += '<p style="color:var(--text-secondary);font-size:12px">No tags yet. Create one above.</p>';
            } else {
                tags.forEach(tag => {
                    html += `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)">
                        <span style="width:12px;height:12px;border-radius:50%;background:${escapeHtml(tag.color)};flex-shrink:0"></span>
                        <span style="flex:1;font-size:13px">${escapeHtml(tag.name)}</span>
                        <button class="btn btn-secondary" onclick="app._deleteTag('${tag.id}')" style="font-size:10px;padding:2px 6px;color:var(--accent)">Delete</button>
                    </div>`;
                });
            }
            html += '</div>';
            content.innerHTML = html;
        } catch {
            content.innerHTML = '<p style="color:var(--accent)">Failed to load tags</p>';
        }
    }

    async _createTag() {
        const name = document.getElementById('new-tag-name').value.trim();
        const color = document.getElementById('new-tag-color').value;
        if (!name) { toast('Enter a tag name', 'warning'); return; }
        try {
            await API.createTag(name, color);
            toast(`Tag "${name}" created`, 'success');
            this.manageTags();
        } catch {
            toast('Failed to create tag (duplicate name?)', 'error');
        }
    }

    async _deleteTag(tagId) {
        try {
            await API.deleteTag(tagId);
            toast('Tag deleted', 'success');
            this.manageTags();
        } catch {
            toast('Failed to delete tag', 'error');
        }
    }

    // === Data Import ===
    importData() {
        const panel = document.getElementById('analysis-panel');
        panel.classList.add('open');
        const content = document.getElementById('analysis-content');

        const labels = ['Person', 'Organization', 'Account', 'Property', 'Event', 'Document', 'Address'];

        let html = `<h3>📤 Import Data</h3>
            <div style="margin-bottom:16px;padding:12px;background:var(--bg-elevated);border-radius:8px;border:1px solid var(--border)">
                <h4 style="font-size:12px;margin-bottom:8px">JSON Import</h4>
                <p style="font-size:11px;color:var(--text-secondary);margin-bottom:8px">Upload a JSON file with entities and relationships</p>
                <input type="file" id="import-json-file" accept=".json" style="font-size:11px;margin-bottom:8px;display:block">
                <button class="btn btn-primary" onclick="app._uploadJson()" style="font-size:11px;padding:4px 12px">Upload JSON</button>
            </div>
            <div style="padding:12px;background:var(--bg-elevated);border-radius:8px;border:1px solid var(--border)">
                <h4 style="font-size:12px;margin-bottom:8px">CSV Import</h4>
                <p style="font-size:11px;color:var(--text-secondary);margin-bottom:8px">Upload a CSV file for a specific entity type or relationship type</p>
                <div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
                    <select id="import-csv-mode" style="font-size:11px;padding:2px 4px;background:var(--bg-elevated);color:var(--text-primary);border:1px solid var(--border);border-radius:4px" onchange="app._updateCsvTypeOptions()">
                        <option value="entities">Entities</option>
                        <option value="relationships">Relationships</option>
                    </select>
                    <select id="import-csv-type" style="font-size:11px;padding:2px 4px;background:var(--bg-elevated);color:var(--text-primary);border:1px solid var(--border);border-radius:4px;flex:1">`;
        labels.forEach(l => { html += `<option value="${l}">${l}</option>`; });
        html += `</select>
                </div>
                <input type="file" id="import-csv-file" accept=".csv" style="font-size:11px;margin-bottom:8px;display:block">
                <button class="btn btn-primary" onclick="app._uploadCsv()" style="font-size:11px;padding:4px 12px">Upload CSV</button>
            </div>
            <div id="import-results" style="margin-top:12px"></div>`;
        content.innerHTML = html;
    }

    _updateCsvTypeOptions() {
        const mode = document.getElementById('import-csv-mode').value;
        const typeSelect = document.getElementById('import-csv-type');
        typeSelect.innerHTML = '';
        if (mode === 'entities') {
            ['Person', 'Organization', 'Account', 'Property', 'Event', 'Document', 'Address'].forEach(l => {
                typeSelect.innerHTML += `<option value="${l}">${l}</option>`;
            });
        } else {
            ['ASSOCIATED_WITH', 'CONTACTED', 'DIRECTS', 'EMPLOYED_BY', 'LOCATED_AT', 'MENTIONED_IN', 'OWNS', 'PARTICIPATED_IN', 'RELATED_TO', 'SUBSIDIARY_OF', 'TRANSFERRED_TO'].forEach(rt => {
                typeSelect.innerHTML += `<option value="${rt}">${rt.replace(/_/g, ' ')}</option>`;
            });
        }
    }

    async _uploadJson() {
        const fileInput = document.getElementById('import-json-file');
        const file = fileInput?.files?.[0];
        if (!file) { toast('Select a JSON file first', 'warning'); return; }
        const resultsEl = document.getElementById('import-results');
        resultsEl.innerHTML = '<div class="spinner"></div>';
        try {
            const formData = new FormData();
            formData.append('file', file);
            const resp = await fetch('/api/import/json', { method: 'POST', body: formData });
            const data = await resp.json();
            if (!resp.ok) {
                resultsEl.innerHTML = `<p style="color:var(--accent);font-size:12px">Error: ${escapeHtml(data.detail || JSON.stringify(data))}</p>`;
                return;
            }
            this._showImportResults(data, resultsEl);
        } catch {
            resultsEl.innerHTML = '<p style="color:var(--accent);font-size:12px">Upload failed</p>';
        }
    }

    async _uploadCsv() {
        const fileInput = document.getElementById('import-csv-file');
        const file = fileInput?.files?.[0];
        if (!file) { toast('Select a CSV file first', 'warning'); return; }
        const mode = document.getElementById('import-csv-mode').value;
        const type = document.getElementById('import-csv-type').value;
        const resultsEl = document.getElementById('import-results');
        resultsEl.innerHTML = '<div class="spinner"></div>';
        try {
            const formData = new FormData();
            formData.append('file', file);
            const url = mode === 'entities'
                ? `/api/import/csv/entities?label=${type}`
                : `/api/import/csv/relationships?rel_type=${type}`;
            const resp = await fetch(url, { method: 'POST', body: formData });
            const data = await resp.json();
            if (!resp.ok) {
                resultsEl.innerHTML = `<p style="color:var(--accent);font-size:12px">Error: ${escapeHtml(data.detail || JSON.stringify(data))}</p>`;
                return;
            }
            this._showImportResults(data, resultsEl);
        } catch {
            resultsEl.innerHTML = '<p style="color:var(--accent);font-size:12px">Upload failed</p>';
        }
    }

    _showImportResults(data, el) {
        const entities = data.imported_entities ?? 0;
        const rels = data.imported_relationships ?? data.imported ?? 0;
        const entityErrs = data.entity_errors?.length ?? 0;
        const relErrs = data.relationship_errors?.length ?? data.errors?.length ?? 0;
        let html = `<div style="padding:8px;border-radius:6px;background:var(--bg-elevated);border:1px solid var(--border)">
            <p style="font-size:12px;color:var(--text-primary)">✅ Imported: <strong>${entities}</strong> entities, <strong>${rels}</strong> relationships</p>`;
        if (entityErrs > 0 || relErrs > 0) {
            html += `<p style="font-size:11px;color:var(--accent);margin-top:4px">⚠️ ${entityErrs} entity errors, ${relErrs} relationship errors</p>`;
        }
        html += '</div>';
        el.innerHTML = html;
        toast(`Import complete: ${entities} entities, ${rels} relationships`, 'success');
    }

    exportCSV() {
        const panel = document.getElementById('analysis-panel');
        panel.classList.add('open');
        const content = document.getElementById('analysis-content');

        const labels = ['Person', 'Organization', 'Account', 'Property', 'Event', 'Document', 'Address'];
        const relTypes = ['DIRECTS', 'OWNS', 'TRANSFERRED_TO', 'SUBSIDIARY_OF', 'EMPLOYED_BY', 'LOCATED_AT', 'ASSOCIATED_WITH', 'CONTACTED', 'RELATED_TO', 'PARTICIPATED_IN', 'MENTIONED_IN'];

        let html = `<h3>📥 CSV Export</h3>
            <div style="margin-bottom:16px">
                <h4 style="font-size:12px;margin-bottom:8px">Export Entities</h4>
                <div style="display:flex;gap:4px;flex-wrap:wrap">`;
        labels.forEach(label => {
            html += `<button class="btn btn-secondary" style="font-size:11px;padding:4px 8px" onclick="app._downloadCSV('/api/export/entities/csv?label=${label}', '${label.toLowerCase()}.csv')">${label}</button>`;
        });
        html += `</div></div>
            <div>
                <h4 style="font-size:12px;margin-bottom:8px">Export Relationships</h4>
                <div style="display:flex;gap:4px;flex-wrap:wrap">
                    <button class="btn btn-primary" style="font-size:11px;padding:4px 8px" onclick="app._downloadCSV('/api/export/relationships/csv', 'all_relationships.csv')">All Types</button>`;
        relTypes.forEach(rt => {
            html += `<button class="btn btn-secondary" style="font-size:11px;padding:4px 8px" onclick="app._downloadCSV('/api/export/relationships/csv?rel_type=${rt}', '${rt.toLowerCase()}.csv')">${rt.replace(/_/g, ' ')}</button>`;
        });
        html += `</div></div>`;
        content.innerHTML = html;
    }

    async _downloadCSV(url, fallbackName) {
        try {
            const resp = await fetch(url);
            if (!resp.ok) {
                const err = await resp.json();
                toast(err.detail || 'Export failed', 'error');
                return;
            }
            const blob = await resp.blob();
            const disposition = resp.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename="(.+?)"/);
            const filename = match ? match[1] : fallbackName;
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            a.click();
            URL.revokeObjectURL(a.href);
            toast(`Exported: ${filename}`, 'success');
        } catch {
            toast('CSV export failed', 'error');
        }
    }

    closeNLQ() {
        document.getElementById('nlq-modal').classList.remove('open');
    }

    async _runNLQuery(question) {
        if (!question) {
            question = document.getElementById('nlq-input').value.trim();
        }
        if (!question) {
            toast('Enter a question first', 'warning');
            return;
        }

        const resultEl = document.getElementById('nlq-result');
        const errorEl = document.getElementById('nlq-error');
        const cypherEl = document.getElementById('nlq-cypher');
        const contentEl = document.getElementById('nlq-results-content');

        resultEl.style.display = 'none';
        errorEl.style.display = 'none';
        contentEl.innerHTML = '<div class="spinner"></div>';

        toast('Translating to Cypher...', 'info');

        try {
            const data = await API.nlQuery(question);

            if (data.error) {
                errorEl.textContent = data.error;
                errorEl.style.display = 'block';
                if (data.query) {
                    cypherEl.textContent = data.query;
                    resultEl.style.display = 'block';
                }
                return;
            }

            cypherEl.textContent = data.query;
            resultEl.style.display = 'block';

            if (!data.results || data.results.length === 0) {
                contentEl.innerHTML = '<p style="color:var(--text-secondary);font-size:12px">No results found.</p>';
            } else {
                contentEl.innerHTML = '';
                data.results.slice(0, 50).forEach(row => {
                    const div = document.createElement('div');
                    div.className = 'nlq-result-row';
                    Object.entries(row).forEach(([key, val], i) => {
                        if (i > 0) div.appendChild(document.createElement('br'));
                        const keySpan = document.createElement('span');
                        keySpan.className = 'key';
                        keySpan.textContent = key + ':';
                        div.appendChild(keySpan);
                        const display = typeof val === 'object' ? JSON.stringify(val, null, 1) : String(val);
                        div.appendChild(document.createTextNode(' ' + display));
                    });
                    contentEl.appendChild(div);
                });
                toast(`${data.count} results found`, 'success');
            }
        } catch (e) {
            errorEl.textContent = 'Query failed: ' + e.message;
            errorEl.style.display = 'block';
        }
    }
}

// Toast notification helper
function toast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const div = document.createElement('div');
    div.className = `toast ${type}`;
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => div.remove(), 4000);
}

// Initialize
window.app = new RedThreadApp();
document.addEventListener('DOMContentLoaded', () => window.app.init());
