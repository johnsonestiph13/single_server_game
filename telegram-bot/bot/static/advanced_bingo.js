// telegram-bot/bot/static/advanced_bingo.js
// Estif Bingo 24/7 - Advanced Bingo Game Client
// Handles WebSocket communication, cartela selection, game logic, and UI updates

// ==================== GLOBAL VARIABLES ====================
let socket = null;
let authToken = null;
let userData = null;
let currentGameState = {
    status: 'idle',
    phase: 'selection',
    timer: 0,
    calledNumbers: [],
    selectedCartelas: [],
    userCartelas: [],
    myCartelas: [],
    maxCartelas: 4,
    cartelaPrice: 10,
    winPercentage: 80
};

let selectedCartelaIds = new Set();
let soundEnabled = true;
let currentSoundPack = 'pack1';
let audioContext = null;
let sounds = {};
let isWaitingForNextRound = false;
let nextRoundTimer = null;

// API Base URL
const API_BASE = window.location.origin + '/api';

// ==================== INITIALIZATION ====================

async function init() {
    showLoading(true);
    
    // Get token from URL
    const urlParams = new URLSearchParams(window.location.search);
    authToken = urlParams.get('token');
    
    if (!authToken) {
        showError('No authentication token found. Please restart the game from Telegram.');
        return;
    }
    
    // Connect WebSocket
    connectWebSocket();
    
    // Load user data
    await loadUserData();
    
    // Load cartelas
    await loadCartelas();
    
    // Load sound settings
    loadSoundSettings();
    
    // Initialize audio
    initAudio();
    
    showLoading(false);
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/socket.io/?token=${authToken}&EIO=4&transport=websocket`;
    
    socket = io({
        path: '/socket.io',
        query: { token: authToken },
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 10,
        reconnectionDelay: 1000
    });
    
    socket.on('connect', () => {
        console.log('WebSocket connected');
        socket.emit('authenticate', { token: authToken });
    });
    
    socket.on('authenticated', (data) => {
        console.log('Authenticated:', data);
        userData = data;
        updateBalanceUI(data.balance);
    });
    
    socket.on('auth_error', (error) => {
        console.error('Auth error:', error);
        showError('Authentication failed. Please restart the game.');
    });
    
    socket.on('game_state', (state) => {
        updateGameState(state);
    });
    
    socket.on('timer_update', (data) => {
        updateTimer(data.remaining, data.is_blinking);
    });
    
    socket.on('number_called', (data) => {
        handleNumberCalled(data);
    });
    
    socket.on('cartela_update', (data) => {
        handleCartelaUpdate(data);
    });
    
    socket.on('game_ended', (data) => {
        handleGameEnded(data);
    });
    
    socket.on('select_success', (data) => {
        handleSelectSuccess(data);
    });
    
    socket.on('select_error', (error) => {
        handleSelectError(error);
    });
    
    socket.on('unselect_success', (data) => {
        handleUnselectSuccess(data);
    });
    
    socket.on('error', (error) => {
        console.error('Socket error:', error);
        showNotification(error.error || 'An error occurred', 'error');
    });
    
    socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        showNotification('Connection lost. Reconnecting...', 'warning');
    });
    
    socket.on('reconnect', () => {
        console.log('WebSocket reconnected');
        showNotification('Reconnected!', 'success');
        socket.emit('authenticate', { token: authToken });
    });
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
        showError('Session expired. Please restart the game.');
        return null;
    }
    
    return response.json();
}

async function loadUserData() {
    try {
        const data = await apiCall('/game/user/balance');
        if (data && data.success) {
            userData = data.data;
            updateBalanceUI(data.data.balance);
        }
    } catch (error) {
        console.error('Error loading user data:', error);
    }
}

async function loadCartelas(page = 1) {
    try {
        const data = await apiCall(`/game/cartelas?page=${page}&limit=100`);
        if (data && data.success) {
            renderCartelas(data.data.cartelas);
            currentGameState.maxCartelas = data.data.max_cartelas;
            currentGameState.cartelaPrice = data.data.cartela_price;
            updateSelectionStatus();
        }
    } catch (error) {
        console.error('Error loading cartelas:', error);
    }
}

// ==================== UI RENDERING ====================

function renderCartelas(cartelas) {
    const container = document.getElementById('cartelasGrid');
    if (!container) return;
    
    if (!cartelas || cartelas.length === 0) {
        container.innerHTML = '<div class="text-center" style="padding: 40px;">No cartelas available</div>';
        return;
    }
    
    container.innerHTML = cartelas.map(cartela => {
        let statusClass = '';
        let statusIcon = '⚪';
        let disabled = false;
        
        if (cartela.is_mine) {
            statusClass = 'selected';
            statusIcon = '🟢';
        } else if (cartela.is_taken) {
            statusClass = 'taken';
            statusIcon = '🔴';
            disabled = true;
        } else {
            statusClass = 'available';
            statusIcon = '⚪';
        }
        
        return `
            <div class="cartela-card ${statusClass} ${disabled ? 'disabled' : ''}" 
                 data-id="${cartela.id}"
                 onclick="${!disabled && currentGameState.phase === 'selection' ? `toggleCartelaSelection(${cartela.id})` : ''}">
                <div class="cartela-id">#${cartela.id}</div>
                <div class="cartela-status ${statusClass}">${statusIcon}</div>
            </div>
        `;
    }).join('');
}

function renderMyCartelas() {
    const container = document.getElementById('myCartelasGrid');
    if (!container) return;
    
    if (!currentGameState.myCartelas || currentGameState.myCartelas.length === 0) {
        container.innerHTML = '<div class="text-center" style="padding: 20px;">No cartelas selected</div>';
        return;
    }
    
    container.innerHTML = currentGameState.myCartelas.map(cartela => `
        <div class="cartela-detail">
            <div class="cartela-header">
                <span class="cartela-number">Cartela #${cartela.id}</span>
                <span class="winning-pattern" id="winPattern_${cartela.id}"></span>
            </div>
            <div class="cartela-grid" id="cartelaGrid_${cartela.id}">
                ${renderCartelaGrid(cartela.grid, currentGameState.calledNumbers)}
            </div>
        </div>
    `).join('');
}

function renderCartelaGrid(grid, calledNumbers) {
    const calledSet = new Set(calledNumbers);
    let html = '';
    
    for (let row = 0; row < 5; row++) {
        for (let col = 0; col < 5; col++) {
            const value = grid[col][row];
            let cellClass = 'cartela-cell';
            
            if (value === 0) {
                cellClass += ' free';
            } else if (calledSet.has(value)) {
                cellClass += ' marked';
            }
            
            html += `<div class="${cellClass}">${value === 0 ? '⭐' : value}</div>`;
        }
    }
    
    return html;
}

function updateGameState(state) {
    currentGameState = { ...currentGameState, ...state };
    
    // Update phase badge
    const phaseBadge = document.getElementById('phaseBadge');
    if (phaseBadge) {
        if (state.status === 'selection') {
            phaseBadge.className = 'phase-badge selection';
            phaseBadge.innerHTML = '🟢 SELECTION PHASE';
            document.getElementById('myCartelasContainer').style.display = 'none';
        } else if (state.status === 'drawing') {
            phaseBadge.className = 'phase-badge drawing';
            phaseBadge.innerHTML = '🟡 DRAWING PHASE';
            if (currentGameState.myCartelas.length > 0) {
                document.getElementById('myCartelasContainer').style.display = 'block';
                renderMyCartelas();
            }
        } else if (state.status === 'ended') {
            phaseBadge.className = 'phase-badge ended';
            phaseBadge.innerHTML = '🔴 ROUND ENDED';
        }
    }
    
    // Update called numbers
    if (state.called_numbers) {
        updateCalledNumbers(state.called_numbers);
    }
    
    // Update selected count
    if (state.selected_count !== undefined) {
        document.getElementById('selectedCount').innerHTML = `📊 Selected: ${state.selected_count}/${state.total_cartelas || 1000}`;
    }
    
    // Update selection status
    updateSelectionStatus();
}

function updateTimer(remaining, isBlinking) {
    const timerElement = document.getElementById('timer');
    if (!timerElement) return;
    
    const minutes = Math.floor(remaining / 60);
    const seconds = remaining % 60;
    const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    
    timerElement.textContent = timeString;
    
    if (remaining <= 10) {
        timerElement.className = 'timer danger';
        if (isBlinking) {
            timerElement.classList.add('blink');
        }
    } else if (remaining <= 20) {
        timerElement.className = 'timer warning';
    } else {
        timerElement.className = 'timer normal';
    }
}

function updateCalledNumbers(numbers) {
    const container = document.getElementById('calledNumbersGrid');
    const countElement = document.getElementById('calledCount');
    
    if (!container) return;
    
    if (countElement) {
        countElement.textContent = `${numbers.length}/75`;
    }
    
    const lastNumber = numbers.length > 0 ? numbers[numbers.length - 1] : null;
    
    container.innerHTML = numbers.map(num => {
        const isLatest = num === lastNumber;
        return `<div class="called-number ${isLatest ? 'latest' : ''}">${num}</div>`;
    }).join('');
    
    // Auto-scroll to show latest numbers
    container.scrollTop = container.scrollHeight;
}

function updateBalanceUI(balance) {
    const balanceElement = document.getElementById('balance');
    if (balanceElement) {
        balanceElement.textContent = `${balance.toFixed(2)} ETB`;
    }
}

function updateSelectionStatus() {
    const statusElement = document.getElementById('selectionStatus');
    if (statusElement) {
        statusElement.textContent = `Selected: ${selectedCartelaIds.size}/${currentGameState.maxCartelas}`;
    }
    
    // Update confirm button visibility
    const confirmBtn = document.getElementById('confirmBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const selectBtn = document.querySelector('.action-buttons .btn-primary');
    
    if (selectedCartelaIds.size > 0 && currentGameState.phase === 'selection') {
        if (confirmBtn) confirmBtn.style.display = 'inline-block';
        if (cancelBtn) cancelBtn.style.display = 'inline-block';
        if (selectBtn) selectBtn.style.display = 'none';
    } else {
        if (confirmBtn) confirmBtn.style.display = 'none';
        if (cancelBtn) cancelBtn.style.display = 'none';
        if (selectBtn) selectBtn.style.display = 'inline-block';
    }
}

// ==================== CARTELA SELECTION ====================

function toggleCartelaSelection(cartelaId) {
    if (currentGameState.phase !== 'selection') {
        showNotification('Cannot select cartelas now', 'warning');
        return;
    }
    
    if (selectedCartelaIds.has(cartelaId)) {
        selectedCartelaIds.delete(cartelaId);
        updateCartelaUI(cartelaId, false);
    } else {
        if (selectedCartelaIds.size >= currentGameState.maxCartelas) {
            showNotification(`Maximum ${currentGameState.maxCartelas} cartelas allowed`, 'warning');
            return;
        }
        selectedCartelaIds.add(cartelaId);
        updateCartelaUI(cartelaId, true);
    }
    
    updateSelectionStatus();
}

function updateCartelaUI(cartelaId, isSelected) {
    const cartelaCard = document.querySelector(`.cartela-card[data-id="${cartelaId}"]`);
    if (!cartelaCard) return;
    
    if (isSelected) {
        cartelaCard.classList.add('selected');
        cartelaCard.classList.remove('available');
        const statusDiv = cartelaCard.querySelector('.cartela-status');
        if (statusDiv) {
            statusDiv.textContent = '🟢';
            statusDiv.className = 'cartela-status selected';
        }
    } else {
        cartelaCard.classList.remove('selected');
        cartelaCard.classList.add('available');
        const statusDiv = cartelaCard.querySelector('.cartela-status');
        if (statusDiv) {
            statusDiv.textContent = '⚪';
            statusDiv.className = 'cartela-status available';
        }
    }
}

function showCartelaSelection() {
    // Scroll to cartelas section
    document.querySelector('.cartelas-container').scrollIntoView({ behavior: 'smooth' });
}

async function confirmSelection() {
    if (selectedCartelaIds.size === 0) {
        showNotification('Please select at least one cartela', 'warning');
        return;
    }
    
    const cartelaIds = Array.from(selectedCartelaIds);
    
    showLoading(true);
    
    socket.emit('select_cartelas', { cartela_ids: cartelaIds });
}

function cancelSelection() {
    selectedCartelaIds.clear();
    updateSelectionStatus();
    
    // Reset all cartela UI
    document.querySelectorAll('.cartela-card.selected').forEach(card => {
        const cartelaId = parseInt(card.dataset.id);
        updateCartelaUI(cartelaId, false);
    });
    
    showNotification('Selection cancelled', 'info');
}

function handleSelectSuccess(data) {
    showLoading(false);
    
    selectedCartelaIds.clear();
    updateSelectionStatus();
    
    // Update balance
    if (data.new_balance !== undefined) {
        updateBalanceUI(data.new_balance);
    }
    
    // Update UI for selected cartelas
    if (data.selected) {
        data.selected.forEach(cartelaId => {
            updateCartelaUI(cartelaId, true);
        });
    }
    
    showNotification(`Selected ${data.total_selected} cartelas for ${data.total_cost} ETB`, 'success');
}

function handleSelectError(error) {
    showLoading(false);
    
    if (error.code === 'insufficient_balance') {
        showBalanceModal(error.required);
    } else {
        showNotification(error.error || 'Failed to select cartelas', 'error');
    }
}

function handleUnselectSuccess(data) {
    if (data.unselected) {
        data.unselected.forEach(cartelaId => {
            updateCartelaUI(cartelaId, false);
        });
    }
    
    if (data.new_balance !== undefined) {
        updateBalanceUI(data.new_balance);
    }
    
    showNotification(`Unselected ${data.unselected.length} cartelas`, 'success');
}

// ==================== GAME PLAY ====================

function handleNumberCalled(data) {
    // Play sound
    playSound('draw');
    
    // Update called numbers
    if (data.called_numbers) {
        updateCalledNumbers(data.called_numbers);
    }
    
    // Update marked cells on my cartelas
    if (data.marked_cells) {
        updateMarkedCells(data.marked_cells);
    }
}

function updateMarkedCells(markedCells) {
    for (const [cartelaId, cells] of Object.entries(markedCells)) {
        const gridElement = document.getElementById(`cartelaGrid_${cartelaId}`);
        if (!gridElement) continue;
        
        cells.forEach(cell => {
            const index = (cell.row * 5) + cell.col;
            const cellElement = gridElement.children[index];
            if (cellElement && !cellElement.classList.contains('marked')) {
                cellElement.classList.add('marked');
                if (cell.value === 0) {
                    cellElement.classList.add('free');
                }
            }
        });
    }
}

function handleCartelaUpdate(data) {
    if (data.action === 'select') {
        data.cartela_ids.forEach(cartelaId => {
            const card = document.querySelector(`.cartela-card[data-id="${cartelaId}"]`);
            if (card && !card.classList.contains('selected')) {
                card.classList.add('taken');
                card.classList.remove('available');
                const statusDiv = card.querySelector('.cartela-status');
                if (statusDiv) {
                    statusDiv.textContent = '🔴';
                    statusDiv.className = 'cartela-status taken';
                }
            }
        });
    } else if (data.action === 'unselect') {
        data.cartela_ids.forEach(cartelaId => {
            const card = document.querySelector(`.cartela-card[data-id="${cartelaId}"]`);
            if (card && card.classList.contains('taken')) {
                card.classList.remove('taken');
                card.classList.add('available');
                const statusDiv = card.querySelector('.cartela-status');
                if (statusDiv) {
                    statusDiv.textContent = '⚪';
                    statusDiv.className = 'cartela-status available';
                }
            }
        });
    }
}

function handleGameEnded(data) {
    playSound('win');
    
    // Show winner modal
    showWinnerModal(data.winners, data.prize_pool);
    
    // Start next round timer
    startNextRoundTimer(data.next_round_delay);
}

function showWinnerModal(winners, prizePool) {
    const modal = document.getElementById('winnerModal');
    const winnerAmount = document.getElementById('winnerAmount');
    const winnerPattern = document.getElementById('winnerPattern');
    const winnerCartela = document.getElementById('winnerCartela');
    
    // Check if current user is a winner
    const myWin = winners.find(w => w.user_id === userData?.user_id);
    
    if (myWin) {
        winnerAmount.textContent = `${myWin.win_amount} ETB`;
        winnerPattern.textContent = getPatternName(myWin.pattern);
        winnerCartela.innerHTML = `<div class="cartela-grid" id="winnerCartelaGrid"></div>`;
        renderWinnerCartela(myWin.grid, myWin.cells);
    } else {
        winnerAmount.textContent = `${prizePool} ETB (Pool)`;
        winnerPattern.textContent = `${winners.length} winner(s)`;
        winnerCartela.innerHTML = `<div class="text-center">Congratulations to the winners!</div>`;
    }
    
    modal.classList.add('active');
}

function renderWinnerCartela(grid, winningCells) {
    const container = document.getElementById('winnerCartelaGrid');
    if (!container) return;
    
    const winningSet = new Set(winningCells.map(c => `${c.col},${c.row}`));
    
    for (let row = 0; row < 5; row++) {
        for (let col = 0; col < 5; col++) {
            const value = grid[col][row];
            const isWinning = winningSet.has(`${col},${row}`);
            const cellClass = `cartela-cell ${isWinning ? 'winning' : ''} ${value === 0 ? 'free' : ''}`;
            container.innerHTML += `<div class="${cellClass}">${value === 0 ? '⭐' : value}</div>`;
        }
    }
}

function getPatternName(pattern) {
    const patterns = {
        'horizontal': 'Horizontal Line',
        'vertical': 'Vertical Line',
        'diagonal_main': 'Main Diagonal',
        'diagonal_anti': 'Anti Diagonal'
    };
    return patterns[pattern] || 'BINGO!';
}

function startNextRoundTimer(seconds) {
    isWaitingForNextRound = true;
    let remaining = seconds;
    
    const timerElement = document.getElementById('nextRoundTimer');
    if (!timerElement) return;
    
    if (nextRoundTimer) clearInterval(nextRoundTimer);
    
    nextRoundTimer = setInterval(() => {
        remaining--;
        timerElement.textContent = `Next round starts in ${remaining}s`;
        
        if (remaining <= 0) {
            clearInterval(nextRoundTimer);
            isWaitingForNextRound = false;
            closeWinnerModal();
        }
    }, 1000);
}

function closeWinnerModal() {
    const modal = document.getElementById('winnerModal');
    modal.classList.remove('active');
}

// ==================== MODALS ====================

function showBalanceModal(required) {
    const modal = document.getElementById('balanceModal');
    const requiredElement = document.getElementById('requiredBalance');
    if (requiredElement) {
        requiredElement.textContent = `${required} ETB`;
    }
    modal.classList.add('active');
}

function closeBalanceModal() {
    const modal = document.getElementById('balanceModal');
    modal.classList.remove('active');
}

function watchOnly() {
    closeBalanceModal();
    showNotification('You are now in watch-only mode', 'info');
}

function chargeBalance() {
    closeBalanceModal();
    // Close the game and open deposit in Telegram
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.close();
    }
    // Redirect to bot deposit
    window.location.href = 'tg://resolve?domain=YourBot&start=deposit';
}

function showGameProgressModal() {
    const modal = document.getElementById('gameProgressModal');
    modal.classList.add('active');
}

function closeGameProgressModal() {
    const modal = document.getElementById('gameProgressModal');
    modal.classList.remove('active');
}

function watchGame() {
    closeGameProgressModal();
    // Just stay in the game and watch
    showNotification('Watching current game...', 'info');
}

function exitGame() {
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.close();
    } else {
        window.close();
    }
}

// ==================== SOUND SYSTEM ====================

function initAudio() {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
}

async function loadSound(soundName) {
    const soundUrl = `/static/sounds/${currentSoundPack}/${soundName}.mp3`;
    
    try {
        const response = await fetch(soundUrl);
        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        sounds[soundName] = audioBuffer;
    } catch (error) {
        console.error(`Failed to load sound ${soundName}:`, error);
    }
}

async function playSound(soundName) {
    if (!soundEnabled || !sounds[soundName]) return;
    
    if (audioContext.state === 'suspended') {
        await audioContext.resume();
    }
    
    const source = audioContext.createBufferSource();
    source.buffer = sounds[soundName];
    source.connect(audioContext.destination);
    source.start();
}

async function loadSoundSettings() {
    const savedPack = localStorage.getItem('soundPack');
    if (savedPack) {
        currentSoundPack = savedPack;
        document.getElementById('soundPack').value = savedPack;
    }
    
    const savedEnabled = localStorage.getItem('soundEnabled');
    if (savedEnabled !== null) {
        soundEnabled = savedEnabled === 'true';
    }
    
    // Load all sounds
    const soundNames = ['draw', 'win', 'bingo', 'click'];
    for (const name of soundNames) {
        await loadSound(name);
    }
}

async function changeSoundPack() {
    const select = document.getElementById('soundPack');
    currentSoundPack = select.value;
    localStorage.setItem('soundPack', currentSoundPack);
    
    // Reload sounds
    const soundNames = ['draw', 'win', 'bingo', 'click'];
    for (const name of soundNames) {
        await loadSound(name);
    }
    
    playSound('click');
    showNotification(`Sound pack changed to ${currentSoundPack}`, 'success');
}

function toggleSound() {
    soundEnabled = !soundEnabled;
    localStorage.setItem('soundEnabled', soundEnabled);
    
    const toggleBtn = document.querySelector('.sound-toggle');
    if (toggleBtn) {
        toggleBtn.textContent = soundEnabled ? '🔊' : '🔇';
    }
    
    if (soundEnabled) {
        playSound('click');
    }
}

// ==================== UTILITIES ====================

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        padding: 12px 24px;
        background: ${type === 'success' ? 'rgba(0, 255, 136, 0.9)' : type === 'error' ? 'rgba(255, 68, 68, 0.9)' : type === 'warning' ? 'rgba(255, 215, 0, 0.9)' : 'rgba(0, 243, 255, 0.9)'};
        color: #0a0a1a;
        border-radius: 30px;
        font-weight: bold;
        z-index: 10000;
        animation: slideUp 0.3s ease;
        box-shadow: 0 0 20px rgba(0,0,0,0.3);
        white-space: nowrap;
        max-width: 90%;
        white-space: normal;
        text-align: center;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideDown 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function showError(message) {
    showNotification(message, 'error');
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from { transform: translateX(-50%) translateY(100%); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
    @keyframes slideDown {
        from { transform: translateX(-50%) translateY(0); opacity: 1; }
        to { transform: translateX(-50%) translateY(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// ==================== EVENT LISTENERS ====================

document.addEventListener('DOMContentLoaded', () => {
    init();
});

// Handle visibility change (page visible/hidden)
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Page hidden, pause audio if needed
    } else {
        // Page visible, resume audio context
        if (audioContext && audioContext.state === 'suspended') {
            audioContext.resume();
        }
    }
});