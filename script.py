import faiss
import telebot
import pickle

# Utility libraries
import os
from dotenv import load_dotenv

# For scheduling bot messaging
import schedule
from threading import Thread
from time import sleep

# LangChain
from langchain.chains import RetrievalQA

from langchain.memory import ConversationBufferMemory
from langchain import PromptTemplate
from langchain.chat_models import ChatOpenAI


from ingest import email_ingest

template = """
Task: Understand the content & context of my emails and create a list of actionable items from the email content. Keep in mind that you're a chat-bot, respond to me as if you're chatting with me on WhatsApp/Telegram.
Style: Like a regular human personal assistant with access to my emails
Tone: Humane
Audience: 20-year old
Length: 2 paragraphs
Note: A user may be having questions about certain emails. Respond to them appropriately without diverting the topic of the email or the conversation.

Respond with the format between `---`:
---
Hey, Ritik. Actionable item-list:

- [Summary of email with subject]
- [Summary of email with subject]
- [Summary of email with subject]

Have a good one! [ADD A QUOTE TO MOTIVATE THE USER FOR HIS DAY]
---

Make sure to use bullet points for each new unread email. Avoid emails that are spam/marketing/newsletter related. Use whitespace to make texts readable.


Context: {context}

Human: {question}
"""
prompt = PromptTemplate(template=template, input_variables=["context", "question"])
llm = ChatOpenAI(temperature=0)

load_dotenv()
token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(token)

try:
    index = faiss.read_index("docs.index")

    with open("faiss_store.pkl", "rb") as f:
        store = pickle.load(f)

    store.index = index
    memory = ConversationBufferMemory()
    chain_type_kwargs = {"prompt": prompt}
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=store.as_retriever(),
        memory=memory,
        chain_type_kwargs=chain_type_kwargs,
    )
except:
    ingest_response = email_ingest()


@bot.message_handler(commands=["refresh", "start"])
def start(message):
    msg_if_emails_available = (
        "Hello, Ritik. Let's get working. I have access to your emails"
    )
    msg_if_no_unread_emails_found = "No new unread emails found."
    ingest_response = email_ingest()
    if ingest_response != True:
        bot.reply_to(message, msg_if_no_unread_emails_found)
        print(msg_if_no_unread_emails_found)
    else:
        bot.reply_to(message, msg_if_emails_available)


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


if __name__ in "__main__":
    schedule.every().day.at("08:00").do(email_ingest)
    Thread(target=schedule_checker).start()

bot.infinity_polling()
