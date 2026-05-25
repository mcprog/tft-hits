document.addEventListener('DOMContentLoaded', () => {
    const puuidElement = document.getElementById('user-puuid');
    const container = document.getElementById('games-container');
    const loadMoreBtn = document.getElementById('load-more-btn');

    if (!puuidElement || !container || !loadMoreBtn) return;

    const puuid = puuidElement.value;
    let currentOffset = 90;
    let epicCount = 0;
    let processedCount = 0;
    let totalInBatch = JSON.parse(container.getAttribute('data-match-ids')).length;

    function formatName(name) {
        if (name === 'Galio') return 'The Mighty Mech';
        if (name === 'IvernMinion') return 'Meepsie';
        if (name.toLowerCase() === 'bardfollower') return 'Meeplord';
        return name;
    }

    // Updated to support 4-star teal coloring
    function getStars(tier) {
        var s = '';
        var c = tier >= 4 ? 'text-teal-400' : (tier === 3 ? 'text-yellow-400' : (tier === 2 ? 'text-slate-300' : 'text-slate-600'));
        for (var i = 0; i < tier; i++) {
            s += '<span class="' + c + ' text-[10px]">★</span>';
        }
        return s;
    }

    function updateProgress() {
        processedCount++;
        const percent = (processedCount / totalInBatch) * 100;
        document.getElementById('processed-count').innerText = processedCount;
        document.getElementById('progress-bar').style.width = `${percent}%`;
        
        if (processedCount === totalInBatch) {
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerText = "Load Another 90 Games";
            
            document.getElementById('search-status').innerText = "Analysis complete for Set 17 high-rolls.";
            document.getElementById('progress-text').innerHTML = `Scan complete: <span class="text-blue-400 font-bold">${epicCount}</span> high-rolls found`;
            
            if (epicCount === 0) document.getElementById('no-results').classList.remove('hidden');
        }
    }

    async function fetchMatch(matchId) {
        try {
            const response = await fetch(`/api/match_details/${matchId}?puuid=${puuid}`);
            const data = await response.json();
            const element = document.getElementById(`match-${matchId}`);

            if (data && data.is_epic) {
                epicCount++;
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
                                    <img src="${u.image_url}" onerror="this.style.display='none'" class="h-12 w-12 rounded bg-slate-900 border ${u.tier >= 4 ? 'border-teal-500' : (u.tier === 3 ? 'border-yellow-500' : 'border-slate-700')}" alt="${u.character_id}">
                                    <p class="text-[10px] mt-1 text-slate-400 font-medium truncate w-12 text-center capitalize">${formatName(u.character_id)}</p>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            } else {
                if (element) element.remove();
            }
        } catch (err) {
            console.error("Error loading match:", err);
            const element = document.getElementById(`match-${matchId}`);
            if (element) element.remove();
        } finally {
            updateProgress();
        }
    }

    async function processQueue(ids, concurrency) {
        loadMoreBtn.disabled = true;
        loadMoreBtn.innerText = "Scanning Matches...";
        document.getElementById('no-results').classList.add('hidden');
        
        const queue = [...ids];
        const workers = [];

        for (let i = 0; i < concurrency; i++) {
            workers.push((async () => {
                while (queue.length > 0) {
                    const id = queue.shift();
                    await fetchMatch(id);
                    await new Promise(r => setTimeout(r, 100));
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

            processedCount = 0; 
            epicCount = 0; 
            totalInBatch = newIds.length; 
            currentOffset += 90;

            document.getElementById('search-status').innerText = "Deep search: Analyzing matches for Set 17 high-rolls.";
            document.getElementById('progress-text').innerHTML = `<span id="processed-count">0</span>/<span id="total-to-scan">${totalInBatch}</span> scanned`;
            document.getElementById('progress-bar').style.width = "0%";

            newIds.forEach(mid => {
                const div = document.createElement('div');
                div.id = `match-${mid}`;
                div.className = "match-placeholder bg-slate-800 p-6 rounded-xl border border-slate-700 animate-pulse";
                div.innerHTML = '<div class="h-24"></div>';
                container.appendChild(div);
            });

            processQueue(newIds, 5);
        } catch (err) { loadMoreBtn.disabled = false; }
    });

    processQueue(JSON.parse(container.getAttribute('data-match-ids')), 5);
});