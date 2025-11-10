// Global state
let currentDate = new Date();
let scheduleData = [];
let summaryData = null;

// Activity type icons
const TYPE_ICONS = {
    'Medication': '💊',
    'Fitness': '💪',
    'Food': '🥗',
    'Therapy': '🧘',
    'Consultation': '👨‍⚕️'
};

// Priority colors
const PRIORITY_COLORS = {
    1: '#ef4444',
    2: '#f59e0b',
    3: '#eab308',
    4: '#3b82f6',
    5: '#8b5cf6'
};

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await loadData();
        renderDashboard();
        renderCalendar();
        setupEventListeners();
        hideLoading();
    } catch (error) {
        console.error('Error initializing app:', error);
        alert('Failed to load schedule data. Please ensure the scheduler has been run.');
    }
});

// Load data from API
async function loadData() {
    const summaryResponse = await fetch('/api/summary');
    const summaryResult = await summaryResponse.json();

    if (!summaryResult.success) {
        throw new Error(summaryResult.error);
    }

    summaryData = summaryResult.data;

    const scheduleResponse = await fetch('/api/schedule');
    const scheduleResult = await scheduleResponse.json();

    if (!scheduleResult.success) {
        throw new Error(scheduleResult.error);
    }

    scheduleData = scheduleResult.data;
}

// Hide loading, show content
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('main-content').style.display = 'block';
}

// Render dashboard stats
function renderDashboard() {
    document.getElementById('success-rate').textContent =
        `${summaryData.overall_success_rate.toFixed(1)}%`;

    document.getElementById('scheduled-count').textContent =
        `${summaryData.total_scheduled} / ${summaryData.total_required}`;

    document.getElementById('cost').textContent =
        `$${summaryData.generation_cost.toFixed(4)}`;

    renderPriorityBreakdown();
    renderTypeBreakdown();
    renderFailures();
}

// Render priority breakdown
function renderPriorityBreakdown() {
    const container = document.getElementById('priority-breakdown');
    const byPriority = summaryData.by_priority;

    container.innerHTML = '';

    for (let i = 1; i <= 5; i++) {
        const key = `priority_${i}`;
        const data = byPriority[key];

        if (!data || data.required === 0) continue;

        const rate = data.success_rate;
        const status = rate >= 90 ? '✓' : rate >= 70 ? '⚠' : '✗';

        const item = document.createElement('div');
        item.className = 'priority-item';
        item.innerHTML = `
            <div class="priority-label">${status} Priority ${i}</div>
            <div class="priority-bar-container">
                <div class="priority-bar p${i}" style="width: ${rate}%">
                    ${rate.toFixed(1)}%
                </div>
            </div>
            <div class="priority-stats">
                ${data.scheduled} / ${data.required}
            </div>
        `;

        container.appendChild(item);
    }
}

// Render activity type breakdown
function renderTypeBreakdown() {
    const container = document.getElementById('type-breakdown');
    const byType = summaryData.by_type;

    container.innerHTML = '';

    Object.entries(byType).forEach(([type, data]) => {
        const icon = TYPE_ICONS[type] || '📋';
        const percentage = (data.scheduled / summaryData.total_scheduled * 100).toFixed(1);

        const item = document.createElement('div');
        item.className = 'type-item';
        item.innerHTML = `
            <div class="type-icon">${icon}</div>
            <div class="type-name">${type}</div>
            <div class="type-count">${data.scheduled}</div>
            <div class="type-percentage">${percentage}%</div>
        `;

        container.appendChild(item);
    });
}

// Render calendar
function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    document.getElementById('current-month').textContent =
        currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const container = document.getElementById('calendar');
    container.innerHTML = '';

    // Day headers
    const dayHeaders = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    dayHeaders.forEach(day => {
        const header = document.createElement('div');
        header.className = 'calendar-day-header';
        header.textContent = day;
        container.appendChild(header);
    });

    // Get first day of month and number of days
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Empty cells for offset
    for (let i = 0; i < firstDay; i++) {
        const empty = document.createElement('div');
        empty.className = 'calendar-day empty';
        container.appendChild(empty);
    }

    // Days with activity counts
    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        const dateStr = formatDate(date);
        const dayActivities = scheduleData.filter(s => s.date === dateStr);

        const dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        dayElement.dataset.date = dateStr;

        dayElement.innerHTML = `
            <div class="day-number">${day}</div>
            ${dayActivities.length > 0 ? `
                <div class="day-count">${dayActivities.length} activities</div>
                <div class="day-indicator"></div>
            ` : '<div class="day-count">No activities</div>'}
        `;

        dayElement.addEventListener('click', () => selectDate(dateStr));

        container.appendChild(dayElement);
    }
}

// Select date and show daily schedule
async function selectDate(dateStr) {
    // Update selected styling
    document.querySelectorAll('.calendar-day').forEach(el => {
        el.classList.remove('selected');
    });

    const selectedElement = document.querySelector(`[data-date="${dateStr}"]`);
    if (selectedElement) {
        selectedElement.classList.add('selected');
    }

    // Update header
    const date = new Date(dateStr + 'T00:00:00');
    document.getElementById('selected-date-header').textContent =
        `📋 Daily Schedule - ${date.toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            year: 'numeric'
        })}`;

    // Fetch and render daily schedule
    const response = await fetch(`/api/schedule/day/${dateStr}`);
    const result = await response.json();

    if (!result.success) {
        console.error('Error loading daily schedule:', result.error);
        return;
    }

    renderDailySchedule(result.data);
}

// Render daily schedule
function renderDailySchedule(activities) {
    const container = document.getElementById('daily-schedule');

    if (activities.length === 0) {
        container.innerHTML = '<p class="placeholder">No activities scheduled for this day</p>';
        return;
    }

    container.innerHTML = '';

    activities.forEach(activity => {
        const item = document.createElement('div');
        item.className = 'schedule-item';
        item.style.borderLeftColor = PRIORITY_COLORS[activity.priority] || '#6b7280';

        const icon = TYPE_ICONS[activity.activity_type] || '📋';

        item.innerHTML = `
            <div class="schedule-time">${formatTime(activity.start_time)} - ${formatEndTime(activity.start_time, activity.duration_minutes)}</div>
            <div class="schedule-name">${icon} ${activity.activity_name}</div>
            <div class="schedule-details">
                <span class="schedule-badge" style="background: ${PRIORITY_COLORS[activity.priority]}; color: white;">
                    P${activity.priority}
                </span>
                <span class="schedule-badge">${activity.activity_type}</span>
                <span class="schedule-badge">${activity.duration_minutes} min</span>
                ${activity.specialist_id ? '<span class="schedule-badge">👨‍⚕️ Specialist</span>' : ''}
                ${activity.equipment_ids && activity.equipment_ids.length > 0 ? '<span class="schedule-badge">🏋️ Equipment</span>' : ''}
            </div>
        `;

        container.appendChild(item);
    });
}

// Render failures
async function renderFailures() {
    const response = await fetch('/api/failures');
    const result = await response.json();

    if (!result.success) {
        console.error('Error loading failures:', result.error);
        return;
    }

    const container = document.getElementById('failures');
    const failures = result.data;

    if (failures.length === 0) {
        container.innerHTML = '<p class="placeholder">🎉 All activities successfully scheduled!</p>';
        return;
    }

    container.innerHTML = '';

    // Show only first 10 failures
    failures.slice(0, 10).forEach(failure => {
        const item = document.createElement('div');
        item.className = 'failure-item';
        item.innerHTML = `
            <div class="failure-name">P${failure.priority} - ${failure.name}</div>
            <div class="failure-reason">
                Required: ${failure.required_occurrences},
                Scheduled: ${failure.scheduled_occurrences},
                Missing: ${failure.missing_occurrences}
            </div>
        `;
        container.appendChild(item);
    });

    if (failures.length > 10) {
        const more = document.createElement('p');
        more.className = 'placeholder';
        more.textContent = `... and ${failures.length - 10} more`;
        container.appendChild(more);
    }
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('prev-month').addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });

    document.getElementById('next-month').addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });
}

// Utility functions
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatTime(timeStr) {
    const [hours, minutes] = timeStr.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
}

function formatEndTime(startTime, duration) {
    const [hours, minutes] = startTime.split(':').map(Number);
    const startMinutes = hours * 60 + minutes;
    const endMinutes = startMinutes + duration;
    const endHours = Math.floor(endMinutes / 60);
    const endMins = endMinutes % 60;
    const ampm = endHours >= 12 ? 'PM' : 'AM';
    const displayHour = endHours % 12 || 12;
    return `${displayHour}:${String(endMins).padStart(2, '0')} ${ampm}`;
}
