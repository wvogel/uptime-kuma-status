// ===== Uptime Status - Admin JS =====

const Admin = (function () {
    "use strict";

    let currentLang = localStorage.getItem("us_lang") || "en";
    let currentTheme = localStorage.getItem("us_theme") || "auto";

    // --- Theme & i18n ---

    function applyTheme(theme) {
        currentTheme = theme;
        localStorage.setItem("us_theme", theme);
        const html = document.documentElement;
        if (theme === "auto") {
            html.setAttribute("data-theme", window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
        } else {
            html.setAttribute("data-theme", theme);
        }
        const btn = document.getElementById("theme-toggle");
        if (btn) btn.setAttribute("data-state", theme);
    }

    function cycleTheme() {
        const order = ["light", "dark", "auto"];
        applyTheme(order[(order.indexOf(currentTheme) + 1) % order.length]);
    }

    function setLang(lang) {
        currentLang = lang;
        localStorage.setItem("us_lang", lang);
        document.getElementById("lang-label").textContent = lang.toUpperCase();
        document.querySelectorAll("[data-i18n]").forEach(el => {
            const key = el.getAttribute("data-i18n");
            const text = (I18N[lang] || {})[key];
            if (text) el.textContent = text;
        });
    }

    // --- API helpers ---

    async function api(method, path, body) {
        const opts = { method, headers: { "Content-Type": "application/json" } };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const res = await fetch(path, opts);
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return res.json();
    }

    function esc(str) {
        const d = document.createElement("div");
        d.textContent = str || "";
        return d.innerHTML;
    }

    function tl(key) {
        return (I18N[currentLang] || {})[key] || key;
    }

    // --- Modal ---

    function showModal(message, type) {
        const icons = { success: "\u2705", error: "\u274c", info: "\u2139\ufe0f" };
        document.getElementById("modal-icon").textContent = icons[type] || icons.info;
        document.getElementById("modal-message").textContent = message;
        const overlay = document.getElementById("modal-overlay");
        overlay.style.display = "flex";
        requestAnimationFrame(() => overlay.classList.add("visible"));
    }

    function closeModal() {
        const overlay = document.getElementById("modal-overlay");
        overlay.classList.remove("visible");
        setTimeout(() => { overlay.style.display = "none"; }, 200);
    }

    // --- Inline delete confirmation ---

    async function confirmDelete(btn, callback) {
        if (btn.dataset.confirming === "true") {
            btn.dataset.confirming = "";
            document.removeEventListener("mousedown", btn._outsideClick);
            await callback();
            return;
        }
        const original = btn.textContent;
        btn.textContent = tl("confirm_delete");
        btn.dataset.confirming = "true";
        btn.classList.add("btn-danger-active");
        btn._outsideClick = (e) => {
            if (!btn.contains(e.target)) {
                btn.textContent = original;
                btn.dataset.confirming = "";
                btn.classList.remove("btn-danger-active");
                document.removeEventListener("mousedown", btn._outsideClick);
            }
        };
        setTimeout(() => document.addEventListener("mousedown", btn._outsideClick), 0);
    }

    // --- Tabs ---

    function initTabs() {
        document.querySelectorAll(".tab-btn").forEach(btn => {
            btn.addEventListener("click", function () {
                document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
                document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
                btn.classList.add("active");
                document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
                loadTab(btn.dataset.tab);
            });
        });
    }

    function loadTab(tab) {
        switch (tab) {
            case "instances": loadInstances(); break;
            case "monitors": loadMonitors(); break;
            case "incidents": loadIncidents(); break;
            case "footer": loadFooter(); break;
            case "settings": loadSettings(); break;
        }
    }

    // --- Instances ---

    let instanceItems = [];

    async function loadInstances() {
        instanceItems = await api("GET", "/api/instances");
        renderInstanceList();
    }

    function renderInstanceList() {
        const list = document.getElementById("instances-list");
        list.innerHTML = "";
        instanceItems.forEach(inst => {
            const div = document.createElement("div");
            div.className = "sortable-item";
            div.draggable = true;
            div.dataset.id = inst.id;
            const statusDot = inst.reachable === true ? "dot-up" :
                              inst.reachable === false ? "dot-down" : "dot-unknown";
            const statusText = inst.reachable === true ? "OK" : inst.reachable === false ? "Error" : "?";
            div.innerHTML = `
                <span class="drag-handle">&#9776;</span>
                <span class="item-label"><strong>${esc(inst.name)}</strong> <span style="color:var(--text-secondary);font-size:12px">${esc(inst.api_url)}</span></span>
                <span><span class="status-dot-inline ${statusDot}"></span>${statusText}</span>
                <button class="btn btn-sm" onclick="event.stopPropagation(); Admin.testInstance(${inst.id})">${tl("test_connection")}</button>
                <button class="btn btn-sm" onclick="event.stopPropagation(); Admin.editInstance(${inst.id})">${tl("edit")}</button>
                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); Admin.confirmDeleteInstance(this, ${inst.id})">${tl("delete")}</button>`;
            div.addEventListener("dragstart", onInstDragStart);
            div.addEventListener("dragover", onInstDragOver);
            div.addEventListener("dragleave", onInstDragLeave);
            div.addEventListener("drop", onInstDrop);
            div.addEventListener("dragend", onInstDragEnd);
            list.appendChild(div);
        });
    }

    let instDragSrcId = null;

    function onInstDragStart(e) {
        instDragSrcId = e.currentTarget.dataset.id;
        e.currentTarget.style.opacity = "0.4";
        e.dataTransfer.effectAllowed = "move";
    }
    function onInstDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add("drag-over");
    }
    function onInstDragLeave(e) {
        e.currentTarget.classList.remove("drag-over");
    }
    async function onInstDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove("drag-over");
        const targetId = e.currentTarget.dataset.id;
        if (instDragSrcId === targetId) return;
        const srcIdx = instanceItems.findIndex(i => String(i.id) === instDragSrcId);
        const tgtIdx = instanceItems.findIndex(i => String(i.id) === targetId);
        const [moved] = instanceItems.splice(srcIdx, 1);
        instanceItems.splice(tgtIdx, 0, moved);
        renderInstanceList();
        await api("POST", "/api/instances/reorder", { instance_ids: instanceItems.map(i => i.id) });
    }
    function onInstDragEnd(e) {
        e.currentTarget.style.opacity = "";
        document.querySelectorAll(".sortable-item").forEach(el => el.classList.remove("drag-over"));
    }

    function showInstanceForm(inst) {
        const form = document.getElementById("instance-form");
        form.style.display = "";
        document.getElementById("inst-id").value = inst ? inst.id : "";
        document.getElementById("inst-name").value = inst ? inst.name : "";
        document.getElementById("inst-api-url").value = inst ? inst.api_url : "";
        document.getElementById("inst-network").value = "shared-npm";
        document.getElementById("inst-snippet-box").style.display = "none";
        document.getElementById("inst-snippet").textContent = "";
    }

    function hideInstanceForm() {
        document.getElementById("instance-form").style.display = "none";
    }

    async function editInstance(id) {
        const inst = instanceItems.find(i => i.id === id);
        if (inst) showInstanceForm(inst);
    }

    function buildSnippet(apiKey) {
        const network = document.getElementById("inst-network").value || "shared-npm";
        return `  uptime-kuma-api:
    image: ghcr.io/wvogel/uptime-kuma-api:latest
    restart: unless-stopped
    environment:
      DB_HOST: mariadb
      DB_PORT: 3306
      DB_NAME: kuma
      DB_USER: kuma
      DB_PASS: <passwort>
      API_KEY: ${apiKey}
      # ALLOWED_RANGES: 10.0.0.0/8,172.16.0.0/12
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:80/health"]
      interval: 30s
      retries: 3
      start_period: 10s
      timeout: 5s
    networks:
      - default
      - ${network}

networks:
  ${network}:
    external: true`;
    }

    function copySnippet() {
        const text = document.getElementById("inst-snippet").textContent;
        navigator.clipboard.writeText(text).then(() => showModal(tl("copied"), "success"));
    }

    async function saveInstance() {
        const id = document.getElementById("inst-id").value;
        const body = {
            name: document.getElementById("inst-name").value,
            api_url: document.getElementById("inst-api-url").value,
        };

        try {
            if (id) {
                await api("PUT", `/api/instances/${id}`, body);
            } else {
                const result = await api("POST", "/api/instances", body);
                const snippet = buildSnippet(result.api_key);
                document.getElementById("inst-snippet").textContent = snippet;
                document.getElementById("inst-snippet-box").style.display = "";
            }
            hideInstanceForm();
            await loadInstances();
            // Auto-test newest instance
            if (!id && instanceItems.length > 0) {
                const newest = instanceItems[instanceItems.length - 1];
                await testInstance(newest.id);
            }
        } catch (e) {
            showModal(e.message, "error");
        }
    }

    async function confirmDeleteInstance(btn, id) {
        await confirmDelete(btn, async () => {
            await api("DELETE", `/api/instances/${id}`);
            await loadInstances();
        });
    }

    async function testInstance(id) {
        try {
            const result = await api("POST", `/api/instances/${id}/test`);
            if (result.reachable) {
                showModal(`${tl("connection_ok")} (${result.monitor_count} monitors)`, "success");
            } else {
                showModal(`${tl("connection_failed")}: ${result.error}`, "error");
            }
        } catch (e) {
            showModal(e.message, "error");
        }
    }

    // --- Monitors ---

    async function loadMonitors() {
        const data = await api("GET", "/api/monitors");
        const tbody = document.querySelector("#monitors-table tbody");
        const nav = document.getElementById("monitors-nav");
        tbody.innerHTML = "";
        nav.innerHTML = "";

        // Build nav + separator rows
        const instances = [];
        let lastInstance = null;
        data.forEach(m => {
            if (m.instance_name !== lastInstance) {
                lastInstance = m.instance_name;
                const anchorId = "inst-" + m.instance_id;
                instances.push({ id: anchorId, name: m.instance_name });

                const sep = document.createElement("tr");
                sep.className = "monitor-instance-sep";
                sep.id = anchorId;
                sep.innerHTML = `<td colspan="3"><strong>${esc(m.instance_name)}</strong></td>`;
                tbody.appendChild(sep);
            }
            const tr = document.createElement("tr");
            tr.dataset.instanceId = m.instance_id;
            tr.dataset.kumaId = m.kuma_id;
            tr.className = "monitor-tree-row";
            const indent = m.depth * 20;
            const prefix = m.depth > 0 ? '<span class="tree-branch">\u2514</span>' : '';
            const nameClass = m.has_children ? "monitor-parent-name" : "";
            tr.innerHTML = `
                <td style="padding-left:${12 + indent}px">${prefix}<span class="dot dot-${m.status}" style="display:inline-block;width:10px;height:10px;vertical-align:middle;margin:0 8px 0 ${m.depth > 0 ? 4 : 0}px"></span><span class="${nameClass}">${esc(m.name)}</span></td>
                <td><span class="dot dot-${m.status}" style="display:inline-block;width:8px;height:8px;vertical-align:middle;margin-right:4px"></span><span class="monitor-status-label">${tl(m.status)}</span></td>
                <td>
                    <label class="toggle">
                        <input type="checkbox" ${!m.hidden ? "checked" : ""}>
                        <span class="toggle-slider"></span>
                    </label>
                </td>`;
            tr.addEventListener("click", function (e) {
                if (e.target.closest(".toggle")) return;
                const cb = tr.querySelector("input[type=checkbox]");
                cb.checked = !cb.checked;
                toggleMonitor(parseInt(tr.dataset.instanceId), parseInt(tr.dataset.kumaId), cb.checked);
            });
            tr.querySelector("input[type=checkbox]").addEventListener("change", function () {
                toggleMonitor(parseInt(tr.dataset.instanceId), parseInt(tr.dataset.kumaId), this.checked);
            });
            tbody.appendChild(tr);
        });

        // Build sidebar nav
        const navButtons = [];
        instances.forEach((inst, i) => {
            const btn = document.createElement("button");
            btn.className = "monitors-nav-item" + (i === 0 ? " active" : "");
            btn.textContent = inst.name;
            btn.title = inst.name;
            btn.dataset.anchor = inst.id;
            btn.addEventListener("click", function () {
                navButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                document.getElementById(inst.id).scrollIntoView({ behavior: "smooth", block: "start" });
            });
            nav.appendChild(btn);
            navButtons.push(btn);
        });

        // Scroll spy: highlight nav item for visible instance
        if (instances.length > 1) {
            const scrollContainer = document.querySelector(".monitors-main") || window;
            const onScroll = () => {
                let activeId = instances[0].id;
                for (const inst of instances) {
                    const el = document.getElementById(inst.id);
                    if (el) {
                        const rect = el.getBoundingClientRect();
                        if (rect.top <= 120) activeId = inst.id;
                    }
                }
                navButtons.forEach(b => {
                    b.classList.toggle("active", b.dataset.anchor === activeId);
                });
            };
            window.addEventListener("scroll", onScroll, { passive: true });
        }
    }

    async function toggleMonitor(instanceId, kumaId, visible) {
        if (visible) {
            await api("DELETE", "/api/monitors/hide", { instance_id: instanceId, kuma_monitor_id: kumaId });
        } else {
            await api("POST", "/api/monitors/hide", { instance_id: instanceId, kuma_monitor_id: kumaId });
        }
    }

    // --- Incidents ---

    let incidentItems = [];

    async function loadIncidents() {
        incidentItems = await api("GET", "/api/incidents");
        renderIncidentList();
    }

    function renderIncidentList() {
        const list = document.getElementById("incidents-list");
        list.innerHTML = "";
        incidentItems.forEach(inc => {
            const div = document.createElement("div");
            div.className = "sortable-item";
            div.draggable = true;
            div.dataset.id = inc.id;
            const label = currentLang === "de" ? inc.title_de : inc.title_en;
            const date = inc.occurred_at ? inc.occurred_at.replace("T", " ").slice(0, 16) : "";
            const sevColors = { info: "var(--blue)", warning: "var(--yellow)", critical: "var(--red)" };
            const activeIcon = inc.active ? "\u25cf" : "\u25cb";
            div.innerHTML = `
                <span class="drag-handle">&#9776;</span>
                <span style="color:${sevColors[inc.severity] || "var(--gray)"};font-size:10px">${activeIcon}</span>
                <span class="item-label">${esc(label)}</span>
                <span class="item-url">${esc(date)}</span>
                <button class="btn btn-sm" onclick="event.stopPropagation(); Admin.editIncident(${inc.id})">${tl("edit")}</button>
                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); Admin.confirmDeleteIncident(this, ${inc.id})">${tl("delete")}</button>`;
            div.addEventListener("dragstart", onIncDragStart);
            div.addEventListener("dragover", onIncDragOver);
            div.addEventListener("dragleave", onIncDragLeave);
            div.addEventListener("drop", onIncDrop);
            div.addEventListener("dragend", onIncDragEnd);
            list.appendChild(div);
        });
    }

    let incDragSrcId = null;
    function onIncDragStart(e) { incDragSrcId = e.currentTarget.dataset.id; e.currentTarget.style.opacity = "0.4"; e.dataTransfer.effectAllowed = "move"; }
    function onIncDragOver(e) { e.preventDefault(); e.currentTarget.classList.add("drag-over"); }
    function onIncDragLeave(e) { e.currentTarget.classList.remove("drag-over"); }
    async function onIncDrop(e) {
        e.preventDefault(); e.currentTarget.classList.remove("drag-over");
        const targetId = e.currentTarget.dataset.id;
        if (incDragSrcId === targetId) return;
        const srcIdx = incidentItems.findIndex(i => String(i.id) === incDragSrcId);
        const tgtIdx = incidentItems.findIndex(i => String(i.id) === targetId);
        const [moved] = incidentItems.splice(srcIdx, 1);
        incidentItems.splice(tgtIdx, 0, moved);
        renderIncidentList();
        await api("POST", "/api/incidents/reorder", { incident_ids: incidentItems.map(i => i.id) });
    }
    function onIncDragEnd(e) { e.currentTarget.style.opacity = ""; document.querySelectorAll(".sortable-item").forEach(el => el.classList.remove("drag-over")); }

    function nowLocal() {
        const d = new Date();
        return d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0") + "-" + String(d.getDate()).padStart(2,"0") + "T" + String(d.getHours()).padStart(2,"0") + ":" + String(d.getMinutes()).padStart(2,"0");
    }

    function showIncidentForm(inc) {
        document.getElementById("incident-form").style.display = "";
        document.getElementById("inc-id").value = inc ? inc.id : "";
        document.getElementById("inc-title-de").value = inc ? inc.title_de : "";
        document.getElementById("inc-title-en").value = inc ? inc.title_en : "";
        document.getElementById("inc-content-de").value = inc ? inc.content_de : "";
        document.getElementById("inc-content-en").value = inc ? inc.content_en : "";
        document.getElementById("inc-severity").value = inc ? inc.severity : "warning";
        document.getElementById("inc-occurred-at").value = inc ? (inc.occurred_at || "").slice(0, 16) : nowLocal();
        document.getElementById("inc-active").checked = inc ? inc.active : true;
    }

    function hideIncidentForm() {
        document.getElementById("incident-form").style.display = "none";
    }

    async function editIncident(id) {
        const inc = incidentItems.find(i => i.id === id);
        if (inc) showIncidentForm(inc);
    }

    async function saveIncident() {
        const id = document.getElementById("inc-id").value;
        const body = {
            title_de: document.getElementById("inc-title-de").value,
            title_en: document.getElementById("inc-title-en").value,
            content_de: document.getElementById("inc-content-de").value,
            content_en: document.getElementById("inc-content-en").value,
            severity: document.getElementById("inc-severity").value,
            occurred_at: document.getElementById("inc-occurred-at").value,
            active: document.getElementById("inc-active").checked,
        };
        try {
            if (id) {
                await api("PUT", `/api/incidents/${id}`, body);
            } else {
                await api("POST", "/api/incidents", body);
            }
            hideIncidentForm();
            await loadIncidents();
        } catch (e) {
            showModal(e.message, "error");
        }
    }

    async function confirmDeleteIncident(btn, id) {
        await confirmDelete(btn, async () => {
            await api("DELETE", `/api/incidents/${id}`);
            await loadIncidents();
        });
    }

    // --- Footer (with drag & drop) ---

    let footerItems = [];

    async function loadFooter() {
        footerItems = await api("GET", "/api/footer");
        renderFooterList();
    }

    function renderFooterList() {
        const list = document.getElementById("footer-list");
        list.innerHTML = "";
        footerItems.forEach(item => {
            const div = document.createElement("div");
            div.className = "sortable-item";
            div.draggable = true;
            div.dataset.id = item.id;
            const label = currentLang === "de" ? item.label_de : item.label_en;
            div.innerHTML = `
                <span class="drag-handle">&#9776;</span>
                <span class="item-label">${esc(label)}</span>
                ${item.url ? `<span class="item-url">${esc(item.url)}</span>` : ""}
                <button class="btn btn-sm" onclick="Admin.editFooterItem(${item.id})">${tl("edit")}</button>
                <button class="btn btn-sm btn-danger" onclick="Admin.confirmDeleteFooterItem(this, ${item.id})">${tl("delete")}</button>`;
            div.addEventListener("dragstart", onDragStart);
            div.addEventListener("dragover", onDragOver);
            div.addEventListener("dragleave", onDragLeave);
            div.addEventListener("drop", onDrop);
            div.addEventListener("dragend", onDragEnd);
            list.appendChild(div);
        });
    }

    let dragSrcId = null;

    function onDragStart(e) {
        dragSrcId = e.currentTarget.dataset.id;
        e.currentTarget.style.opacity = "0.4";
        e.dataTransfer.effectAllowed = "move";
    }

    function onDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add("drag-over");
    }

    function onDragLeave(e) {
        e.currentTarget.classList.remove("drag-over");
    }

    async function onDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove("drag-over");
        const targetId = e.currentTarget.dataset.id;
        if (dragSrcId === targetId) return;

        const srcIdx = footerItems.findIndex(i => String(i.id) === dragSrcId);
        const tgtIdx = footerItems.findIndex(i => String(i.id) === targetId);
        const [moved] = footerItems.splice(srcIdx, 1);
        footerItems.splice(tgtIdx, 0, moved);

        renderFooterList();
        await api("POST", "/api/footer/reorder", { item_ids: footerItems.map(i => i.id) });
    }

    function onDragEnd(e) {
        e.currentTarget.style.opacity = "";
        document.querySelectorAll(".sortable-item").forEach(el => el.classList.remove("drag-over"));
    }

    function showFooterForm(item) {
        document.getElementById("footer-form").style.display = "";
        document.getElementById("ft-id").value = item ? item.id : "";
        document.getElementById("ft-label-de").value = item ? item.label_de : "";
        document.getElementById("ft-label-en").value = item ? item.label_en : "";
        document.getElementById("ft-url").value = item ? item.url : "";
    }

    function hideFooterForm() {
        document.getElementById("footer-form").style.display = "none";
    }

    async function editFooterItem(id) {
        const item = footerItems.find(i => i.id === id);
        if (item) showFooterForm(item);
    }

    async function saveFooterItem() {
        const id = document.getElementById("ft-id").value;
        const body = {
            label_de: document.getElementById("ft-label-de").value,
            label_en: document.getElementById("ft-label-en").value,
            url: document.getElementById("ft-url").value,
        };
        try {
            if (id) {
                await api("PUT", `/api/footer/${id}`, body);
            } else {
                await api("POST", "/api/footer", body);
            }
            hideFooterForm();
            await loadFooter();
        } catch (e) {
            showModal(e.message, "error");
        }
    }

    async function confirmDeleteFooterItem(btn, id) {
        await confirmDelete(btn, async () => {
            await api("DELETE", `/api/footer/${id}`);
            await loadFooter();
        });
    }

    // --- Settings ---

    async function loadSettings() {
        const data = await api("GET", "/api/settings");
        document.getElementById("set-title-de").value = data.page_title_de || "";
        document.getElementById("set-title-en").value = data.page_title_en || "";
        document.getElementById("set-lang").value = data.default_lang || "en";
        document.getElementById("set-notice-de").value = data.notice_de || "";
        document.getElementById("set-notice-en").value = data.notice_en || "";
        document.getElementById("set-ticket-url").value = data.ticket_url || "";
        document.getElementById("set-ticket-label-de").value = data.ticket_label_de || "";
        document.getElementById("set-ticket-label-en").value = data.ticket_label_en || "";

        const logoLight = data.logo_light;
        const logoDark = data.logo_dark;
        if (logoLight) {
            const img = document.getElementById("logo-light-preview");
            img.src = logoLight + "?t=" + Date.now();
            img.style.display = "";
        }
        if (logoDark) {
            const img = document.getElementById("logo-dark-preview");
            img.src = logoDark + "?t=" + Date.now();
            img.style.display = "";
        }
    }

    async function saveSettings() {
        const settings = [
            { key: "page_title_de", value: document.getElementById("set-title-de").value },
            { key: "page_title_en", value: document.getElementById("set-title-en").value },
            { key: "default_lang", value: document.getElementById("set-lang").value },
            { key: "notice_de", value: document.getElementById("set-notice-de").value },
            { key: "notice_en", value: document.getElementById("set-notice-en").value },
            { key: "ticket_url", value: document.getElementById("set-ticket-url").value },
            { key: "ticket_label_de", value: document.getElementById("set-ticket-label-de").value },
            { key: "ticket_label_en", value: document.getElementById("set-ticket-label-en").value },
        ];
        for (const s of settings) {
            await api("PUT", "/api/settings", s);
        }
        await loadSettings();
    }

    async function uploadLogo(variant) {
        const input = document.getElementById(`logo-${variant}-file`);
        if (!input.files.length) return;
        const form = new FormData();
        form.append("file", input.files[0]);
        const res = await fetch(`/api/settings/logo/${variant}`, { method: "POST", body: form });
        const data = await res.json();
        const preview = document.getElementById(`logo-${variant}-preview`);
        preview.src = data.path + "?t=" + Date.now();
        preview.style.display = "";
    }

    // --- Init ---

    document.addEventListener("DOMContentLoaded", function () {
        applyTheme(currentTheme);
        setLang(currentLang);

        document.getElementById("theme-toggle").addEventListener("click", cycleTheme);
        document.getElementById("lang-toggle").addEventListener("click", () => {
            setLang(currentLang === "en" ? "de" : "en");
        });

        initTabs();
        loadInstances();
    });

    return {
        showInstanceForm: () => showInstanceForm(),
        hideInstanceForm,
        saveInstance,
        editInstance,
        confirmDeleteInstance,
        testInstance,
        toggleMonitor,
        showIncidentForm: () => showIncidentForm(),
        hideIncidentForm,
        saveIncident,
        editIncident,
        confirmDeleteIncident,
        showFooterForm: () => showFooterForm(),
        hideFooterForm,
        saveFooterItem,
        editFooterItem,
        confirmDeleteFooterItem,
        saveSettings,
        uploadLogo,
        closeModal,
        copySnippet,
    };
})();
