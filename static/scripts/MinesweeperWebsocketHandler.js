// Extract the game ID from the URL query parameters
const gameId = new URLSearchParams(window.location.search).get('gameId');

// Establish a WebSocket connection for the game
let ws = new WebSocket(`wss://ws.marko.sh/SecureMinesweeper?gameId=${gameId}`);

// Function to send tile click coordinates to the server
function RevealTiles(x, y) {
    const tileElement = document.querySelector(`.grid > div[pos-x='${x}'][pos-y='${y}']`);
    if (tileElement && tileElement.classList.contains('revealed')) {
        console.error('Tile is already revealed. Cannot reveal again.');
        return;
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
        const message = {
            action: 'RevealTile',
            coordinates: { x: x, y: y },
            gameId: gameId,
        };
        ws.send(JSON.stringify(message));
        console.log('Message sent:', message);
    } else {
        console.error('WebSocket is not open. Cannot send message.');
    }
}

function FlagTile(x, y, event) {
    event.preventDefault();
    event.stopPropagation();
    const tileElement = document.querySelector(`.grid > div[pos-x='${x}'][pos-y='${y}']`);
    if (tileElement && tileElement.classList.contains('revealed')) {
        console.error('Tile is already revealed. Cannot flag.');
        return;
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
        const message = {
            action: 'ToggleFlagOnTile',
            coordinates: { x: x, y: y },
            gameId: gameId,
        };
        ws.send(JSON.stringify(message));
        console.log('Flag message sent:', message);
    } else {
        console.error('WebSocket is not open. Cannot send flag message.');
    }
}

// Handle incoming messages from the WebSocket server
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Message from server:', data);
    
    // Process messages based on their action type
    if (data.action === 'UpdateTiles') {
        updateTiles(data.tiles); // Update the grid with revealed tiles
    } else if (data.action === 'DisplayMessage') {
        alert(data.data); // Show a message to the user
    } else if (data.action == 'SetFlagState') {
        const { x, y } = data.coordinates;
        const tileElement = document.querySelector(`.grid > div[pos-x='${x}'][pos-y='${y}']`);
        switch (data.flagged) {
            case true:
                tileElement.textContent = '🚩';
                tileElement.classList.add('flagged');
                break;
            case false:
                tileElement.textContent = '';
                tileElement.classList.remove('flagged');
                break;
        }
    }
};

// Function to update the game grid with revealed tiles
function updateTiles(tiles) {
    tiles.forEach((tile) => {
        const { x, y, value } = tile;
        const tileElement = document.querySelector(`.grid > div[pos-x='${x}'][pos-y='${y}']`);
        if (tileElement) {
            switch (value) {
                case 0: 
                    tileElement.textContent = ''; // Show number or blank for 0
                    break;
                case 9:
                    tileElement.textContent = '💣'; // Show bomb for 9
                    break;
                default:
                    tileElement.textContent = value; // Show value
            }
            tileElement.classList.add('revealed'); // Mark the tile as revealed
        }
    });
}