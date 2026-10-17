import html
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Générateur de CV", page_icon="📄", layout="wide")

# ---------- Textes de l'interface et du CV ----------
T = {
    "fr": {
        "dir": "ltr",
        "app_title": "Générateur de CV",
        "full_name": "Nom complet",
        "job": "Titre professionnel",
        "email": "Email",
        "phone": "Téléphone",
        "city": "Ville",
        "summary": "Profil (2-3 phrases)",
        "experience": "Expériences professionnelles",
        "education": "Formation",
        "skills": "Compétences (une par ligne)",
        "skills_title": "Compétences",
        "languages": "Langues (une par ligne)",
        "languages_title": "Langues",
        "position": "Poste",
        "company": "Entreprise",
        "period": "Période",
        "description": "Description",
        "diploma": "Diplôme",
        "school": "Établissement",
        "preview": "Aperçu",
        "dl_pdf": "Télécharger en PDF",
        "dl_html": "Télécharger en HTML",
        "pdf_error": "L'export PDF n'est pas disponible sur cette machine (WeasyPrint). "
                     "Télécharge le HTML et imprime-le en PDF depuis ton navigateur.",
    },
    "ar": {
        "dir": "rtl",
        "app_title": "منشئ السيرة الذاتية",
        "full_name": "الاسم الكامل",
        "job": "المسمى الوظيفي",
        "email": "البريد الإلكتروني",
        "phone": "الهاتف",
        "city": "المدينة",
        "summary": "نبذة عنك (جملتان أو ثلاث)",
        "experience": "الخبرات المهنية",
        "education": "التعليم",
        "skills": "المهارات (مهارة في كل سطر)",
        "skills_title": "المهارات",
        "languages": "اللغات (لغة في كل سطر)",
        "languages_title": "اللغات",
        "position": "المنصب",
        "company": "المؤسسة",
        "period": "الفترة",
        "description": "الوصف",
        "diploma": "الشهادة",
        "school": "المؤسسة التعليمية",
        "preview": "المعاينة",
        "dl_pdf": "تحميل PDF",
        "dl_html": "تحميل HTML",
        "pdf_error": "تصدير PDF غير متاح على هذا الجهاز. حمّل ملف HTML واطبعه كـ PDF من المتصفح.",
    },
}

EXP_COLS = ["poste", "entreprise", "periode", "description"]
EDU_COLS = ["diplome", "ecole", "periode"]


# ---------- Fonctions utilitaires ----------
def esc(value) -> str:
    return html.escape(str(value or "").strip()).replace("\n", "<br>")


def non_empty_rows(df: pd.DataFrame):
    df = df.fillna("")
    return [r for _, r in df.iterrows() if any(str(v).strip() for v in r.values)]


def lines(text: str):
    return [l.strip() for l in (text or "").splitlines() if l.strip()]


def build_html(t: dict, d: dict) -> str:
    contact = " &bull; ".join(
        esc(x) for x in (d["email"], d["phone"], d["city"]) if x and x.strip()
    )

    exp_html = ""
    for r in non_empty_rows(d["experiences"]):
        exp_html += f"""
        <div class="item">
          <div class="row"><b>{esc(r['poste'])}</b><span class="muted">{esc(r['periode'])}</span></div>
          <div class="muted">{esc(r['entreprise'])}</div>
          <p>{esc(r['description'])}</p>
        </div>"""

    edu_html = ""
    for r in non_empty_rows(d["education"]):
        edu_html += f"""
        <div class="item">
          <div class="row"><b>{esc(r['diplome'])}</b><span class="muted">{esc(r['periode'])}</span></div>
          <div class="muted">{esc(r['ecole'])}</div>
        </div>"""

    def section(title, body):
        return f"<h2>{esc(title)}</h2>{body}" if body else ""

    skills = "".join(f"<li>{esc(s)}</li>" for s in lines(d["skills"]))
    langs = "".join(f"<li>{esc(s)}</li>" for s in lines(d["languages"]))

    return f"""<!DOCTYPE html>
<html lang="{'ar' if t['dir'] == 'rtl' else 'fr'}" dir="{t['dir']}">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 15mm; }}
  body {{ font-family: 'Amiri', 'Noto Naskh Arabic', 'Segoe UI', Arial, sans-serif;
         color: #222; font-size: 11pt; line-height: 1.45; }}
  h1 {{ margin: 0; font-size: 24pt; color: #1f3a5f; }}
  .job {{ font-size: 13pt; color: #555; margin-top: 2px; }}
  .contact {{ margin-top: 6px; color: #444; font-size: 10pt; }}
  header {{ border-bottom: 3px solid #1f3a5f; padding-bottom: 10px; margin-bottom: 8px; }}
  h2 {{ font-size: 12pt; text-transform: uppercase; letter-spacing: 1px; color: #1f3a5f;
       border-bottom: 1px solid #ccc; padding-bottom: 3px; margin: 16px 0 8px; }}
  .item {{ margin-bottom: 10px; page-break-inside: avoid; }}
  .row {{ display: flex; justify-content: space-between; gap: 12px; }}
  .muted {{ color: #666; }}
  p {{ margin: 3px 0 0; }}
  ul {{ margin: 0; padding-inline-start: 18px; columns: 2; }}
</style>
</head>
<body>
  <header>
    <h1>{esc(d['name'])}</h1>
    <div class="job">{esc(d['job'])}</div>
    <div class="contact">{contact}</div>
  </header>
  {section({'fr': 'Profil', 'ar': 'نبذة'}[d['lang']], f"<p>{esc(d['summary'])}</p>" if d['summary'].strip() else "")}
  {section(t['experience'], exp_html)}
  {section(t['education'], edu_html)}
  {section(t['skills_title'], f"<ul>{skills}</ul>" if skills else "")}
  {section(t['languages_title'], f"<ul>{langs}</ul>" if langs else "")}
</body>
</html>"""


def make_pdf(html_str: str) -> bytes:
    from weasyprint import HTML  # import ici : l'app marche même sans WeasyPrint
    return HTML(string=html_str).write_pdf()


# ---------- Interface ----------
lang_label = st.sidebar.radio("Langue du CV / لغة السيرة", ["Français", "العربية"])
lang = "fr" if lang_label == "Français" else "ar"
t = T[lang]

st.title(f"📄 {t['app_title']}")
left, right = st.columns([1, 1], gap="large")

with left:
    name = st.text_input(t["full_name"])
    job = st.text_input(t["job"])
    c1, c2, c3 = st.columns(3)
    email = c1.text_input(t["email"])
    phone = c2.text_input(t["phone"])
    city = c3.text_input(t["city"])
    summary = st.text_area(t["summary"], height=100)

    st.subheader(t["experience"])
    experiences = st.data_editor(
        pd.DataFrame(columns=EXP_COLS),
        num_rows="dynamic",
        use_container_width=True,
        key="exp",
        column_config={
            "poste": t["position"],
            "entreprise": t["company"],
            "periode": t["period"],
            "description": t["description"],
        },
    )

    st.subheader(t["education"])
    education = st.data_editor(
        pd.DataFrame(columns=EDU_COLS),
        num_rows="dynamic",
        use_container_width=True,
        key="edu",
        column_config={
            "diplome": t["diploma"],
            "ecole": t["school"],
            "periode": t["period"],
        },
    )

    skills = st.text_area(t["skills"], height=100)
    languages = st.text_area(t["languages"], height=80)

data = {
    "lang": lang,
    "name": name, "job": job, "email": email, "phone": phone, "city": city,
    "summary": summary, "experiences": experiences, "education": education,
    "skills": skills, "languages": languages,
}
cv_html = build_html(t, data)

with right:
    st.subheader(t["preview"])
    components.html(cv_html, height=900, scrolling=True)

    st.download_button(t["dl_html"], cv_html, file_name="cv.html", mime="text/html")
    try:
        st.download_button(
            t["dl_pdf"], make_pdf(cv_html), file_name="cv.pdf", mime="application/pdf"
        )
    except Exception:
        st.info(t["pdf_error"])
