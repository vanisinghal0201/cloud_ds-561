import subprocess
import multiprocessing

def run_client(client_number):
    command = f"python3 http-client.py -d 34.29.113.69 -b none -w none -n 50000"  # Modify as needed
    subprocess.run(command, shell=True)

if __name__ == "__main__":
    num_clients = 2

    # Use the same random seed for both clients
    seed = 42

    # Create a pool of worker processes
    pool = multiprocessing.Pool(processes=num_clients)

    # Start the clients with different numbers and the same seed
    pool.map(run_client, range(1, num_clients + 1))

    pool.close()
    pool.join()

    print("Both clients have completed their requests.")
