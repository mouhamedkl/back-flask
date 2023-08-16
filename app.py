import threading
from users import app as users_app
from emails import app as emails_app

if __name__ == "__main__":
    # Create thread objects for each Flask app
    users_thread = threading.Thread(target=users_app.run, kwargs={"host": "0.0.0.0", "port": 5000})
    emails_thread = threading.Thread(target=emails_app.run, kwargs={"host": "0.0.0.0", "port": 5001})

    # Start both threads 
    users_thread.start() 
    emails_thread.start()

    # Wait for both threads to finish
    users_thread.join()
    emails_thread.join()
