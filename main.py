from dotenv import load_dotenv
from openai import OpenAI
from sqlite import DataBase
import google.generativeai as genai
import tempfile
import requests
import json
import os
import random
import http.client


global db
db = DataBase("db.db")


load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GOOGLE_SEARCH_URL = "https://google.serper.dev/search"
client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))


def google_request(question, search_engine="/search"):

    print(f"⚪ Requesting links from Google ({search_engine})...")

    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps(
        {
            "q": question,
            "hl": "de",
            "page": 10,
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

    print("⚪ Extracting PDF pages...")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"🟠 {type(e).__name__}: {e}")
        return None

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(response.content)
        tmp_file_path = tmp_file.name

    sample_pdf = genai.upload_file(tmp_file_path)
    model = genai.GenerativeModel("gemini-1.5-flash")

    try:
        response = model.generate_content(["Summarize the content of this file, extract valueable information.", sample_pdf])
        return response.text
    except Exception as e:
        print(f"🟠 {type(e).__name__}: {e}")


def call_gpt(messages, model="gpt-4o-mini", use_json=False):

    print("⚪ Calling ChatGPT...")

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
        print(f"🔴 Error calling GPT: {e}")
        return None


def load_text_file(path):

    print("⚪ Loading text file...")

    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"🔴 Error loading file: {e}")


def append_text_file(file_path, text):
    try:
        with open(file_path, "a", encoding="utf-8") as file:
            file.writelines(f"{text}\n")
    except Exception as e:
        print(f"🔴 Error appending file: {e}")


def create_text_file(path, name, title):
    try:
        with open(rf"{path}\{name}.txt", "x", encoding="utf-8") as file:
            file.write(f"{title}")
    except Exception as e:
        print(f"🔴 Error creating file: {e}")


def extract(user_input, model="gpt-4o-mini"):

    print("⚪ Extracting info...")

    messages = [{"role": "user", "content": f"{user_input} \n\nUse JSON, to extract topic, title and question. They must now contain any quotes."}]
    response = call_gpt(messages, model=model, use_json=True)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        print("🔴 Failed to parse JSON.")
        return {"topic": "Error", "title": "Error", "question": "Error"}


def gen_bullet_points(topic, title, question, amount, prompt):

    prompt = str(prompt)

    print(f"🔵 Generating {amount} bulletpoints...")

    if not prompt:
        raise ValueError("We do not have a prompt template!")

    formatted_prompt = prompt.format(
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
    if not bulletpoints:
        raise ("No bulletpoints generated.")
    return bulletpoints


def expand_bullet_point(bulletpoint, prompt, sources, complete_source_ids):

    if not bulletpoint:
        raise ValueError("No bulletpoint.")

    print(f"🔵 Expanding bulletpoint ({bulletpoint})...")

    db.move_to_sheet("sources")

    materials = []

    for link in sources:
        result = extract_pdf_pages(link)
        if result:

            materials.extend(result)

            if db.check_if_exists("link", link) == False:
                db.insert(["link", "summary"], [link, result])
                source_id = db.get_element("link", link, "id")
            else:
                source_id = db.get_element("link", link, "id")
                print(f"⚫ Inserting duplicate source prevented! (id: {source_id})")

            if complete_source_ids:
                complete_source_ids = f"{complete_source_ids}, {source_id}"
            else:
                complete_source_ids = source_id

    formatted_prompt = prompt.format(bulletpoint=bulletpoint, materials=materials)

    messages = []
    messages.append({"role": "user", "content": formatted_prompt})
    text = call_gpt(messages)
    return text, str(complete_source_ids)


def prompted_writing(topic, bulletpoints, prompt):

    print(f"⚪ Writing using prompt...")

    formatted_prompt = prompt.format(topic=topic, bulletpoints=bulletpoints)

    messages = []
    messages.append({"role": "user", "content": formatted_prompt})

    text = call_gpt(messages)

    if not text:
        raise ValueError("Error: GPT intro response is empty.")
    return text


def load_prompts(directory):
    prompts = {}
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            promptname = filename.split(".")[0]
            prompts[promptname] = load_text_file(file_path)
        except Exception as e:
            print(f"🔴 Error reading {file_path}: {e}")
    return prompts


def write_full_paper(user_input, request_id, prompts):

    print("🟢 Generating paper info...")

    paper_details = extract(user_input)
    topic, title, question = (
        paper_details["topic"],
        paper_details["title"],
        paper_details["question"],
    )

    db.move_to_sheet("papers")
    db.update("topic", topic, "id", request_id)
    db.update("title", title, "id", request_id)
    db.update("question", question, "id", request_id)

    intro_prompt = prompts["prompt_intro"]
    conclusion_prompt = prompts["prompt_conclusion"]
    creating_bullets_prompt = prompts["prompt_bullets"]
    expanding_bullets_prompt = prompts["prompt_extend_w_data"]

    bulletpoint_amount = random.randint(7, 10)
    bulletpoints = gen_bullet_points(topic, title, question, bulletpoint_amount, creating_bullets_prompt)

    if not bulletpoints:
        raise ValueError("Failed to generate bullet points.")

    str_bulletpoints = ""
    for bulletpoint in bulletpoints:
        str_bulletpoints = f"{str_bulletpoints} - {bulletpoint}"

    print("🟢 Writing the paper (introduction)...")

    intro_text = prompted_writing(topic, bulletpoints, intro_prompt)

    db.move_to_sheet("chapters")
    db.insert(
        [
            "text_part",
            "chapter_title",
            "text",
            "source_ids",
        ],
        [
            "1.",
            "Introduction.",
            intro_text,
            "",
        ],
    )

    components_ids = ""
    formatted_component_id = db.get_element("text", intro_text, "id")
    components_ids += formatted_component_id

    print("🟢 Writing the paper (main part)...")

    for index, bulletpoint in enumerate(bulletpoints, start=1):

        db.move_to_sheet("sources")

        question = f"{topic}: {bulletpoint}"

        sources = []
        sources_ids = ""
        sources.extend(google_request(question))
        sources.extend(google_request(question, "/scholar"))

        expanded_bullet_point, sources_ids = expand_bullet_point(bulletpoint, expanding_bullets_prompt, sources, sources_ids)

        db.move_to_sheet("chapters")
        db.insert(
            [
                "text_part",
                "chapter_title",
                "text",
                "source_ids",
            ],
            [
                f"{index + 1}.",
                bulletpoint,
                expanded_bullet_point,
                sources_ids,
            ],
        )

        components_ids += f", {db.get_element('text', expanded_bullet_point, 'id')}"

    print("🟢 Writing the paper (conclusion)...")

    conclusion_text = prompted_writing(topic, bulletpoints, conclusion_prompt)

    db.insert(
        [
            "text_part",
            "chapter_title",
            "text",
            "source_ids",
        ],
        [
            f"{len(bulletpoints) + 2}.",
            "Conclusion.",
            conclusion_text,
            "",
        ],
    )

    components_ids += f", {db.get_element('text', conclusion_text, 'id')}"

    db.move_to_sheet("papers")
    db.update("chapter_ids", components_ids, "id", request_id)

    return None


def compose_text_paper(request_id):

    # - - - - - - - VOCABULARY - - - - - - -

    file_name = f"paper{request_id}"
    file_full_path = rf"papers\{file_name}.txt"

    # - - - - - - - FILE WRITING - - - - - - -

    db.move_to_sheet("papers")
    title = db.get_element("id", request_id, "title")
    formatted_title = title.replace("'", "")

    create_text_file("papers", file_name, f"# {formatted_title}\n")

    chapter_ids = [int(chapter_id.strip().replace("'", "")) for chapter_id in db.get_element("id", request_id, "chapter_ids").split(", ")]

    db.move_to_sheet("chapters")

    # Introduction

    introduction = db.get_element("id", chapter_ids[0], "text")
    clean_intro = introduction.replace("'", "").replace("\\n", "\n")
    formatted_introduction = clean_intro.splitlines()

    append_text_file(file_full_path, f"## {formatted_introduction[0]}")
    for line in formatted_introduction[1:]:
        append_text_file(file_full_path, f"{line}")

    # Main part

    for index, chapter_id in enumerate(chapter_ids[1:-1], start=1):

        chapter_content = db.get_element("id", chapter_id, "text")
        clean_content = chapter_content.replace("'", "").replace("\\n", "\n")
        formatted_chapter_content = clean_content.splitlines()

        append_text_file(file_full_path, f"## Kapitel {index}: {formatted_chapter_content[0]}")
        for line in formatted_chapter_content[1:]:
            append_text_file(file_full_path, f"{line}")

    # Conclusion

    conclusion = db.get_element("id", chapter_ids[-1], "text")
    clean_conclusion = conclusion.replace("'", "").replace("\\n", "\n")
    formatted_conclusion = clean_conclusion.splitlines()

    append_text_file(file_full_path, f"## {formatted_conclusion[0]}")
    for line in formatted_conclusion[1:]:
        append_text_file(file_full_path, f"{line}")

    # Sources

    append_text_file(file_full_path, f"## Quellen:")

    source_ids = []

    db.move_to_sheet("chapters")

    for chapter_id in chapter_ids[1:-1]:
        chapter_source_ids = db.get_element("id", chapter_id, "source_ids").replace("'", "")
        try:
            formatted_chapter_sources_ids = [int(link_id.strip()) for link_id in chapter_source_ids.split(", ")]
        except Exception as e:
            print(f"Something's wrong with sources for the {chapter_id} chapter:\n{e}")
        source_ids.extend(formatted_chapter_sources_ids)

    db.move_to_sheet("sources")

    for source in source_ids:
        source_line = f"- {db.get_element('id', source, 'link')}"
        cleaned_source_line = source_line.replace("'", "")
        append_text_file(file_full_path, f"{cleaned_source_line}\n")


# CALLS:

db.move_to_sheet("papers")
user_input = "Hallo, ich möchte eine Hausarbeit über das Thema 'Influencer Marketing' schreiben!"

db.insert(
    [
        "user_input",
        "topic",
        "title",
        "question",
        "chapter_ids",
    ],
    [
        user_input,
        "",
        "",
        "",
        "",
    ],
)

request_id = db.get_last_line_id()

prompts = load_prompts(r"C:\Users\msvre\code\mischa\prompts")
write_full_paper(str(user_input), request_id, prompts)

compose_text_paper(request_id)

print(load_text_file(f"papers/paper{request_id}.txt"))