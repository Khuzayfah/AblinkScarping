// Ablink SGCarmart Scraper - Frontend

// Resilient fetch wrapper: adds timeout + retry for transient network failures
async function fetchWithRetry(url, options, retries, timeout) {
    retries = retries || 2;
    timeout = timeout || 15000;
    for (var attempt = 0; attempt <= retries; attempt++) {
        try {
            var controller = new AbortController();
            var timer = setTimeout(function () { controller.abort(); }, timeout);
            var opts = Object.assign({}, options || {}, { signal: controller.signal });
            var response = await fetch(url, opts);
            clearTimeout(timer);
            return response;
        } catch (err) {
            clearTimeout(timer);
            if (attempt < retries) {
                // Wait before retry (exponential backoff: 1s, 2s)
                await new Promise(function (r) { setTimeout(r, 1000 * (attempt + 1)); });
                continue;
            }
            throw err;
        }
    }
}

// Returns today's date as "YYYY-MM-DD" in LOCAL browser time (not UTC)
function getLocalDateStr(date) {
    var d = date || new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function showNotification(message, isError) {
    isError = isError || false;
    var toast = document.getElementById('notificationToast');
    var body = document.getElementById('toastMessage');
    body.textContent = message;
    toast.classList.remove('bg-success', 'bg-danger', 'text-white');
    toast.classList.add(isError ? 'bg-danger' : 'bg-success', 'text-white');
    new bootstrap.Toast(toast).show();
}

function setLoading(show) {
    document.getElementById('loadingSpinner').style.display = show ? 'block' : 'none';
}

async function loadStatus() {
    try {
        var r = await fetchWithRetry('/api/status');
        if (!r.ok) return;
        var s = await r.json();
        document.getElementById('statusBadge').textContent = s.status;
        document.getElementById('statusBadge').classList.toggle('scraping', s.status === 'Scraping');
        document.getElementById('lastScrape').textContent = s.last_scrape_at
            ? 'Last scrape: ' + s.last_scrape_at
            : 'Last scrape: —';
        if (s.schedule) {
            var sh = s.schedule.hour;
            var sm = s.schedule.minute;
            document.getElementById('scheduleTime').value = (sh < 10 ? '0' + sh : '' + sh) + ':' + (sm < 10 ? '0' + sm : '' + sm);
            document.getElementById('currentSchedule').textContent = 'Current: ' + formatTimeDisplay(sh, sm) + ' SGT';
        } else {
            document.getElementById('currentSchedule').textContent = 'Current: —';
        }
        var nextEl = document.getElementById('nextRunDisplay');
        if (nextEl) {
            nextEl.textContent = s.next_run_display || '—';
        }
    } catch (e) {
        console.error(e);
    }
}

function formatTimeDisplay(hour, minute) {
    var h = hour % 12 || 12;
    var ampm = hour < 12 ? 'AM' : 'PM';
    return (h < 10 ? '0' : '') + h + ':' + (minute < 10 ? '0' : '') + minute + ' ' + ampm;
}

async function updateSchedule() {
    var timeInput = document.getElementById('scheduleTime').value;
    if (!timeInput) {
        showNotification('Please select a time', true);
        return;
    }
    var parts = timeInput.split(':');
    var hour = parseInt(parts[0], 10);
    var minute = parseInt(parts[1], 10) || 0;
    try {
        var r = await fetch('/api/schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hour: hour, minute: minute })
        });
        if (!r.ok) throw new Error('Failed to update schedule');
        var d = await r.json();
        document.getElementById('currentSchedule').textContent = 'Current: ' + formatTimeDisplay(d.schedule.hour, d.schedule.minute) + ' SGT';
        showNotification('Schedule updated');
        loadStatus();
    } catch (e) {
        showNotification('Error: ' + e.message, true);
    }
}

function formatPrice(val) {
    if (val == null || val === '') return '–';
    return '$' + Number(val).toLocaleString();
}

// Daily table: grouped by category with numbered sub-lists per model
function buildTable(dailyData) {
    var container = document.getElementById('dataTableBody');
    var thead = document.getElementById('tableHead');
    container.innerHTML = '';
    thead.innerHTML = '';

    if (!dailyData || !dailyData.groups) return;

    var colSpan = 5;

    // Build header row
    var headerTr = document.createElement('tr');
    ['No', 'Name & Model', 'Year Reg', 'Depreciation', 'Dealer Name'].forEach(function (label) {
        var th = document.createElement('th');
        th.textContent = label;
        if (label === 'Name & Model') th.className = 'vehicle-col';
        if (label === 'No') th.style.width = '45px';
        headerTr.appendChild(th);
    });
    thead.appendChild(headerTr);

    var groups = dailyData.groups || [];
    groups.forEach(function (group) {
        // Count total sold in this category
        var catTotal = 0;
        (group.models || []).forEach(function (m) { catTotal += (m.entries || []).length; });

        // Category header row
        var catTr = document.createElement('tr');
        catTr.className = 'category-row';
        var catTd = document.createElement('td');
        catTd.colSpan = colSpan;
        catTd.innerHTML = group.category + (catTotal > 0 ? ' <span style="opacity:0.7;font-size:0.8rem;">(' + catTotal + ' sold)</span>' : '');
        catTr.appendChild(catTd);
        container.appendChild(catTr);

        var models = group.models || [];
        models.forEach(function (modelData) {
            var entries = modelData.entries || [];

            if (entries.length === 0) {
                // Model with no data
                var emptyTr = document.createElement('tr');
                emptyTr.className = 'model-empty-row';
                emptyTr.innerHTML =
                    '<td class="no-col">–</td>' +
                    '<td class="vehicle-col">' + modelData.name_model + '</td>' +
                    '<td>–</td><td>–</td><td>–</td>';
                container.appendChild(emptyTr);
            } else {
                entries.forEach(function (entry, idx) {
                    var tr = document.createElement('tr');
                    if (idx === 0) tr.className = 'model-first-row';
                    tr.innerHTML =
                        '<td class="no-col">' + (idx + 1) + '</td>' +
                        '<td class="vehicle-col">' + (idx === 0 ? modelData.name_model : '') + '</td>' +
                        '<td>' + (entry.year_registered || '–') + '</td>' +
                        '<td class="depre-cell">' + (entry.depreciation || '–') + '</td>' +
                        '<td>' + (entry.dealer_name || '–') + '</td>';
                    container.appendChild(tr);
                });
            }
        });
    });
}

function getReportDate() {
    var d = document.getElementById('reportDate');
    var d2 = document.getElementById('reportDateTop');
    if (d2 && d2.value) return d2.value;
    return d ? d.value : getLocalDateStr();
}

function setReportDate(val) {
    var d = document.getElementById('reportDate');
    var d2 = document.getElementById('reportDateTop');
    if (d) d.value = val;
    if (d2) d2.value = val;
}

function navDate(offset) {
    var current = getReportDate();
    if (!current) current = getLocalDateStr();
    var d = new Date(current + 'T00:00:00');
    d.setDate(d.getDate() + offset);
    var today = new Date();
    today.setHours(0,0,0,0);
    if (d > today) return; // Don't go to future
    var newDate = getLocalDateStr(d);
    setReportDate(newDate);
    loadDailyReport();
}

function navToday() {
    var today = getLocalDateStr();
    setReportDate(today);
    loadDailyReport();
}

async function loadDailyReport() {
    var date = getReportDate();
    if (!date) {
        showNotification('Please select a date', true);
        return;
    }
    setLoading(true);
    try {
        var r = await fetchWithRetry('/api/daily-report?date=' + date);
        if (!r.ok) throw new Error('Failed to load report');
        var data = await r.json();
        setReportDate(data.date);
        // Format date nicely: "Thu, 6 Feb 2026"
        var dp = new Date(data.date + 'T00:00:00');
        var days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
        var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        var niceDate = days[dp.getDay()] + ', ' + dp.getDate() + ' ' + months[dp.getMonth()] + ' ' + dp.getFullYear();
        document.getElementById('reportDateLabel').textContent = niceDate;
        // Check if there is any sold data in groups
        var hasSold = false;
        if (data.daily_table && data.daily_table.groups) {
            data.daily_table.groups.forEach(function (g) {
                g.models.forEach(function (m) {
                    if (m.entries && m.entries.length > 0) hasSold = true;
                });
            });
        }
        // Always show table wrapper so calendar nav is visible
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('dataTableWrapper').style.display = 'block';
        document.getElementById('exportBar').style.display = hasSold ? 'flex' : 'none';
        if (hasSold) {
            buildTable(data.daily_table);
        } else {
            // Show empty message inside table
            var tbody = document.getElementById('dataTableBody');
            var thead = document.getElementById('tableHead');
            thead.innerHTML = '';
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:40px;color:#9ca3af;"><i class="bi bi-inbox" style="font-size:2rem;display:block;margin-bottom:8px;"></i>No sold data for this date.<br>Click REFRESH DATA to scrape, or navigate to another date.</td></tr>';
        }
        var totalSold = data.summary ? (data.summary.total_sold || 0) : 0;
        var badge = document.getElementById('soldCountBadge');
        if (badge) {
            badge.textContent = totalSold + ' sold';
            badge.style.display = totalSold > 0 ? 'inline-block' : 'none';
        }
        showNotification('Sold report loaded for ' + date + ' (' + totalSold + ' units sold)');
    } catch (e) {
        showNotification('Error: ' + e.message, true);
        // Keep nav wrapper visible so user can still navigate dates
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('dataTableWrapper').style.display = 'block';
        var errThead = document.getElementById('tableHead');
        var errTbody = document.getElementById('dataTableBody');
        if (errThead) errThead.innerHTML = '';
        if (errTbody) errTbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:40px;color:#ef4444;"><i class="bi bi-exclamation-triangle" style="font-size:2rem;display:block;margin-bottom:8px;"></i>Failed to load data: ' + e.message + '</td></tr>';
    } finally {
        setLoading(false);
    }
}

var SCRAPE_ESTIMATE_SECS = 300; // 5 minutes baseline
var SCRAPE_PHASES = [
    { at: 0,   label: 'Initialising scraper...' },
    { at: 15,  label: 'Connecting to SGCarMart.com...' },
    { at: 40,  label: 'Fetching active listings (page 1–5)...' },
    { at: 90,  label: 'Fetching active listings (page 6–12)...' },
    { at: 150, label: 'Fetching active listings (page 13–20)...' },
    { at: 210, label: 'Processing detail pages & cache...' },
    { at: 255, label: 'Detecting sold vehicles...' },
    { at: 280, label: 'Writing to database...' },
    { at: 295, label: 'Finalising report...' }
];

function _fmt(s) {
    var m = Math.floor(s / 60), sec = s % 60;
    return m + ':' + (sec < 10 ? '0' : '') + sec;
}

function showScrapingOverlay() {
    var overlay = document.getElementById('scrapingOverlay');
    var elapsedEl = document.getElementById('scrapeElapsed');
    var remainEl = document.getElementById('scrapeRemaining');
    var bar = document.getElementById('scrapeProgressBar');
    var phaseEl = document.getElementById('scrapePhaseLabel');
    if (!overlay) return;
    overlay.classList.add('active');
    var seconds = 0;
    window._scrapeTimerInterval = setInterval(function () {
        seconds++;
        // Elapsed
        if (elapsedEl) elapsedEl.textContent = _fmt(seconds);
        // Remaining (counts down from estimate, but never goes below 0:05)
        var remaining = Math.max(5, SCRAPE_ESTIMATE_SECS - seconds);
        if (remainEl) remainEl.textContent = '~' + _fmt(remaining);
        // Progress bar: asymptotic — fast early, slows near 95%
        var pct = Math.min(95, 95 * (1 - Math.exp(-seconds / 240)));
        if (bar) bar.style.width = pct + '%';
        // Phase label
        var phase = SCRAPE_PHASES[0].label;
        for (var i = 0; i < SCRAPE_PHASES.length; i++) {
            if (seconds >= SCRAPE_PHASES[i].at) phase = SCRAPE_PHASES[i].label;
        }
        if (phaseEl) phaseEl.textContent = phase;
    }, 1000);
}

function hideScrapingOverlay() {
    var overlay = document.getElementById('scrapingOverlay');
    var bar = document.getElementById('scrapeProgressBar');
    var phaseEl = document.getElementById('scrapePhaseLabel');
    if (overlay) overlay.classList.remove('active');
    if (bar) { bar.style.transition = 'width .3s'; bar.style.width = '100%'; }
    if (phaseEl) phaseEl.textContent = 'Done!';
    if (window._scrapeTimerInterval) {
        clearInterval(window._scrapeTimerInterval);
        window._scrapeTimerInterval = null;
    }
    setTimeout(function () {
        var elapsedEl = document.getElementById('scrapeElapsed');
        var remainEl = document.getElementById('scrapeRemaining');
        if (elapsedEl) elapsedEl.textContent = '0:00';
        if (remainEl) remainEl.textContent = '~5:00';
        if (bar) { bar.style.transition = 'none'; bar.style.width = '0%'; }
        if (phaseEl) phaseEl.textContent = 'Initialising...';
    }, 800);
}

async function triggerScrape() {
    var btn = document.getElementById('btnRefresh');
    if (btn.disabled) return;
    btn.disabled = true;
    document.getElementById('statusBadge').textContent = 'Scraping';
    document.getElementById('statusBadge').classList.add('scraping');
    showScrapingOverlay();
    try {
        var r = await fetch('/api/scrape', { method: 'POST' });
        if (r.status === 409) {
            hideScrapingOverlay();
            showNotification('Scrape already in progress', true);
            btn.disabled = false;
            loadStatus();
            return;
        }
        if (!r.ok) throw new Error('Failed to start scrape');
        var check = setInterval(async function () {
            var s = await fetch('/api/status').then(function (x) { return x.json(); }).catch(function () { return {}; });
            if (s.status === 'Ready') {
                clearInterval(check);
                hideScrapingOverlay();
                btn.disabled = false;
                loadStatus();
                loadDailyReport();
                loadHistory();
                loadSgcarmartSold();
                autoExpandAndLoadDepreciationTables();
                showNotification('Scraping selesai. Data sudah diperbarui!');
            }
        }, 3000);
        setTimeout(function () {
            clearInterval(check);
            hideScrapingOverlay();
            btn.disabled = false;
            loadStatus();
            loadDailyReport();
            loadHistory();
            loadSgcarmartSold();
            autoExpandAndLoadDepreciationTables();
        }, 300000);
    } catch (e) {
        hideScrapingOverlay();
        showNotification('Error: ' + e.message, true);
        btn.disabled = false;
        loadStatus();
    }
}

function exportData(format) {
    var date = getReportDate();
    if (!date) {
        showNotification('Select a report date first', true);
        return;
    }
    window.open('/api/export/' + format + '?date=' + date, '_blank');
    showNotification('Downloading ' + format.toUpperCase() + '...');
}

async function loadHistory() {
    try {
        var r = await fetchWithRetry('/api/history');
        if (!r.ok) return;
        var dates = await r.json();
        var sel = document.getElementById('historySelect');
        if (!sel) return;
        sel.innerHTML = '<option value="">-- History (' + dates.length + ' days) --</option>';
        dates.forEach(function (d) {
            var opt = document.createElement('option');
            opt.value = d.date;
            opt.textContent = d.date + ' (' + d.count + ' sold)';
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('loadHistory error:', e);
    }
}

function onHistorySelect() {
    var sel = document.getElementById('historySelect');
    if (sel && sel.value) {
        setReportDate(sel.value);
        loadDailyReport();
    }
}

async function clearSoldData() {
    var date = getReportDate();
    if (!date) {
        showNotification('No date selected', true);
        return;
    }
    if (!confirm('Clear all sold data for ' + date + '?\nYou can re-scrape after clearing.')) return;
    try {
        var r = await fetch('/api/sold-log/clear?date=' + date, { method: 'DELETE' });
        if (!r.ok) throw new Error('Failed to clear');
        var d = await r.json();
        showNotification(d.message);
        loadDailyReport();
        loadHistory();
    } catch (e) {
        showNotification('Error: ' + e.message, true);
    }
}

function formatSoldDate(dateStr) {
    if (!dateStr) return '–';
    var d = new Date(dateStr);
    var day = d.getDate();
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var mon = months[d.getMonth()];
    var year = d.getFullYear();
    return day + '-' + mon + '-' + year;
}

function buildSoldLogTable(list) {
    if (!list || list.length === 0) {
        return '<div class="sold-log-empty">No sold listings found. Click REFRESH DATA to scrape from SGCarMart.</div>';
    }
    var html = '<table class="table data-table sold-log-table">';
    html += '<thead><tr>';
    html += '<th style="width:40px">No</th>';
    html += '<th>Date Found Sold</th>';
    html += '<th class="vehicle-col">Name &amp; Model</th>';
    html += '<th>Year</th>';
    html += '<th>Depreciation</th>';
    html += '<th>Dealer</th>';
    html += '</tr></thead><tbody>';
    list.forEach(function (entry, idx) {
        html += '<tr>';
        html += '<td class="no-col">' + (idx + 1) + '</td>';
        html += '<td>' + formatSoldDate(entry.scrape_date) + '</td>';
        html += '<td class="vehicle-col">' + (entry.make_model || '–') + '</td>';
        html += '<td>' + (entry.year_registered != null ? entry.year_registered : '–') + '</td>';
        html += '<td class="depre-cell">' + (entry.depreciation || '–') + '</td>';
        html += '<td>' + (entry.dealer_name || '–') + '</td>';
        html += '</tr>';
    });
    html += '</tbody></table>';
    return html;
}

function toggleSoldLog() {
    var content = document.getElementById('soldLogContent');
    var icon = document.getElementById('soldLogToggleIcon');
    var isHidden = content.style.display === 'none';
    content.style.display = isHidden ? 'block' : 'none';
    icon.className = isHidden ? 'bi bi-chevron-down' : 'bi bi-chevron-right';
}

function toggleActiveLog() {
    var body = document.getElementById('activeLogBody');
    var icon = document.getElementById('activeLogIcon');
    var isHidden = body.style.display === 'none';
    body.style.display = isHidden ? 'block' : 'none';
    icon.className = isHidden ? 'bi bi-chevron-down' : 'bi bi-chevron-right';
}

function toggleGuide() {
    var body = document.getElementById('guideBody');
    var icon = document.getElementById('guideToggleIcon');
    var isHidden = body.style.display === 'none';
    body.style.display = isHidden ? 'block' : 'none';
    icon.className = isHidden ? 'bi bi-chevron-down' : 'bi bi-chevron-right';
}

async function loadActiveLog() {
    var dateInput = document.getElementById('activeLogDate');
    var date = dateInput && dateInput.value ? dateInput.value : '';
    if (!date) {
        showNotification('Please select a date', true);
        return;
    }
    var container = document.getElementById('activeLogContainer');
    var info = document.getElementById('activeLogInfo');
    container.innerHTML = '<div class="sold-log-empty">Loading...</div>';
    try {
        var r = await fetch('/api/listings?date=' + date + '&limit=5000');
        if (!r.ok) throw new Error('Failed');
        var list = await r.json();
        if (info) info.textContent = list.length + ' matched target vehicles';
        if (!list || list.length === 0) {
            container.innerHTML = '<div class="sold-log-empty">No active listings for this date.</div>';
            return;
        }
        var html = '<table class="table data-table sold-log-table">';
        html += '<thead><tr>';
        html += '<th style="width:35px">No</th>';
        html += '<th class="vehicle-col">Name &amp; Model</th>';
        html += '<th>Year</th>';
        html += '<th>Depreciation</th>';
        html += '<th>Dealer</th>';
        html += '</tr></thead><tbody>';
        list.forEach(function (entry, idx) {
            html += '<tr>';
            html += '<td class="no-col">' + (idx + 1) + '</td>';
            html += '<td class="vehicle-col">' + (entry.make_model || '–') + '</td>';
            html += '<td>' + (entry.registered_year != null ? entry.registered_year : '–') + '</td>';
            html += '<td class="depre-cell">' + (entry.depreciation || '–') + '</td>';
            html += '<td>' + (entry.dealer_name || '–') + '</td>';
            html += '</tr>';
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="sold-log-empty">Error loading listings.</div>';
    }
}

async function loadSgcarmartSold() {
    var container = document.getElementById('soldLogContainer');
    var countBadge = document.getElementById('soldLogCountBadge');
    var info = document.getElementById('soldLogInfo');
    container.innerHTML = '<div class="sold-log-empty">Loading...</div>';
    try {
        var r = await fetch('/api/sgcarmart-sold?limit=5000');
        if (!r.ok) throw new Error('Failed to load');
        var data = await r.json();
        var list = data.items || [];
        // data.total is now filtered (target vehicles only) — same as dep table total
        if (info) info.textContent = 'Showing ' + list.length + ' of ' + data.total + ' matched target vehicles (all-time)';
        container.innerHTML = buildSoldLogTable(list);
    } catch (e) {
        container.innerHTML = '<div class="sold-log-empty">Error loading sold listings.</div>';
    }
}

function exportSgcarmartSoldCsv() {
    window.open('/api/export/sgcarmart-sold-csv', '_blank');
    showNotification('Downloading SGCarMart Sold CSV...');
}

// Toggle depreciation tables
function toggleActiveDepreciationTable() {
    var body = document.getElementById('activeDepreciationBody');
    var icon = document.getElementById('activeDepreciationIcon');
    var isHidden = body.style.display === 'none';
    body.style.display = isHidden ? 'block' : 'none';
    icon.className = isHidden ? 'bi bi-chevron-down' : 'bi bi-chevron-right';
}

function toggleSoldDepreciationTable() {
    var body = document.getElementById('soldDepreciationBody');
    var icon = document.getElementById('soldDepreciationIcon');
    var isHidden = body.style.display === 'none';
    body.style.display = isHidden ? 'block' : 'none';
    icon.className = isHidden ? 'bi bi-chevron-down' : 'bi bi-chevron-right';
}

// Toggle AND auto-load sold depreciation when expanded
function toggleAndLoadSoldDepreciation() {
    var body = document.getElementById('soldDepreciationBody');
    var icon = document.getElementById('soldDepreciationIcon');
    var isHidden = body.style.display === 'none';

    body.style.display = isHidden ? 'block' : 'none';
    icon.className = isHidden ? 'bi bi-chevron-down' : 'bi bi-chevron-right';

    // Auto-load data when expanding (only load once)
    if (isHidden && !body.dataset.loaded) {
        loadSoldDepreciationTable();
        body.dataset.loaded = 'true';
    }
}

// Build depreciation table matching exact screenshot format
// Each year has 3 sub-columns: LOW, AVG, COUNT
function buildDepreciationTable(data, categories, dateStr) {
    var currentYear = new Date().getFullYear();
    var years = [];
    for (var y = currentYear; y >= 2016; y--) { years.push(y); }
    years.push("2015 & Older");

    var d = new Date(dateStr + 'T00:00:00');
    var months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    var formattedDate = d.getDate() + ' ' + months[d.getMonth()];

    // Colors
    var hdrBg = '#4472C4';
    var hdrBorder = '#3a63a8';
    var subHdrBg = '#D6E4F0';
    var subHdrColor = '#1f2937';
    var catBg = '#548235';
    var catBorder = '#3d6128';
    var cellBorder = '#B4C6E7';
    var emptyCell = '-';
    var countColBg = '#D6E4F0';
    var avgColBg = '#E8F0FE';

    var yearGroupCount = years.length; // all years (2014 to current)
    var catColSpan = 1 + (yearGroupCount * 3) + 1;
    var dataTotalCols = yearGroupCount * 3;

    // Shared cell style for readability
    var cs = 'text-align:center;padding:6px 5px;border:1px solid ' + cellBorder + ';';
    var csNum = cs + 'font-size:0.78rem;font-weight:700;letter-spacing:0.3px;';

    var html = '<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;">';
    html += '<table style="border-collapse:collapse;font-size:0.78rem;width:100%;min-width:1600px;">';

    // === TITLE ROW ===
    html += '<tr>';
    html += '<td style="background:#1f2937;color:white;font-weight:700;padding:10px 14px;border:1px solid ' + hdrBorder + ';white-space:nowrap;font-size:0.85rem;">DATE: ' + formattedDate + '</td>';
    html += '<td colspan="' + dataTotalCols + '" style="background:white;text-align:center;font-size:1.3rem;font-weight:800;letter-spacing:8px;padding:12px;border:1px solid ' + cellBorder + ';">D E P R E C I A T I O N &nbsp; / &nbsp; U N I T S</td>';
    html += '<td style="background:white;border:1px solid ' + cellBorder + ';"></td>';
    html += '</tr>';

    // === YEAR HEADERS ===
    html += '<tr>';
    html += '<td rowspan="2" style="background:' + hdrBg + ';color:white;font-weight:700;padding:8px 10px;border:1px solid ' + hdrBorder + ';text-align:center;vertical-align:middle;min-width:170px;font-size:0.82rem;"></td>';
    years.forEach(function(year) {
        html += '<td colspan="3" style="background:' + hdrBg + ';color:white;font-weight:700;text-align:center;padding:8px 4px;border:1px solid ' + hdrBorder + ';border-left:2px solid ' + hdrBorder + ';font-size:0.88rem;">' + year + '</td>';
    });
    html += '<td rowspan="2" style="background:' + hdrBg + ';color:white;font-weight:700;text-align:center;padding:8px 6px;border:1px solid ' + hdrBorder + ';vertical-align:middle;white-space:nowrap;font-size:0.82rem;">TOTAL<br>UNITS</td>';
    html += '</tr>';

    // === SUB-HEADERS: LOW / AVG / COUNT ===
    html += '<tr>';
    for (var i = 0; i < yearGroupCount; i++) {
        html += '<td style="background:' + subHdrBg + ';color:' + subHdrColor + ';font-weight:700;text-align:center;padding:5px 3px;border:1px solid ' + cellBorder + ';font-size:0.68rem;border-left:2px solid ' + cellBorder + ';">LOW</td>';
        html += '<td style="background:' + subHdrBg + ';color:' + subHdrColor + ';font-weight:700;text-align:center;padding:5px 3px;border:1px solid ' + cellBorder + ';font-size:0.68rem;">AVG</td>';
        html += '<td style="background:' + countColBg + ';color:' + subHdrColor + ';font-weight:700;text-align:center;padding:5px 3px;border:1px solid ' + cellBorder + ';font-size:0.68rem;">COUNT</td>';
    }
    html += '</tr>';

    // === DATA ROWS ===
    for (var category in categories) {
        if (!categories.hasOwnProperty(category)) continue;

        html += '<tr>';
        html += '<td colspan="' + catColSpan + '" style="background:' + catBg + ';color:white;font-weight:700;padding:9px 16px;text-align:left;border:1px solid ' + catBorder + ';font-size:0.85rem;letter-spacing:0.5px;">' + category + '</td>';
        html += '</tr>';

        var models = categories[category];
        var rowIdx = 0;
        models.forEach(function(vehicle) {
            var vehicleData = data[vehicle] || {};
            var rowBg = rowIdx % 2 === 0 ? '#FFFFFF' : '#F2F7FC';
            rowIdx++;

            html += '<tr style="background:' + rowBg + ';">';
            html += '<td style="text-align:left;font-weight:700;padding:6px 10px;border:1px solid ' + cellBorder + ';white-space:nowrap;font-size:0.8rem;color:#1e3a5f;">' + vehicle + '</td>';

            var totalUnits = 0;

            function renderYearGroup(yearData) {
                if (yearData && (yearData.lowest || yearData.unit)) {
                    var lo = yearData.lowest ? '$' + yearData.lowest.toLocaleString() : emptyCell;
                    var av = yearData.average ? '$' + yearData.average.toLocaleString() : emptyCell;
                    var un = yearData.unit || 0;
                    totalUnits += un;
                    html += '<td style="' + csNum + 'border-left:2px solid ' + cellBorder + ';color:#1a5f2a;">' + lo + '</td>';
                    html += '<td style="' + csNum + 'background:' + avgColBg + ';color:#4472C4;">' + av + '</td>';
                    html += '<td style="' + csNum + 'background:' + countColBg + ';color:#1f2937;">' + un + '</td>';
                } else {
                    html += '<td style="' + cs + 'border-left:2px solid ' + cellBorder + ';color:#d1d5db;">' + emptyCell + '</td>';
                    html += '<td style="' + cs + 'background:' + avgColBg + ';color:#d1d5db;">' + emptyCell + '</td>';
                    html += '<td style="' + cs + 'background:' + countColBg + ';color:#d1d5db;">' + emptyCell + '</td>';
                }
            }

            years.forEach(function(year) {
                var yd = vehicleData[year] || vehicleData[String(year)];
                renderYearGroup(yd);
            });

            html += '<td style="text-align:center;font-weight:800;padding:6px 8px;border:1px solid ' + cellBorder + ';background:#E2EFDA;font-size:0.88rem;color:#1a5f2a;">' + totalUnits + '</td>';
            html += '</tr>';
        });
    }

    html += '</table></div>';
    return html;
}

// Build sold count table (COUNT only, no LOW/AVG columns)
function buildSoldCountTable(data, categories, dateStr) {
    var currentYear = new Date().getFullYear();
    var years = [];
    for (var y = currentYear; y >= 2016; y--) { years.push(y); }
    years.push("2015 & Older");

    var d = new Date(dateStr + 'T00:00:00');
    var months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    var formattedDate = d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();

    // Colors
    var hdrBg = '#4472C4';
    var hdrBorder = '#3a63a8';
    var catBg = '#548235';
    var catBorder = '#3d6128';
    var cellBorder = '#B4C6E7';
    var emptyCell = '-';
    var countColBg = '#D6E4F0';

    var yearGroupCount = years.length;
    var catColSpan = 1 + yearGroupCount + 1;

    var cs = 'text-align:center;padding:6px 5px;border:1px solid ' + cellBorder + ';';
    var csNum = cs + 'font-size:0.82rem;font-weight:700;letter-spacing:0.3px;';

    var html = '<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;">';
    html += '<table style="border-collapse:collapse;font-size:0.78rem;width:100%;min-width:900px;">';

    // === TITLE ROW ===
    html += '<tr>';
    html += '<td style="background:#1f2937;color:white;font-weight:700;padding:10px 14px;border:1px solid ' + hdrBorder + ';white-space:nowrap;font-size:0.85rem;">AS OF: ' + formattedDate + '</td>';
    html += '<td colspan="' + yearGroupCount + '" style="background:white;text-align:center;font-size:1.2rem;font-weight:800;letter-spacing:6px;padding:12px;border:1px solid ' + cellBorder + ';">L A S T &nbsp; 6 0 &nbsp; D A Y S &nbsp; S O L D &nbsp; V E H I C L E S</td>';
    html += '<td style="background:white;border:1px solid ' + cellBorder + ';"></td>';
    html += '</tr>';

    // === YEAR HEADERS ===
    html += '<tr>';
    html += '<td style="background:' + hdrBg + ';color:white;font-weight:700;padding:8px 10px;border:1px solid ' + hdrBorder + ';text-align:center;vertical-align:middle;min-width:170px;font-size:0.82rem;"></td>';
    years.forEach(function(year) {
        html += '<td style="background:' + hdrBg + ';color:white;font-weight:700;text-align:center;padding:8px 6px;border:1px solid ' + hdrBorder + ';font-size:0.88rem;">' + year + '</td>';
    });
    html += '<td style="background:' + hdrBg + ';color:white;font-weight:700;text-align:center;padding:8px 6px;border:1px solid ' + hdrBorder + ';vertical-align:middle;white-space:nowrap;font-size:0.82rem;">TOTAL<br>UNITS</td>';
    html += '</tr>';

    // === DATA ROWS ===
    for (var category in categories) {
        if (!categories.hasOwnProperty(category)) continue;

        html += '<tr>';
        html += '<td colspan="' + catColSpan + '" style="background:' + catBg + ';color:white;font-weight:700;padding:9px 16px;text-align:left;border:1px solid ' + catBorder + ';font-size:0.85rem;letter-spacing:0.5px;">' + category + '</td>';
        html += '</tr>';

        var models = categories[category];
        var rowIdx = 0;
        models.forEach(function(vehicle) {
            var vehicleData = data[vehicle] || {};
            var rowBg = rowIdx % 2 === 0 ? '#FFFFFF' : '#F2F7FC';
            rowIdx++;

            html += '<tr style="background:' + rowBg + ';">';
            html += '<td style="text-align:left;font-weight:700;padding:6px 10px;border:1px solid ' + cellBorder + ';white-space:nowrap;font-size:0.8rem;color:#1e3a5f;">' + vehicle + '</td>';

            var totalUnits = 0;

            years.forEach(function(year) {
                var yd = vehicleData[year] || vehicleData[String(year)];
                if (yd && yd.unit) {
                    totalUnits += yd.unit;
                    html += '<td style="' + csNum + 'background:' + countColBg + ';color:#1f2937;">' + yd.unit + '</td>';
                } else {
                    html += '<td style="' + cs + 'background:' + countColBg + ';color:#d1d5db;">' + emptyCell + '</td>';
                }
            });

            html += '<td style="text-align:center;font-weight:800;padding:6px 8px;border:1px solid ' + cellBorder + ';background:#E2EFDA;font-size:0.88rem;color:#1a5f2a;">' + totalUnits + '</td>';
            html += '</tr>';
        });
    }

    html += '</table></div>';
    return html;
}

// Export depreciation table data
function exportDepreciationTable(source, format) {
    var dateInput = document.getElementById('activeDepreciationDate');
    var date = (source === 'active' && dateInput) ? dateInput.value : '';
    var url = '/api/export/depreciation-' + format + '?source=' + source;
    if (date) url += '&date=' + date;
    window.open(url, '_blank');
    showNotification('Downloading Depreciation ' + format.toUpperCase() + '...');
}

// Load active listings depreciation table
async function loadActiveDepreciationTable() {
    var dateInput = document.getElementById('activeDepreciationDate');
    var date = dateInput && dateInput.value ? dateInput.value : '';
    if (!date) {
        showNotification('Please select a date', true);
        return;
    }

    var container = document.getElementById('activeDepreciationContainer');
    container.innerHTML = '<div class="sold-log-empty">Loading...</div>';

    try {
        // Fetch depreciation data and categories in parallel
        var [depRes, catRes] = await Promise.all([
            fetchWithRetry('/api/depreciation-by-year?date=' + date + '&source=active'),
            fetchWithRetry('/api/vehicle-categories')
        ]);

        if (!depRes.ok || !catRes.ok) throw new Error('Failed to load data');

        var result = await depRes.json();
        var categories = await catRes.json();

        if (Object.keys(result.data).length === 0) {
            container.innerHTML = '<div class="sold-log-empty">No depreciation data for this date.</div>';
            return;
        }

        container.innerHTML = buildDepreciationTable(result.data, categories.categories, date);

        // Sync active listing badge to match exactly what dep table shows
        var totalDepUnits = 0;
        for (var m in result.data) {
            for (var y in result.data[m]) totalDepUnits += result.data[m][y].unit || 0;
        }
        var activeBadge = document.getElementById('activeLogBadge');
        if (activeBadge) activeBadge.textContent = totalDepUnits;
    } catch (e) {
        container.innerHTML = '<div class="sold-log-empty">Error loading depreciation table: ' + e.message + '</div>';
    }
}

// Load sold listings count table (last 60 days)
async function loadSoldDepreciationTable() {
    var container = document.getElementById('soldDepreciationContainer');
    container.innerHTML = '<div class="sold-log-empty">Loading...</div>';

    try {
        // Fetch sold data (last 60 days) and categories in parallel
        var [depRes, catRes] = await Promise.all([
            fetchWithRetry('/api/depreciation-by-year?source=sold&days=60'),
            fetchWithRetry('/api/vehicle-categories')
        ]);

        if (!depRes.ok || !catRes.ok) throw new Error('Failed to load data');

        var result = await depRes.json();
        var categories = await catRes.json();

        if (Object.keys(result.data).length === 0) {
            container.innerHTML = '<div class="sold-log-empty">No sold data in the last 60 days. Click REFRESH DATA to scrape SGCarMart sold listings.</div>';
            return;
        }

        // Use today's date for display
        var today = getLocalDateStr();
        container.innerHTML = buildSoldCountTable(result.data, categories.categories, today);

        // Show stats
        var totalModels = Object.keys(result.data).length;
        var totalUnits = 0;
        for (var model in result.data) {
            for (var year in result.data[model]) {
                totalUnits += result.data[model][year].unit || 0;
            }
        }
        // Sync badge
        var soldBadge = document.getElementById('soldLogCountBadge');
        if (soldBadge && totalUnits > 0) {
            soldBadge.textContent = totalUnits + ' (60d)';
            soldBadge.style.display = 'inline-block';
        }
        var soldInfo = document.getElementById('soldDepreciationInfo');
        if (soldInfo) {
            soldInfo.textContent = 'Total: ' + totalUnits + ' sold vehicles in last 60 days';
        }
        showNotification('Loaded sold count: ' + totalUnits + ' units across ' + totalModels + ' models (last 60 days)');
    } catch (e) {
        container.innerHTML = '<div class="sold-log-empty">Error loading sold count table: ' + e.message + '</div>';
    }
}

// Auto-expand & load both depreciation tables
function autoExpandAndLoadDepreciationTables() {
    var today = getLocalDateStr();

    // Active depreciation: expand + set date + load
    var activeBody = document.getElementById('activeDepreciationBody');
    var activeIcon = document.getElementById('activeDepreciationIcon');
    var activeDate = document.getElementById('activeDepreciationDate');
    if (activeBody && activeBody.style.display === 'none') {
        activeBody.style.display = 'block';
        if (activeIcon) activeIcon.className = 'bi bi-chevron-down';
    }
    if (activeDate) activeDate.value = today;
    loadActiveDepreciationTable();

    // Sold depreciation: expand + load
    var soldBody = document.getElementById('soldDepreciationBody');
    var soldIcon = document.getElementById('soldDepreciationIcon');
    if (soldBody && soldBody.style.display === 'none') {
        soldBody.style.display = 'block';
        if (soldIcon) soldIcon.className = 'bi bi-chevron-down';
    }
    loadSoldDepreciationTable();
    if (soldBody) soldBody.dataset.loaded = 'true';
}

document.addEventListener('DOMContentLoaded', function () {
    loadStatus();
    loadDashboardSummary();
    var today = getLocalDateStr();
    setReportDate(today);
    loadDailyReport();
    loadHistory();
    // Set default dates for log sections
    var activeDate = document.getElementById('activeLogDate');
    if (activeDate) activeDate.value = today;
    // Set default dates for depreciation tables
    var activeDepDate = document.getElementById('activeDepreciationDate');
    if (activeDepDate) activeDepDate.value = today;
    var soldDepDate = document.getElementById('soldDepreciationDate');
    if (soldDepDate) soldDepDate.value = today;
    // Auto-expand and load both depreciation tables on page load
    // (dep tables also set the badges so counts match exactly)
    autoExpandAndLoadDepreciationTables();
});

async function loadActiveLogCount(date) {
    // Show today's active listing count (same data source as dep table), not all-time total
    try {
        var d = date || getLocalDateStr();
        var r = await fetchWithRetry('/api/depreciation-by-year?source=active&date=' + d);
        if (!r.ok) return;
        var data = await r.json();
        var badge = document.getElementById('activeLogBadge');
        if (badge) badge.textContent = data.total_rows != null ? data.total_rows : 0;
    } catch(e) {}
}

async function loadSgcarmartSoldCount() {
    try {
        var r = await fetchWithRetry('/api/sgcarmart-sold?limit=1');
        if (!r.ok) return;
        var data = await r.json();
        var badge = document.getElementById('soldLogCountBadge');
        if (badge) {
            badge.textContent = data.total + ' total';
            badge.style.display = data.total > 0 ? 'inline-block' : 'none';
        }
    } catch(e) {}
}

// Load Gmail OAuth2 status
async function loadGmailStatus() {
    try {
        var r = await fetchWithRetry('/api/gmail-status');
        if (!r.ok) return;
        var s = await r.json();
        var notConn = document.getElementById('gmailNotConnected');
        var conn = document.getElementById('gmailConnected');
        var badge = document.getElementById('gmailEnabledBadge');
        if (s.connected) {
            if (notConn) notConn.style.display = 'none';
            if (conn) conn.style.display = 'block';
            var senderEl = document.getElementById('gmailSenderDisplay');
            if (senderEl) senderEl.textContent = s.sender_email || '—';
            var recipEl = document.getElementById('gmailRecipientInput');
            if (recipEl) recipEl.value = s.recipient || '';
            var sw = document.getElementById('gmailEnabledSwitch');
            if (sw) sw.checked = s.enabled === true || s.enabled === 'true';
            if (badge) {
                badge.textContent = (s.enabled === true || s.enabled === 'true') ? 'ENABLED' : 'DISABLED';
                badge.style.background = (s.enabled === true || s.enabled === 'true') ? '#16a34a' : '#6b7280';
                badge.style.color = 'white';
                badge.style.display = 'inline-block';
            }
        } else {
            if (notConn) notConn.style.display = 'block';
            if (conn) conn.style.display = 'none';
            if (badge) badge.style.display = 'none';
            // Show hint if Google credentials not configured
            var btn = document.getElementById('btnConnectGmail');
            if (btn && !s.has_client_id) {
                btn.title = 'Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env first';
            }
        }
        // Handle ?gmail_connected=1 redirect
        if (window.location.search.includes('gmail_connected=1')) {
            showNotification('Gmail connected successfully!');
            history.replaceState(null, '', window.location.pathname);
        }
    } catch(e) {}
}

function connectGmail() {
    fetch('/api/gmail-auth-url').then(function(r) {
        return r.json().then(function(d) { return { ok: r.ok, data: d }; });
    }).then(function(res) {
        if (res.ok && res.data.auth_url) {
            window.location.href = res.data.auth_url;
        } else {
            var msg = (res.data && (res.data.detail || res.data.message)) || 'Failed to get auth URL';
            showNotification(msg, true);
        }
    }).catch(function() { showNotification('Error connecting Gmail', true); });
}

async function disconnectGmail() {
    try {
        var r = await fetch('/api/gmail-logout', { method: 'POST' });
        if (r.ok) {
            showNotification('Gmail disconnected');
            loadGmailStatus();
        }
    } catch(e) { showNotification('Error disconnecting', true); }
}

async function saveGmailSettings() {
    var recipEl = document.getElementById('gmailRecipientInput');
    var sw = document.getElementById('gmailEnabledSwitch');
    var recipient = recipEl ? recipEl.value.trim() : '';
    var enabled = sw ? sw.checked : false;
    try {
        var r = await fetch('/api/gmail-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipient: recipient, enabled: enabled })
        });
        if (r.ok) {
            showNotification('Gmail settings saved');
            loadGmailStatus();
        } else {
            var d = await r.json();
            showNotification(d.detail || 'Failed to save settings', true);
        }
    } catch(e) { showNotification('Error saving settings', true); }
}

async function toggleGmailEnabled() {
    var sw = document.getElementById('gmailEnabledSwitch');
    var recipEl = document.getElementById('gmailRecipientInput');
    var enabled = sw ? sw.checked : false;
    var recipient = recipEl ? recipEl.value.trim() : '';
    try {
        var r = await fetch('/api/gmail-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipient: recipient, enabled: enabled })
        });
        var badge = document.getElementById('gmailEnabledBadge');
        if (r.ok && badge) {
            badge.textContent = enabled ? 'ENABLED' : 'DISABLED';
            badge.style.background = enabled ? '#16a34a' : '#6b7280';
            badge.style.display = 'inline-block';
        }
    } catch(e) {}
}

// LEGACY stub kept for old references (replaced by loadGmailStatus)
async function loadEmailSettings() {
    try {
        var r = await fetch('/api/email-settings');
        if (!r.ok) return;
        var s = await r.json();
        var badge = document.getElementById('emailEnabledBadge');
        var toEl = document.getElementById('emailToDisplay');
        var smtpEl = document.getElementById('emailSmtpDisplay');
        if (badge) {
            badge.textContent = s.enabled ? 'ENABLED' : 'DISABLED';
            badge.style.background = s.enabled ? '#1a5f2a' : '#6b7280';
            badge.style.color = 'white';
        }
        if (toEl) toEl.textContent = s.email_to || '(not set)';
        if (smtpEl) smtpEl.textContent = s.smtp_host ? s.smtp_host + ':' + s.smtp_port : '(not set)';
    } catch(e) {}
}

// Send email report now (Gmail OAuth2)
async function sendEmailNow() {
    var btn = document.getElementById('btnSendEmail');
    var statusEl = document.getElementById('emailStatusMsg');
    if (btn) btn.disabled = true;
    if (statusEl) statusEl.textContent = 'Sending...';

    try {
        var dateInput = document.getElementById('activeDepreciationDate');
        var date = dateInput && dateInput.value ? dateInput.value : getLocalDateStr();
        var r = await fetch('/api/send-email?date=' + date, { method: 'POST' });
        var data = await r.json();
        if (r.ok && data.success) {
            if (statusEl) statusEl.textContent = data.message;
            showNotification('Email sent successfully!');
        } else {
            var msg = data.detail || data.message || 'Failed to send email';
            if (statusEl) statusEl.textContent = msg;
            showNotification(msg, true);
        }
    } catch(e) {
        if (statusEl) statusEl.textContent = 'Error: ' + e.message;
        showNotification('Email error: ' + e.message, true);
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function restoreBackup(input) {
    var file = input.files[0];
    if (!file) return;
    var statusEl = document.getElementById('restoreStatus');
    statusEl.textContent = 'Uploading...';
    statusEl.style.color = '#9ca3af';
    var formData = new FormData();
    formData.append('file', file);
    try {
        var r = await fetch('/api/backup/restore', { method: 'POST', body: formData });
        var data = await r.json();
        if (r.ok && data.success) {
            statusEl.textContent = '✓ Restored successfully. Reloading...';
            statusEl.style.color = '#22c55e';
            showNotification('Database restored. Reloading page...');
            setTimeout(function () { location.reload(); }, 2000);
        } else {
            statusEl.textContent = '✗ ' + (data.detail || data.message || 'Restore failed');
            statusEl.style.color = '#ef4444';
        }
    } catch(e) {
        statusEl.textContent = '✗ Error: ' + e.message;
        statusEl.style.color = '#ef4444';
    }
    input.value = '';
}

// ══ Developer Tools toggle ══
function toggleDevTools() {
    var body = document.getElementById('devToolsBody');
    var chevron = document.getElementById('devToolsChevron');
    if (!body) return;
    var open = body.style.display !== 'none';
    body.style.display = open ? 'none' : 'block';
    if (chevron) chevron.style.transform = open ? '' : 'rotate(180deg)';
}

// ══ Error Reporter ══
var _errorLog = [];
var WA_NUMBER = '6282377660027';

function _showError(msg, source) {
    var entry = '[' + new Date().toISOString() + '] ' + (source || '') + '\n' + msg;
    _errorLog.unshift(entry);
    if (_errorLog.length > 20) _errorLog.pop();
    var reporter = document.getElementById('errorReporter');
    var textEl = document.getElementById('errorText');
    var waLink = document.getElementById('waReportLink');
    if (!reporter || !textEl) return;
    textEl.textContent = _errorLog.slice(0, 5).join('\n\n---\n\n');
    var waText = encodeURIComponent(
        'Bug Report — Ablink Scraper\n' +
        'URL: ' + window.location.href + '\n' +
        'Time: ' + new Date().toISOString() + '\n\n' +
        entry.substring(0, 300)
    );
    if (waLink) waLink.href = 'https://wa.me/' + WA_NUMBER + '?text=' + waText;
    reporter.style.display = 'block';
}

function copyError() {
    var text = _errorLog.join('\n\n---\n\n');
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function () {
            showNotification('Error log copied to clipboard');
        });
    } else {
        var ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta);
        ta.select(); document.execCommand('copy');
        document.body.removeChild(ta);
        showNotification('Copied!');
    }
}

function dismissError() {
    var reporter = document.getElementById('errorReporter');
    if (reporter) reporter.style.display = 'none';
}

// Global error catchers
window.onerror = function (msg, src, line, col, err) {
    _showError((err ? err.stack : msg) || msg, (src || '') + ':' + line + ':' + col);
    return false;
};
window.onunhandledrejection = function (e) {
    var msg = e.reason ? (e.reason.stack || e.reason.message || String(e.reason)) : String(e);
    _showError(msg, 'UnhandledRejection');
};

// ============================================================
// Market Dashboard
// ============================================================
function _fmtMoney(v) {
    if (v == null) return '—';
    return '$' + Number(v).toLocaleString();
}
function _trendBadge(trend, opts) {
    opts = opts || {};
    if (!trend || trend.direction == null || trend.delta == null) {
        return '<span class="dash-trend flat"><i class="bi bi-dash"></i> —</span>';
    }
    var isUnits = !!opts.units;
    var dir = trend.direction;
    var cls = 'flat';
    var icon = 'bi-dash';
    if (dir === 'up') {
        cls = isUnits ? 'units-up' : 'up';
        icon = 'bi-arrow-up-right';
    } else if (dir === 'down') {
        cls = isUnits ? 'units-down' : 'down';
        icon = 'bi-arrow-down-right';
    }
    var amt = opts.money ? _fmtMoney(trend.delta) : trend.delta;
    return '<span class="dash-trend ' + cls + '"><i class="bi ' + icon + '"></i> ' + amt + '</span>';
}

async function loadDashboardSummary() {
    try {
        var r = await fetchWithRetry('/api/dashboard-summary');
        if (!r.ok) return;
        var d = await r.json();

        var badge = document.getElementById('dashSnapshotBadge');
        if (badge) {
            badge.textContent = d.snapshot_date
                ? ('Snapshot: ' + d.snapshot_date + (d.compare_date ? ' vs ' + d.compare_date : ''))
                : 'No data yet';
        }

        var catRow = document.getElementById('dashCategoryRow');
        if (catRow) {
            catRow.innerHTML = (d.categories || []).map(function (c) {
                return '' +
                    '<div class="col-12 col-sm-6 col-lg-3">' +
                        '<div class="dash-card">' +
                            '<div class="dash-card-label">' + c.name + '</div>' +
                            '<div class="dash-card-row">' +
                                '<div class="dash-card-value">' + _fmtMoney(c.avg_dep) + '</div>' +
                                _trendBadge(c.avg_dep_trend, { money: true }) +
                            '</div>' +
                            '<div class="dash-card-sub">Avg depreciation / yr (7d trend)</div>' +
                            '<div class="dash-card-row mt-1">' +
                                '<div class="dash-card-value" style="font-size:1.05rem;">' + (c.units != null ? c.units : 0) + ' units</div>' +
                                _trendBadge(c.units_trend, { units: true }) +
                            '</div>' +
                        '</div>' +
                    '</div>';
            }).join('');
        }

        var setText = function (id, v) {
            var el = document.getElementById(id);
            if (el) el.textContent = v != null ? Number(v).toLocaleString() : 0;
        };
        var sg = d.sgcarmart_sold_summary || {};
        setText('sgSoldYesterdayVal', sg.yesterday);
        setText('sgSold7dVal', sg.last_7_days);
        setText('sgSold30dVal', sg.last_30_days);

        var wl = document.getElementById('dashWatchlist');
        if (wl) {
            wl.innerHTML = (d.watchlist || []).map(function (w) {
                return '' +
                    '<div class="dash-watch-card">' +
                        '<div class="dash-watch-model">' + w.model + '</div>' +
                        '<div class="dash-watch-metric">' +
                            '<span class="label">Avg dep/yr</span>' +
                            '<span class="value">' + _fmtMoney(w.avg_dep) + ' ' + _trendBadge(w.avg_dep_trend, { money: true }) + '</span>' +
                        '</div>' +
                        '<div class="dash-watch-metric">' +
                            '<span class="label">Units</span>' +
                            '<span class="value">' + (w.units != null ? w.units : 0) + ' ' + _trendBadge(w.units_trend, { units: true }) + '</span>' +
                        '</div>' +
                    '</div>';
            }).join('');
        }
    } catch (e) {
        console.error('Dashboard load failed:', e);
    }
}

// ============================================================
// Dashboard Customize Modal
// ============================================================
var _dashAvailableModels = [];
var _dashCfgState = { compare_days: 7, categories: [], watchlist: [] };

async function openDashboardSettings() {
    try {
        var r = await fetchWithRetry('/api/dashboard-config');
        if (!r.ok) throw new Error('Failed to load config');
        var data = await r.json();
        _dashAvailableModels = data.available_models || [];
        _dashCfgState = JSON.parse(JSON.stringify(data.config));
        _renderDashSettings();
        var modalEl = document.getElementById('dashSettingsModal');
        new bootstrap.Modal(modalEl).show();
    } catch (e) {
        showNotification('Could not load settings: ' + e.message, true);
    }
}

function _renderDashSettings() {
    document.getElementById('dashCfgCompareDays').value = _dashCfgState.compare_days || 7;

    var catBox = document.getElementById('dashCfgCategories');
    catBox.innerHTML = (_dashCfgState.categories || []).map(function (c, idx) {
        return _renderDashCategoryEditor(c, idx);
    }).join('');

    var wlBox = document.getElementById('dashCfgWatchlist');
    wlBox.innerHTML = (_dashCfgState.watchlist || []).map(function (m, idx) {
        return _renderDashWatchModelEditor(m, idx);
    }).join('');
}

function _renderDashCategoryEditor(cat, idx) {
    var modelChips = (cat.models || []).map(function (m, mIdx) {
        return '<span class="dash-cfg-chip">' +
                    _escapeHtml(m) +
                    ' <button type="button" class="btn-close btn-close-sm" aria-label="Remove" onclick="removeDashCatModel(' + idx + ',' + mIdx + ')"></button>' +
               '</span>';
    }).join('');
    return '' +
        '<div class="dash-cfg-card">' +
            '<div class="d-flex align-items-center gap-2 mb-2">' +
                '<input type="text" class="form-control form-control-sm fw-bold" value="' + _escapeAttr(cat.name || '') + '" onchange="updateDashCatName(' + idx + ', this.value)" placeholder="Category name">' +
                '<button class="btn btn-sm btn-outline-danger" onclick="removeDashCategory(' + idx + ')"><i class="bi bi-trash"></i></button>' +
            '</div>' +
            '<div class="dash-cfg-chips">' + (modelChips || '<span class="text-muted small">No models</span>') + '</div>' +
            '<div class="mt-2">' +
                '<select class="form-select form-select-sm" onchange="addDashCatModel(' + idx + ', this.value); this.value=\'\';">' +
                    '<option value="">+ Add model…</option>' +
                    _dashAvailableModels.map(function (m) {
                        return '<option value="' + _escapeAttr(m) + '">' + _escapeHtml(m) + '</option>';
                    }).join('') +
                '</select>' +
            '</div>' +
        '</div>';
}

function _renderDashWatchModelEditor(model, idx) {
    return '' +
        '<div class="d-flex gap-2 mb-2">' +
            '<select class="form-select form-select-sm" onchange="updateDashWatchModel(' + idx + ', this.value)">' +
                _dashAvailableModels.map(function (m) {
                    var sel = (m === model) ? ' selected' : '';
                    return '<option value="' + _escapeAttr(m) + '"' + sel + '>' + _escapeHtml(m) + '</option>';
                }).join('') +
            '</select>' +
            '<button class="btn btn-sm btn-outline-danger" onclick="removeDashWatchModel(' + idx + ')"><i class="bi bi-trash"></i></button>' +
        '</div>';
}

function _escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
}
function _escapeAttr(s) { return _escapeHtml(s); }

function addDashCategory() {
    _dashCfgState.categories.push({ name: 'NEW CATEGORY', models: [] });
    _renderDashSettings();
}
function removeDashCategory(idx) {
    _dashCfgState.categories.splice(idx, 1);
    _renderDashSettings();
}
function updateDashCatName(idx, name) {
    if (_dashCfgState.categories[idx]) _dashCfgState.categories[idx].name = name;
}
function addDashCatModel(catIdx, model) {
    if (!model) return;
    var cat = _dashCfgState.categories[catIdx];
    if (!cat) return;
    cat.models = cat.models || [];
    if (cat.models.indexOf(model) === -1) {
        cat.models.push(model);
        _renderDashSettings();
    }
}
function removeDashCatModel(catIdx, modelIdx) {
    var cat = _dashCfgState.categories[catIdx];
    if (cat && cat.models) {
        cat.models.splice(modelIdx, 1);
        _renderDashSettings();
    }
}
function addDashWatchModel() {
    _dashCfgState.watchlist.push(_dashAvailableModels[0] || '');
    _renderDashSettings();
}
function updateDashWatchModel(idx, value) {
    _dashCfgState.watchlist[idx] = value;
}
function removeDashWatchModel(idx) {
    _dashCfgState.watchlist.splice(idx, 1);
    _renderDashSettings();
}

async function saveDashSettings() {
    var cd = parseInt(document.getElementById('dashCfgCompareDays').value, 10);
    if (isNaN(cd) || cd < 1) cd = 7;
    _dashCfgState.compare_days = cd;
    try {
        var r = await fetchWithRetry('/api/dashboard-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(_dashCfgState)
        });
        if (!r.ok) throw new Error('Save failed');
        showNotification('Dashboard settings saved');
        var modalEl = document.getElementById('dashSettingsModal');
        bootstrap.Modal.getInstance(modalEl).hide();
        await loadDashboardSummary();
    } catch (e) {
        showNotification('Save failed: ' + e.message, true);
    }
}

async function resetDashSettings() {
    if (!confirm('Reset to default dashboard config?')) return;
    try {
        var r = await fetchWithRetry('/api/dashboard-config/reset', { method: 'POST' });
        if (!r.ok) throw new Error('Reset failed');
        var data = await r.json();
        _dashCfgState = JSON.parse(JSON.stringify(data.config));
        _renderDashSettings();
        showNotification('Reset to default');
        await loadDashboardSummary();
    } catch (e) {
        showNotification('Reset failed: ' + e.message, true);
    }
}

