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
