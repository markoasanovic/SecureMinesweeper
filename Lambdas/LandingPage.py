import boto3
import os
from jinja2 import Template
from boto3.dynamodb.conditions import Key

# Initialize AWS DynamoDB and S3 clients
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

# Load environment variables for S3 bucket and DynamoDB table
TEMPLATE_BUCKET_NAME = os.environ["TEMPLATE_BUCKET_NAME"]
WEBSOCKET_TABLE = os.environ["WEBSOCKET_TABLE"]

# Define constants for template folder and file names
TEMPLATE_FOLDER_NAME = "SecureMinesweeper"
MINESWEEPER_TEMPLATE_FILE = "MinesweeperTemplate.jinja"
LANDING_PAGE_FILE = "LandingPage.jinja"


def lambda_handler(event, context):
    """
    Serve correct template based on if there is a ?gameId=[id] URI param
    """

    # Extract gameId from query parameters
    query_params = event.get("queryStringParameters") or {}
    game_id = query_params.get("gameId")

    # Decide whether to serve the Minesweeper template or the Landing Page
    # if there is no game id, then serve the landing page
    if game_id is not None:
        template_key = f"{TEMPLATE_FOLDER_NAME}/{MINESWEEPER_TEMPLATE_FILE}"

        # Fetch game board data from DynamoDB
        table = dynamodb.Table(WEBSOCKET_TABLE)
        dynamo_response = table.get_item(Key={"gameId": game_id})

        if "Item" not in dynamo_response:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "text/plain"},
                "body": f"Game with gameId {game_id} not found.",
            }
        
        itm = dynamo_response["Item"]

        board_state = [
            [
                {"value": value, "revealed": revealed, "flagged": flagged}
                for value, revealed, flagged in zip(row_values, row_revealed, row_flagged)
            ]
            for row_values, row_revealed, row_flagged in zip(
                itm["boardValues"], itm["revealedTiles"], itm["flagPositions"]
            )
        ]
        #print(board_state)

        # Fetch and render the Minesweeper template
        response = s3_client.get_object(Bucket=TEMPLATE_BUCKET_NAME, Key=template_key)
        template_content = response["Body"].read().decode("utf-8")
        template = Template(template_content)
        rendered_html = template.render(grid=board_state)
    else:
        # otherwise serve the Landing Page
        template_key = f"{TEMPLATE_FOLDER_NAME}/{LANDING_PAGE_FILE}"

        # Fetch and "render" (not needed at the moment) the Landing Page template
        response = s3_client.get_object(Bucket=TEMPLATE_BUCKET_NAME, Key=template_key)
        rendered_html = response["Body"].read().decode("utf-8")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": rendered_html,
    }
