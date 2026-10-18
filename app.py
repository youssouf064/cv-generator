import base64
import datetime
import html
import io
import json
import re
from urllib.parse import quote

import pandas as pd
from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Générateur de CV", page_icon="📄", layout="wide")


# =====================================================================
#  Réglages (secrets Streamlit)
#  Dans Streamlit Cloud : Manage app > Settings > Secrets, par exemple :
#      access_codes = ["MAURI-1234", "MAURI-5678"]
#      payment_info = "Paye 200 MRU par Bankily au 22 00 00 00 puis envoie la preuve sur WhatsApp."
#      app_url = "https://ton-app.streamlit.app"
#  Sans "access_codes", l'app reste 100 % gratuite et sans filigrane.
# =====================================================================
def secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


_codes = secret("access_codes", [])
if isinstance(_codes, str):
    _codes = [_codes]
ACCESS_CODES = [str(c).strip() for c in (_codes or []) if str(c).strip()]
APP_URL = str(secret("app_url", "") or "")
PAYMENT_INFO = str(secret("payment_info", "") or "")


# =====================================================================
#  Constantes
# =====================================================================
PALETTE = {
    "blue": "#1f4e79",
    "green": "#1b7f5c",
    "burgundy": "#8e2a3c",
    "purple": "#5b3f9a",
    "orange": "#d9622b",
    "slate": "#2b3a4a",
}
COLOR_KEYS = list(PALETTE) + ["custom"]
TEMPLATES = ["modern", "classic", "banner"]
LANG_LABELS = {"Français": "fr", "English": "en", "العربية": "ar"}

EXP_COLS = ["poste", "entreprise", "periode", "description"]
EDU_COLS = ["diplome", "ecole", "periode"]
CERT_COLS = ["titre", "organisme", "annee"]
PROJ_COLS = ["nom", "description"]
SKILL_COLS = ["competence", "niveau"]
LANG_COLS = ["langue", "niveau"]
TABLES = {
    "exp": EXP_COLS, "edu": EDU_COLS, "cert": CERT_COLS,
    "proj": PROJ_COLS, "skills": SKILL_COLS, "langs": LANG_COLS,
}
FIELDS = ["name", "job", "email", "phone", "city", "summary", "interests", "references"]

FONTS = "'Amiri', 'Noto Naskh Arabic', 'Segoe UI', Arial, sans-serif"
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")
PHOTO_RE = re.compile(r"data:image/jpeg;base64,[A-Za-z0-9+/=]+")


# =====================================================================
#  Textes (interface + CV)
# =====================================================================
T = {
    "fr": {
        "dir": "ltr", "lang_code": "fr",
        "app_title": "Générateur de CV",
        "tab_form": "1. Mon CV", "tab_preview": "2. Aperçu et téléchargement",
        "tab_letter": "3. Lettre de motivation",
        "template": "Modèle", "tpl_modern": "Moderne", "tpl_classic": "Classique",
        "tpl_banner": "Bandeau",
        "color": "Couleur du CV", "custom_color": "Choisir une couleur",
        "colors": {"blue": "Bleu", "green": "Vert", "burgundy": "Bordeaux",
                   "purple": "Violet", "orange": "Orange", "slate": "Ardoise",
                   "custom": "Personnalisée"},
        "example_btn": "Remplir avec un exemple", "clear_btn": "Tout effacer",
        "photo": "Photo (facultatif)",
        "photo_help": "Formats JPG ou PNG. La photo est recadrée en carré automatiquement.",
        "remove_photo": "Retirer la photo",
        "full_name": "Nom complet", "job": "Titre professionnel",
        "job_ph": "Ex. Assistant administratif",
        "job_help": "Le poste que tu vises, en 2 à 6 mots.",
        "email": "Email", "phone": "Téléphone", "city": "Ville",
        "summary": "Profil (2-3 phrases)",
        "summary_help": "Présente-toi en 2 ou 3 phrases : ton métier, ton expérience, tes points forts.",
        "profile_title": "Profil", "contact_title": "Contact",
        "experience": "Expériences professionnelles",
        "exp_tip": "Commence par ton poste le plus récent et décris tes missions en une ou deux phrases.",
        "education": "Formation",
        "edu_tip": "Indique ton diplôme le plus élevé en premier.",
        "certs": "Certifications et formations courtes", "certs_title": "Certifications",
        "projects": "Projets", "projects_title": "Projets",
        "skills_label": "Compétences (niveau de 1 à 5)", "skills_title": "Compétences",
        "languages_label": "Langues (niveau de 1 à 5)", "languages_title": "Langues",
        "interests": "Centres d'intérêt (un par ligne)", "interests_title": "Centres d'intérêt",
        "references": "Références", "references_title": "Références",
        "position": "Poste", "company": "Entreprise", "period": "Période",
        "description": "Description", "diploma": "Diplôme", "school": "Établissement",
        "cert_name": "Certification", "cert_org": "Organisme", "year": "Année",
        "proj_name": "Projet", "skill": "Compétence", "language": "Langue", "level": "Niveau",
        "preview": "Aperçu",
        "dl_pdf": "Télécharger en PDF", "dl_html": "Télécharger en HTML",
        "pdf_error": "L'export PDF n'est pas disponible sur cette machine (WeasyPrint). "
                     "Télécharge le HTML et imprime-le en PDF depuis ton navigateur.",
        "wm": "VERSION GRATUITE",
        "code_label": "Code d'accès (retire le filigrane)",
        "code_ok": "Code valide : filigrane retiré.", "code_bad": "Code incorrect.",
        "payment_info": "Pour obtenir un code d'accès et retirer le filigrane, contacte le créateur de l'app.",
        "share_wa": "Partager sur WhatsApp",
        "share_msg": "Crée ton CV gratuitement, en français, anglais ou arabe : {url}",
        "save_btn": "Sauvegarder mon CV (fichier)",
        "load_label": "Recharger un CV sauvegardé", "load_btn": "Charger ce fichier",
        "load_error": "Fichier invalide.",
        "lt_company": "Entreprise ou organisation", "lt_position": "Poste visé",
        "lt_offer": "Offre d'emploi (colle le texte, facultatif)",
        "lt_hint": "Colle l'offre pour que l'app mette en avant les compétences qui correspondent.",
        "lt_generate": "Générer la lettre", "lt_text": "Lettre (tu peux la modifier)",
        "lt_subject": "Objet : Candidature au poste de {position}",
        "dl_letter_pdf": "Télécharger la lettre en PDF",
        "dl_letter_html": "Télécharger la lettre en HTML",
    },
    "en": {
        "dir": "ltr", "lang_code": "en",
        "app_title": "CV Builder",
        "tab_form": "1. My CV", "tab_preview": "2. Preview and download",
        "tab_letter": "3. Cover letter",
        "template": "Template", "tpl_modern": "Modern", "tpl_classic": "Classic",
        "tpl_banner": "Banner",
        "color": "CV color", "custom_color": "Pick a color",
        "colors": {"blue": "Blue", "green": "Green", "burgundy": "Burgundy",
                   "purple": "Purple", "orange": "Orange", "slate": "Slate",
                   "custom": "Custom"},
        "example_btn": "Fill with an example", "clear_btn": "Clear everything",
        "photo": "Photo (optional)",
        "photo_help": "JPG or PNG. The photo is automatically cropped to a square.",
        "remove_photo": "Remove photo",
        "full_name": "Full name", "job": "Professional title",
        "job_ph": "E.g. Administrative Assistant",
        "job_help": "The position you are aiming for, in 2 to 6 words.",
        "email": "Email", "phone": "Phone", "city": "City",
        "summary": "Profile (2-3 sentences)",
        "summary_help": "Introduce yourself in 2 or 3 sentences: your job, experience and strengths.",
        "profile_title": "Profile", "contact_title": "Contact",
        "experience": "Work experience",
        "exp_tip": "Start with your most recent job and describe your duties in one or two sentences.",
        "education": "Education",
        "edu_tip": "List your highest degree first.",
        "certs": "Certifications and short courses", "certs_title": "Certifications",
        "projects": "Projects", "projects_title": "Projects",
        "skills_label": "Skills (level from 1 to 5)", "skills_title": "Skills",
        "languages_label": "Languages (level from 1 to 5)", "languages_title": "Languages",
        "interests": "Interests (one per line)", "interests_title": "Interests",
        "references": "References", "references_title": "References",
        "position": "Position", "company": "Company", "period": "Period",
        "description": "Description", "diploma": "Degree", "school": "School",
        "cert_name": "Certification", "cert_org": "Issuer", "year": "Year",
        "proj_name": "Project", "skill": "Skill", "language": "Language", "level": "Level",
        "preview": "Preview",
        "dl_pdf": "Download as PDF", "dl_html": "Download as HTML",
        "pdf_error": "PDF export is not available on this machine (WeasyPrint). "
                     "Download the HTML and print it to PDF from your browser.",
        "wm": "FREE VERSION",
        "code_label": "Access code (removes the watermark)",
        "code_ok": "Valid code: watermark removed.", "code_bad": "Wrong code.",
        "payment_info": "To get an access code and remove the watermark, contact the app creator.",
        "share_wa": "Share on WhatsApp",
        "share_msg": "Create your CV for free, in French, English or Arabic: {url}",
        "save_btn": "Save my CV (file)",
        "load_label": "Reload a saved CV", "load_btn": "Load this file",
        "load_error": "Invalid file.",
        "lt_company": "Company or organization", "lt_position": "Target position",
        "lt_offer": "Job offer (paste the text, optional)",
        "lt_hint": "Paste the offer so the app highlights the skills that match.",
        "lt_generate": "Generate the letter", "lt_text": "Letter (you can edit it)",
        "lt_subject": "Subject: Application for the position of {position}",
        "dl_letter_pdf": "Download the letter as PDF",
        "dl_letter_html": "Download the letter as HTML",
    },
    "ar": {
        "dir": "rtl", "lang_code": "ar",
        "app_title": "منشئ السيرة الذاتية",
        "tab_form": "1. سيرتي", "tab_preview": "2. المعاينة والتحميل",
        "tab_letter": "3. خطاب التقديم",
        "template": "القالب", "tpl_modern": "عصري", "tpl_classic": "كلاسيكي",
        "tpl_banner": "شريط علوي",
        "color": "لون السيرة", "custom_color": "اختر لوناً",
        "colors": {"blue": "أزرق", "green": "أخضر", "burgundy": "عنابي",
                   "purple": "بنفسجي", "orange": "برتقالي", "slate": "رمادي داكن",
                   "custom": "لون مخصص"},
        "example_btn": "املأ بمثال", "clear_btn": "مسح الكل",
        "photo": "الصورة (اختياري)",
        "photo_help": "صيغة JPG أو PNG. يتم قص الصورة تلقائياً على شكل مربع.",
        "remove_photo": "إزالة الصورة",
        "full_name": "الاسم الكامل", "job": "المسمى الوظيفي",
        "job_ph": "مثال: مساعد إداري",
        "job_help": "الوظيفة التي تستهدفها في بضع كلمات.",
        "email": "البريد الإلكتروني", "phone": "الهاتف", "city": "المدينة",
        "summary": "نبذة عنك (جملتان أو ثلاث)",
        "summary_help": "عرّف بنفسك في جملتين أو ثلاث: مهنتك وخبرتك ونقاط قوتك.",
        "profile_title": "نبذة", "contact_title": "التواصل",
        "experience": "الخبرات المهنية",
        "exp_tip": "ابدأ بآخر وظيفة لك وصف مهامك في جملة أو جملتين.",
        "education": "التعليم",
        "edu_tip": "اذكر أعلى شهادة أولاً.",
        "certs": "الشهادات والدورات القصيرة", "certs_title": "الشهادات",
        "projects": "المشاريع", "projects_title": "المشاريع",
        "skills_label": "المهارات (المستوى من 1 إلى 5)", "skills_title": "المهارات",
        "languages_label": "اللغات (المستوى من 1 إلى 5)", "languages_title": "اللغات",
        "interests": "الاهتمامات (اهتمام في كل سطر)", "interests_title": "الاهتمامات",
        "references": "المراجع", "references_title": "المراجع",
        "position": "المنصب", "company": "المؤسسة", "period": "الفترة",
        "description": "الوصف", "diploma": "الشهادة", "school": "المؤسسة التعليمية",
        "cert_name": "الشهادة", "cert_org": "الجهة", "year": "السنة",
        "proj_name": "المشروع", "skill": "المهارة", "language": "اللغة", "level": "المستوى",
        "preview": "المعاينة",
        "dl_pdf": "تحميل PDF", "dl_html": "تحميل HTML",
        "pdf_error": "تصدير PDF غير متاح على هذا الجهاز. حمّل ملف HTML واطبعه كـ PDF من المتصفح.",
        "wm": "نسخة مجانية",
        "code_label": "رمز الوصول (لإزالة العلامة المائية)",
        "code_ok": "الرمز صحيح: تمت إزالة العلامة المائية.", "code_bad": "الرمز غير صحيح.",
        "payment_info": "للحصول على رمز وصول وإزالة العلامة المائية، تواصل مع صاحب التطبيق.",
        "share_wa": "مشاركة على واتساب",
        "share_msg": "أنشئ سيرتك الذاتية مجاناً بالعربية أو الفرنسية أو الإنجليزية: {url}",
        "save_btn": "حفظ سيرتي (ملف)",
        "load_label": "إعادة تحميل سيرة محفوظة", "load_btn": "تحميل هذا الملف",
        "load_error": "ملف غير صالح.",
        "lt_company": "المؤسسة أو المنظمة", "lt_position": "الوظيفة المستهدفة",
        "lt_offer": "إعلان الوظيفة (الصق النص، اختياري)",
        "lt_hint": "الصق الإعلان ليبرز التطبيق المهارات المطابقة.",
        "lt_generate": "إنشاء الخطاب", "lt_text": "الخطاب (يمكنك تعديله)",
        "lt_subject": "الموضوع: طلب توظيف لشغل وظيفة {position}",
        "dl_letter_pdf": "تحميل الخطاب بصيغة PDF",
        "dl_letter_html": "تحميل الخطاب بصيغة HTML",
    },
}

LETTER = {
    "fr": {
        "sep": ", ",
        "greeting": "Madame, Monsieur,",
        "intro": "C'est avec un vif intérêt que je vous adresse ma candidature au poste de {position} au sein de {company}.",
        "skills_match": "Mes compétences en {skills} correspondent aux besoins exprimés dans votre offre.",
        "skills_top": "Je maîtrise notamment {skills}.",
        "body": "Mon parcours m'a permis de développer l'esprit d'équipe, la rigueur et le sens de l'organisation nécessaires pour réussir à ce poste. Je suis convaincu(e) que mon profil répond à vos attentes.",
        "closing_offer": "Je reste à votre disposition pour un entretien afin de vous présenter plus en détail ma motivation.",
        "formula": "Dans l'attente de votre réponse, je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.",
        "position_default": "[poste visé]", "company_default": "votre structure",
    },
    "en": {
        "sep": ", ",
        "greeting": "Dear Hiring Manager,",
        "intro": "I am writing to apply for the position of {position} at {company}.",
        "skills_match": "My skills in {skills} match the requirements stated in your job offer.",
        "skills_top": "My main skills include {skills}.",
        "body": "My background has helped me develop teamwork, rigor and the organizational skills needed to succeed in this role. I am confident that my profile meets your expectations.",
        "closing_offer": "I would welcome the opportunity to discuss my application in an interview.",
        "formula": "Thank you for your time and consideration. Yours sincerely,",
        "position_default": "[position]", "company_default": "your organization",
    },
    "ar": {
        "sep": "، ",
        "greeting": "السيد/السيدة المحترم(ة)،",
        "intro": "يسعدني أن أتقدم بطلبي لشغل وظيفة {position} لدى {company}.",
        "skills_match": "مهاراتي في {skills} تتوافق مع المتطلبات الواردة في إعلانكم.",
        "skills_top": "أتقن على وجه الخصوص: {skills}.",
        "body": "أتمتع بروح العمل الجماعي والانضباط والقدرة على التنظيم، وأنا على يقين بأن مؤهلاتي تتوافق مع متطلبات هذه الوظيفة.",
        "closing_offer": "يسعدني أن أقابلكم لأشرح دوافعي بمزيد من التفصيل.",
        "formula": "وتفضلوا بقبول فائق الاحترام والتقدير،",
        "position_default": "[الوظيفة المستهدفة]", "company_default": "مؤسستكم",
    },
}

EXAMPLES = {
    "fr": {
        "name": "Aminetou Mint Salem", "job": "Assistante administrative",
        "email": "aminetou.salem@email.com", "phone": "+222 22 00 00 00", "city": "Nouakchott",
        "summary": "Assistante administrative avec 3 ans d'expérience en gestion de documents, accueil et saisie de données. Organisée, rigoureuse et à l'aise avec les outils bureautiques.",
        "interests": "Lecture\nBénévolat\nInformatique", "references": "Disponibles sur demande.",
        "tables": {
            "exp": [
                {"poste": "Assistante administrative", "entreprise": "Cabinet Horizon", "periode": "2023 - 2026",
                 "description": "Accueil, gestion du courrier, classement des dossiers et saisie de données."},
                {"poste": "Agent de saisie", "entreprise": "Projet de collecte de données", "periode": "2022 - 2023",
                 "description": "Saisie et vérification de questionnaires sur tablette."},
            ],
            "edu": [{"diplome": "Licence en gestion", "ecole": "Université de Nouakchott", "periode": "2019 - 2022"}],
            "cert": [{"titre": "Bureautique (Word, Excel)", "organisme": "Centre de formation", "annee": "2021"}],
            "proj": [{"nom": "Suivi des stocks", "description": "Tableau Excel de suivi des entrées et sorties pour une boutique."}],
            "skills": [{"competence": "Word", "niveau": 5}, {"competence": "Excel", "niveau": 4},
                       {"competence": "Saisie de données", "niveau": 5}, {"competence": "Accueil", "niveau": 4}],
            "langs": [{"langue": "Arabe", "niveau": 5}, {"langue": "Français", "niveau": 4},
                      {"langue": "Anglais", "niveau": 2}],
        },
    },
    "en": {
        "name": "Aminetou Mint Salem", "job": "Administrative Assistant",
        "email": "aminetou.salem@email.com", "phone": "+222 22 00 00 00", "city": "Nouakchott",
        "summary": "Administrative assistant with 3 years of experience in document management, reception and data entry. Organized, rigorous and comfortable with office software.",
        "interests": "Reading\nVolunteering\nComputers", "references": "Available on request.",
        "tables": {
            "exp": [
                {"poste": "Administrative Assistant", "entreprise": "Horizon Firm", "periode": "2023 - 2026",
                 "description": "Reception, mail handling, file organization and data entry."},
                {"poste": "Data Entry Clerk", "entreprise": "Data collection project", "periode": "2022 - 2023",
                 "description": "Entry and verification of questionnaires on tablets."},
            ],
            "edu": [{"diplome": "Bachelor in Management", "ecole": "University of Nouakchott", "periode": "2019 - 2022"}],
            "cert": [{"titre": "Office software (Word, Excel)", "organisme": "Training center", "annee": "2021"}],
            "proj": [{"nom": "Stock tracking", "description": "Excel sheet tracking incoming and outgoing goods for a shop."}],
            "skills": [{"competence": "Word", "niveau": 5}, {"competence": "Excel", "niveau": 4},
                       {"competence": "Data entry", "niveau": 5}, {"competence": "Reception", "niveau": 4}],
            "langs": [{"langue": "Arabic", "niveau": 5}, {"langue": "French", "niveau": 4},
                      {"langue": "English", "niveau": 2}],
        },
    },
    "ar": {
        "name": "أمينتو منت سالم", "job": "مساعدة إدارية",
        "email": "aminetou.salem@email.com", "phone": "+222 22 00 00 00", "city": "نواكشوط",
        "summary": "مساعدة إدارية بخبرة ثلاث سنوات في إدارة الوثائق والاستقبال وإدخال البيانات. منظمة ودقيقة وتتقن برامج المكتب.",
        "interests": "القراءة\nالعمل التطوعي\nالحاسوب", "references": "متوفرة عند الطلب.",
        "tables": {
            "exp": [
                {"poste": "مساعدة إدارية", "entreprise": "مكتب الأفق", "periode": "2023 - 2026",
                 "description": "الاستقبال وإدارة البريد وتنظيم الملفات وإدخال البيانات."},
                {"poste": "عاملة إدخال بيانات", "entreprise": "مشروع جمع البيانات", "periode": "2022 - 2023",
                 "description": "إدخال الاستبيانات ومراجعتها على الأجهزة اللوحية."},
            ],
            "edu": [{"diplome": "إجازة في التسيير", "ecole": "جامعة نواكشوط", "periode": "2019 - 2022"}],
            "cert": [{"titre": "برامج المكتب (وورد، إكسل)", "organisme": "مركز تكوين", "annee": "2021"}],
            "proj": [{"nom": "متابعة المخزون", "description": "جدول إكسل لمتابعة دخول وخروج البضائع في متجر."}],
            "skills": [{"competence": "وورد", "niveau": 5}, {"competence": "إكسل", "niveau": 4},
                       {"competence": "إدخال البيانات", "niveau": 5}, {"competence": "الاستقبال", "niveau": 4}],
            "langs": [{"langue": "العربية", "niveau": 5}, {"langue": "الفرنسية", "niveau": 4},
                      {"langue": "الإنجليزية", "niveau": 2}],
        },
    },
}

EMPTY = {**{f: "" for f in FIELDS}, "photo": "", "tables": {k: [] for k in TABLES}}


# =====================================================================
#  Fonctions utilitaires
# =====================================================================
def esc(value) -> str:
    return html.escape(str(value or "").strip()).replace("\n", "<br>")


def lines(text: str):
    return [l.strip() for l in (text or "").splitlines() if l.strip()]


def text_on(hex_color: str) -> str:
    """Blanc sur fond foncé, noir sur fond clair (le texte reste lisible)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#ffffff" if (0.299 * r + 0.587 * g + 0.114 * b) < 160 else "#1a1a1a"


def make_df(records, cols) -> pd.DataFrame:
    df = pd.DataFrame(records or []).reindex(columns=cols)
    if "niveau" in cols:
        df["niveau"] = pd.to_numeric(df["niveau"], errors="coerce")
    return df


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


def dots(level) -> str:
    try:
        n = max(0, min(5, int(round(float(level)))))
    except (TypeError, ValueError):
        return ""
    if n == 0:
        return ""
    cells = "".join(f'<i class="d{" on" if i < n else ""}"></i>' for i in range(5))
    return f'<span class="dots">{cells}</span>'


def level_rows(df: pd.DataFrame, namecol: str):
    out = []
    for _, r in df.fillna("").iterrows():
        n = str(r[namecol]).strip()
        if n:
            out.append((n, r["niveau"]))
    return out


def plain_rows(df: pd.DataFrame):
    df = df.fillna("")
    return [r for _, r in df.iterrows() if any(str(v).strip() for v in r.values)]


# =====================================================================
#  Construction du CV
# =====================================================================
WM_CSS = (".wm { position: fixed; top: 42%; left: 0; right: 0; text-align: center; "
          "font-size: 54pt; font-weight: bold; color: rgba(0,0,0,.09); "
          "transform: rotate(-28deg); z-index: 99; }")


def css_dots(fill: str, line: str) -> str:
    return (".dots { white-space: nowrap; } "
            f".d {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; "
            f"margin: 0 1px; border: 1px solid {line}; }} "
            f".d.on {{ background: {fill}; }}")


def fragments(t: dict, d: dict) -> dict:
    f = {}
    f["exp"] = "".join(
        f"""<div class="item">
          <div class="row"><b>{esc(r['poste'])}</b><span class="muted">{esc(r['periode'])}</span></div>
          <div class="muted">{esc(r['entreprise'])}</div>
          <p>{esc(r['description'])}</p></div>"""
        for r in plain_rows(d["exp"]))
    f["edu"] = "".join(
        f"""<div class="item">
          <div class="row"><b>{esc(r['diplome'])}</b><span class="muted">{esc(r['periode'])}</span></div>
          <div class="muted">{esc(r['ecole'])}</div></div>"""
        for r in plain_rows(d["edu"]))
    f["cert"] = "".join(
        f"""<div class="item">
          <div class="row"><b>{esc(r['titre'])}</b><span class="muted">{esc(r['annee'])}</span></div>
          <div class="muted">{esc(r['organisme'])}</div></div>"""
        for r in plain_rows(d["cert"]))
    f["proj"] = "".join(
        f"""<div class="item"><b>{esc(r['nom'])}</b><p>{esc(r['description'])}</p></div>"""
        for r in plain_rows(d["proj"]))
    f["summary"] = f"<p>{esc(d['summary'])}</p>" if d["summary"].strip() else ""
    f["refs"] = f"<p>{esc(d['references'])}</p>" if d["references"].strip() else ""
    f["skills"] = level_rows(d["skills"], "competence")
    f["langs"] = level_rows(d["langs"], "langue")
    f["interests"] = lines(d["interests"])
    f["contact"] = [(lbl, val) for lbl, val in (
        (t["email"], d["email"]), (t["phone"], d["phone"]), (t["city"], d["city"])
    ) if val and val.strip()]
    return f


def section(title: str, body: str) -> str:
    return f"<h2>{esc(title)}</h2>{body}" if body else ""


def build_cv(t: dict, d: dict, template: str, color: str,
             preview: bool = False, watermark: bool = False) -> str:
    rtl = t["dir"] == "rtl"
    start = "right" if rtl else "left"
    f = fragments(t, d)
    wm = f'<div class="wm">{esc(t["wm"])}</div>' if watermark else ""
    on = text_on(color)
    head = (f'<!DOCTYPE html>\n<html lang="{t["lang_code"]}" dir="{t["dir"]}">\n'
            '<head>\n<meta charset="utf-8">\n<style>\n')

    # ---------------------------------------------------------------
    if template == "classic":
        pad = "body { padding: 10mm 12mm; }" if preview else ""
        photo_tag = f'<img class="photo" src="{d["photo"]}" alt="">' if d["photo"] else ""
        contact = " &bull; ".join(esc(v) for _, v in f["contact"])
        sk = "".join(f"<li>{esc(n)} {dots(l)}</li>" for n, l in f["skills"])
        lg = "".join(f"<li>{esc(n)} {dots(l)}</li>" for n, l in f["langs"])
        it = "".join(f"<li>{esc(i)}</li>" for i in f["interests"])
        return f"""{head}
  @page {{ size: A4; margin: 15mm; }}
  body {{ font-family: {FONTS}; color: #222; font-size: 11pt; line-height: 1.45; }}
  {pad}
  {WM_CSS}
  {css_dots(color, color)}
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
  {wm}
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
  {section(t['profile_title'], f['summary'])}
  {section(t['experience'], f['exp'])}
  {section(t['education'], f['edu'])}
  {section(t['certs_title'], f['cert'])}
  {section(t['projects_title'], f['proj'])}
  {section(t['skills_title'], f"<ul>{sk}</ul>" if sk else "")}
  {section(t['languages_title'], f"<ul>{lg}</ul>" if lg else "")}
  {section(t['interests_title'], f"<ul>{it}</ul>" if it else "")}
  {section(t['references_title'], f['refs'])}
</body>
</html>"""

    # ---------------------------------------------------------------
    zoom = "body { zoom: 0.7; }" if preview else ""
    line = "rgba(255,255,255,.45)" if on == "#ffffff" else "rgba(0,0,0,.30)"
    pill = "rgba(255,255,255,.18)" if on == "#ffffff" else "rgba(0,0,0,.08)"

    def lv_rows(rows):
        return "".join(
            f'<div class="lv"><span>{esc(n)}</span>{dots(l)}</div>' for n, l in rows)

    if template == "banner":
        grad_dir = "to right" if rtl else "to left"
        photo_tag = f'<img class="bphoto" src="{d["photo"]}" alt="">' if d["photo"] else ""
        contact = " &bull; ".join(esc(v) for _, v in f["contact"])
        pills = "".join(f'<span class="pill">{esc(i)}</span>' for i in f["interests"])

        def aside_section(title, body):
            return f"<h3>{esc(title)}</h3>{body}" if body else ""

        return f"""{head}
  @page {{ size: A4; margin: 0;
          background: linear-gradient({grad_dir}, #eef1f5 62mm, #ffffff 62mm); }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: {FONTS}; font-size: 10.5pt; line-height: 1.45; color: #222; }}
  {zoom}
  {WM_CSS}
  {css_dots(color, color)}
  .page {{ width: 210mm; }}
  .band {{ display: flex; align-items: center; gap: 18px; background: {color}; color: {on};
          padding: 12mm 14mm; }}
  .bphoto {{ width: 34mm; height: 34mm; border-radius: 50%; object-fit: cover;
            border: 3px solid {on}; flex-shrink: 0; }}
  .band h1 {{ margin: 0; font-size: 26pt; line-height: 1.1; }}
  .band .job {{ font-size: 13pt; margin-top: 4px; opacity: .92; }}
  .band .contact {{ font-size: 9.5pt; margin-top: 6px; opacity: .9; }}
  .body {{ display: flex; min-height: 236mm; }}
  .bmain {{ flex: 1; padding: 8mm 12mm; background: #ffffff; }}
  .baside {{ width: 62mm; flex-shrink: 0; background: #eef1f5; padding: 8mm 8mm; }}
  h2 {{ font-size: 11.5pt; text-transform: uppercase; letter-spacing: 1.5px; color: {color};
       border-bottom: 2px solid {color}; padding-bottom: 3px; margin: 14px 0 8px; }}
  .baside h3 {{ font-size: 10pt; text-transform: uppercase; letter-spacing: 1.5px;
               color: {color}; border-bottom: 1px solid #c9d0d9; padding-bottom: 3px; margin: 12px 0 8px; }}
  .lv {{ display: flex; justify-content: space-between; align-items: center; gap: 6px;
        margin-bottom: 5px; font-size: 9.5pt; }}
  .pill {{ display: inline-block; background: #ffffff; border: 1px solid #c9d0d9;
          border-radius: 10px; padding: 2px 9px; margin: 0 3px 5px 3px; font-size: 9.5pt; }}
  .item {{ margin-bottom: 10px; page-break-inside: avoid; }}
  .row {{ display: flex; justify-content: space-between; gap: 12px; }}
  .muted {{ color: #666; }}
  p {{ margin: 3px 0 0; }}
</style>
</head>
<body>
  {wm}
  <div class="page">
    <div class="band">
      {photo_tag}
      <div>
        <h1>{esc(d['name'])}</h1>
        <div class="job">{esc(d['job'])}</div>
        <div class="contact">{contact}</div>
      </div>
    </div>
    <div class="body">
      <main class="bmain">
        {section(t['profile_title'], f['summary'])}
        {section(t['experience'], f['exp'])}
        {section(t['education'], f['edu'])}
        {section(t['certs_title'], f['cert'])}
        {section(t['projects_title'], f['proj'])}
        {section(t['references_title'], f['refs'])}
      </main>
      <aside class="baside">
        {aside_section(t['skills_title'], lv_rows(f['skills']))}
        {aside_section(t['languages_title'], lv_rows(f['langs']))}
        {aside_section(t['interests_title'], pills)}
      </aside>
    </div>
  </div>
</body>
</html>"""

    # ---------------------------------------------------------------  modern
    grad_dir = "to left" if rtl else "to right"
    photo_block = (f'<div class="photo-wrap"><img class="photo" src="{d["photo"]}" alt=""></div>'
                   if d["photo"] else "")
    contact_items = "".join(
        f'<div class="ci"><span class="label">{esc(lbl)}</span>{esc(val)}</div>'
        for lbl, val in f["contact"])
    pills = "".join(f'<span class="pill">{esc(i)}</span>' for i in f["interests"])

    def side_section(title, body):
        return f"<h3>{esc(title)}</h3>{body}" if body else ""

    return f"""{head}
  @page {{ size: A4; margin: 0;
          background: linear-gradient({grad_dir}, {color} 68mm, #ffffff 68mm); }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: {FONTS}; font-size: 10.5pt; line-height: 1.45; color: #222; }}
  {zoom}
  {WM_CSS}
  {css_dots(on, on)}
  .cv {{ display: flex; width: 210mm; min-height: 296mm; }}
  .side {{ width: 68mm; flex-shrink: 0; background: {color}; color: {on}; padding: 14mm 8mm; }}
  .main {{ flex: 1; background: #ffffff; padding: 14mm 12mm; }}
  .photo-wrap {{ text-align: center; margin-bottom: 10mm; }}
  .photo {{ width: 38mm; height: 38mm; border-radius: 50%; object-fit: cover;
           border: 3px solid {on}; }}
  .side h3 {{ font-size: 10pt; text-transform: uppercase; letter-spacing: 1.5px;
             border-bottom: 1px solid {line}; padding-bottom: 3px; margin: 14px 0 8px; }}
  .ci {{ margin-bottom: 7px; font-size: 9.5pt; word-wrap: break-word; overflow-wrap: anywhere; }}
  .label {{ display: block; font-size: 7.5pt; text-transform: uppercase;
           letter-spacing: 1px; opacity: .75; }}
  .lv {{ display: flex; justify-content: space-between; align-items: center; gap: 6px;
        margin-bottom: 5px; font-size: 9.5pt; }}
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
  {wm}
  <div class="cv">
    <aside class="side">
      {photo_block}
      {side_section(t['contact_title'], contact_items)}
      {side_section(t['skills_title'], lv_rows(f['skills']))}
      {side_section(t['languages_title'], lv_rows(f['langs']))}
      {side_section(t['interests_title'], pills)}
    </aside>
    <main class="main">
      <h1>{esc(d['name'])}</h1>
      <div class="job">{esc(d['job'])}</div>
      {section(t['profile_title'], f['summary'])}
      {section(t['experience'], f['exp'])}
      {section(t['education'], f['edu'])}
      {section(t['certs_title'], f['cert'])}
      {section(t['projects_title'], f['proj'])}
      {section(t['references_title'], f['refs'])}
    </main>
  </div>
</body>
</html>"""


# =====================================================================
#  Lettre de motivation
# =====================================================================
def generate_letter(lang, name, position, company, summary, skill_names, offer) -> str:
    L = LETTER[lang]
    position = position.strip() or L["position_default"]
    company = company.strip() or L["company_default"]
    low = (offer or "").lower()
    matched = [s for s in skill_names if low and s.lower() in low]
    if matched:
        sk = L["skills_match"].format(skills=L["sep"].join(matched[:5]))
    elif skill_names:
        sk = L["skills_top"].format(skills=L["sep"].join(skill_names[:4]))
    else:
        sk = ""
    parts = [L["greeting"], L["intro"].format(position=position, company=company)]
    if summary.strip():
        parts.append(summary.strip())
    if sk:
        parts.append(sk)
    parts += [L["body"], L["closing_offer"], L["formula"], name.strip()]
    return "\n\n".join(p for p in parts if p)


def build_letter(t: dict, d: dict, company: str, position: str, text: str,
                 color: str, preview: bool = False, watermark: bool = False) -> str:
    rtl = t["dir"] == "rtl"
    end_align = "left" if rtl else "right"
    pad = "body { padding: 10mm 12mm; }" if preview else ""
    wm = f'<div class="wm">{esc(t["wm"])}</div>' if watermark else ""
    sender = "<br>".join(esc(x) for x in (d["name"], d["email"], d["phone"]) if x and x.strip())
    date = datetime.date.today().strftime("%d/%m/%Y")
    place = f"{esc(d['city'])}, {date}" if d["city"].strip() else date
    subject = esc(t["lt_subject"].format(position=position.strip())) if position.strip() else ""
    body = "".join(f"<p>{esc(p)}</p>" for p in text.split("\n\n") if p.strip())
    return f"""<!DOCTYPE html>
<html lang="{t['lang_code']}" dir="{t['dir']}">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 22mm; }}
  body {{ font-family: {FONTS}; font-size: 11.5pt; line-height: 1.6; color: #222; }}
  {pad}
  {WM_CSS}
  .bar {{ height: 6px; background: {color}; margin-bottom: 10mm; }}
  .sender {{ margin-bottom: 10mm; }}
  .sender b {{ color: {color}; font-size: 13pt; }}
  .date {{ text-align: {end_align}; margin-bottom: 8mm; }}
  .to {{ font-weight: bold; margin-bottom: 8mm; }}
  .subject {{ font-weight: bold; margin-bottom: 8mm; color: {color}; }}
  p {{ margin: 0 0 4mm; text-align: justify; }}
</style>
</head>
<body>
  {wm}
  <div class="bar"></div>
  <div class="sender">{sender}</div>
  <div class="date">{place}</div>
  <div class="to">{esc(company)}</div>
  <div class="subject">{subject}</div>
  {body}
</body>
</html>"""


def make_pdf(html_str: str) -> bytes:
    from weasyprint import HTML  # import ici : l'app marche même sans WeasyPrint
    return HTML(string=html_str).write_pdf()


# =====================================================================
#  État de l'application (session)
# =====================================================================
s = st.session_state


def apply_state(data: dict):
    """Remplit tous les champs depuis un dictionnaire (exemple, effacement, fichier chargé)."""
    full = {**EMPTY, **data}
    for fld in FIELDS:
        s["f_" + fld] = str(full.get(fld, "") or "")
    photo = str(full.get("photo", "") or "")
    s["photo_data"] = photo if PHOTO_RE.fullmatch(photo) else ""
    s["photo_src"] = None
    s["photo_ver"] = s.get("photo_ver", 0) + 1
    tables = full.get("tables") or {}
    for key, cols in TABLES.items():
        recs = tables.get(key, [])
        s["df_" + key] = make_df(recs if isinstance(recs, list) else [], cols)
    if data.get("lang_label") in LANG_LABELS:
        s["lang_label"] = data["lang_label"]
    if data.get("template") in TEMPLATES:
        s["template"] = data["template"]
    if data.get("color_key") in COLOR_KEYS:
        s["color_key"] = data["color_key"]
    cc = data.get("color_custom")
    if isinstance(cc, str) and HEX_RE.fullmatch(cc):
        s["color_custom"] = cc
    s["ver"] = s.get("ver", 0) + 1


def fill_example():
    apply_state(EXAMPLES[LANG_LABELS[s["lang_label"]]])


def clear_all():
    apply_state({})
    s["letter_text"] = ""


def load_cv():
    up = s.get(f"load_file_{s.get('ver', 0)}")
    if up is None:
        return
    try:
        data = json.loads(up.getvalue().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError
    except Exception:
        s["load_error"] = True
        return
    s["load_error"] = False
    apply_state(data)


if "ver" not in s:
    s["lang_label"] = "Français"
    s["template"] = "modern"
    s["color_key"] = "blue"
    s["color_custom"] = "#1f4e79"
    s["letter_text"] = ""
    s["lt_company"] = ""
    s["lt_position"] = ""
    s["lt_offer"] = ""
    s["load_error"] = False
    apply_state({})
    s["ver"] = 0


# =====================================================================
#  Interface : barre latérale (haut)
# =====================================================================
st.sidebar.radio("Langue du CV / Language / لغة السيرة", list(LANG_LABELS), key="lang_label")
lang = LANG_LABELS[s["lang_label"]]
t = T[lang]
ver = s["ver"]

st.sidebar.button(t["example_btn"], on_click=fill_example)
st.sidebar.button(t["clear_btn"], on_click=clear_all)

# Code d'accès (actif seulement si des codes sont définis dans les secrets)
unlocked = True
if ACCESS_CODES:
    st.sidebar.divider()
    code = st.sidebar.text_input(t["code_label"], type="password", key="access_code")
    unlocked = code.strip() in ACCESS_CODES
    if code.strip():
        (st.sidebar.success if unlocked else st.sidebar.error)(
            t["code_ok"] if unlocked else t["code_bad"])
    if not unlocked:
        st.sidebar.info(PAYMENT_INFO or t["payment_info"])
watermark = bool(ACCESS_CODES) and not unlocked

if APP_URL:
    st.sidebar.link_button(
        t["share_wa"], "https://wa.me/?text=" + quote(t["share_msg"].format(url=APP_URL)))


# =====================================================================
#  Interface : page principale
# =====================================================================
st.title(f"📄 {t['app_title']}")
tab_form, tab_preview, tab_letter = st.tabs([t["tab_form"], t["tab_preview"], t["tab_letter"]])


def table(key, cfg):
    return st.data_editor(
        s["df_" + key], num_rows="dynamic", key=f"ed_{key}_{ver}", column_config=cfg)


level_cfg = st.column_config.NumberColumn(t["level"], min_value=1, max_value=5, step=1, format="%d")

with tab_form:
    o1, o2 = st.columns(2)
    o1.radio(t["template"], TEMPLATES, key="template",
             format_func=lambda k: t["tpl_" + k], horizontal=True)
    o2.selectbox(t["color"], COLOR_KEYS, key="color_key",
                 format_func=lambda k: t["colors"][k])
    if s["color_key"] == "custom":
        st.color_picker(t["custom_color"], key="color_custom")

    up = st.file_uploader(t["photo"], type=["jpg", "jpeg", "png"],
                          help=t["photo_help"], key=f"photo_up_{s['photo_ver']}")
    if up is not None:
        fid = getattr(up, "file_id", up.name)
        if s.get("photo_src") != fid:
            s["photo_data"] = process_photo(up)
            s["photo_src"] = fid
    if s["photo_data"]:
        pc1, pc2 = st.columns([1, 4])
        pc1.image(s["photo_data"], width=90)
        if pc2.button(t["remove_photo"]):
            s["photo_data"] = ""
            s["photo_src"] = None
            s["photo_ver"] += 1
            st.rerun()

    st.text_input(t["full_name"], key="f_name")
    st.text_input(t["job"], key="f_job", placeholder=t["job_ph"], help=t["job_help"])
    c1, c2, c3 = st.columns(3)
    c1.text_input(t["email"], key="f_email")
    c2.text_input(t["phone"], key="f_phone")
    c3.text_input(t["city"], key="f_city")
    st.text_area(t["summary"], key="f_summary", height=100, help=t["summary_help"])

    st.subheader(t["experience"])
    st.caption(t["exp_tip"])
    ed_exp = table("exp", {"poste": t["position"], "entreprise": t["company"],
                           "periode": t["period"], "description": t["description"]})

    st.subheader(t["education"])
    st.caption(t["edu_tip"])
    ed_edu = table("edu", {"diplome": t["diploma"], "ecole": t["school"], "periode": t["period"]})

    st.subheader(t["certs"])
    ed_cert = table("cert", {"titre": t["cert_name"], "organisme": t["cert_org"], "annee": t["year"]})

    st.subheader(t["projects"])
    ed_proj = table("proj", {"nom": t["proj_name"], "description": t["description"]})

    st.subheader(t["skills_label"])
    ed_skills = table("skills", {"competence": t["skill"], "niveau": level_cfg})

    st.subheader(t["languages_label"])
    ed_langs = table("langs", {"langue": t["language"], "niveau": level_cfg})

    st.text_area(t["interests"], key="f_interests", height=80)
    st.text_area(t["references"], key="f_references", height=70)

# ---------- Données et couleur ----------
color = s["color_custom"] if s["color_key"] == "custom" else PALETTE[s["color_key"]]
template = s["template"]
data = {
    "photo": s["photo_data"],
    "name": s["f_name"], "job": s["f_job"], "email": s["f_email"],
    "phone": s["f_phone"], "city": s["f_city"], "summary": s["f_summary"],
    "interests": s["f_interests"], "references": s["f_references"],
    "exp": ed_exp, "edu": ed_edu, "cert": ed_cert, "proj": ed_proj,
    "skills": ed_skills, "langs": ed_langs,
}
cv_html = build_cv(t, data, template, color, watermark=watermark)
cv_preview = build_cv(t, data, template, color, preview=True, watermark=watermark)

with tab_preview:
    components.html(cv_preview, height=860 if template != "classic" else 900, scrolling=True)
    st.download_button(t["dl_html"], cv_html, file_name="cv.html", mime="text/html")
    try:
        st.download_button(t["dl_pdf"], make_pdf(cv_html), file_name="cv.pdf",
                           mime="application/pdf")
    except Exception:
        st.info(t["pdf_error"])

with tab_letter:
    st.caption(t["lt_hint"])
    l1, l2 = st.columns(2)
    l1.text_input(t["lt_company"], key="lt_company")
    l2.text_input(t["lt_position"], key="lt_position")
    st.text_area(t["lt_offer"], key="lt_offer", height=120)
    if st.button(t["lt_generate"]):
        skill_names = [n for n, _ in level_rows(ed_skills, "competence")]
        s["letter_text"] = generate_letter(
            lang, s["f_name"], s["lt_position"], s["lt_company"],
            s["f_summary"], skill_names, s["lt_offer"])
    st.text_area(t["lt_text"], key="letter_text", height=360)

    if s["letter_text"].strip():
        letter_html = build_letter(t, data, s["lt_company"], s["lt_position"],
                                   s["letter_text"], color, watermark=watermark)
        letter_preview = build_letter(t, data, s["lt_company"], s["lt_position"],
                                      s["letter_text"], color, preview=True, watermark=watermark)
        components.html(letter_preview, height=700, scrolling=True)
        st.download_button(t["dl_letter_html"], letter_html,
                           file_name="lettre.html", mime="text/html")
        try:
            st.download_button(t["dl_letter_pdf"], make_pdf(letter_html),
                               file_name="lettre.pdf", mime="application/pdf")
        except Exception:
            st.info(t["pdf_error"])

# =====================================================================
#  Barre latérale (bas) : sauvegarde et rechargement du CV
# =====================================================================
payload = {
    "version": 1,
    "lang_label": s["lang_label"], "template": template,
    "color_key": s["color_key"], "color_custom": s["color_custom"],
    **{fld: s["f_" + fld] for fld in FIELDS},
    "photo": s["photo_data"],
    "tables": {
        "exp": ed_exp.fillna("").to_dict("records"),
        "edu": ed_edu.fillna("").to_dict("records"),
        "cert": ed_cert.fillna("").to_dict("records"),
        "proj": ed_proj.fillna("").to_dict("records"),
        "skills": ed_skills.fillna("").to_dict("records"),
        "langs": ed_langs.fillna("").to_dict("records"),
    },
}
with st.sidebar:
    st.divider()
    st.download_button(
        t["save_btn"], json.dumps(payload, ensure_ascii=False, default=str),
        file_name="mon-cv.json", mime="application/json")
    st.file_uploader(t["load_label"], type=["json"], key=f"load_file_{ver}")
    st.button(t["load_btn"], on_click=load_cv)
    if s.get("load_error"):
        st.error(t["load_error"])
