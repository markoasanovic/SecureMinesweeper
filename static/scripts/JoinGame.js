// Get references to input, button, and message elements
const gameIdInput = document.getElementById('gameId');
const gameButton = document.getElementById('gameButton');
const message = document.getElementById('message');

// Function to validate the game ID input
function validateInput() {
    const inputLength = gameIdInput.value.length; // Get the length of the entered game ID

    if (inputLength >= 5) {
        // Enable the button and hide the warning message if input is valid
        gameButton.disabled = false;
        message.classList.remove('visible');
    } else {
        // Disable the button and show the warning message if input is invalid
        gameButton.disabled = true;
        message.classList.add('visible');
    }
}

async function createOrJoinGame() {
    const gameId = gameIdInput.value; // Retrieve the entered game ID

    // Make a POST request to the API to create a new game board with the specified Game ID
    const response = await fetch('https://api.marko.sh/SecureMinesweeper/CreateBoard', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ gameId }),
    });

    if (!response.ok) {
        const error = await response.json();
        alert(`Failed to create game: ${error.message}`); // Display error message to the user
        return;
    }

    // Redirect to the game page on successful response
    window.location.href = `https://marko.sh/SecureMinesweeper/play?gameId=${encodeURIComponent(gameId)}`;
}
