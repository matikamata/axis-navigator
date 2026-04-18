#!/usr/bin/env python3
"""
AXIS-NIDDHI — graph_builder.py
AXIS COSMOS — Graph Builder V1.0

Consumes ÑĀṆA.to_graph_hint() output and constructs enriched
canonical knowledge graphs with gravity scores, centrality,
cluster detection, and multi-layer annotation.

INVARIANT: All input must come from ÑĀṆA. Never read CSL directly.

GRAVITY FORMULA:
  gravity_score = citation_count * 0.5
                + edge_degree    * 0.3
                + path_frequency * 0.2
"""

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Canonical relation type matrix ────────────────────────────────────────────
# Derived from PureDhamma corpus structure and paticca samuppada chain
RELATION_TYPES = {
    # Causal chain (paticca samuppada sequence)
    ("avijja",            "sankhara"):         "causal",
    ("sankhara",          "tanha"):            "causal",
    ("tanha",             "dukkha"):           "causal",
    ("avijja",            "dukkha"):           "causal",
    ("avijja",            "paticca_samuppada"):"depends_on",
    ("tanha",             "paticca_samuppada"):"depends_on",

    # Cessation chain
    ("magga",             "nibbana"):          "cessation",
    ("magga",             "tanha"):            "cessation",
    ("phala",             "nibbana"):          "cessation",

    # Three marks dependencies
    ("tilakkhana",        "anicca"):           "depends_on",
    ("tilakkhana",        "dukkha"):           "depends_on",
    ("tilakkhana",        "anatta"):           "depends_on",

    # Co-occurrence clusters
    ("dukkha",            "anicca"):           "co_occurs",
    ("dukkha",            "anatta"):           "co_occurs",
    ("anicca",            "anatta"):           "co_occurs",
    ("avijja",            "tanha"):            "co_occurs",
    ("sankhara",          "avijja"):           "co_occurs",
}

# Canonical study path sequences
STUDY_PATHS = {
    "BEGINNER_PATH":              ["dukkha", "anicca", "anatta", "tilakkhana"],
    "DEPENDENT_ORIGINATION_PATH": ["avijja", "sankhara", "tanha", "paticca_samuppada"],
    "LIBERATION_PATH":            ["magga", "phala", "nibbana"],
}

# Canonical citation density (CSL occurrences per concept — from semantic layer)
CITATION_DENSITY = {
    "dukkha":            6,
    "anicca":            7,
    "anatta":            7,
    "tilakkhana":        6,
    "avijja":            5,
    "sankhara":          7,
    "tanha":             6,
    "paticca_samuppada": 8,
    "magga":             6,
    "phala":             3,
    "nibbana":           6,
}


@dataclass
class CosmosNode:
    concept_id:       str
    label:            str
    type_:            str
    depth:            int
    citation_count:   int   = 0
    edge_degree:      int   = 0
    path_frequency:   int   = 0
    centrality_score: float = 0.0
    gravity_score:    float = 0.0
    cluster_id:       str   = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = d.pop("type_")
        return d


@dataclass
class CosmosEdge:
    source:        str
    target:        str
    relation_type: str  = "co_occurs"
    weight:        float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CosmosCluster:
    cluster_id:     str
    name:           str
    concepts:       list[str]
    gravity_center: str   = ""
    total_gravity:  float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CosmosGraph:
    schema:   str = "AXIS-COSMOS-GRAPH-V1"
    nodes:    list[CosmosNode]  = field(default_factory=list)
    edges:    list[CosmosEdge]  = field(default_factory=list)
    clusters: list[CosmosCluster] = field(default_factory=list)
    stats:    dict              = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema":   self.schema,
            "nodes":    [n.to_dict() for n in self.nodes],
            "edges":    [e.to_dict() for e in self.edges],
            "clusters": [c.to_dict() for c in self.clusters],
            "stats":    self.stats,
        }


class GraphBuilder:
    """
    Builds enriched COSMOS graph from ÑĀṆA graph_hint output.

    INVARIANT: Input must come exclusively from ÑĀṆA.to_graph_hint().
    This class never accesses CSL or semantic/concepts/ directly.
    """

    def __init__(self):
        self._path_index: dict[str, int] = self._build_path_index()

    def _build_path_index(self) -> dict[str, int]:
        """Count how many study paths include each concept."""
        idx: dict[str, int] = defaultdict(int)
        for path_seq in STUDY_PATHS.values():
            for slug in path_seq:
                idx[slug] += 1
        return dict(idx)

    def build(self, graph_hint: dict) -> CosmosGraph:
        """
        Build a full CosmosGraph from ÑĀṆA graph_hint.

        Args:
            graph_hint: dict from NanaResponse.to_graph_hint()

        Returns:
            CosmosGraph with gravity, centrality, clusters
        """
        raw_nodes = graph_hint.get("nodes", [])
        raw_edges = graph_hint.get("edges", [])

        # 1. Build edge degree map
        degree: dict[str, int] = defaultdict(int)
        for e in raw_edges:
            degree[e["from"]] += 1
            degree[e["to"]]   += 1

        # 2. Build CosmosNodes
        nodes: list[CosmosNode] = []
        for n in raw_nodes:
            slug  = n["id"]
            cites = CITATION_DENSITY.get(slug, n.get("citation_count", 2))
            deg   = degree[slug]
            pfreq = self._path_index.get(slug, 0)

            gravity = round(
                cites * 0.5 + deg * 0.3 + pfreq * 0.2, 3
            )
            nodes.append(CosmosNode(
                concept_id     = slug,
                label          = n.get("label", slug),
                type_          = n.get("type", ""),
                depth          = n.get("depth", 0),
                citation_count = cites,
                edge_degree    = deg,
                path_frequency = pfreq,
                gravity_score  = gravity,
            ))

        # 3. Compute centrality (normalized degree)
        max_deg = max((n.edge_degree for n in nodes), default=1)
        for n in nodes:
            n.centrality_score = round(n.edge_degree / max(max_deg, 1), 3)

        # 4. Build CosmosEdges with canonical relation types
        edges: list[CosmosEdge] = []
        seen_edges: set[tuple] = set()
        for e in raw_edges:
            src, tgt = e["from"], e["to"]
            key = (src, tgt)
            if key in seen_edges:
                continue
            seen_edges.add(key)

            rtype = (
                RELATION_TYPES.get((src, tgt)) or
                RELATION_TYPES.get((tgt, src)) or
                "co_occurs"
            )
            w = e.get("weight", 1.0)
            edges.append(CosmosEdge(source=src, target=tgt,
                                    relation_type=rtype, weight=w))

        # 5. Inject path_sequence edges from study paths
        node_ids = {n.concept_id for n in nodes}
        for path_id, seq in STUDY_PATHS.items():
            for i in range(len(seq) - 1):
                s, t = seq[i], seq[i+1]
                if s in node_ids and t in node_ids:
                    key = (s, t)
                    if key not in seen_edges:
                        seen_edges.add(key)
                        edges.append(CosmosEdge(
                            source=s, target=t,
                            relation_type="path_sequence", weight=0.8
                        ))

        # 6. Cluster detection — canonical constellations
        clusters = self._detect_clusters(nodes, edges)

        # 7. Assign cluster_id to nodes
        node_map = {n.concept_id: n for n in nodes}
        for cluster in clusters:
            for slug in cluster.concepts:
                if slug in node_map:
                    node_map[slug].cluster_id = cluster.cluster_id

        # 8. Stats
        gravity_sorted = sorted(nodes, key=lambda n: -n.gravity_score)
        stats = {
            "node_count":      len(nodes),
            "edge_count":      len(edges),
            "cluster_count":   len(clusters),
            "highest_gravity": gravity_sorted[0].concept_id if gravity_sorted else "",
            "highest_gravity_score": gravity_sorted[0].gravity_score if gravity_sorted else 0,
            "avg_gravity":     round(sum(n.gravity_score for n in nodes) / max(len(nodes),1), 3),
            "relation_types":  dict(
                sorted(
                    {rt: sum(1 for e in edges if e.relation_type == rt)
                     for rt in set(e.relation_type for e in edges)}.items()
                )
            ),
        }

        return CosmosGraph(nodes=nodes, edges=edges, clusters=clusters, stats=stats)

    def _detect_clusters(self, nodes: list[CosmosNode],
                         edges: list[CosmosEdge]) -> list[CosmosCluster]:
        """
        Detect canonical constellations — concept groups with structural cohesion.
        Uses predefined canonical cluster seeds + graph expansion.
        """
        node_ids = {n.concept_id for n in nodes}
        node_map = {n.concept_id: n for n in nodes}

        # Build adjacency
        adj: dict[str, set[str]] = defaultdict(set)
        for e in edges:
            adj[e.source].add(e.target)
            adj[e.target].add(e.source)

        # Canonical constellation seeds — from corpus analysis
        CONSTELLATION_SEEDS = [
            {
                "id":       "SUFFERING_CLUSTER",
                "name":     "Origin of Suffering",
                "seeds":    {"avijja", "sankhara", "tanha", "dukkha"},
            },
            {
                "id":       "THREE_MARKS_CLUSTER",
                "name":     "Three Marks of Existence",
                "seeds":    {"anicca", "anatta", "dukkha", "tilakkhana"},
            },
            {
                "id":       "LIBERATION_CLUSTER",
                "name":     "Liberation Sequence",
                "seeds":    {"magga", "phala", "nibbana"},
            },
        ]

        clusters: list[CosmosCluster] = []
        assigned: set[str] = set()

        for seed_def in CONSTELLATION_SEEDS:
            # Only include seeds present in current graph
            members = seed_def["seeds"] & node_ids
            if len(members) < 2:
                continue

            # Expand: add neighbors with ≥2 connections into cluster
            candidates = set(members)
            for slug in list(members):
                for neighbor in adj.get(slug, set()):
                    if neighbor not in assigned and neighbor in node_ids:
                        connections_to_cluster = sum(
                            1 for m in members if m in adj.get(neighbor, set())
                        )
                        if connections_to_cluster >= 2:
                            candidates.add(neighbor)

            # Remove already-assigned (prefer first cluster)
            final = candidates - assigned
            if not final:
                continue

            assigned |= final

            # Gravity center = highest gravity node in cluster
            gravity_center = max(
                (slug for slug in final if slug in node_map),
                key=lambda s: node_map[s].gravity_score,
                default=""
            )
            total_g = round(sum(node_map[s].gravity_score for s in final
                                if s in node_map), 3)

            clusters.append(CosmosCluster(
                cluster_id     = seed_def["id"],
                name           = seed_def["name"],
                concepts       = sorted(final),
                gravity_center = gravity_center,
                total_gravity  = total_g,
            ))

        return clusters

    def build_full_graph(self) -> CosmosGraph:
        """
        Build the complete 11-concept canonical graph.
        Calls ÑĀṆA conceptually for all 11 canonical concepts.
        In production: call NanaEngine.ask('all concepts', 'concept_map').to_graph_hint()
        """
        ALL_CONCEPTS = [
            {"id": "dukkha",            "label": "Dukkha",              "type": "dhamma_characteristic", "depth": 0},
            {"id": "anicca",            "label": "Anicca",              "type": "dhamma_characteristic", "depth": 0},
            {"id": "anatta",            "label": "Anattā",              "type": "dhamma_characteristic", "depth": 0},
            {"id": "tilakkhana",        "label": "Tilakkhaṇa",          "type": "doctrine",              "depth": 1},
            {"id": "avijja",            "label": "Avijjā",              "type": "mental_factor",         "depth": 0},
            {"id": "sankhara",          "label": "Saṅkhāra",            "type": "doctrine",              "depth": 1},
            {"id": "tanha",             "label": "Taṇhā",               "type": "mental_factor",         "depth": 0},
            {"id": "paticca_samuppada", "label": "Paṭicca Samuppāda",   "type": "doctrine",              "depth": 1},
            {"id": "magga",             "label": "Ariya Aṭṭhaṅgika Magga","type": "practice",            "depth": 1},
            {"id": "phala",             "label": "Phala",               "type": "attainment",            "depth": 2},
            {"id": "nibbana",           "label": "Nibbāna",             "type": "attainment",            "depth": 2},
        ]
        ALL_EDGES = [
            # Three marks
            {"from": "tilakkhana",        "to": "anicca",            "weight": 1.0},
            {"from": "tilakkhana",        "to": "dukkha",            "weight": 1.0},
            {"from": "tilakkhana",        "to": "anatta",            "weight": 1.0},
            {"from": "dukkha",            "to": "anicca",            "weight": 0.9},
            {"from": "dukkha",            "to": "anatta",            "weight": 0.9},
            {"from": "anicca",            "to": "anatta",            "weight": 0.8},
            # Causal chain
            {"from": "avijja",            "to": "sankhara",          "weight": 1.0},
            {"from": "avijja",            "to": "tanha",             "weight": 0.9},
            {"from": "avijja",            "to": "paticca_samuppada", "weight": 1.0},
            {"from": "sankhara",          "to": "tanha",             "weight": 0.8},
            {"from": "tanha",             "to": "dukkha",            "weight": 1.0},
            {"from": "tanha",             "to": "paticca_samuppada", "weight": 0.9},
            # Liberation
            {"from": "magga",             "to": "nibbana",           "weight": 1.0},
            {"from": "magga",             "to": "phala",             "weight": 1.0},
            {"from": "phala",             "to": "nibbana",           "weight": 1.0},
            {"from": "magga",             "to": "dukkha",            "weight": 0.7},
            # Cross-links
            {"from": "paticca_samuppada", "to": "dukkha",            "weight": 0.8},
            {"from": "paticca_samuppada", "to": "tanha",             "weight": 0.8},
            {"from": "nibbana",           "to": "tilakkhana",        "weight": 0.6},
            {"from": "avijja",            "to": "dukkha",            "weight": 0.8},
        ]
        hint = {
            "schema":    "AXIS-COSMOS-GRAPH-V1",
            "nodes":     ALL_CONCEPTS,
            "edges":     ALL_EDGES,
            "citations": [],
            "confidence": 1.0,
        }
        return self.build(hint)
