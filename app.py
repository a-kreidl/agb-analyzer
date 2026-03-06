import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import fitz  # pymupdf

load_dotenv()
client = Anthropic()

st.title("AGB Analyzer")
st.write("Lade eine AGB als Textdatei hoch oder gib eine URL ein.")

option = st.radio("Eingabemethode", ["Datei hochladen", "URL eingeben"])

text = ""

if option == "Datei hochladen":
    uploaded_file = st.file_uploader("AGB hochladen", type=["txt", "pdf"])
    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            text = ""
            for page in pdf:
                text += page.get_text()
            st.success("PDF erfolgreich geladen!")
        else:
            text = uploaded_file.read().decode("utf-8")
            st.success("Datei erfolgreich geladen!")

elif option == "URL eingeben":
    url = st.text_input("URL der AGB")
    if url:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            st.success("Seite erfolgreich geladen!")
        except Exception as e:
            st.error(f"Fehler beim Laden der URL: {e}")

if text:
    if st.button("AGB analysieren"):
        with st.spinner("Analyse läuft..."):
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": f"""Analysiere diese AGB und prüfe auf problematische Klauseln.

Gib deine Antwort GENAU in diesem Format aus, eine Klausel pro Zeile:
ROT: [Klausel] | [kurze Begründung]
GELB: [Klausel] | [kurze Begründung]
GRÜN: [Aspekt] | [kurze Begründung]

Analysiere mindestens 5 Punkte. Sei präzise und juristisch korrekt.

AGB:
{text}"""}
                ]
            )

            result = message.content[0].text
            lines = result.strip().split("\n")

            has_results = any(
                line.startswith("ROT:") or line.startswith("GELB:") or line.startswith("GRÜN:")
                for line in lines
            )

            if not has_results:
                st.warning("⚠️ Die vorliegenden Daten entsprechen nicht den rechtlichen Vorgaben für AGB und können daher nicht analysiert werden.")
            else:
                st.subheader("Auswertung")
                for line in lines:
                    if line.startswith("ROT:"):
                        content = line[4:].strip()
                    elif line.startswith("GELB:"):
                        content = line[5:].strip()
                    elif line.startswith("GRÜN:"):
                        content = line[5:].strip()
                    else:
                        content = None

                    if content:
                        # BGB Paragraphen erkennen z.B. § 307, § 308
                        import re
                        def make_bgb_links(text):
                            def replace_paragraph(match):
                                para = match.group(1)
                                url = f"https://www.gesetze-im-internet.de/bgb/__{para}.html"
                                return f'<a href="{url}" target="_blank">§ {para} BGB</a>'
                            return re.sub(r'§\s*(\d+)\s*BGB', replace_paragraph, text)

                        linked = make_bgb_links(content)

                        if line.startswith("ROT:"):
                            st.markdown(f'<div style="background:#ffd7d7;padding:10px;border-radius:5px;margin:4px 0">🔴 {linked}</div>', unsafe_allow_html=True)
                        elif line.startswith("GELB:"):
                            st.markdown(f'<div style="background:#fff3cd;padding:10px;border-radius:5px;margin:4px 0">🟡 {linked}</div>', unsafe_allow_html=True)
                        elif line.startswith("GRÜN:"):
                            st.markdown(f'<div style="background:#d4edda;padding:10px;border-radius:5px;margin:4px 0">🟢 {linked}</div>', unsafe_allow_html=True)
                    elif line.strip():
                        st.write(line)