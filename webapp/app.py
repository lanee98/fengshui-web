"""
Immerse Home · 风水审查 Web 后端
封装 fengshui-audit skill 的 18 条几何规则引擎，提供 HTTP API。
"""
import json
import copy
import math
import time
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


def overlap(a, b):
    """分离轴判定；允许家具边缘接触，不允许实体相交。"""
    for r in (a, b):
        h = check.heading_vec(r.heading)
        for axis in (h, (-h[1], h[0])):
            pa = [check.dot(p, axis) for p in a.corners()]
            pb = [check.dot(p, axis) for p in b.corners()]
            if min(max(pa), max(pb)) - max(min(pa), min(pb)) <= 0.015:
                return False
    return True


def placement_error(data, item, origin=None):
    r = check.Rect(item["rect"])
    walls = data.get("walls", [])
    points = [p for w in walls for p in (w["a"], w["b"])]
    if not points:
        return "缺少墙体边界，请先完善户型。"
    x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
    y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
    if any(p[0] < x0 - .02 or p[0] > x1 + .02 or p[1] < y0 - .02 or p[1] > y1 + .02 for p in r.corners()):
        return "家具超出了户型边界，请减小移动距离或调整方向。"
    inset = dict(item["rect"], len=max(.001, r.len - .035), wid=max(.001, r.wid - .035))
    inner = check.Rect(inset)
    for w in walls:
        a, b = tuple(w["a"]), tuple(w["b"])
        if inner.contains(a) or inner.contains(b) or any(check.seg_intersect(a, b, p, q) for p, q in inner.edges()):
            return "家具与墙体相交，请调整移动距离或旋转角度。"
        if origin and check.seg_intersect(origin, r.c, a, b):
            return "这次移动会穿过墙体，请在当前房间内调整，或分步经过门洞移动。"
    for other in data.get("furniture", []):
        if other["id"] != item["id"] and overlap(r, check.Rect(other["rect"])):
            return "家具与「%s」重叠，请调整位置。" % other.get("name", other["id"])
    for door in data.get("doors", []):
        n = door.get("normal", [0, 1])
        opening = check.Rect({"cx": door["center"][0], "cy": door["center"][1],
                              "len": .2, "wid": door.get("width", .9), "heading": check.heading_of(n)})
        if overlap(r, opening):
            return "家具挡住了「%s」的门洞，请为出入口留出空间。" % door.get("name", "门")
    return None


def validate_scene(data):
    if not isinstance(data, dict) or not data.get("walls"):
        raise ValueError("缺少有效的墙体数据。")
    if len(data.get("furniture", [])) > 200 or len(data["walls"]) > 1000:
        raise ValueError("户型过于复杂，请分区调整。")
    check.Scene(data)
    ids = [f.get("id") for f in data.get("furniture", [])]
    if any(not fid for fid in ids) or len(set(ids)) != len(ids):
        raise ValueError("家具编号缺失或重复，请重新生成户型。")
    for w in data["walls"]:
        if any(not math.isfinite(float(v)) for p in (w["a"], w["b"]) for v in p):
            raise ValueError("墙体坐标必须是有限数字。")
    for f in data.get("furniture", []):
        if any(not math.isfinite(float(f["rect"].get(k, 0))) for k in ("cx", "cy", "len", "wid", "heading")):
            raise ValueError("家具坐标和角度必须是有限数字。")
        if f["rect"]["len"] <= 0 or f["rect"]["wid"] <= 0:
            raise ValueError("家具尺寸必须大于零。")


def candidates(data, item):
    old = item["rect"]
    headings = list(dict.fromkeys([old.get("heading", 0), 0, 90, 180, 270]))
    if item["type"] == "mirror":
        headings += [(old.get("heading", 0) + delta) % 360 for delta in (30, -30, 60, -60, 120, -120)]
    positions = [(old["cx"], old["cy"])]
    for distance in (.2, .4, .65, 1., 1.5, 2.):
        for i in range(8):
            a = i * math.pi / 4
            positions.append((old["cx"] + math.cos(a) * distance, old["cy"] + math.sin(a) * distance))
    for x, y in positions:
        for heading in headings:
            yield dict(old, cx=round(x, 4), cy=round(y, 4), heading=heading)
    # 将家具背边放在实墙内侧 2cm；同时尝试沿墙的位置，避免写死示例坐标。
    for w in data["walls"]:
        if w.get("is_window"):
            continue
        a, b = w["a"], w["b"]
        u = check.norm(check.sub(b, a))
        if check.length(check.sub(b, a)) < old["wid"]:
            continue
        n = (-u[1], u[0])
        for t in (.2, .35, .5, .65, .8):
            p = check.add(a, check.mul(check.sub(b, a), t))
            for sign in (-1, 1):
                facing = check.mul(n, sign)
                c = check.add(p, check.mul(facing, old["len"] / 2 + .02))
                yield dict(old, cx=round(c[0], 4), cy=round(c[1], 4), heading=check.heading_of(facing) % 360)


def signature(v):
    return v["rule_id"], tuple(sorted(v.get("objects", [])))


def auto_repair(source, audit, rule_id=None):
    validate_scene(source)
    data = copy.deepcopy(source)
    before = audit(data)
    result = before
    changes = []
    deadline = time.monotonic() + 6
    functions = {r[0]: r[4] for r in check.RULES}
    for iteration in range(16):
        improved = False
        allowed = {v["rule_id"] for v in result["violations"]}
        for violation in result["violations"]:
            rid = violation["rule_id"]
            if rule_id and rid != rule_id:
                continue
            targets = [f for f in data.get("furniture", []) if f["id"] in violation.get("objects", [])]
            targets.sort(key=lambda f: (f["type"] != "mirror", f["type"] != "sink"))
            for item in targets:
                old = dict(item["rect"])
                origin = (old["cx"], old["cy"])
                best = None
                for candidate in candidates(data, item):
                    if time.monotonic() > deadline:
                        break
                    if candidate == old:
                        continue
                    item["rect"] = candidate
                    if placement_error(data, item, origin):
                        continue
                    trial_scene = check.Scene(data)
                    target = functions[rid](trial_scene)
                    if target is not None and item["id"] in target.get("objects", []):
                        continue
                    trial = audit(data)
                    trial_ids = {v["rule_id"] for v in trial["violations"]}
                    if trial["skipped"] or not trial_ids.issubset(allowed):
                        continue
                    travel = math.hypot(candidate["cx"] - old["cx"], candidate["cy"] - old["cy"])
                    turn = abs((candidate.get("heading", 0) - old.get("heading", 0) + 180) % 360 - 180)
                    cost = (len(trial["violations"]), travel + turn / 360)
                    if best is None or cost < best[0]:
                        best = (cost, dict(candidate), trial)
                item["rect"] = old
                if best:
                    item["rect"] = best[1]
                    changes.append({"id": item["id"], "name": item.get("name", item["id"]),
                                    "before": old, "after": best[1], "rule_id": rid})
                    result = best[2]
                    improved = True
                    break
            if improved or time.monotonic() > deadline:
                break
        if not improved or time.monotonic() > deadline:
            break
    remaining = {signature(v) for v in result["violations"]}
    resolved = [v for v in before["violations"] if signature(v) not in remaining]
    return {"scene": data, "audit": result, "changes": changes, "resolved": resolved,
            "message": ("已调整 %d 次家具摆位，复检剩余 %d 项。" % (len(changes), len(result["violations"]))
                        if changes else "未找到同时满足墙体、家具间距和现有规则的自动摆位，请尝试手动调整。")}


def manual_repair(source, fid, dx, dz, turn, audit):
    validate_scene(source)
    if any(not math.isfinite(float(v)) or abs(float(v)) > 1000 for v in (dx, dz, turn)):
        raise ValueError("移动距离和旋转角度必须是有效数字。")
    data = copy.deepcopy(source)
    item = next((f for f in data.get("furniture", []) if f["id"] == fid), None)
    if not item:
        raise ValueError("未找到选中的家具，请重新选择。")
    old = dict(item["rect"])
    item["rect"].update(cx=round(old["cx"] + float(dx), 4), cy=round(old["cy"] + float(dz), 4),
                        heading=round((old.get("heading", 0) + float(turn)) % 360, 2))
    if item["rect"] == old:
        raise ValueError("请填写非零的移动距离或旋转角度。")
    error = placement_error(data, item, (old["cx"], old["cy"]))
    if error:
        raise ValueError(error)
    result = audit(data)
    before = audit(source)
    remaining = {signature(v) for v in result["violations"]}
    return {"scene": data, "audit": result, "changes": [{"id": fid, "name": item.get("name", fid),
            "before": old, "after": item["rect"]}],
            "resolved": [v for v in before["violations"] if signature(v) not in remaining],
            "message": "家具已移动并完成复检。"}


@app.route("/api/repair", methods=["POST"])
def repair_layout():
    """对当前户型实际家具进行自动/手动调整，并返回真实复检结果。"""
    payload = request.get_json(force=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("scene"), dict):
        return jsonify({"error": "缺少有效的户型数据。"}), 400
    try:
        mode = payload.get("mode", "auto")
        if mode == "manual":
            result = manual_repair(payload["scene"], payload.get("furniture_id"),
                                   payload.get("dx", 0), payload.get("dz", 0), payload.get("turn", 0), run_audit)
        elif mode == "auto":
            result = auto_repair(payload["scene"], run_audit, payload.get("rule_id"))
        else:
            raise ValueError("未知的调整方式。")
        return jsonify(result)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    print("=" * 60)
    print("  Immerse Home · 风水审查可视化平台")
    print("  后端启动中... http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
