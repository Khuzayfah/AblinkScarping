// Ablink SGCarmart Scraper - Frontend

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
        var r = await fetch('/api/status');
        if (!r.ok) return;
        var s = await r.json();
        document.getElementById('statusBadge').textContent = s.status;
        document.getElementById('statusBadge').classList.toggle('scraping', s.status === 'Scraping');
        document.getElementById('lastScrape').textContent = s.last_scrape_at
            ? 'Last scrape: ' + s.last_scrape_at
            : 'Last scrape: —';
        if (s.schedule_display) {
            var [h, m] = s.schedule_display.split(':');
            document.getElementById('scheduleTime').value = (h.length === 1 ? '0' + h : h) + ':' + (m.length === 1 ? '0' + m : m);
            document.getElementById('currentSchedule').textContent = 'Current: ' + formatTimeDisplay(parseInt(h), parseInt(m)) + ' SGT';
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
    return d ? d.value : new Date().toISOString().slice(0, 10);
}

function setReportDate(val) {
    var d = document.getElementById('reportDate');
    var d2 = document.getElementById('reportDateTop');
    if (d) d.value = val;
    if (d2) d2.value = val;
}

function navDate(offset) {
    var current = getReportDate();
    if (!current) current = new Date().toISOString().slice(0, 10);
    var d = new Date(current + 'T00:00:00');
    d.setDate(d.getDate() + offset);
    var today = new Date();
    today.setHours(0,0,0,0);
    if (d > today) return; // Don't go to future
    var newDate = d.toISOString().slice(0, 10);
    setReportDate(newDate);
    loadDailyReport();
}

function navToday() {
    var today = new Date().toISOString().slice(0, 10);
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
        var r = await fetch('/api/daily-report?date=' + date);
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
        document.getElementById('emptyState').style.display = 'block';
        document.getElementById('dataTableWrapper').style.display = 'none';
    } finally {
        setLoading(false);
    }
}

async function triggerScrape() {
    var btn = document.getElementById('btnRefresh');
    if (btn.disabled) return;
    btn.disabled = true;
    document.getElementById('statusBadge').textContent = 'Scraping';
    document.getElementById('statusBadge').classList.add('scraping');
    try {
        var r = await fetch('/api/scrape', { method: 'POST' });
        if (r.status === 409) {
            showNotification('Scrape already in progress', true);
            btn.disabled = false;
            loadStatus();
            return;
        }
        if (!r.ok) throw new Error('Failed to start scrape');
        showNotification('Scraping started. This may take a few minutes.');
        var check = setInterval(async function () {
            var s = await fetch('/api/status').then(function (x) { return x.json(); }).catch(function () { return {}; });
            if (s.status === 'Ready') {
                clearInterval(check);
                btn.disabled = false;
                loadStatus();
                loadDailyReport();
                loadHistory();
                loadSgcarmartSold();
                loadSgcarmartSoldCount();
                loadActiveLogCount();
                showNotification('Scraping completed. All data refreshed.');
            }
        }, 3000);
        setTimeout(function () {
            clearInterval(check);
            btn.disabled = false;
            loadStatus();
            loadDailyReport();
            loadHistory();
            loadSgcarmartSold();
            loadSgcarmartSoldCount();
            loadActiveLogCount();
        }, 300000);
    } catch (e) {
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
        var r = await fetch('/api/history');
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
        var r = await fetch('/api/listings?date=' + date + '&limit=500');
        if (!r.ok) throw new Error('Failed');
        var list = await r.json();
        if (info) info.textContent = list.length + ' listings found';
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
        var r = await fetch('/api/sgcarmart-sold?limit=500');
        if (!r.ok) throw new Error('Failed to load');
        var data = await r.json();
        var list = data.items || [];
        if (countBadge) {
            countBadge.textContent = data.total + ' total';
            countBadge.style.display = data.total > 0 ? 'inline-block' : 'none';
        }
        if (info) info.textContent = 'Showing ' + list.length + ' of ' + data.total + ' sold listings';
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
// Each year has 3 sub-columns: Lowest, Average, Unit
function buildDepreciationTable(data, categories, dateStr) {
    // Fixed year columns from current year down to 2015, then "2014 & Older"
    var currentYear = new Date().getFullYear();
    var years = [];
    for (var y = currentYear; y >= 2015; y--) {
        years.push(y);
    }
    var OLDER_KEY = '2014'; // merged "2014 & Older" bucket from API

    // Format date: "DATE: 9 DEC"
    var d = new Date(dateStr + 'T00:00:00');
    var months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    var formattedDate = d.getDate() + ' ' + months[d.getMonth()];

    // Style constants matching screenshot
    var hdrBg = '#4472C4';
    var hdrBorder = '#3a63a8';
    var subHdrBg = '#D6E4F0';
    var subHdrColor = '#1f2937';
    var catBg = '#548235';
    var catBorder = '#3d6128';
    var cellBorder = '#B4C6E7';
    var emptyCell = '-';
    var unitColBg = '#D6E4F0';   // light blue tint for unit columns
    var avgColBg = '#E8F0FE';    // slightly different blue for average

    // Total columns for category colspan: 1 (vehicle) + (years+1)*3 (L,A,U per year incl older) + 1 (total units)
    var yearGroupCount = years.length + 1; // +1 for "2014 & Older"
    var catColSpan = 1 + (yearGroupCount * 3) + 1;

    var html = '<div style="overflow-x:auto;"><table style="border-collapse:collapse;font-size:0.72rem;width:100%;min-width:1600px;">';

    // === ROW 1: TITLE ===
    var dataTotalCols = yearGroupCount * 3; // all data columns (years * 3)
    html += '<tr>';
    html += '<td style="background:#1f2937;color:white;font-weight:700;padding:8px 12px;border:1px solid ' + hdrBorder + ';white-space:nowrap;">DATE: ' + formattedDate + '</td>';
    html += '<td colspan="' + dataTotalCols + '" style="background:white;text-align:center;font-size:1.3rem;font-weight:800;letter-spacing:6px;padding:10px;border:1px solid ' + cellBorder + ';">D E P R E C I A T I O N &nbsp; / &nbsp; U N I T S</td>';
    html += '<td style="background:white;border:1px solid ' + cellBorder + ';"></td>';
    html += '</tr>';

    // === ROW 2: YEAR HEADERS ===
    html += '<tr>';
    html += '<td rowspan="2" style="background:' + hdrBg + ';color:white;font-weight:700;padding:6px 8px;border:1px solid ' + hdrBorder + ';text-align:center;vertical-align:middle;min-width:160px;"></td>';
    years.forEach(function(year) {
        html += '<td colspan="3" style="background:' + hdrBg + ';color:white;font-weight:700;text-align:center;padding:6px 2px;border:1px solid ' + hdrBorder + ';border-left:2px solid ' + hdrBorder + ';">' + year + '</td>';
    });
    html += '<td colspan="3" style="background:' + hdrBg + ';color:white;font-weight:700;text-align:center;padding:6px 2px;border:1px solid ' + hdrBorder + ';border-left:2px solid ' + hdrBorder + ';white-space:nowrap;">2014 &amp; Older</td>';
    html += '<td rowspan="2" style="background:' + hdrBg + ';color:white;font-weight:700;text-align:center;padding:6px 4px;border:1px solid ' + hdrBorder + ';vertical-align:middle;white-space:nowrap;">TOTAL<br>UNITS</td>';
    html += '</tr>';

    // === ROW 3: SUB-HEADERS (Lowest / Average / Unit) ===
    html += '<tr>';
    for (var i = 0; i < yearGroupCount; i++) {
        html += '<td style="background:' + subHdrBg + ';color:' + subHdrColor + ';font-weight:600;text-align:center;padding:3px 1px;border:1px solid ' + cellBorder + ';font-size:0.62rem;border-left:2px solid ' + cellBorder + ';">Lowest</td>';
        html += '<td style="background:' + subHdrBg + ';color:' + subHdrColor + ';font-weight:600;text-align:center;padding:3px 1px;border:1px solid ' + cellBorder + ';font-size:0.62rem;">Average</td>';
        html += '<td style="background:' + unitColBg + ';color:' + subHdrColor + ';font-weight:600;text-align:center;padding:3px 1px;border:1px solid ' + cellBorder + ';font-size:0.62rem;"></td>';
    }
    html += '</tr>';

    // === DATA ROWS ===
    for (var category in categories) {
        if (!categories.hasOwnProperty(category)) continue;

        // Category header
        html += '<tr>';
        html += '<td colspan="' + catColSpan + '" style="background:' + catBg + ';color:white;font-weight:700;padding:7px 14px;text-align:left;border:1px solid ' + catBorder + ';font-size:0.8rem;letter-spacing:0.5px;">' + category + '</td>';
        html += '</tr>';

        var models = categories[category];
        var rowIdx = 0;
        models.forEach(function(vehicle) {
            var vehicleData = data[vehicle] || {};
            var rowBg = rowIdx % 2 === 0 ? '#FFFFFF' : '#F2F7FC';
            rowIdx++;

            html += '<tr style="background:' + rowBg + ';">';
            html += '<td style="text-align:left;font-weight:600;padding:4px 8px;border:1px solid ' + cellBorder + ';white-space:nowrap;">' + vehicle + '</td>';

            var totalUnits = 0;

            // Helper to render one year group (3 cells)
            function renderYearGroup(yearData) {
                if (yearData && (yearData.lowest || yearData.unit)) {
                    var lo = yearData.lowest ? '$' + yearData.lowest.toLocaleString() : emptyCell;
                    var av = yearData.average ? '$' + yearData.average.toLocaleString() : emptyCell;
                    var un = yearData.unit || 0;
                    totalUnits += un;
                    html += '<td style="text-align:center;padding:3px 2px;border:1px solid ' + cellBorder + ';border-left:2px solid ' + cellBorder + ';font-size:0.71rem;">' + lo + '</td>';
                    html += '<td style="text-align:center;padding:3px 2px;border:1px solid ' + cellBorder + ';font-size:0.71rem;background:' + avgColBg + ';">' + av + '</td>';
                    html += '<td style="text-align:center;padding:3px 2px;border:1px solid ' + cellBorder + ';font-size:0.71rem;background:' + unitColBg + ';font-weight:600;">' + un + '</td>';
                } else {
                    html += '<td style="text-align:center;padding:3px 2px;border:1px solid ' + cellBorder + ';border-left:2px solid ' + cellBorder + ';color:#ccc;">' + emptyCell + '</td>';
                    html += '<td style="text-align:center;padding:3px 2px;border:1px solid ' + cellBorder + ';background:' + avgColBg + ';color:#ccc;">' + emptyCell + '</td>';
                    html += '<td style="text-align:center;padding:3px 2px;border:1px solid ' + cellBorder + ';background:' + unitColBg + ';color:#ccc;">' + emptyCell + '</td>';
                }
            }

            // Regular years
            years.forEach(function(year) {
                var yd = vehicleData[year] || vehicleData[String(year)];
                renderYearGroup(yd);
            });

            // "2014 & Older"
            var olderData = vehicleData[OLDER_KEY] || vehicleData[parseInt(OLDER_KEY)];
            renderYearGroup(olderData);

            // Total Units
            html += '<td style="text-align:center;font-weight:700;padding:4px 6px;border:1px solid ' + cellBorder + ';background:#E2EFDA;font-size:0.8rem;">' + totalUnits + '</td>';
            html += '</tr>';
        });
    }

    html += '</table></div>';
    return html;
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
            fetch('/api/depreciation-by-year?date=' + date + '&source=active'),
            fetch('/api/vehicle-categories')
        ]);

        if (!depRes.ok || !catRes.ok) throw new Error('Failed to load data');

        var result = await depRes.json();
        var categories = await catRes.json();

        if (Object.keys(result.data).length === 0) {
            container.innerHTML = '<div class="sold-log-empty">No depreciation data for this date.</div>';
            return;
        }

        container.innerHTML = buildDepreciationTable(result.data, categories.categories, date);
    } catch (e) {
        container.innerHTML = '<div class="sold-log-empty">Error loading depreciation table: ' + e.message + '</div>';
    }
}

// Load sold listings depreciation table (ALL-TIME accumulated sold data)
async function loadSoldDepreciationTable() {
    var container = document.getElementById('soldDepreciationContainer');
    container.innerHTML = '<div class="sold-log-empty">Loading...</div>';

    try {
        // Fetch depreciation data and categories in parallel
        // Note: sold source uses ALL accumulated sold data (all-time), no date filter
        var [depRes, catRes] = await Promise.all([
            fetch('/api/depreciation-by-year?source=sold'),
            fetch('/api/vehicle-categories')
        ]);

        if (!depRes.ok || !catRes.ok) throw new Error('Failed to load data');

        var result = await depRes.json();
        var categories = await catRes.json();

        if (Object.keys(result.data).length === 0) {
            container.innerHTML = '<div class="sold-log-empty">No sold depreciation data available. Click REFRESH DATA to scrape SGCarMart sold listings.</div>';
            return;
        }

        // Use today's date for display since it's current accumulated data
        var today = new Date().toISOString().slice(0, 10);
        container.innerHTML = buildDepreciationTable(result.data, categories.categories, today);

        // Show stats
        var totalModels = Object.keys(result.data).length;
        var totalUnits = 0;
        for (var model in result.data) {
            for (var year in result.data[model]) {
                totalUnits += result.data[model][year].unit || 0;
            }
        }
        showNotification('Loaded sold depreciation: ' + totalUnits + ' units across ' + totalModels + ' models (all-time accumulated)');
    } catch (e) {
        container.innerHTML = '<div class="sold-log-empty">Error loading sold depreciation table: ' + e.message + '</div>';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadStatus();
    var today = new Date().toISOString().slice(0, 10);
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
    // Load stats for badges
    loadActiveLogCount(today);
    loadSgcarmartSoldCount();
});

async function loadActiveLogCount(date) {
    try {
        var r2 = await fetch('/api/statistics');
        if (!r2.ok) return;
        var stats = await r2.json();
        var badge = document.getElementById('activeLogBadge');
        if (badge) badge.textContent = stats.total_listings;
    } catch(e) {}
}

async function loadSgcarmartSoldCount() {
    try {
        var r = await fetch('/api/sgcarmart-sold?limit=1');
        if (!r.ok) return;
        var data = await r.json();
        var badge = document.getElementById('soldLogCountBadge');
        if (badge) {
            badge.textContent = data.total + ' total';
            badge.style.display = data.total > 0 ? 'inline-block' : 'none';
        }
    } catch(e) {}
}
