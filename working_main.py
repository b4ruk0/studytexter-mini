from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
import requests
import json
import os
import random

load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GOOGLE_URL = "https://google.serper.dev/search"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def google_search_links(question):
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "q": f"\"wikipedia\"{question}",
        "num": 10,
    }
    response = requests.post(
        GOOGLE_URL,
        json=payload,
        headers=headers,
    )
    if response.status_code == 200:
        return response.json()
    else:
        raise f"Error: {response.status_code}, {response.text}"


def extract_links(google_search):
    links = []
    for result in google_search["organic"]:
        links.append(result["link"])
    return links


def link_to_data(link):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(link, headers=headers, timeout=5)
    soup = BeautifulSoup(response.text, 'html.parser')
    content_div = soup.find("div", {"class": "mw-parser-output"})
    if not content_div:
        print("Could not find the main content section.")
    paragraphs = content_div.find_all("p")
    page_text = "\n".join([p.get_text() for p in paragraphs if p.get_text().strip()])
    return page_text.strip()


def call_gpt(messages, model="gpt-4o-mini", use_json=False):
    try:
        response_format = {"type": "json_object"} if use_json else None
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format=response_format,
        )
        reply = response.choices[0].message.content
        if reply:
            return reply

        raise ValueError("GPT response is None!")
    except Exception as e:
        print(f"Error calling GPT: {e}")
        return None


def load_text_file(path):
    try:
        with open(path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Error loading file: {e}")


def extract(user_input, model="gpt-4o-mini"):
    messages = [{"role": "user", "content": f"{user_input} \n\nUse JSON, to extract topic, title and question."}]
    response = call_gpt(messages, model=model, use_json=True)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        print("Failed to parse JSON.")
        return {"topic": "Error", "title": "Error", "question": "Error"}


def gen_bullet_points(topic, title, question, amount):
    prompt_template = load_text_file(r"prompts\prompt_bullets.txt")
    if not prompt_template:
        raise ValueError("We do not have a prompt template!")

    formatted_prompt = prompt_template.format(
        language="German",
        topic=topic,
        title=title,
        question=question,
        count=amount,
    )
    messages = [{"role": "user", "content": formatted_prompt}]

    response = call_gpt(messages, use_json=True)
    response_decoded = json.loads(response)
    bulletpoints = response_decoded["bulletpoints"]
    return bulletpoints


def expand_bullet_point(bulletpoint):
    if not bulletpoint:
        return "# ERROR"
    expand_prompt = load_text_file(r"prompts\prompt_extend_w_data.txt")
    websites = google_search_links(bulletpoint)
    links = extract_links(websites)[1]
    materials = link_to_data(links)
    formatted_prompt = expand_prompt.format(bulletpoint=bulletpoint, materials=materials)
    messages = []
    messages.append({"role": "user", "content": formatted_prompt})
    text = call_gpt(messages)
    if not text:
        return "Error: GPT response is empty"
    return text


def write_intro(topic, bulletpoints):
    prompt_intro = load_text_file(r"prompts\prompt_intro.txt")
    formatted_prompt = prompt_intro.format(topic=topic, bulletpoints=bulletpoints)
    messages = []
    messages.append({"role": "user", "content": formatted_prompt})
    text = call_gpt(messages)
    if not text:
        return "Error: GPT intro response is empty"
    return text


def write_conclusion(topic, bulletpoints):
    prompt_conclusion = load_text_file(r"prompts\prompt_conclusion.txt")
    formatted_prompt = prompt_conclusion.format(topic=topic, bulletpoints=bulletpoints)
    messages = []
    messages.append({"role": "user", "content": formatted_prompt})
    text = call_gpt(messages)
    if not text:
        return "Error: GPT conclusion response is empty"
    return text


def write_full_paper(user_input):
    paper_details = extract(user_input)
    topic, title, question = (
        paper_details["topic"],
        paper_details["title"],
        paper_details["question"],
    )
    amount = random.randint(4, 6)

    bulletpoints = gen_bullet_points(topic, title, question, amount)

    if not bulletpoints:
        raise ValueError("Failed to generate bullet points.")

    intro_text = write_intro(topic, bulletpoints)
    conclusion_text = write_conclusion(topic, bulletpoints)

    output_lines = []
    output_lines.append(f"# Title: {title}\n")
    output_lines.append(f"## {intro_text}\n")

    for index, bulletpoint in enumerate(bulletpoints, start=1):
        expanded = expand_bullet_point(bulletpoint)
        output_lines.append(f"## Kapitel {index}: {expanded}\n")

    output_lines.append(f"## {conclusion_text}\n")

    return "\n".join(output_lines)



user_input = "Influencer Marketing"
prompt_bullets = load_text_file(r"prompts\prompt_bullets.txt")
write_full_paper(user_input)
paper = write_full_paper(user_input)
print(paper)