// ===== Uptime Status - Public Page JS =====

(function () {
    "use strict";

    let currentLang = localStorage.getItem("us_lang") || document.documentElement.lang || "en";
    let currentTheme = localStorage.getItem("us_theme") || "auto";
    let ws = null;
    let reconnectTimer = null;

    // --- Theme ---

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
        updateLogo();
    }

    function cycleTheme() {
        const order = ["light", "dark", "auto"];
        const next = order[(order.indexOf(currentTheme) + 1) % order.length];
        applyTheme(next);
    }

    function isDarkActive() {
        if (currentTheme === "dark") return true;
        if (currentTheme === "light") return false;
        return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }

    function updateLogo() {
        const logo = document.getElementById("logo");
        if (!logo) return;
        const src = isDarkActive() ? logo.dataset.dark : logo.dataset.light;
        if (src) {
            logo.src = src;
            logo.style.display = "";
        } else {
            logo.style.display = "none";
        }
    }

    // --- i18n ---

    function tl(key) {
        return (I18N[currentLang] || {})[key] || key;
    }

    function setLang(lang) {
        currentLang = lang;
        localStorage.setItem("us_lang", lang);
        document.documentElement.lang = lang;
        document.getElementById("lang-label").textContent = lang.toUpperCase();

        document.querySelectorAll("[data-i18n]").forEach(el => {
            if (el.id === "page-title") return; // title from settings, not i18n
            const key = el.getAttribute("data-i18n");
            const text = (I18N[lang] || {})[key];
            if (text) el.textContent = text;
        });

        // Update title from settings
        if (typeof STATUS_DATA !== "undefined") {
            const title = (STATUS_DATA.settings || {})["page_title_" + lang];
            if (title) document.getElementById("page-title").textContent = title;
        }

        // Update incidents and footer with language-specific content
        if (typeof STATUS_DATA !== "undefined") {
            updateIncidents(STATUS_DATA.incidents);
            updateFooter(STATUS_DATA.footer_items);
        }
    }

    function cycleLang() {
        setLang(currentLang === "en" ? "de" : "en");
    }

    // --- WebSocket + HTTP fallback ---

    function connectWS() {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        ws = new WebSocket(`${proto}//${location.host}/ws`);

        ws.onmessage = function (e) {
            const msg = JSON.parse(e.data);
            if (msg.type === "full") {
                window.STATUS_DATA = msg.data;
                renderFull(msg.data);
            } else if (msg.type === "incident") {
                handleIncidentUpdate(msg);
            }
        };

        ws.onclose = function () {
            ws = null;
            reconnectTimer = setTimeout(connectWS, 3000);
        };

        ws.onerror = function () {
            ws && ws.close();
        };
    }

    // Fallback: poll via HTTP every 30s in case WS is flaky
    async function pollStatus() {
        try {
            const resp = await fetch("/api/status");
            if (resp.ok) {
                const data = await resp.json();
                window.STATUS_DATA = data;
                renderFull(data);
            }
        } catch (e) { /* ignore */ }
    }

    setInterval(pollStatus, 10000);

    // --- Render ---

    function renderFull(data) {
        updateOverallBanner(data);
        updatePageTitle(data.settings || {});
        updateIncidents(data.incidents);
        updateIssues(data);
        updateMonitorGrid(data);
        updateFooter(data.footer_items);
        updateFooterNotice(data.settings || {});
        updateLogoFromSettings(data.settings || {});
        requestAnimationFrame(balanceColumns);
    }

    function updateIssues(data) {
        const container = document.getElementById("issues-container");
        if (!container) return;
        const issues = [];
        const maintenance = [];
        const multiInstance = (data.instances || []).length > 1;
        (data.instances || []).forEach(inst => {
            collectIssues(inst.groups || [], inst.name, [], issues, maintenance, multiInstance);
        });
        container.innerHTML = "";

        if (issues.length > 0) {
            container.appendChild(buildIssueBox(
                "issues-box-issues",
                (I18N[currentLang] || {}).some_issues || "Some systems are experiencing issues",
                issues
            ));
        }

        if (maintenance.length > 0) {
            container.appendChild(buildIssueBox(
                "issues-box-maintenance",
                (I18N[currentLang] || {}).under_maintenance || "Under maintenance",
                maintenance
            ));
        }
    }

    function buildIssueBox(cssClass, titleText, items) {
        const box = document.createElement("div");
        box.className = "issues-box " + cssClass;
        const title = document.createElement("div");
        title.className = "issues-title";
        title.textContent = titleText;
        box.appendChild(title);
        items.forEach(iss => {
            const row = document.createElement("div");
            row.className = "issue-row";
            const path = iss.path ? `<span class="issue-path">${esc(iss.path)}</span>` : "";
            row.innerHTML = `<span class="dot dot-${iss.status}"></span>${path}<span class="issue-name">${esc(iss.name)}</span>`;
            box.appendChild(row);
        });
        return box;
    }

    function collectIssues(nodes, instanceName, parents, issues, maintenance, multiInstance) {
        nodes.forEach(n => {
            const path = multiInstance
                ? [instanceName, ...parents].join(" \u203a ")
                : parents.length > 0 ? parents.join(" \u203a ") : "";
            const isGroup = n.children && n.children.length > 0;
            if (!isGroup) {
                if (n.status === "maintenance") {
                    maintenance.push({ name: n.name, status: n.status, path: path });
                } else if (n.status && n.status !== "up" && n.status !== "unknown" && n.status !== "inactive") {
                    issues.push({ name: n.name, status: n.status, path: path });
                }
            }
            if (n.children) {
                collectIssues(n.children, instanceName, [...parents, n.name], issues, maintenance, multiInstance);
            }
        });
    }

    function updatePageTitle(settings) {
        const title = settings["page_title_" + currentLang];
        const el = document.getElementById("page-title");
        if (el && title) el.textContent = title;
    }

    function updateLogoFromSettings(settings) {
        const logo = document.getElementById("logo");
        if (!logo) return;
        const light = settings.logo_light || "";
        const dark = settings.logo_dark || "";
        if (logo.dataset.light === light && logo.dataset.dark === dark) return;
        logo.dataset.light = light;
        logo.dataset.dark = dark;
        updateLogo();
        logo.style.display = (light || dark) ? "" : "none";
    }

    function updateOverallBanner(data) {
        const statuses = [];
        (data.instances || []).forEach(inst => collectStatuses(inst.groups || [], statuses));

        let overall = "unknown";
        if (statuses.length === 0) overall = "unknown";
        else if (statuses.includes("down")) overall = "down";
        else if (statuses.some(s => ["pending", "unreachable"].includes(s))) overall = "degraded";
        else overall = "up";

        const key = overall === "up" ? "all_operational" : (overall === "down" ? "major_outage" : "some_issues");
        const text = (I18N[currentLang] || {})[key] || key;

        const headerStatus = document.getElementById("header-status");
        if (headerStatus) {
            headerStatus.className = "header-status overall-" + overall;
            headerStatus.textContent = text;
        }
    }

    function collectStatuses(nodes, out) {
        nodes.forEach(n => {
            out.push(n.status);
            if (n.children) collectStatuses(n.children, out);
        });
    }

    function updateIncidents(incidents) {
        const container = document.getElementById("incidents-container");
        container.innerHTML = "";
        (incidents || []).forEach(inc => {
            if (!inc.active) return;
            const div = document.createElement("div");
            div.className = "incident incident-" + inc.severity;
            div.dataset.incidentId = inc.id;
            const title = currentLang === "de" ? inc.title_de : inc.title_en;
            const content = currentLang === "de" ? inc.content_de : inc.content_en;
            const date = inc.occurred_at ? inc.occurred_at.replace("T", " ").slice(0, 16) : "";
            const sevLabel = tl("severity_" + inc.severity);
            let html = `<span class="incident-severity">${esc(sevLabel)}</span>`;
            html += `<strong class="incident-title">${esc(title)}</strong>`;
            if (date) html += `<span class="incident-date">${esc(date)}</span>`;
            if (content) html += `<span class="incident-content">${esc(content)}</span>`;
            div.innerHTML = html;
            container.appendChild(div);
        });
    }

    function updateMonitorGrid(data) {
        const grid = document.getElementById("monitor-grid");
        grid.innerHTML = "";
        const multiInstance = (data.instances || []).length > 1;

        (data.instances || []).forEach(inst => {
            if (multiInstance) {
                const hdr = document.createElement("div");
                hdr.className = "instance-header";
                let html = `<h2>${esc(inst.name)}</h2>`;
                if (!inst.reachable) {
                    const label = (I18N[currentLang] || {}).unreachable || "Unreachable";
                    html += `<span class="badge badge-unreachable">${esc(label)}</span>`;
                }
                hdr.innerHTML = html;
                grid.appendChild(hdr);
            }

            (inst.groups || []).forEach(group => {
                const card = document.createElement("div");
                card.className = "monitor-card" + (!inst.reachable ? " card-unreachable" : "");

                if (group.children && group.children.length > 0) {
                    card.innerHTML =
                        `<div class="card-header"><span class="dot dot-${group.status}"></span><h3>${esc(group.name)}</h3></div>` +
                        `<div class="card-body">${renderChildren(group.children)}</div>`;
                } else {
                    card.innerHTML =
                        `<div class="monitor-row" data-monitor-id="${group.id}"><span class="dot dot-${group.status}"></span><span class="monitor-name">${esc(group.name)}</span></div>`;
                }
                grid.appendChild(card);
            });
        });
    }

    function renderChildren(children) {
        let html = "";
        children.forEach(child => {
            html += `<div class="monitor-row" data-monitor-id="${child.id}"><span class="dot dot-${child.status}"></span><span class="monitor-name">${esc(child.name)}</span></div>`;
            if (child.children) {
                child.children.forEach(sub => {
                    html += `<div class="monitor-row monitor-row-nested" data-monitor-id="${sub.id}"><span class="dot dot-${sub.status}"></span><span class="monitor-name">${esc(sub.name)}</span></div>`;
                });
            }
        });
        return html;
    }

    function balanceColumns() {
        const grid = document.getElementById("monitor-grid");
        if (!grid) return;

        const cs = getComputedStyle(grid);
        const colCount = parseInt(cs.columnCount) || Math.max(1, Math.floor(grid.clientWidth / 320));
        if (colCount < 2) return;

        // Split children into groups: each group is either a single
        // instance-header or a run of consecutive monitor-cards
        const groups = [];
        let currentCards = [];
        Array.from(grid.children).forEach(el => {
            if (el.classList.contains("instance-header")) {
                if (currentCards.length > 0) {
                    groups.push({ type: "cards", els: currentCards });
                    currentCards = [];
                }
                groups.push({ type: "header", el: el });
            } else if (el.classList.contains("monitor-card")) {
                currentCards.push(el);
            }
        });
        if (currentCards.length > 0) {
            groups.push({ type: "cards", els: currentCards });
        }

        // Balance each card group independently
        const ordered = [];
        groups.forEach(g => {
            if (g.type === "header") {
                ordered.push(g.el);
            } else {
                balanceCardGroup(g.els, colCount).forEach(el => ordered.push(el));
            }
        });

        // Apply new order
        let changed = false;
        const children = Array.from(grid.children);
        for (let i = 0; i < ordered.length; i++) {
            if (children[i] !== ordered[i]) { changed = true; break; }
        }
        if (changed) {
            ordered.forEach(el => grid.appendChild(el));
        }

    }

    function balanceCardGroup(cards, colCount) {
        if (cards.length < 2) return cards;

        const items = cards.map(el => ({ el, h: el.offsetHeight }));

        // Greedy bin-packing: tallest first, assign to shortest column
        items.sort((a, b) => b.h - a.h);
        const cols = Array.from({ length: colCount }, () => ({ h: 0, items: [] }));
        items.forEach(item => {
            const shortest = cols.reduce((min, c) => c.h < min.h ? c : min, cols[0]);
            shortest.items.push(item);
            shortest.h += item.h;
        });

        // CSS columns fill top-to-bottom per column
        return cols.flatMap(c => c.items.map(i => i.el));
    }

    function updateFooter(items) {
        const container = document.querySelector(".footer-items");
        if (!container) return;
        container.innerHTML = "";
        (items || []).forEach((item, i) => {
            const label = currentLang === "de" ? item.label_de : item.label_en;
            const span = document.createElement("span");
            span.className = "footer-item";
            if (item.url) {
                span.innerHTML = `<a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(label)}</a>`;
            } else {
                span.textContent = label;
            }
            container.appendChild(span);
            if (i < items.length - 1) {
                const sep = document.createElement("span");
                sep.className = "footer-sep";
                sep.innerHTML = "&middot;";
                container.appendChild(sep);
            }
        });
    }

    function updateFooterNotice(settings) {
        const container = document.getElementById("footer-notice");
        if (!container) return;
        container.innerHTML = "";
        const notice = settings["notice_" + currentLang] || "";
        const ticketUrl = settings.ticket_url || "";
        const ticketLabel = settings["ticket_label_" + currentLang] || ticketUrl;
        if (notice) {
            const span = document.createElement("span");
            span.className = "footer-notice-text";
            span.textContent = notice;
            container.appendChild(span);
        }
        if (ticketUrl) {
            const a = document.createElement("a");
            a.className = "footer-ticket-link";
            a.href = ticketUrl;
            a.target = "_blank";
            a.rel = "noopener";
            a.textContent = ticketLabel;
            container.appendChild(a);
        }
    }

    function handleIncidentUpdate(msg) {
        // Re-fetch full status on incident changes for simplicity
        if (ws) {
            // The next full message from WS will update everything
        }
    }

    function esc(str) {
        const div = document.createElement("div");
        div.textContent = str || "";
        return div.innerHTML;
    }

    // --- Init ---

    document.addEventListener("DOMContentLoaded", function () {
        applyTheme(currentTheme);
        setLang(currentLang);

        document.getElementById("theme-toggle").addEventListener("click", cycleTheme);
        document.getElementById("lang-toggle").addEventListener("click", cycleLang);

        // Listen for OS theme changes
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
            if (currentTheme === "auto") updateLogo();
        });

        connectWS();

        let resizeTimer;
        window.addEventListener("resize", function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(balanceColumns, 150);
        });
    });
})();
