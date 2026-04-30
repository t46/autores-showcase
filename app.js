// AutoRes Showcase — fetch + render
(() => {
    const ACCENT = '#0066cc';
    const ACCENT_LIGHT = '#9ec5ff';
    const GREEN = '#22c55e';
    const RED = '#ef4444';
    const GRAY = '#9ca3af';
    const GOLD = '#f9a825';

    Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = '#444';

    // ---------------- helpers ----------------
    const $ = id => document.getElementById(id);
    const el = (tag, attrs = {}, children = []) => {
        const e = document.createElement(tag);
        for (const [k, v] of Object.entries(attrs)) {
            if (k === 'class') e.className = v;
            else if (k === 'html') e.innerHTML = v;
            else if (k === 'text') e.textContent = v;
            else e.setAttribute(k, v);
        }
        for (const c of [].concat(children)) {
            if (c == null) continue;
            e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
        }
        return e;
    };
    const fmt = (n, d = 2) => (typeof n === 'number' ? n.toFixed(d) : '—');
    const pct = n => (typeof n === 'number' ? n.toFixed(1) + '%' : '—');

    // ---------------- main ----------------
    async function main() {
        try {
            const [overview, paperbench, selfImproving, reproduce, litScout] = await Promise.all([
                fetch('./data/overview.json').then(r => r.json()),
                fetch('./data/paperbench.json').then(r => r.json()),
                fetch('./data/self-improving.json').then(r => r.json()),
                fetch('./data/reproduce.json').then(r => r.json()),
                fetch('./data/literature-scout.json').then(r => r.json()),
            ]);

            renderHero(overview);
            renderPaperbench(paperbench);
            renderSelfImproving(selfImproving);
            renderReproduce(reproduce);
            renderLitScout(litScout);
            renderOverviewTable(overview);

            $('footer-time').textContent = '生成日時: ' + (overview._generated_at || '—');
        } catch (e) {
            console.error('showcase fatal:', e);
            $('hero-subtitle').textContent = 'データ読み込みエラー: ' + e.message;
        }
    }

    // ---------------- Hero ----------------
    function renderHero(o) {
        if (o.title) $('hero-title').textContent = o.title;
        if (o.subtitle) $('hero-subtitle').textContent = o.subtitle;
        const tiles = $('component-tiles');
        for (const c of o.components || []) {
            const a = el('a', { class: 'tile', href: '#' + c.id });
            a.appendChild(el('h3', { html: c.name + ` <span class="status ${c.status === 'alpha' ? 'alpha' : ''}">${c.status || ''}</span>` }));
            a.appendChild(el('div', { class: 'tagline', text: c.tagline || '' }));
            a.appendChild(el('div', { class: 'metric', text: c.metric || '' }));
            tiles.appendChild(a);
        }
    }

    // ---------------- §1 PaperBench ----------------
    function renderPaperbench(d) {
        if (d.summary) $('pb-summary').textContent = d.summary;

        // line chart
        const its = (d.iterations || []).filter(i => 'hierarchical_score' in i);
        new Chart($('chart-pb-line'), {
            type: 'line',
            data: {
                labels: its.map(i => i.label),
                datasets: [
                    {
                        label: '階層スコア',
                        data: its.map(i => i.hierarchical_score),
                        borderColor: ACCENT,
                        backgroundColor: ACCENT,
                        tension: 0.2,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                    },
                    {
                        label: '単純平均',
                        data: its.map(i => i.simple_average_score),
                        borderColor: ACCENT_LIGHT,
                        backgroundColor: ACCENT_LIGHT,
                        tension: 0.2,
                        pointRadius: 5,
                        borderDash: [4, 4],
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}%` } },
                },
                scales: {
                    y: { min: 0, max: 100, ticks: { callback: v => v + '%' } },
                },
            },
        });

        // stacked distribution
        const bins = ['0-25', '26-50', '51-75', '76-100'];
        const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e'];
        new Chart($('chart-pb-dist'), {
            type: 'bar',
            data: {
                labels: its.map(i => i.label),
                datasets: bins.map((b, i) => ({
                    label: b,
                    data: its.map(it => (it.score_distribution || {})[b] || 0),
                    backgroundColor: colors[i],
                })),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y} ノード` } },
                },
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, title: { display: true, text: 'ノード数' } },
                },
            },
        });

        // notes (3 iter × improved/failed)
        const notesHost = $('pb-notes');
        const labels = { v0: 'v0 baseline (43.2%)', v1: 'v1 +1 iter (67.5%)', v2: 'v2 +2 iter (94.5%)' };
        for (const key of ['v0', 'v1', 'v2']) {
            const n = (d.notes || {})[key] || {};
            const grid = el('div', { class: 'notes-grid' });
            const mkDetails = (title, items, kind) => {
                const det = el('details', { class: 'col-' + kind });
                if (kind === 'improved') det.open = false;
                det.appendChild(el('summary', { text: `${title}（${items.length}件）` }));
                const ul = el('ul');
                for (const t of items) ul.appendChild(el('li', { text: t }));
                det.appendChild(ul);
                return det;
            };
            grid.appendChild(mkDetails('改善した点', n.improved || [], 'improved'));
            grid.appendChild(mkDetails('失敗した点', n.failed || [], 'failed'));
            notesHost.appendChild(el('div', { class: 'iter-block' }, [
                el('div', { class: 'iter-label', html: `<strong style="font-size:14px;">${labels[key]}</strong>` }),
                grid,
            ]));
        }

        // sota table
        const tbody = document.querySelector('#pb-sota tbody');
        for (const r of d.sota_table || []) {
            const tr = el('tr', { class: (r.ours ? 'ours ' : '') + (r.highlight ? 'highlight' : '') });
            tr.appendChild(el('td', { text: r.agent }));
            tr.appendChild(el('td', { text: pct(r.score) }));
            tr.appendChild(el('td', { text: r.note || '' }));
            tbody.appendChild(tr);
        }

        if (d.caveat) {
            $('pb-caveat').innerHTML = '<strong>注意:</strong> ' + d.caveat;
        }
    }

    // ---------------- §2 self-improving ----------------
    function renderSelfImproving(d) {
        if (d.summary) $('si-summary').textContent = d.summary;

        const cycles = d.cycles || [];
        new Chart($('chart-cycles'), {
            type: 'bar',
            data: {
                labels: cycles.map(c => 'サイクル ' + c.cycle),
                datasets: [{
                    label: '精度',
                    data: cycles.map(c => c.accuracy),
                    backgroundColor: cycles.map(c => c.cycle === d.best_cycle ? GOLD : (c.regressed ? RED : ACCENT)),
                    borderColor: cycles.map(c => c.cycle === d.best_cycle ? '#b76e00' : (c.regressed ? '#b91c1c' : '#003c80')),
                    borderWidth: 1,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => {
                                const c = cycles[ctx.dataIndex];
                                return [
                                    `精度: ${c.accuracy.toFixed(4)}`,
                                    `損失: ${c.loss.toFixed(4)}`,
                                    `変化: ${c.improvement_delta >= 0 ? '+' : ''}${c.improvement_delta.toFixed(4)}`,
                                    `${c.improvement.description}`,
                                ];
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        min: 0.55, max: 0.75,
                        title: { display: true, text: 'CIFAR-10 テスト精度' },
                    },
                },
            },
        });

        const grid = $('cycle-grid');
        for (const c of cycles) {
            const card = el('div', { class: 'cycle-card' + (c.cycle === d.best_cycle ? ' best' : '') + (c.regressed ? ' regressed' : '') });
            card.appendChild(el('div', { class: 'cycle-num', text: 'サイクル ' + c.cycle }));
            card.appendChild(el('div', { class: 'acc', text: c.accuracy.toFixed(4) }));
            const deltaCls = c.improvement_delta > 0 ? 'up' : (c.improvement_delta < 0 ? 'down' : '');
            const deltaSign = c.improvement_delta >= 0 ? '+' : '';
            card.appendChild(el('div', {
                class: 'delta ' + deltaCls,
                text: `変化 ${deltaSign}${c.improvement_delta.toFixed(4)} · 損失 ${c.loss.toFixed(3)}`,
            }));
            card.appendChild(el('div', { class: 'desc', text: c.improvement.description }));
            const meta = el('div', { class: 'meta' });
            meta.appendChild(el('span', { class: 'badge', text: c.improvement.category || '不明' }));
            meta.appendChild(el('span', { class: 'badge', text: `信頼度 ${c.improvement.confidence.toFixed(2)}` }));
            if (c.cycle === d.best_cycle) meta.appendChild(el('span', { class: 'badge best', text: '★ ベスト' }));
            card.appendChild(meta);
            grid.appendChild(card);
        }

        if (d.note) $('si-note').innerHTML = '<strong>観察:</strong> ' + d.note;
    }

    // ---------------- §3 reproduce ----------------
    function renderReproduce(d) {
        if (d.summary) $('rp-summary').textContent = d.summary;

        const paper = d.paper || {};
        $('rp-paper-title').textContent = paper.title || '—';
        $('rp-paper-arxiv').textContent = paper.arxiv_id || '—';
        $('rp-paper-link').href = paper.arxiv_url || `https://arxiv.org/abs/${paper.arxiv_id || ''}`;

        // gauge
        const score = d.reproduction_score || 0;
        const gauge = $('rp-gauge');
        gauge.style.setProperty('--pct', score);
        $('rp-gauge-text').textContent = (score * 100).toFixed(0) + '%';
        $('rp-score-value').textContent = score.toFixed(2) + ' (' + (score * 100).toFixed(0) + '%)';
        $('rp-duration-value').textContent = (d.total_duration || 0).toFixed(1) + ' 秒';

        // duration bar
        const stages = d.stages || [];
        new Chart($('chart-stages'), {
            type: 'bar',
            data: {
                labels: stages.map(s => s.name),
                datasets: [{
                    label: '所要時間（秒）',
                    data: stages.map(s => s.duration),
                    backgroundColor: stages.map(s => s.success ? ACCENT : RED),
                }],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: ctx => `${ctx.parsed.x.toFixed(2)}s — ${stages[ctx.dataIndex].message}` } },
                },
                scales: { x: { title: { display: true, text: '秒' } } },
            },
        });

        // timeline
        const tl = $('stage-timeline');
        for (const s of stages) {
            const li = el('li');
            li.appendChild(el('span', { class: 'stage-indicator' + (s.success ? '' : ' fail') }));
            li.appendChild(el('div', {}, [
                el('div', { class: 'stage-name', text: s.name }),
                el('div', { class: 'stage-msg', text: s.message }),
            ]));
            li.appendChild(el('span', { class: 'stage-dur', text: s.duration.toFixed(2) + 's' }));
            tl.appendChild(li);
        }

        // claims
        const ch = $('claims-list');
        for (const c of d.claims || []) {
            const card = el('div', { class: 'claim' });
            const head = el('div', { class: 'claim-head' });
            head.appendChild(el('code', { text: c.description }));
            head.appendChild(el('span', { class: 'claim-status ' + (c.status || ''), text: c.status || '' }));
            card.appendChild(head);
            const exp = c.expected != null ? c.expected : '—';
            const act = c.actual != null ? c.actual : '—';
            card.appendChild(el('div', { class: 'claim-numbers', html: `期待値: <strong>${exp}</strong> / 実測値: <strong>${act}</strong>` }));
            if (c.reason) card.appendChild(el('div', { class: 'claim-numbers', text: '理由: ' + c.reason }));
            ch.appendChild(card);
        }
    }

    // ---------------- §4 literature-scout ----------------
    function renderLitScout(d) {
        if (d.summary) $('ls-summary').textContent = d.summary;

        const flow = $('ls-concept');
        for (const s of d.concept || []) {
            const step = el('div', { class: 'concept-step' });
            step.appendChild(el('div', { class: 'step-num', text: 'ステップ ' + s.step }));
            step.appendChild(el('div', { class: 'step-label', text: s.label }));
            step.appendChild(el('div', { class: 'step-detail', text: s.detail }));
            flow.appendChild(step);
        }

        $('ls-cli').textContent = d.cli_sample || '';

        const ph = $('ls-papers');
        for (const p of d.sample_papers || []) {
            const card = el('div', { class: 'paper-card' });
            const head = el('div', { class: 'paper-head' });
            head.appendChild(el('div', { class: 'paper-title', text: p.title }));
            head.appendChild(el('div', { class: 'paper-relevance', text: '関連度 ' + (p.relevance || 0).toFixed(2) }));
            card.appendChild(head);
            card.appendChild(el('div', { class: 'paper-meta', text: 'arXiv: ' + (p.arxiv_id || '—') }));
            if (p.abstract_snippet) card.appendChild(el('div', { class: 'paper-abstract', text: p.abstract_snippet }));
            if (p.reasoning) card.appendChild(el('div', { class: 'paper-reasoning', text: 'Claude の判定: ' + p.reasoning }));
            ph.appendChild(card);
        }

        if (d.note) $('ls-note').innerHTML = '<strong>注意:</strong> ' + d.note;
    }

    // ---------------- §5 overview table ----------------
    function renderOverviewTable(o) {
        const tbody = document.querySelector('#overview-matrix tbody');
        for (const r of o.matrix || []) {
            const tr = el('tr');
            tr.appendChild(el('td', { html: '<strong>' + r.name + '</strong>' }));
            tr.appendChild(el('td', { text: r.input }));
            tr.appendChild(el('td', { text: r.output }));
            tr.appendChild(el('td', { text: r.key_finding }));
            tbody.appendChild(tr);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', main);
    } else {
        main();
    }
})();
