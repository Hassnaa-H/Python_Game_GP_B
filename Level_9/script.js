const codeInput = document.getElementById('codeInput');
const runButton = document.getElementById('runButton');
const statusMessage = document.getElementById('statusMessage');
const player = document.querySelector('.player');

const START_POS = { left: 70, top: 15 };
const MOVE_STEP_H = 135;
const MOVE_STEP_V = 65;
let currentPosition = { ...START_POS };
const resultOverlay = document.getElementById('resultOverlay');
const nextLevelButton = document.getElementById('nextLevelButton');
const tryAgainButton = document.getElementById('tryAgainButton');
const counter = document.getElementById('diamondCounter');
let collected = 0;

const itemPositions = [
    { top: 330, left: 225 },
    { top: 330, left: 358 },
    { top: 145, left: 630 },
    { top: 338, left: 770 },
    { top: 515, left: 491 }
];
const items = document.querySelectorAll('.item');

function getCurrentLevel() {
    const pathParts = window.location.pathname.split('/').filter(p => p);
    const level = pathParts.find(p => p.startsWith('Level_'));
    return level || 'Level_9';
}

function getNextLevelUrl() {
    const currentLevel = getCurrentLevel();
    const match = currentLevel.match(/^Level_(\d+)$/);
    if (!match) {
        return '../Level_9/index.html';
    }

    const currentIndex = parseInt(match[1], 10);
    const nextIndex = currentIndex + 1;
    return `../Level_${nextIndex}/index.html`;
}

function showSuccessOverlay() {
    statusMessage.textContent = '';
    resultOverlay.classList.remove('hidden');
}

function hideSuccessOverlay() {
    resultOverlay.classList.add('hidden');
}

function setPlayerPosition(position) {
    currentPosition = { ...position };
    player.style.left = `${position.left}px`;
    player.style.top = `${position.top}px`;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function animateMoves(moves) {
    await sleep(800);
    for (const command of moves) {
        if (command === 'right') currentPosition.left += MOVE_STEP_H;
        if (command === 'left') currentPosition.left -= MOVE_STEP_H;
        if (command === 'up') currentPosition.top -= MOVE_STEP_V;
        if (command === 'down') currentPosition.top += MOVE_STEP_V;

        player.style.left = `${currentPosition.left}px`;
        player.style.top = `${currentPosition.top}px`;

        // Check for diamond collection
        for(let i = 0; i < items.length; i++){
            if(items[i].style.display !== 'none' && Math.abs(currentPosition.left - itemPositions[i].left) < 80 && Math.abs(currentPosition.top - itemPositions[i].top) < 80){
                items[i].style.display = 'none';
                collected++;
                counter.textContent = `Scoure: ${collected}`;
            }
        }

        await sleep(800);
    }
}

async function runCode() {
    const code = codeInput.value.trim();
    if (!code) {
        statusMessage.textContent = 'Please enter your code before pressing Run.';
        return;
    }

    runButton.disabled = true;
    statusMessage.textContent = 'Validating code...';
    setPlayerPosition(START_POS);
    
    // Reset diamonds and counter
    collected = 0;
    counter.textContent = 'Scoure: 0';
    items.forEach(item => item.style.display = 'block');
    console.log('Game reset: diamonds restored, counter set to 0');

    try {
        const result = window.GameValidator ? await window.GameValidator.validate(code, getCurrentLevel()) : { success: false, moves: [], message: 'Code validation engine failed to load.' };
        
        if (!result.moves) {
            statusMessage.textContent = `❌ ${result.message || 'Invalid code or incorrect sequence.'}`;
            return;
        }

        if (result.moves.length > 0) {
            statusMessage.textContent = `Executing ${result.moves.length} move(s)...`;
            await animateMoves(result.moves);
        }

        if (result.success) {
            showSuccessOverlay();
        } else {
            statusMessage.textContent = `${result.message}`;
        }
    } catch (error) {
        statusMessage.textContent = `Validation error: ${error.message}`;
    } finally {
        runButton.disabled = false;
    }
}

runButton.addEventListener('click', runCode);

if (nextLevelButton) {
    nextLevelButton.addEventListener('click', () => {
        window.location.href = getNextLevelUrl();
    });
}

if (tryAgainButton) {
    tryAgainButton.addEventListener('click', () => {
        hideSuccessOverlay();
        window.location.reload();
    });
}

setPlayerPosition(START_POS);
