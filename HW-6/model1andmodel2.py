import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import pymysql
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder
import ipaddress

# Define your Cloud SQL database credentials
db_config = {
    'connection_name': 'ds-561-vanisinghal:us-central1:hw-5-database',
    'username': 'root',
    'password': '1234',
    'db_name': 'hw-5',
}

# Create a SQLAlchemy database engine using the Cloud SQL Connector
def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    instance_connection_name = db_config['connection_name']
    db_user = db_config['username']
    db_pass = db_config['password']
    db_name = db_config['db_name']

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

# Define a function to fetch data from the database
def fetch_data():
    sql_query1 = "SELECT * FROM Requests"
    requests_df = pd.read_sql_query(sql_query1, db)
    
    sql_query2 = "SELECT * FROM Clients"
    clients_df = pd.read_sql_query(sql_query2, db)
    
    df = clients_df.merge(requests_df, on='user_id', how='inner')
    
    return df

# Data preprocessing and feature engineering
def preprocess_data1(df):
    df = df.dropna()
    le = LabelEncoder()
    df['country_encoded'] = le.fit_transform(df['country'])
    def ip_to_int(ip_str):
        ip = ipaddress.IPv4Address(ip_str)
        return int(ip)

    # Apply the function to the 'client_ip' column and create a new column with integer values
    df['client_ip_int'] = df['client_ip'].apply(ip_to_int)

    # Split the data into features (X) and the target (y)
    X = df[['client_ip_int']]  # You can add more features as needed
    y = df['country_encoded']

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    return X_train, X_test, y_train, y_test, le

def preprocess_data2(df):
    df = df.dropna()
    le = LabelEncoder()
    df['gender_encoded'] = le.fit_transform(df['gender'])
    df['age_encoded'] = le.fit_transform(df['age'])
    df['country_encoded'] = le.fit_transform(df['country'])
    df['is_banned_encoded'] = le.fit_transform(df['is_banned'])

    # Convert IP addresses to integers
    def ip_to_int(ip_str):
        ip = ipaddress.IPv4Address(ip_str)
        return int(ip)

    df['client_ip_int'] = df['client_ip'].apply(ip_to_int)

    # Split the data into features (X) and the target (y)
    X = df[['gender_encoded', 'age_encoded', 'client_ip_int','country_encoded','is_banned_encoded']]  # You can add more features as needed
    y = le.fit_transform(df['income'])

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    return X_train, X_test, y_train, y_test,le


# Build and train the machine learning model for the first problem
def build_and_train_model(X_train, y_train):
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    return model

# Evaluate the model for the first problem
def evaluate_model(model, X_test, y_test, le):
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    y_test_decoded = le.inverse_transform(y_test)
    y_pred_decoded = le.inverse_transform(y_pred)
    
    report = classification_report(y_test_decoded, y_pred_decoded)

    return accuracy, report



db = init_connection_pool()    
data = fetch_data()

# Preprocess the data for the first problem
X_train1, X_test1, y_train1, y_test1, le1 = preprocess_data1(data)

# Build and train the model for the first problem
model1 = build_and_train_model(X_train1, y_train1)

# Evaluate the model for the first problem
accuracy1, report1 = evaluate_model(model1, X_test1, y_test1, le1)

print("Model 1 - Predicting Country:")
print(f"Accuracy: {accuracy1 * 100:.2f}%")
print("Classification Report:")
print(report1)

# Preprocess the data for the second problem
X_train2, X_test2, y_train2, y_test2, le2 = preprocess_data2(data)

# Build and train the model for the second problem
model2 = build_and_train_model(X_train2, y_train2)

# Evaluate the model for the second problem
accuracy2, report2 = evaluate_model(model2, X_test2, y_test2, le2)

print("Model 2 - Predicting Income:")
print(f"Accuracy: {accuracy2 * 100:.2f}%")
print("Classification Report:")
print(report2)
