import requests
import threading

def make_request(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Request successful")
        else:
            print(f"Request failed with status code: {response.status_code}")
        return response.elapsed.total_seconds()
    except requests.RequestException:
        return None

def worker(target_url, num_requests_per_thread, response_times):
    for _ in range(num_requests_per_thread):
        response_time = make_request(target_url)
        if response_time is not None:
            response_times.append(response_time)

def stress_test(target_url, num_requests, num_threads):
    response_times = []

    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker, args=(target_url, num_requests // num_threads, response_times))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
        
    print("Response Times")    
    print(response_times)
    print("Stress test completed.")

if __name__ == '__main__':
    target_url = "http://34.29.113.69/229.html"
    num_requests = 1000
    num_threads = 100
    stress_test(target_url, num_requests, num_threads)
