import os
import email
import csv
import imaplib
import datetime
import pickle
import faiss

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.document_loaders.csv_loader import CSVLoader

load_dotenv()


def process_email_message(email_message):
    csv_data = []

    # Header Details
    date_tuple = email.utils.parsedate_tz(email_message["Date"])
    if date_tuple:
        local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
        local_message_date = str(local_date.strftime("%a, %d %b %Y %H:%M:%S"))
    email_from = str(
        email.header.make_header(email.header.decode_header(email_message["From"]))
    )
    email_to = str(
        email.header.make_header(email.header.decode_header(email_message["To"]))
    )
    subject = str(
        email.header.make_header(email.header.decode_header(email_message["Subject"]))
    )

    # Body details
    for part in email_message.walk():
        if part.get_content_type() == "text/plain":
            body = part.get_payload(decode=True)
            try:
                body_text = body.decode("utf-8")
            except UnicodeDecodeError:
                body_text = body.decode("utf-8", errors="replace")
            data = {"From": email_from, "Subject": subject, "Body": body_text}
            csv_data.append(data)
    return csv_data


def write_to_csv(csv_data, filename):
    with open(filename, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["From", "Subject", "Body"])
        writer.writeheader()
        writer.writerows(csv_data)


def email_ingest():
    # Email Handler Section Below.
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
    mail.list()
    mail.select("inbox")

    # Fetch email UIDs
    status, data = mail.uid("search", None, "UNSEEN")  # ALL/UNSEEN
    email_uids = data[0].split()

    csv_data = []

    # Process each email
    for uid in email_uids:
        result, email_data = mail.uid("fetch", uid, "(RFC822)")
        raw_email = email_data[0][1]
        try:
            raw_email_string = raw_email.decode("utf-8")
        except UnicodeDecodeError:
            raw_email_string = raw_email.decode("utf-8", errors="replace")
        email_message = email.message_from_string(raw_email_string)

        csv_data.extend(process_email_message(email_message))

    write_to_csv(csv_data, "data.csv")

    # Langchain Section Below
    loader = CSVLoader(file_path="./data.csv")
    data = loader.load()

    if not data:
        return ValueError("No new emails.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", ";", ",", " ", ""],
    )
    texts = text_splitter.split_documents(data)

    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

    if not texts or not embeddings:
        return ValueError("No new emails.")

    instance = None
    try:
        instance = FAISS.from_documents(texts, embeddings)
        faiss.write_index(instance.index, "docs.index")
        instance.index = None
        with open("faiss_store.pkl", "wb") as f:
            pickle.dump(instance, f)
        return True
    except Exception as e:
        return e
