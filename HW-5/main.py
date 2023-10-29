from flask import Flask, Response, abort, request
import functions_framework
from google.cloud import storage, logging as gcloud_logging
from google.cloud import pubsub_v1
import mysql.connector
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

db_connection = mysql.connector.connect(
    host='34.132.68.140',
    user='root',
    password='1234',
    database='hw5'
)

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
    
def insert_request(country, client_ip, gender, age, income, is_banned, time_of_day, requested_file, status_code):
    cursor = db_connection.cursor()
    query = """
    INSERT INTO Countries (CountryName) VALUES (%s) ON DUPLICATE KEY UPDATE CountryName = CountryName;
    INSERT INTO Clients (CountryID, Gender, Age, Income, IsBanned) 
    VALUES (
        (SELECT CountryID FROM Countries WHERE CountryName = %s), 
        %s, %s, %s, %s
    );
    INSERT INTO Requests (ClientIP, TimeOfDay, RequestedFile, CountryID) 
    VALUES (
        %s, %s, %s, (SELECT CountryID FROM Countries WHERE CountryName = %s)
    );
    """
    cursor.execute(query, (country, country, gender, age, income, is_banned, client_ip, time_of_day, requested_file, country))
    
    # Insert the request into the FailedRequests table if the status code is not 200
    if status_code != 200:
        insert_failed_request(cursor, time_of_day, requested_file, status_code)
    
    db_connection.commit()
    cursor.close()
    
def insert_failed_request(cursor, time_of_day, requested_file, status_code):
    cursor.execute(
        "INSERT INTO FailedRequests (TimeOfDay, RequestedFile, StatusCode) VALUES (%s, %s, %s)",
        (time_of_day, requested_file, status_code)
    )
            
HTTP_METHODS = ['GET','POST','PUT', 'DELETE', 'HEAD', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']
@app.route('/<path:filename>', methods=HTTP_METHODS)
def serve_file(filename):

    # Check the client's country
    
    country = request.headers.get('X-country')
    client_ip = request.headers.get('X-client-IP')
    gender = request.headers.get('X-gender')
    age = request.headers.get('X-age')
    income = request.headers.get('X-income')
    is_banned = country in BANNED_COUNTRIES
    time_of_day = request.headers.get('X-time-of-day')
    
    if request.method != 'GET':
        logger.log_text(f"Erroneous request method {request.method} for file: {filename}")
        insert_request(country, client_ip, gender, age, income, is_banned, time_of_day, filename, 400)
        return "Not Implemented", 501

    if is_banned:
        # Log the request and publish it to Pub/Sub if the country is banned
        # logger.log_text(f"Request from banned country: {country} for file: {filename}")
        publish_banned_request(country, str(filename), request)
        insert_request(country, client_ip, gender, age, income, is_banned, time_of_day, filename, 400)
        return "Permission Denied", 400

    try:
        # Try to get the file from the Google Cloud Storage bucket
        blob = storage_client.bucket(bucket_name).blob(f'files/{filename}')
        content = blob.download_as_text()
        logger.log_text(f"Request served successfully: {filename}")
        insert_request(country, client_ip, gender, age, income, is_banned, time_of_day, filename, 200)

        # Return the file content as a response
        return Response(content, mimetype='text/html'), 200
    except Exception as e:
        # Handle exceptions, e.g., file not found
        logger.log_text(f"Error handling file request for {filename}: {str(e)}")
        insert_request(country, client_ip, gender, age, income, is_banned, time_of_day, filename, 404)
        return abort(404)
        


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
