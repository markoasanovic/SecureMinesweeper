import os
import json
import boto3

# Load environment variables for DynamoDB table and API Gateway endpoint
DYNAMO_TABLE_NAME = os.environ["WEBSOCKET_TABLE"]
API_GATEWAY_ENDPOINT = os.environ["API_GATEWAY_ENDPOINT"]

# Initialize DynamoDB resource and table
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMO_TABLE_NAME)

# Initialize API Gateway client for WebSocket message handling
apigateway = boto3.client(
    "apigatewaymanagementapi",
    endpoint_url=API_GATEWAY_ENDPOINT,
)


def lambda_handler(event, context):
    """
    Handles the initial WebSocket connection.
    """
    connection_id = event["requestContext"]["connectionId"]
    game_id = event["queryStringParameters"].get("gameId")

    # Return an error if gameId is not provided
    if not game_id:
        return {"statusCode": 400, "body": "Missing gameId in URI"}

    # Fetch game data from DynamoDB
    response = table.get_item(Key={"gameId": game_id})
    game = response.get("Item")

    # Return an error if the game ID is not found
    if not game:
        return {"statusCode": 404, "body": "Game not found"}

    # Add the connection ID to the game's connection list
    connections = game.get("connections", [])
    connections.append(connection_id)

    # Update the database with the updated connections
    table.update_item(
        Key={"gameId": game_id},
        UpdateExpression="SET connections = :c",
        ExpressionAttributeValues={":c": connections},
    )

    # Notify all players about the new connection
    for conn_id in connections:
        apigateway.post_to_connection(
            ConnectionId=conn_id,
            Data=json.dumps(
                {
                    "message": "PlayerJoined",
                    "details": f"A new player has joined game {game_id}.",
                }
            ).encode("utf-8"),
        )

    return {"statusCode": 200, "body": "Connection established"}
