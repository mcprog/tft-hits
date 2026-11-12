document.addEventListener('DOMContentLoaded', () => {
    const puuidElement = document.getElementById('user-puuid');
    const container = document.getElementById('games-container');
    const loadMoreBtn = document.getElementById('load-more-btn');
    const statusPanel = document.getElementById('unified-status-panel');
    const shareBtn = document.getElementById('share-btn');

    // Clipboard Share Logic
    if (shareBtn) {
        shareBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(window.location.href);
                const textSpan = document.getElementById('share-text');

                // Trigger visual success state
                textSpan.innerText = 'Copied!';
                shareBtn.classList.add('text-green-400', 'border-green-500/50');
                shareBtn.classList.remove('text-slate-300', 'border-slate-600');

                // Revert after 2 seconds
                setTimeout(() => {
                    textSpan.innerText = 'Share Link';
                    shareBtn.classList.remove('text-green-400', 'border-green-500/50');
                    shareBtn.classList.add('text-slate-300', 'border-slate-600');
                }, 2000);
            } catch (err) {
                console.error('Failed to copy link', err);
            }
        });
    }

    if (!puuidElement || !container || !loadMoreBtn) return;

    const puuid = puuidElement.value;
    let currentOffset = 90;
    let epicCount = 0;
    let batchCount = 0;

    // The batch currently being scanned. Batches run one at a time because the button is disabled mid-scan.
    let activeBatch = null;

    // Match IDs already placed on the page, so an overlapping batch never scans or renders a game twice
    const seenMatchIds = new Set();

    const prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function formatName(name) {
        if (!name) return '';

        const lowerName = name.toLowerCase();
        if (lowerName === 'belveth') return "Bel'Veth";
        if (lowerName === 'kaisa') return "Kai'Sa";
        if (lowerName === 'aurelionsol') return 'Aurelion Sol';
        if (lowerName === 'masteryi') return 'Master Yi';
        if (lowerName === 'twistedfate') return 'Twisted Fate';

        // Set 18 display names that differ from their internal apiName
        if (lowerName === 'khazix') return "Kha'Zix";
        if (lowerName === 'reksai') return "Rek'Sai";
        if (lowerName === 'kogmaw') return "Kog'Maw";
        if (lowerName === 'gnarsmall') return 'Gnar';
        if (lowerName === 'sentry') return 'Pebbles';
        if (lowerName === 'crimsonraptor') return 'Mama Beak';

        return name;
    }

    function getStars(tier) {
        var s = '';
        var c = tier >= 4 ? 'text-teal-400' : (tier === 3 ? 'text-yellow-400' : (tier === 2 ? 'text-slate-300' : 'text-slate-600'));
        for (var i = 0; i < tier; i++) {
            s += '<span class="' + c + ' text-[10px]">★</span>';
        }
        return s;
    }

    function scrollToElement(element, block) {
        element.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: block });
    }

    // Collects the parts of a status panel so the top panel and the per-batch panels share one code path
    function getStatusRefs(panel) {
        return {
            panel: panel,
            title: panel.querySelector('.js-status-title'),
            message: panel.querySelector('.js-status-message'),
            bar: panel.querySelector('.js-progress-bar'),
            processed: panel.querySelector('.js-processed-count'),
            total: panel.querySelector('.js-total-to-scan')
        };
    }

    // Builds the status panel shown under the divider of every batch after the first
    function buildBatchStatusPanel() {
        const panel = document.createElement('div');
        panel.className = 'batch-status-panel bg-slate-800/50 border border-slate-700/60 p-8 rounded-xl shadow-lg text-center w-full max-w-2xl mx-auto';
        panel.innerHTML = `
            <h3 class="js-status-title text-xl font-bold text-slate-200 mb-2 uppercase tracking-tight"></h3>
            <p class="js-status-message text-slate-400 font-medium mb-6"></p>
            <div class="w-full bg-slate-900 rounded-full h-2 border border-slate-700 overflow-hidden mb-2">
                <div class="js-progress-bar bg-blue-500 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
            </div>
            <div class="text-xs font-bold text-slate-500 uppercase tracking-wider text-right">
                <span><span class="js-processed-count">0</span>/<span class="js-total-to-scan">--</span> scanned</span>
            </div>
        `;
        return panel;
    }

    function prepareScan(ids, startOffset) {
        batchCount++;
        const isFirst = batchCount === 1;

        // Skip anything already on the page (match history shifts when new games are played between loads)
        const scanIds = ids.filter(mid => !seenMatchIds.has(mid));
        scanIds.forEach(mid => seenMatchIds.add(mid));

        if (isFirst) {
            container.innerHTML = ''; // Ensure container is completely clean before injection
        }

        // Every batch gets its own section so earlier results stay on the page
        const section = document.createElement('div');
        section.className = 'batch-section flex flex-col gap-6 empty:hidden scroll-mt-6';
        section.dataset.batch = batchCount;

        let status = null;
        if (isFirst) {
            // The first batch reports through the panel at the top of the page
            if (statusPanel) {
                statusPanel.classList.remove('hidden');
                status = getStatusRefs(statusPanel);
            }
        } else {
            // Later batches sit below a divider and report through their own panel
            const divider = document.createElement('hr');
            divider.className = 'batch-divider w-full border-0 border-t-2 border-slate-700/60';
            section.appendChild(divider);

            const panel = buildBatchStatusPanel();
            section.appendChild(panel);
            status = getStatusRefs(panel);
        }

        if (status) {
            if (status.title) {
                status.title.innerText = 'Analyzing Data';
                status.title.className = 'js-status-title text-xl font-bold text-slate-200 mb-2 uppercase tracking-tight';
            }
            if (status.message) status.message.innerText = 'Deep scanning match history for high-rolls...';
            if (status.bar) status.bar.style.width = "0%";
            if (status.processed) status.processed.innerText = '0';
            if (status.total) status.total.innerText = scanIds.length;
        }

        scanIds.forEach(mid => {
            const div = document.createElement('div');
            div.id = `match-${mid}`;
            div.className = "match-placeholder bg-slate-800 p-6 rounded-xl border border-slate-700 animate-pulse";
            div.innerHTML = '<div class="h-24"></div>';
            section.appendChild(div);
        });

        container.appendChild(section);

        activeBatch = {
            section: section,
            status: status,
            isFirst: isFirst,
            rangeStart: startOffset + 1,
            rangeEnd: startOffset + ids.length,
            total: scanIds.length,
            processed: 0,
            epicCount: 0
        };

        // Bring the new batch into view so its progress and results are visible
        if (!isFirst) scrollToElement(section, 'start');

        return scanIds;
    }

    function finishBatch() {
        const batch = activeBatch;
        if (!batch) return;

        loadMoreBtn.disabled = false;
        loadMoreBtn.innerText = "Load Another 90 Games";

        const status = batch.status;
        if (status && status.bar) status.bar.style.width = "100%";

        if (batch.epicCount === 0) {
            if (!status) return;

            if (status.title) {
                status.title.innerText = 'No High-Rolls Found';
                status.title.className = 'js-status-title text-xl font-bold text-blue-400 mb-2 uppercase tracking-tight';
            }
            if (status.message) {
                status.message.innerText = batch.isFirst
                    ? 'This player hasn\'t hit a Prismatic vertical or a 3-Star 4/5-cost champion in this batch of games.'
                    : `This player hasn't hit a Prismatic vertical or a 3-Star 4/5-cost champion in games ${batch.rangeStart} to ${batch.rangeEnd}.`;
            }
            status.panel.classList.remove('hidden');

            if (!batch.isFirst) {
                // The notice sits below the earlier results, so pull it into view and glow briefly to catch the eye
                status.panel.classList.add('notice-glow');
                status.panel.addEventListener('animationend', () => {
                    status.panel.classList.remove('notice-glow');
                }, { once: true });
                scrollToElement(status.panel, 'center');
            }
        } else if (batch.isFirst) {
            if (status) status.panel.classList.add('hidden');
        } else {
            // Drop the progress panel so the divider sits directly above the new games, then scroll to the top one
            if (status) status.panel.remove();
            scrollToElement(batch.section, 'start');
        }
    }

    function updateProgress() {
        const batch = activeBatch;
        if (!batch) return;

        batch.processed++;
        const percent = batch.total === 0 ? 100 : (batch.processed / batch.total) * 100;

        if (batch.status) {
            if (batch.status.processed) batch.status.processed.innerText = Math.min(batch.processed, batch.total);
            if (batch.status.bar) batch.status.bar.style.width = `${Math.min(percent, 100)}%`;
        }

        if (batch.processed >= batch.total) {
            finishBatch();
        }
    }

    async function fetchMatch(matchId) {
        try {
            const response = await fetch(`/api/match_details/${matchId}?puuid=${puuid}`);
            if (!response.ok) throw new Error('Network error on match payload');

            const data = await response.json();
            const element = document.getElementById(`match-${matchId}`);

            if (data && data.is_epic) {
                epicCount++;
                if (activeBatch) activeBatch.epicCount++;
                if (element) {
                    element.classList.remove('animate-pulse');

                    // --- DOUBLE UP PLACEMENT FIX ---
                    // Convert individual placements (1-8) to team placements (1-4)
                    let displayPlacement = data.placement;
                    if (data.game_mode === 'Double Up') {
                        displayPlacement = Math.ceil(data.placement / 2);
                    }

                    element.innerHTML = `
                        <div class="flex flex-col gap-6">
                            <div class="flex justify-between items-start">
                                <div>
                                    <p class="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                                        ${data.readable_date} • <span class="text-blue-400">${data.game_mode}</span>
                                    </p>
                                    <h3 class="text-2xl font-black italic">Place: <span class="text-blue-400">#${displayPlacement}</span></h3>
                                    <div class="flex flex-wrap gap-2 mt-3">
                                        ${data.has_prismatic ? `<span class="bg-purple-900/40 text-purple-300 px-3 py-1 rounded border border-purple-500/50 text-xs font-bold uppercase tracking-tight">PRISMATIC ${data.prismatic_name}</span>` : ''}
                                        ${data.has_high_cost_3star ? data.high_cost_units.map(n => `
                                            <span class="bg-yellow-900/40 text-yellow-300 px-3 py-1 rounded border border-yellow-500/50 text-xs font-bold uppercase tracking-tight">3* ${formatName(n)}</span>
                                        `).join('') : ''}
                                    </div>
                                </div>
                            </div>

                            <div class="flex flex-wrap gap-3 pt-4 border-t border-slate-700/50">
                                ${data.units.map(u => `
                                    <div class="flex flex-col items-center w-16">
                                        <div class="flex h-3 mb-1 items-center justify-center">${getStars(u.tier)}</div>
                                        <img src="${u.image_url}" onerror="this.style.display='none'" class="h-12 w-12 rounded bg-slate-900 border ${u.tier >= 4 ? 'border-teal-500' : (u.tier === 3 ? 'border-yellow-500' : 'border-slate-700')} mb-1" alt="${u.character_id}">

                                        <!-- Item Inline Row -->
                                        ${u.items && u.items.length > 0 ? `
                                        <div class="flex gap-0.5 justify-center mb-1">
                                            ${u.items.map(itemUrl => `
                                                <div class="w-4 h-4 rounded-sm bg-slate-700 border border-slate-900 overflow-hidden">
                                                    <img src="${itemUrl}" onerror="this.style.display='none'" class="w-full h-full object-cover">
                                                </div>
                                            `).join('')}
                                        </div>
                                        ` : '<div class="h-5 mb-1"></div>'}

                                        <p class="text-[10px] text-slate-400 font-medium w-full text-center capitalize break-words leading-tight">${formatName(u.character_id)}</p>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }
            } else {
                if (element) element.remove();
            }
        } catch (err) {
            console.error("Error loading match array:", err);
            const element = document.getElementById(`match-${matchId}`);
            if (element) element.remove();
        } finally {
            updateProgress();
        }
    }

    async function processQueue(ids, concurrency) {
        loadMoreBtn.disabled = true;
        loadMoreBtn.innerText = "Scanning Matches...";

        const queue = [...ids];
        const workers = [];

        for (let i = 0; i < concurrency; i++) {
            workers.push((async () => {
                while (queue.length > 0) {
                    const id = queue.shift();
                    await fetchMatch(id);
                }
            })());
        }
        await Promise.all(workers);
    }

    // Lays out a new batch and scans it, appending below anything already on the page
    function startBatch(ids, startOffset) {
        const scanIds = prepareScan(ids, startOffset);
        if (scanIds.length > 0) {
            processQueue(scanIds, 5);
        } else {
            // Nothing to scan, so settle the batch straight away
            finishBatch();
        }
    }

    loadMoreBtn.addEventListener('click', async () => {
        loadMoreBtn.disabled = true;
        try {
            const batchStart = currentOffset;
            const res = await fetch(`/api/get_more_ids?puuid=${puuid}&start=${batchStart}`);
            const newIds = await res.json();
            if (newIds.length === 0) { loadMoreBtn.innerText = "No More Matches"; return; }

            currentOffset += 90;
            startBatch(newIds, batchStart);
        } catch (err) {
            loadMoreBtn.disabled = false;
        }
    });

    // Capture IDs passed directly from the Jinja environment and execute
    let initialIds = [];
    try {
        const rawAttr = container.getAttribute('data-match-ids');
        if (rawAttr) {
            initialIds = JSON.parse(rawAttr);
        }
    } catch(e) {
        console.error("Failed to parse initial match IDs", e);
    }

    startBatch(initialIds || [], 0);
});
