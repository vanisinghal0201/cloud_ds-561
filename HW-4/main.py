from flask import Flask, Response, abort, request
import functions_framework
from google.cloud import storage, logging as gcloud_logging
from google.cloud import pubsub_v1
import json

app = Flask(__name__)

# Initialize a Google Cloud Storage client
storage_client = storage.Client.create_anonymous_client()

# Define the Google Cloud Storage bucket name
bucket_name = 'hw-2-bucket-ds561'

# Set up Google Cloud Logging
logging_client = gcloud_logging.Client()
logger = logging_client.logger('gcs-file-requests')

# List of banned countries
BANNED_COUNTRIES = ['North Korea', 'Iran', 'Cuba', 'Myanmar', 'Iraq', 'Libya', 'Sudan', 'Zimbabwe', 'Syria']


def publish_banned_request(country, filename, request):
    # Initialize a Pub/Sub publisher client
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path('ds-561-vanisinghal', 'handle-banned-messages')
    

    # Prepare data for publishing
    data = {
        'country': country,
        'ip': request.headers.get('X-client-IP'),
        'filename': filename
    }

    # Publish the request data to Pub/Sub
    publisher.publish(topic_path, data=json.dumps(data).encode("utf-8"))

@app.route('/<path:filename>', methods=['GET'])
def serve_file(filename):

    # Check the client's country
    
    country = request.headers.get('X-country')
    
    if request.method != 'GET':
        logger.log_text(f"Erroneous request method {request.method} for file: {filename}")
        return "Not Implemented", 501

    if country in BANNED_COUNTRIES:
        # Log the request and publish it to Pub/Sub if the country is banned
        # logger.log_text(f"Request from banned country: {country} for file: {filename}")
        publish_banned_request(country, str(filename), request)
        return "Permission Denied", 400

    try:
        # Try to get the file from the Google Cloud Storage bucket
        blob = storage_client.bucket(bucket_name).blob(f'files/{filename}')
        content = blob.download_as_text()

        # Return the file content as a response
        return Response(content, mimetype='text/html'), 200
    except Exception as e:
        # Handle exceptions, e.g., file not found
        logger.log_text(f"Error handling file request for {filename}: {str(e)}")
        abort(404)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
