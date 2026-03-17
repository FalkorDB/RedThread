/** RedThread — Graph Visualization with vis-network */

const NODE_COLORS = {
    Person: '#3b82f6',
    Organization: '#8b5cf6',
    Account: '#22c55e',
    Property: '#f59e0b',
    Event: '#ef4444',
    Document: '#06b6d4',
    Address: '#64748b',
};

const NODE_SHAPES = {
    Person: 'dot',
    Organization: 'diamond',
    Account: 'square',
    Property: 'triangle',
    Event: 'star',
    Document: 'box',
    Address: 'hexagon',
};

const EDGE_COLORS = {
    OWNS: '#22c55e',
    DIRECTS: '#8b5cf6',
    EMPLOYED_BY: '#3b82f6',
    TRANSFERRED_TO: '#ef4444',
    LOCATED_AT: '#64748b',
    CONTACTED: '#f59e0b',
    RELATED_TO: '#06b6d4',
    PARTICIPATED_IN: '#f97316',
    MENTIONED_IN: '#a78bfa',
    SUBSIDIARY_OF: '#ec4899',
    ASSOCIATED_WITH: '#94a3b8',
};

class GraphViz {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.nodes = new vis.DataSet();
        this.edges = new vis.DataSet();
        this.network = null;
        this.selectedNode = null;
        this.highlightedPaths = new Set();
        this._init();
    }

    _init() {
        const options = {
            nodes: {
                font: { color: '#f1f5f9', size: 12, face: 'Inter, system-ui' },
                borderWidth: 2,
                shadow: { enabled: true, color: 'rgba(0,0,0,0.3)', size: 8 },
                scaling: { min: 15, max: 40, label: { enabled: true, min: 10, max: 14 } },
            },
            edges: {
                font: { color: '#94a3b8', size: 9, face: 'Inter, system-ui', align: 'middle' },
                arrows: { to: { enabled: true, scaleFactor: 0.7 } },
                smooth: { type: 'curvedCW', roundness: 0.15 },
                width: 1.5,
                hoverWidth: 3,
            },
            physics: {
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -60,
                    centralGravity: 0.005,
                    springLength: 150,
                    springConstant: 0.04,
                    damping: 0.4,
                },
                stabilization: { iterations: 150, fit: true },
            },
            interaction: {
                hover: true,
                multiselect: true,
                navigationButtons: false,
                keyboard: { enabled: true },
            },
            layout: { improvedLayout: true },
        };

        this.network = new vis.Network(
            this.container,
            { nodes: this.nodes, edges: this.edges },
            options
        );

        this.network.on('click', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                this.selectedNode = nodeId;
                if (window.app) window.app.onNodeSelect(nodeId);
            } else {
                this.selectedNode = null;
                if (window.app) window.app.onNodeDeselect();
            }
        });

        this.network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                if (window.app) window.app.expandNode(nodeId);
            }
        });
    }

    addNode(entity) {
        const id = entity.id;
        if (this.nodes.get(id)) return;

        const label = entity.label || 'Unknown';
        const displayName = entity.name || entity.account_number ||
            entity.full_address || entity.description || entity.title || id;
        const risk = entity.risk_score || 0;

        let borderColor = NODE_COLORS[label] || '#64748b';
        if (risk >= 60) borderColor = '#ef4444';
        else if (risk >= 30) borderColor = '#f59e0b';

        this.nodes.add({
            id,
            label: displayName.substring(0, 25),
            title: `${label}: ${displayName}\nRisk: ${risk}`,
            color: {
                background: NODE_COLORS[label] || '#64748b',
                border: borderColor,
                highlight: { background: '#ef4444', border: '#dc2626' },
                hover: { background: NODE_COLORS[label] || '#64748b', border: '#f1f5f9' },
            },
            shape: NODE_SHAPES[label] || 'dot',
            size: Math.max(15, Math.min(35, 15 + risk / 5)),
            _data: entity,
        });
    }

    addEdge(edge) {
        const edgeId = `${edge.source}-${edge.rel_type}-${edge.target}`;
        if (this.edges.get(edgeId)) return;

        const isTransfer = edge.rel_type === 'TRANSFERRED_TO';
        const amount = edge.properties?.amount;
        let edgeLabel = edge.rel_type.replace(/_/g, ' ');
        if (isTransfer && amount) {
            edgeLabel = `$${Number(amount).toLocaleString()}`;
        }

        this.edges.add({
            id: edgeId,
            from: edge.source,
            to: edge.target,
            label: edgeLabel,
            color: {
                color: EDGE_COLORS[edge.rel_type] || '#94a3b8',
                highlight: '#ef4444',
                hover: '#f1f5f9',
            },
            width: isTransfer ? Math.max(1.5, Math.min(5, Math.log10(amount || 1))) : 1.5,
            dashes: edge.rel_type === 'ASSOCIATED_WITH' ? [5, 5] : false,
            _data: edge,
        });
    }

    loadNeighborhood(data) {
        if (!data || !data.nodes) return;
        data.nodes.forEach(n => this.addNode(n));
        (data.edges || []).forEach(e => this.addEdge(e));
        this.network.fit({ animation: true });
    }

    highlightPath(pathData) {
        if (!pathData || !pathData.nodes) return;

        // Add path nodes and edges
        pathData.nodes.forEach(n => this.addNode(n));
        pathData.edges.forEach(e => this.addEdge(e));

        // Highlight path nodes
        const pathNodeIds = pathData.nodes.map(n => n.id);
        pathNodeIds.forEach(id => {
            const node = this.nodes.get(id);
            if (node) {
                this.nodes.update({
                    id,
                    borderWidth: 4,
                    color: { ...node.color, border: '#ef4444' },
                });
                this.highlightedPaths.add(id);
            }
        });

        this.network.fit({ nodes: pathNodeIds, animation: true });
    }

    clearHighlights() {
        this.highlightedPaths.forEach(id => {
            const node = this.nodes.get(id);
            if (node && node._data) {
                const label = node._data.label || 'Unknown';
                this.nodes.update({
                    id,
                    borderWidth: 2,
                    color: { ...node.color, border: NODE_COLORS[label] || '#64748b' },
                });
            }
        });
        this.highlightedPaths.clear();
    }

    clear() {
        this.nodes.clear();
        this.edges.clear();
        this.highlightedPaths.clear();
    }

    fitView() {
        this.network.fit({ animation: true });
    }

    getNodeIds() {
        return this.nodes.getIds();
    }

    getNodeData(id) {
        const node = this.nodes.get(id);
        return node ? node._data : null;
    }
}
