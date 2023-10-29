from flask import Flask, Response, abort, request
import functions_framework
from google.cloud import storage, logging as gcloud_logging
from google.cloud import pubsub_v1
import mysql.connector
import json
import sqlalchemy
#from connect_connector import connect_with_connector
from google.cloud.sql.connector import Connector, IPTypes
import pymysql
from google.cloud import secretmanager
import datetime

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

# GCP project in which to store secrets in Secret Manager.
project_id = "ds-561-vanisinghal"

# ID of the secret to create.
secret_ids = ["db_user","db_pass","db_name","sql_INSTANCE_CONNECTION_NAME","pub_ip"]

creds = {}

def access_secret_version(secret_id, version_id="latest"):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = client.access_secret_version(name=name)

    # Return the decoded payload.
    return response.payload.data.decode('UTF-8')

for secret_id in secret_ids:
    # Access the secret version.
    creds[secret_id] = access_secret_version(secret_id=secret_id)
    
def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """
    Initializes a connection pool for a Cloud SQL instance of MySQL.

    Uses the Cloud SQL Python Connector package.
    """
    # Note: Saving credentials in environment variables is convenient, but not
    # secure - consider a more secure solution such as
    # Cloud Secret Manager (https://cloud.google.com/secret-manager) to help
    # keep secrets safe.

    global creds

    instance_connection_name = creds["sql_INSTANCE_CONNECTION_NAME"]  # e.g. 'project:region:instance'
    db_user = creds["db_user"]  # e.g. 'my-db-user'
    db_pass = creds["db_pass"]  # e.g. 'my-db-password'
    db_name = creds["db_name"]  # e.g. 'my-database'

    ip_type = IPTypes.PUBLIC

    connector = Connector(ip_type)

    def getconn() -> pymysql.connections.Connection:
        conn: pymysql.connections.Connection = connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn

    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
        # [START_EXCLUDE]
        # Pool size is the maximum number of permanent connections to keep.
        pool_size=5,
        # Temporarily exceeds the set pool_size if no connections are available.
        max_overflow=2,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        pool_timeout=30,  # 30 seconds
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # re-established
        pool_recycle=1800,  # 30 minutes
        # [END_EXCLUDE]
    )
    return pool


def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    """Sets up connection pool for the app."""
    return connect_with_connector()

db = None

# init_db lazily instantiates a database connection pool. Users of Cloud Run or
# App Engine may wish to skip this lazy instantiation and connect as soon
# as the function is loaded. This is primarily to help testing.
@app.before_first_request
def init_db() -> sqlalchemy.engine.base.Engine:
    """Initiates connection to database and its' structure."""
    global db
    db = init_connection_pool()    
    
    
    

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
    
def insert_request(db,country, client_ip, gender, age, income, is_banned, time_of_day, requested_file, status_code):
   
    stmt_user = sqlalchemy.text(
        "INSERT INTO Clients (client_ip, gender, age, income, is_banned) VALUES (:client_ip, :gender, :age, :income, :is_banned)"
    )
    stmt_request = sqlalchemy.text(
        "INSERT INTO Requests (user_id, country, time_of_day, requested_file) VALUES (:user_id, :country, :time, :requested_file)"
    )
    
    try:
        # Using a with statement ensures that the connection is always released
        # back into the pool at the end of statement (even if an error occurs)
        with db.connect() as conn:
            res = conn.execute(stmt_user, parameters={"client_ip": client_ip, "gender": gender, "age":age, "income": income, "is_banned":is_banned})
            conn.execute(stmt_request, parameters={"user_id": res.lastrowid, "country":country, "time": time_of_day, "requested_file":requested_file})
            conn.commit()
    except Exception as e:
        # If something goes wrong, handle the error in this section. This might
        # involve retrying or adjusting parameters depending on the situation.
        # [START_EXCLUDE]
        print(e)
        return Response(
            status=500,
            response="Please check the application logs for more details.",
        )
    # Insert the request into the FailedRequests table if the status code is not 200
    if status_code != 200:
        insert_failed_request(db, time_of_day, requested_file, status_code)
 
    
def insert_failed_request(db, time_of_day, requested_file, status_code):
    db = init_connection_pool()

    stmt_failed_request = sqlalchemy.text(
        "INSERT INTO FailedRequests (TimeOfDay, RequestedFile, StatusCode) VALUES (:TimeOfDay, :RequestedFile, :StatusCode)"
    )
    time_cast = datetime.datetime.now(tz=datetime.timezone.utc)
    try:
        # Using a with statement ensures that the connection is always released
        # back into the pool at the end of statement (even if an error occurs)
        with db.connect() as conn:
            res = conn.execute(stmt_failed_request, parameters={"TimeOfDay": time_of_day, "RequestedFile": requested_file, "StatusCode":status_code})
            conn.commit()
    except Exception as e:
        # If something goes wrong, handle the error in this section. This might
        # involve retrying or adjusting parameters depending on the situation.
        # [START_EXCLUDE]
        print(e)
        return Response(
            status=500,
            response="Please check the application logs for more details.",
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
    
    global db
    db = init_connection_pool()
    time_of_day = datetime.datetime.now(tz=datetime.timezone.utc)
    if request.method != 'GET':
        logger.log_text(f"Erroneous request method {request.method} for file: {filename}")
        insert_request(db,country, client_ip, gender, age, income, is_banned, time_of_day, filename, 501)
        return "Not Implemented", 501
    if is_banned:
        # Log the request and publish it to Pub/Sub if the country is banned
        # logger.log_text(f"Request from banned country: {country} for file: {filename}")
        publish_banned_request(country, str(filename), request)
        insert_request(db,country, client_ip, gender, age, income, is_banned, time_of_day, filename, 400)

        return "Permission Denied", 400

    try:
        # Try to get the file from the Google Cloud Storage bucket
        blob = storage_client.bucket(bucket_name).blob(f'files/{filename}')
        content = blob.download_as_text()
        logger.log_text(f"Request served successfully: {filename}")
        insert_request(db,country, client_ip, gender, age, income, is_banned, time_of_day, filename, 200)

        # Return the file content as a response
        return Response(content, mimetype='text/html'), 200
    except Exception as e:
        # Handle exceptions, e.g., file not found
        logger.log_text(f"Error handling file request for {filename}: {str(e)}")
        insert_request(db,country, client_ip, gender, age, income, is_banned, time_of_day, filename, 404)

        return abort(404)
        


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
