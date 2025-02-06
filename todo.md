## 1. Prompt Engineering

Schreibe eine Prompt, um aus einer Kundenanfrage strukturierten Input für unser Programm per ChatGPT zu extrahieren.
Am Ende sollen Titel, Thema, und Forschungsfrage nutzbar sein.

### Kundenanfrage:

- Hallo, ich möchte eine Hausarbeit über das Thema Influencer Marketing schreiben.

- Hi, please write a bachelors thesis with the title "Influencer Marketing" and the research question "How influencer marketing is changing business?"

### Antwort:

You will be given an user request. You should output me three variables: title, topic and question. If something is missing, you should make the variable up, but still connected to the generl topic of the request. Make your output in german, even if it's written in another language.
User request: *user request*.

## 2. Python Implementation

Jetzt ist die Frage wie man das in Python umsetzt.

- Nutze die OpenAI API und schreibe eine einfache Funktion um GPT Input zu geben und Output zu erhalten.

```python
def call_gpt(input):
    ...
    return output
```

- Dann brauchst du eine Funktion, um Titel, Thema, und Forschungsfrage zu extrahieren.

```python
def extract(input):
    output = call_gpt(input)
    ...
    return topic, title, question
```

## 3. Application

Nun können wir aus dem Thema eine Arbeit schreiben.
Um mehr in die Tiefe zu gehen und besser als nur GPT zu schreiben, ist es gut iterativ aus Stichpunkten einen Fließtext zu generieren.

- Schreibe eine Funktion um in Schleife aus dem Thema Stichpunkte zu schreiben und aus diesen Stichpunkten die volle Arbeit.

```python
def write(topic, title, question):
    bullet_points = call_gpt()
    ...
    for item in bullet_points:
        text = call_gpt()
        ...
    return paper
```