"""
Immerse Home · 风水审查 Web 后端
封装 fengshui-audit skill 的 18 条几何规则引擎，提供 HTTP API。
"""
import json
import sys
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

# 将 fengshui-audit 的 scripts 目录加入 path
AUDIT_DIR = Path(__file__).resolve().parent.parent / "fengshui-audit"
SCRIPTS_DIR = AUDIT_DIR / "scripts"
ASSETS_DIR = AUDIT_DIR / "assets"
sys.path.insert(0, str(SCRIPTS_DIR))

import check  # noqa: E402  风水审查引擎

app = Flask(__name__, static_folder="static", static_url_path="")


def run_audit(scene_data: dict, culture: bool = False) -> dict:
    """直接对 scene dict 运行审查，绕过文件 IO。"""
    s = check.Scene(scene_data)
    violations, passed, skipped = [], [], []

    for rid, name, cat, sev, fn, suggestion, vtext in check.RULES:
        try:
            res = fn(s)
        except Exception as e:
            skipped.append({"rule_id": rid, "name": name,
                            "reason": "%s: %s" % (type(e).__name__, e)})
            continue
        if res is None:
            passed.append({"rule_id": rid, "name": name})
            continue
        objs = res.get("objects", [])
        label = []
        for o in objs:
            nm = ""
            for f in s.furn:
                if f["id"] == o:
                    nm = f["name"]
            for d in s.doors:
                if d["id"] == o:
                    nm = d["name"]
            for w in s.walls:
                if w["id"] == o:
                    nm = check.wall_label(s, w)
            for b in s.beams:
                if b["id"] == o:
                    nm = b.get("name") or o
            label.append(nm or o)
        violations.append({
            "rule_id": rid,
            "name": name,
            "category": cat,
            "severity": sev,
            "objects": objs,
            "object_labels": label,
            "violation_text": vtext,
            "suggestion": check._fill(suggestion, label),
            "detail": res.get("detail", ""),
            "measured": res.get("measured"),
        })

    violations.sort(key=lambda v: (check.SEVERITY_ORDER.get(v["severity"], 9), v["rule_id"]))
    counts = {"high": 0, "medium": 0, "low": 0}
    for v in violations:
        counts[v["severity"]] = counts.get(v["severity"], 0) + 1

    if culture:
        import minggua
        culture_ref = minggua.check_owner(scene_data.get("meta", {}).get("owner"), s)
    else:
        culture_ref = {"enabled": False, "reason": "文化参考模块未启用。"}

    return {
        "scene": scene_data.get("meta", {}).get("name", "未命名户型"),
        "rule_version": "v1.0",
        "rule_count": len(check.RULES),
        "summary": {
            "violations": len(violations),
            "by_severity": counts,
            "passed": len(passed),
            "skipped": len(skipped),
        },
        "violations": violations,
        "passed_rules": passed,
        "skipped": skipped,
        "culture_reference": culture_ref,
    }


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/3d")
def three_d():
    return send_from_directory(app.static_folder, "3d.html")


@app.route("/plan")
def plan_editor():
    """户型图上传 → 识墙 → 摆家具 → 生成 3D。"""
    return send_from_directory(app.static_folder, "plan.html")


@app.route("/api/scenes")
def list_scenes():
    """列出可用的示例户型。"""
    scenes = []
    if ASSETS_DIR.exists():
        for f in sorted(ASSETS_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                scenes.append({
                    "id": f.stem,
                    "name": data.get("meta", {}).get("name", f.stem),
                    "note": data.get("meta", {}).get("note", ""),
                })
            except Exception:
                pass
    return jsonify(scenes)


@app.route("/api/scene/<scene_id>")
def get_scene(scene_id: str):
    """返回指定示例户型的 JSON。"""
    p = ASSETS_DIR / (scene_id + ".json")
    if not p.exists():
        return jsonify({"error": "scene not found"}), 404
    return jsonify(json.loads(p.read_text(encoding="utf-8")))


@app.route("/api/rules")
def list_rules():
    """列出全部 18 条规则元数据。"""
    rules = []
    for rid, name, cat, sev, fn, suggestion, vtext in check.RULES:
        rules.append({
            "rule_id": rid,
            "name": name,
            "category": cat,
            "severity": sev,
            "violation_text": vtext,
        })
    return jsonify(rules)


@app.route("/api/audit", methods=["POST"])
def audit():
    """对传入的户型 JSON 运行风水审查。"""
    data = request.get_json(force=True)
    if not data or "walls" not in data:
        return jsonify({"error": "无效的场景数据：缺少 walls 字段"}), 400
    culture = request.args.get("culture", "false").lower() == "true"
    result = run_audit(data, culture=culture)
    return jsonify(result)


@app.route("/api/audit-file", methods=["POST"])
def audit_file():
    """对上传的场景文件运行审查（兼容前端文件上传）。"""
    if "file" not in request.files:
        return jsonify({"error": "未上传文件"}), 400
    f = request.files["file"]
    try:
        data = json.loads(f.read().decode("utf-8"))
    except Exception as e:
        return jsonify({"error": "JSON 解析失败: %s" % e}), 400
    culture = request.form.get("culture", "false").lower() == "true"
    result = run_audit(data, culture=culture)
    return jsonify(result)


if __name__ == "__main__":
    print("=" * 60)
    print("  Immerse Home · 风水审查可视化平台")
    print("  后端启动中... http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
