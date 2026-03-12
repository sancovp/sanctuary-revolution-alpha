const ui = {
  spaceSelect: document.querySelector("#spaceSelect"),
  activateSpace: document.querySelector("#activateSpace"),
  newSpaceName: document.querySelector("#newSpaceName"),
  createSpaceBtn: document.querySelector("#createSpaceBtn"),
  parentSelect: document.querySelector("#parentSelect"),
  pointLabel: document.querySelector("#pointLabel"),
  addPointBtn: document.querySelector("#addPointBtn"),
  attrName: document.querySelector("#attrName"),
  attrSpectrum: document.querySelector("#attrSpectrum"),
  attrDefault: document.querySelector("#attrDefault"),
  addAttrBtn: document.querySelector("#addAttrBtn"),
  bloomCoordinate: document.querySelector("#bloomCoordinate"),
  bloomLabel: document.querySelector("#bloomLabel"),
  bloomCount: document.querySelector("#bloomCount"),
  bloomBtn: document.querySelector("#bloomBtn"),
  spaceCanvas: document.querySelector("#spaceCanvas"),
  includedPoints: document.querySelector("#includedPoints"),
  composedCoordinate: document.querySelector("#composedCoordinate"),
  manualCoordinate: document.querySelector("#manualCoordinate"),
  runScryBtn: document.querySelector("#runScryBtn"),
  clearIncludeBtn: document.querySelector("#clearIncludeBtn"),
  scryOutput: document.querySelector("#scryOutput"),
  pointDetail: document.querySelector("#pointDetail"),
  llmPrompt: document.querySelector("#llmPrompt"),
  dumpNeighborhood: document.querySelector("#dumpNeighborhood"),
  autoApply: document.querySelector("#autoApply"),
  saturate: document.querySelector("#saturate"),
  maxActions: document.querySelector("#maxActions"),
  perParentCap: document.querySelector("#perParentCap"),
  maxCycles: document.querySelector("#maxCycles"),
  retryAttempts: document.querySelector("#retryAttempts"),
  runSuggestBtn: document.querySelector("#runSuggestBtn"),
  llmOutput: document.querySelector("#llmOutput"),
  statusLog: document.querySelector("#statusLog"),
};

const state = {
  activeSpace: "",
  spaces: [],
  space: null,
  selectedNodeId: "root",
  includedNodeIds: new Set(),
  hoveredNodeId: "",
  lastScry: null,
  lastWarnings: [],
};

function logStatus(message, isError = false) {
  const stamp = new Date().toLocaleTimeString();
  const line = `${stamp} ${isError ? "[error]" : "[ok]"} ${message}`;
  ui.statusLog.textContent = `${line}\n${ui.statusLog.textContent}`.trim().slice(0, 4000);
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `${response.status} ${response.statusText}`);
  }
  return data;
}

function getNodeMap() {
  const map = new Map();
  const nodes = state.space?.nodes || [];
  for (const node of nodes) map.set(node.id, node);
  return map;
}

function parsePrimitive(text) {
  const raw = String(text ?? "").trim();
  if (raw === "") return undefined;
  if (raw === "true") return true;
  if (raw === "false") return false;
  const num = Number(raw);
  if (!Number.isNaN(num)) return num;
  return raw;
}

function composeCoordinateFromIncluded() {
  const nodeMap = getNodeMap();
  const levelSets = new Map();
  const warnings = [];

  for (const nodeId of state.includedNodeIds) {
    const node = nodeMap.get(nodeId);
    if (!node) continue;
    const digits = node.pathDigits || [];
    for (let i = 0; i < digits.length; i++) {
      const digit = Number(digits[i]);
      if (!levelSets.has(i)) levelSets.set(i, new Set());
      const slotSet = levelSets.get(i);

      if (digit > 8) {
        warnings.push(`Node ${node.id} at level ${i + 1} exceeds digit 8; mapped to 0 superposition.`);
        slotSet.add(0);
      } else if (!slotSet.has(0)) {
        slotSet.add(digit);
      }
    }
  }

  const levels = Array.from(levelSets.keys())
    .sort((a, b) => a - b)
    .map((idx) => {
      const digits = Array.from(levelSets.get(idx)).sort((a, b) => a - b);
      if (digits.includes(0)) return "0";
      return digits.join("");
    })
    .filter(Boolean);

  return { coordinate: levels.join("."), warnings };
}

function renderSpaceSelector() {
  ui.spaceSelect.innerHTML = "";
  for (const name of state.spaces) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    if (name === state.activeSpace) opt.selected = true;
    ui.spaceSelect.appendChild(opt);
  }
}

function renderParentSelector() {
  const nodes = state.space?.nodes || [];
  ui.parentSelect.innerHTML = "";
  for (const node of nodes) {
    const opt = document.createElement("option");
    opt.value = node.id;
    opt.textContent = `${node.id} (${node.label})`;
    if (node.id === state.selectedNodeId) opt.selected = true;
    ui.parentSelect.appendChild(opt);
  }
}

function renderIncluded() {
  ui.includedPoints.innerHTML = "";
  const nodeMap = getNodeMap();
  const ids = Array.from(state.includedNodeIds).sort();
  if (ids.length === 0) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = "(none)";
    ui.includedPoints.appendChild(chip);
  } else {
    for (const id of ids) {
      const node = nodeMap.get(id);
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = `${id}${node ? ":" + node.label : ""}`;
      ui.includedPoints.appendChild(chip);
    }
  }

  const composed = composeCoordinateFromIncluded();
  state.lastWarnings = composed.warnings;
  ui.composedCoordinate.textContent = composed.coordinate || "-";
}

function formatNodeDetails(node) {
  if (!node) return "No node";
  return pretty({
    id: node.id,
    label: node.label,
    depth: node.depth,
    slotCount: node.slotCount,
    children: node.children,
    attributes: node.attributes,
    pathDigits: node.pathDigits,
    parentId: node.parentId,
  });
}

function setDetailFromNode(nodeId, source = "hover") {
  const node = getNodeMap().get(nodeId);
  if (!node) return;
  ui.pointDetail.textContent = `${source.toUpperCase()}\n${formatNodeDetails(node)}`;
}

function toggleInclude(nodeId) {
  if (state.includedNodeIds.has(nodeId)) {
    state.includedNodeIds.delete(nodeId);
  } else {
    state.includedNodeIds.add(nodeId);
  }
  renderIncluded();
  renderSpaceCanvas();
}

function renderSpaceCanvas() {
  const nodes = state.space?.nodes || [];
  const grouped = new Map();
  for (const node of nodes) {
    if (!grouped.has(node.depth)) grouped.set(node.depth, []);
    grouped.get(node.depth).push(node);
  }

  ui.spaceCanvas.innerHTML = "";

  const depths = Array.from(grouped.keys()).sort((a, b) => a - b);
  for (const depth of depths) {
    const row = document.createElement("section");
    row.className = "depth-row";

    const label = document.createElement("div");
    label.className = "depth-label";
    label.textContent = `Depth ${depth}`;
    row.appendChild(label);

    const grid = document.createElement("div");
    grid.className = "node-grid";

    const depthNodes = grouped.get(depth).sort((a, b) => a.id.localeCompare(b.id));
    for (const node of depthNodes) {
      const card = document.createElement("article");
      card.className = "node-card";
      if (node.id === state.selectedNodeId) card.classList.add("selected");
      if (state.includedNodeIds.has(node.id)) card.classList.add("included");

      card.addEventListener("mouseenter", () => {
        state.hoveredNodeId = node.id;
        setDetailFromNode(node.id, "hover");
      });

      card.addEventListener("click", () => {
        state.selectedNodeId = node.id;
        renderParentSelector();
        renderSpaceCanvas();
        setDetailFromNode(node.id, "selected");
      });

      const title = document.createElement("div");
      title.className = "node-title";
      title.textContent = node.label;

      const meta = document.createElement("div");
      meta.className = "node-meta";
      meta.textContent = `${node.id} | slots:${node.slotCount} | kids:${node.children.length}`;

      const actions = document.createElement("div");
      actions.className = "card-actions";

      const includeBtn = document.createElement("button");
      includeBtn.className = "include-toggle";
      if (state.includedNodeIds.has(node.id)) includeBtn.classList.add("active");
      includeBtn.textContent = state.includedNodeIds.has(node.id) ? "Included" : "Include";
      includeBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        toggleInclude(node.id);
      });

      const attrCount = document.createElement("span");
      attrCount.className = "node-meta";
      attrCount.textContent = `attrs:${node.attributes.length}`;

      actions.appendChild(includeBtn);
      actions.appendChild(attrCount);

      card.appendChild(title);
      card.appendChild(meta);
      card.appendChild(actions);
      grid.appendChild(card);
    }

    row.appendChild(grid);
    ui.spaceCanvas.appendChild(row);
  }
}

async function loadSpace(spaceName) {
  const data = await api(`/api/spaces/${encodeURIComponent(spaceName)}`);
  state.space = data.space;
  state.activeSpace = data.space.name;
  state.spaces = data.spaces || state.spaces;
  if (!getNodeMap().has(state.selectedNodeId)) state.selectedNodeId = "root";
  state.includedNodeIds.forEach((id) => {
    if (!getNodeMap().has(id)) state.includedNodeIds.delete(id);
  });
  renderSpaceSelector();
  renderParentSelector();
  renderIncluded();
  renderSpaceCanvas();
  setDetailFromNode(state.selectedNodeId, "selected");
  logStatus(`Loaded space ${spaceName}.`);
}

async function initialLoad() {
  const base = await api("/api/spaces");
  state.spaces = base.spaces || [];
  state.activeSpace = base.activeSpace || state.spaces[0] || "";
  renderSpaceSelector();
  if (state.activeSpace) {
    await loadSpace(state.activeSpace);
  } else {
    logStatus("No spaces found.", true);
  }
}

ui.activateSpace.addEventListener("click", async () => {
  try {
    const selected = ui.spaceSelect.value;
    await api(`/api/spaces/${encodeURIComponent(selected)}/activate`, { method: "POST", body: "{}" });
    await loadSpace(selected);
  } catch (error) {
    logStatus(error.message, true);
  }
});

ui.createSpaceBtn.addEventListener("click", async () => {
  try {
    const name = ui.newSpaceName.value.trim();
    const data = await api("/api/spaces", {
      method: "POST",
      body: pretty({ name }),
    });
    state.spaces = data.spaces || [];
    state.activeSpace = data.activeSpace || name;
    ui.newSpaceName.value = "";
    await loadSpace(state.activeSpace);
  } catch (error) {
    logStatus(error.message, true);
  }
});

ui.addPointBtn.addEventListener("click", async () => {
  try {
    const parentId = ui.parentSelect.value || state.selectedNodeId || "root";
    const label = ui.pointLabel.value.trim();
    if (!label) {
      logStatus("Point label is required.", true);
      return;
    }
    await api(`/api/spaces/${encodeURIComponent(state.activeSpace)}/points`, {
      method: "POST",
      body: pretty({ parentId, label }),
    });
    ui.pointLabel.value = "";
    await loadSpace(state.activeSpace);
  } catch (error) {
    logStatus(error.message, true);
  }
});

ui.addAttrBtn.addEventListener("click", async () => {
  try {
    const nodeId = state.selectedNodeId || "root";
    const name = ui.attrName.value.trim();
    const spectrum = ui.attrSpectrum.value
      .split(",")
      .map((x) => x.trim())
      .filter((x) => x.length > 0)
      .map(parsePrimitive);
    const defaultValue = parsePrimitive(ui.attrDefault.value);

    if (!name || spectrum.length === 0) {
      logStatus("Attribute name and spectrum are required.", true);
      return;
    }

    await api(`/api/spaces/${encodeURIComponent(state.activeSpace)}/attributes`, {
      method: "POST",
      body: pretty({ nodeId, name, spectrum, defaultValue }),
    });
    ui.attrName.value = "";
    ui.attrSpectrum.value = "";
    ui.attrDefault.value = "";
    await loadSpace(state.activeSpace);
  } catch (error) {
    logStatus(error.message, true);
  }
});

ui.bloomBtn.addEventListener("click", async () => {
  try {
    const coordinate = ui.bloomCoordinate.value.trim();
    const slotLabel = ui.bloomLabel.value.trim() || "point";
    const count = Number(ui.bloomCount.value || "4");
    await api(`/api/spaces/${encodeURIComponent(state.activeSpace)}/bloom`, {
      method: "POST",
      body: pretty({ coordinate, slotLabel, count }),
    });
    await loadSpace(state.activeSpace);
  } catch (error) {
    logStatus(error.message, true);
  }
});

ui.runScryBtn.addEventListener("click", async () => {
  try {
    const composed = composeCoordinateFromIncluded();
    const manual = ui.manualCoordinate.value.trim();
    const coordinate = manual || composed.coordinate;
    const includeNodeIds = Array.from(state.includedNodeIds);

    const data = await api(`/api/spaces/${encodeURIComponent(state.activeSpace)}/scry`, {
      method: "POST",
      body: pretty({ coordinate, includeNodeIds }),
    });
    state.lastScry = data;
    ui.scryOutput.textContent = pretty(data);

    if (data.warnings?.length) {
      logStatus(`Scry ran with warnings (${data.warnings.length}).`, true);
    } else {
      logStatus(`Scry resolved ${data.resolved?.length || 0} nodes at ${data.coordinate || "(none)"}.`);
    }
  } catch (error) {
    logStatus(error.message, true);
  }
});

ui.clearIncludeBtn.addEventListener("click", () => {
  state.includedNodeIds.clear();
  renderIncluded();
  renderSpaceCanvas();
  logStatus("Cleared included points.");
});

ui.runSuggestBtn.addEventListener("click", async () => {
  try {
    const composed = composeCoordinateFromIncluded();
    const coordinate = ui.manualCoordinate.value.trim() || state.lastScry?.coordinate || composed.coordinate || "";
    const includeNodeIds = Array.from(state.includedNodeIds);
    const prompt = ui.llmPrompt.value.trim();
    const dumpNeighborhood = Boolean(ui.dumpNeighborhood?.checked);
    const autoApply = Boolean(ui.autoApply?.checked);
    const saturate = Boolean(ui.saturate?.checked);
    const maxActionsRaw = Number(ui.maxActions?.value || "12");
    const maxActions = Number.isFinite(maxActionsRaw) ? Math.max(1, Math.min(64, maxActionsRaw)) : 12;
    const perParentCapRaw = Number(ui.perParentCap?.value || "0");
    const perParentCap = Number.isFinite(perParentCapRaw) ? Math.max(0, Math.min(16, perParentCapRaw)) : 0;
    const maxCyclesRaw = Number(ui.maxCycles?.value || "3");
    const maxCycles = Number.isFinite(maxCyclesRaw) ? Math.max(1, Math.min(12, maxCyclesRaw)) : 3;
    const retryAttemptsRaw = Number(ui.retryAttempts?.value || "2");
    const retryAttempts = Number.isFinite(retryAttemptsRaw) ? Math.max(0, Math.min(4, retryAttemptsRaw)) : 2;

    const data = await api(`/api/spaces/${encodeURIComponent(state.activeSpace)}/llm-suggest`, {
      method: "POST",
      body: pretty({
        coordinate,
        includeNodeIds,
        prompt,
        dumpNeighborhood,
        autoApply,
        saturate,
        maxActions,
        perParentCap,
        maxCycles,
        retryAttempts,
      }),
    });
    ui.llmOutput.textContent = pretty(data);
    if (autoApply) {
      await loadSpace(state.activeSpace);
    }
    const added = Number(data?.applied?.added || 0);
    const attempted = Number(data?.applied?.attempted || 0);
    const cyclesRun = Number(data?.saturation?.cyclesRun || 1);
    const stopReason = String(data?.saturation?.stopReason || "");
    if (autoApply) {
      const cycleMsg = data?.saturation?.enabled
        ? `cycles=${cyclesRun}/${Number(data?.saturation?.maxCycles || maxCycles)}`
        : `cycles=${cyclesRun}`;
      const stopMsg = stopReason ? ` stop=${stopReason}` : "";
      logStatus(`LLM suggest ${data.stub ? "fallback" : "completed"}; applied ${added}/${attempted}, ${cycleMsg}.${stopMsg}`, data.stub);
    } else {
      logStatus(data.stub ? "LLM suggest fallback completed." : "LLM suggest completed.");
    }
  } catch (error) {
    logStatus(error.message, true);
  }
});

initialLoad().catch((error) => {
  logStatus(error.message, true);
});
