import os
import re
from html.parser import HTMLParser
from collections import defaultdict
import numpy as np
from google.cloud import storage
from google.oauth2 import service_account
import json
import time
import concurrent.futures
from bs4 import BeautifulSoup
import re

f = open('ds-561-vanisinghal-aa18c6c25b69.json')
creds = json.load(f)


credentials = service_account.Credentials.from_service_account_info(creds)
"""

def read_last_run_time(types,filename="logs.json"):
    try:
        with open(filename, "r") as f:
            data = f.read()
            if not data:
                return None  # File is empty
            data_json = json.loads(data)
            return data_json.get(types + '_time', None)
    except (FileNotFoundError, json.JSONDecodeError):
        return None  # File not found or invalid JSON

def write_run_info(elapsed_upload_time,elapsed_processing_time, incoming_stats, outgoing_stats, top_5_counts, filename="logs.json"):
    with open(filename, "w") as f:
        data = {'upload_time': elapsed_upload_time}
        data['processing_time'] = elapsed_processing_time
        # incoming_stats["Quintiles"] = incoming_stats["Quintiles"].tolist()
        # outgoing_stats["Quintiles"] = outgoing_stats["Quintiles"].tolist()
        # data['incoming_stats'] = incoming_stats
        # data['outgoing_stats'] = outgoing_stats
        # data['top_5_pages'] = top_5_counts
        json.dump(data, f)

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

def upload_folder_to_storage(bucket_name, folder_path):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    count = 0

    last_run_time = read_last_run_time("upload","logs.json")

    if last_run_time is not None:
        print(f"Please note, this could take some time. Last run took {last_run_time} seconds.")

    start_time = time.time()

    for root, _, files in os.walk(folder_path):
        for file in files:
            local_file = os.path.join(root, file)
            remote_path = os.path.relpath(local_file, folder_path)

            # Check if blob already exists
            blob = bucket.blob('files/'+remote_path)
            if not blob.exists():
                blob.upload_from_filename(local_file)
                count+=1
            else:
                break

    end_time = time.time()
    elapsed_time = end_time - start_time

    write_run_info(elapsed_time,read_last_run_time('processing'), {}, {}, {})

    print(f"{count} files uploaded")
"""
# Custom parser to extract links
class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href":
                    self.links.append(value)


def compute_stats(link_counts):
    return {
        "Average": np.mean(link_counts),
        "Median": np.median(link_counts),
        "Max": max(link_counts),
        "Min": min(link_counts),
        "Quintiles": np.percentile(link_counts, [20, 40, 60, 80])
    }


def iterative_pagerank(graph, damping_factor=0.85, max_iterations=10, convergence_threshold=0.005):
    # Initialize PageRank scores for all pages to 1/N, where N is the number of pages.
    num_pages = len(graph)
    pagerank = {page: 1.0 / num_pages for page in graph}

    for iteration in range(max_iterations):
        new_pagerank = {}
        total_diff = 0.0

        for page in graph:
            new_pagerank[page] = (1 - damping_factor) / num_pages

            # Calculate the contributions from incoming links (pages pointing to this page).
            for linking_page in graph:
                if page != linking_page and linking_page in graph[page]:
                    num_outgoing_links = len(graph[linking_page])
                    new_pagerank[page] += damping_factor * pagerank[linking_page] / num_outgoing_links

            # Calculate the absolute difference between the new and old PageRank scores.
            diff = abs(new_pagerank[page] - pagerank[page])
            total_diff += diff

        # Update the PageRank scores with the new scores.
        pagerank = new_pagerank

        # Check for convergence.
        if total_diff < convergence_threshold:
            break

    return pagerank

def process_blob(blob):
    
    filename = blob.name.replace("files/", "").replace(".html", "")
    file_content = blob.download_as_text()
    soup = BeautifulSoup(file_content, 'html.parser')

    # Extract outgoing links
    outgoing_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        outgoing_links.append(href)
    #parser = LinkExtractor()

    #with blob.open("r") as f:
        #parser.feed(f.read())

    #links = {re.sub(r"\.html$", "", link) for link in parser.links}
    return filename, outgoing_links

def upload_file_to_storage(bucket_name, folder_path):
    client = storage.Client(project="ds-561-vanisinghal", credentials=credentials)
    bucket = client.get_bucket(bucket_name)
    start_time = time.time()

    for root, _, files in os.walk(folder_path):
        for file in files:
            local_file = os.path.join(root, file)
            remote_path = os.path.relpath(local_file, folder_path)

            # Check if blob already exists
            blob = bucket.blob('files/'+remote_path)
            if not blob.exists():
                blob.upload_from_filename(local_file)
                count+=1
            else:
                break

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"{elapsed_time} time taken")

    #print(f"{count} files uploaded")

def main():
    storage_client = storage.Client(project="ds-561-vanisinghal", credentials=credentials)
    bucket_name = "hw-2-bucket-ds561"

    folder_path = "./files"  

    upload_file_to_storage(bucket_name, folder_path)

    

    start_time = time.time()


    bucket = storage_client.bucket(bucket_name)
    blobs = list(bucket.list_blobs())
    web_graph = {}
    outgoing_links = defaultdict(int)
    
    for blob in blobs:
        # Download the file.
        file_content = blob.download_as_text()
        file_links = process_blob(blob)

        for links in file_links:
                web_graph[file_links[0]] = links
                outgoing_links[file_links[0]] = len(links)
        

    
    incoming_links_count = [len(graph[filename]) for filename in web_graph]
    outgoing_links_count = [out_count[filename] for filename in web_graph]

    print("Incoming links stats:", compute_stats(incoming_links_count))
    print("Outgoing links stats:", compute_stats(outgoing_links_count))

    page_rank = iterative_pagerank(web_graph)
    top_5_pages = sorted(page_rank, key=page_rank.get, reverse=True)[:5]
    print("Top 5 pages by PageRank Algo:", top_5_pages)

    end_time = time.time()

    

if __name__ == "__main__":
    main()