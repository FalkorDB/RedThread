/** RedThread — API Client */

const API = {
    base: '',

    async get(path) {
        const res = await fetch(`${this.base}${path}`);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    },

    async post(path, data) {
        const res = await fetch(`${this.base}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    },

    async del(path) {
        const res = await fetch(`${this.base}${path}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    },

    // Entities
    getEntity: (id) => API.get(`/api/entities/${id}`),
    searchEntities: (q) => API.get(`/api/entities/?q=${encodeURIComponent(q)}`),
    listEntities: (label, skip = 0, limit = 50) =>
        API.get(`/api/entities/?label=${label}&skip=${skip}&limit=${limit}`),
    getNeighborhood: (id, depth = 1, limit = 50) =>
        API.get(`/api/entities/${id}/neighborhood?depth=${depth}&limit=${limit}`),
    getRelationships: (id) =>
        API.get(`/api/entities/${id}/relationships`),
    createEntity: (label, data) => API.post(`/api/entities/${label}`, data),
    deleteEntity: (label, id) => API.del(`/api/entities/${label}/${id}`),

    // Relationships
    createRelationship: (data) => API.post('/api/relationships/', data),

    // Analysis
    findPaths: (src, tgt, maxDepth = 6) =>
        API.get(`/api/analysis/paths?source=${src}&target=${tgt}&max_depth=${maxDepth}`),
    shortestPath: (src, tgt) =>
        API.get(`/api/analysis/shortest-path?source=${src}&target=${tgt}`),
    moneyFlow: (src, tgt = null) => {
        let url = `/api/analysis/money-flow?source=${src}`;
        if (tgt) url += `&target=${tgt}`;
        return API.get(url);
    },
    entityReach: (id, depth = 3) =>
        API.get(`/api/analysis/reach?entity_id=${id}&max_depth=${depth}`),
    detectPatterns: () => API.get('/api/analysis/patterns'),
    circularFlows: () => API.get('/api/analysis/patterns/circular-flows'),
    shellCompanies: () => API.get('/api/analysis/patterns/shell-companies'),
    structuring: () => API.get('/api/analysis/patterns/structuring'),
    passthrough: () => API.get('/api/analysis/patterns/passthrough'),
    hiddenConnections: (e1, e2) =>
        API.get(`/api/analysis/patterns/hidden-connections?entity1=${e1}&entity2=${e2}`),
    computeRisk: (id) => API.get(`/api/analysis/risk/${id}`),
    highestRisk: () => API.get('/api/analysis/risk'),
    centrality: () => API.get('/api/analysis/centrality'),
    bridges: () => API.get('/api/analysis/bridges'),
    sharedConnections: (e1, e2) =>
        API.get(`/api/analysis/shared-connections?entity1=${e1}&entity2=${e2}`),
    validateGraph: () => API.get('/api/analysis/validate'),
    recomputeRisk: () => API.post('/api/analysis/risk/recompute', {}),
    timeline: (id) => API.get(`/api/analysis/timeline/${id}`),
    stats: () => API.get('/api/analysis/stats'),

    // Investigations
    listInvestigations: () => API.get('/api/investigations/'),
    createInvestigation: (data) => API.post('/api/investigations/', data),
    getInvestigation: (id) => API.get(`/api/investigations/${id}`),
    addEntityToInvestigation: (invId, entityId, label) =>
        API.post(`/api/investigations/${invId}/entities?entity_id=${entityId}&entity_label=${label}`, {}),

    // Export
    exportSubgraph: (id, depth = 2) =>
        API.get(`/api/export/subgraph?entity_id=${id}&depth=${depth}`),
    generateReport: (id) => API.get(`/api/export/report?entity_id=${id}`),

    // Temporal
    graphAtTime: (date, entityId = null) => {
        let url = `/api/temporal/graph-at?date=${encodeURIComponent(date)}`;
        if (entityId) url += `&entity_id=${encodeURIComponent(entityId)}`;
        return API.get(url);
    },
    temporalChanges: (start, end) =>
        API.get(`/api/temporal/changes?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`),
    temporalTimeline: () => API.get('/api/temporal/timeline'),
    temporalDateRange: () => API.get('/api/temporal/date-range'),
    entityTemporalProfile: (id) => API.get(`/api/temporal/entity/${encodeURIComponent(id)}`),

    // Snapshots & Diff
    createSnapshot: (investigationId, name) =>
        API.post(`/api/snapshots/?investigation_id=${encodeURIComponent(investigationId)}&name=${encodeURIComponent(name)}`, {}),
    listSnapshots: (investigationId = null) => {
        let url = '/api/snapshots/';
        if (investigationId) url += `?investigation_id=${encodeURIComponent(investigationId)}`;
        return API.get(url);
    },
    diffSnapshots: (a, b) =>
        API.get(`/api/snapshots/diff/compare?snapshot_a=${encodeURIComponent(a)}&snapshot_b=${encodeURIComponent(b)}`),
    diffCurrent: (snapshotId) =>
        API.get(`/api/snapshots/diff/current?snapshot_id=${encodeURIComponent(snapshotId)}`),

    // Natural Language Query
    nlQuery: (question) => API.post('/api/nlq/query', { question }),
    nlTranslate: (question) => API.post('/api/nlq/translate', { question }),
    nlExamples: () => API.get('/api/nlq/examples'),
};
