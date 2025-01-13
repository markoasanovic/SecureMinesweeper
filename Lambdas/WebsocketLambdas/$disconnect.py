import json
import boto3
import os
from boto3.dynamodb.conditions import Attr

# Initialize DynamoDB resource and table
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["WEBSOCKET_TABLE"])


def lambda_handler(event, context):
    """
    Handles a WebSocket user disconnect event.
    """
    connection_id = event["requestContext"]["connectionId"]

    # Scan the DynamoDB table to find all games with this connection ID
    response = table.scan(FilterExpression=Attr("connections").contains(connection_id))
    items = response.get("Items", [])

    # Return a message if no games are found for this connection ID
    if not items:
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "No games found for this connectionId"}),
        }

    # Process each game where this connection ID is found
    for item in items:
        game_id = item["gameId"]
        connections = item["connections"]

        # Remove the connection ID from the game's connection list
        if connection_id in connections:
            connections.remove(connection_id)

            # Update the DynamoDB table with the modified connection list
            table.update_item(
                Key={"gameId": game_id},
                UpdateExpression="SET connections = :new_connections",
                ExpressionAttributeValues={":new_connections": connections},
            )

    # Return a success message with details of the games updated
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Disconnected and removed from all games",
                "connectionId": connection_id,
                "games": [item["gameId"] for item in items],
            }
        ),
    }
