import base64
import html
import io

import pandas as pd
from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Générateur de CV", page_icon="📄", layout="wide")

# ---------- Couleurs disponibles ----------
PALETTE = {
    "blue": "#1f4e79",
    "green": "#1b7f5c",
    "burgundy": "#8e2a3c",
    "purple": "#5b3f9a",
    "orange": "#d9622b",
    "slate": "#2b3a4a",
}

# ---------- Textes de l'interface et du CV ----------
T = {
    "fr": {
        "dir": "ltr",
        "app_title": "Générateur de CV",
        "template": "Modèle",
        "tpl_modern": "Moderne",
        "tpl_classic": "Classique",
        "color": "Couleur du CV",
        "custom_color": "Choisir une couleur",
        "colors": {
            "blue": "Bleu", "green": "Vert", "burgundy": "Bordeaux",
            "purple": "Violet", "orange": "Orange", "slate": "Ardoise",
            "custom": "Personnalisée",
        },
        "photo": "Photo (facultatif)",
        "photo_help": "Formats JPG ou PNG. La photo est recadrée en carré automatiquement.",
        "full_name": "Nom complet",
        "job": "Titre professionnel",
        "email": "Email",
        "phone": "Téléphone",
        "city": "Ville",
        "summary": "Profil (2-3 phrases)",
        "profile_title": "Profil",
        "contact_title": "Contact",
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
        "template": "القالب",
        "tpl_modern": "عصري",
        "tpl_classic": "كلاسيكي",
        "color": "لون السيرة",
        "custom_color": "اختر لوناً",
        "colors": {
            "blue": "أزرق", "green": "أخضر", "burgundy": "عنابي",
            "purple": "بنفسجي", "orange": "برتقالي", "slate": "رمادي داكن",
            "custom": "لون مخصص",
        },
        "photo": "الصورة (اختياري)",
        "photo_help": "صيغة JPG أو PNG. يتم قص الصورة تلقائياً على شكل مربع.",
        "full_name": "الاسم الكامل",
        "job": "المسمى الوظيفي",
        "email": "البريد الإلكتروني",
        "phone": "الهاتف",
        "city": "المدينة",
        "summary": "نبذة عنك (جملتان أو ثلاث)",
        "profile_title": "نبذة",
        "contact_title": "التواصل",
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

FONTS = "'Amiri', 'Noto Naskh Arabic', 'Segoe UI', Arial, sans-serif"


# ---------- Fonctions utilitaires ----------
def esc(value) -> str:
    return html.escape(str(value or "").strip()).replace("\n", "<br>")


def non_empty_rows(df: pd.DataFrame):
    df = df.fillna("")
    return [r for _, r in df.iterrows() if any(str(v).strip() for v in r.values)]


def lines(text: str):
    return [l.strip() for l in (text or "").splitlines() if l.strip()]


def text_on(hex_color: str) -> str:
    """Blanc sur fond foncé, noir sur fond clair (pour que le texte reste lisible)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#ffffff" if (0.299 * r + 0.587 * g + 0.114 * b) < 160 else "#1a1a1a"


def process_photo(uploaded) -> str:
    """Recadre en carré, redimensionne, compresse et renvoie une image intégrable (data URI).
    La photo reste en mémoire : rien n'est enregistré sur le serveur."""
    if uploaded is None:
        return ""
    try:
        img = Image.open(uploaded)
        img = ImageOps.exif_transpose(img)  # corrige l'orientation des photos de téléphone
        img = img.convert("RGB")
        img = ImageOps.fit(img, (400, 400), method=Image.LANCZOS, centering=(0.5, 0.4))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


# ---------- Construction du CV ----------
def build_html(t: dict, d: dict, template: str, color: str, preview: bool = False) -> str:
    rtl = t["dir"] == "rtl"
    start = "right" if rtl else "left"
    lang_code = "ar" if rtl else "fr"

    # Blocs communs aux deux modèles
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

    summary_html = f"<p>{esc(d['summary'])}</p>" if d["summary"].strip() else ""

    if template == "classic":
        contact = " &bull; ".join(
            esc(x) for x in (d["email"], d["phone"], d["city"]) if x and x.strip()
        )
        skills = "".join(f"<li>{esc(s)}</li>" for s in lines(d["skills"]))
        langs = "".join(f"<li>{esc(s)}</li>" for s in lines(d["languages"]))
        photo_tag = f'<img class="photo" src="{d["photo"]}" alt="">' if d["photo"] else ""
        return f"""<!DOCTYPE html>
<html lang="{lang_code}" dir="{t['dir']}">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 15mm; }}
  body {{ font-family: {FONTS}; color: #222; font-size: 11pt; line-height: 1.45; }}
  h1 {{ margin: 0; font-size: 24pt; color: {color}; }}
  .job {{ font-size: 13pt; color: #555; margin-top: 2px; }}
  .contact {{ margin-top: 6px; color: #444; font-size: 10pt; }}
  header {{ border-bottom: 3px solid {color}; padding-bottom: 10px; margin-bottom: 8px; }}
  .head {{ display: flex; align-items: center; gap: 18px; }}
  .photo {{ width: 32mm; height: 32mm; border-radius: 50%; object-fit: cover;
           border: 2px solid {color}; flex-shrink: 0; }}
  h2 {{ font-size: 12pt; text-transform: uppercase; letter-spacing: 1px; color: {color};
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
    <div class="head">
      {photo_tag}
      <div>
        <h1>{esc(d['name'])}</h1>
        <div class="job">{esc(d['job'])}</div>
        <div class="contact">{contact}</div>
      </div>
    </div>
  </header>
  {section(t['profile_title'], summary_html)}
  {section(t['experience'], exp_html)}
  {section(t['education'], edu_html)}
  {section(t['skills_title'], f"<ul>{skills}</ul>" if skills else "")}
  {section(t['languages_title'], f"<ul>{langs}</ul>" if langs else "")}
</body>
</html>"""

    # ----- Modèle moderne : colonne latérale colorée + colonne principale -----
    on = text_on(color)
    line = "rgba(255,255,255,.45)" if on == "#ffffff" else "rgba(0,0,0,.30)"
    pill = "rgba(255,255,255,.18)" if on == "#ffffff" else "rgba(0,0,0,.08)"
    grad_dir = "to left" if rtl else "to right"
    zoom = "body { zoom: 0.7; }" if preview else ""

    photo_block = (
        f'<div class="photo-wrap"><img class="photo" src="{d["photo"]}" alt=""></div>'
        if d["photo"] else ""
    )

    contact_items = ""
    for label, val in ((t["email"], d["email"]), (t["phone"], d["phone"]), (t["city"], d["city"])):
        if val and val.strip():
            contact_items += (
                f'<div class="ci"><span class="label">{esc(label)}</span>{esc(val)}</div>'
            )

    skill_pills = "".join(f'<span class="pill">{esc(s)}</span>' for s in lines(d["skills"]))
    lang_pills = "".join(f'<span class="pill">{esc(s)}</span>' for s in lines(d["languages"]))

    def side_section(title, body):
        return f"<h3>{esc(title)}</h3>{body}" if body else ""

    return f"""<!DOCTYPE html>
<html lang="{lang_code}" dir="{t['dir']}">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 0;
          background: linear-gradient({grad_dir}, {color} 68mm, #ffffff 68mm); }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: {FONTS}; font-size: 10.5pt; line-height: 1.45; color: #222; }}
  {zoom}
  .cv {{ display: flex; width: 210mm; min-height: 296mm; }}
  .side {{ width: 68mm; flex-shrink: 0; background: {color}; color: {on};
          padding: 14mm 8mm; }}
  .main {{ flex: 1; background: #ffffff; padding: 14mm 12mm; }}
  .photo-wrap {{ text-align: center; margin-bottom: 10mm; }}
  .photo {{ width: 38mm; height: 38mm; border-radius: 50%; object-fit: cover;
           border: 3px solid {on}; }}
  .side h3 {{ font-size: 10pt; text-transform: uppercase; letter-spacing: 1.5px;
             border-bottom: 1px solid {line}; padding-bottom: 3px; margin: 14px 0 8px; }}
  .ci {{ margin-bottom: 7px; font-size: 9.5pt; word-wrap: break-word; overflow-wrap: anywhere; }}
  .label {{ display: block; font-size: 7.5pt; text-transform: uppercase;
           letter-spacing: 1px; opacity: .75; }}
  .pill {{ display: inline-block; background: {pill}; border-radius: 10px;
          padding: 2px 9px; margin: 0 3px 5px 3px; font-size: 9.5pt; }}
  h1 {{ margin: 0; font-size: 26pt; line-height: 1.1; color: {color}; }}
  .job {{ font-size: 13pt; color: #666; margin: 4px 0 4px; }}
  .main h2 {{ font-size: 11.5pt; text-transform: uppercase; letter-spacing: 1.5px;
             color: {color}; border-bottom: 2px solid {color};
             padding-bottom: 3px; margin: 16px 0 8px; }}
  .item {{ margin-bottom: 10px; page-break-inside: avoid;
          border-{start}: 3px solid {color}; padding-{start}: 10px; }}
  .row {{ display: flex; justify-content: space-between; gap: 12px; }}
  .muted {{ color: #666; }}
  p {{ margin: 3px 0 0; }}
</style>
</head>
<body>
  <div class="cv">
    <aside class="side">
      {photo_block}
      {side_section(t['contact_title'], contact_items)}
      {side_section(t['skills_title'], skill_pills)}
      {side_section(t['languages_title'], lang_pills)}
    </aside>
    <main class="main">
      <h1>{esc(d['name'])}</h1>
      <div class="job">{esc(d['job'])}</div>
      {section(t['profile_title'], summary_html)}
      {section(t['experience'], exp_html)}
      {section(t['education'], edu_html)}
    </main>
  </div>
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
    o1, o2 = st.columns(2)
    template = o1.radio(
        t["template"], ["modern", "classic"],
        format_func=lambda k: t["tpl_" + k], horizontal=True,
    )
    color_key = o2.selectbox(
        t["color"], list(PALETTE) + ["custom"], format_func=lambda k: t["colors"][k]
    )
    if color_key == "custom":
        color = st.color_picker(t["custom_color"], "#1f4e79")
    else:
        color = PALETTE[color_key]

    uploaded_photo = st.file_uploader(
        t["photo"], type=["jpg", "jpeg", "png"], help=t["photo_help"]
    )
    photo = process_photo(uploaded_photo)
    if photo:
        st.image(photo, width=120)

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
    "photo": photo,
    "name": name, "job": job, "email": email, "phone": phone, "city": city,
    "summary": summary, "experiences": experiences, "education": education,
    "skills": skills, "languages": languages,
}
cv_html = build_html(t, data, template, color)
preview_html = build_html(t, data, template, color, preview=True)

with right:
    st.subheader(t["preview"])
    components.html(
        preview_html, height=840 if template == "modern" else 900, scrolling=True
    )

    st.download_button(t["dl_html"], cv_html, file_name="cv.html", mime="text/html")
    try:
        st.download_button(
            t["dl_pdf"], make_pdf(cv_html), file_name="cv.pdf", mime="application/pdf"
        )
    except Exception:
        st.info(t["pdf_error"])
