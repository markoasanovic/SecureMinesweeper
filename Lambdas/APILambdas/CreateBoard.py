import json
import random
import boto3
from datetime import datetime, timezone
import os

# Load environment variables for DynamoDB table
WEBSOCKET_TABLE = os.environ["WEBSOCKET_TABLE"]

CORS_HEADERS = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS, POST",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
            }

# Initialize DynamoDB resource and table
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(WEBSOCKET_TABLE)

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
            "headers": CORS_HEADERS,
            "body": json.dumps({"message": "GameReady", "gameId": game_id}),
        }

    # Create a new game board
    size = 25
    bomb_count = 65
    all_positions = [(x, y) for x in range(size) for y in range(size)]
    random.shuffle(all_positions)
    bomb_positions = all_positions[:bomb_count]
    
    board_values = [[0 for _ in range(size)] for _ in range(size)]

    for x, y in bomb_positions:
        board_values[x][y] = 9

    for bomb_x, bomb_y in bomb_positions:
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = bomb_x + dx, bomb_y + dy
                if 0 <= nx < size and 0 <= ny < size and board_values[nx][ny] != 9:
                    board_values[nx][ny] += 1

    game_data = {
        "gameId": game_id,
        "timeStarted": datetime.now(timezone.utc).isoformat(),
        "connections": [],
        "gameConcluded": False,
        "boardSize": size,
        "bombCount": bomb_count,
        "remainingTiles": size * size - bomb_count,
        "boardValues": board_values,
        "revealedTiles": [[False for _ in range(size)] for _ in range(size)],
        "flagPositions": [[False for _ in range(size)] for _ in range(size)],
    }

    table.put_item(Item=game_data)

    # get and deserialize the item from the table
    response = table.get_item(Key={"gameId": game_id})
    item = response["Item"]
    print("deserizalized:", item)

    # Return success response with game details
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps(
            {
                "message": "GameReady",
                "gameId": game_id,
                "boardSize": size,
                "bombCount": bomb_count,
            }
        ),
    }