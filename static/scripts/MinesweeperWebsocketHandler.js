// Extract the game ID from the URL query parameters
const gameId = new URLSearchParams(window.location.search).get('gameId');

// Establish a WebSocket connection for the game
let ws = new WebSocket(`wss://ws.marko.sh/SecureMinesweeper?gameId=${gameId}`);

// Function to send tile click coordinates to the server
function RevealTiles(x, y) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        // Construct and send a message to reveal a tile
        // TODO: Maybe we don't need to send gameId here, will have to look into it
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

// Handle incoming messages from the WebSocket server
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Message from server:', data);
    
    // Process messages based on their action type
    // This is partly debug, not to stay forever only while in devel
    if (data.action === 'updateTiles') {
        updateTiles(data.tiles); // Update the grid with revealed tiles
    } else if (data.action === 'DisplayMessage') {
        alert(data.data); // Show a message to the user
    }
};

// Function to update the game grid with revealed tiles
function updateTiles(tiles) {
    tiles.forEach((tile) => {
        const { y, x, value } = tile;
        // Locate the corresponding tile element on the grid
        const tileElement = document.querySelector(`.grid > div[pos-x='${x}'][pos-y='${y}']`);
        if (tileElement) {
            tileElement.textContent = value === 0 ? '' : value; // Show number or blank for 0
            tileElement.classList.add('revealed'); // Mark the tile as revealed
        }
    });
}