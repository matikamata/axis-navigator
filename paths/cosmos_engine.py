#!/usr/bin/env python3
"""
AXIS-NIDDHI — cosmos_engine.py
AXIS COSMOS — Knowledge Graph Engine V1.0

PURPOSE:
  Visualize canonical knowledge graph.
  Debug semantic relationships.
  Explore concept clusters and canonical constellations.

INVARIANT:
  All knowledge flows through AXIS ÑĀṆA.
  cosmos_engine never reads CSL directly.

PIPELINE:
  ÑĀṆA.to_graph_hint()
    → GraphBuilder.build()
    → CosmosGraph (nodes + edges + clusters + gravity)
    → outputs: cosmos_graph.json, cosmos_clusters.json,
               cosmos_gravity.json, cosmos_paths.json,
               cosmos_visual.html

USAGE:
  python3 cosmos_engine.py build
  python3 cosmos_engine.py stats
  python3 cosmos_engine.py export [--output-dir PATH]
  python3 cosmos_engine.py serve [PORT]
"""

import json
import os
import sys
import http.server
import socketserver
from pathlib import Path
from datetime import datetime, timezone

# ── Resolve paths ─────────────────────────────────────────────────────────────
_SELF = Path(__file__).resolve()

def _resolve_base() -> Path:
    env = os.environ.get("BENG_BASE")
    if env:
        return Path(env)
    for candidate in [_SELF.parent, _SELF.parent.parent,
                      _SELF.parent.parent.parent]:
        if (candidate / "semantic").is_dir():
            return candidate
    return Path.cwd()

BASE = _resolve_base()

# ── Inline graph_builder to avoid path complexity in standalone mode ──────────
# In deployed pipeline: from axis_cosmos.graph_builder import GraphBuilder
_gb_path = _SELF.parent / "graph_builder.py"
if _gb_path.exists():
    import importlib.util
    _spec = importlib.util.spec_from_file_location("graph_builder", _gb_path)
    _mod  = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    GraphBuilder = _mod.GraphBuilder
    CosmosGraph  = _mod.CosmosGraph
else:
    raise ImportError("graph_builder.py not found alongside cosmos_engine.py")


# ── COSMOS Engine ──────────────────────────────────────────────────────────────
class CosmosEngine:
    """
    AXIS COSMOS — orchestrates graph build, analysis, and export.
    Single entry point for all Cosmos operations.
    """

    def __init__(self, output_dir: Path = None):
        self.builder    = GraphBuilder()
        self.output_dir = output_dir or BASE / "axis_cosmos" / "outputs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._graph: CosmosGraph = None

    def build(self) -> CosmosGraph:
        """Build the complete canonical knowledge graph."""
        self._graph = self.builder.build_full_graph()
        return self._graph

    def get_graph(self) -> CosmosGraph:
        if self._graph is None:
            self.build()
        return self._graph

    # ── Export methods ─────────────────────────────────────────────────────────

    def export_graph(self) -> Path:
        """Export cosmos_graph.json — full node/edge/cluster graph."""
        g = self.get_graph()
        ts = datetime.now(timezone.utc).isoformat()
        payload = {
            "generated":  ts,
            "engine":     "AXIS-COSMOS V1.0",
            "invariant":  "All knowledge sourced from AXIS ÑĀṆA",
            **g.to_dict()
        }
        out = self.output_dir / "cosmos_graph.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        return out

    def export_clusters(self) -> Path:
        """Export cosmos_clusters.json — canonical constellations."""
        g = self.get_graph()
        payload = {
            "schema":    "AXIS-COSMOS-CLUSTERS-V1",
            "generated": datetime.now(timezone.utc).isoformat(),
            "clusters":  [c.to_dict() for c in g.clusters],
            "total":     len(g.clusters),
        }
        out = self.output_dir / "cosmos_clusters.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        return out

    def export_gravity(self) -> Path:
        """Export cosmos_gravity.json — gravity scores for all nodes."""
        g = self.get_graph()
        ranked = sorted(g.nodes, key=lambda n: -n.gravity_score)
        payload = {
            "schema":    "AXIS-COSMOS-GRAVITY-V1",
            "generated": datetime.now(timezone.utc).isoformat(),
            "formula":   "gravity = citation_count*0.5 + edge_degree*0.3 + path_frequency*0.2",
            "rankings":  [
                {
                    "rank":              i + 1,
                    "concept_id":        n.concept_id,
                    "label":             n.label,
                    "gravity_score":     n.gravity_score,
                    "citation_count":    n.citation_count,
                    "edge_degree":       n.edge_degree,
                    "path_frequency":    n.path_frequency,
                    "centrality_score":  n.centrality_score,
                    "cluster_id":        n.cluster_id,
                }
                for i, n in enumerate(ranked)
            ],
        }
        out = self.output_dir / "cosmos_gravity.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        return out

    def export_paths(self) -> Path:
        """Export cosmos_paths.json — study path graph annotation."""
        from graph_builder import STUDY_PATHS  # noqa
        g = self.get_graph()
        node_map = {n.concept_id: n for n in g.nodes}

        paths_enriched = {}
        for path_id, seq in STUDY_PATHS.items():
            paths_enriched[path_id] = {
                "sequence": seq,
                "nodes":    [
                    {
                        "concept_id":    s,
                        "label":         node_map[s].label if s in node_map else s,
                        "gravity_score": node_map[s].gravity_score if s in node_map else 0,
                        "cluster_id":    node_map[s].cluster_id if s in node_map else "",
                    }
                    for s in seq
                ],
                "total_gravity": round(
                    sum(node_map[s].gravity_score for s in seq if s in node_map), 3
                ),
            }

        payload = {
            "schema":    "AXIS-COSMOS-PATHS-V1",
            "generated": datetime.now(timezone.utc).isoformat(),
            "paths":     paths_enriched,
        }
        out = self.output_dir / "cosmos_paths.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        return out

    def export_visual(self) -> Path:
        """Export cosmos_visual.html — interactive D3 force graph."""
        g = self.get_graph()
        html = _build_visual_html(g)
        out = self.output_dir / "cosmos_visual.html"
        out.write_text(html, encoding="utf-8")
        return out

    def export_all(self) -> dict[str, Path]:
        """Export all COSMOS outputs."""
        return {
            "graph":    self.export_graph(),
            "clusters": self.export_clusters(),
            "gravity":  self.export_gravity(),
            "paths":    self.export_paths(),
            "visual":   self.export_visual(),
        }

    # ── Stats / debug ──────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return graph statistics for CLI/debug display."""
        g = self.get_graph()
        return g.stats

    def print_stats(self):
        g = self.get_graph()
        s = g.stats
        GRN = "\033[0;32m"; CYN = "\033[0;96m"; NC = "\033[0m"; BOLD = "\033[1m"
        print(f"\n{CYN}{'═'*52}{NC}")
        print(f"{CYN}  💎 AXIS COSMOS — Graph Statistics{NC}")
        print(f"{CYN}{'═'*52}{NC}")
        print(f"  {'Concepts (nodes)':<24} {BOLD}{s['node_count']}{NC}")
        print(f"  {'Edges':<24} {BOLD}{s['edge_count']}{NC}")
        print(f"  {'Clusters':<24} {BOLD}{s['cluster_count']}{NC}")
        print(f"  {'Highest gravity':<24} {BOLD}{s['highest_gravity']}{NC} ({s['highest_gravity_score']})")
        print(f"  {'Average gravity':<24} {s['avg_gravity']}")
        print()
        print(f"  {BOLD}Relation types:{NC}")
        for rt, count in s.get("relation_types", {}).items():
            print(f"    {rt:<20} {count}")
        print()

        ranked = sorted(g.nodes, key=lambda n: -n.gravity_score)
        print(f"  {BOLD}Gravity ranking:{NC}")
        for i, n in enumerate(ranked):
            bar = "█" * int(n.gravity_score * 2)
            print(f"    {i+1:>2}. {n.label:<28} {n.gravity_score:>5.2f}  {GRN}{bar}{NC}")
        print()

        print(f"  {BOLD}Canonical constellations:{NC}")
        for c in g.clusters:
            print(f"    [{c.cluster_id}]")
            print(f"       {c.name}")
            print(f"       members: {', '.join(c.concepts)}")
            print(f"       center:  {c.gravity_center}  gravity: {c.total_gravity}")
        print(f"\n{CYN}{'═'*52}{NC}\n")

    # ── Serve ──────────────────────────────────────────────────────────────────

    def serve(self, port: int = 7777):
        """Serve cosmos_visual.html on localhost."""
        visual = self.output_dir / "cosmos_visual.html"
        if not visual.exists():
            print("Building visual first...")
            self.export_visual()

        os.chdir(self.output_dir)
        handler = http.server.SimpleHTTPRequestHandler

        class QuietHandler(handler):
            def log_message(self, *args): pass

        with socketserver.TCPServer(("", port), QuietHandler) as srv:
            print(f"\n  💎 AXIS COSMOS serving at http://localhost:{port}/cosmos_visual.html")
            print(f"  Ctrl+C to stop\n")
            try:
                srv.serve_forever()
            except KeyboardInterrupt:
                print("\n  Stopped.")


# ── HTML visual builder ────────────────────────────────────────────────────────
def _build_visual_html(g: "CosmosGraph") -> str:
    """Build interactive D3 force-directed graph HTML."""
    nodes_json    = json.dumps([n.to_dict() for n in g.nodes], ensure_ascii=False)
    edges_json    = json.dumps([e.to_dict() for e in g.edges], ensure_ascii=False)
    clusters_json = json.dumps([c.to_dict() for c in g.clusters], ensure_ascii=False)
    stats_json    = json.dumps(g.stats, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AXIS COSMOS — Canonical Knowledge Graph</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Georgia', serif; background: #0d0d0d; color: #e8e4dc; overflow: hidden; }}
#canvas {{ width: 100vw; height: 100vh; }}
svg {{ width: 100%; height: 100%; }}
.node circle {{ stroke-width: 2; cursor: pointer; transition: r 0.2s; }}
.node:hover circle {{ stroke-width: 3; }}
.node text {{ font-size: 11px; fill: #e8e4dc; pointer-events: none; text-anchor: middle; }}
.node text.pali {{ font-style: italic; font-size: 12px; }}
.link {{ stroke-opacity: 0.5; fill: none; }}
.link.causal         {{ stroke: #ef9f27; stroke-width: 2; stroke-dasharray: none; }}
.link.cessation      {{ stroke: #5dcaa5; stroke-width: 2; stroke-dasharray: 4,2; }}
.link.depends_on     {{ stroke: #85b7eb; stroke-width: 1.5; }}
.link.co_occurs      {{ stroke: #b4b2a9; stroke-width: 1; stroke-dasharray: 2,3; }}
.link.path_sequence  {{ stroke: #afa9ec; stroke-width: 2.5; }}
#hud {{ position: fixed; top: 16px; left: 16px; width: 220px; z-index: 10; }}
#hud h1 {{ font-size: 13px; letter-spacing: 3px; text-transform: uppercase;
           color: #5dcaa5; margin-bottom: 8px; font-weight: normal; }}
.stat {{ font-size: 12px; color: #888780; margin: 3px 0; }}
.stat b {{ color: #e8e4dc; }}
#legend {{ position: fixed; bottom: 16px; left: 16px; z-index: 10; }}
#legend h3 {{ font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
              color: #888780; margin-bottom: 6px; font-weight: normal; }}
.leg-item {{ display: flex; align-items: center; gap: 6px; font-size: 11px;
             color: #888780; margin: 3px 0; }}
.leg-line {{ width: 24px; height: 2px; }}
#tooltip {{ position: fixed; padding: 10px 14px; background: rgba(13,13,13,0.95);
            border: 0.5px solid #444; border-radius: 6px; font-size: 12px;
            pointer-events: none; display: none; z-index: 20; max-width: 240px; }}
#tooltip .t-pali {{ font-size: 14px; color: #e8e4dc; font-style: italic; margin-bottom: 4px; }}
#tooltip .t-row  {{ color: #888780; margin: 2px 0; }}
#tooltip .t-row b {{ color: #e8e4dc; }}
#clusters-panel {{ position: fixed; top: 16px; right: 16px; width: 200px; z-index: 10; }}
#clusters-panel h3 {{ font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
                      color: #888780; margin-bottom: 8px; font-weight: normal; }}
.cluster-item {{ margin-bottom: 10px; }}
.cluster-name {{ font-size: 12px; color: #e8e4dc; margin-bottom: 3px; }}
.cluster-members {{ font-size: 11px; color: #888780; font-style: italic; }}
</style>
</head>
<body>
<div id="canvas"><svg id="svg"></svg></div>

<div id="hud">
  <h1>AXIS COSMOS</h1>
  <div class="stat">Corpus: <b>PureDhamma v1</b></div>
  <div class="stat">Concepts: <b id="s-nodes">—</b></div>
  <div class="stat">Edges: <b id="s-edges">—</b></div>
  <div class="stat">Clusters: <b id="s-clusters">—</b></div>
  <div class="stat">Highest gravity: <b id="s-hg">—</b></div>
</div>

<div id="clusters-panel">
  <h3>Constellations</h3>
  <div id="cluster-list"></div>
</div>

<div id="legend">
  <h3>Edge types</h3>
  <div class="leg-item"><div class="leg-line" style="background:#ef9f27"></div> causal</div>
  <div class="leg-item"><div class="leg-line" style="background:#5dcaa5;border-top:2px dashed #5dcaa5;height:0"></div> cessation</div>
  <div class="leg-item"><div class="leg-line" style="background:#85b7eb"></div> depends on</div>
  <div class="leg-item"><div class="leg-line" style="background:#afa9ec"></div> study path</div>
  <div class="leg-item"><div class="leg-line" style="background:#b4b2a9;border-top:2px dotted #b4b2a9;height:0"></div> co-occurs</div>
</div>

<div id="tooltip">
  <div class="t-pali" id="tt-pali"></div>
  <div class="t-row">type: <b id="tt-type"></b></div>
  <div class="t-row">gravity: <b id="tt-gravity"></b></div>
  <div class="t-row">citations: <b id="tt-cites"></b></div>
  <div class="t-row">centrality: <b id="tt-cent"></b></div>
  <div class="t-row">cluster: <b id="tt-cluster"></b></div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const NODES    = {nodes_json};
const EDGES    = {edges_json};
const CLUSTERS = {clusters_json};
const STATS    = {stats_json};

// HUD
document.getElementById('s-nodes').textContent    = STATS.node_count;
document.getElementById('s-edges').textContent    = STATS.edge_count;
document.getElementById('s-clusters').textContent = STATS.cluster_count;
document.getElementById('s-hg').textContent       = STATS.highest_gravity +
  ' (' + STATS.highest_gravity_score + ')';

// Cluster panel
const clusterList = document.getElementById('cluster-list');
CLUSTERS.forEach(c => {{
  clusterList.innerHTML += `<div class="cluster-item">
    <div class="cluster-name">${{c.name}}</div>
    <div class="cluster-members">${{c.concepts.join(' · ')}}</div>
  </div>`;
}});

// Color maps
const TYPE_COLORS = {{
  dhamma_characteristic: '#ef9f27',
  doctrine:              '#85b7eb',
  mental_factor:         '#f0997b',
  practice:              '#5dcaa5',
  attainment:            '#afa9ec',
}};
const CLUSTER_STROKE = {{
  SUFFERING_CLUSTER:     '#ef9f27',
  THREE_MARKS_CLUSTER:   '#85b7eb',
  LIBERATION_CLUSTER:    '#5dcaa5',
}};

const svg   = d3.select('#svg');
const W     = window.innerWidth;
const H     = window.innerHeight;
const g     = svg.append('g');

svg.call(d3.zoom().scaleExtent([0.3, 3])
  .on('zoom', e => g.attr('transform', e.transform)));

// Gravity → radius map
const maxG = d3.max(NODES, d => d.gravity_score) || 1;
const rScale = d3.scaleSqrt().domain([0, maxG]).range([14, 38]);

// Force simulation
const sim = d3.forceSimulation(NODES)
  .force('link', d3.forceLink(EDGES)
    .id(d => d.concept_id)
    .source(d => d.source)
    .target(d => d.target)
    .distance(d => d.relation_type === 'path_sequence' ? 120 : 160)
    .strength(0.4))
  .force('charge', d3.forceManyBody().strength(-400))
  .force('center', d3.forceCenter(W / 2, H / 2))
  .force('collision', d3.forceCollide().radius(d => rScale(d.gravity_score) + 12));

// Edges
const link = g.append('g').selectAll('line')
  .data(EDGES)
  .join('line')
  .attr('class', d => 'link ' + (d.relation_type || 'co_occurs'))
  .attr('stroke-width', d => d.weight * 2);

// Nodes
const node = g.append('g').selectAll('.node')
  .data(NODES)
  .join('g')
  .attr('class', 'node')
  .call(d3.drag()
    .on('start', (e, d) => {{ if (!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
    .on('drag',  (e, d) => {{ d.fx=e.x; d.fy=e.y; }})
    .on('end',   (e, d) => {{ if (!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}));

node.append('circle')
  .attr('r',      d => rScale(d.gravity_score))
  .attr('fill',   d => TYPE_COLORS[d.type] || '#888')
  .attr('fill-opacity', 0.15)
  .attr('stroke', d => CLUSTER_STROKE[d.cluster_id] || TYPE_COLORS[d.type] || '#888')
  .attr('stroke-width', d => d.depth === 0 ? 2.5 : 1.5);

node.append('text')
  .attr('class', 'pali')
  .attr('dy', '-0.3em')
  .text(d => d.label);

node.append('text')
  .attr('dy', '1.1em')
  .attr('font-size', '9px')
  .attr('fill', '#666')
  .text(d => 'g:' + d.gravity_score.toFixed(2));

// Tooltip
const tt = document.getElementById('tooltip');
node.on('mouseover', (e, d) => {{
  document.getElementById('tt-pali').textContent    = d.label;
  document.getElementById('tt-type').textContent    = d.type;
  document.getElementById('tt-gravity').textContent = d.gravity_score;
  document.getElementById('tt-cites').textContent   = d.citation_count;
  document.getElementById('tt-cent').textContent    = d.centrality_score;
  document.getElementById('tt-cluster').textContent = d.cluster_id || '—';
  tt.style.display = 'block';
}}).on('mousemove', e => {{
  tt.style.left = (e.clientX + 14) + 'px';
  tt.style.top  = (e.clientY - 10) + 'px';
}}).on('mouseleave', () => {{ tt.style.display = 'none'; }});

sim.on('tick', () => {{
  link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
  node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
}});
</script>
</body>
</html>"""


# ── CLI ────────────────────────────────────────────────────────────────────────
def _cli():
    GRN = "\033[0;32m"; CYN = "\033[0;96m"; NC = "\033[0m"; BOLD = "\033[1m"
    DIAMOND = "💎"
    args = sys.argv[1:]
    cmd  = args[0] if args else "help"

    engine = CosmosEngine()

    if cmd == "build":
        print(f"\n{CYN}{DIAMOND} AXIS COSMOS — Building canonical graph…{NC}")
        g = engine.build()
        s = g.stats
        print(f"{GRN}  ✅ Graph built{NC}")
        print(f"     nodes={s['node_count']}  edges={s['edge_count']}  "
              f"clusters={s['cluster_count']}  "
              f"highest_gravity={s['highest_gravity']} ({s['highest_gravity_score']})")

    elif cmd == "stats":
        engine.print_stats()

    elif cmd == "export":
        out_dir = BASE / "axis_cosmos" / "outputs"
        if "--output-dir" in args:
            idx = args.index("--output-dir")
            if idx + 1 < len(args):
                out_dir = Path(args[idx + 1])
        engine.output_dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{CYN}{DIAMOND} AXIS COSMOS — Exporting all outputs…{NC}")
        files = engine.export_all()
        for name, path in files.items():
            size = path.stat().st_size
            print(f"  {GRN}✔{NC}  {name:<10} → {path.name}  ({size:,} bytes)")
        print(f"\n  Output dir: {out_dir}\n")

    elif cmd == "serve":
        port = int(args[1]) if len(args) > 1 else 7777
        engine.export_visual()
        engine.serve(port)

    else:
        print(f"\n{BOLD}axis cosmos{NC} — AXIS COSMOS CLI\n")
        print("Commands:")
        print("  cosmos build              Build canonical graph")
        print("  cosmos stats              Graph statistics + gravity ranking")
        print("  cosmos export             Export all JSON + HTML outputs")
        print("  cosmos serve [PORT]       Serve interactive graph (default 7777)")
        print()


if __name__ == "__main__":
    _cli()
