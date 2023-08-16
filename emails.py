import email
import imaplib
import threading
import time
from email.header import decode_header
import re
import schedule
from mysql.connector import pooling
from flask_cors import CORS
from flask_cors import cross_origin
from flask import Flask, request, jsonify
from geotext import GeoText
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'klaimohamed1994@gmail.com'
app.config['MAIL_PASSWORD'] = 'nnpvjpcogwzpzsbv'
app.config['MAIL_DEFAULT_SENDER'] = 'klaimohamed1994@gmail.com'

mail=Mail(app)
CORS(app)
previous_email = None
db_connection_pool = pooling.MySQLConnectionPool(
    pool_name="email_pool",
    pool_size=5,
    host="localhost",
    user="root",
    password="",
    database="emails",
)
def extract_locations(text):
    places = GeoText(text)
    
    if not places.cities and not places.countries:
        return "Aucun"
    
    locations = list(places.cities) + list(places.countries)
    return ", ".join(locations)

def extract_emails_from_body(email_body, delimiter=', '):
    # Define a regular expression pattern to match email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b'
    # Use re.findall() to extract email addresses from the email body
    extracted_emails = re.findall(email_pattern, email_body)
    # Join the extracted emails using the specified delimiter
    emails_str = delimiter.join(extracted_emails)
    if emails_str=='':
       emails_str="Aucun"
    return emails_str

def classify_email(email_subject, email_content):
    # Define regular expressions for identifying distance and presentiel keywords
    distance_keywords = ['remote', 'virtual', 'online', 'distance']
    presentiel_keywords = ['in-person', 'onsite', 'physical', 'face-to-face','presentiel']
    # Convert email content to lowercase for case-insensitive matching
    email_content = email_content.lower()
    # Search for distance keywords
    for keyword in distance_keywords:
        if re.search(keyword, email_subject, re.IGNORECASE) or re.search(keyword, email_content, re.IGNORECASE):
            return 'Distance'
    # Search for presentiel keywords
    for keyword in presentiel_keywords:
        if re.search(keyword, email_subject, re.IGNORECASE) or re.search(keyword, email_content, re.IGNORECASE):
            return 'Presentiel'
    return 'Aucun'
def extract_dates(body):
    date_regex = r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b"
    date_matches = re.findall(date_regex, body)
    dates=[]
    for match in date_matches:
        day = match[0]
        month = match[1]
        year = match[2]
        date = f"{day}/{month}/{year}"
        dates.append(date)
    if dates:
        print("Dates found:", date)
    else:
        date="Aucun"
        print("No dates found.") 
    return date
def extract_durations(body):
    duration_regex = r"\b(\d+)\s*(mois|semaines|jours|months|weeks|days)s?\b"
    # Find all matches of durations in the email body
    duration_matches = re.findall(duration_regex, body, re.IGNORECASE)
    durations = []
    for match in duration_matches:
        duration_value = match[0]
        duration_unit = match[1]
        duration = f"{duration_value} {duration_unit}"
        durations.append(duration)
    if durations:
        print("Durations found:", duration)
    else:
        duration="Aucun"
        print("No durations found.")  
    return duration
def process_email():
    global previous_email
    # Connexion au serveur de messagerie IMAP
    imap_server = imaplib.IMAP4_SSL("imap.gmail.com")
    imap_server.login("klaimohamed1994@gmail.com", "biwkfvtfnzhscbrf")
    imap_server.select("INBOX")
    # Recherche des emails en fonction de critères spécifiques (récupération du dernier email)
    status, email_ids = imap_server.search(None, "ALL")
    latest_email_id = email_ids[0].split()[-1]
    # Récupération des données du dernier email
    status, email_data = imap_server.fetch(latest_email_id, "(RFC822)")
    raw_email = email_data[0][1]
    email_message = email.message_from_bytes(raw_email)
    # Extraction des données pertinentes de l'email
    sender_header = email_message["From"]
    sender_decoded = decode_header(sender_header)[0][0]
    start_index = sender_decoded.find("<") + 1
    end_index = sender_decoded.find(">")
    name = sender_decoded[: start_index - 1]
    sender = sender_decoded[start_index:end_index]
    subject_header = email_message["Subject"]
    subject_decoded = decode_header(subject_header)[0][0]
    subject = (
        subject_decoded.decode("utf-8")
        if isinstance(subject_decoded, bytes)
        else subject_decoded
    )
    date = email_message["Date"]
    title = ["offre", "stage", "emploi", "job", "offer", "internship", "d'ete", "summer"]
    found_titles = []
    sub = subject.split()
    for word in sub:
        lowercase_word = word.lower()
        if (
            any(lowercase_word in title.lower() for title in title)
            and lowercase_word not in found_titles
            and len(lowercase_word) > 2
        ):
            found_titles.append(lowercase_word)

    filtered_title = " ".join(found_titles)
    if filtered_title == "":
        filtered_title = "Email does not contain any relevant title."

    print(filtered_title)
    
    body = ""
    # Extraction du corps de l'email basé sur le type de contenu (text/plain)
    for part in email_message.walk():
        if part.get_content_type() == "text/plain":
            body = part.get_payload(decode=True).decode("utf-8")
            break
    email_body=extract_emails_from_body(body)
    words = body.split()
    etat = classify_email(subject, body)
    location = extract_locations(body) 
    skills = [
        "react",
        "angular",
        "vuejs",
        "javascript",
        "nodejs",
        "python",
        "java",
        "c++",
        ".Net",
        "spring",
        "programmation"
        "html,",
        "css"
    ]
    found_keywords = []
    for word in words:
        lowercase_word = word.lower()
        if (
            any(lowercase_word in skills.lower() for skills in skills)
            and lowercase_word not in found_keywords
            and len(lowercase_word) > 2
        ):
            found_keywords.append(lowercase_word)
    filtered_skills = " ".join(found_keywords)
    if filtered_skills == " ":
        filtered_skills = "Aucun."
    domaine = [
        "algorithm",
        "artificial intelligence (ai)",
        "big data",
        "cloud computing",
        "cryptography",
        "cybersecurity",
        "data analysis",
        "data science",
        "développement informatique",
        "développement web",
        "database",
        "digital transformation",
        "internet of things (IoT)",
        "machine learning",
        "network",
        "operating system",
        "programming language",
        "software development",
        "web development",
        "virtual reality (vr)",
        "augmented reality (ar)",
        "blockchain",
        "computer graphics",
        "computer vision",
        "data Mining",
        "robotics",
    ]
    
   
    
    found_keywords1 = []
    for word in words:
        lowercase_word = word.lower()
        if (
            any(lowercase_word in d.lower() for d in domaine)
            and lowercase_word not in found_keywords1
            and len(lowercase_word) > 2
        ):
            found_keywords1.append(lowercase_word)

    filtered_domaine = " ".join(found_keywords1)
    if filtered_domaine == "":
        filtered_domaine = "Aucun."
    duration=extract_durations(body)
    date_limit=extract_dates(body)
    
    link_regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    # Search for the link pattern in the email body
    link_match = re.search(link_regex, body)
    link = ""
    if link_match:
        link = link_match.group()
        print("Link:", link)
    else:
        link = "Aucun"
        print("No link found.")
    # Connexion à la base de données à partir du pool de connexions
    db_connection = db_connection_pool.get_connection()

    # Insertion des données dans la base de données
    if filtered_title != "Email does not contain any relevant title." and (
        previous_email is None
        or ( 
            etat,
            email_body,
            sender,
            subject,
            date,
            filtered_skills,
            name,
            filtered_domaine,
            duration,
            location,
            link,
            body,
            date_limit
        )
        != previous_email
    ):
        previous_email = (
            etat,
            email_body,
            sender,
            subject,
            date,
            filtered_skills,
            name,
            filtered_domaine,
            duration,
            location,
            link,
            body,
            date_limit
        )
        cursor = db_connection.cursor()
        sql = "INSERT INTO emails (etat ,email_body,sender, subject, date, skills, name, domaine, dure, location,link,body,date_limit) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s)"
        email_data = (
            etat,
            email_body,
            sender,
            subject,
            date,
            filtered_skills,
            name,
            filtered_domaine,
            duration,
            location,
            link,
            body,
            date_limit
        )
        cursor.execute(sql, email_data)
        db_connection.commit()
        cursor.close()

    db_connection.close()

    # Fermeture de la connexion au serveur IMAP
    imap_server.close()
    imap_server.logout()

    print("Email processed")


def schedule_email_processing():
    schedule.every(10).seconds.do(process_email)

    while True:
        schedule.run_pending()
        time.sleep(1)


def start_email_processing_thread():
    thread = threading.Thread(target=schedule_email_processing)
    thread.start()

@app.route("/all", methods=["GET"])
@cross_origin()
def show_emails():
    # Connexion à la base de données à partir du pool de connexions
    db_connection = db_connection_pool.get_connection()

    # Récupération des données de la base de données
    cursor = db_connection.cursor()
    sql = "SELECT id ,etat ,sender,email_body, subject, date, skills, name, domaine, dure, location, link,body,date_limit FROM emails"
    cursor.execute(sql)
    emails = cursor.fetchall()
    columns = [
        column[0] for column in cursor.description
    ]  # Get column names from cursor
    cursor.close()
    db_connection.close()

    # Create a list of dictionaries with column names as keys
    result = []
    for email in emails:
        email_dict = {}
        for i, value in enumerate(email):
            email_dict[columns[i]] = value
        result.append(email_dict)

    return jsonify(result)
    #return render_template("emails.html", emails=emails)
@app.route("/email/<int:email_id>", methods=["GET"])
@cross_origin()
def get_email_by_id(email_id):
    # Connect to the database using the connection pool
    db_connection = db_connection_pool.get_connection()
    cursor = db_connection.cursor()
    
    # Retrieve the email by its ID from the database
    sql = "SELECT id,etat, sender,email_body, subject, date, skills, name, domaine, dure, location, link,body,date_limit FROM emails WHERE id = %s"
    cursor.execute(sql, (email_id,))
    email = cursor.fetchone()
    columns = [
        column[0] for column in cursor.description
    ]  # Get column names from cursor
    cursor.close()
    db_connection.close()
    # If the email is found, return it as a dictionary
    if email:
       email_dict = dict(zip(columns, email))
       return jsonify(email_dict)
    else:
        return jsonify({"error": "Email not found"}), 404

# ... (previous imports and code)

# Function to filter emails from the database
def filter_emails(domaine):
    connection = db_connection_pool.get_connection()
    cursor = connection.cursor()

    query = "SELECT id, etat, email_body, sender, subject, date, skills, name, domaine, dure, location, link FROM emails WHERE 1=1"
    if domaine:
        query += f" AND domaine = '{domaine}'"

    cursor.execute(query)
    emails = cursor.fetchall()

    cursor.close()
    connection.close()

    emails_list = []
    for email in emails:
        email_dict = {
            'id': email[0],
            'etat': email[1],
            'email_body': email[2],
            'sender': email[3],
            'subject': email[4],
            'date': email[5],
            'skills': email[6],
            'name': email[7],
            'domaine': email[8],
            'dure': email[9],
            'location': email[10],
            'link': email[11],
        }
        emails_list.append(email_dict)

    return emails_list

# Route to filter emails

@app.route('/filter_emails', methods=['POST'])
@cross_origin()
def route_filter_emails():
    data = request.get_json()
    domaine = data.get('domaine')

    if not domaine:
        return jsonify({'error': 'Domaine parameter is missing'}), 400

    filtered_emails = filter_emails(domaine)
    return jsonify(filtered_emails)



@app.route('/send_email', methods=['POST'])
def send_email():
    email = request.form['email']
    message = request.form['message']
    subject = request.form['subject']
    attachment = request.files.get('attachment')

    msg = Message(subject=subject, sender='klaimohamed1994@gmail.com', recipients=[email])
    msg.body = message
    if attachment:
        msg.attach(attachment.filename, 'application/octet-stream', attachment.read())

    try:
        mail.send(msg)
        return jsonify({'message': 'Email sent successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/data', methods=['GET'])
def get_data():
    page = int(request.args.get('page', 1))
    items_per_page = 10  # Number of items per page

    start_index = (page - 1) * items_per_page

    db_connection = db_connection_pool.get_connection()
    cursor = db_connection.cursor()

    try:
        # Get sum of a column
        cursor.execute("SELECT SUM(sender) FROM emails")
        total_sum = cursor.fetchone()[0]

        # Get paginated data
        cursor.execute(f"SELECT * FROM emails LIMIT {start_index}, {items_per_page}")
        data = cursor.fetchall()
        columns = [
            column[0] for column in cursor.description
        ]  # Get column names from cursor
        result = []

        for email in data:
            email_dict = {}
            for i, value in enumerate(email):
                email_dict[columns[i]] = value
            result.append(email_dict)
    
        response = {
            'total_sum': total_sum,
            'data': result
        }

    finally:
        cursor.close()
        db_connection.close()

    return jsonify(response)


if __name__ == "__main__":
    start_email_processing_thread()
    app.run()
