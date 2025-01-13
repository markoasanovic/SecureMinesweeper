import json
import random
import boto3
from datetime import datetime, timezone
import os

# Load environment variables for DynamoDB table
WEBSOCKET_TABLE = os.environ["WEBSOCKET_TABLE"]

# Initialize DynamoDB resource and table
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(WEBSOCKET_TABLE)


def create_board(size, bomb_count):
    """
    Create a new Minesweeper game board.
    """
    if bomb_count >= size * size:
        raise ValueError("Too many bombs for board size")

    # Initialize the board with default values
    board = [
        [{"BombsNear": 0, "TileRevealed": False} for _ in range(size)]
        for _ in range(size)
    ]

    # Randomly select bomb positions
    all_positions = [(x, y) for x in range(size) for y in range(size)]
    random.shuffle(all_positions)
    bomb_positions = all_positions[:bomb_count]

    # Place bombs and calculate adjacent counts
    for x, y in bomb_positions:
        board[x][y]["BombsNear"] = 9
    for bomb_x, bomb_y in bomb_positions:
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = bomb_x + dx, bomb_y + dy
                if (
                    0 <= nx < size
                    and 0 <= ny < size
                    and board[nx][ny]["BombsNear"] != 9
                ):
                    board[nx][ny]["BombsNear"] += 1

    return board


def lambda_handler(event, context):
    """
    Creates a new Minesweeper game board and saves it to DynamoDB. Returning results to client at end with some basic information.
    """
    body = json.loads(event["body"])
    game_id = body.get("gameId")

    # Return an error if gameId is not provided
    if not game_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing gameId"})}

    # Check if the game already exists, if it does just return that game
    response = table.get_item(Key={"gameId": game_id})
    if "Item" in response:
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS, POST",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
            },
            "body": json.dumps({"message": "GameReady", "gameId": game_id}),
        }

    # Create a new game board
    size = 25
    bomb_count = 65
    board = create_board(size, bomb_count)

    # Prepare game data to store in DynamoDB
    game_data = {
        "gameId": game_id,
        "currentBoardState": board,
        "timeStarted": datetime.now(timezone.utc).isoformat(),
        "connections": [],
        "gameConcluded": False,
    }
    table.put_item(Item=game_data)

    # Return success response with game details
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS, POST",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
        },
        "body": json.dumps(
            {
                "message": "GameReady",
                "gameId": game_id,
                "boardSize": size,
                "bombCount": bomb_count,
            }
        ),
    }
