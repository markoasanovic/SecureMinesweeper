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

def lambda_handler(event, context):
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
    board_size = int(itm["boardSize"]["N"])
    connections = [conn["S"] for conn in itm["connections"]["L"]]
    
    # check if value provided in in acceptable range
    if 0 > selected_x >= board_size or 0 > selected_y >= board_size:
        msg = {
            "action": "DisplayMessage",
            "data": f"Invalid coordinates ({selected_x}, {selected_y}).",
        }
        send_message(connection_id, msg)
        return {"statusCode": 400, "body": json.dumps({"message": "Invalid coordinates"})}

    # check if tile is already revealed
    if revealed_tiles[selected_y][selected_x]:
        msg = {
            "action": "DisplayMessage",
            "data": f"Tile ({selected_x}, {selected_y}) is already revealed.",
        }
        send_message(connection_id, msg)
        return {"statusCode": 400, "body": json.dumps({"message": "Tile already revealed"})}

    # all checks complete, invert flag and send to all users
    new_flag = not flag_positions[selected_y][selected_x]
    msg = {
        "action": "SetFlagState",
        "coordinates": {"x": selected_x, "y": selected_y}, 
        "flagged": new_flag
    }
    for connection in connections:
        send_message(connection, msg)
    
    # Update single position in flagPositions dynamoDB using the x and y coordinates
    dynamodb.update_item(
        TableName=WEBSOCKET_TABLE,
        Key={"gameId": {"S": game_id}},
        UpdateExpression=f"SET flagPositions[{selected_y}][{selected_x}] = :new_flag",
        ExpressionAttributeValues={":new_flag": {"BOOL": new_flag}}
    )

    return {"statusCode": 200, "body": json.dumps({"message": "Flag toggled successfully"})}