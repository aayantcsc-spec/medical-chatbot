"""
knowledge.py
------------
Health knowledge base used by the Rule-Based, ML and DL bots.

Each topic has:
    category   - one of the 20 categories shown on the comparison page
    questions  - different ways a user may ask about this topic (training data)
    keywords   - words used by the Rule-Based bot
    short      - 1-2 sentence overview
    details    - key facts (symptoms / causes / benefits)
    advice     - what the person can do (self-care / prevention)
    doctor     - when to see a doctor (or call emergency services)
    urgent     - True if this is a medical emergency topic

NOTE: this is general health education only. No medicine doses are given
on purpose, because dosing must come from a doctor or pharmacist.
"""

DISCLAIMER = ("This is general health information, not a diagnosis. "
              "Please talk to a doctor for advice about your own situation.")

TOPICS = [
# ---------------------------------------------------------------- General Medical
{
 "id": "fever", "category": "General Medical", "urgent": False,
 "questions": [
    "What are the common symptoms of fever?", "What are the symptoms of a fever?",
    "How do I know if I have a fever?", "What happens when you have a fever?",
    "fever symptoms", "I feel hot and shivering, is it fever?",
    "What is a normal body temperature and when is it a fever?",
    "What should I do when I have a fever?", "How to reduce fever at home?"],
 "keywords": ["fever", "temperature", "feverish", "shivering", "chills"],
 "short": "A fever means your body temperature is higher than normal, usually 38 C (100.4 F) or above. It is often a sign that the body is fighting an infection.",
 "details": "Common signs are feeling hot, sweating, chills and shivering, headache, muscle aches, tiredness, loss of appetite and mild dehydration.",
 "advice": "Rest, drink plenty of fluids, wear light clothing and keep the room comfortable. Ask a pharmacist or doctor which fever medicine is suitable for you.",
 "doctor": "See a doctor if the fever lasts more than 3 days, goes above 39.5 C (103 F), or comes with a stiff neck, rash, confusion, trouble breathing or severe pain."},
{
 "id": "headache", "category": "General Medical", "urgent": False,
 "questions": [
    "What causes headaches?", "Why do I get headaches so often?",
    "What are the common causes of headache?", "I have a headache what should I do",
    "How can I relieve a headache?", "What triggers a migraine?",
    "headache causes", "Why does my head hurt?", "When is a headache serious?"],
 "keywords": ["headache", "migraine", "head hurts", "head pain", "head ache", "headaches"],
 "short": "Most headaches are tension-type headaches or migraines and are not dangerous. Common triggers include stress, dehydration, missed meals, poor sleep, eye strain and too much screen time.",
 "details": "Tension headaches feel like a tight band around the head. Migraines are often one-sided, throbbing, and may come with nausea or sensitivity to light and sound.",
 "advice": "Rest in a quiet dark room, drink water, eat regular meals, sleep well, take screen breaks and manage stress. Keep a diary to find your triggers.",
 "doctor": "Get urgent medical help for a sudden very severe headache, headache after a head injury, or headache with fever and stiff neck, confusion, weakness or vision changes."},
{
 "id": "common_cold", "category": "General Medical", "urgent": False,
 "questions": [
    "What are the symptoms of the common cold?", "How can I treat a cold at home?",
    "I have a runny nose and sneezing", "How long does a cold last?", "Why do I sneeze so much?",
    "home remedies for cold", "What is the difference between a cold and an allergy?", "blocked nose and sneezing what to do"],
 "keywords": ["cold", "common cold", "runny nose", "sneezing", "sneeze", "blocked nose", "stuffy nose", "congestion"],
 "short": "The common cold is a mild viral infection of the nose and throat. It usually gets better by itself in 7 to 10 days.",
 "details": "Typical symptoms are a runny or blocked nose, sneezing, sore throat, mild cough, mild headache and feeling tired. Allergies cause similar sneezing but usually no fever and last longer.",
 "advice": "Rest, drink warm fluids, use steam inhalation or salt-water nasal rinses, and wash hands often to avoid spreading it. Antibiotics do not work against colds.",
 "doctor": "See a doctor if symptoms last more than 10 days, you have a high fever, ear or chest pain, trouble breathing, or if a baby, older adult or person with a chronic illness is affected."},
{
 "id": "sore_throat", "category": "General Medical", "urgent": False,
 "questions": [
    "What is a good home remedy for a sore throat?", "What causes a sore throat?", "My throat hurts when I swallow",
    "How can I relieve throat pain?", "sore throat treatment", "Why is my throat itchy and scratchy?",
    "When should I see a doctor for a sore throat?", "throat pain and difficulty swallowing"],
 "keywords": ["sore throat", "throat pain", "throat hurts", "scratchy throat", "tonsils", "tonsillitis", "throat infection"],
 "short": "A sore throat is most often caused by a viral infection such as a cold or flu. Allergies, dry air, smoke and bacterial infections like strep throat can also cause it.",
 "details": "It may feel scratchy, dry or painful when swallowing, and the throat can look red. Strep throat often comes with fever, swollen glands and white patches on the tonsils.",
 "advice": "Gargle with warm salt water, sip warm drinks with honey (not for babies under 1 year), rest your voice, drink plenty of fluids and avoid smoke.",
 "doctor": "See a doctor if the sore throat lasts more than a week, you have a high fever, trouble swallowing or breathing, drooling, a rash, or white patches on the tonsils."},
# ---------------------------------------------------------------- Medication
{
 "id": "medicine_precautions", "category": "Medication", "urgent": False,
 "questions": [
    "What precautions should be taken when taking medicine?",
    "How should I take medicines safely?", "What are the safety tips for using medication?",
    "Is it safe to take medicine without a doctor?", "medicine safety precautions",
    "What should I know before taking a new medicine?",
    "Can I mix different medicines together?", "Why should I read the medicine label?",
    "What to do if I miss a dose of my medicine?"],
 "keywords": ["medicine", "medication", "tablet", "tablets", "pills", "drug", "dose", "prescription"],
 "short": "Medicines are safe when used correctly. Always follow the instructions from your doctor or pharmacist and read the label before use.",
 "details": "Check the dose, timing and expiry date. Tell your doctor about allergies, other medicines, supplements and pregnancy. Never share prescription medicines with others.",
 "advice": "Do not stop or change a prescribed medicine on your own, store medicines away from children, and ask a pharmacist before combining medicines.",
 "doctor": "Contact a doctor or pharmacist if you get a rash, swelling, trouble breathing, vomiting or any unusual reaction. For a suspected overdose, call emergency services right away."},
{
 "id": "antibiotics", "category": "Medication", "urgent": False,
 "questions": [
    "When should antibiotics be used?", "Do antibiotics work for cold and flu?",
    "What is antibiotic resistance?", "Can I stop antibiotics when I feel better?",
    "How should I take antibiotics?", "antibiotics for viral infection",
    "Are antibiotics safe to take without prescription?", "What are the side effects of antibiotics?"],
 "keywords": ["antibiotic", "antibiotics", "amoxicillin", "resistance"],
 "short": "Antibiotics treat bacterial infections only. They do not work against viruses such as the common cold or flu.",
 "details": "Using antibiotics when they are not needed, or stopping early, can cause antibiotic resistance. Side effects can include stomach upset, diarrhoea and allergic reactions.",
 "advice": "Take antibiotics only when prescribed, finish the course exactly as your doctor says, and never use leftover antibiotics.",
 "doctor": "See a doctor if you get a rash, swelling of the face, trouble breathing, severe diarrhoea, or if you do not improve after a few days of treatment."},
# ---------------------------------------------------------------- Emergency
{
 "id": "chest_pain_emergency", "category": "Emergency", "urgent": True,
 "questions": [
    "What should I do if I have severe chest pain?", "I have severe chest pain, what do I do?",
    "Chest pain emergency", "My chest hurts badly and I feel breathless",
    "I think I am having a heart attack", "What to do for sudden chest pain?",
    "pressure in my chest and left arm pain", "Is chest pain an emergency?"],
 "keywords": ["chest pain", "heart attack", "chest hurts", "chest pressure", "chest tightness"],
 "short": "Severe chest pain can be a sign of a heart attack and is a medical emergency. Call your local emergency number (for example 112 or 108 in India, 911 in the US) immediately.",
 "details": "Warning signs include pressure or tightness in the chest, pain spreading to the arm, jaw or back, shortness of breath, cold sweat, nausea and light-headedness.",
 "advice": "Stop all activity and sit down, stay calm, and unlock your door if you are alone. Do not drive yourself to hospital. If a doctor has told you to, chew an aspirin while waiting for help.",
 "doctor": "Call emergency services immediately. Do not wait to see if the pain goes away."},
{
 "id": "stroke_signs", "category": "Emergency", "urgent": True,
 "questions": [
    "What are the signs of a stroke?", "How do I recognise a stroke?",
    "Face drooping and slurred speech what should I do?", "What is FAST for stroke?",
    "My father has sudden weakness on one side", "stroke emergency symptoms",
    "sudden numbness in face arm or leg", "What to do if someone has a stroke?"],
 "keywords": ["stroke", "face drooping", "slurred speech", "one side weak", "paralysis"],
 "short": "A stroke is a medical emergency caused by a blocked or burst blood vessel in the brain. Fast treatment saves brain function, so call emergency services immediately.",
 "details": "Remember FAST: Face drooping, Arm weakness, Speech difficulty, Time to call emergency services. Other signs are sudden confusion, trouble seeing, severe headache or loss of balance.",
 "advice": "Note the time symptoms started, keep the person calm and lying safely, and do not give food, drink or medicine.",
 "doctor": "Call emergency services immediately, even if the symptoms seem to go away."},
# ---------------------------------------------------------------- more emergencies
{
 "id": "poisoning", "category": "Emergency", "urgent": True,
 "questions": [
    "I accidentally swallowed a cleaning product. What should I do?", "My child swallowed bleach",
    "What to do if someone swallows poison?", "I took too many tablets by mistake",
    "My toddler drank a chemical", "poisoning first aid", "someone swallowed a battery",
    "What should I do in case of an overdose?"],
 "keywords": ["swallowed", "poison", "poisoning", "overdose", "cleaning product", "bleach", "chemical", "ingested", "too many tablets"],
 "short": "Swallowing a poison, chemical, cleaning product or too much medicine is a medical emergency. Call your local emergency number or poison control centre immediately.",
 "details": "Keep the container or label to show the doctors, and note what was swallowed, how much and when.",
 "advice": "Do not make the person vomit, and do not give food, milk or water unless a medical professional tells you to. If the person is unconscious or has trouble breathing, call emergency services at once.",
 "doctor": "Call emergency services or the poison control centre immediately, even if the person seems fine."},
{
 "id": "self_harm", "category": "Emergency", "urgent": True,
 "questions": [
    "I feel like harming myself", "I want to end my life", "I have suicidal thoughts",
    "I do not want to live anymore", "I want to hurt myself", "What should I do if I feel suicidal?",
    "My friend says he wants to die", "I feel like giving up on life"],
 "keywords": ["suicide", "suicidal", "harm myself", "harming myself", "hurt myself", "hurting myself", "end my life", "kill myself", "want to die", "self harm", "self-harm"],
 "short": "I am really sorry you are in so much pain. You deserve support, and you do not have to go through this alone.",
 "details": "Thoughts of suicide or self-harm are a sign of deep distress, not weakness, and they can get better with help.",
 "advice": "If you might act on these thoughts, call your local emergency number right now. You can also contact a crisis helpline (in India Tele-MANAS 14416 or 1800-891-4416, in the US call or text 988), or reach out to a trusted person and stay with them. Move away from anything you could use to hurt yourself.",
 "doctor": "Please contact a doctor, a mental health professional or emergency services right now. Telling someone is the first step."},
{
 "id": "severe_allergy", "category": "Emergency", "urgent": True,
 "questions": [
    "What should I do for a severe allergic reaction?", "Face swelling and trouble breathing after eating",
    "What is anaphylaxis?", "allergic reaction with hives and breathing problems",
    "My throat is swelling after a bee sting", "signs of a serious allergy",
    "How do I use an epinephrine auto-injector?", "What to do if someone has an allergic reaction?"],
 "keywords": ["allergic reaction", "anaphylaxis", "anaphylactic", "swelling of throat", "bee sting", "hives", "epinephrine", "allergy"],
 "short": "A severe allergic reaction (anaphylaxis) is life-threatening. Call emergency services immediately.",
 "details": "Signs include swelling of the lips, face or throat, trouble breathing or wheezing, hives, dizziness or fainting, vomiting and a fast heartbeat.",
 "advice": "If the person has a prescribed adrenaline (epinephrine) auto-injector, use it as they were trained to and then call emergency services. Lay the person flat with legs raised unless breathing is hard, and stay with them.",
 "doctor": "Call emergency services immediately, even if symptoms improve after using the injector."},
{
 "id": "choking", "category": "Emergency", "urgent": True,
 "questions": [
    "What should I do if someone is choking?", "Food is stuck in my throat and I cannot breathe",
    "How do I help a choking child?", "Heimlich manoeuvre steps", "My baby is choking",
    "choking first aid", "someone cannot speak or cough after eating", "What to do when a person chokes on food?"],
 "keywords": ["choking", "choke", "choked", "heimlich", "stuck in throat"],
 "short": "Choking is an emergency when a person cannot cough, speak or breathe. Call emergency services immediately.",
 "details": "Signs are being unable to speak or cry, a silent or weak cough, clutching the throat and blue lips.",
 "advice": "For an adult or child over 1 year: encourage coughing; if they cannot cough, give up to 5 back blows between the shoulder blades, then up to 5 abdominal thrusts, and repeat until help arrives. For a baby, use back blows and chest thrusts only. Learning first aid in a certified course is very helpful.",
 "doctor": "Call emergency services immediately. Anyone who needed abdominal thrusts should be checked by a doctor afterwards."},
{
 "id": "severe_bleeding", "category": "Emergency", "urgent": True,
 "questions": [
    "What should I do for heavy bleeding that will not stop?", "Deep wound bleeding a lot",
    "How to stop severe bleeding?", "bleeding will not stop after an accident",
    "Someone is losing a lot of blood", "severe bleeding first aid",
    "I cut my leg badly and it keeps bleeding", "How to control bleeding in an emergency?"],
 "keywords": ["heavy bleeding", "severe bleeding", "bleeding a lot", "bleeding will not stop", "bleeding won't stop", "blood loss", "losing blood"],
 "short": "Heavy bleeding that does not stop is an emergency. Call emergency services immediately.",
 "details": "Danger signs are blood soaking through cloth, pale cold skin, fast heartbeat, dizziness, confusion or fainting.",
 "advice": "Press firmly with a clean cloth directly on the wound and keep pressing without lifting to check. Add more cloth on top if it soaks through. Raise the injured limb if possible, keep the person lying down and warm, and do not remove objects stuck in the wound.",
 "doctor": "Call emergency services immediately and keep pressure on the wound until help arrives."},
{
 "id": "breathing_difficulty", "category": "Emergency", "urgent": True,
 "questions": [
    "I cannot breathe properly what should I do?", "What to do if someone has difficulty breathing?",
    "sudden shortness of breath", "I am struggling to breathe", "Why am I out of breath suddenly?",
    "breathing emergency", "My lips are turning blue and I am breathless",
    "trouble breathing and wheezing at rest"],
 "keywords": ["cannot breathe", "can't breathe", "difficulty breathing", "trouble breathing", "shortness of breath", "breathless", "struggling to breathe", "out of breath"],
 "short": "Sudden or severe difficulty breathing is a medical emergency. Call emergency services immediately.",
 "details": "Warning signs are struggling for breath, being unable to speak full sentences, blue or grey lips, chest pain, wheezing and confusion.",
 "advice": "Sit upright, loosen tight clothing, try to stay calm and breathe slowly, and use your prescribed reliever inhaler if you have one. Do not lie flat.",
 "doctor": "Call emergency services immediately, especially if breathing is getting worse or lips look blue."},
# ---------------------------------------------------------------- Respiratory
{
 "id": "asthma", "category": "Respiratory Health", "urgent": False,
 "questions": [
    "What are the symptoms of asthma?", "How do I know if I have asthma?",
    "asthma symptoms", "Why do I wheeze and cough at night?",
    "What triggers an asthma attack?", "What should I do during an asthma attack?",
    "I get chest tightness and wheezing", "Is asthma curable?"],
 "keywords": ["asthma", "wheeze", "wheezing", "inhaler"],
 "short": "Asthma is a long-term condition in which the airways become swollen and narrow, making breathing difficult.",
 "details": "Common symptoms are wheezing, coughing (especially at night or early morning), chest tightness and shortness of breath. Triggers include dust, pollen, smoke, cold air, exercise and infections.",
 "advice": "Avoid known triggers, do not smoke, and use the inhaler and action plan your doctor gave you. Asthma cannot be cured but it can be well controlled.",
 "doctor": "Get emergency help if breathing is very difficult, you cannot speak a full sentence, lips turn blue, or the reliever inhaler does not help."},
{
 "id": "cough", "category": "Respiratory Health", "urgent": False,
 "questions": [
    "What causes a cough?", "Why do I have a cough that won't go away?",
    "How can I treat a cough at home?", "dry cough causes", "What causes a persistent cough?",
    "When should I worry about a cough?", "I keep coughing for two weeks", "cough with phlegm what does it mean"],
 "keywords": ["cough", "coughing", "phlegm", "mucus", "coughs"],
 "short": "A cough is the body's way of clearing the airways. Most coughs are caused by viral infections like colds and settle by themselves in 1 to 3 weeks.",
 "details": "Other causes include allergies, asthma, acid reflux, smoking, dust and, less commonly, chest infections or tuberculosis.",
 "advice": "Drink warm fluids, rest, avoid smoke and dust, and keep the air moist. Warm water with honey can soothe the throat in adults and children over one year old.",
 "doctor": "See a doctor if the cough lasts more than 3 weeks, or comes with blood, high fever, weight loss, night sweats or shortness of breath."},
# ---------------------------------------------------------------- Heart
{
 "id": "heart_warning_signs", "category": "Heart Health", "urgent": False,
 "questions": [
    "What are the warning signs of heart problems?", "How do I know if my heart is unhealthy?",
    "heart disease symptoms", "What are the early signs of heart disease?",
    "I get palpitations and feel tired, is it my heart?", "signs of a heart problem in women",
    "Why do I feel breathless on climbing stairs?", "How can I keep my heart healthy?"],
 "keywords": ["heart", "palpitation", "palpitations", "heartbeat", "cardiac", "heart disease"],
 "short": "Heart problems can show up as chest discomfort, shortness of breath, unusual tiredness, an irregular or racing heartbeat, or swelling in the legs.",
 "details": "Other signs are dizziness, fainting, pain in the arm, jaw or back, and nausea. Women may have milder or unusual symptoms such as fatigue and indigestion-like pain.",
 "advice": "Stay active, eat more vegetables, fruit and whole grains, avoid tobacco, limit salt and alcohol, and get your blood pressure and cholesterol checked.",
 "doctor": "Book a doctor visit if you notice these signs. Call emergency services if you have chest pain, fainting or severe breathlessness."},
{
 "id": "blood_pressure", "category": "Heart Health", "urgent": False,
 "questions": [
    "What are the symptoms of high blood pressure?", "What causes high blood pressure?",
    "How can I lower my blood pressure naturally?", "What is a normal blood pressure?",
    "hypertension symptoms", "Why is high blood pressure called a silent killer?",
    "low blood pressure symptoms", "How to control hypertension?"],
 "keywords": ["blood pressure", "hypertension", "bp"],
 "short": "High blood pressure (hypertension) usually has no symptoms, which is why it is called the silent killer. Over time it raises the risk of heart attack, stroke and kidney disease.",
 "details": "A reading around 120/80 mmHg is considered normal. Repeated readings of 140/90 mmHg or higher need medical review. Severe cases may cause headache, nosebleeds or blurred vision.",
 "advice": "Reduce salt, stay active, maintain a healthy weight, limit alcohol, avoid smoking, manage stress and check your pressure regularly.",
 "doctor": "See a doctor for regular high readings. Seek emergency care for very high pressure with chest pain, severe headache, weakness or trouble speaking."},
# ---------------------------------------------------------------- Mental Health
{
 "id": "stress_signs", "category": "Mental Health", "urgent": False,
 "questions": [
    "What are common signs of stress?", "How do I know if I am stressed?",
    "stress symptoms", "I feel overwhelmed and cannot relax",
    "How can I manage stress?", "What are the effects of stress on the body?",
    "Why do I feel tense and irritable all the time?", "ways to reduce stress"],
 "keywords": ["stress", "stressed", "overwhelmed", "tense", "burnout", "pressure"],
 "short": "Stress is the body's reaction to pressure or demands. A little stress is normal, but long-term stress can affect your health.",
 "details": "Common signs are irritability, anxiety, trouble sleeping, headaches, muscle tension, stomach upset, tiredness, poor concentration and changes in appetite.",
 "advice": "Try regular exercise, deep breathing, good sleep, breaks from work, time with friends and family, and talking about your worries. Limit caffeine and alcohol.",
 "doctor": "Speak to a doctor or counsellor if stress affects your daily life for weeks. If you have thoughts of harming yourself, contact emergency services or a crisis helpline right away."},
{
 "id": "depression_signs", "category": "Mental Health", "urgent": False,
 "questions": [
    "What are the signs of depression?", "How do I know if I am depressed?",
    "I feel sad and hopeless all the time", "depression symptoms",
    "I have lost interest in everything", "What are the signs of anxiety?",
    "How can I help a friend who is depressed?", "Is feeling sad for weeks normal?"],
 "keywords": ["depression", "depressed", "sad", "hopeless", "lonely"],
 "short": "Depression is more than feeling sad. It is a common and treatable mental health condition that affects mood, thinking and daily life.",
 "details": "Signs include a low mood most of the day, loss of interest, changes in sleep or appetite, tiredness, trouble concentrating, feeling worthless and, sometimes, thoughts of self-harm. Anxiety brings constant worry, restlessness and a racing heart.",
 "advice": "Talk to someone you trust, keep a routine, get sunlight and exercise, and avoid alcohol. Therapy and, when needed, medicines prescribed by a doctor work well.",
 "doctor": "Please see a doctor or mental health professional if these feelings last more than two weeks. If you think about harming yourself, call emergency services or a crisis helpline immediately."},
# ---------------------------------------------------------------- Nutrition
{
 "id": "healthy_diet", "category": "Nutrition", "urgent": False,
 "questions": [
    "What foods are good for a healthy diet?", "What should I eat to stay healthy?",
    "What is a balanced diet?", "healthy foods list", "Which foods are good for health?",
    "How can I eat healthier?", "What is the best diet for a healthy body?",
    "Which vitamins and nutrients do I need?"],
 "keywords": ["diet", "foods", "eat healthy", "balanced diet", "nutrition", "nutrients", "vitamins", "healthy food"],
 "short": "A healthy diet includes a variety of vegetables, fruits, whole grains, protein foods and healthy fats, while limiting sugar, salt and highly processed food.",
 "details": "Good choices are leafy greens, colourful vegetables, fruit, whole grains like oats and brown rice, pulses, nuts, seeds, fish, eggs, dairy or alternatives, and olive or mustard oil in small amounts.",
 "advice": "Fill half your plate with vegetables and fruit, eat regular meals, control portion sizes, drink water instead of sugary drinks and cook at home when you can.",
 "doctor": "Talk to a doctor or dietitian if you have diabetes, kidney disease, food allergies, are pregnant, or want to make big changes to your diet."},
{
 "id": "hydration", "category": "Nutrition", "urgent": False,
 "questions": [
    "How much water should I drink in a day?", "What are the signs of dehydration?",
    "Why is drinking water important?", "dehydration symptoms", "How do I stay hydrated?",
    "I feel thirsty and have a dry mouth", "What happens if I do not drink enough water?",
    "benefits of drinking water"],
 "keywords": ["water", "dehydration", "dehydrated", "hydrated", "thirsty", "hydration"],
 "short": "Water helps control body temperature, digestion, joints and kidney function. Most healthy adults need around 2 to 3 litres of fluids a day, more in hot weather or when exercising.",
 "details": "Signs of dehydration are thirst, dry mouth, dark yellow urine, headache, tiredness, dizziness and passing less urine.",
 "advice": "Sip water through the day, eat fruit and vegetables with high water content, and drink more when it is hot or when you are ill. Pale yellow urine is a good sign.",
 "doctor": "See a doctor if you cannot keep fluids down, feel very dizzy or confused, or pass very little urine. People with heart or kidney disease should ask how much to drink."},
# ---------------------------------------------------------------- Fitness
{
 "id": "exercise_benefits", "category": "Fitness & Exercise", "urgent": False,
 "questions": [
    "What are the benefits of regular exercise?", "Why is exercise good for you?",
    "How does exercise improve health?", "benefits of exercise", "Why should I exercise daily?",
    "What does physical activity do for the body?", "Is walking good exercise?",
    "How does exercise help mental health?"],
 "keywords": ["exercise", "workout", "physical activity", "walking", "gym", "fitness"],
 "short": "Regular exercise strengthens the heart, muscles and bones, helps control weight and improves mood and sleep.",
 "details": "It lowers the risk of heart disease, type 2 diabetes, high blood pressure, some cancers and depression, and improves energy, balance and memory.",
 "advice": "Adults should aim for about 150 minutes of moderate activity a week, such as brisk walking, plus muscle-strengthening exercise on 2 days. Start slowly and increase gradually.",
 "doctor": "Check with a doctor before starting if you have heart disease, chest pain, dizziness, joint problems, are pregnant or have been inactive for a long time."},
{
 "id": "exercise_start", "category": "Fitness & Exercise", "urgent": False,
 "questions": [
    "How do I start exercising as a beginner?", "How much exercise do I need each week?",
    "What is a good beginner workout?", "How can I stay motivated to exercise?",
    "I am overweight how should I start exercising?", "How to prevent injury while exercising?",
    "exercise routine for beginners", "How often should I work out?"],
 "keywords": ["beginner", "start exercising", "routine", "motivated", "injury", "stretching", "warm up"],
 "short": "Beginners should start with light activity such as a 10 to 15 minute daily walk and slowly build up.",
 "details": "A balanced week includes aerobic activity (walking, cycling, swimming), strength exercises and stretching. Warming up and cooling down lower the risk of injury.",
 "advice": "Choose activities you enjoy, set small goals, exercise with a friend, wear proper shoes, drink water and rest between hard sessions.",
 "doctor": "Stop and get medical advice if you feel chest pain, severe breathlessness, dizziness or sharp joint pain during exercise."},
# ---------------------------------------------------------------- Sleep
{
 "id": "sleep_importance", "category": "Sleep Health", "urgent": False,
 "questions": [
    "Why is getting enough sleep important?", "How much sleep do I need?",
    "What happens if I do not get enough sleep?", "benefits of good sleep",
    "Why is sleep important for health?", "How many hours should adults sleep?",
    "What are the effects of sleep deprivation?", "Does lack of sleep affect weight?"],
 "keywords": ["sleep", "sleeping", "sleep deprivation", "hours of sleep", "rest"],
 "short": "Sleep lets the body repair itself, strengthens the immune system and helps memory, learning and mood. Most adults need 7 to 9 hours a night.",
 "details": "Long-term lack of sleep increases the risk of obesity, diabetes, heart disease, depression and accidents, and reduces concentration and immunity.",
 "advice": "Keep a regular sleep schedule, avoid screens and caffeine before bed, keep the bedroom dark and quiet, and get daylight and exercise during the day.",
 "doctor": "See a doctor if you stay very sleepy during the day, snore loudly with pauses in breathing, or sleep problems last for weeks."},
{
 "id": "insomnia", "category": "Sleep Health", "urgent": False,
 "questions": [
    "How can I sleep better at night?", "I cannot fall asleep what should I do?",
    "What causes insomnia?", "tips for better sleep", "Why do I wake up in the middle of the night?",
    "How to fix my sleep schedule?", "insomnia remedies", "I feel tired even after sleeping"],
 "keywords": ["insomnia", "cannot sleep", "can't sleep", "sleepless", "wake up at night", "sleep better"],
 "short": "Insomnia means trouble falling asleep, staying asleep or waking too early. Stress, irregular routines, caffeine, screen use and some health conditions are common causes.",
 "details": "Short-term insomnia often follows stress or a change in routine. Long-term insomnia may be linked to anxiety, depression, pain, sleep apnoea or certain medicines.",
 "advice": "Go to bed and wake up at the same time daily, avoid caffeine in the afternoon, put phones away an hour before bed, keep the room cool and dark, and try relaxation or breathing exercises.",
 "doctor": "See a doctor if poor sleep lasts more than a few weeks or affects your daytime life. Do not rely on sleeping pills without medical advice."},
# ---------------------------------------------------------------- Infections
{
 "id": "flu", "category": "Infections & Diseases", "urgent": False,
 "questions": [
    "What are the symptoms of flu?", "How do I know if I have the flu?",
    "flu symptoms", "What is the difference between cold and flu?",
    "How long does the flu last?", "How is influenza treated?",
    "I have body aches fever and cough, is it flu?", "How can I prevent the flu?"],
 "keywords": ["flu", "influenza", "body aches", "cold and flu"],
 "short": "Flu (influenza) is a viral infection of the nose, throat and lungs. It starts suddenly and feels worse than a common cold.",
 "details": "Symptoms are fever, chills, cough, sore throat, runny nose, muscle and body aches, headache and tiredness. It usually lasts about a week.",
 "advice": "Rest, drink plenty of fluids, stay at home to avoid spreading it, cover coughs and wash hands often. A yearly flu vaccine lowers your risk.",
 "doctor": "See a doctor if you have trouble breathing, chest pain, confusion, or symptoms that improve and then return. Older adults, pregnant women and people with chronic illness should seek early advice."},
{
 "id": "food_poisoning", "category": "Infections & Diseases", "urgent": False,
 "questions": [
    "What are the symptoms of food poisoning?", "What should I do for food poisoning?",
    "I have vomiting and diarrhoea after eating", "How long does food poisoning last?",
    "What causes diarrhea?", "stomach infection symptoms", "How to treat diarrhoea at home?",
    "What should I eat when I have a stomach bug?"],
 "keywords": ["food poisoning", "diarrhea", "diarrhoea", "vomiting", "stomach bug", "loose motion", "stomach infection"],
 "short": "Food poisoning is an illness from eating food or water contaminated with germs. It usually settles in 1 to 3 days.",
 "details": "Symptoms include nausea, vomiting, stomach cramps, watery diarrhoea, mild fever and tiredness. Dehydration is the main danger.",
 "advice": "Sip oral rehydration solution or clean water often, rest, and eat bland foods like rice, banana or toast when you feel able. Avoid alcohol and oily food.",
 "doctor": "See a doctor if there is blood in the stool, high fever, signs of dehydration, symptoms lasting more than 3 days, or if the patient is a baby, an older adult or pregnant."},
# ---------------------------------------------------------------- Dental
{
 "id": "toothache", "category": "Dental Health", "urgent": False,
 "questions": [
    "What causes toothache?", "Why does my tooth hurt?", "How can I relieve a toothache?",
    "toothache causes", "My tooth is very sensitive to cold and hot", "What to do for tooth pain at night?",
    "Why do I have pain in my tooth when chewing?", "Is toothache serious?"],
 "keywords": ["toothache", "tooth", "teeth", "dental pain", "cavity", "tooth pain"],
 "short": "Toothache is most often caused by tooth decay (cavities), but gum disease, a cracked tooth, an abscess or teeth grinding can also cause it.",
 "details": "Pain with hot or cold foods suggests decay or exposed roots. Throbbing pain, swelling or a bad taste may mean an infection or abscess.",
 "advice": "Rinse with warm salt water, brush gently, floss to remove trapped food, and avoid very hot, cold or sugary foods until you see a dentist.",
 "doctor": "See a dentist soon. Seek urgent care for facial swelling, fever, or trouble swallowing or breathing."},
{
 "id": "gum_care", "category": "Dental Health", "urgent": False,
 "questions": [
    "Why do my gums bleed?", "How do I keep my teeth healthy?", "How often should I brush my teeth?",
    "What causes bad breath?", "bleeding gums causes", "How to prevent cavities?",
    "Should I floss every day?", "oral hygiene tips"],
 "keywords": ["gums", "gum", "bleeding gums", "brush", "bad breath", "floss", "oral hygiene"],
 "short": "Bleeding gums are usually a sign of gingivitis, an early gum disease caused by plaque build-up. Bad breath often comes from the same cause.",
 "details": "Other causes are brushing too hard, vitamin deficiencies, smoking and some medicines. Untreated gum disease can lead to loose teeth.",
 "advice": "Brush gently twice a day with fluoride toothpaste, clean between teeth daily, limit sugary snacks, avoid tobacco and visit a dentist every 6 to 12 months.",
 "doctor": "See a dentist if gums bleed for more than a week, are swollen or painful, or if you have constant bad breath or loose teeth."},
# ---------------------------------------------------------------- Eye
{
 "id": "eye_irritation", "category": "Eye Health", "urgent": False,
 "questions": [
    "What can cause eye irritation?", "Why are my eyes red and itchy?", "Why do my eyes burn?",
    "eye irritation causes", "My eyes are watery and red", "What are the symptoms of pink eye?",
    "How to treat red eyes at home?", "Why do my eyes feel dry?"],
 "keywords": ["eye", "eyes", "red eyes", "itchy eyes", "pink eye", "conjunctivitis", "watery eyes", "dry eyes"],
 "short": "Eye irritation is commonly caused by allergies, dry eyes, dust or smoke, contact lens use, or infections such as conjunctivitis (pink eye).",
 "details": "Allergy usually causes itching and watering in both eyes. Infection can cause redness, sticky discharge and swollen eyelids. Dry eyes cause burning and a gritty feeling.",
 "advice": "Do not rub your eyes, wash hands often, remove contact lenses, use a clean cool compress, rest your eyes from screens, and avoid sharing towels.",
 "doctor": "See a doctor quickly for eye pain, loss of vision, sensitivity to light, a chemical splash, injury, or if redness does not improve in a few days."},
{
 "id": "eye_strain", "category": "Eye Health", "urgent": False,
 "questions": [
    "How can I reduce eye strain from screens?", "What is digital eye strain?",
    "My eyes hurt after using the computer", "How to protect my eyes?",
    "What is the 20-20-20 rule?", "headache and tired eyes from screen",
    "How often should I get my eyes checked?", "tips for healthy eyes"],
 "keywords": ["eye strain", "screen", "computer", "20-20-20", "tired eyes", "vision", "eyesight"],
 "short": "Digital eye strain comes from long periods of screen use and causes tired, dry or aching eyes, blurred vision and headaches.",
 "details": "We blink less when looking at screens, which dries the eyes. Poor lighting, glare and uncorrected vision problems make it worse.",
 "advice": "Follow the 20-20-20 rule: every 20 minutes look at something 20 feet (6 metres) away for 20 seconds. Blink often, adjust screen brightness and keep the screen at arm's length.",
 "doctor": "Have an eye test if symptoms continue, or if you notice blurred vision, double vision or trouble seeing at night. Most adults should have an eye check every 1 to 2 years."},
# ---------------------------------------------------------------- Blood
{
 "id": "anemia", "category": "Blood Health", "urgent": False,
 "questions": [
    "What are common symptoms of anemia?", "What are the signs of anaemia?",
    "anemia symptoms", "Why do I feel weak and look pale?", "What causes low hemoglobin?",
    "How can I increase my hemoglobin?", "What foods help with iron deficiency?",
    "I feel tired and dizzy all the time, could it be anemia?"],
 "keywords": ["anemia", "anaemia", "hemoglobin", "haemoglobin", "iron deficiency", "pale", "low iron"],
 "short": "Anaemia means the blood has too few healthy red blood cells or too little haemoglobin to carry oxygen around the body.",
 "details": "Common symptoms are tiredness, weakness, pale skin, dizziness, headache, shortness of breath, cold hands and feet and a fast heartbeat. Iron deficiency is the most common cause.",
 "advice": "Eat iron-rich foods such as leafy greens, pulses, eggs, meat, dates and fortified cereals, and add vitamin C foods like lemon or orange to help absorption.",
 "doctor": "See a doctor for a blood test to find the cause before taking iron tablets. Seek urgent care for chest pain, fainting or severe breathlessness."},
{
 "id": "cholesterol", "category": "Blood Health", "urgent": False,
 "questions": [
    "What causes high cholesterol?", "How can I lower my cholesterol?",
    "What are the symptoms of high cholesterol?", "cholesterol levels explained",
    "Which foods reduce cholesterol?", "What is the difference between good and bad cholesterol?",
    "Why is high cholesterol dangerous?", "Do I need a cholesterol test?"],
 "keywords": ["cholesterol", "ldl", "hdl", "lipid", "triglycerides"],
 "short": "Cholesterol is a fatty substance in the blood. Too much LDL (bad) cholesterol can build up in the arteries and raise the risk of heart attack and stroke.",
 "details": "High cholesterol usually has no symptoms and is found by a blood test. Causes include an unhealthy diet, lack of exercise, obesity, smoking, diabetes and family history.",
 "advice": "Eat more vegetables, fruit, oats, pulses and nuts, cut down on fried food, fatty meat and butter, stay active, stop smoking and keep a healthy weight.",
 "doctor": "Ask your doctor for a cholesterol test, especially if you are over 40 or have diabetes, high blood pressure or a family history of heart disease."},
# ---------------------------------------------------------------- Symptoms
{
 "id": "dizziness", "category": "Symptoms", "urgent": False,
 "questions": [
    "What causes dizziness?", "Why do I feel dizzy when I stand up?", "I feel lightheaded what should I do?",
    "dizziness causes", "Why is the room spinning?", "What is vertigo?",
    "I feel dizzy and weak", "When is dizziness serious?"],
 "keywords": ["dizziness", "dizzy", "lightheaded", "light headed", "vertigo", "spinning", "faint"],
 "short": "Dizziness has many causes, including dehydration, low blood sugar, low blood pressure, standing up too quickly, anaemia, ear problems, anxiety and some medicines.",
 "details": "Vertigo is a spinning feeling, often from an inner-ear problem. Light-headedness feels like you might faint and is often linked to blood pressure, blood sugar or fluids.",
 "advice": "Sit or lie down, drink water, eat something, and stand up slowly. Avoid driving or climbing until it passes.",
 "doctor": "Get emergency help if dizziness comes with chest pain, fainting, trouble speaking, weakness, severe headache or vision changes. See a doctor if it keeps coming back."},
{
 "id": "fatigue", "category": "Symptoms", "urgent": False,
 "questions": [
    "Why do I feel tired all the time?", "What causes constant fatigue?", "I have no energy what could be the reason?",
    "fatigue causes", "Why am I always sleepy?", "How can I boost my energy?",
    "I feel weak and exhausted", "tiredness and weakness reasons"],
 "keywords": ["tired", "fatigue", "exhausted", "no energy", "weakness", "weak", "sleepy"],
 "short": "Feeling tired all the time can come from poor sleep, stress, an unbalanced diet, lack of exercise or an underlying problem such as anaemia, thyroid disease, diabetes or depression.",
 "details": "Other causes include infections, vitamin D or B12 deficiency, sleep apnoea, certain medicines and long-term illnesses.",
 "advice": "Sleep 7 to 9 hours, eat regular balanced meals, drink water, exercise lightly, limit caffeine and alcohol and find time to relax.",
 "doctor": "See a doctor if tiredness lasts more than 2 weeks, or comes with weight loss, fever, shortness of breath, low mood or other new symptoms. Basic blood tests can help find the cause."},
# ---------------------------------------------------------------- First Aid
{
 "id": "minor_burn", "category": "First Aid", "urgent": False,
 "questions": [
    "What should I do for a minor burn?", "How do I treat a burn at home?", "First aid for burns",
    "I burned my hand with hot water", "How to treat a small burn?", "Should I put ice or toothpaste on a burn?",
    "burn first aid", "How long should I cool a burn?"],
 "keywords": ["burn", "burns", "burned", "scald", "scalded", "blister"],
 "short": "For a minor burn, cool the area right away under cool running water for 20 minutes.",
 "details": "Remove rings or tight items near the burn before swelling starts. Do not use ice, butter, toothpaste or oil, and do not burst blisters.",
 "advice": "After cooling, cover the burn loosely with a clean non-stick dressing or cling film, keep it clean and dry, and watch for signs of infection.",
 "doctor": "Get medical help for burns larger than your palm, on the face, hands, feet or genitals, deep or white or charred burns, chemical or electrical burns, and burns on babies or older adults."},
{
 "id": "minor_cut", "category": "First Aid", "urgent": False,
 "questions": [
    "How do I treat a minor cut?", "What should I do for a small wound?", "How to stop bleeding from a cut?",
    "first aid for cuts and scrapes", "My finger is bleeding what should I do?", "How to clean a wound?",
    "When does a cut need stitches?", "What to do for a nosebleed?"],
 "keywords": ["cut", "wound", "bleeding", "scrape", "nosebleed", "stitches", "injury"],
 "short": "To treat a minor cut, first wash your hands, then press a clean cloth firmly on the wound for several minutes to stop bleeding.",
 "details": "Rinse the wound with clean running water, gently clean around it with soap, and cover it with a clean bandage. Change the dressing daily.",
 "advice": "Keep the wound clean and dry and check that your tetanus vaccination is up to date. For a nosebleed, sit forward and pinch the soft part of the nose for 10 minutes.",
 "doctor": "Get medical care if bleeding does not stop after 10 minutes of pressure, the cut is deep or gaping, caused by an animal bite or dirty object, or shows redness, pus or fever. Call emergency services for heavy bleeding."},
# ---------------------------------------------------------------- Women's health
{
 "id": "menstrual_cramps", "category": "Women's Health", "urgent": False,
 "questions": [
    "What are common symptoms of menstrual cramps?", "Why do I get period pain?", "How can I relieve menstrual cramps?",
    "period cramps remedies", "What causes painful periods?", "My periods are very painful what should I do?",
    "menstrual pain symptoms", "Is it normal to have cramps during periods?"],
 "keywords": ["menstrual", "period pain", "periods", "cramps", "menstruation", "dysmenorrhea"],
 "short": "Menstrual cramps are throbbing or aching pains in the lower abdomen that start just before or during a period. They are very common.",
 "details": "They can spread to the lower back and thighs and may come with nausea, loose stools, headache and tiredness. They are caused by the womb contracting.",
 "advice": "A warm heat pad, gentle exercise, rest, warm drinks and relaxation can help. Ask a doctor or pharmacist about suitable pain relief.",
 "doctor": "See a doctor if the pain is severe, gets worse over time, stops you from doing daily activities, comes with very heavy bleeding, or starts after age 25."},
{
 "id": "pregnancy_signs", "category": "Women's Health", "urgent": False,
 "questions": [
    "What are the early signs of pregnancy?", "How do I know if I am pregnant?", "pregnancy symptoms",
    "I missed my period am I pregnant?", "What should I eat during pregnancy?", "What is morning sickness?",
    "How to take care of health during pregnancy?", "When should I take a pregnancy test?"],
 "keywords": ["pregnancy", "pregnant", "missed period", "morning sickness", "prenatal"],
 "short": "A missed period is often the first sign of pregnancy. Other early signs include tender breasts, nausea, tiredness and needing to pass urine more often.",
 "details": "You may also notice mood changes, food cravings or dislikes and mild cramping. A home pregnancy test is most reliable from the first day of a missed period.",
 "advice": "If pregnant, start folic acid as advised by your doctor, eat a balanced diet, avoid alcohol and smoking, and attend regular antenatal check-ups.",
 "doctor": "Book an appointment to confirm pregnancy. Seek urgent care for heavy bleeding, severe abdominal pain, fever, or reduced baby movements later in pregnancy."},
# ---------------------------------------------------------------- Child health
{
 "id": "child_fever", "category": "Child Health", "urgent": False,
 "questions": [
    "What should I do if a child has a fever?", "My child has a fever, what should I do?", "How to treat fever in kids?",
    "baby has high temperature", "When should I take my child with fever to a doctor?", "child fever home care",
    "My toddler feels hot and is cranky", "Can I give paracetamol to my child?"],
 "keywords": ["child fever", "baby fever", "kid fever", "toddler", "my child", "my baby", "infant"],
 "short": "Fever in children is common and is usually caused by a viral infection. Keep the child comfortable, rested and well hydrated.",
 "details": "Dress the child in light clothes, offer plenty of fluids or breast milk and check their temperature. Never give aspirin to children. Ask a doctor or pharmacist about the right medicine and dose for the child's age and weight.",
 "advice": "Watch how the child is behaving: drinking, playing and responding normally is a good sign. Do not use cold baths or alcohol rubs.",
 "doctor": "Take a baby under 3 months to a doctor straight away for any fever of 38 C (100.4 F) or higher. See a doctor if a child has fever for more than 3 days, a rash, stiff neck, seizure, trouble breathing, refuses to drink, or is very drowsy."},
{
 "id": "child_dehydration", "category": "Child Health", "urgent": False,
 "questions": [
    "How do I know if my child is dehydrated?", "My child has diarrhoea and vomiting what should I do?", "How to give fluids to a sick child?",
    "signs of dehydration in babies", "What is ORS and when should I use it?", "My baby is not drinking milk",
    "How much should a child drink when sick?", "child diarrhea treatment"],
 "keywords": ["child dehydration", "oral rehydration", "ors", "baby not drinking", "child diarrhoea", "child diarrhea", "child vomiting"],
 "short": "Children can become dehydrated quickly when they have vomiting, diarrhoea or fever, so give small frequent sips of fluid.",
 "details": "Signs include a dry mouth, no tears when crying, sunken eyes, fewer wet nappies or very little urine, sleepiness and cold hands and feet.",
 "advice": "Use oral rehydration solution (ORS) as directed on the packet, keep breastfeeding or feeding babies, and offer fluids in small sips every few minutes.",
 "doctor": "Take the child to a doctor urgently if there are signs of dehydration, blood in the stool, repeated vomiting, severe tummy pain, or if the child is a young baby or very sleepy."},
# ---------------------------------------------------------------- Older adults
{
 "id": "fall_prevention", "category": "Older Adult Health", "urgent": False,
 "questions": [
    "How can older adults reduce their risk of falling?", "How to prevent falls in elderly people?", "fall prevention tips for seniors",
    "My grandmother keeps falling what should we do?", "How to make a home safe for older adults?", "Why do older people fall so often?",
    "exercises to improve balance in old age", "elderly safety at home"],
 "keywords": ["fall", "falls", "falling", "elderly", "older adults", "seniors", "balance", "grandmother", "grandfather"],
 "short": "Falls are a leading cause of injury in older adults, but most can be prevented with simple steps.",
 "details": "Common causes are weak muscles, poor balance, poor eyesight, some medicines, low blood pressure and hazards at home such as loose rugs, poor lighting and wet floors.",
 "advice": "Stay active with balance and strength exercises like walking or tai chi, remove loose rugs, add good lighting and grab bars, wear non-slip footwear, and have eyesight and medicines reviewed regularly.",
 "doctor": "See a doctor after any fall, especially if there is a head injury, severe pain or confusion. Call emergency services for loss of consciousness or if the person cannot move."},
{
 "id": "memory_changes", "category": "Older Adult Health", "urgent": False,
 "questions": [
    "Is forgetfulness normal in old age?", "What are the early signs of dementia?", "How can older adults keep their memory sharp?",
    "My father is becoming forgetful", "dementia symptoms", "What is the difference between normal ageing and Alzheimer's?",
    "brain health tips for seniors", "How to care for an older adult with memory loss?"],
 "keywords": ["dementia", "alzheimer", "alzheimers", "forgetful", "forgetfulness", "memory loss", "memory"],
 "short": "Mild forgetfulness, like misplacing keys now and then, can be a normal part of ageing. Memory loss that disrupts daily life is not normal and needs medical review.",
 "details": "Warning signs of dementia include repeatedly asking the same questions, getting lost in familiar places, trouble with familiar tasks, confusion about time and personality changes.",
 "advice": "Stay physically and socially active, keep the mind busy with reading or puzzles, eat a healthy diet, sleep well and manage blood pressure, diabetes and hearing problems.",
 "doctor": "Book a doctor visit if memory problems are getting worse or affecting daily life. Some causes, such as vitamin deficiency or thyroid problems, are treatable."},
{
 "id": "weight_management", "category": "Nutrition", "urgent": False,
 "questions": [
    "How can I lose weight safely?", "How to lose weight fast?", "What is a healthy weight?",
    "Why am I gaining weight?", "weight loss tips", "How to maintain a healthy weight?",
    "What is BMI?", "Is crash dieting safe?"],
 "keywords": ["lose weight", "weight loss", "weight gain", "gaining weight", "obesity", "overweight", "bmi", "crash diet"],
 "short": "Safe weight loss is slow and steady, usually about 0.5 to 1 kg a week. Crash diets and skipping meals are not safe and the weight usually returns.",
 "details": "Weight depends on food, activity, sleep, stress, medicines and medical conditions such as thyroid problems. BMI between 18.5 and 24.9 is considered healthy for most adults, but it is only a guide.",
 "advice": "Eat more vegetables, fruit, whole grains and protein, cut sugary drinks and fried snacks, control portions, walk or exercise most days and sleep 7 to 9 hours.",
 "doctor": "Talk to a doctor or dietitian before a big diet change, if you have a medical condition, or if you gain or lose weight without trying."},
{
 "id": "back_pain", "category": "Symptoms", "urgent": False,
 "questions": [
    "What causes back pain?", "How can I relieve lower back pain?", "My back hurts when I sit for long",
    "back pain exercises", "When is back pain serious?", "Why do I have pain in my lower back?",
    "How to prevent back pain?", "neck and shoulder pain from desk work"],
 "keywords": ["back pain", "backache", "lower back", "spine", "neck pain", "shoulder pain", "sciatica"],
 "short": "Most back pain comes from muscle strain, poor posture, long hours of sitting or lifting heavy objects, and usually improves within a few weeks.",
 "details": "Other causes include disc problems, arthritis and, less often, infections or other illnesses. Pain that spreads down the leg may be sciatica.",
 "advice": "Stay gently active instead of bed rest, use heat packs, sit with back support, take movement breaks every 30 minutes, strengthen your core and lift with your knees.",
 "doctor": "See a doctor if pain lasts more than 4 to 6 weeks, or comes with leg weakness, numbness, fever or weight loss. Get emergency help for loss of bladder or bowel control, or pain after a serious fall."},
{
 "id": "indigestion", "category": "Symptoms", "urgent": False,
 "questions": [
    "What causes acidity and heartburn?", "How to treat indigestion?", "I have gas and bloating after meals",
    "What causes stomach pain?", "How can I relieve constipation?", "acid reflux symptoms",
    "Why do I feel nauseous after eating?", "stomach ache after eating"],
 "keywords": ["acidity", "heartburn", "indigestion", "bloating", "gas", "constipation", "acid reflux", "stomach pain", "stomach ache", "stomachache", "nausea", "abdominal pain"],
 "short": "Indigestion, acidity, bloating and constipation are common digestive problems, usually caused by eating too fast, large or oily meals, low fibre or water intake, stress or lack of activity.",
 "details": "Acid reflux causes a burning feeling in the chest or throat, often after meals or when lying down. Constipation means hard stools or fewer than three bowel movements a week.",
 "advice": "Eat smaller meals slowly, avoid oily and spicy food and late-night meals, drink water, eat fibre-rich foods like fruit, vegetables and whole grains, and stay active. Do not lie down right after eating.",
 "doctor": "See a doctor if symptoms last more than 2 weeks, or you have blood in the stool, black stools, vomiting, unexplained weight loss or trouble swallowing. Get emergency help for severe or sudden stomach pain."},
{
 "id": "skin_rash", "category": "Symptoms", "urgent": False,
 "questions": [
    "What causes a skin rash?", "Why is my skin itchy?", "How can I treat acne?",
    "I have red itchy patches on my skin", "skin allergy symptoms", "How do I care for dry skin?",
    "What causes pimples?", "rash on my body what to do"],
 "keywords": ["rash", "itchy skin", "itching", "acne", "pimples", "skin allergy", "dry skin", "eczema", "skin"],
 "short": "Skin rashes and itching can be caused by allergies, heat, dry skin, eczema, infections, insect bites or reactions to soaps and medicines. Acne is caused by blocked oil glands and hormone changes.",
 "details": "Allergic rashes are often itchy and red with raised bumps. Infections may be painful, warm or have pus. Dry skin looks flaky and feels tight.",
 "advice": "Avoid scratching and known triggers, use mild soap, moisturise regularly, wear loose cotton clothes, keep skin clean and do not squeeze pimples.",
 "doctor": "See a doctor if the rash is spreading fast, painful, blistering, has pus, comes with fever, or lasts more than 2 weeks. Get emergency help if there is facial swelling or trouble breathing."},
{
 "id": "joint_pain", "category": "Older Adult Health", "urgent": False,
 "questions": [
    "What causes joint pain?", "How can I relieve knee pain?", "What are the symptoms of arthritis?",
    "My knees hurt when I climb stairs", "joint pain in old age", "What is the difference between osteoarthritis and rheumatoid arthritis?",
    "How to keep bones and joints healthy?", "What causes swollen painful joints?"],
 "keywords": ["joint pain", "knee pain", "arthritis", "osteoarthritis", "joints", "swollen joints", "bones", "osteoporosis"],
 "short": "Joint pain is often caused by injury, overuse or arthritis. Osteoarthritis is wear and tear of the joints and is common with age, while rheumatoid arthritis is an immune condition.",
 "details": "Signs of arthritis include pain, stiffness (especially in the morning), swelling and reduced movement. Extra body weight puts more strain on the knees and hips.",
 "advice": "Keep moving with low-impact exercise like walking, swimming or cycling, maintain a healthy weight, use heat or cold packs, and eat enough calcium and vitamin D for bone health.",
 "doctor": "See a doctor if a joint is hot, red and swollen, pain lasts more than a few weeks, stiffness lasts more than 30 minutes in the morning, or you cannot move the joint."},
{
 "id": "uti", "category": "Women's Health", "urgent": False,
 "questions": [
    "What are the symptoms of a urinary tract infection?", "Why does it burn when I urinate?", "How can I prevent UTI?",
    "I have to urinate frequently and it hurts", "uti treatment", "What causes urinary infection?",
    "burning sensation while passing urine", "Is cloudy urine a sign of infection?"],
 "keywords": ["uti", "urinary", "urine", "urinate", "urination", "burning urine", "bladder"],
 "short": "A urinary tract infection (UTI) is a bacterial infection of the bladder or urinary tract. It is common, especially in women, and needs treatment from a doctor.",
 "details": "Symptoms include burning when passing urine, needing to go often, cloudy or strong-smelling urine, lower tummy pain and sometimes blood in the urine.",
 "advice": "Drink plenty of water, do not hold urine for long, urinate after sex, wipe from front to back and keep the genital area clean.",
 "doctor": "See a doctor for a urine test and treatment. Get urgent care for fever, shaking, back or side pain, vomiting, or if you are pregnant or the patient is a child or older adult."},
# ---------------------------------------------------------------- Hygiene
{
 "id": "infection_prevention", "category": "Health & Hygiene", "urgent": False,
 "questions": [
    "How can I prevent the spread of infections?", "How to stop germs from spreading?", "infection prevention tips",
    "How can I avoid catching a cold?", "How do I protect my family from infections?", "What can I do to avoid getting sick?",
    "ways to prevent spreading disease", "How do viruses spread?"],
 "keywords": ["prevent infection", "spread of infection", "germs", "spread", "avoid getting sick", "contagious", "disinfect"],
 "short": "You can lower the spread of infections by washing hands often, covering coughs and sneezes, staying home when ill and keeping vaccinations up to date.",
 "details": "Germs spread through droplets from coughs and sneezes, contaminated hands and surfaces, food and water, and close contact.",
 "advice": "Wash hands with soap for 20 seconds, cover your mouth with a tissue or elbow, avoid touching your face, do not share personal items, clean frequently touched surfaces and wear a mask when you are sick or in crowded places.",
 "doctor": "See a doctor if you or a family member has a high fever, difficulty breathing or symptoms that are getting worse."},
{
 "id": "handwashing", "category": "Health & Hygiene", "urgent": False,
 "questions": [
    "How should I wash my hands properly?", "When should I wash my hands?", "Is hand sanitizer as good as soap?",
    "handwashing steps", "Why is hand washing important?", "How long should I wash my hands?",
    "personal hygiene tips", "How to keep good hygiene every day?"],
 "keywords": ["hand wash", "handwashing", "wash hands", "sanitizer", "hygiene", "soap"],
 "short": "Washing your hands with soap and clean water is one of the best ways to prevent illness.",
 "details": "Wet your hands, lather with soap including backs of hands, between fingers and under nails, scrub for at least 20 seconds, rinse well and dry with a clean towel.",
 "advice": "Wash before eating or cooking, after using the toilet, after coughing or sneezing, after touching animals or rubbish, and after caring for someone sick. Use an alcohol-based sanitizer (at least 60 percent alcohol) when soap is not available.",
 "doctor": "See a doctor if frequent washing causes painful cracked skin or rashes on your hands."},
# ---------------------------------------------------------------- Prevention
{
 "id": "diabetes_risk", "category": "Prevention", "urgent": False,
 "questions": [
    "How can I reduce my risk of diabetes?", "How to prevent type 2 diabetes?", "What are the symptoms of diabetes?",
    "diabetes prevention tips", "What are the early signs of diabetes?", "I urinate a lot and feel thirsty, is it diabetes?",
    "Which foods should I avoid to prevent diabetes?", "Who is at risk of diabetes?"],
 "keywords": ["diabetes", "diabetic", "blood sugar", "sugar level", "insulin", "glucose"],
 "short": "Type 2 diabetes can often be prevented or delayed with healthy lifestyle habits, even if you have a family history.",
 "details": "Warning signs include frequent urination, increased thirst, constant hunger, tiredness, blurred vision, slow-healing wounds and unexplained weight loss. Risk rises with excess weight, inactivity, age and family history.",
 "advice": "Keep a healthy weight, be active for about 150 minutes a week, eat plenty of vegetables, whole grains and pulses, cut down on sugary drinks and sweets, and do not smoke.",
 "doctor": "Get a blood sugar test if you have symptoms or risk factors, especially over age 35. See a doctor urgently for confusion, vomiting, fruity-smelling breath or very high blood sugar."},
{
 "id": "preventive_checkups", "category": "Prevention", "urgent": False,
 "questions": [
    "What health check-ups should I get regularly?", "Why are regular health check-ups important?", "Which vaccines do adults need?",
    "preventive health screening", "How often should I get a health check-up?", "How can I stay healthy as I age?",
    "What screening tests are important after 40?", "Are vaccines safe?"],
 "keywords": ["checkup", "check-up", "checkups", "screening", "vaccine", "vaccines", "vaccination", "immunization", "preventive"],
 "short": "Regular check-ups and vaccinations help find problems early and prevent serious diseases.",
 "details": "Common checks include blood pressure, blood sugar, cholesterol, weight and BMI, eye and dental exams, and age-specific screening such as cancer screening. Vaccines protect against diseases like flu, tetanus, hepatitis B and others.",
 "advice": "Keep a record of your vaccines, eat well, stay active, avoid tobacco, limit alcohol and ask your doctor which tests suit your age and family history.",
 "doctor": "Talk to your doctor about a personal check-up schedule, especially if you are over 40, pregnant, or have a chronic condition or family history of disease."},
]

# 46-category extension -------------------------------------------------------
from chatbot.health_qa.knowledge_extra import EXTRA_TOPICS, EXTRA_QUESTIONS   # noqa: E402
from chatbot.health_qa.taxonomy import TOPIC_CATEGORIES         # noqa: E402

TOPICS = TOPICS + EXTRA_TOPICS
for _t in TOPICS:
    _t["questions"] = list(_t["questions"]) + EXTRA_QUESTIONS.get(_t["id"], [])
    _t["categories"] = TOPIC_CATEGORIES[_t["id"]]               # KeyError = topic without a category

# helper lookups --------------------------------------------------------------
TOPIC_BY_ID = {t["id"]: t for t in TOPICS}
CATEGORIES = sorted({t["category"] for t in TOPICS})

# The 20 example questions shown on the Comparison page: (emoji, category, question, expected topic id)
PRESET_QUESTIONS = [
    ("🩺", "General Medical", "What are the common symptoms of fever?", "fever"),
    ("💊", "Medication", "What precautions should be taken when taking medicine?", "medicine_precautions"),
    ("🚨", "Emergency", "What should I do if I have severe chest pain?", "chest_pain_emergency"),
    ("🫁", "Respiratory Health", "What are the symptoms of asthma?", "asthma"),
    ("❤️", "Heart Health", "What are the warning signs of heart problems?", "heart_warning_signs"),
    ("🧠", "Mental Health", "What are common signs of stress?", "stress_signs"),
    ("🍎", "Nutrition", "What foods are good for a healthy diet?", "healthy_diet"),
    ("🏃", "Fitness & Exercise", "What are the benefits of regular exercise?", "exercise_benefits"),
    ("😴", "Sleep Health", "Why is getting enough sleep important?", "sleep_importance"),
    ("🦠", "Infections & Diseases", "What are the symptoms of flu?", "flu"),
    ("🦷", "Dental Health", "What causes toothache?", "toothache"),
    ("👁️", "Eye Health", "What can cause eye irritation?", "eye_irritation"),
    ("🩸", "Blood Health", "What are common symptoms of anemia?", "anemia"),
    ("🤒", "Symptoms", "What causes dizziness?", "dizziness"),
    ("🧴", "First Aid", "What should I do for a minor burn?", "minor_burn"),
    ("👩", "Women's Health", "What are common symptoms of menstrual cramps?", "menstrual_cramps"),
    ("👶", "Child Health", "What should I do if a child has a fever?", "child_fever"),
    ("🧓", "Older Adult Health", "How can older adults reduce their risk of falling?", "fall_prevention"),
    ("🧼", "Health & Hygiene", "How can I prevent the spread of infections?", "infection_prevention"),
    ("🛡️", "Prevention", "How can I reduce my risk of diabetes?", "diabetes_risk"),
    ("🩺", "Doctor Guidance", "Which doctor treats thyroid problems?", "doctor_thyroid"),
    ("🧑‍⚕️", "Doctor Guidance", "What doctor should I visit for persistent stomach pain?", "doctor_digestive"),
    ("😟", "Stress and Anxiety", "Why do I feel anxious all the time?", "anxiety_signs"),
    ("🧪", "Medical Tests", "What does a CBC blood test measure?", "blood_tests_reports"),
    ("🍬", "Diabetes", "What is diabetes?", "diabetes_basics"),
    ("🆘", "Emergency Signs", "What are the warning signs of a medical emergency?", "emergency_warning_signs_general"),
]
