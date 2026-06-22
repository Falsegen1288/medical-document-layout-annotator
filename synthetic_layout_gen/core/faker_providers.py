# core/faker_providers.py
import random
from faker import Faker

fake = Faker()

def seed_faker(seed: int):
    random.seed(seed)
    Faker.seed(seed)

def fake_company_name() -> str:
    return fake.company()

def fake_invoice_number() -> str:
    # INV-YYYY-NNNNN
    year = random.randint(2020, 2028)
    num = random.randint(10000, 99999)
    return f"INV-{year}-{num}"

def fake_patient_id() -> str:
    # Format: PT-XX-NNNNN (never resembles real MRN formats)
    letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
    num = random.randint(10000, 99999)
    return f"PT-{letters}-{num}"

def fake_diagnosis_code() -> str:
    # Fully fabricated ICD-like code, e.g. "FAB-12.34"
    prefix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))
    n1 = random.randint(10, 99)
    n2 = random.randint(10, 99)
    return f"{prefix}-{n1}.{n2}"

def fake_case_citation() -> str:
    # e.g., "123 F.3d 456 (9th Cir. 2024)"
    volume = random.randint(1, 999)
    reporter = random.choice(["F.3d", "F.2d", "U.S.", "S.Ct.", "L.Ed.2d", "Cal.Rptr."])
    page = random.randint(1, 999)
    circuit = random.choice(["1st Cir.", "2nd Cir.", "3rd Cir.", "4th Cir.", "5th Cir.", "6th Cir.", "7th Cir.", "8th Cir.", "9th Cir.", "10th Cir.", "11th Cir.", "D.C. Cir.", "Fed. Cir."])
    year = random.randint(1880, 2026)
    return f"{volume} {reporter} {page} ({circuit} {year})"

def fake_currency_amount(lo=1, hi=5000) -> str:
    amount = random.uniform(lo, hi)
    return f"${amount:,.2f}"

def fake_product_sku() -> str:
    # e.g. SKU-123-ABCD
    n = random.randint(100, 999)
    letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
    return f"SKU-{n}-{letters}"
