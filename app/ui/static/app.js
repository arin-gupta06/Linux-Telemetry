/**
 * AlgoFight Linux Telemetry & Evaluation Service Dashboard Frontend
 */

document.addEventListener("DOMContentLoaded", () => {
    // Tab switching logic
    const tabs = document.querySelectorAll(".nav-tab");
    const contents = document.querySelectorAll(".tab-content");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            contents.forEach(c => c.classList.remove("active"));

            tab.classList.add("active");
            const target = document.getElementById(tab.dataset.tab);
            if (target) target.classList.add("active");
        });
    });

    // Time-series history buffers for canvas drawing
    const historyLength = 30;
    const timeLabels = [];
    const cpuHistory = [];
    const ramHistory = [];
    const throughputHistory = [];
    const lightQueueHistory = [];
    const heavyQueueHistory = [];

    // Canvas charts init
    const cpuCanvas = document.getElementById("chart-cpu");
    const ramCanvas = document.getElementById("chart-ram");
    const tpCanvas = document.getElementById("chart-throughput");
    const qCanvas = document.getElementById("chart-queues");

    function drawLineChart(canvas, dataSeries, color = "#06b6d4", maxVal = 100) {
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
        ctx.lineWidth = 1;
        for (let i = 0; i < 4; i++) {
            const y = (h / 4) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        if (dataSeries.length < 2) return;

        ctx.beginPath();
        const step = w / (historyLength - 1);
        const effectiveMax = Math.max(maxVal, ...dataSeries, 1);

        for (let i = 0; i < dataSeries.length; i++) {
            const x = i * step;
            const normalized = dataSeries[i] / effectiveMax;
            const y = h - (normalized * (h - 20) + 10);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }

        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.stroke();

        ctx.lineTo((dataSeries.length - 1) * step, h);
        ctx.lineTo(0, h);
        ctx.closePath();

        const grad = ctx.createLinearGradient(0, 0, 0, h);
        grad.addColorStop(0, color.replace(")", ", 0.25)").replace("rgb", "rgba"));
        grad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = grad;
        ctx.fill();
    }

    // Pino Log Terminal State
    let logEntries = [];
    let currentFilterLevel = "all";
    let currentSearchQuery = "";
    const terminal = document.getElementById("log-terminal");
    const searchInput = document.getElementById("log-search-input");
    const autoScroll = document.getElementById("chk-autoscroll");
    const logModal = document.getElementById("log-modal");
    const logJsonContent = document.getElementById("log-json-content");
    const btnCloseModal = document.getElementById("btn-close-modal");

    if (btnCloseModal) {
        btnCloseModal.addEventListener("click", () => {
            logModal.style.display = "none";
        });
    }

    document.querySelectorAll(".pill-filter").forEach(pill => {
        pill.addEventListener("click", () => {
            document.querySelectorAll(".pill-filter").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentFilterLevel = pill.dataset.level;
            renderLogs();
        });
    });

    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            currentSearchQuery = e.target.value.toLowerCase();
            renderLogs();
        });
    }

    function renderLogs() {
        if (!terminal) return;
        const filtered = logEntries.filter(entry => {
            if (currentFilterLevel !== "all" && entry.level < parseInt(currentFilterLevel)) {
                return false;
            }
            if (currentSearchQuery) {
                const text = `${entry.msg} ${entry.name} ${entry.submission_id || ""} ${entry.battle_id || ""} ${entry.user_id || ""}`.toLowerCase();
                return text.includes(currentSearchQuery);
            }
            return true;
        });

        if (filtered.length === 0) {
            terminal.innerHTML = '<div class="terminal-empty">No matching logs found.</div>';
            return;
        }

        terminal.innerHTML = "";
        filtered.forEach(entry => {
            const row = document.createElement("div");
            row.className = "log-line";
            row.addEventListener("click", () => showLogDetail(entry));

            const timeStr = new Date(entry.time).toLocaleTimeString();
            const badgeClass = `lvl-${entry.level}`;

            let pills = "";
            if (entry.submission_id) pills += `<span class="log-extra-pill">${entry.submission_id}</span> `;
            if (entry.battle_id) pills += `<span class="log-extra-pill">${entry.battle_id}</span> `;

            row.innerHTML = `
                <span class="log-time">${timeStr}</span>
                <span class="log-badge ${badgeClass}">${entry.level_name.toUpperCase()}</span>
                <span class="log-name">[${entry.name}]</span>
                <span class="log-msg">${escapeHtml(entry.msg)} ${pills}</span>
            `;
            terminal.appendChild(row);
        });

        if (autoScroll && autoScroll.checked) {
            terminal.scrollTop = terminal.scrollHeight;
        }

        const badge = document.getElementById("badge-logs-count");
        if (badge) badge.innerText = logEntries.length;
    }

    function showLogDetail(entry) {
        if (!logModal || !logJsonContent) return;
        logJsonContent.innerText = JSON.stringify(entry.raw || entry, null, 2);
        logModal.style.display = "flex";
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Battles Visualizer (Supports Any Battle Type: 1v1, Multiplayer FFA, Solo, Tournament)
    function renderBattles(battles) {
        const container = document.getElementById("battles-container");
        if (!container) return;

        if (!battles || battles.length === 0) {
            container.innerHTML = '<div class="terminal-empty glass-card">No battles ingested yet. Run a match or use the injector.</div>';
            return;
        }

        container.innerHTML = "";
        battles.forEach(b => {
            const card = document.createElement("div");
            card.className = "battle-card glass-card";

            const participants = b.participants && b.participants.length > 0 
                ? b.participants 
                : [b.player1, b.player2].filter(Boolean);

            const bType = b.battle_type || (participants.length <= 2 ? "1v1 DUEL" : `FFA (${participants.length} PLAYERS)`);

            let participantsHtml = '<div class="battle-participants-grid">';
            participants.forEach((p, idx) => {
                const isWinner = b.winner_id === p.user_id || p.rank === 1;
                const rankBadge = p.rank ? `<span class="rank-pill">#${p.rank}</span>` : "";

                participantsHtml += `
                    <div class="player-box ${isWinner ? 'winner-glow' : ''}">
                        <div class="player-name">
                            ${isWinner ? '<span class="crown-icon">👑</span>' : ''}
                            ${rankBadge}
                            <span>${p.username || p.user_id}</span>
                            <span class="lang-tag">${(p.language || 'cpp').toUpperCase()}</span>
                        </div>
                        <div class="player-stat"><span>Time</span><strong>${(p.execution_time_ms || 0).toFixed(1)} ms</strong></div>
                        <div class="player-stat"><span>Memory</span><strong>${(p.peak_memory_kb || 0).toFixed(0)} KB</strong></div>
                        <div class="player-stat"><span>Score</span><strong>${p.score || 0} pts</strong></div>
                        <div class="player-stat"><span>Verdict</span><strong class="${p.verdict === 'ACCEPTED' ? 'text-success' : 'text-danger'}">${p.verdict} (${p.tests_passed || 0}/${p.tests_total || 0})</strong></div>
                    </div>
                `;
            });
            participantsHtml += '</div>';

            card.innerHTML = `
                <div class="battle-header">
                    <div>
                        <div class="battle-id">${b.battle_id} • <span class="battle-type-tag">${bType.toUpperCase()}</span></div>
                        <div class="battle-problem">${b.problem_title || "Algorithm Challenge"}</div>
                    </div>
                    <span class="live-pill">${b.status}</span>
                </div>
                ${participantsHtml}
                <div class="battle-footer">
                    <span>Duration: <strong>${(b.duration_seconds || 0).toFixed(1)}s</strong></span>
                    ${b.speed_delta_ms > 0 ? `<span>Speed Δ: <strong>${b.speed_delta_ms.toFixed(1)} ms</strong></span>` : ''}
                    <span>${new Date(b.timestamp * 1000).toLocaleTimeString()}</span>
                </div>
            `;
            container.appendChild(card);
        });
    }

    // Stress Testing Sliders & Controls
    const sJobs = document.getElementById("stress-jobs");
    const sUsers = document.getElementById("stress-users");
    const sHeavy = document.getElementById("stress-heavy");
    const sFail = document.getElementById("stress-fail");

    if (sJobs) sJobs.addEventListener("input", e => document.getElementById("val-jobs").innerText = parseInt(e.target.value).toLocaleString());
    if (sUsers) sUsers.addEventListener("input", e => document.getElementById("val-users").innerText = e.target.value);
    if (sHeavy) sHeavy.addEventListener("input", e => document.getElementById("val-heavy").innerText = e.target.value + "%");
    if (sFail) sFail.addEventListener("input", e => document.getElementById("val-fail").innerText = e.target.value + "%");

    const btnStartStress = document.getElementById("btn-start-stress");
    const btnStopStress = document.getElementById("btn-stop-stress");

    if (btnStartStress) {
        btnStartStress.addEventListener("click", async () => {
            const config = {
                total_jobs: parseInt(sJobs.value),
                users: parseInt(sUsers.value),
                heavy_ratio: parseFloat(sHeavy.value) / 100.0,
                failure_rate: parseFloat(sFail.value) / 100.0,
                scenario: "concurrent"
            };

            try {
                const res = await fetch("/api/v1/stress/start", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                if (res.ok) {
                    btnStartStress.disabled = true;
                    btnStopStress.disabled = false;
                } else {
                    alert("Failed to start stress test: " + data.detail);
                }
            } catch (err) {
                alert("Error: " + err.message);
            }
        });
    }

    if (btnStopStress) {
        btnStopStress.addEventListener("click", async () => {
            try {
                await fetch("/api/v1/stress/stop", { method: "POST" });
                btnStartStress.disabled = false;
                btnStopStress.disabled = true;
            } catch (err) {
                alert("Error stopping stress test: " + err.message);
            }
        });
    }

    function updateStressStatus(stress) {
        if (!stress) return;
        const navBadge = document.getElementById("stress-nav-badge");
        const cardStatus = document.getElementById("stress-card-status");
        const isRunning = stress.state === "running" || stress.state === "starting";

        if (navBadge) {
            navBadge.innerText = stress.state.toUpperCase();
            navBadge.style.color = isRunning ? "#34d399" : "#94a3b8";
        }
        if (cardStatus) {
            cardStatus.innerText = stress.state.toUpperCase();
            cardStatus.className = `status-badge ${isRunning ? 'text-success' : ''}`;
        }

        if (btnStartStress && btnStopStress) {
            btnStartStress.disabled = isRunning;
            btnStopStress.disabled = !isRunning;
        }

        const progFill = document.getElementById("stress-progress-fill");
        const progText = document.getElementById("stress-progress-text");
        if (progFill) progFill.style.width = `${stress.progress_percent || 0}%`;
        if (progText) progText.innerText = `${stress.progress_percent || 0}% (${stress.completed_jobs || 0} / ${stress.total_jobs || 0})`;

        const lat = stress.end_to_end_latency_seconds || {};
        if (document.getElementById("p-avg")) document.getElementById("p-avg").innerText = `${(lat.avg || 0).toFixed(2)}s`;
        if (document.getElementById("p-p50")) document.getElementById("p-p50").innerText = `${(lat.p50 || 0).toFixed(2)}s`;
        if (document.getElementById("p-p90")) document.getElementById("p-p90").innerText = `${(lat.p90 || 0).toFixed(2)}s`;
        if (document.getElementById("p-p95")) document.getElementById("p-p95").innerText = `${(lat.p95 || 0).toFixed(2)}s`;
        if (document.getElementById("p-p99")) document.getElementById("p-p99").innerText = `${(lat.p99 || 0).toFixed(2)}s`;
        if (document.getElementById("p-max")) document.getElementById("p-max").innerText = `${(lat.max || 0).toFixed(2)}s`;

        if (document.getElementById("stress-time-tag")) document.getElementById("stress-time-tag").innerText = `Elapsed: ${(stress.elapsed_seconds || 0).toFixed(1)}s`;
        if (document.getElementById("stress-rps")) document.getElementById("stress-rps").innerText = `${(stress.throughput_rps || 0).toFixed(1)} RPS`;
        if (document.getElementById("stress-success")) document.getElementById("stress-success").innerText = stress.successful_jobs || 0;
        if (document.getElementById("stress-failed")) document.getElementById("stress-failed").innerText = `${stress.failed_jobs || 0} / ${stress.retry_events || 0}`;
        if (document.getElementById("stress-workers")) document.getElementById("stress-workers").innerText = stress.active_workers || 0;
    }

    // Ingestion Simulator Buttons
    const btnInjInfo = document.getElementById("btn-inject-pino-info");
    const btnInjWarn = document.getElementById("btn-inject-pino-warn");
    const btnInjErr = document.getElementById("btn-inject-pino-err");
    const btnInjExec = document.getElementById("btn-inject-execution");
    const btnInjBattle = document.getElementById("btn-inject-battle");
    const btnSendCustom = document.getElementById("btn-send-custom-json");
    const customJson = document.getElementById("custom-json-input");
    const alertBox = document.getElementById("inject-result-alert");

    async function sendLogPayload(payload) {
        try {
            const res = await fetch("/api/v1/telemetry/logs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            showAlert("Successfully injected log! " + JSON.stringify(data), true);
        } catch (err) {
            showAlert("Failed to inject log: " + err.message, false);
        }
    }

    function showAlert(msg, isSuccess) {
        if (!alertBox) return;
        alertBox.style.display = "block";
        alertBox.className = isSuccess ? "alert-box alert-success" : "alert-box alert-error";
        alertBox.innerText = msg;
        setTimeout(() => { alertBox.style.display = "none"; }, 4000);
    }

    if (btnInjInfo) {
        btnInjInfo.addEventListener("click", () => {
            sendLogPayload({
                level: 30,
                msg: "submission.queued: submission registered in BullMQ queue",
                name: "algofight-worker",
                submissionId: `sub-${Math.floor(Math.random() * 9000 + 1000)}`,
                userId: "user-alice",
            });
        });
    }

    if (btnInjWarn) {
        btnInjWarn.addEventListener("click", () => {
            sendLogPayload({
                level: 40,
                msg: "execution.warning: worker memory exceeded 80% soft limit",
                name: "algofight-worker",
                submissionId: `sub-${Math.floor(Math.random() * 9000 + 1000)}`,
                memoryKb: 64200,
            });
        });
    }

    if (btnInjErr) {
        btnInjErr.addEventListener("click", () => {
            sendLogPayload({
                level: 50,
                msg: "execution.failed: runtime exception in user submission sandbox",
                name: "algofight-executor",
                submissionId: `sub-${Math.floor(Math.random() * 9000 + 1000)}`,
                err: { type: "SegmentationFault", message: "SIGSEGV 11 address out of bounds" }
            });
        });
    }

    if (btnInjExec) {
        btnInjExec.addEventListener("click", async () => {
            const execPayload = {
                submission_id: `sub-${Math.floor(Math.random() * 9000 + 1000)}`,
                user_id: "user-charlie",
                problem_id: "two-sum",
                language: "cpp",
                compile_time_ms: Math.random() * 80 + 30,
                execution_time_ms: Math.random() * 50 + 10,
                cpu_time_ms: Math.random() * 45 + 10,
                peak_memory_kb: Math.random() * 8000 + 12000,
                verdict: "ACCEPTED",
                pass_count: 10,
                total_testcases: 10,
            };
            try {
                const res = await fetch("/api/v1/telemetry/ingest", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(execPayload)
                });
                const data = await res.json();
                showAlert("Execution telemetry ingested: " + data.submission_id, true);
            } catch (e) {
                showAlert("Error: " + e.message, false);
            }
        });
    }

    if (btnInjBattle) {
        btnInjBattle.addEventListener("click", async () => {
            const bId = `battle-${Math.floor(Math.random() * 9000 + 1000)}`;
            const battlePayload = {
                battle_id: bId,
                room_id: `room-${Math.floor(Math.random() * 900 + 100)}`,
                battle_type: "FFA_MULTIPLAYER",
                problem_id: "graph-dijkstra",
                problem_title: "Shortest Path Arena (4-Player FFA)",
                status: "FINISHED",
                duration_seconds: 18.5,
                participants: [
                    {
                        user_id: "player-alpha",
                        username: "AlphaCoder",
                        language: "cpp",
                        execution_time_ms: 18.2,
                        cpu_time_ms: 16.0,
                        peak_memory_kb: 14200,
                        score: 100,
                        rank: 1,
                        verdict: "ACCEPTED",
                        tests_passed: 15,
                        tests_total: 15,
                    },
                    {
                        user_id: "player-beta",
                        username: "BetaMaster",
                        language: "python",
                        execution_time_ms: 32.5,
                        cpu_time_ms: 30.1,
                        peak_memory_kb: 22400,
                        score: 80,
                        rank: 2,
                        verdict: "ACCEPTED",
                        tests_passed: 15,
                        tests_total: 15,
                    },
                    {
                        user_id: "player-gamma",
                        username: "GammaKnight",
                        language: "cpp",
                        execution_time_ms: 45.1,
                        cpu_time_ms: 43.0,
                        peak_memory_kb: 16800,
                        score: 60,
                        rank: 3,
                        verdict: "ACCEPTED",
                        tests_passed: 12,
                        tests_total: 15,
                    },
                    {
                        user_id: "player-delta",
                        username: "DeltaStrike",
                        language: "c",
                        execution_time_ms: 12.0,
                        cpu_time_ms: 11.2,
                        peak_memory_kb: 9800,
                        score: 0,
                        rank: 4,
                        verdict: "WRONG_ANSWER",
                        tests_passed: 5,
                        tests_total: 15,
                    }
                ],
                winner_id: "player-alpha",
            };
            try {
                const res = await fetch("/api/v1/telemetry/battle", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(battlePayload)
                });
                const data = await res.json();
                showAlert("Multiplayer FFA Battle match ingested: " + data.battle_id, true);
            } catch (e) {
                showAlert("Error: " + e.message, false);
            }
        });
    }

    if (btnSendCustom) {
        btnSendCustom.addEventListener("click", () => {
            try {
                const parsed = JSON.parse(customJson.value);
                sendLogPayload(parsed);
            } catch (e) {
                showAlert("Invalid JSON: " + e.message, false);
            }
        });
    }

    function connectSSE() {
        const sseStatus = document.getElementById("sse-status-pill");
        const eventSource = new EventSource("/api/v1/stream");

        eventSource.onopen = () => {
            if (sseStatus) {
                sseStatus.innerHTML = '<span class="live-beacon"></span> LIVE SSE STREAM';
                sseStatus.style.borderColor = "rgba(16, 185, 129, 0.3)";
                sseStatus.style.color = "#34d399";
            }
        };

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const vitals = data.vitals || {};

                document.getElementById("header-cpu").innerText = `${(vitals.cpu_percent || 0).toFixed(1)}%`;
                document.getElementById("header-cpu-bar").style.width = `${vitals.cpu_percent || 0}%`;

                document.getElementById("header-ram").innerText = `${(vitals.ram_percent || 0).toFixed(1)}%`;
                document.getElementById("header-ram-bar").style.width = `${vitals.ram_percent || 0}%`;

                document.getElementById("header-throughput").innerText = `${(vitals.throughput_rps || 0).toFixed(1)} RPS`;
                document.getElementById("header-workers").innerText = vitals.active_workers || 0;

                document.getElementById("cpu-curr").innerText = `${(vitals.cpu_percent || 0).toFixed(1)}%`;
                document.getElementById("ram-curr").innerText = `${(vitals.ram_percent || 0).toFixed(1)}%`;
                document.getElementById("ram-used-tag").innerText = `${vitals.ram_used_mb || 0} MB / ${vitals.ram_total_mb || 0} MB`;
                document.getElementById("ram-free").innerText = `${vitals.ram_free_mb || 0} MB free`;
                document.getElementById("workers-count").innerText = vitals.active_workers || 0;
                document.getElementById("light-q-depth").innerText = vitals.light_queue_depth || 0;
                document.getElementById("heavy-q-depth").innerText = vitals.heavy_queue_depth || 0;
                // Update Runtime Pool Cluster UI
                if (data.runtime_pool) {
                    updateRuntimePoolUI(data.runtime_pool);
                }


                if (vitals.load_avg) {
                    document.getElementById("cpu-load-tag").innerText = `Load: ${vitals.load_avg.map(x => x.toFixed(2)).join(", ")}`;
                }
                if (vitals.per_cpu_percent) {
                    document.getElementById("per-cpu-info").innerText = vitals.per_cpu_percent.map(p => `${p.toFixed(0)}%`).join(" | ");
                }

                cpuHistory.push(vitals.cpu_percent || 0);
                ramHistory.push(vitals.ram_percent || 0);
                throughputHistory.push(vitals.throughput_rps || 0);
                lightQueueHistory.push(vitals.light_queue_depth || 0);
                heavyQueueHistory.push(vitals.heavy_queue_depth || 0);

                if (cpuHistory.length > historyLength) cpuHistory.shift();
                if (ramHistory.length > historyLength) ramHistory.shift();
                if (throughputHistory.length > historyLength) throughputHistory.shift();
                if (lightQueueHistory.length > historyLength) lightQueueHistory.shift();
                if (heavyQueueHistory.length > historyLength) heavyQueueHistory.shift();

                drawLineChart(cpuCanvas, cpuHistory, "rgb(6, 182, 212)", 100);
                drawLineChart(ramCanvas, ramHistory, "rgb(99, 102, 241)", 100);
                drawLineChart(tpCanvas, throughputHistory, "rgb(16, 185, 129)", 100);
                drawLineChart(qCanvas, lightQueueHistory, "rgb(245, 158, 11)", 50);

                if (data.logs && data.logs.length > 0) {
                    logEntries = data.logs;
                    renderLogs();
                }

                if (data.battles) {
                    renderBattles(data.battles);
                }

                if (data.stress) {
                    updateStressStatus(data.stress);
                }

                if (data.cache_stats) {
                    const cs = data.cache_stats;
                    if (document.getElementById("c-raw-count")) document.getElementById("c-raw-count").innerText = cs.raw_telemetry?.count || 0;
                    if (document.getElementById("c-log-count")) document.getElementById("c-log-count").innerText = cs.logs?.total_stored || 0;
                    if (document.getElementById("c-battle-count")) document.getElementById("c-battle-count").innerText = cs.battles?.total_battles || 0;
                    if (document.getElementById("c-exec-count")) document.getElementById("c-exec-count").innerText = cs.executions?.total_executions || 0;
                    if (document.getElementById("c-stress-count")) document.getElementById("c-stress-count").innerText = cs.stress_reports_count || 0;
                    if (document.getElementById("cache-raw-json") && data.raw_series) {
                        document.getElementById("cache-raw-json").innerText = JSON.stringify(data.raw_series.slice(-3), null, 2);
                    }
                }

            } catch (err) {
                console.error("SSE message parse error:", err);
            }
        };

        eventSource.onerror = (err) => {
            if (sseStatus) {
                sseStatus.innerHTML = '<span class="live-beacon" style="background:#ef4444"></span> RECONNECTING...';
                sseStatus.style.borderColor = "rgba(239, 68, 68, 0.3)";
                sseStatus.style.color = "#f87171";
            }
        };
    }

    connectSSE();
});


function updateRuntimePoolUI(pool) {
    const countEl = document.getElementById("active-runtimes-count");
    if (countEl) countEl.innerText = pool.active_runtimes_count || 2;

    const cooldownEl = document.getElementById("cooldown-timer");
    if (cooldownEl) {
        cooldownEl.innerText = (pool.cooldown_seconds_remaining ? Math.floor(pool.cooldown_seconds_remaining) : 60) + "s";
    }

    const badgeEl = document.getElementById("scaling-state-badge");
    if (badgeEl && pool.scaling_state) {
        badgeEl.innerText = pool.scaling_state;
        if (pool.scaling_state === "SCALING_OUT") {
            badgeEl.style.color = "#f59e0b";
            badgeEl.style.background = "rgba(245, 158, 11, 0.15)";
            badgeEl.style.borderColor = "rgba(245, 158, 11, 0.3)";
        } else if (pool.scaling_state === "COOLDOWN_DRAIN") {
            badgeEl.style.color = "#3b82f6";
            badgeEl.style.background = "rgba(59, 130, 246, 0.15)";
            badgeEl.style.borderColor = "rgba(59, 130, 246, 0.3)";
        } else {
            badgeEl.style.color = "#10b981";
            badgeEl.style.background = "rgba(16, 185, 129, 0.15)";
            badgeEl.style.borderColor = "rgba(16, 185, 129, 0.3)";
        }
    }

    const gridEl = document.getElementById("runtime-pool-grid");
    if (gridEl && Array.isArray(pool.runtimes) && pool.runtimes.length > 0) {
        gridEl.innerHTML = pool.runtimes.map((r, i) => {
            const isBaseline = r.port === 2001 || r.port === 2002;
            const role = isBaseline ? (r.port === 2001 ? "Baseline (Compiler)" : "Baseline (Scripts)") : "Dynamic Elastic";
            const statusColor = r.status === "DRAINING" ? "#f59e0b" : "#10b981";
            return `
                <div class="runtime-instance-box" style="padding: 10px 14px; border-radius: 8px; background: rgba(31, 41, 55, 0.6); border: 1px solid rgba(75, 85, 99, 0.4);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <strong style="color: #e5e7eb; font-size: 0.85rem;">Piston-${i + 1} (:${r.port})</strong>
                        <span style="color: ${statusColor}; font-size: 0.75rem; font-weight: 600;">${r.status || 'HEALTHY'}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #9ca3af;">Role: ${role}</div>
                    <div style="font-size: 0.75rem; color: #a78bfa; margin-top: 4px;">In-flight Jobs: ${r.active_jobs || 0}</div>
                </div>
            `;
        }).join("");
    }
}
