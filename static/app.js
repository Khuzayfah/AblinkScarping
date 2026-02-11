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

// Build depreciation table like screenshot with category grouping
function buildDepreciationTable(data, categories, dateStr) {
    // Get all years from all vehicles
    var allYears = new Set();
    for (var model in data) {
        if (data.hasOwnProperty(model)) {
            for (var year in data[model]) {
                allYears.add(parseInt(year));
            }
        }
    }
    var years = Array.from(allYears).sort().reverse(); // 2025, 2024, 2023...

    if (years.length === 0) {
        return '<div class="sold-log-empty">No data available for this date.</div>';
    }

    // Format date nicely: "9 DEC"
    var dateParts = dateStr.split('-'); // 2026-02-09
    var d = new Date(dateStr + 'T00:00:00');
    var months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    var formattedDate = d.getDate() + ' ' + months[d.getMonth()];

    var yearColSpan = years.length * 3; // 3 columns per year (L, A, U)
    var totalColSpan = yearColSpan + 3; // +3 for DATE + VEHICLE NAME + TOTAL UNITS

    var html = '<table class="table data-table" style="font-size:0.75rem;">';

    // Header row: DATE | Vehicle Name | 2025 [L][A][U] | 2024 [L][A][U] | ...
    html += '<thead><tr>';
    html += '<th style="width:80px;background:#1f2937;color:white;border:1px solid #374151;">DATE</th>';
    html += '<th style="text-align:left;background:#1f2937;color:white;border:1px solid #374151;min-width:180px;">VEHICLE NAME</th>';

    years.forEach(function(year) {
        html += '<th colspan="3" style="background:#1f2937;color:white;border-left:2px solid #4b5563;border:1px solid #374151;text-align:center;">' + year + '</th>';
    });
    html += '<th style="background:#1f2937;color:white;border:1px solid #374151;text-align:center;">TOTAL UNITS</th>';
    html += '</tr>';

    // Sub-header: [LOWEST] [AVERAGE] [UNIT] for each year
    html += '<tr>';
    html += '<th style="background:#374151;color:white;border:1px solid #4b5563;"></th>';
    html += '<th style="background:#374151;color:white;border:1px solid #4b5563;"></th>';
    years.forEach(function(year) {
        html += '<th style="background:#374151;color:white;border:1px solid #4b5563;text-align:center;font-size:0.7rem;">LOWEST</th>';
        html += '<th style="background:#374151;color:white;border:1px solid #4b5563;text-align:center;font-size:0.7rem;">AVERAGE</th>';
        html += '<th style="background:#374151;color:white;border:1px solid #4b5563;text-align:center;font-size:0.7rem;">UNIT</th>';
    });
    html += '<th style="background:#374151;color:white;border:1px solid #4b5563;"></th>';
    html += '</tr></thead>';

    html += '<tbody>';

    // Iterate through categories
    for (var category in categories) {
        if (!categories.hasOwnProperty(category)) continue;

        // Category header row
        html += '<tr class="category-row">';
        html += '<td colspan="' + totalColSpan + '" style="background:#1a5f2a;color:white;font-weight:700;padding:10px 14px;text-align:left;border:1px solid #145221;">';
        html += category;
        html += '</td></tr>';

        // Models in this category
        var models = categories[category];
        models.forEach(function(vehicle) {
            var vehicleData = data[vehicle] || {};

            html += '<tr style="background:#f9fafb;">';
            html += '<td style="text-align:center;border:1px solid #e5e7eb;font-size:0.75rem;">' + formattedDate + '</td>';
            html += '<td style="text-align:left;font-weight:500;border:1px solid #e5e7eb;">' + vehicle + '</td>';

            var totalUnits = 0;
            years.forEach(function(year) {
                var yearData = vehicleData[year];
                if (yearData) {
                    var lowest = yearData.lowest ? '$' + yearData.lowest.toLocaleString() : '–';
                    var average = yearData.average ? '$' + yearData.average.toLocaleString() : '–';
                    var unit = yearData.unit || 0;
                    totalUnits += unit;

                    html += '<td style="text-align:center;border:1px solid #e5e7eb;">' + lowest + '</td>';
                    html += '<td style="text-align:center;border:1px solid #e5e7eb;">' + average + '</td>';
                    html += '<td style="text-align:center;border:1px solid #e5e7eb;">' + unit + '</td>';
                } else {
                    html += '<td style="text-align:center;border:1px solid #e5e7eb;">–</td>';
                    html += '<td style="text-align:center;border:1px solid #e5e7eb;">–</td>';
                    html += '<td style="text-align:center;border:1px solid #e5e7eb;">0</td>';
                }
            });

            html += '<td style="text-align:center;font-weight:600;border:1px solid #e5e7eb;">' + totalUnits + '</td>';
            html += '</tr>';
        });
    }

    html += '</tbody></table>';
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

// Load sold listings depreciation table
async function loadSoldDepreciationTable() {
    var dateInput = document.getElementById('soldDepreciationDate');
    var date = dateInput && dateInput.value ? dateInput.value : '';
    if (!date) {
        showNotification('Please select a date', true);
        return;
    }

    var container = document.getElementById('soldDepreciationContainer');
    container.innerHTML = '<div class="sold-log-empty">Loading...</div>';

    try {
        // Fetch depreciation data and categories in parallel
        var [depRes, catRes] = await Promise.all([
            fetch('/api/depreciation-by-year?date=' + date + '&source=sold'),
            fetch('/api/vehicle-categories')
        ]);

        if (!depRes.ok || !catRes.ok) throw new Error('Failed to load data');

        var result = await depRes.json();
        var categories = await catRes.json();

        if (Object.keys(result.data).length === 0) {
            container.innerHTML = '<div class="sold-log-empty">No sold depreciation data for this date.</div>';
            return;
        }

        container.innerHTML = buildDepreciationTable(result.data, categories.categories, date);
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
