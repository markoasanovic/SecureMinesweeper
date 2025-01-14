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

def reveal_surrounding_tiles(selected_x, selected_y, board_values, revealed_tiles, flag_positions):
    """
    Reveal all tiles around a given tile.
    """
    queue = [(selected_x, selected_y)]
    newly_revealed_tiles = []

    while queue:
        x, y = queue.pop(0)
        newly_revealed_tiles.append((x, y))
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                new_x, new_y = x + dx, y + dy
                # if tile is out of range skip
                if not (0 <= new_x < len(board_values[0])) or not (0 <= new_y < len(board_values)):
                    continue
                # if tile is already revealed skip
                if revealed_tiles[new_y][new_x] or (new_x, new_y) in newly_revealed_tiles:
                    continue
                # if tile is flagged skip
                if flag_positions[new_y][new_x]:
                    continue
                # if tile is a bomb skip
                if board_values[new_y][new_x] == 9:
                    continue
                # if tile is between 1 and 8 (inclusive) reveal it
                if 0 < board_values[new_y][new_x] < 9:
                    newly_revealed_tiles.append((new_x, new_y))
                    continue
                # in all other cases, get neighbor.
                newly_revealed_tiles.append((new_x, new_y))
                queue.append((new_x, new_y))
    return newly_revealed_tiles

def lambda_handler(event, context):
    """
    Handles tile reveal requests.
    """
    body = json.loads(event["body"])
    game_id = body["gameId"]
    coords = body["coordinates"]
    selected_x, selected_y = coords["x"], coords["y"]

    connection_id = event["requestContext"]["connectionId"]

    # Fetch the game board from DynamoDB
    resp = dynamodb.get_item(TableName=WEBSOCKET_TABLE, Key={"gameId": {"S": game_id}})
    if "Item" not in resp:
        print(f"Game {game_id} not found or has no board state.")
        return {"statusCode": 404, "body": json.dumps({"message": "Game not found"})}
    elif resp['Item']["gameConcluded"]["BOOL"]:
        msg = {
            "action": "DisplayMessage",
            "data": f"Game '{game_id}' has already concluded.",
        }
        send_message(connection_id, msg)
        return {"statusCode": 400, "body": json.dumps({"message": "Game concluded"})}

    itm = resp["Item"]
    revealed_tiles = [
        [val['BOOL'] for val in row["L"]]
        for row in itm["revealedTiles"]["L"]
    ]
    flag_positions = [
        [val['BOOL'] for val in row["L"]]
        for row in itm["flagPositions"]["L"]
    ]
    board_values = [
        [int(val['N']) for val in row["L"]] 
        for row in itm["boardValues"]["L"]
    ]
    board_size = int(itm["boardSize"]["N"])
    connections = [conn["S"] for conn in itm["connections"]["L"]]

    # Validate the selected tile
    if selected_x < 0 or selected_x >= board_size or selected_y < 0 or selected_y >= board_size:
        msg = {"action": "DisplayMessage", "data": "Invalid tile selected"}
        send_message(connection_id, msg)
        return {"statusCode": 400, "body": json.dumps({"message": "Invalid tile selected"})}

    if revealed_tiles[selected_y][selected_x]:
        msg = {"action": "DisplayMessage", "data": "Tile already revealed"}
        send_message(connection_id, msg)
        return {"statusCode": 400, "body": json.dumps({"message": "Tile already revealed"})}

    if flag_positions[selected_y][selected_x]:
        msg = {"action": "DisplayMessage", "data": "Tile flagged, unflag tile to reveal it"}
        send_message(connection_id, msg)
        return {"statusCode": 400, "body": json.dumps({"message": "Tile flagged"})}

    newly_revealed = []

    # Handle bombs
    if board_values[selected_y][selected_x] == 9:
        newly_revealed = [
            (x, y) for y in range(board_size) for x in range(board_size)
            if not revealed_tiles[y][x]
        ]
        dynamodb.update_item(
            TableName=WEBSOCKET_TABLE,
            Key={"gameId": {"S": game_id}},
            UpdateExpression="SET gameConcluded = :concluded",
            ExpressionAttributeValues={
                ":concluded": {"BOOL": True},
            },
        )
        # TODO: Cleanup/move to bottom with others, have single point of notification
        notification = {
            "action": "UpdateTiles",
            "tiles": [
                {"x": x, "y": y, "value": board_values[y][x]} for x, y in newly_revealed
            ]
        }
        for conn_id in connections:
            send_message(conn_id, notification)

        msg = {"action": "DisplayMessage", "data": f"Game '{game_id}' over!"}
        send_message(connection_id, msg)
        return {"statusCode": 200, "body": json.dumps({"message": "User selected bomb. Game over."})}

    # Handle number tiles or empty tiles
    if 0 < board_values[selected_y][selected_x] < 9:
        newly_revealed.append((selected_x, selected_y))
    else:
        newly_revealed = reveal_surrounding_tiles(
            selected_x, selected_y, board_values, revealed_tiles, flag_positions
        )

    # Notify all connected clients
    notification = {
        "action": "UpdateTiles",
        "tiles": [
            {"x": x, "y": y, "value": board_values[y][x]} for x, y in newly_revealed
        ]
    }
    for conn_id in connections:
        send_message(conn_id, notification)

    # TODO: Make this only update the required tiles.
    # Update revealed tiles in the database
    for x, y in newly_revealed:
        revealed_tiles[y][x] = True

    # Batch update to DynamoDB
    dynamodb.update_item(
        TableName=WEBSOCKET_TABLE,
        Key={"gameId": {"S": game_id}},
        UpdateExpression="SET revealedTiles = :revealed",
        ExpressionAttributeValues={":revealed": serializer.serialize(revealed_tiles)},
    )


    return {"statusCode": 200, "body": json.dumps({"message": "Completed successfully"})}