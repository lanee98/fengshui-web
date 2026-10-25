(function (root) {
  "use strict";
  const KEY = "immersehome.document";
  const clone = value => JSON.parse(JSON.stringify(value));
  function parse(key) { try { return JSON.parse(root.localStorage.getItem(key) || "null"); } catch (_) { return null; } }
  function valid(scene) { return !!scene && Array.isArray(scene.walls) && Array.isArray(scene.furniture); }
  function newId() { return "plan-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10); }
  function read() {
    const doc = parse(KEY);
    return doc && doc.schema === 1 && valid(doc.original) && valid(doc.updated) ? doc : null;
  }
  function commit(scene, options = {}) {
    if (!valid(scene)) throw new Error("户型数据不完整，暂时无法保存。");
    const prior = read();
    scene.meta = scene.meta || {};
    const id = options.newDocument ? newId() : (scene.meta.document_id || newId());
    scene.meta.document_id = id;
    const same = prior && prior.id === id;
    const locked = options.lockBaseline !== false;
    const original = same && prior.baselineLocked ? prior.original : clone(scene);
    const now = new Date().toISOString();
    const doc = {schema: 1, id, original, updated: clone(scene), baselineLocked: !!(same && prior.baselineLocked) || locked,
      createdAt: same ? prior.createdAt : now, updatedAt: now, revision: same ? prior.revision + 1 : 1,
      migrated: same ? prior.migrated : !!options.migrated};
    // 原始版与修改版放在同一条记录中，避免两个版本只保存了一半。
    root.localStorage.setItem(KEY, JSON.stringify(doc));
    root.localStorage.setItem("immersehome.scene", JSON.stringify(doc.updated));
    return clone(doc);
  }
  function restore() {
    const doc = read();
    if (doc) return doc;
    const scene = parse("immersehome.scene");
    return valid(scene) ? commit(scene, {migrated: true}) : null;
  }
  function ensure(scene) {
    const doc = read();
    return doc && scene.meta?.document_id === doc.id ? doc : commit(scene, {migrated: !scene.meta?.document_id});
  }
  root.SceneStore = {KEY, read, commit, restore, ensure, clone, newId};
})(globalThis);
