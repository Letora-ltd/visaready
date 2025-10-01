import json, os, datetime, sys

FRONT = os.path.join("frontend","seed","checklists.json")
BACK  = os.path.join("data","seed","checklists.json")

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def add_entry(store, key, items, sources, fees, proc, stamp):
    store[key] = {
        "last_verified": stamp,
        "items": items,
        "fees": fees,
        "processing": proc,
        "sources": sources
    }

today = str(datetime.date.today())
CODES = ["DE","FR","IT","ES","ID","LK","NP","VN","PH","CN","HK","RU","ZA","CH","NL"]

# Official India links (used for XX->IN)
S_IN = [
    {"label":"Indian e-Visa (Official)", "url":"https://indianvisaonline.gov.in/evisa/"},
    {"label":"Bureau of Immigration (India)", "url":"https://boi.gov.in/"}
]

# Light country-side source placeholders for IN->XX (you can refine later in Admin)
S_OUT_STUDENT = {
    "DE":[{"label":"Germany — Student Visa (Official)","url":"https://india.diplo.de/in-en/service/05-VisaEinreise/-/2523148"}],
    "FR":[{"label":"France — Campus France","url":"https://www.campusfrance.org/en"}],
    "IT":[{"label":"Italy — Study Visa","url":"https://vistoperitalia.esteri.it/"}],
    "ES":[{"label":"Spain — Student (Ministry)","url":"https://www.exteriores.gob.es/"}],
    "ID":[{"label":"Indonesia — Immigration","url":"https://www.imigrasi.go.id/en/"}],
    "LK":[{"label":"Sri Lanka — Immigration","url":"https://www.immigration.gov.lk/"}],
    "NP":[{"label":"Nepal Immigration","url":"https://www.immigration.gov.np/"}],
    "VN":[{"label":"Vietnam Immigration","url":"https://www.immigration.gov.vn/"}],
    "PH":[{"label":"Bureau of Immigration Philippines","url":"https://immigration.gov.ph/"}],
    "CN":[{"label":"China — COVA","url":"https://cova.mfa.gov.cn/"}],
    "HK":[{"label":"Hong Kong — Study","url":"https://www.immd.gov.hk/eng/services/visas/study.html"}],
    "RU":[{"label":"Russia — Visa portal","url":"https://visa.kdmid.ru/"}],
    "ZA":[{"label":"South Africa — Home Affairs","url":"http://www.dha.gov.za/"}],
    "CH":[{"label":"Switzerland — SEM","url":"https://www.sem.admin.ch/sem/en/home.html"}],
    "NL":[{"label":"Netherlands — Visas & permits","url":"https://www.netherlandsandyou.nl/travel-and-residence/visas-and-permits"}],
}
S_OUT_WORK = {
    "DE":[{"label":"Germany — Employment Visa","url":"https://india.diplo.de/in-en/service/05-VisaEinreise"}],
    "FR":[{"label":"France-Visas — Work","url":"https://france-visas.gouv.fr/"}],
    "IT":[{"label":"Italy — Work Visa","url":"https://vistoperitalia.esteri.it/"}],
    "ES":[{"label":"Spain — Work Permits","url":"https://www.exteriores.gob.es/"}],
    "ID":[{"label":"Indonesia — KITAS","url":"https://www.imigrasi.go.id/en/"}],
    "LK":[{"label":"Sri Lanka — Employment","url":"https://www.immigration.gov.lk/visas/"}],
    "NP":[{"label":"Nepal — Work Visa","url":"https://www.imigration.gov.np/".replace("imigration","immigration")}],
    "VN":[{"label":"Vietnam — Work","url":"https://www.immigration.gov.vn/"}],
    "PH":[{"label":"Philippines — Work Visa","url":"https://immigration.gov.ph/"}],
    "CN":[{"label":"China — Z Visa (Work)","url":"https://cova.mfa.gov.cn/"}],
    "HK":[{"label":"Hong Kong — Employment Visa","url":"https://www.immd.gov.hk/eng/services/visas/employment.html"}],
    "RU":[{"label":"Russia — Work Visa","url":"https://visa.kdmid.ru/"}],
    "ZA":[{"label":"South Africa — Temporary Residence","url":"http://www.dha.gov.za/index.php/immigration-services/temporary-residence"}],
    "CH":[{"label":"Switzerland — Work","url":"https://www.sem.admin.ch/sem/en/home.html"}],
    "NL":[{"label":"Netherlands — Work","url":"https://www.netherlandsandyou.nl/work"}],
}

# Base item templates
IN_TO_X_STUDENT = [
    {"title":"Valid passport","details":"6+ months validity; required blank pages."},
    {"title":"Admission/Offer letter","details":"From recognised institution."},
    {"title":"Financial proof","details":"Bank statements, scholarships, or sponsor docs."},
    {"title":"Insurance & medical","details":"As required by host country."},
    {"title":"Application & biometrics","details":"Online form; appointment and biometrics if required."},
    {"title":"Accommodation","details":"Dorm booking/host letter/lease."}
]
IN_TO_X_WORK = [
    {"title":"Valid passport","details":"6+ months validity; blank pages."},
    {"title":"Employment contract/offer","details":"Meets host-country requirements."},
    {"title":"Work authorisation","details":"Permit/sponsor approvals where applicable."},
    {"title":"Qualifications","details":"Degrees, experience letters, registrations."},
    {"title":"Application & biometrics","details":"Online form; appointment and biometrics if required."},
    {"title":"Insurance","details":"Health/travel insurance; employer coverage if applicable."}
]
X_TO_IN_STUDENT = [
    {"title":"Valid passport","details":"Meets India’s validity requirements; blank pages."},
    {"title":"Admission letter (India)","details":"From Indian university/college."},
    {"title":"Proof of funds","details":"As per FRRO guidance."},
    {"title":"FRRO requirements","details":"Registration after arrival if required."},
    {"title":"Apply Student Visa (S) / e-Visa","details":"Online application; follow mission instructions."},
    {"title":"Accommodation","details":"Hostel booking/letter/lease."}
]
X_TO_IN_WORK = [
    {"title":"Valid passport","details":"Meets India’s validity requirements; blank pages."},
    {"title":"Employment contract (India)","details":"Offer letter; salary threshold may apply."},
    {"title":"Employment Visa (E)","details":"Apply online; supporting letters and qualifications."},
    {"title":"FRRO registration","details":"After arrival where required."},
    {"title":"Medical/Police clearance","details":"If required by mission/employer."},
    {"title":"Insurance","details":"Medical/travel insurance recommended."}
]

fees_student_out = "Consular fee + service charge (varies)"
proc_student_out = "Typically 2–6+ weeks (varies by season and mission)"
fees_work_out    = "Consular fee + service charge (varies)"
proc_work_out    = "Typically 3–8+ weeks (role/country dependent)"
fees_in          = "Varies by nationality and duration"
proc_student_in  = "3–10 working days typical; FRRO registration after arrival when required"
proc_work_in     = "3–15 working days typical; extra time for clearances"

for code in CODES:
    # IN -> XX
    key_s = f"IN->{code}::STUDENT"
    key_w = f"IN->{code}::WORK"
    add_entry(checklists, key_s, IN_TO_X_STUDENT, S_OUT_STUDENT.get(code, []), fees_student_out, proc_student_out, today)
    add_entry(checklists, key_w, IN_TO_X_WORK,    S_OUT_WORK.get(code,    []), fees_work_out,    proc_work_out,    today)
    # XX -> IN
    key_s2 = f"{code}->IN::STUDENT"
    key_w2 = f"{code}->IN::WORK"
    add_entry(checklists, key_s2, X_TO_IN_STUDENT, S_IN, fees_in, proc_student_in, today)
    add_entry(checklists, key_w2, X_TO_IN_WORK,    S_IN, fees_in, proc_work_in,    today)

# Write back to both copies
dump(FRONT, checklists)
dump(BACK,  checklists)

print("v3.3 STUDENT & WORK variants added to:", FRONT, "and", BACK)
