from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai
import tempfile
import requests
import json
import os
import random
import http.client


load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GOOGLE_SEARCH_URL = "https://google.serper.dev/search"
client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))


def google_request(question, search_engine="/search"):

    print(f"Requesting links from Google ({search_engine})...")

    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps(
        {
            "q": question,
            "hl": "de",
        }
    )
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    conn.request(
        "POST",
        search_engine,
        payload,
        headers,
    )
    res = conn.getresponse()
    data = res.read()
    data = data.decode("utf-8")

    results = json.loads(data)

    pdf_links = []
    pdf_links = [link for item in results.get("organic", []) if (link := item.get("link")).endswith("pdf")]

    return pdf_links


def extract_pdf_pages(url):

    print("Extracting PDF pages...")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"{type(e).__name__}: {e}")
        return None

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(response.content)
        tmp_file_path = tmp_file.name

    sample_pdf = genai.upload_file(tmp_file_path)
    model = genai.GenerativeModel("gemini-1.5-flash")

    try:
        response = model.generate_content(["Give me a summary of this pdf file.", sample_pdf])
        return response.text
    except Exception as e:
        print(f"{type(e).__name__}: {e}")


def call_gpt(messages, model="gpt-4o-mini", use_json=False):

    print("Calling ChatGPT...")

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

        raise ValueError("GPT response is None!")  # FIXME
    except Exception as e:
        print(f"Error calling GPT: {e}")
        return None


def load_text_file(path):

    print("Loading text file...")

    try:
        with open(path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Error loading file: {e}")


def extract(user_input, model="gpt-4o-mini"):

    print("Extracting info...")

    messages = [{"role": "user", "content": f"{user_input} \n\nUse JSON, to extract topic, title and question."}]
    response = call_gpt(messages, model=model, use_json=True)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        print("Failed to parse JSON.")
        return {"topic": "Error", "title": "Error", "question": "Error"}


def gen_bullet_points(topic, title, question, amount):

    print("Generating bulletpoints...")

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

    print(f"Expanding bulletpoint ({bulletpoint})...")

    if not bulletpoint:
        raise ValueError("No bulletpoint.")

    expand_prompt = load_text_file(r"prompts\prompt_extend_w_data.txt")

    links = []
    links.extend(google_request(bulletpoint))
    links.extend(google_request(bulletpoint, "/scholar"))

    materials = []
    for link in links:
        result = extract_pdf_pages(link)
        if result:
            materials.extend(result)

    formatted_prompt = expand_prompt.format(bulletpoint=bulletpoint, materials=materials)

    messages = []
    messages.append({"role": "user", "content": formatted_prompt})
    text = call_gpt(messages)

    if not text:
        raise ValueError("! Error: GPT response is empty.")

    return text


def prompted_writing(topic, bulletpoints, path):

    print(f"Writing using prompt ({path})...")

    prompt_intro = load_text_file(f"{path}")
    formatted_prompt = prompt_intro.format(topic=topic, bulletpoints=bulletpoints)

    messages = []
    messages.append({"role": "user", "content": formatted_prompt})

    text = call_gpt(messages)

    if not text:
        raise ValueError("! Error: GPT intro response is empty.")
    return text


def write_full_paper(user_input):

    print("Generating the paper...")

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

    intro_text = prompted_writing(topic, bulletpoints, r"prompts\prompt_intro.txt")
    conclusion_text = prompted_writing(topic, bulletpoints, r"prompts\prompt_conclusion.txt")

    print("Writing the paper (introduction)...")

    output_lines = []
    output_lines.append(f"# Title: {title}\n")
    output_lines.append(f"## {intro_text}\n")

    print("Writing the paper (main part)...")

    for index, bulletpoint in enumerate(bulletpoints, start=1):
        expanded = expand_bullet_point(bulletpoint)
        output_lines.append(f"## Kapitel {index}: {expanded}\n")

    print("Writing the paper (conclusion)...")

    output_lines.append(f"## {conclusion_text}\n")

    return "\n".join(output_lines)


# CALLS:

user_input = "Hallo, ich möchte eine Hausarbeit über das Thema Influencer Marketing schreiben."

prompt_bullets = load_text_file(r"prompts\prompt_bullets.txt")

write_full_paper(user_input)
paper = write_full_paper(user_input)
print(
    """-----------------------------------------
---------- FINISHED SUCCESFULLY ---------
-----------------------------------------"""
)
print(paper)
