// telegram-bot/bot/static/mini_bingo.js
// Estif Bingo 24/7 - Mini Bingo Game Client
// Single-player practice mode with random cartela generation

// ==================== GLOBAL VARIABLES ====================
let authToken = null;
let userData = null;
let gameSession = null;
let currentGameState = {
    isPlaying: false,
    cartela: null,
    calledNumbers: [],
    gameCost: 5,
    winPercentage: 80,
    winAmount: 4,
    status: 'idle' // idle, active, won, gameover
};

let soundEnabled = true;
let currentSoundPack = 'pack1';
let audioContext = null;
let sounds = {};

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
    
    // Load user data
    await loadUserData();
    
    // Load game settings
    await loadGameSettings();
    
    // Load sound settings
    await loadSoundSettings();
    
    // Initialize audio
    initAudio();
    
    showLoading(false);
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

async function loadGameSettings() {
    try {
        const data = await apiCall('/mini-bingo/settings');
        if (data && data.success) {
            currentGameState.gameCost = data.data.game_cost;
            currentGameState.winPercentage = data.data.win_percentage;
            currentGameState.winAmount = data.data.win_amount;
            
            document.getElementById('gameCost').textContent = `${currentGameState.gameCost} ETB`;
            document.getElementById('winRate').textContent = `${currentGameState.winPercentage}%`;
            document.getElementById('winAmount').textContent = `${currentGameState.winAmount} ETB`;
        }
    } catch (error) {
        console.error('Error loading game settings:', error);
    }
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

// ==================== GAME FUNCTIONS ====================

async function startGame() {
    if (currentGameState.isPlaying) {
        showNotification('Game already in progress', 'warning');
        return;
    }
    
    // Check balance
    if (userData && userData.balance < currentGameState.gameCost) {
        showBalanceModal(currentGameState.gameCost);
        return;
    }
    
    showLoading(true);
    
    try {
        const data = await apiCall('/mini-bingo/start', { method: 'POST' });
        
        if (data && data.success) {
            gameSession = data.data;
            currentGameState.isPlaying = true;
            currentGameState.cartela = data.data.cartela;
            currentGameState.calledNumbers = [];
            currentGameState.status = 'active';
            
            // Update UI
            updateBalanceUI(userData.balance - currentGameState.gameCost);
            renderCartela(data.data.cartela);
            
            // Show game elements
            document.getElementById('calledNumbersSection').style.display = 'block';
            document.getElementById('cartelaContainer').style.display = 'block';
            document.getElementById('startBtn').style.display = 'none';
            document.getElementById('drawBtn').style.display = 'inline-block';
            document.getElementById('endBtn').style.display = 'inline-block';
            
            // Update called numbers display
            updateCalledNumbers([]);
            
            showNotification(`Game started! Cost: ${currentGameState.gameCost} ETB`, 'success');
            playSound('click');
        } else if (data && data.error === 'insufficient_balance') {
            showBalanceModal(currentGameState.gameCost);
        } else {
            showNotification(data?.error || 'Failed to start game', 'error');
        }
    } catch (error) {
        console.error('Error starting game:', error);
        showNotification('Failed to start game', 'error');
    }
    
    showLoading(false);
}

async function drawNumber() {
    if (!currentGameState.isPlaying || currentGameState.status !== 'active') {
        showNotification('Game is not active', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const data = await apiCall('/mini-bingo/draw', {
            method: 'POST',
            body: JSON.stringify({ session_id: gameSession.session_id })
        });
        
        if (data && data.success) {
            const number = data.data.number;
            const calledNumbers = data.data.called_numbers;
            const markedCells = data.data.marked_cells;
            const gameStatus = data.data.game_status;
            
            // Update called numbers
            currentGameState.calledNumbers = calledNumbers;
            updateCalledNumbers(calledNumbers);
            
            // Highlight the drawn number
            highlightDrawnNumber(number);
            
            // Update marked cells on cartela
            updateMarkedCells(markedCells);
            
            // Play sound
            playSound('draw');
            
            // Check if game is won
            if (gameStatus === 'won') {
                await handleWin(data.data.win_amount, data.data.win_pattern);
            }
        } else if (data && data.game_ended) {
            await handleGameOver();
        } else {
            showNotification(data?.error || 'Failed to draw number', 'error');
        }
    } catch (error) {
        console.error('Error drawing number:', error);
        showNotification('Failed to draw number', 'error');
    }
    
    showLoading(false);
}

async function endGame() {
    if (!currentGameState.isPlaying) {
        showNotification('No active game', 'warning');
        return;
    }
    
    if (!confirm('Are you sure you want to end this game? No refund will be given.')) {
        return;
    }
    
    showLoading(true);
    
    try {
        const data = await apiCall('/mini-bingo/end', {
            method: 'POST',
            body: JSON.stringify({ session_id: gameSession.session_id })
        });
        
        if (data && data.success) {
            resetGameUI();
            showNotification('Game ended', 'info');
            playSound('click');
        }
    } catch (error) {
        console.error('Error ending game:', error);
        showNotification('Failed to end game', 'error');
    }
    
    showLoading(false);
}

async function handleWin(winAmount, winPattern) {
    currentGameState.status = 'won';
    
    // Update balance
    if (userData) {
        userData.balance += winAmount;
        updateBalanceUI(userData.balance);
    }
    
    // Show winner modal
    showWinnerModal(winAmount, winPattern, currentGameState.cartela);
    
    // Play win sound
    playSound('win');
    
    // Reset game UI after modal is closed
    setTimeout(() => {
        resetGameUI();
    }, 500);
}

async function handleGameOver() {
    currentGameState.status = 'gameover';
    
    // Show game over modal
    showGameoverModal();
    
    // Reset game UI after modal is closed
}

function resetGameUI() {
    currentGameState.isPlaying = false;
    currentGameState.cartela = null;
    currentGameState.calledNumbers = [];
    currentGameState.status = 'idle';
    gameSession = null;
    
    // Hide game elements
    document.getElementById('calledNumbersSection').style.display = 'none';
    document.getElementById('cartelaContainer').style.display = 'none';
    document.getElementById('startBtn').style.display = 'inline-block';
    document.getElementById('drawBtn').style.display = 'none';
    document.getElementById('endBtn').style.display = 'none';
    document.getElementById('playAgainBtn').style.display = 'none';
    
    // Clear grids
    document.getElementById('calledNumbersGrid').innerHTML = '';
    document.getElementById('cartelaGrid').innerHTML = '';
}

function resetAndPlay() {
    closeWinnerModal();
    closeGameoverModal();
    startGame();
}

// ==================== UI RENDERING ====================

function renderCartela(grid) {
    const container = document.getElementById('cartelaGrid');
    if (!container) return;
    
    let html = '';
    for (let row = 0; row < 5; row++) {
        for (let col = 0; col < 5; col++) {
            const value = grid[col][row];
            let cellClass = 'cartela-cell';
            
            if (value === 0) {
                cellClass += ' free';
            }
            
            html += `<div class="${cellClass}" data-col="${col}" data-row="${row}" data-value="${value}">${value === 0 ? '⭐' : value}</div>`;
        }
    }
    
    container.innerHTML = html;
}

function updateMarkedCells(markedCells) {
    const container = document.getElementById('cartelaGrid');
    if (!container) return;
    
    markedCells.forEach(cell => {
        const index = (cell.row * 5) + cell.col;
        const cellElement = container.children[index];
        if (cellElement && !cellElement.classList.contains('marked')) {
            cellElement.classList.add('marked');
            if (cell.is_free) {
                cellElement.classList.add('free');
            }
            
            // Add animation
            cellElement.style.animation = 'markPulse 0.3s';
            setTimeout(() => {
                cellElement.style.animation = '';
            }, 300);
        }
    });
    
    // Update marked count
    const markedCount = document.querySelectorAll('#cartelaGrid .cartela-cell.marked').length;
    document.getElementById('markedCount').textContent = `Marked: ${markedCount}/24`;
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

function highlightDrawnNumber(number) {
    // Flash the number on the cartela if present
    const cells = document.querySelectorAll(`#cartelaGrid .cartela-cell[data-value="${number}"]`);
    cells.forEach(cell => {
        cell.style.animation = 'markPulse 0.3s';
        setTimeout(() => {
            cell.style.animation = '';
        }, 300);
    });
}

function updateBalanceUI(balance) {
    const balanceElement = document.getElementById('balance');
    if (balanceElement) {
        balanceElement.textContent = `${balance.toFixed(2)} ETB`;
    }
    
    // Update userData
    if (userData) {
        userData.balance = balance;
    }
}

// ==================== MODALS ====================

function showWinnerModal(winAmount, winPattern, cartela) {
    const modal = document.getElementById('winnerModal');
    const winnerAmount = document.getElementById('winnerAmount');
    const winnerPattern = document.getElementById('winnerPattern');
    const winnerCartela = document.getElementById('winnerCartela');
    
    winnerAmount.textContent = `${winAmount} ETB`;
    winnerPattern.textContent = getPatternName(winPattern);
    
    // Render winning cartela
    let gridHtml = '<div class="cartela-grid" style="max-width: 300px; margin: 0 auto;">';
    for (let row = 0; row < 5; row++) {
        for (let col = 0; col < 5; col++) {
            const value = cartela[col][row];
            const isWinning = isWinningCell(winPattern, col, row);
            const cellClass = `cartela-cell ${isWinning ? 'winning' : ''} ${value === 0 ? 'free' : ''}`;
            gridHtml += `<div class="${cellClass}">${value === 0 ? '⭐' : value}</div>`;
        }
    }
    gridHtml += '</div>';
    winnerCartela.innerHTML = gridHtml;
    
    modal.classList.add('active');
}

function isWinningCell(pattern, col, row) {
    // Simple pattern detection for display
    if (pattern === 'horizontal' && row === 2) return true;
    if (pattern === 'vertical' && col === 2) return true;
    if (pattern === 'diagonal_main' && col === row) return true;
    if (pattern === 'diagonal_anti' && col + row === 4) return true;
    return false;
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

function closeWinnerModal() {
    const modal = document.getElementById('winnerModal');
    modal.classList.remove('active');
    resetGameUI();
}

function showGameoverModal() {
    const modal = document.getElementById('gameoverModal');
    modal.classList.add('active');
}

function closeGameoverModal() {
    const modal = document.getElementById('gameoverModal');
    modal.classList.remove('active');
    resetGameUI();
}

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

function chargeBalance() {
    closeBalanceModal();
    // Close the game and open deposit in Telegram
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.close();
    }
    // Redirect to bot deposit
    window.location.href = 'tg://resolve?domain=YourBot&start=deposit';
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
    const savedPack = localStorage.getItem('miniSoundPack');
    if (savedPack) {
        currentSoundPack = savedPack;
        document.getElementById('soundPack').value = savedPack;
    }
    
    const savedEnabled = localStorage.getItem('miniSoundEnabled');
    if (savedEnabled !== null) {
        soundEnabled = savedEnabled === 'true';
        updateSoundToggleUI();
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
    localStorage.setItem('miniSoundPack', currentSoundPack);
    
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
    localStorage.setItem('miniSoundEnabled', soundEnabled);
    updateSoundToggleUI();
    
    if (soundEnabled) {
        playSound('click');
    }
}

function updateSoundToggleUI() {
    const toggleBtn = document.querySelector('.sound-toggle');
    if (toggleBtn) {
        toggleBtn.textContent = soundEnabled ? '🔊' : '🔇';
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
        padding: 10px 20px;
        background: ${type === 'success' ? 'rgba(0, 255, 136, 0.9)' : type === 'error' ? 'rgba(255, 68, 68, 0.9)' : type === 'warning' ? 'rgba(255, 215, 0, 0.9)' : 'rgba(0, 243, 255, 0.9)'};
        color: #0a0a1a;
        border-radius: 30px;
        font-weight: bold;
        z-index: 10000;
        animation: slideUp 0.3s ease;
        box-shadow: 0 0 20px rgba(0,0,0,0.3);
        font-size: 14px;
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
    if (!document.hidden && audioContext && audioContext.state === 'suspended') {
        audioContext.resume();
    }
});