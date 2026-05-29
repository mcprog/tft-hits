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
    let processedCount = 0;
    let totalInBatch = 0;

    function formatName(name) {
        if (!name) return '';
        if (name === 'Galio') return 'The Mighty Mech';
        if (name === 'IvernMinion') return 'Meepsie';
        if (name.toLowerCase() === 'bardfollower') return 'Meeplord';
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

    function prepareScan(ids) {
        processedCount = 0;
        totalInBatch = ids.length;
        
        if (statusPanel) {
            statusPanel.classList.remove('hidden');
            
            const icon = document.getElementById('status-icon');
            if (icon) {
                icon.innerText = '📡';
                icon.classList.add('animate-pulse');
            }
            
            const title = document.getElementById('status-title');
            if (title) {
                title.innerText = 'Analyzing Data';
                title.className = 'text-xl font-bold text-slate-200 mb-2 uppercase tracking-tight';
            }
            
            const msg = document.getElementById('status-message');
            if (msg) msg.innerText = 'Deep scanning match history for high-rolls...';
            
            const pbar = document.getElementById('progress-bar');
            if (pbar) pbar.style.width = "0%";
            
            const ptext = document.getElementById('progress-text');
            if (ptext) ptext.innerHTML = `<span id="processed-count">0</span>/<span id="total-to-scan">${totalInBatch}</span> scanned`;
        }

        container.innerHTML = ''; // Ensure container is completely clean before injection

        ids.forEach(mid => {
            const div = document.createElement('div');
            div.id = `match-${mid}`;
            div.className = "match-placeholder bg-slate-800 p-6 rounded-xl border border-slate-700 animate-pulse";
            div.innerHTML = '<div class="h-24"></div>';
            container.appendChild(div);
        });
    }

    function updateProgress() {
        processedCount++;
        const percent = totalInBatch === 0 ? 100 : (processedCount / totalInBatch) * 100;
        
        const countEl = document.getElementById('processed-count');
        if (countEl) countEl.innerText = Math.min(processedCount, totalInBatch);
        
        const barEl = document.getElementById('progress-bar');
        if (barEl) barEl.style.width = `${Math.min(percent, 100)}%`;
        
        if (processedCount >= totalInBatch) {
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerText = "Load Another 90 Games";
            
            if (epicCount === 0 && statusPanel) {
                const icon = document.getElementById('status-icon');
                if (icon) {
                    icon.innerText = '📭';
                    icon.classList.remove('animate-pulse');
                }
                
                const title = document.getElementById('status-title');
                if (title) {
                    title.innerText = 'No High-Rolls Found';
                    title.className = 'text-xl font-bold text-blue-400 mb-2 uppercase tracking-tight';
                }
                
                const msg = document.getElementById('status-message');
                if (msg) msg.innerText = 'This player hasn\'t hit a Prismatic vertical or a 3-Star 4/5-cost champion in this batch of games.';
                statusPanel.classList.remove('hidden');
            } else if (epicCount > 0 && statusPanel) {
                statusPanel.classList.add('hidden');
            }
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
                if (element) {
                    element.classList.remove('animate-pulse');
                    element.innerHTML = `
                        <div class="flex flex-col gap-6">
                            <div class="flex justify-between items-start">
                                <div>
                                    <p class="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                                        ${data.readable_date} • <span class="text-blue-400">${data.game_mode}</span>
                                    </p>
                                    <h3 class="text-2xl font-black italic">Place: <span class="text-blue-400">#${data.placement}</span></h3>
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
                                    <div class="flex flex-col items-center">
                                        <div class="flex h-3 mb-1 items-center justify-center">${getStars(u.tier)}</div>
                                        <img src="${u.image_url}" onerror="this.style.display='none'" class="h-12 w-12 rounded bg-slate-900 border ${u.tier >= 4 ? 'border-teal-500' : (u.tier === 3 ? 'border-yellow-500' : 'border-slate-700')} mb-1" alt="${u.character_id}">
                                        
                                        ${u.items && u.items.length > 0 ? `
                                        <div class="flex gap-0.5 justify-center mb-1">
                                            ${u.items.map(itemUrl => `
                                                <div class="w-4 h-4 rounded-sm bg-slate-700 border border-slate-900 overflow-hidden">
                                                    <img src="${itemUrl}" onerror="this.style.display='none'" class="w-full h-full object-cover">
                                                </div>
                                            `).join('')}
                                        </div>
                                        ` : '<div class="h-5 mb-1"></div>'}
                                        
                                        <p class="text-[10px] text-slate-400 font-medium truncate w-16 text-center capitalize">${formatName(u.character_id)}</p>
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

    loadMoreBtn.addEventListener('click', async () => {
        loadMoreBtn.disabled = true;
        try {
            const res = await fetch(`/api/get_more_ids?puuid=${puuid}&start=${currentOffset}`);
            const newIds = await res.json();
            if (newIds.length === 0) { loadMoreBtn.innerText = "No More Matches"; return; }

            currentOffset += 90;
            prepareScan(newIds);
            processQueue(newIds, 5);
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

    if (initialIds && initialIds.length > 0) {
        prepareScan(initialIds);
        processQueue(initialIds, 5);
    } else {
        totalInBatch = 0;
        updateProgress();
    }
});