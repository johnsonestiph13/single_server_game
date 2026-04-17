// telegram-bot/bot/static/admin.js
// Estif Bingo 24/7 - Admin Dashboard JavaScript
// Handles all admin panel functionality, API calls, and UI updates

// ==================== GLOBAL VARIABLES ====================
let authToken = localStorage.getItem('adminToken');
let currentUser = null;
let currentPage = {
    users: 1,
    deposits: 1,
    withdrawals: 1
};
let revenueChart = null;

// API Base URL
const API_BASE = window.location.origin + '/api';

// ==================== AUTHENTICATION ====================

async function login(email, password) {
    try {
        const response = await fetch(`${API_BASE}/admin/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('adminToken', authToken);
            localStorage.setItem('adminUser', JSON.stringify(currentUser));
            showDashboard();
            return true;
        } else {
            showNotification(data.error || 'Login failed', 'error');
            return false;
        }
    } catch (error) {
        console.error('Login error:', error);
        showNotification('Network error. Please try again.', 'error');
        return false;
    }
}

function logout() {
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminUser');
    authToken = null;
    currentUser = null;
    showLoginForm();
    showNotification('Logged out successfully', 'success');
}

function checkAuth() {
    if (!authToken) {
        showLoginForm();
        return false;
    }
    return true;
}

// ==================== UI RENDERING ====================

function showLoginForm() {
    document.body.innerHTML = `
        <div class="container" style="max-width: 400px; margin-top: 100px;">
            <div class="card" style="text-align: center;">
                <div class="card-title">🔐 Admin Login</div>
                <div class="form-group">
                    <input type="email" id="loginEmail" class="form-control" placeholder="Email">
                </div>
                <div class="form-group">
                    <input type="password" id="loginPassword" class="form-control" placeholder="Password">
                </div>
                <button class="btn btn-primary" onclick="login(document.getElementById('loginEmail').value, document.getElementById('loginPassword').value)">Login</button>
            </div>
        </div>
    `;
}

function showDashboard() {
    // Check if we need to reload the page structure
    if (!document.querySelector('.stats-grid')) {
        location.reload();
        return;
    }
    
    // Update admin info
    if (currentUser) {
        document.getElementById('adminName').textContent = currentUser.name || 'Admin';
        document.getElementById('adminEmail').textContent = currentUser.email;
    }
    
    // Load all data
    loadDashboardStats();
    loadUsers();
    loadDeposits();
    loadWithdrawals();
    loadGameStatus();
    loadSettings();
    
    // Start auto-refresh
    startAutoRefresh();
}

// ==================== API CALLS ====================

async function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        }
    };
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...defaultOptions,
        ...options,
        headers: { ...defaultOptions.headers, ...options.headers }
    });
    
    if (response.status === 401) {
        logout();
        throw new Error('Session expired');
    }
    
    return response.json();
}

// ==================== DASHBOARD ====================

async function loadDashboardStats() {
    try {
        const data = await apiCall('/admin/statistics');
        
        if (data.success) {
            document.getElementById('totalUsers').textContent = data.data.users.total.toLocaleString();
            document.getElementById('activeUsers').textContent = data.data.users.active_24h.toLocaleString();
            document.getElementById('totalVolume').textContent = `${data.data.financial.total_deposits.toLocaleString()} ETB`;
            document.getElementById('totalWins').textContent = `${data.data.financial.total_wins.toLocaleString()} ETB`;
            document.getElementById('houseEdge').textContent = `${((data.data.financial.house_edge / data.data.games.total_bets) * 100 || 0).toFixed(1)}%`;
            document.getElementById('winPercent').textContent = `${data.data.games.win_percentage || 80}%`;
            
            // Update recent activity
            updateRecentActivity(data.data);
            
            // Update game stats
            updateGameStats(data.data);
            
            // Update chart
            updateRevenueChart(data.data);
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

function updateRecentActivity(data) {
    const container = document.getElementById('recentActivity');
    if (!container) return;
    
    // Mock recent activity - in production, fetch from API
    container.innerHTML = `
        <div style="padding: 10px 0; border-bottom: 1px solid rgba(0,243,255,0.1);">
            <span class="badge badge-success">New User</span>
            <span style="float: right;">2 minutes ago</span>
            <div>New user registered: user_12345</div>
        </div>
        <div style="padding: 10px 0; border-bottom: 1px solid rgba(0,243,255,0.1);">
            <span class="badge badge-info">Deposit</span>
            <span style="float: right;">15 minutes ago</span>
            <div>Deposit of 500 ETB approved</div>
        </div>
        <div style="padding: 10px 0;">
            <span class="badge badge-warning">Win</span>
            <span style="float: right;">1 hour ago</span>
            <div>User won 400 ETB in round #1234</div>
        </div>
    `;
}

function updateGameStats(data) {
    const container = document.getElementById('gameStats');
    if (!container) return;
    
    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span>Total Rounds:</span>
            <span class="text-info">${data.games.total_rounds || 0}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span>Completed Rounds:</span>
            <span class="text-success">${data.games.completed_rounds || 0}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span>Total Cartelas Sold:</span>
            <span class="text-warning">${(data.games.total_cartelas_sold || 0).toLocaleString()}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span>Total Bets:</span>
            <span class="text-info">${(data.games.total_bets || 0).toLocaleString()} ETB</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <span>Active Players:</span>
            <span class="text-success">${data.games.active_players || 0}</span>
        </div>
    `;
}

function updateRevenueChart(data) {
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Mock data - in production, fetch from API
    const chartData = {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
            label: 'Revenue (ETB)',
            data: [1250, 2300, 1800, 2900, 3450, 4100, 3800],
            borderColor: '#00f3ff',
            backgroundColor: 'rgba(0, 243, 255, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4
        }]
    };
    
    if (revenueChart) {
        revenueChart.destroy();
    }
    
    revenueChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    labels: { color: '#fff' }
                }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(0, 243, 255, 0.1)' },
                    ticks: { color: '#888' }
                },
                x: {
                    grid: { color: 'rgba(0, 243, 255, 0.1)' },
                    ticks: { color: '#888' }
                }
            }
        }
    });
}

// ==================== USERS MANAGEMENT ====================

async function loadUsers(page = 1) {
    currentPage.users = page;
    
    try {
        const searchTerm = document.getElementById('userSearch')?.value || '';
        const url = `/admin/users?page=${page}&limit=20${searchTerm ? `&search=${encodeURIComponent(searchTerm)}` : ''}`;
        const data = await apiCall(url);
        
        if (data.success) {
            renderUsersTable(data.data.users, data.data.pagination);
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

function renderUsersTable(users, pagination) {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No users found</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.telegram_id}</td>
            <td>${user.username || '-'}</td>
            <td>${user.first_name || ''} ${user.last_name || ''}</td>
            <td class="text-info">${user.balance || 0} ETB</td>
            <td>${user.total_games_played || 0}</td>
            <td>${user.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-danger">Inactive</span>'}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="viewUser(${user.telegram_id})">View</button>
                <button class="btn btn-sm btn-warning" onclick="adjustBalance(${user.telegram_id})">Balance</button>
            </td>
        </tr>
    `).join('');
    
    // Render pagination
    renderPagination('usersPagination', pagination, loadUsers);
}

function searchUsers() {
    loadUsers(1);
}

function viewUser(userId) {
    // Implement user detail view
    showNotification(`Viewing user ${userId}`, 'info');
}

function adjustBalance(userId) {
    const amount = prompt('Enter amount to add/deduct (use - for deduction):');
    if (amount) {
        adjustUserBalance(userId, parseFloat(amount));
    }
}

async function adjustUserBalance(userId, amount) {
    try {
        const operation = amount >= 0 ? 'add' : 'deduct';
        const data = await apiCall(`/admin/users/${userId}/balance`, {
            method: 'PUT',
            body: JSON.stringify({ amount: Math.abs(amount), operation })
        });
        
        if (data.success) {
            showNotification(`Balance updated: ${data.data.new_balance} ETB`, 'success');
            loadUsers(currentPage.users);
        } else {
            showNotification(data.error || 'Failed to update balance', 'error');
        }
    } catch (error) {
        console.error('Error adjusting balance:', error);
        showNotification('Error adjusting balance', 'error');
    }
}

// ==================== DEPOSITS MANAGEMENT ====================

async function loadDeposits() {
    try {
        const data = await apiCall('/admin/deposits?status=pending');
        
        if (data.success) {
            renderDepositsTable(data.data.deposits);
        }
    } catch (error) {
        console.error('Error loading deposits:', error);
    }
}

function renderDepositsTable(deposits) {
    const tbody = document.getElementById('depositsTableBody');
    if (!tbody) return;
    
    if (!deposits || deposits.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No pending deposits</td></tr>';
        return;
    }
    
    tbody.innerHTML = deposits.map(deposit => `
        <tr>
            <td>#${deposit.id}</td>
            <td>${deposit.first_name || deposit.telegram_id}</td>
            <td class="text-warning">${deposit.amount} ETB</td>
            <td>${deposit.method}</td>
            <td>${deposit.transaction_id || '-'}</td>
            <td>${new Date(deposit.created_at).toLocaleString()}</td>
            <td>
                <button class="btn btn-sm btn-success" onclick="approveDeposit(${deposit.id})">Approve</button>
                <button class="btn btn-sm btn-danger" onclick="rejectDeposit(${deposit.id})">Reject</button>
            </td>
        </tr>
    `).join('');
}

async function approveDeposit(depositId) {
    if (!confirm('Approve this deposit?')) return;
    
    try {
        const data = await apiCall(`/admin/deposits/${depositId}/approve`, { method: 'POST' });
        
        if (data.success) {
            showNotification('Deposit approved', 'success');
            loadDeposits();
            loadDashboardStats();
        } else {
            showNotification(data.error || 'Failed to approve deposit', 'error');
        }
    } catch (error) {
        console.error('Error approving deposit:', error);
        showNotification('Error approving deposit', 'error');
    }
}

async function rejectDeposit(depositId) {
    const reason = prompt('Enter rejection reason:');
    if (!reason) return;
    
    try {
        const data = await apiCall(`/admin/deposits/${depositId}/reject`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
        
        if (data.success) {
            showNotification('Deposit rejected', 'success');
            loadDeposits();
        } else {
            showNotification(data.error || 'Failed to reject deposit', 'error');
        }
    } catch (error) {
        console.error('Error rejecting deposit:', error);
        showNotification('Error rejecting deposit', 'error');
    }
}

// ==================== WITHDRAWALS MANAGEMENT ====================

async function loadWithdrawals() {
    try {
        const data = await apiCall('/admin/withdrawals?status=pending');
        
        if (data.success) {
            renderWithdrawalsTable(data.data.withdrawals);
        }
    } catch (error) {
        console.error('Error loading withdrawals:', error);
    }
}

function renderWithdrawalsTable(withdrawals) {
    const tbody = document.getElementById('withdrawalsTableBody');
    if (!tbody) return;
    
    if (!withdrawals || withdrawals.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No pending withdrawals</td></tr>';
        return;
    }
    
    tbody.innerHTML = withdrawals.map(withdrawal => `
        <tr>
            <td>#${withdrawal.id}</td>
            <td>${withdrawal.first_name || withdrawal.telegram_id}</td>
            <td class="text-warning">${withdrawal.amount} ETB</td>
            <td>${withdrawal.method}</td>
            <td>${withdrawal.details_encrypted ? '***' : '-'}</td>
            <td>${new Date(withdrawal.created_at).toLocaleString()}</td>
            <td>
                <button class="btn btn-sm btn-success" onclick="approveWithdrawal(${withdrawal.id})">Approve</button>
                <button class="btn btn-sm btn-danger" onclick="rejectWithdrawal(${withdrawal.id})">Reject</button>
            </td>
        </tr>
    `).join('');
}

async function approveWithdrawal(withdrawalId) {
    if (!confirm('Approve this withdrawal?')) return;
    
    try {
        const data = await apiCall(`/admin/withdrawals/${withdrawalId}/approve`, { method: 'POST' });
        
        if (data.success) {
            showNotification('Withdrawal approved', 'success');
            loadWithdrawals();
            loadDashboardStats();
        } else {
            showNotification(data.error || 'Failed to approve withdrawal', 'error');
        }
    } catch (error) {
        console.error('Error approving withdrawal:', error);
        showNotification('Error approving withdrawal', 'error');
    }
}

async function rejectWithdrawal(withdrawalId) {
    const reason = prompt('Enter rejection reason:');
    if (!reason) return;
    
    try {
        const data = await apiCall(`/admin/withdrawals/${withdrawalId}/reject`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
        
        if (data.success) {
            showNotification('Withdrawal rejected', 'success');
            loadWithdrawals();
        } else {
            showNotification(data.error || 'Failed to reject withdrawal', 'error');
        }
    } catch (error) {
        console.error('Error rejecting withdrawal:', error);
        showNotification('Error rejecting withdrawal', 'error');
    }
}

// ==================== GAME CONTROL ====================

async function loadGameStatus() {
    try {
        const data = await apiCall('/admin/game/settings');
        
        if (data.success) {
            document.getElementById('winPercentage').value = data.data.win_percentage;
            document.getElementById('soundPack').value = data.data.default_sound_pack;
            document.getElementById('maintenanceMode').value = data.data.maintenance_mode ? 'true' : 'false';
        }
        
        // Also load current game state
        const gameState = await apiCall('/game/state');
        if (gameState.success) {
            document.getElementById('gameStatusText').textContent = gameState.data.status;
            document.getElementById('currentRound').textContent = gameState.data.round_id || '-';
            document.getElementById('playersInGame').textContent = gameState.data.players_count || 0;
            document.getElementById('cartelasSelected').textContent = gameState.data.selected_count || 0;
            document.getElementById('calledNumbers').textContent = `${gameState.data.called_numbers?.length || 0}/75`;
        }
    } catch (error) {
        console.error('Error loading game status:', error);
    }
}

async function forceStartGame() {
    if (!confirm('Force start a new round?')) return;
    
    try {
        const data = await apiCall('/admin/game/force-start', { method: 'POST' });
        
        if (data.success) {
            showNotification('Game force started', 'success');
            loadGameStatus();
        } else {
            showNotification(data.error || 'Failed to start game', 'error');
        }
    } catch (error) {
        console.error('Error starting game:', error);
        showNotification('Error starting game', 'error');
    }
}

async function forceStopGame() {
    if (!confirm('Force stop current round?')) return;
    
    try {
        const data = await apiCall('/admin/game/force-stop', { method: 'POST' });
        
        if (data.success) {
            showNotification('Game force stopped', 'success');
            loadGameStatus();
        } else {
            showNotification(data.error || 'Failed to stop game', 'error');
        }
    } catch (error) {
        console.error('Error stopping game:', error);
        showNotification('Error stopping game', 'error');
    }
}

async function resetGame() {
    if (!confirm('WARNING: This will reset the entire game state. Continue?')) return;
    
    try {
        const data = await apiCall('/admin/game/reset', { method: 'POST' });
        
        if (data.success) {
            showNotification('Game reset successfully', 'success');
            loadGameStatus();
        } else {
            showNotification(data.error || 'Failed to reset game', 'error');
        }
    } catch (error) {
        console.error('Error resetting game:', error);
        showNotification('Error resetting game', 'error');
    }
}

async function updateWinPercentage() {
    const percentage = document.getElementById('winPercentage').value;
    
    try {
        const data = await apiCall('/admin/game/settings', {
            method: 'PUT',
            body: JSON.stringify({ win_percentage: parseInt(percentage) })
        });
        
        if (data.success) {
            showNotification(`Win percentage updated to ${percentage}%`, 'success');
            loadDashboardStats();
        } else {
            showNotification(data.error || 'Failed to update win percentage', 'error');
        }
    } catch (error) {
        console.error('Error updating win percentage:', error);
        showNotification('Error updating win percentage', 'error');
    }
}

async function updateSoundPack() {
    const soundPack = document.getElementById('soundPack').value;
    
    try {
        const data = await apiCall('/admin/game/settings', {
            method: 'PUT',
            body: JSON.stringify({ default_sound_pack: soundPack })
        });
        
        if (data.success) {
            showNotification(`Sound pack updated to ${soundPack}`, 'success');
        } else {
            showNotification(data.error || 'Failed to update sound pack', 'error');
        }
    } catch (error) {
        console.error('Error updating sound pack:', error);
        showNotification('Error updating sound pack', 'error');
    }
}

async function toggleMaintenanceMode() {
    const enabled = document.getElementById('maintenanceMode').value === 'true';
    
    try {
        const data = await apiCall('/admin/game/settings', {
            method: 'PUT',
            body: JSON.stringify({ maintenance_mode: enabled })
        });
        
        if (data.success) {
            showNotification(`Maintenance mode ${enabled ? 'enabled' : 'disabled'}`, 'success');
        } else {
            showNotification(data.error || 'Failed to toggle maintenance mode', 'error');
        }
    } catch (error) {
        console.error('Error toggling maintenance mode:', error);
        showNotification('Error toggling maintenance mode', 'error');
    }
}

// ==================== REPORTS ====================

async function generateReport(type) {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;
    
    if (!startDate || !endDate) {
        showNotification('Please select both start and end dates', 'error');
        return;
    }
    
    try {
        const data = await apiCall(`/admin/reports/${type}?start_date=${startDate}&end_date=${endDate}`);
        
        if (data.success) {
            displayReport(data.data, type);
        } else {
            showNotification(data.error || 'Failed to generate report', 'error');
        }
    } catch (error) {
        console.error('Error generating report:', error);
        showNotification('Error generating report', 'error');
    }
}

function displayReport(reportData, type) {
    const container = document.getElementById('reportResult');
    if (!container) return;
    
    const titles = {
        commission: '💰 Commission Report',
        wins: '🏆 Wins Report',
        total: '📊 Total Report'
    };
    
    let html = `
        <div style="margin-top: 20px;">
            <h3 style="color: #00f3ff;">${titles[type] || 'Report'}</h3>
            <div style="background: rgba(0,0,0,0.3); border-radius: 10px; padding: 15px; margin-top: 10px;">
                <pre style="color: #fff; font-family: monospace; white-space: pre-wrap;">${JSON.stringify(reportData, null, 2)}</pre>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

async function exportReport() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;
    
    if (!startDate || !endDate) {
        showNotification('Please select both start and end dates', 'error');
        return;
    }
    
    window.open(`${API_BASE}/admin/reports/export?start_date=${startDate}&end_date=${endDate}&token=${authToken}`, '_blank');
}

// ==================== SETTINGS ====================

async function loadSettings() {
    // Settings are loaded in loadGameStatus
}

async function changePassword() {
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (!newPassword || !confirmPassword) {
        showNotification('Please fill in both password fields', 'error');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showNotification('Passwords do not match', 'error');
        return;
    }
    
    try {
        const data = await apiCall('/admin/change-password', {
            method: 'POST',
            body: JSON.stringify({ password: newPassword })
        });
        
        if (data.success) {
            showNotification('Password changed successfully', 'success');
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
        } else {
            showNotification(data.error || 'Failed to change password', 'error');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        showNotification('Error changing password', 'error');
    }
}

async function sendBroadcast() {
    const message = document.getElementById('broadcastMessage').value;
    
    if (!message) {
        showNotification('Please enter a message to broadcast', 'error');
        return;
    }
    
    if (!confirm(`Send this message to ALL users?\n\n${message.substring(0, 100)}${message.length > 100 ? '...' : ''}`)) {
        return;
    }
    
    try {
        const data = await apiCall('/admin/broadcast', {
            method: 'POST',
            body: JSON.stringify({ message })
        });
        
        if (data.success) {
            showNotification(`Broadcast sent to ${data.data.recipient_count} users`, 'success');
            document.getElementById('broadcastMessage').value = '';
        } else {
            showNotification(data.error || 'Failed to send broadcast', 'error');
        }
    } catch (error) {
        console.error('Error sending broadcast:', error);
        showNotification('Error sending broadcast', 'error');
    }
}

// ==================== UTILITIES ====================

function renderPagination(containerId, pagination, callback) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (!pagination || pagination.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '';
    for (let i = 1; i <= Math.min(pagination.total_pages, 10); i++) {
        html += `<button class="page-btn ${i === pagination.page ? 'active' : ''}" onclick="callback(${i})">${i}</button>`;
    }
    container.innerHTML = html;
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? 'rgba(0, 255, 136, 0.9)' : type === 'error' ? 'rgba(255, 68, 68, 0.9)' : 'rgba(0, 243, 255, 0.9)'};
        color: #0a0a1a;
        border-radius: 10px;
        font-weight: bold;
        z-index: 10000;
        animation: slideIn 0.3s ease;
        box-shadow: 0 0 20px rgba(0,0,0,0.3);
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

let refreshInterval = null;

function startAutoRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(() => {
        if (document.querySelector('.tab-content.active')) {
            loadDashboardStats();
            loadGameStatus();
        }
    }, 30000);
}

// ==================== TAB HANDLING ====================

document.addEventListener('DOMContentLoaded', () => {
    // Check authentication
    const savedToken = localStorage.getItem('adminToken');
    const savedUser = localStorage.getItem('adminUser');
    
    if (savedToken && savedUser) {
        authToken = savedToken;
        currentUser = JSON.parse(savedUser);
        showDashboard();
    } else if (document.querySelector('.stats-grid')) {
        // Already on dashboard, just load data
        if (authToken) {
            showDashboard();
        }
    } else {
        showLoginForm();
    }
    
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(tabId).classList.add('active');
            
            // Load tab-specific data
            if (tabId === 'users') loadUsers();
            if (tabId === 'deposits') loadDeposits();
            if (tabId === 'withdrawals') loadWithdrawals();
            if (tabId === 'game') loadGameStatus();
        });
    });
});