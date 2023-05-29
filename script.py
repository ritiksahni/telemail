# For emails and telegram
import imaplib
import email
import csv
import telebot

# Utility libraries
import datetime
import os
from dotenv import load_dotenv

# For scheduling bot messaging
import schedule
from threading import Thread
from time import sleep

# LangChain
from langchain.chains import RetrievalQA
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings

template = """
You are a personal assistant capable of going through your owner's email content and summarizing, creating to-do items based on that.

Your owner's name is Ritik Sahni. Address him by his name.

Ritik Sahni could also ask for clarification so make sure to respond to those questions.

Do not try to do anything else other than summarizing, and answering questions. You're NOT capable of doing anything else such as schedule meetings.

When you initiate a conversation, you must always reply with the main substance i.e. email summary, actionable items list.

You could use the following format:
Actionable Emails:
[Sender Name] - [Email Subject] - [Email Summary]

Current to-do:
- [to-do item name (for e.g. write back to Rohan at 3pm accepting offer for lunch)]

Make sure to include important date and time if any email content has one.

Clear the to-do items or add items to the list if Ritik asks you to do so. Make sure you don't make mistakes regarding the status of the to-do list.
{context}

Human: {question}
"""
prompt = PromptTemplate(template=template, input_variables=["context", "question"])
llm = ChatOpenAI(temperature=0)

load_dotenv()
token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(token)

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

    # Header Details
    date_tuple = email.utils.parsedate_tz(email_message["Date"])
    if date_tuple:
        local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
        local_message_date = "%s" % (str(local_date.strftime("%a, %d %b %Y %H:%M:%S")))
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
        else:
            continue

# Write data to CSV file
with open("data.csv", "w", newline="") as csvFile:
    writer = csv.DictWriter(csvFile, fieldnames=["From", "Subject", "Body"])
    writer.writeheader()
    writer.writerows(csv_data)
# Email Variables:
# email_from, subject, body.decode('utf-8)

# Langchain Section Below
loader = CSVLoader(file_path="./data.csv")
data = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separators=["\n\n", "\n", ".", ";", ",", " ", ""],
)
texts = text_splitter.split_documents(data)

embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
# instance = Chroma.from_documents(texts, embeddings, persist_directory="./data")
instance = FAISS.from_documents(texts, embeddings)

retriever = instance.as_retriever()
memory = ConversationBufferMemory()

chain_type_kwargs = {"prompt": prompt}
qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    memory=memory,
    chain_type_kwargs=chain_type_kwargs,
)


@bot.message_handler(commands=["greet", "start"])
def start(message):
    msg = """Hello, Ritik. Let's get working."""
    bot.reply_to(message, msg)


@bot.message_handler(func=lambda m: True)
def all(message):
    print(f"Message received: {message.text}")
    bot.reply_to(message, qa.run(message.text))


print("Bot Started And Waiting For New Messages\n")


# Scheduler
def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(1)


def message_user():
    return bot.send_message(os.getenv("USER_ID"), qa.run("Hey"))


if __name__ in "__main__":
    schedule.every().day.at("08:00").do(message_user)
    Thread(target=schedule_checker).start()

bot.infinity_polling()
