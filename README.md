# SecureMinesweeper

**SecureMinesweeper** Is a way for friends to play Minesweeper together without worrying about cheating. The game stores all tile information on the backend and only reveals it once an action is made. This change is reflected in real-time to all viewers and players!

## Features
- **Server-Side Game Generation & Processing**: The grid is generated server-side with tiles only being revealed after being selected, ensuring the client has no prior knowledge of tile positions.
- **WebSocket Integration**: Real-time updates for tile reveals and game events enabling multiple people to play at the same time.
- **AWS Architecture**: Built on AWS using Lambda, API Gateway, CloudFront, DynamoDB, S3.

## Architecture
The application is built using the following AWS services:

1. **Lambda Functions**:
   - `GenerateGrid`: Generates the Minesweeper grid.
   - `RevealTile`: WebSocket endpoint to reveal a tile, updates the game stored in DynamoDB, and updates all connected clients.
   - `$connect` and `$disconnect`: Manage WebSocket connections.
   - `LandingPage`: Will either serve the "Create or Join Game" screen or will populate the board with the latest game state if a ?gameId=[id] is passed.
 
2. **S3 Buckets**:
   - `Static Assets`: Stores static assets accessible via CloudFront.
   - `Template Files`: Stores template files to be used via the Lambda functions.

3. **CloudFront**:
   - Used for content deliver of static assets and for security to encrypt traffic.

## Endpoints

- **REST API**: `https://api.marko.sh/SecureMinesweeper/GenerateGrid` - REST endpoint for generating the game grid.
- **WebSocket API**: `wss://ws.marko.sh/SecureMinesweeper/` - WebSocket endpoint for all real-time interactions.
  - Sub-paths: `/RevealTile`, `$connect`, `$disconnect`
- **Static Content**: `https://www.marko.sh/static/*` - All static assets can be found here.
- **Landing Page**: `https://marko.sh/SecureMinesweeper/play` - Hosts the landing page and game interface.

## How to Deploy
### TODO
I would like to make this project deployable via CloudFormation to make deployment easier as there is many permissions required to ensure that each Lambda can access it's required resources with as little privilege as required. 

## How to Play
1. Visit the landing page: `https://marko.sh/SecureMinesweeper/play`.
2. Enter a Game ID. If this ID already exists you will be added to that game, otherwise a new game will be created.
3. Interact with the game board by clicking tiles.
   - Revealed tiles update in real-time via WebSocket events.
   - If a bomb tile is selected then the game state will be set to complete, and no more interaction will be possible.

## Future goals
1. Create CloudFormation code to make deployment/portability easier.
2. Resolve race conditions where multiple users making quick actions can cause their boards to be out of sync.
3. Rework board structure again to improve overall performance.

## Contact
For questions or support, reach out to Marko Asanovic at:
- Email: [contact@marko.sh](mailto:contact@marko.sh)
- GitHub: [markoasanovic](https://github.com/markoasanovic)