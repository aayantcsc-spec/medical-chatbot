"""
taxonomy.py - the 46 MediChat health categories, the suggested first point of care for
each, and the mapping from model intents (topic ids) to categories.

Two levels:
    category (46)   coarse scope + safety priority + who-to-see guidance   (this file)
    topic / intent  fine-grained label the three models predict           (knowledge.py + knowledge_extra.py)

A topic may belong to several categories (e.g. `stroke_signs` is a medical emergency, a brain
health topic and an emergency-warning-sign topic). The FIRST category in the list is the primary
one. Specialist advice is general guidance for a first point of care - not a diagnosis, and a
doctor decides whether a specialist is needed.
"""

# id -> (number, display name, first point of care, specialist who may be involved, urgency)
# urgency: "emergency" | "urgent" (same-day care may be needed) | "routine" | "info"
_C = [
    ("general_health", "General Health", "General Physician", "Depends on the concern", "info"),
    ("physical_symptoms", "Physical Symptoms", "General Physician", "Specialist depends on the symptom", "routine"),
    ("common_diseases", "Common Diseases", "General Physician", "Specialist if the illness is long-lasting or complicated", "routine"),
    ("mental_health", "Mental Health", "General Physician or a qualified mental health professional", "Psychologist (talk therapy) or Psychiatrist (medical assessment and medicines)", "routine"),
    ("mental_health_emergency", "Mental Health Emergencies", "Emergency services / nearest hospital, or a crisis helpline", "Psychiatrist (urgent assessment)", "emergency"),
    ("medical_emergency", "Medical Emergencies", "Emergency Department - call 112 now", "Emergency physician", "emergency"),
    ("first_aid", "First Aid", "First aid at home for minor injuries; General Physician if it does not improve", "Emergency Department for serious injuries", "urgent"),
    ("doctor_guidance", "Doctor and Specialist Guidance", "General Physician (usual first point of care)", "Specialist chosen by the doctor based on the problem", "info"),
    ("medication_information", "Medication Information", "Pharmacist or the prescribing doctor", "Doctor who prescribed the medicine", "info"),
    ("treatment_information", "Treatment Information", "The doctor treating you", "Specialist for the condition", "info"),
    ("self_care", "Self-Care and Home Care", "Self-care first; General Physician if no improvement", "-", "routine"),
    ("disease_prevention", "Disease Prevention", "General Physician", "-", "info"),
    ("diet_nutrition", "Diet and Nutrition", "General Physician or a Registered Dietitian", "Dietitian / Endocrinologist for medical diets", "info"),
    ("fitness_exercise", "Fitness and Exercise", "General Physician before starting if you have a health condition", "Physiotherapist / Sports Medicine doctor for injuries", "info"),
    ("sleep_problems", "Sleep Problems", "General Physician", "Sleep specialist, ENT doctor or Psychiatrist depending on the cause", "routine"),
    ("stress_anxiety", "Stress and Anxiety", "General Physician or a counsellor", "Psychologist or Psychiatrist", "routine"),
    ("depression_low_mood", "Depression and Low Mood", "General Physician or a qualified mental health professional", "Psychologist or Psychiatrist", "routine"),
    ("emotional_wellbeing", "Emotional Well-Being", "A trusted person, counsellor or General Physician", "Psychologist", "info"),
    ("suicidal_self_harm", "Suicidal Thoughts and Self-Harm Support", "Emergency services (112) or a crisis helpline right now; stay with a trusted person", "Psychiatrist (urgent assessment)", "emergency"),
    ("pregnancy_maternal", "Pregnancy and Maternal Health", "Obstetrician-Gynaecologist", "Obstetrician-Gynaecologist", "routine"),
    ("womens_health", "Women's Health", "Gynaecologist or General Physician", "Gynaecologist", "routine"),
    ("mens_health", "Men's Health", "General Physician", "Urologist for urinary or prostate concerns", "routine"),
    ("childrens_health", "Children's Health", "Paediatrician", "Paediatric specialist if referred", "routine"),
    ("teenage_health", "Teenage Health", "Paediatrician or General Physician", "Dermatologist, counsellor or Psychologist depending on the concern", "routine"),
    ("older_adults_health", "Older Adults' Health", "General Physician / Geriatrician", "Geriatrician or the relevant specialist", "routine"),
    ("skin_hair", "Skin and Hair Health", "General Physician", "Dermatologist", "routine"),
    ("dental_oral", "Dental and Oral Health", "Dentist", "Dentist / Oral surgeon", "routine"),
    ("eye_vision", "Eye and Vision Health", "Optometrist or Ophthalmologist", "Ophthalmologist", "routine"),
    ("heart_health", "Heart Health", "General Physician", "Cardiologist", "routine"),
    ("brain_nervous_system", "Brain and Nervous System Health", "General Physician", "Neurologist", "routine"),
    ("digestive_health", "Stomach and Digestive Health", "General Physician", "Gastroenterologist", "routine"),
    ("respiratory_health", "Respiratory Health", "General Physician", "Pulmonologist (chest physician)", "routine"),
    ("diabetes_blood_sugar", "Diabetes and Blood Sugar", "General Physician", "Endocrinologist / Diabetologist", "routine"),
    ("blood_pressure", "Blood Pressure", "General Physician", "Cardiologist if needed", "routine"),
    ("allergies", "Allergies", "General Physician", "Allergist / Immunologist, or Dermatologist for skin allergies", "routine"),
    ("infections_fever", "Infections and Fever", "General Physician", "Infectious-disease specialist if severe or unusual", "routine"),
    ("medical_tests_reports", "Medical Tests and Reports", "The doctor who ordered the test", "Specialist relevant to the result", "info"),
    ("vaccination_immunization", "Vaccination and Immunization", "General Physician or Paediatrician (child vaccines)", "-", "info"),
    ("chronic_disease_management", "Chronic Disease Management", "Your regular General Physician", "Specialist for the condition (e.g. Endocrinologist, Cardiologist)", "routine"),
    ("rehabilitation_recovery", "Rehabilitation and Recovery", "The treating doctor, then a Physiotherapist", "Physiotherapist / Rehabilitation (PM&R) doctor / Occupational therapist", "routine"),
    ("substance_use_addiction", "Substance Use and Addiction Support", "General Physician or a de-addiction centre", "Psychiatrist / addiction specialist", "routine"),
    ("sexual_reproductive_health", "Sexual and Reproductive Health", "Gynaecologist (women) or General Physician / Urologist (men)", "Gynaecologist, Urologist or a sexual-health clinic", "routine"),
    ("disability_accessibility", "Disability and Accessibility-Related Health", "General Physician and the relevant rehabilitation team", "Rehabilitation (PM&R) doctor, therapists, disability services", "routine"),
    ("emergency_warning_signs", "Emergency Warning Signs", "Emergency Department - call 112 now", "Emergency physician", "emergency"),
    ("follow_up", "Follow-Up Questions and Next Steps", "As per the earlier topic", "-", "info"),
    ("out_of_scope", "Out-of-Scope Questions and Safe Fallbacks", "-", "-", "info"),
]

CATEGORIES_46 = [
    {"no": i + 1, "id": c[0], "name": c[1], "first_care": c[2], "specialist": c[3], "urgency": c[4]}
    for i, c in enumerate(_C)
]
assert len(CATEGORIES_46) == 46 and len({c["id"] for c in CATEGORIES_46}) == 46
CATEGORY_BY_ID = {c["id"]: c for c in CATEGORIES_46}

# topic id -> categories (first = primary)
TOPIC_CATEGORIES = {
    # ---- original topics
    "fever": ["infections_fever", "physical_symptoms"],
    "headache": ["physical_symptoms", "brain_nervous_system"],
    "common_cold": ["common_diseases", "respiratory_health", "self_care"],
    "sore_throat": ["physical_symptoms", "common_diseases", "self_care"],
    "medicine_precautions": ["medication_information"],
    "antibiotics": ["medication_information", "infections_fever"],
    "chest_pain_emergency": ["medical_emergency", "heart_health", "emergency_warning_signs"],
    "stroke_signs": ["medical_emergency", "brain_nervous_system", "emergency_warning_signs"],
    "poisoning": ["medical_emergency", "substance_use_addiction", "emergency_warning_signs"],
    "self_harm": ["suicidal_self_harm", "mental_health_emergency"],
    "severe_allergy": ["medical_emergency", "allergies", "emergency_warning_signs"],
    "choking": ["medical_emergency", "first_aid", "emergency_warning_signs"],
    "severe_bleeding": ["medical_emergency", "first_aid", "emergency_warning_signs"],
    "breathing_difficulty": ["medical_emergency", "respiratory_health", "emergency_warning_signs"],
    "asthma": ["respiratory_health", "chronic_disease_management"],
    "cough": ["respiratory_health", "physical_symptoms"],
    "heart_warning_signs": ["heart_health", "emergency_warning_signs"],
    "blood_pressure": ["blood_pressure", "heart_health"],
    "stress_signs": ["stress_anxiety", "mental_health"],
    "depression_signs": ["depression_low_mood", "mental_health"],
    "healthy_diet": ["diet_nutrition", "general_health"],
    "hydration": ["diet_nutrition", "self_care"],
    "exercise_benefits": ["fitness_exercise", "general_health"],
    "exercise_start": ["fitness_exercise"],
    "sleep_importance": ["sleep_problems", "general_health"],
    "insomnia": ["sleep_problems"],
    "flu": ["infections_fever", "common_diseases"],
    "food_poisoning": ["digestive_health", "infections_fever"],
    "toothache": ["dental_oral"],
    "gum_care": ["dental_oral"],
    "eye_irritation": ["eye_vision"],
    "eye_strain": ["eye_vision"],
    "anemia": ["common_diseases", "diet_nutrition"],
    "cholesterol": ["heart_health", "medical_tests_reports"],
    "dizziness": ["physical_symptoms", "brain_nervous_system"],
    "fatigue": ["physical_symptoms"],
    "minor_burn": ["first_aid", "self_care"],
    "minor_cut": ["first_aid"],
    "menstrual_cramps": ["womens_health"],
    "pregnancy_signs": ["pregnancy_maternal", "womens_health"],
    "child_fever": ["childrens_health", "infections_fever"],
    "child_dehydration": ["childrens_health"],
    "fall_prevention": ["older_adults_health", "disease_prevention"],
    "memory_changes": ["older_adults_health", "brain_nervous_system"],
    "weight_management": ["diet_nutrition", "fitness_exercise"],
    "back_pain": ["physical_symptoms", "rehabilitation_recovery"],
    "indigestion": ["digestive_health", "physical_symptoms"],
    "skin_rash": ["skin_hair", "allergies"],
    "joint_pain": ["physical_symptoms", "older_adults_health"],
    "uti": ["womens_health", "infections_fever"],
    "infection_prevention": ["disease_prevention", "infections_fever"],
    "handwashing": ["disease_prevention"],
    "diabetes_risk": ["diabetes_blood_sugar", "disease_prevention"],
    "preventive_checkups": ["disease_prevention", "vaccination_immunization"],
    # ---- topics added for the 46-category scope (knowledge_extra.py)
    "general_health_education": ["general_health"],
    "mental_health_general": ["mental_health"],
    "mental_health_crisis": ["mental_health_emergency", "mental_health"],
    "anxiety_signs": ["stress_anxiety", "mental_health"],
    "low_mood_support": ["depression_low_mood", "mental_health"],
    "emotional_support": ["emotional_wellbeing", "mental_health"],
    "doctor_general_guidance": ["doctor_guidance"],
    "doctor_headache_neuro": ["doctor_guidance", "brain_nervous_system", "physical_symptoms"],
    "doctor_skin": ["doctor_guidance", "skin_hair", "allergies"],
    "doctor_thyroid": ["doctor_guidance", "chronic_disease_management"],
    "doctor_digestive": ["doctor_guidance", "digestive_health"],
    "doctor_joint_bone": ["doctor_guidance", "physical_symptoms"],
    "treatment_information": ["treatment_information"],
    "home_remedies_selfcare": ["self_care"],
    "medication_information": ["medication_information"],
    "medication_dosage_request": ["medication_information"],
    "mens_health": ["mens_health"],
    "teen_health": ["teenage_health"],
    "acne_hair_care": ["skin_hair", "teenage_health"],
    "numbness_tingling": ["brain_nervous_system", "physical_symptoms"],
    "diabetes_basics": ["diabetes_blood_sugar", "chronic_disease_management"],
    "allergy_general": ["allergies"],
    "blood_tests_reports": ["medical_tests_reports"],
    "vaccination_info": ["vaccination_immunization", "childrens_health"],
    "chronic_disease_management": ["chronic_disease_management"],
    "rehabilitation_recovery": ["rehabilitation_recovery"],
    "substance_use_support": ["substance_use_addiction"],
    "sexual_reproductive_health": ["sexual_reproductive_health"],
    "disability_accessibility": ["disability_accessibility"],
    "emergency_warning_signs_general": ["emergency_warning_signs", "medical_emergency"],
    "follow_up_simplify": ["follow_up"],
    "follow_up_next_steps": ["follow_up"],
    "out_of_scope": ["out_of_scope"],
    "tropical_fevers": ["common_diseases", "infections_fever"],
    "pcos_periods": ["womens_health", "sexual_reproductive_health"],
    "pregnancy_care": ["pregnancy_maternal"],
    "older_adult_care": ["older_adults_health", "chronic_disease_management"],
}

# intents that are about the conversation or scope, not a medical topic
META_INTENTS = {"follow_up_simplify", "follow_up_next_steps", "out_of_scope"}


def primary_category(topic_id):
    cats = TOPIC_CATEGORIES.get(topic_id)
    return cats[0] if cats else None


def categories_of(topic_id):
    return list(TOPIC_CATEGORIES.get(topic_id, []))


def care_line(topic_id):
    """'Suggested first point of care' sentence for a topic (None for meta intents)."""
    if topic_id in META_INTENTS:
        return None
    cat = CATEGORY_BY_ID.get(primary_category(topic_id))
    if not cat or cat["first_care"] == "-":
        return None
    line = "Suggested first point of care: " + cat["first_care"] + "."
    if cat["specialist"] not in ("-", "Depends on the concern") and cat["urgency"] not in ("emergency",):
        line += " A specialist - " + cat["specialist"] + " - may be needed if your doctor advises it."
    return line
