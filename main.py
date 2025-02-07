from google.genai import types
from dotenv       import load_dotenv
from openai       import OpenAI
from bs4          import BeautifulSoup
from google       import genai
import httpx
import requests
import json
import os
import random
import http.client

load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GOOGLE_SEARCH_URL = "https://google.serper.dev/search"
client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client_genai = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

def google_scholar_search(question):
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({
        "q": question,
        "hl": "de",
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/scholar", payload, headers)
    res = conn.getresponse()
    data = res.read()
    data.decode("utf-8")
    results = json.loads(data.decode("utf-8"))
    pdf_links = []
    for item in results.get("organic", []):
        link = item.get("link")
        if link and link.endswith(".pdf"):
            pdf_links.append(link)
    return pdf_links


def google_search(question):
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({
        "q": question,
        "hl": "de"
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/search", payload, headers)
    res = conn.getresponse()
    data = res.read()
    data.decode("utf-8")
    results = json.loads(data.decode("utf-8"))
    pdf_links = []
    for item in results.get("organic", []):
        link = item.get("link")
        if link and link.endswith(".pdf"):
            pdf_links.append(link)
    return pdf_links


def extract_pdf_pages(path):
    doc_data = httpx.get(path).content
    prompt = "Summarize this document"
    try:
        response = client_genai.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=doc_data,
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )
    except:
        return ""
    else:
        return response.text


def extract_links(google_search):
    links = []
    for result in google_search["organic"]:
        links.append(result["link"])
    return links


def link_to_data(link):
    response = requests.get(link)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()


def call_gpt(messages, model="gpt-4o-mini", use_json=False):
    try:
        response_format = {"type": "json_object"} if use_json else None
        response = client_openai.chat.completions.create(
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
    links = []
    links.extend(google_search(bulletpoint))
    links.extend(google_scholar_search(bulletpoint))
    materials = []
    for link in links:
        materials.extend(extract_pdf_pages(link))
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


user_input = 'Hallo, ich möchte eine Hausarbeit über das Thema Influencer Marketing schreiben.'
prompt_bullets = load_text_file(r"prompts\prompt_bullets.txt")
write_full_paper(user_input)
paper = write_full_paper(user_input)
print(paper)