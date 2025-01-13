import json
import boto3
import os
from boto3.dynamodb.types import TypeSerializer

# Initialize DynamoDB client and serializer
dynamodb = boto3.client("dynamodb")
serializer = TypeSerializer()

# Load environment variables for DynamoDB table and API Gateway endpoint
WEBSOCKET_TABLE = os.environ["WEBSOCKET_TABLE"]
API_GATEWAY_ENDPOINT = os.environ["API_GATEWAY_ENDPOINT"]

# Initialize API Gateway Management API client
apigateway = boto3.client("apigatewaymanagementapi", endpoint_url=API_GATEWAY_ENDPOINT)


def send_message(connection_id, message):
    """
    Send a JSON message to a specific WebSocket connection.
    """
    try:
        apigateway.post_to_connection(
            ConnectionId=connection_id, Data=json.dumps(message)
        )
    except apigateway.exceptions.GoneException:
        print(f"Connection {connection_id} is gone. Cleanup will happen separately.")


# Convert DynamoDB board data to a Python-friendly format
def convert_from_dynamodb(board_data):
    """
    Convert DynamoDB format back to regular Python structure.
    """
    board = []
    for row in board_data:
        board_row = []
        for tile in row["L"]:
            board_row.append(
                {
                    "BombsNear": int(tile["M"]["BombsNear"]["N"]),
                    "TileRevealed": tile["M"]["TileRevealed"]["BOOL"],
                }
            )
        board.append(board_row)
    return board


# Reveal a tile and adjacent tiles using BFS
def reveal_tile(board, start_x, start_y, visited):
    """
    Reveal a tile and all adjacent 0-tiles, standard Minesweeper reveal using BFS.
    """
    # All early exit conditions
    if (
        start_x < 0  # Out-of-bounds on x-axis
        or start_y < 0  # Out-of-bounds on y-axis
        or start_x >= len(board)  # Exceeds board's width
        or start_y >= len(board[0])  # Exceeds board's height
        or (start_x, start_y) in visited  # Already visited tile
        or board[start_y][start_x]["TileRevealed"]  # Tile is already revealed
    ):
        return [], board

    # Initialize queue with the starting tile and a list to track revealed tiles
    queue = [(start_x, start_y)]
    revealed_tiles = []

    # Process tiles in the queue
    while queue:
        # Dequeue the first tile
        x, y = queue.pop(0)

        # Validate the current tile using same as early exit conditions
        if (
            x < 0
            or y < 0
            or x >= len(board)
            or y >= len(board[0])
            or (x, y) in visited
            or board[y][x]["TileRevealed"]
        ):
            continue

        # Reveal the current tile and add it to the visited set
        board[y][x]["TileRevealed"] = True
        bombs_near = board[y][x]["BombsNear"]

        # Add the revealed tile's data to the list of revealed tiles
        revealed_tiles.append({"x": x, "y": y, "value": bombs_near})
        visited.add((x, y))

        # If the current tile has 0 bombs nearby, enqueue its neighbors for further processing
        if bombs_near == 0:
            for dx, dy in [
                (-1, -1),
                (-1, 0),
                (-1, 1),
                (0, -1),
                (0, 1),
                (1, -1),
                (1, 0),
                (1, 1),
            ]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < len(board)  # check neighbor is within x-axis bounds
                    and 0
                    <= ny
                    < len(board[0])  # check neighbor is within y-axis bounds
                    and (nx, ny) not in visited  # check revisiting the same tile
                ):
                    queue.append((nx, ny))

    # Return the list of revealed tiles and the updated board
    return revealed_tiles, board


# Save the updated board state to DynamoDB
def save_board_state(game_id, board):
    """
    Write the updated board back to DynamoDB.
    """
    serialized_board = serializer.serialize(board)["L"]
    dynamodb.update_item(
        TableName=WEBSOCKET_TABLE,
        Key={"gameId": {"S": game_id}},
        UpdateExpression="SET currentBoardState = :board",
        ExpressionAttributeValues={":board": {"L": serialized_board}},
    )


def lambda_handler(event, context):
    """
    Handles tile reveal requests.
    """
    body = json.loads(event["body"])
    game_id = body["gameId"]
    coords = body["coordinates"]
    x, y = coords["x"], coords["y"]
    connection_id = event["requestContext"]["connectionId"]

    # Fetch the game board from DynamoDB
    resp = dynamodb.get_item(TableName=WEBSOCKET_TABLE, Key={"gameId": {"S": game_id}})

    # if the game does not exist or is concluded conditions checks
    if "Item" not in resp or "currentBoardState" not in resp["Item"]:
        print(f"Game {game_id} not found or has no board state.")
        return {"statusCode": 404, "body": json.dumps({"message": "Game not found"})}
    elif resp["Item"]["gameConcluded"]["BOOL"]:
        print(f"Game {game_id} has already concluded.")
        msg = {
            "action": "DisplayMessage",
            "data": f"Game {game_id} has already concluded.",
        }
        send_message(connection_id, msg)
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Game has already concluded"}),
        }

    # Otherwise convert table
    current_board_state = resp["Item"]["currentBoardState"]["L"]
    current_board_state = convert_from_dynamodb(current_board_state)

    # Reveal necessary tiles and save board again
    visited = set()
    revealed_tiles, updated_board = reveal_tile(current_board_state, x, y, visited)
    save_board_state(game_id, updated_board)

    # Inform all connections of the updated state of the game
    connections = [conn["S"] for conn in resp["Item"]["connections"]["L"]]
    msg = {"action": "updateTiles", "tiles": revealed_tiles}
    for conn_id in connections:
        send_message(conn_id, msg)

    # If the tile selected was a 9 (bomb) then game over message displayed and DynamoDB updated
    for revealed_tile in revealed_tiles:
        if revealed_tile["value"] == 9:
            dynamodb.update_item(
                TableName=WEBSOCKET_TABLE,
                Key={"gameId": {"S": game_id}},
                UpdateExpression="SET gameConcluded = :concluded",
                ExpressionAttributeValues={":concluded": {"BOOL": True}},
            )
            msg = {"action": "DisplayMessage", "data": f"Game {game_id} over!"}
            for conn_id in connections:
                send_message(conn_id, msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Game concluded"}),
            }

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Tiles revealed", "tiles": revealed_tiles}),
    }
