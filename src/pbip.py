"""Write a Power BI project (.pbip) from code: TMDL semantic model + PBIR report.

The semantic model imports CSV files from a folder given by the DataFolder parameter,
defines relationships and DAX measures. The report uses the PBIR (enhanced report)
format: one JSON file per page and per visual. All JSON files can be validated against
Microsoft's published schemas (github.com/microsoft/json-schemas) with validate().

Power BI Desktop runs on Windows only. Open <Name>.pbip there, set the DataFolder
parameter (Transform data > Edit parameters) to this project's dashboards/powerbi/data/
folder, and refresh.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
VISUAL_SCHEMA = f"{SCHEMA}/item/report/definition/visualContainer/2.4.0/schema.json"
PAGE_SCHEMA = f"{SCHEMA}/item/report/definition/page/2.0.0/schema.json"
PAGES_SCHEMA = f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json"
VERSION_SCHEMA = f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json"
REPORT_SCHEMA = f"{SCHEMA}/item/report/definition/report/3.0.0/schema.json"
PBIR_SCHEMA = f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json"
PBISM_SCHEMA = f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json"
PBIP_SCHEMA = f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json"

M_TYPES = {"string": "type text", "int64": "Int64.Type", "double": "type number", "dateTime": "type datetime",
           "boolean": "type logical"}


@dataclass
class Measure:
    name: str
    expression: str
    format_string: str | None = None
    folder: str | None = None


@dataclass
class Table:
    name: str
    csv: Path                                  # CSV file inside the DataFolder
    measures: list[Measure] = field(default_factory=list)
    key: str | None = None                     # column marked as key (date tables)
    is_date_table: bool = False
    formats: dict[str, str] = field(default_factory=dict)
    hidden: tuple[str, ...] = ()

    def columns(self) -> list[tuple[str, str]]:
        frame = pd.read_csv(self.csv, nrows=1000)
        cols = []
        for name, dtype in frame.dtypes.items():
            if pd.api.types.is_bool_dtype(dtype):
                t = "boolean"
            elif pd.api.types.is_integer_dtype(dtype):
                t = "int64"
            elif pd.api.types.is_float_dtype(dtype):
                t = "double"
            elif frame[name].dropna().astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all() and frame[name].notna().any():
                t = "dateTime"
            else:
                t = "string"
            cols.append((name, t))
        return cols


@dataclass
class Relationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str


@dataclass
class Visual:
    """visual_type examples: card, lineChart, clusteredBarChart, clusteredColumnChart, tableEx, pivotTable."""
    visual_type: str
    x: int
    y: int
    w: int
    h: int
    roles: dict[str, list[tuple[str, str, str]]]   # role -> [(kind 'measure'|'column', table, field)]
    title: str | None = None


@dataclass
class Page:
    display_name: str
    visuals: list[Visual]
    width: int = 1280
    height: int = 720


def _q(name: str) -> str:
    """Quote a TMDL object name when it contains anything but letters, digits and underscores."""
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


def _table_tmdl(t: Table) -> str:
    lines = [f"table {_q(t.name)}"]
    if t.is_date_table:
        lines.append("\tdataCategory: Time")
    lines.append("")
    for m in t.measures:
        lines.append(f"\tmeasure {_q(m.name)} = {m.expression}")
        if m.format_string:
            lines.append(f"\t\tformatString: {m.format_string}")
        if m.folder:
            lines.append(f"\t\tdisplayFolder: {m.folder}")
        lines.append("")
    cols = t.columns()
    for name, dtype in cols:
        lines.append(f"\tcolumn {_q(name)}")
        lines.append(f"\t\tdataType: {dtype}")
        if t.key == name:
            lines.append("\t\tisKey")
        if name in t.hidden:
            lines.append("\t\tisHidden")
        fmt = t.formats.get(name) or ("yyyy-mm-dd" if dtype == "dateTime" else None)
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append("\t\tsummarizeBy: " + ("sum" if dtype in ("int64", "double") and not name.endswith("_id") else "none"))
        lines.append(f"\t\tsourceColumn: {name}")
        lines.append("")
    types = ", ".join(f'{{"{n}", {M_TYPES[d]}}}' for n, d in cols)
    m_lines = [
        "let",
        f'    Source = Csv.Document(File.Contents(DataFolder & "{t.csv.name}"), [Delimiter=",", '
        f'Columns={len(cols)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        f'    Typed = Table.TransformColumnTypes(Headers, {{{types}}}, "en-US")',
        "in",
        "    Typed",
    ]
    lines.append(f"\tpartition {_q(t.name)} = m")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    lines += ["\t\t\t\t" + ln for ln in m_lines]
    lines.append("")
    return "\n".join(lines) + "\n"


def _field(kind: str, table: str, name: str) -> dict:
    src = {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}
    return {"Measure": src} if kind == "measure" else {"Column": src}


def _literal(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def _visual_json(v: Visual, idx: int) -> dict:
    name = f"v{idx:02d}_{uuid.uuid4().hex[:8]}"
    query_state = {}
    for role, fields in v.roles.items():
        query_state[role] = {"projections": [
            {"field": _field(kind, table, fname), "queryRef": f"{table}.{fname}", "nativeQueryRef": fname}
            for kind, table, fname in fields]}
    visual = {"visualType": v.visual_type, "query": {"queryState": query_state}}
    if v.title:
        visual["visualContainerObjects"] = {"title": [{"properties": {
            "show": _literal("true"), "text": _literal("'" + v.title.replace("'", "''") + "'")}}]}
    return {"$schema": VISUAL_SCHEMA, "name": name,
            "position": {"x": v.x, "y": v.y, "z": idx * 1000, "width": v.w, "height": v.h, "tabOrder": idx * 1000},
            "visual": visual}


def write_project(out_dir: Path, name: str, tables: list[Table], relationships: list[Relationship],
                  pages: list[Page], data_folder_hint: str) -> Path:
    """Write <name>.pbip, <name>.SemanticModel/ and <name>.Report/ into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sm, rp = out_dir / f"{name}.SemanticModel", out_dir / f"{name}.Report"
    (sm / "definition" / "tables").mkdir(parents=True, exist_ok=True)
    (rp / "definition" / "pages").mkdir(parents=True, exist_ok=True)

    def dump(path: Path, obj: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    dump(out_dir / f"{name}.pbip", {"$schema": PBIP_SCHEMA, "version": "1.0",
                                    "artifacts": [{"report": {"path": f"{name}.Report"}}],
                                    "settings": {"enableAutoRecovery": True}})
    # --- semantic model (TMDL) ---
    dump(sm / "definition.pbism", {"$schema": PBISM_SCHEMA, "version": "4.2", "settings": {}})
    (sm / "definition" / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1567\n\n", encoding="utf-8")
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tsourceQueryCulture: en-US", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull",
             "", "annotation PBI_QueryOrder = " + json.dumps(["DataFolder"] + [t.name for t in tables]), ""]
    model += [f"ref table {_q(t.name)}" for t in tables]
    (sm / "definition" / "model.tmdl").write_text("\n".join(model) + "\n", encoding="utf-8")
    hint = data_folder_hint.replace('"', "")
    (sm / "definition" / "expressions.tmdl").write_text(
        f'expression DataFolder = "{hint}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        "\tannotation PBI_ResultType = Text\n\n", encoding="utf-8")
    rel_lines = []
    for r in relationships:
        rel_lines += [f"relationship {uuid.uuid4()}", f"\tfromColumn: {_q(r.from_table)}.{_q(r.from_column)}",
                      f"\ttoColumn: {_q(r.to_table)}.{_q(r.to_column)}", ""]
    (sm / "definition" / "relationships.tmdl").write_text("\n".join(rel_lines), encoding="utf-8")
    for t in tables:
        (sm / "definition" / "tables" / f"{t.name}.tmdl").write_text(_table_tmdl(t), encoding="utf-8")
    # --- report (PBIR) ---
    dump(rp / "definition.pbir", {"$schema": PBIR_SCHEMA, "version": "4.0",
                                  "datasetReference": {"byPath": {"path": f"../{name}.SemanticModel"}}})
    dump(rp / "definition" / "version.json", {"$schema": VERSION_SCHEMA, "version": "2.0.0"})
    dump(rp / "definition" / "report.json", {"$schema": REPORT_SCHEMA, "themeCollection": {}})
    page_names = []
    for p_idx, page in enumerate(pages, start=1):
        pname = f"page{p_idx:02d}"
        page_names.append(pname)
        dump(rp / "definition" / "pages" / pname / "page.json",
             {"$schema": PAGE_SCHEMA, "name": pname, "displayName": page.display_name, "displayOption": "FitToPage",
              "height": page.height, "width": page.width})
        for v_idx, v in enumerate(page.visuals, start=1):
            vj = _visual_json(v, v_idx)
            dump(rp / "definition" / "pages" / pname / "visuals" / vj["name"] / "visual.json", vj)
    dump(rp / "definition" / "pages" / "pages.json",
         {"$schema": PAGES_SCHEMA, "pageOrder": page_names, "activePageName": page_names[0]})
    return out_dir / f"{name}.pbip"


def validate(project_dir: Path, schema_root: Path) -> list[str]:
    """Validate every JSON file of the project against the local copy of Microsoft's schemas.

    schema_root is the 'fabric' folder of a clone of github.com/microsoft/json-schemas.
    Returns a list of problems (empty = valid).
    """
    from jsonschema import Draft7Validator
    from referencing import Registry
    from referencing.jsonschema import DRAFT7

    registry = Registry()
    for path in schema_root.rglob("*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        resource = DRAFT7.create_resource(doc)
        uri = "https://developer.microsoft.com/json-schemas/fabric/" + path.relative_to(schema_root).as_posix()
        registry = registry.with_resource(uri, resource)
        if isinstance(doc, dict) and doc.get("$id"):
            registry = registry.with_resource(doc["$id"], resource)
    problems = []
    for path in project_dir.rglob("*"):
        if path.suffix not in (".json", ".pbir", ".pbism", ".pbip"):
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        schema_uri = doc.get("$schema")
        if not schema_uri:
            continue
        schema = registry.contents(schema_uri)
        validator = Draft7Validator(schema, registry=registry)
        for err in validator.iter_errors(doc):
            problems.append(f"{path.relative_to(project_dir)}: {err.message} at {list(err.absolute_path)}")
    return problems
