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
            document.getElementById('currentSchedule').textContent = 'Current: ' + formatTimeDisplay(parseInt(h), parseInt(m));
        } else {
            document.getElementById('currentSchedule').textContent = 'Current: —';
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
        document.getElementById('currentSchedule').textContent = 'Current: ' + formatTimeDisplay(d.schedule.hour, d.schedule.minute);
        showNotification('Schedule updated');
    } catch (e) {
        showNotification('Error: ' + e.message, true);
    }
}

function formatPrice(val) {
    if (val == null || val === '') return '–';
    return '$' + Number(val).toLocaleString();
}

// Daily table columns: Date | Name & Model | Year registered | Depreciation | Dealer name
var DAILY_COLUMNS = [
    { key: 'date', label: 'Date' },
    { key: 'name_model', label: 'Name & Model' },
    { key: 'year_registered', label: 'Year registered' },
    { key: 'depreciation', label: 'Depreciation' },
    { key: 'dealer_name', label: 'Dealer name' }
];

function buildTable(dailyRows) {
    var thead = document.getElementById('tableHead');
    var tbody = document.getElementById('dataTableBody');
    thead.innerHTML = '';
    tbody.innerHTML = '';

    var tr = document.createElement('tr');
    DAILY_COLUMNS.forEach(function (col) {
        var th = document.createElement('th');
        th.textContent = col.label;
        if (col.key === 'name_model') th.className = 'vehicle-col';
        tr.appendChild(th);
    });
    thead.appendChild(tr);

    (dailyRows || []).forEach(function (row) {
        var tr = document.createElement('tr');
        DAILY_COLUMNS.forEach(function (col) {
            var td = document.createElement('td');
            var val = row[col.key];
            if (col.key === 'name_model') {
                td.className = 'vehicle-col';
                td.textContent = val == null ? '–' : val;
            } else {
                td.textContent = val == null || val === '' ? '–' : val;
            }
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
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
        document.getElementById('reportDateLabel').textContent = data.date;
        if (data.daily_table && data.daily_table.length > 0) {
            document.getElementById('emptyState').style.display = 'none';
            document.getElementById('dataTableWrapper').style.display = 'block';
            document.getElementById('exportBar').style.display = 'flex';
            buildTable(data.daily_table);
        } else {
            document.getElementById('emptyState').style.display = 'block';
            document.getElementById('dataTableWrapper').style.display = 'none';
            document.getElementById('exportBar').style.display = 'none';
            document.getElementById('reportDate').value = date;
        }
        showNotification('Report loaded for ' + date);
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
                showNotification('Scraping completed.');
            }
        }, 3000);
        setTimeout(function () {
            clearInterval(check);
            btn.disabled = false;
            loadStatus();
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

function formatSoldDate(dateStr) {
    if (!dateStr) return '–';
    var d = new Date(dateStr);
    var day = d.getDate();
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var mon = months[d.getMonth()];
    var year = d.getFullYear();
    return day + '-' + mon + '-' + year;
}

function buildSoldLogLine(entry) {
    var date = '<span class="sold-log-date">' + formatSoldDate(entry.sold_date) + '</span>';
    var make = '<span class="sold-log-make">' + (entry.make_model || '–') + '</span>';
    var year = '<span class="sold-log-year">' + (entry.year_registered != null ? entry.year_registered : '–') + '</span>';
    var depre = '<span class="sold-log-depre">' + (entry.depreciation || '–') + '</span>';
    var dealer = '<span class="sold-log-dealer">' + (entry.dealer_name || '–') + '</span>';
    return date + ' / ' + make + ' / ' + year + ' / ' + depre + ' / ' + dealer;
}

async function loadSoldLog() {
    var dateInput = document.getElementById('soldLogDate');
    var date = dateInput && dateInput.value ? dateInput.value : '';
    var url = '/api/sold-log' + (date ? '?date=' + date : '');
    var container = document.getElementById('soldLogContainer');
    try {
        var r = await fetch(url);
        if (!r.ok) throw new Error('Failed to load sold log');
        var list = await r.json();
        if (!list || list.length === 0) {
            container.innerHTML = '<div class="sold-log-empty">No sold log entries for this period.</div>';
            return;
        }
        container.innerHTML = list.map(function (entry) {
            return '<div class="sold-log-line">' + buildSoldLogLine(entry) + '</div>';
        }).join('');
    } catch (e) {
        container.innerHTML = '<div class="sold-log-empty">Error loading sold log.</div>';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadStatus();
    var today = new Date().toISOString().slice(0, 10);
    setReportDate(today);
    loadDailyReport();
    loadSoldLog();
});

// ============================================================
// DEBUG CONSOLE FUNCTIONS
// ============================================================

function debugLog(message, type = 'info') {
    const output = document.getElementById('debugOutput');
    const timestamp = new Date().toLocaleTimeString();
    const line = document.createElement('div');

    let icon = '';
    let className = 'debug-log-info';

    if (type === 'success') {
        icon = '✓';
        className = 'debug-log-success';
    } else if (type === 'error') {
        icon = '✗';
        className = 'debug-log-error';
    } else if (type === 'warning') {
        icon = '⚠';
        className = 'debug-log-warning';
    } else if (type === 'info') {
        icon = 'ℹ';
        className = 'debug-log-info';
    }

    line.innerHTML = `<span class="debug-log-timestamp">[${timestamp}]</span> <span class="${className}">${icon} ${message}</span>`;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

function clearDebugLogs() {
    document.getElementById('debugOutput').innerHTML = '';
    debugLog('Debug console cleared', 'info');
}

function copyDebugLogs() {
    const output = document.getElementById('debugOutput');
    const text = output.innerText;

    if (!text || text.includes('No logs yet')) {
        showNotification('No logs to copy', true);
        return;
    }

    navigator.clipboard.writeText(text).then(() => {
        showNotification('Logs copied to clipboard!');
        debugLog('Logs copied to clipboard', 'success');
    }).catch(err => {
        showNotification('Failed to copy: ' + err, true);
    });
}

async function runQuickTest() {
    debugLog('========================================', 'info');
    debugLog('QUICK DIAGNOSTIC TEST STARTED', 'info');
    debugLog('========================================', 'info');

    try {
        debugLog('Running comprehensive diagnostics...', 'info');

        const response = await fetch('/api/debug/quick-test', {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            debugLog('Test completed successfully', 'success');
            debugLog('========================================', 'info');

            // Display results
            data.results.forEach(result => {
                const type = result.success ? 'success' : 'error';
                debugLog(`[${result.test}] ${result.message}`, type);

                if (result.details) {
                    debugLog(`  Details: ${result.details}`, 'info');
                }
            });

            debugLog('========================================', 'info');
            debugLog(`Summary: ${data.summary}`, data.all_passed ? 'success' : 'warning');

            if (!data.all_passed) {
                debugLog('⚠ Some tests failed. Copy logs and send to developer.', 'warning');
            }
        } else {
            debugLog(`Test failed: ${data.error || 'Unknown error'}`, 'error');
        }

    } catch (error) {
        debugLog(`Error running test: ${error.message}`, 'error');
        debugLog('Make sure the backend is running and accessible', 'warning');
    }
}

async function testNetwork() {
    debugLog('Testing network connectivity...', 'info');

    try {
        const response = await fetch('/api/debug/test-network', {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok && data.success) {
            debugLog(`✓ Network test passed`, 'success');
            debugLog(`  SGCarMart.com: HTTP ${data.status_code}`, 'success');
            debugLog(`  Response time: ${data.response_time}ms`, 'info');
        } else {
            debugLog(`✗ Network test failed: ${data.error}`, 'error');
            debugLog('  Possible causes:', 'warning');
            debugLog('    - Server firewall blocking outgoing HTTPS', 'warning');
            debugLog('    - DNS resolution issue', 'warning');
            debugLog('    - SGCarMart blocking server IP', 'warning');
        }
    } catch (error) {
        debugLog(`Error: ${error.message}`, 'error');
    }
}

async function testBrowser() {
    debugLog('Testing browser (Playwright/Chromium)...', 'info');
    debugLog('This may take 10-30 seconds...', 'info');

    try {
        const response = await fetch('/api/debug/test-browser', {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok && data.success) {
            debugLog(`✓ Browser test passed`, 'success');
            debugLog(`  Chromium launched: OK`, 'success');
            debugLog(`  Page loaded: ${data.page_title}`, 'success');
            debugLog(`  Listings found: ${data.listings_count}`, 'info');

            if (data.listings_count === 0) {
                debugLog('⚠ Warning: No listings found on search page', 'warning');
                debugLog('  Possible causes:', 'warning');
                debugLog('    - Page structure changed', 'warning');
                debugLog('    - JavaScript selectors need update', 'warning');
                debugLog('    - SGCarMart blocking detection', 'warning');
            }
        } else {
            debugLog(`✗ Browser test failed: ${data.error}`, 'error');
            debugLog('  Common fixes:', 'warning');
            debugLog('    - Run: playwright install chromium', 'info');
            debugLog('    - Run: playwright install-deps chromium', 'info');
            debugLog('    - Check Dockerfile has all dependencies', 'info');
        }
    } catch (error) {
        debugLog(`Error: ${error.message}`, 'error');
    }
}
