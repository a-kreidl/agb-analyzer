import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import fitz  # pymupdf

load_dotenv()
client = Anthropic()

PLAYBOOK = """
Du bist ein juristischer Experte für deutsches AGB-Recht mit Fokus auf Online-Geschäfte und digitale Dienste.

Prüfe die AGB nach folgenden Kategorien und verwende ausschließlich dieses Ampelsystem:
- ROT: Klausel fehlt komplett (Pflichtangabe) ODER ist nach AGB-Recht absolut unzulässig
- GELB: Klausel vorhanden, greift aber unangemessen in Verbraucherrechte ein, ist ungewöhnlich oder problematisch
- GRÜN: Klausel rechtlich konform, entspricht gesetzlichen Mustern (z.B. gesetzliche Widerrufsbelehrung)

Prüfkategorien:

1. HAFTUNGSBESCHRÄNKUNGEN (§§ 307-309 BGB)
   - ROT: Ausschluss der Haftung für Vorsatz, grobe Fahrlässigkeit oder Schäden an Leben, Körper, Gesundheit
   - GELB: Beschränkung von Kardinalpflichten oder unklare Formulierungen
   - GRÜN: Zulässige Haftungsbeschränkung für leichte Fahrlässigkeit bei nicht-wesentlichen Pflichten

2. GEWÄHRLEISTUNG/MÄNGELHAFTUNG
   - ROT: Vollständiger Ausschluss der Gewährleistung gegenüber Verbrauchern
   - GELB: Einschränkung der Gewährleistung ohne klare Begründung
   - GRÜN: Gesetzliche Gewährleistungsrechte werden korrekt benannt

3. WIDERRUFSBELEHRUNG
   - ROT: Fehlt komplett
   - GELB: Vorhanden aber unvollständig oder fehlerhaft
   - GRÜN: Entspricht dem gesetzlichen Muster gemäß Anlage 1 zu Art. 246a § 1 Abs. 2 EGBGB

4. EIGENTUMSVORBEHALT
   - ROT: Fehlt bei Warenlieferung komplett
   - GELB: Erweiterter Eigentumsvorbehalt ohne klare Formulierung
   - GRÜN: Einfacher Eigentumsvorbehalt nach IHK-Muster korrekt formuliert

5. LIEFERUNG UND ZAHLUNG
   - ROT: Keine Angaben zu Lieferfristen oder nur unverbindliche Angaben wie "in der Regel"
   - GELB: Lieferfristen vorhanden aber unzureichend präzise
   - GRÜN: Konkrete Lieferfristen mit Höchstfrist angegeben (z.B. "ca. 5-7 Tage")

6. VERSANDKOSTEN
   - ROT: Versandkosten nur in AGB versteckt, nicht am Produkt ausgewiesen
   - GELB: Versandkosten-Staffelung unklar oder Auslandsversand nicht aufgeschlüsselt
   - GRÜN: Versandkosten transparent und vollständig angegeben

7. ZAHLUNGSBEDINGUNGEN
   - ROT: Unzulässige Zusatzkosten für Zahlungsarten ohne kostenlose Alternative
   - GELB: Zahlungsbedingungen unklar oder eingeschränkte Auswahl ohne Begründung
   - GRÜN: Zahlungsarten klar benannt, Zusatzkosten transparent und zulässig

8. GERICHTSSTAND UND RECHTSWAHL
   - ROT: Ausschließlicher Gerichtsstand zum Nachteil des Verbrauchers
   - GELB: Ausländisches Recht gewählt – Verbraucher könnte benachteiligt werden
   - GRÜN: Deutsches Recht, zulässiger Gerichtsstand

9. VERTRAGSSTRAFE
   - ROT: Vertragsstrafe gegenüber Verbrauchern in AGB vereinbart (§ 309 Nr. 6 BGB)
   - GELB: Vertragsstrafe im B2B-Bereich mit unangemessener Höhe
   - GRÜN: Keine Vertragsstrafe vorhanden

10. TRANSPARENZGEBOT (§ 307 I 2 BGB)
    - ROT: Wesentliche Klauseln völlig unklar oder widersprüchlich
    - GELB: Einzelne Klauseln schwer verständlich oder mehrdeutig
    - GRÜN: Klauseln klar, verständlich und widerspruchsfrei

11. ÜBERRASCHENDE KLAUSELN (§ 305c BGB)
    - ROT: Klauseln die der Verbraucher bei diesem Vertragstyp absolut nicht erwarten muss
    - GELB: Ungewöhnliche Klauseln die zumindest erklärungsbedürftig sind
    - GRÜN: Keine überraschenden Klauseln vorhanden

12. VERBRAUCHERSCHLICHTUNG
    - ROT: Kein Hinweis auf Streitbeilegung / OS-Plattform trotz B2C-Geschäft
    - GELB: Hinweis vorhanden aber unvollständig
    - GRÜN: Vollständiger Hinweis auf Streitbeilegung und OS-Plattform

Gib deine Antwort AUSSCHLIESSLICH in diesem Format aus, eine Klausel pro Zeile:
ROT: [Kategorie] | [Befund und Begründung mit BGB-Paragraph wenn relevant]
GELB: [Kategorie] | [Befund und Begründung mit BGB-Paragraph wenn relevant]
GRÜN: [Kategorie] | [Befund und Begründung mit BGB-Paragraph wenn relevant]

Prüfe alle 12 Kategorien. Wenn eine Kategorie nicht relevant ist (z.B. Eigentumsvorbehalt bei reinen Dienstleistungen), lass sie weg.
Keine Einleitung, keine Zusammenfassung, nur die Ampelzeilen.
"""

st.title("AGB Analyzer")
st.write("Lade eine AGB als Textdatei oder PDF hoch, oder gib eine URL ein.")

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
                    {"role": "user", "content": f"{PLAYBOOK}\n\nAGB:\n{text}"}
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
                import re
                def make_bgb_links(text):
                    def replace_paragraph(match):
                        para = match.group(1)
                        url = f"https://www.gesetze-im-internet.de/bgb/__{para}.html"
                        return f'<a href="{url}" target="_blank">§ {para} BGB</a>'
                    return re.sub(r'§\s*(\d+)\s*BGB', replace_paragraph, text)

                rot = [l for l in lines if l.startswith("ROT:")]
                gelb = [l for l in lines if l.startswith("GELB:")]
                gruen = [l for l in lines if l.startswith("GRÜN:")]

                st.subheader("Auswertung")

                if rot:
                    st.markdown("### 🔴 Kritisch")
                    for line in rot:
                        content = make_bgb_links(line[4:].strip())
                        st.markdown(f'<div style="background:#ffd7d7;padding:10px;border-radius:5px;margin:4px 0">{content}</div>', unsafe_allow_html=True)

                if gelb:
                    st.markdown("### 🟡 Auffällig")
                    for line in gelb:
                        content = make_bgb_links(line[5:].strip())
                        st.markdown(f'<div style="background:#fff3cd;padding:10px;border-radius:5px;margin:4px 0">{content}</div>', unsafe_allow_html=True)

                if gruen:
                    st.markdown("### 🟢 Konform")
                    for line in gruen:
                        content = make_bgb_links(line[5:].strip())
                        st.markdown(f'<div style="background:#d4edda;padding:10px;border-radius:5px;margin:4px 0">{content}</div>', unsafe_allow_html=True)

                total = len(rot) + len(gelb) + len(gruen)
                st.markdown("---")
                st.markdown(f"**Zusammenfassung:** {len(rot)} kritisch · {len(gelb)} auffällig · {len(gruen)} konform · {total} geprüft")