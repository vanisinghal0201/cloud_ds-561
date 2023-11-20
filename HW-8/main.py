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

def get_instance_zone():
    """
    Fetches the zone information of the current GCP instance.
    """
    metadata_server = "http://metadata.google.internal/computeMetadata/v1/instance/zone"
    metadata_flavor = {"Metadata-Flavor": "Google"}
    try:
        response = requests.get(metadata_server, headers=metadata_flavor)
        if response.status_code == 200:
            # The response includes the full zone path, so we split to get the last part
            return response.text.split('/')[-1]
    except requests.exceptions.RequestException:
        return "Unknown"
    

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
    
HTTP_METHODS = ['GET','POST','PUT', 'DELETE', 'HEAD', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']
@app.route('/', methods=HTTP_METHODS)
def home():
    zone = get_instance_zone()
    response = make_response("Not the path you are looking for", 200)
    response.headers['Server-Zone'] = zone
    return response
    
@app.route('/<path:filename>', methods=HTTP_METHODS)
def serve_file(filename):

    # Check the client's country
    
    country = request.headers.get('X-country')
    client_ip = request.headers.get('X-client-IP')
    gender = request.headers.get('X-gender')
    age = request.headers.get('X-age')
    income = request.headers.get('X-income')
    is_banned = country in BANNED_COUNTRIES

    zone = get_instance_zone()
    
    if request.method != 'GET':
        logger.log_text(f"Erroneous request method {request.method} for file: {filename}")
        response = make_response("Not Implemented", 501)
        response.headers['Server-Zone'] = zone
        return response

    if country in BANNED_COUNTRIES:
        # Log the request and publish it to Pub/Sub if the country is banned
        # logger.log_text(f"Request from banned country: {country} for file: {filename}")
        publish_banned_request(country, str(filename), request)
        response = make_response("Permission Denied", 400)
        response.headers['Server-Zone'] = zone
        return response

    try:
        # Try to get the file from the Google Cloud Storage bucket
        blob = storage_client.bucket(bucket_name).blob(f'files/{filename}')
        content = blob.download_as_text()

        # Return the file content as a response
        return Response(content, mimetype='text/html'), 200
    except Exception as e:
        # Handle exceptions, e.g., file not found
        logger.log_text(f"Error handling file request for {filename}: {str(e)}")
        response = make_response("File not found", 404)
        response.headers['Server-Zone'] = zone
        return response
    
    blob = bucket.blob('files/' + filename)
    content = blob.download_as_text()
    
    response = make_response(content)  # Adjust the mimetype based on your file types
    response.headers['Server-Zone'] = zone
    response.headers['Content-Type'] = 'text/html'
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
