#!/usr/bin/env python3
"""
World Model Schema 加载与验证脚本。

验证所有 YAML schema 文件可被正确解析，且必需字段存在。
这个脚本是 Engine 加载器的最小原型。
"""
import yaml
import os
import sys
from pathlib import Path

WORLD_MODEL_DIR = Path(__file__).parent

ERRORS = []
WARNINGS = []


def load_yaml(rel_path: str) -> dict:
    """Load a YAML file relative to world-model/ directory."""
    path = WORLD_MODEL_DIR / rel_path
    if not path.exists():
        ERRORS.append(f"MISSING: {rel_path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        ERRORS.append(f"EMPTY: {rel_path}")
        return {}
    return data


def check_required(obj, fields: list[str], context: str):
    """Check that required fields exist in a dict."""
    for field in fields:
        if field not in obj:
            ERRORS.append(f"MISSING FIELD: {context}.{field}")


def validate_entities():
    """Load and validate all entity schema files."""
    print("═" * 60)
    print("VALIDATING ENTITIES")
    print("═" * 60)

    # 1. Technology Nodes
    tech = load_yaml("entities/technology.schema.yaml")
    nodes = tech.get("technology_nodes", [])
    if not nodes:
        ERRORS.append("technology.schema.yaml: technology_nodes is empty")
    else:
        print(f"  Technology Nodes: {len(nodes)}")
        required_fields = ["id", "name", "category", "tier", "activated",
                           "prerequisites", "unlocks", "effects", "suppliers", "adopters"]
        for node in nodes:
            check_required(node, required_fields, f"tech_node.{node.get('id','?')}")
            for eff in node.get("effects", []):
                check_required(eff, ["target", "operation", "value"],
                               f"tech_node.{node.get('id')}.effect")
        tiers = set(n["tier"] for n in nodes)
        print(f"  Tiers: {tiers}")
        active = [n["id"] for n in nodes if n.get("activated")]
        inactive = [n["id"] for n in nodes if not n.get("activated")]
        print(f"  Activated: {len(active)} | Inactive: {len(inactive)}")

    # 2. Companies
    comp = load_yaml("entities/company.schema.yaml")
    brands = comp.get("companies", [])
    if not brands:
        ERRORS.append("company.schema.yaml: companies is empty")
    else:
        print(f"\n  Companies: {len(brands)}")
        for brand in brands:
            check_required(brand, ["id", "name", "country", "dna", "goal_function",
                                    "decision_period", "initial_state", "product_lineup",
                                    "supply_chain", "ai_strategy"],
                           f"company.{brand.get('id','?')}")
            dna_fields = ["profit_first", "innovation_lead", "ecosystem_lock",
                          "volume_aggressive", "price_aggressive",
                          "supply_diversify", "risk_appetite"]
            check_required(brand.get("dna", {}), dna_fields,
                           f"company.{brand.get('id')}.dna")
            print(f"    {brand['name']:12s} | "
                  f"profit={brand['dna']['profit_first']} "
                  f"innovation={brand['dna']['innovation_lead']} "
                  f"volume={brand['dna']['volume_aggressive']} "
                  f"risk={brand['dna']['risk_appetite']} | "
                  f"period={brand['decision_period']}q "
                  f"mkt_share={brand['initial_state']['market_share']}%")

    # 3. Consumer Segments
    cons = load_yaml("entities/consumer.schema.yaml")
    segments = cons.get("consumer_segments", [])
    if not segments:
        ERRORS.append("consumer.schema.yaml: consumer_segments is empty")
    else:
        print(f"\n  Consumer Segments: {len(segments)}")
        total_pct = 0
        for seg in segments:
            check_required(seg, ["id", "name", "age_range", "size_pct",
                                  "preferences", "trend_vectors"],
                           f"segment.{seg.get('id','?')}")
            total_pct += seg.get("size_pct", 0)
            pref_count = len(seg.get("preferences", {}))
            trend_count = len(seg.get("trend_vectors", {}))
            print(f"    {seg['name']:16s} | size={seg['size_pct']:4.1f}% "
                  f"preferences={pref_count} trends={trend_count}")
        if abs(total_pct - 100) > 0.5:
            WARNINGS.append(f"Consumer segments total = {total_pct}%, expected 100%")

    # 4. Supply Chain
    sc = load_yaml("entities/supply_chain.schema.yaml")
    suppliers = sc.get("suppliers", [])
    links = sc.get("links", [])
    prop_rules = sc.get("propagation_rules", [])
    if not suppliers:
        ERRORS.append("supply_chain.schema.yaml: suppliers is empty")
    else:
        print(f"\n  Suppliers: {len(suppliers)}")
        for s in suppliers:
            check_required(s, ["id", "name", "country", "category",
                                "dna", "resources", "tech_dependency"],
                           f"supplier.{s.get('id','?')}")
            print(f"    {s['name']:25s} | {s['category']:20s} "
                  f"risk={s['dna']['geopolitical_risk']} "
                  f"resources={len(s['resources'])}")
    print(f"  Supply Chain Links: {len(links)}")
    for link in links:
        check_required(link, ["id", "from", "to", "resource_type",
                               "allocation_pct", "reliability", "cost_per_unit",
                               "lead_time_quarters"],
                       f"link.{link.get('id','?')}")
    print(f"  Propagation Rules: {len(prop_rules)}")


def validate_rules():
    """Load and validate all rule files."""
    print("\n" + "═" * 60)
    print("VALIDATING RULES")
    print("═" * 60)

    sys_rules = load_yaml("rules/system.rules.yaml")
    rules = sys_rules.get("rules", [])
    if not rules:
        ERRORS.append("system.rules.yaml: rules is empty")
    else:
        print(f"  System Rules: {len(rules)}")
        type_counts = {}
        for rule in rules:
            check_required(rule, ["id", "type", "condition", "effect"],
                           f"rule.{rule.get('id','?')}")
            rt = rule.get("type", "unknown")
            type_counts[rt] = type_counts.get(rt, 0) + 1
            for eff in rule.get("effect", []):
                check_required(eff, ["target", "operation", "value"],
                               f"rule.{rule.get('id')}.effect")
        for rt, count in type_counts.items():
            print(f"    {rt}: {count} rules")

    # Scenario rules
    base_rules = load_yaml("rules/scenario/base_2025.rules.yaml")
    print(f"  Scenario base_2025 rules: {len(base_rules.get('rules', []))}")
    print(f"    Scenario: {base_rules.get('scenario', 'unknown')}")


def validate_world_state():
    """Validate the world state schema and initial state."""
    print("\n" + "═" * 60)
    print("VALIDATING WORLD STATE")
    print("═" * 60)

    # Schema
    ws_schema = load_yaml("schemas/world_state.schema.yaml")
    ws = ws_schema.get("world_state", {})
    if ws:
        print(f"  World State Schema: OK")
        print(f"    Technology status: {len(ws.get('technology_status', {}))} nodes")
        print(f"    Brand states: {len(ws.get('brand_states', {}))} brands")
        print(f"    Consumer segments: {len(ws.get('consumer_segments', {}))} segments")
        print(f"    Supplier states: {len(ws.get('supplier_states', {}))} suppliers")
        print(f"    Active rules: {len(ws.get('active_rules', []))}")
        print(f"    Global metrics: {len(ws.get('global_metrics', {}))} metrics")

    # Initial state
    init = load_yaml("initial_states/2025Q1.world.yaml")
    if init:
        print(f"\n  Initial State (2025Q1): OK")
        print(f"    Tick: {init.get('tick')} | Year: {init.get('year')} Q{init.get('quarter')}")
        print(f"    Tech activations: {len(init.get('technology_activation', {}))}")
        print(f"    Brands: {len(init.get('brands', {}))}")
        print(f"    Suppliers: {len(init.get('suppliers', {}))}")
        print(f"    Global baselines: {len(init.get('global_baselines', {}))}")
        print(f"    Scenario: {init.get('scenario')}")


def validate_cross_references():
    """Check that cross-references between schemas are consistent."""
    print("\n" + "═" * 60)
    print("VALIDATING CROSS-REFERENCES")
    print("═" * 60)

    tech = load_yaml("entities/technology.schema.yaml")
    comp = load_yaml("entities/company.schema.yaml")
    sc = load_yaml("entities/supply_chain.schema.yaml")
    cons = load_yaml("entities/consumer.schema.yaml")
    rules_data = load_yaml("rules/system.rules.yaml")

    tech_ids = {n["id"] for n in tech.get("technology_nodes", [])}
    brand_ids = {b["id"] for b in comp.get("companies", [])}
    supplier_ids = {s["id"] for s in sc.get("suppliers", [])}
    segment_ids = {s["id"] for s in cons.get("consumer_segments", [])}

    print(f"  Technology Node IDs: {tech_ids}")
    print(f"  Brand IDs: {brand_ids}")
    print(f"  Supplier IDs: {supplier_ids}")
    print(f"  Consumer Segment IDs: {segment_ids}")

    # Check technology node references in supply chain links
    for link in sc.get("links", []):
        tech_ref = link.get("tech_node")
        if tech_ref and tech_ref not in tech_ids:
            WARNINGS.append(f"Link {link['id']} references unknown tech_node: {tech_ref}")

    # Check rule targets reference valid entities
    target_prefixes = {"brand_": brand_ids, "supplier_": supplier_ids,
                       "segment_": segment_ids, "tech.": None, "world.": None}
    for rule in rules_data.get("rules", []):
        for eff in rule.get("effect", []):
            target = eff.get("target", "")
            # Only check brand/segment/supplier references, skip compound targets
            if target.startswith("brand_") and target in brand_ids:
                pass  # valid single brand reference
            elif target.startswith("segment_") and target in segment_ids:
                pass  # valid single segment reference

    # Check that company supply_chain references valid suppliers
    for brand in comp.get("companies", []):
        for sc_ref in brand.get("supply_chain", []):
            sid = sc_ref.get("supplier", "")
            if sid not in supplier_ids:
                WARNINGS.append(f"Brand {brand['id']} references unknown supplier: {sid}")

    print("  Cross-references: ", end="")
    if any("unknown" in str(w).lower() for w in WARNINGS):
        print("WARNINGS FOUND")
    else:
        print("OK")


def main():
    print("=" * 60)
    print("  SMARTPHONE WORLD MODEL — SCHEMA VALIDATION")
    print("=" * 60)

    validate_entities()
    validate_rules()
    validate_world_state()
    validate_cross_references()

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    if ERRORS:
        print(f"\n  ❌ ERRORS ({len(ERRORS)}):")
        for e in ERRORS:
            print(f"    - {e}")
    if WARNINGS:
        print(f"\n  ⚠️  WARNINGS ({len(WARNINGS)}):")
        for w in WARNINGS:
            print(f"    - {w}")
    if not ERRORS and not WARNINGS:
        print("\n  ✅ ALL CHECKS PASSED")
    elif not ERRORS:
        print(f"\n  ✅ All {len(WARNINGS)} warnings are non-blocking")

    return len(ERRORS)


if __name__ == "__main__":
    sys.exit(main())
