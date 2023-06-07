# For emails and telegram
import imaplib
import email
import csv
import faiss
import telebot
import pickle

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

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings

from ingest import email_ingest

template = """
Task: Understand the content & context of my emails and create a list of actionable items from the email content. Keep in mind that you're a chat-bot, respond to me as if you're chatting with me on WhatsApp/Telegram.
Style: Like a regular human personal assistant with access to my emails
Tone: Humane
Audience: 20-year old
Length: 2 paragraphs
Note: A user may be having questions about certain emails. Respond to them appropriately without diverting the topic of the email or the conversation.

Be smart enough to separate newsletter content from more important emails.

Respond with only the format below:

Hey, [greeting message of your choice].

There are [NUMBER OF NEW EMAILS] new emails in your inbox. Here is a list of actionable items for you:

[ACTIONABLE ITEM LIST ONLY BASED ON THE CONTENT OF THE EMAILS]

Have a good one! [ADD A QUOTE TO MOTIVATE THE USER FOR HIS DAY]
---


Context: {context}

Human: {question}
"""
prompt = PromptTemplate(template=template, input_variables=["context", "question"])
llm = ChatOpenAI(temperature=0)

load_dotenv()
token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(token)

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


@bot.message_handler(commands=["refresh", "start"])
def start(message):
    msg = """Hello, Ritik. Let's get working. I have access to your emails"""
    email_ingest()
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


if __name__ in "__main__":
    schedule.every().day.at("08:00").do(email_ingest)
    Thread(target=schedule_checker).start()

bot.infinity_polling()
