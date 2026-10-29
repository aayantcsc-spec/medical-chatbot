# -*- coding: utf-8 -*-
"""
localized.py - Hindi (Devanagari) and Hinglish (Roman) presentation text for the chat reply.

Scope and honesty
-----------------
* The curated knowledge base (knowledge.py / knowledge_extra.py) is written in English only.
* TOPIC_I18N holds hand-written Hindi and Hinglish versions of the `short`, `advice` and `doctor`
  text of the most common topics. They are faithful renderings of the English KB text - no new
  medical claims were added. They have NOT been reviewed by a clinician or a professional
  translator; review them before any public deployment.
* A topic that has no entry here is shown in English with a short note saying so. Nothing is
  machine-translated at run time, and a missing translation is never invented.
* Safety notices (112 / Tele-MANAS), headings, greetings and the doctor-specialty guidance exist
  in all three languages.
"""

LANGS = ("en", "hinglish", "hi")

# ------------------------------------------------------------------------------- UI strings
STR = {
    "en": {
        "overview": "Overview", "causes": "Possible causes", "do": "What you can do", "seek": "When to seek medical help",
        "warn": "Warning signs", "doctor": "Doctor to consult", "follow": "To guide you better, could you tell me",
        "med": "Medicine precautions", "test": "About tests and reports", "life": "Lifestyle guidance",
        "key": "Key points", "also": "You also mentioned", "while": "While you wait for help",
        "disclaimer": "This is general health information, not a diagnosis. A qualified clinician can assess your own situation.",
        "footer": "General health information · Not a diagnosis",
        "no_answer": "I don't have a reliable answer to this as written. Answers are clearer when the question names the main symptom or "
                     "health topic, how long it has lasted and whether it is getting worse. For advice about your own situation, please see a doctor.",
        "uncertain_short": "These symptoms alone cannot identify the cause.",
        "uncertain": "These are only possibilities - many different things can cause these symptoms, and I cannot tell which applies to you.",
        "en_only": "Detailed information on this topic is currently available in English only, so the rest of this answer is in English.",
        "fallback": "I am not sure I understood that as a health question. I can help with common symptoms, first aid, medicine safety, "
                    "nutrition, exercise, sleep, mental wellbeing, tests, prevention and which doctor to see. Could you describe it a little differently?",
        "clarify": "I want to be sure I understand. Which symptom or body area is bothering you, how long has it been going on, and is it getting worse?",
        "oos": "That does not look like a health question, so I will not guess. I can help with symptoms, first aid, medicines, nutrition, sleep, "
               "mental wellbeing, tests and which doctor to see.",
        "multi_intro": "You mentioned more than one symptom ({symptoms}). These can occur together with several different conditions, such as an infection, and on their own they cannot identify the cause, so I cannot say what is behind them.",
        "multi_note": "Tell me how long you have had them, whether they are getting worse, and if anything else is happening, and I can guide you better.",
        "first_step": "Best first step", "see_sooner": "See a doctor sooner if", "not_dx": "A specialty suggestion is not a diagnosis.",
        "emerg_not_routine": "Do not wait for a routine appointment if you have warning signs - call 112 or go to the nearest emergency department.",
        "emergency": "This may be a medical emergency. Please call your local emergency number now (112 in India; 108 for an ambulance in many states) "
                     "or go to the nearest hospital. Do not wait for an online answer.",
        "selfharm": "I am really sorry you are feeling this much pain, and I am glad you said it. You deserve support right now. If you might act on these "
                    "thoughts, please call 112 or go to the nearest emergency department. You can also call Tele-MANAS, India's free 24x7 mental health "
                    "helpline, on 14416 or 1800-891-4416, and please tell someone you trust so you are not alone tonight.",
        "mentalcrisis": "This sounds like a mental health emergency, and you deserve help right now. Please call 112 or go to the nearest emergency "
                        "department. Tele-MANAS (free, 24x7) is on 14416 or 1800-891-4416. If you are with someone who is in crisis, stay with them and keep everyone safe.",
        "emerg_close": "This is general safety information, not a diagnosis. It does not replace emergency care.",
        "support": "Free, confidential support is available any time from Tele-MANAS (Government of India) on 14416 or 1800-891-4416. If you ever feel unsafe, call 112.",
    },
    "hinglish": {
        "overview": "Overview", "causes": "Ho sakne wale karan", "do": "Aap kya kar sakte hain", "seek": "Doctor ko kab dikhayein",
        "warn": "Khatre ke sanket", "doctor": "Kaun sa doctor dikhayein", "follow": "Aapko behtar guide karne ke liye, kya aap bata sakte hain",
        "med": "Dawai ke baare mein savdhaniyan", "test": "Tests aur reports ke baare mein", "life": "Lifestyle guidance",
        "key": "Zaroori baatein", "also": "Aapne ye bhi bataya", "while": "Madad aane tak",
        "disclaimer": "Ye general health jaankari hai, diagnosis nahi hai. Aapki apni situation ko ek qualified doctor hi sahi se dekh sakta hai.",
        "footer": "General health jaankari · Diagnosis nahi",
        "no_answer": "Is sawal ka mere paas bharosemand jawab nahi hai. Jawab tab behtar hota hai jab sawal mein mukhya symptom ya health topic, "
                     "kitne din se hai aur kya badh raha hai, ye likha ho. Apni situation ke liye kripya doctor se milein.",
        "uncertain_short": "Sirf in symptoms se karan pata nahi chal sakta.",
        "uncertain": "Ye sirf sambhavnayein hain - in symptoms ke kai alag karan ho sakte hain, aur main nahi bata sakta ki aapke case mein kaun sa hai.",
        "en_only": "Is topic ki detailed jaankari abhi sirf English mein hai, isliye jawab ka baaki hissa English mein hai.",
        "fallback": "Mujhe pakka nahi ki main ise health question ki tarah samajh paya. Main common symptoms, first aid, dawai ki safety, khana-peena, "
                    "exercise, neend, mental wellbeing, tests, bachav aur kaun sa doctor dikhana hai - in sab mein help kar sakta hoon. Kya aap ise thoda alag tarah se likh sakte hain?",
        "clarify": "Main sahi se samajhna chahta hoon. Kaun sa symptom ya body ka kaun sa hissa pareshan kar raha hai, kitne time se hai, aur kya badhta ja raha hai?",
        "oos": "Ye health question nahi lagta, isliye main andaza nahi lagaunga. Main symptoms, first aid, dawai, khana-peena, neend, mental wellbeing, "
               "tests aur kaun sa doctor dikhana hai - in mein help kar sakta hoon.",
        "multi_intro": "Aapne ek se zyada symptoms bataye hain ({symptoms}). Ye kai alag wajah se ek saath ho sakte hain, isliye main nahi bata sakta ki inke peeche kya hai.",
        "multi_note": "Mujhe bataiye ye kitne din se hain, kya badh rahe hain, aur kya aur kuch ho raha hai - phir main behtar guide kar paunga.",
        "first_step": "Sabse pehla kadam", "see_sooner": "In sthitiyon mein jaldi doctor ko dikhayein", "not_dx": "Specialty ka suggestion diagnosis nahi hota.",
        "emerg_not_routine": "Agar khatre ke sanket hon to routine appointment ka intezaar na karein - 112 par call karein ya nazdeeki emergency department jayein.",
        "emergency": "Ye medical emergency ho sakti hai. Kripya abhi 112 par call karein (kai rajyon mein ambulance ke liye 108) ya nazdeeki hospital jayein. "
                     "Online jawab ka intezaar na karein.",
        "selfharm": "Mujhe bahut dukh hai ki aap itna dard mehsoos kar rahe hain, aur achha hai ki aapne bataya. Aap abhi support ke haqdaar hain. Agar in vicharon par "
                    "amal karne ka khatra ho to kripya 112 par call karein ya nazdeeki emergency department jayein. Aap Tele-MANAS (Bharat sarkar ki free 24x7 mental health "
                    "helpline) par bhi 14416 ya 1800-891-4416 par call kar sakte hain. Kripya kisi apne ko bata dein taaki aap aaj raat akele na rahein.",
        "mentalcrisis": "Ye mental health emergency lagti hai, aur aap abhi madad ke haqdaar hain. Kripya 112 par call karein ya nazdeeki emergency department jayein. "
                        "Tele-MANAS (free, 24x7) 14416 ya 1800-891-4416 par hai. Agar aap kisi aise vyakti ke saath hain jo crisis mein hai to unke saath rahein aur sabko surakshit rakhein.",
        "emerg_close": "Ye general safety jaankari hai, diagnosis nahi. Ye emergency ilaaj ki jagah nahi le sakti.",
        "support": "Tele-MANAS (Bharat sarkar) se free aur confidential support kisi bhi samay 14416 ya 1800-891-4416 par mil sakta hai. Khud ko unsafe mehsoos karein to 112 par call karein.",
    },
    "hi": {
        "overview": "संक्षेप में", "causes": "संभावित कारण", "do": "आप क्या कर सकते हैं", "seek": "डॉक्टर को कब दिखाएं",
        "warn": "खतरे के संकेत", "doctor": "कौन से डॉक्टर को दिखाएं", "follow": "आपको बेहतर मार्गदर्शन देने के लिए, क्या आप बता सकते हैं",
        "med": "दवा से जुड़ी सावधानियां", "test": "जांच और रिपोर्ट के बारे में", "life": "जीवनशैली संबंधी सुझाव",
        "key": "ज़रूरी बातें", "also": "आपने यह भी बताया", "while": "मदद आने तक",
        "disclaimer": "यह सामान्य स्वास्थ्य जानकारी है, निदान (डायग्नोसिस) नहीं। आपकी अपनी स्थिति को योग्य डॉक्टर ही सही तरह से देख सकते हैं।",
        "footer": "सामान्य स्वास्थ्य जानकारी · निदान नहीं",
        "no_answer": "इस सवाल का मेरे पास भरोसेमंद जवाब नहीं है। जवाब तब बेहतर होता है जब सवाल में मुख्य लक्षण या स्वास्थ्य विषय, "
                     "कितने दिनों से है और क्या बढ़ रहा है, यह लिखा हो। अपनी स्थिति के लिए कृपया डॉक्टर से मिलें।",
        "uncertain_short": "केवल इन लक्षणों से कारण पता नहीं चल सकता।",
        "uncertain": "ये केवल संभावनाएं हैं - इन लक्षणों के कई अलग कारण हो सकते हैं, और मैं यह नहीं बता सकता कि आपके मामले में कौन सा है।",
        "en_only": "इस विषय की विस्तृत जानकारी अभी केवल अंग्रेज़ी में उपलब्ध है, इसलिए उत्तर का बाकी हिस्सा अंग्रेज़ी में है।",
        "fallback": "मुझे यकीन नहीं है कि मैं इसे स्वास्थ्य संबंधी प्रश्न के रूप में समझ पाया। मैं सामान्य लक्षण, प्राथमिक उपचार, दवा की सुरक्षा, खान-पान, "
                    "व्यायाम, नींद, मानसिक स्वास्थ्य, जांच, बचाव और कौन से डॉक्टर को दिखाएं - इन सब में मदद कर सकता हूं। क्या आप इसे थोड़ा अलग तरह से लिख सकते हैं?",
        "clarify": "मैं ठीक से समझना चाहता हूं। कौन सा लक्षण या शरीर का कौन सा हिस्सा परेशान कर रहा है, कितने समय से है, और क्या यह बढ़ रहा है?",
        "oos": "यह स्वास्थ्य संबंधी प्रश्न नहीं लगता, इसलिए मैं अंदाज़ा नहीं लगाऊंगा। मैं लक्षण, प्राथमिक उपचार, दवा, खान-पान, नींद, मानसिक स्वास्थ्य, "
               "जांच और कौन से डॉक्टर को दिखाएं - इन में मदद कर सकता हूं।",
        "multi_intro": "आपने एक से अधिक लक्षण बताए हैं ({symptoms})। ये कई अलग कारणों से एक साथ हो सकते हैं, इसलिए मैं नहीं बता सकता कि इनके पीछे क्या है।",
        "multi_note": "मुझे बताइए कि ये कितने दिनों से हैं, क्या बढ़ रहे हैं, और क्या कुछ और भी हो रहा है - तब मैं बेहतर मार्गदर्शन दे पाऊंगा।",
        "first_step": "सबसे पहला कदम", "see_sooner": "इन स्थितियों में जल्दी डॉक्टर को दिखाएं", "not_dx": "विशेषज्ञ का सुझाव निदान नहीं होता।",
        "emerg_not_routine": "यदि खतरे के संकेत हों तो सामान्य अपॉइंटमेंट का इंतज़ार न करें - 112 पर कॉल करें या नज़दीकी इमरजेंसी विभाग जाएं।",
        "emergency": "यह मेडिकल इमरजेंसी हो सकती है। कृपया अभी 112 पर कॉल करें (कई राज्यों में एम्बुलेंस के लिए 108) या नज़दीकी अस्पताल जाएं। "
                     "ऑनलाइन उत्तर का इंतज़ार न करें।",
        "selfharm": "मुझे बहुत दुख है कि आप इतना दर्द महसूस कर रहे हैं, और अच्छा है कि आपने यह बताया। आप अभी सहारे के हक़दार हैं। यदि इन विचारों पर अमल करने का "
                    "खतरा हो तो कृपया 112 पर कॉल करें या नज़दीकी इमरजेंसी विभाग जाएं। आप टेली-मानस (भारत सरकार की निःशुल्क 24x7 मानसिक स्वास्थ्य हेल्पलाइन) पर भी "
                    "14416 या 1800-891-4416 पर कॉल कर सकते हैं। कृपया किसी अपने को बता दें ताकि आप आज रात अकेले न रहें।",
        "mentalcrisis": "यह मानसिक स्वास्थ्य आपातकाल लगता है, और आप अभी मदद के हक़दार हैं। कृपया 112 पर कॉल करें या नज़दीकी इमरजेंसी विभाग जाएं। "
                        "टेली-मानस (निःशुल्क, 24x7) 14416 या 1800-891-4416 पर है। यदि आप किसी ऐसे व्यक्ति के साथ हैं जो संकट में है, तो उनके साथ रहें और सबको सुरक्षित रखें।",
        "emerg_close": "यह सामान्य सुरक्षा जानकारी है, निदान नहीं। यह आपातकालीन इलाज की जगह नहीं ले सकती।",
        "support": "टेली-मानस (भारत सरकार) से निःशुल्क और गोपनीय सहायता किसी भी समय 14416 या 1800-891-4416 पर मिल सकती है। यदि आप असुरक्षित महसूस करें तो 112 पर कॉल करें।",
    },
}

# Immediate-action lines per emergency class (safety.py category -> text)
GUIDANCE = {
    "hinglish": {
        "chest pain / possible heart attack": "Jo kar rahe hain use rok dein, baith jayein aur shant rahein. Khud gaadi na chalayein. Tight kapde dheele karein.",
        "severe breathing difficulty": "Seedhe baithein, tight kapde dheele karein aur dheere saans lene ki koshish karein. Let na jayein. Agar doctor ne inhaler ya emergency dawai di hai to unke bataye anusar use karein.",
        "possible stroke": "Symptoms kab shuru hue ye time note karein aur emergency team ko bata dein. Munh se khana, paani ya dawai na dein. Vyakti ko surakshit aur sthir rakhein.",
        "loss of consciousness / seizure": "Dekhein ki vyakti saans le raha hai ya nahi. Saans normal ho to use karwat par litayein. Saans normal na ho aur aap trained hon to CPR shuru karein. Daure ke samay sir ko bachayein aur munh mein kuch na daalein.",
        "severe bleeding": "Saaf kapde se ghaav ko mazbooti se dabayein aur dabaye rakhein. Bheega hua kapda na hatayein - uske upar aur kapda rakhein. Sambhav ho to chot wala hissa upar uthayein.",
        "poisoning / overdose": "Doctor ke kehne tak ulti karne ke liye na kahein. Dawai ya dabba dikhane ke liye sambhal kar rakhein aur vyakti ke saath rahein.",
        "choking / severe allergic reaction": "Dam ghutne par: agar vyakti khaans, bol ya saans na le paye to trained hone par peeth par thapki aur abdominal thrusts dein. Gambhir allergy mein: agar adrenaline auto-injector di gayi ho to use karein, aur saans mein dikkat na ho to pair upar karke letein.",
        "pregnancy emergency": "Baayein karwat par letein aur lakshan thamne ka intezaar na karein. Kisi se hospital le jaane ko kahein ya ambulance bulayein.",
        "mental health crisis": "Surakshit jagah par jayein, nuksan pahunchane wali cheezon se door rahein aur kisi bharosemand ke saath rahein.",
    },
    "hi": {
        "chest pain / possible heart attack": "जो कर रहे हैं उसे रोक दें, बैठ जाएं और शांत रहें। खुद गाड़ी न चलाएं। तंग कपड़े ढीले करें।",
        "severe breathing difficulty": "सीधे बैठें, तंग कपड़े ढीले करें और धीरे-धीरे सांस लेने की कोशिश करें। लेटें नहीं। यदि डॉक्टर ने इन्हेलर या आपातकालीन दवा दी है तो उनके बताए अनुसार उपयोग करें।",
        "possible stroke": "लक्षण कब शुरू हुए यह समय नोट करें और इमरजेंसी टीम को बताएं। मुंह से खाना, पानी या दवा न दें। व्यक्ति को सुरक्षित और स्थिर रखें।",
        "loss of consciousness / seizure": "देखें कि व्यक्ति सांस ले रहा है या नहीं। सांस सामान्य हो तो उसे करवट पर लिटाएं। सांस सामान्य न हो और आप प्रशिक्षित हों तो CPR शुरू करें। दौरे के समय सिर को बचाएं और मुंह में कुछ न डालें।",
        "severe bleeding": "साफ कपड़े से घाव को मज़बूती से दबाएं और दबाए रखें। भीगा हुआ कपड़ा न हटाएं - उसके ऊपर और कपड़ा रखें। संभव हो तो चोट वाला हिस्सा ऊपर उठाएं।",
        "poisoning / overdose": "डॉक्टर के कहने तक उल्टी करवाने की कोशिश न करें। दवा या डिब्बा दिखाने के लिए संभालकर रखें और व्यक्ति के साथ रहें।",
        "choking / severe allergic reaction": "दम घुटने पर: यदि व्यक्ति खांस, बोल या सांस न ले पाए तो प्रशिक्षित होने पर पीठ पर थपकी और पेट पर दबाव (एब्डोमिनल थ्रस्ट) दें। गंभीर एलर्जी में: यदि एड्रेनालिन ऑटो-इंजेक्टर दिया गया हो तो उपयोग करें, और सांस में दिक्कत न हो तो पैर ऊपर करके लेटें।",
        "pregnancy emergency": "बाईं करवट पर लेटें और लक्षण थमने का इंतज़ार न करें। किसी से अस्पताल ले जाने को कहें या एम्बुलेंस बुलाएं।",
        "mental health crisis": "सुरक्षित जगह पर जाएं, नुकसान पहुंचा सकने वाली चीज़ों से दूर रहें और किसी भरोसेमंद व्यक्ति के साथ रहें।",
    },
}

# ------------------------------------------------------------------------------- small talk
SMALL_TALK = {
    "greeting": {
        "en": ["Hello! I'm MediChat, a health information assistant. What would you like to know today?",
               "Hi there! I'm MediChat. You can ask me about symptoms, which doctor to see, medicines, diet, sleep and more. How can I help?"],
        "hinglish": ["Namaste! Main MediChat hoon. Aapko kis health-related question mein help chahiye?",
                     "Hello! Main MediChat hoon. Aap symptoms, kaun sa doctor dikhana hai, dawai, khana-peena ya neend ke baare mein pooch sakte hain. Main kaise help karun?"],
        "hi": ["नमस्ते! मैं MediChat हूं। आपको किस स्वास्थ्य संबंधी प्रश्न में मदद चाहिए?",
               "नमस्ते! मैं MediChat हूं। आप लक्षण, कौन से डॉक्टर को दिखाएं, दवा, खान-पान या नींद के बारे में पूछ सकते हैं। मैं कैसे मदद करूं?"],
    },
    "how_are_you": {
        "en": ["I'm doing well, thank you for asking! I'm here to help with your health questions. How are you feeling today?"],
        "hinglish": ["Main theek hoon, poochne ke liye shukriya! Main aapke health questions mein help ke liye yahan hoon. Aap aaj kaisa mehsoos kar rahe hain?"],
        "hi": ["मैं ठीक हूं, पूछने के लिए धन्यवाद! मैं आपके स्वास्थ्य संबंधी प्रश्नों में मदद के लिए यहां हूं। आप आज कैसा महसूस कर रहे हैं?"],
    },
    "thanks": {
        "en": ["You're welcome! If anything else comes up, just ask. Take care of yourself."],
        "hinglish": ["Aapka swagat hai! Agar aur kuch poochna ho to bejhijhak poochiye. Apna khayal rakhiye."],
        "hi": ["आपका स्वागत है! यदि कुछ और पूछना हो तो बेझिझक पूछिए। अपना ध्यान रखिए।"],
    },
    "bye": {
        "en": ["Goodbye! Take care, and please see a doctor if you ever feel seriously unwell."],
        "hinglish": ["Alvida! Apna khayal rakhiye, aur agar kabhi tabiyat zyada kharab lage to doctor ko zaroor dikhayein."],
        "hi": ["अलविदा! अपना ध्यान रखिए, और यदि कभी तबीयत ज़्यादा खराब लगे तो डॉक्टर को ज़रूर दिखाएं।"],
    },
    "identity": {
        "en": ["I'm MediChat, a health information assistant built for research and education. I can share general information on symptoms, "
               "when to see a doctor and which specialist to consult - I can't diagnose or prescribe."],
        "hinglish": ["Main MediChat hoon, research aur education ke liye bana health information assistant. Main symptoms, doctor ko kab dikhana hai aur kaun sa specialist "
                     "dikhana hai - iski general jaankari de sakta hoon. Main diagnosis ya prescription nahi de sakta."],
        "hi": ["मैं MediChat हूं, शोध और शिक्षा के लिए बना एक स्वास्थ्य सूचना सहायक। मैं लक्षणों, डॉक्टर को कब दिखाएं और कौन से विशेषज्ञ को दिखाएं - इसकी सामान्य जानकारी दे सकता हूं। "
               "मैं निदान या दवा का पर्चा नहीं दे सकता।"],
    },
    "help": {
        "en": ["I can help with: common symptoms (like fever or headache), which doctor to consult, medicine safety, diet and exercise, sleep, "
               "stress, blood tests, prevention, and warning signs that need urgent care. Just describe your question in your own words - English, Hindi or Hinglish."],
        "hinglish": ["Main in mein help kar sakta hoon: common symptoms (jaise bukhar ya sir dard), kaun sa doctor dikhana hai, dawai ki safety, khana aur exercise, neend, "
                     "stress, blood tests, bachav, aur wo khatre ke sanket jinmein turant ilaaj chahiye. Aap apne shabdon mein poochiye - English, Hindi ya Hinglish."],
        "hi": ["मैं इनमें मदद कर सकता हूं: सामान्य लक्षण (जैसे बुखार या सिरदर्द), कौन से डॉक्टर को दिखाएं, दवा की सुरक्षा, खान-पान और व्यायाम, नींद, "
               "तनाव, ब्लड टेस्ट, बचाव, और वे खतरे के संकेत जिनमें तुरंत इलाज चाहिए। आप अपने शब्दों में पूछिए - अंग्रेज़ी, हिंदी या हिंग्लिश।"],
    },
    "ack": {
        "en": ["Okay! Let me know if you have another health question."],
        "hinglish": ["Theek hai! Koi aur health question ho to bataiye."],
        "hi": ["ठीक है! कोई और स्वास्थ्य संबंधी प्रश्न हो तो बताइए।"],
    },
}

# ----------------------------------------------------------- doctor / specialty guidance
# Each area: how to recognise it (on canonical English), the specialist, and localised text.
SPECIALTY_AREAS = [
    # (key, regex on canonical English, specialist, first_stop_key)
    ("heart", r"chest pain|heart|palpitation|blood pressure|cholesterol", "Cardiologist"),
    ("breathing", r"breath|cough|asthma|wheez|lungs?|respirat", "Pulmonologist / Chest physician"),
    ("digestive", r"stomach|abdominal|belly|gastric|acidity|digest|constipation|diarrh|vomit|nausea|liver|bowel|ulcer|indigestion", "Gastroenterologist"),
    ("skin", r"skin|rash|acne|itch|eczema|hair|psoriasis|dermat", "Dermatologist"),
    ("dental", r"tooth|teeth|dental|gum|dentist", "Dentist"),
    ("eye", r"\beyes?\b|vision|sight|eye irritation|blurred", "Ophthalmologist (eye specialist)"),
    ("ent", r"\bear\b|hearing|\bnose\b|sinus|throat|tonsil|\bent\b", "ENT specialist"),
    ("headache", r"headache|migraine|seizure|numb|tingling|nerve|memory|dizz", "Neurologist"),
    ("thyroid", r"thyroid|tsh|goitre|goiter|hormone", "Endocrinologist"),
    ("diabetes", r"diabet|blood sugar|insulin", "Endocrinologist / Diabetologist"),
    ("joint", r"joint|knee|bone|arthritis|back pain|shoulder|fracture|muscle", "Orthopaedic doctor or Rheumatologist"),
    ("womens", r"period|menstru|pregnan|vaginal|pcos|menopause|breast", "Gynaecologist"),
    ("child", r"\bchild\b|\bbaby\b|infant|toddler|newborn|kid", "Paediatrician (children's doctor)"),
    ("mental", r"anxiety|stress|depress|low mood|panic|mental|sleep|insomnia|suicid", "Psychiatrist, psychologist or counsellor"),
    ("urinary", r"urin|kidney|bladder|uti\b", "Urologist (or Nephrologist for kidney problems)"),
]

SPECIALTY_TEXT = {
    "heart": {
        "en": ("Start with a General Physician for blood pressure or heart-related worries; they can arrange an ECG and tests and refer you to a Cardiologist if needed.",
               "chest pain or pressure, pain spreading to the arm or jaw, breathlessness, sweating or fainting - these need emergency care (112), not an appointment."),
        "hinglish": ("Blood pressure ya dil se jude chinta ke liye pehle General Physician ko dikhayein; wo ECG aur tests karwa kar zaroorat par Cardiologist ke paas bhej sakte hain.",
                     "seene mein dard ya dabav, dard ka haath ya jabde tak failna, saans phoolna, paseena ya behoshi - inmein appointment nahi, emergency ilaaj (112) chahiye."),
        "hi": ("ब्लड प्रेशर या दिल से जुड़ी चिंता के लिए पहले General Physician को दिखाएं; वे ECG और जांच करवाकर ज़रूरत होने पर Cardiologist के पास भेज सकते हैं।",
               "सीने में दर्द या दबाव, दर्द का बांह या जबड़े तक फैलना, सांस फूलना, पसीना या बेहोशी - इनमें अपॉइंटमेंट नहीं, इमरजेंसी इलाज (112) चाहिए।"),
    },
    "breathing": {
        "en": ("Start with a General Physician. A Pulmonologist (chest specialist) is suggested if cough or breathing problems last, keep returning or you have asthma.",
               "breathing is difficult at rest, lips look blue, you cannot speak a full sentence or cough up blood - this is an emergency (112)."),
        "hinglish": ("Pehle General Physician ko dikhayein. Agar khansi ya saans ki dikkat lambi chale, baar-baar aaye ya aapko asthma ho to Pulmonologist (chest specialist) ko dikhayein.",
                     "aaram karte samay bhi saans lene mein dikkat ho, hont neele dikhein, ek poora vakya na bol payein ya khansi mein khoon aaye - ye emergency hai (112)."),
        "hi": ("पहले General Physician को दिखाएं। यदि खांसी या सांस की दिक्कत लंबी चले, बार-बार लौटे या आपको अस्थमा हो तो Pulmonologist (छाती के विशेषज्ञ) को दिखाएं।",
               "आराम करते समय भी सांस लेने में कठिनाई हो, होंठ नीले दिखें, एक पूरा वाक्य न बोल पाएं या खांसी में खून आए - यह इमरजेंसी है (112)।"),
    },
    "digestive": {
        "en": ("Start with a General Physician. A Gastroenterologist (digestive specialist) is advised if the problem lasts, keeps returning or comes with warning signs.",
               "severe or sudden stomach pain, vomiting blood, black or bloody stools, a hard swollen belly, or pain with high fever."),
        "hinglish": ("Pehle General Physician ko dikhayein. Agar dikkat lambi chale, baar-baar aaye ya khatre ke sanket hon to Gastroenterologist (pet aur pachan ke specialist) ko dikhayein.",
                     "pet mein tez ya achanak dard, khoon ki ulti, kale ya khoon wale mal, sakht phoola hua pet, ya tez bukhar ke saath dard."),
        "hi": ("पहले General Physician को दिखाएं। यदि समस्या लंबी चले, बार-बार लौटे या खतरे के संकेत हों तो Gastroenterologist (पेट और पाचन के विशेषज्ञ) को दिखाएं।",
               "पेट में तेज़ या अचानक दर्द, खून की उल्टी, काला या खून वाला मल, सख्त फूला हुआ पेट, या तेज़ बुखार के साथ दर्द।"),
    },
    "skin": {
        "en": ("For a new rash or mild problem start with a General Physician; a Dermatologist is the specialist for skin, hair and nails.",
               "the rash spreads fast, blisters, hurts a lot, comes with fever, or the lips/face swell or breathing becomes difficult (emergency)."),
        "hinglish": ("Nayi rash ya halki samasya ke liye pehle General Physician ko dikhayein; Dermatologist twacha, baal aur nakhun ke specialist hote hain.",
                     "rash tezi se phaile, chhale pade, bahut dard ho, bukhar ho, ya hont/chehra sooje ya saans lene mein dikkat ho (emergency)."),
        "hi": ("नए रैश या हल्की समस्या के लिए पहले General Physician को दिखाएं; Dermatologist त्वचा, बाल और नाखून के विशेषज्ञ होते हैं।",
               "रैश तेज़ी से फैले, छाले पड़ें, बहुत दर्द हो, बुखार हो, या होंठ/चेहरा सूजे या सांस लेने में दिक्कत हो (इमरजेंसी)।"),
    },
    "dental": {
        "en": ("See a Dentist - they treat tooth, gum and mouth problems.",
               "there is facial swelling, fever, or trouble swallowing or breathing - seek urgent care."),
        "hinglish": ("Dentist ko dikhayein - wo daant, masude aur munh ki samasyaon ka ilaaj karte hain.",
                     "chehre par sujan ho, bukhar ho, ya nigalne ya saans lene mein dikkat ho - turant ilaaj lein."),
        "hi": ("Dentist (दंत चिकित्सक) को दिखाएं - वे दांत, मसूड़ों और मुंह की समस्याओं का इलाज करते हैं।",
               "चेहरे पर सूजन हो, बुखार हो, या निगलने या सांस लेने में दिक्कत हो - तुरंत इलाज लें।"),
    },
    "eye": {
        "en": ("An Ophthalmologist (eye specialist) is the right doctor for eye problems; an optometrist can check vision and glasses.",
               "there is sudden vision loss, severe eye pain, a chemical splash or an eye injury - go to an eye emergency or hospital at once."),
        "hinglish": ("Aankhon ki samasya ke liye Ophthalmologist (aankhon ke specialist) sahi doctor hain; optometrist nazar aur chashme ki jaanch kar sakte hain.",
                     "achanak nazar chali jaye, aankh mein tez dard ho, chemical ya chot lage - turant eye emergency ya hospital jayein."),
        "hi": ("आंखों की समस्या के लिए Ophthalmologist (नेत्र रोग विशेषज्ञ) सही डॉक्टर हैं; optometrist नज़र और चश्मे की जांच कर सकते हैं।",
               "अचानक नज़र चली जाए, आंख में तेज़ दर्द हो, केमिकल या चोट लगे - तुरंत आई इमरजेंसी या अस्पताल जाएं।"),
    },
    "ent": {
        "en": ("Start with a General Physician; an ENT specialist (ear, nose and throat) is suggested if the problem lasts or keeps returning.",
               "breathing or swallowing becomes difficult, there is sudden hearing loss, or high fever with severe throat pain and drooling."),
        "hinglish": ("Pehle General Physician ko dikhayein; agar samasya lambi chale ya baar-baar aaye to ENT specialist (kaan, naak, gala) ko dikhayein.",
                     "saans lene ya nigalne mein dikkat ho, achanak sunna kam ho jaye, ya tez bukhar ke saath gale mein bahut dard aur laar tapke."),
        "hi": ("पहले General Physician को दिखाएं; यदि समस्या लंबी चले या बार-बार लौटे तो ENT विशेषज्ञ (कान, नाक, गला) को दिखाएं।",
               "सांस लेने या निगलने में दिक्कत हो, अचानक सुनना कम हो जाए, या तेज़ बुखार के साथ गले में बहुत दर्द और लार टपके।"),
    },
    "headache": {
        "en": ("For frequent headaches or dizziness, start with a General Physician. They check common causes such as eye strain, stress, poor sleep or high blood pressure and refer you to a Neurologist if needed.",
               "a sudden very severe headache, a headache after a head injury, or headache with weakness, confusion, trouble speaking, vision loss, or stiff neck with fever (emergency)."),
        "hinglish": ("Baar-baar sir dard ya chakkar ke liye pehle General Physician ko dikhayein. Wo aankhon ka strain, stress, kam neend ya high blood pressure jaise aam karan dekhte hain aur zaroorat par Neurologist ke paas bhejte hain.",
                     "achanak bahut tez sir dard, sir par chot ke baad sir dard, ya kamzori, confusion, bolne mein dikkat, nazar jaana, ya bukhar ke saath akdi hui gardan ke saath sir dard (emergency)."),
        "hi": ("बार-बार सिरदर्द या चक्कर के लिए पहले General Physician को दिखाएं। वे आंखों का तनाव, तनाव, कम नींद या हाई ब्लड प्रेशर जैसे सामान्य कारण देखते हैं और ज़रूरत होने पर Neurologist के पास भेजते हैं।",
               "अचानक बहुत तेज़ सिरदर्द, सिर पर चोट के बाद सिरदर्द, या कमज़ोरी, भ्रम, बोलने में दिक्कत, नज़र जाना, या बुखार के साथ अकड़ी हुई गर्दन के साथ सिरदर्द (इमरजेंसी)।"),
    },
    "thyroid": {
        "en": ("Thyroid concerns are usually first assessed by a General Physician, who can order a blood test (such as TSH). An Endocrinologist (hormone specialist) helps if the problem is complex or hard to control.",
               "there is swelling in the neck, trouble swallowing, unexplained weight, heart-rate or energy changes, or a very fast heartbeat with chest pain or confusion (urgent)."),
        "hinglish": ("Thyroid ki chinta mein aam taur par pehle General Physician dekhte hain, jo blood test (jaise TSH) likh sakte hain. Samasya jatil ya kaabu se bahar ho to Endocrinologist (hormone specialist) madad karte hain.",
                     "gardan mein sujan ho, nigalne mein dikkat ho, bina wajah wazan, dhadkan ya energy mein badlav ho, ya bahut tez dhadkan ke saath seene mein dard ya confusion ho (turant)."),
        "hi": ("थायरॉइड की चिंता में आमतौर पर पहले General Physician देखते हैं, जो ब्लड टेस्ट (जैसे TSH) लिख सकते हैं। समस्या जटिल या काबू से बाहर हो तो Endocrinologist (हार्मोन विशेषज्ञ) मदद करते हैं।",
               "गर्दन में सूजन हो, निगलने में दिक्कत हो, बिना कारण वज़न, धड़कन या ऊर्जा में बदलाव हो, या बहुत तेज़ धड़कन के साथ सीने में दर्द या भ्रम हो (तुरंत)।"),
    },
    "diabetes": {
        "en": ("See a General Physician or an Endocrinologist/Diabetologist for blood sugar concerns.",
               "confusion, fainting, repeated vomiting, fruity-smelling breath, or a blood sugar that is very high or very low (urgent)."),
        "hinglish": ("Blood sugar ki chinta ke liye General Physician ya Endocrinologist/Diabetologist ko dikhayein.",
                     "confusion, behoshi, baar-baar ulti, phal jaisi gandh wali saans, ya bahut zyada ya bahut kam blood sugar (turant)."),
        "hi": ("ब्लड शुगर की चिंता के लिए General Physician या Endocrinologist/Diabetologist को दिखाएं।",
               "भ्रम, बेहोशी, बार-बार उल्टी, फल जैसी गंध वाली सांस, या बहुत ज़्यादा या बहुत कम ब्लड शुगर (तुरंत)।"),
    },
    "joint": {
        "en": ("Start with a General Physician. An Orthopaedic doctor treats bones, joints and injuries, and a Rheumatologist treats inflammatory conditions such as rheumatoid arthritis.",
               "a joint is hot, red and very swollen with fever, a bone may be broken, you cannot bear weight, or there is sudden severe pain after an injury; also loss of bladder or bowel control with back pain (emergency)."),
        "hinglish": ("Pehle General Physician ko dikhayein. Orthopaedic doctor haddi, jodon aur chot ka ilaaj karte hain, aur Rheumatologist rheumatoid arthritis jaisi sujan wali bimariyon ka.",
                     "jod garam, laal aur bahut soojha ho aur bukhar ho, haddi tootne ka shak ho, bojh na utha payein, chot ke baad achanak tez dard ho; ya kamar dard ke saath peshab-potty par kaabu na rahe (emergency)."),
        "hi": ("पहले General Physician को दिखाएं। Orthopaedic डॉक्टर हड्डी, जोड़ों और चोट का इलाज करते हैं, और Rheumatologist रूमेटॉइड अर्थराइटिस जैसी सूजन वाली बीमारियों का।",
               "जोड़ गर्म, लाल और बहुत सूजा हो और बुखार हो, हड्डी टूटने का शक हो, वज़न न उठा पाएं, चोट के बाद अचानक तेज़ दर्द हो; या कमर दर्द के साथ पेशाब-शौच पर काबू न रहे (इमरजेंसी)।"),
    },
    "womens": {
        "en": ("A Gynaecologist is the specialist for periods, pregnancy and women's health concerns; a General Physician can be a first step.",
               "pregnant with bleeding, severe pain or reduced baby movements, or very heavy bleeding with dizziness (emergency)."),
        "hinglish": ("Gynaecologist periods, pregnancy aur mahilaon ke swasthya ke specialist hain; General Physician pehla kadam ho sakte hain.",
                     "pregnancy mein khoon aaye, tez dard ho ya bacche ki hilchal kam ho, ya bahut zyada bleeding ke saath chakkar aaye (emergency)."),
        "hi": ("Gynaecologist पीरियड्स, गर्भावस्था और महिलाओं के स्वास्थ्य के विशेषज्ञ हैं; General Physician पहला कदम हो सकते हैं।",
               "गर्भावस्था में खून आए, तेज़ दर्द हो या बच्चे की हलचल कम हो, या बहुत ज़्यादा ब्लीडिंग के साथ चक्कर आए (इमरजेंसी)।"),
    },
    "child": {
        "en": ("A Paediatrician (children's doctor) is the right first stop for babies and children.",
               "a baby under 3 months has a fever of 38 C (100.4 F) or higher, or a child is very drowsy, refuses to drink, has trouble breathing, a stiff neck, a seizure or a spreading rash."),
        "hinglish": ("Bacchon ke liye Paediatrician (bachon ke doctor) sahi pehla kadam hain.",
                     "3 mahine se chhote baby ko 38 C (100.4 F) ya usse zyada bukhar ho, ya bachha bahut sust ho, kuch pee na raha ho, saans mein dikkat ho, gardan akdi ho, daura pade ya rash phail raha ho."),
        "hi": ("बच्चों के लिए Paediatrician (बाल रोग विशेषज्ञ) सही पहला कदम हैं।",
               "3 महीने से छोटे शिशु को 38 C (100.4 F) या उससे ज़्यादा बुखार हो, या बच्चा बहुत सुस्त हो, कुछ पी न रहा हो, सांस में दिक्कत हो, गर्दन अकड़ी हो, दौरा पड़े या रैश फैल रहा हो।"),
    },
    "mental": {
        "en": ("A General Physician, a counsellor, a psychologist or a Psychiatrist can help; a psychiatrist can also prescribe medicines if needed.",
               "you have thoughts of harming yourself or others, or feel unable to keep yourself safe - call 112 or Tele-MANAS (14416 / 1800-891-4416) right away."),
        "hinglish": ("General Physician, counsellor, psychologist ya Psychiatrist madad kar sakte hain; zaroorat par psychiatrist dawai bhi likh sakte hain.",
                     "khud ko ya doosron ko nuksan pahunchane ke vichar aayein, ya aap khud ko surakshit na rakh paayein - turant 112 ya Tele-MANAS (14416 / 1800-891-4416) par call karein."),
        "hi": ("General Physician, काउंसलर, मनोवैज्ञानिक (psychologist) या मनोचिकित्सक (Psychiatrist) मदद कर सकते हैं; ज़रूरत होने पर मनोचिकित्सक दवा भी लिख सकते हैं।",
               "खुद को या दूसरों को नुकसान पहुंचाने के विचार आएं, या आप खुद को सुरक्षित न रख पाएं - तुरंत 112 या टेली-मानस (14416 / 1800-891-4416) पर कॉल करें।"),
    },
    "urinary": {
        "en": ("Start with a General Physician, who can arrange a urine test. A Urologist (or Nephrologist for kidney problems) is advised if it keeps returning or there are stones or kidney concerns.",
               "fever or shaking, back or side pain, vomiting, blood in urine, or if the patient is pregnant, a child or an older adult (urgent)."),
        "hinglish": ("Pehle General Physician ko dikhayein, jo urine test karwa sakte hain. Baar-baar ho, pathri ho ya kidney ki chinta ho to Urologist (kidney ke liye Nephrologist) ko dikhayein.",
                     "bukhar ya kaampna, peeth ya kamar ke side mein dard, ulti, peshab mein khoon, ya mareez pregnant, bachha ya buzurg ho (turant)."),
        "hi": ("पहले General Physician को दिखाएं, जो यूरिन टेस्ट करवा सकते हैं। बार-बार हो, पथरी हो या किडनी की चिंता हो तो Urologist (किडनी के लिए Nephrologist) को दिखाएं।",
               "बुखार या कंपकंपी, पीठ या बगल में दर्द, उल्टी, पेशाब में खून, या मरीज़ गर्भवती, बच्चा या बुज़ुर्ग हो (तुरंत)।"),
    },
    "general": {
        "en": ("A General Physician (family doctor) is usually the best first stop. They assess the problem, treat common conditions and refer you to a specialist when needed.",
               "you have severe breathing difficulty, sudden severe chest pain, signs of a stroke or heavy bleeding."),
        "hinglish": ("General Physician (family doctor) aam taur par sabse achha pehla kadam hain. Wo samasya ko dekhte hain, aam bimariyon ka ilaaj karte hain aur zaroorat par specialist ke paas bhejte hain.",
                     "saans lene mein gambhir dikkat ho, achanak seene mein tez dard ho, stroke ke sanket hon ya bahut zyada khoon beh raha ho."),
        "hi": ("General Physician (फैमिली डॉक्टर) आमतौर पर सबसे अच्छा पहला कदम हैं। वे समस्या को देखते हैं, आम बीमारियों का इलाज करते हैं और ज़रूरत होने पर विशेषज्ञ के पास भेजते हैं।",
               "सांस लेने में गंभीर दिक्कत हो, अचानक सीने में तेज़ दर्द हो, स्ट्रोक के संकेत हों या बहुत ज़्यादा खून बह रहा हो।"),
    },
}

# ---------------------------------------------------------- translated topic text (S, A, D)
TOPIC_I18N = {
    "fever": {
        "hinglish": ("Bukhar ka matlab hai ki aapke sharir ka temperature normal se zyada hai, aam taur par 38 C (100.4 F) ya usse upar. Ye aksar is baat ka sanket hota hai ki sharir kisi infection se lad raha hai.",
                     "Aaram karein, bahut saara paani aur taral padarth peeyein, halke kapde pehnein aur kamre ko aaramdayak rakhein. Bukhar ki kaun si dawai aapke liye theek hai, ye kisi pharmacist ya doctor se poochein.",
                     "Agar bukhar 3 din se zyada rahe, 39.5 C (103 F) se upar jaye, ya saath mein akdi hui gardan, rash, confusion, saans mein dikkat ya tez dard ho to doctor ko dikhayein."),
        "hi": ("बुखार का मतलब है कि आपके शरीर का तापमान सामान्य से ज़्यादा है, आमतौर पर 38 C (100.4 F) या उससे ऊपर। यह अक्सर इस बात का संकेत होता है कि शरीर किसी संक्रमण से लड़ रहा है।",
               "आराम करें, खूब पानी और तरल पदार्थ पिएं, हल्के कपड़े पहनें और कमरे को आरामदायक रखें। बुखार की कौन सी दवा आपके लिए ठीक है, यह किसी फार्मासिस्ट या डॉक्टर से पूछें।",
               "यदि बुखार 3 दिन से ज़्यादा रहे, 39.5 C (103 F) से ऊपर जाए, या साथ में अकड़ी हुई गर्दन, रैश, भ्रम, सांस में दिक्कत या तेज़ दर्द हो तो डॉक्टर को दिखाएं।"),
    },
    "headache": {
        "hinglish": ("Zyadatar sir dard tension-type headache ya migraine hote hain aur khatarnak nahi hote. Aam trigger hain: stress, paani ki kami, khana chhodna, kam neend, aankhon ka strain aur zyada screen time.",
                     "Shant, andhere kamre mein aaram karein, paani peeyein, time par khana khayein, achhi neend lein, screen se break lein aur stress sambhalein. Apne triggers pehchanne ke liye diary rakhein.",
                     "Achanak bahut tez sir dard, sir par chot ke baad sir dard, ya bukhar ke saath akdi hui gardan, confusion, kamzori ya nazar mein badlav ke saath sir dard ho to turant medical madad lein."),
        "hi": ("ज़्यादातर सिरदर्द टेंशन-टाइप सिरदर्द या माइग्रेन होते हैं और खतरनाक नहीं होते। आम कारण हैं: तनाव, पानी की कमी, खाना छोड़ना, कम नींद, आंखों का तनाव और ज़्यादा स्क्रीन टाइम।",
               "शांत, अंधेरे कमरे में आराम करें, पानी पिएं, समय पर खाना खाएं, अच्छी नींद लें, स्क्रीन से ब्रेक लें और तनाव संभालें। अपने कारण पहचानने के लिए डायरी रखें।",
               "अचानक बहुत तेज़ सिरदर्द, सिर पर चोट के बाद सिरदर्द, या बुखार के साथ अकड़ी हुई गर्दन, भ्रम, कमज़ोरी या नज़र में बदलाव के साथ सिरदर्द हो तो तुरंत चिकित्सा सहायता लें।"),
    },
    "cough": {
        "hinglish": ("Khansi sharir ka saans ki nali saaf karne ka tarika hai. Zyadatar khansi cold jaise viral infection se hoti hai aur 1 se 3 hafte mein apne aap theek ho jati hai.",
                     "Garam taral padarth peeyein, aaram karein, dhuein aur dhool se bachein aur hawa mein nami rakhein. Garam paani mein shahad adults aur 1 saal se bade bachon ke gale ko aaram de sakta hai.",
                     "Agar khansi 3 hafte se zyada chale, ya khoon, tez bukhar, wazan ghatna, raat ko paseena ya saans phoolne ke saath ho to doctor ko dikhayein."),
        "hi": ("खांसी शरीर का सांस की नलियों को साफ करने का तरीका है। ज़्यादातर खांसी सर्दी-जुकाम जैसे वायरल संक्रमण से होती है और 1 से 3 हफ्ते में अपने आप ठीक हो जाती है।",
               "गर्म तरल पदार्थ पिएं, आराम करें, धुएं और धूल से बचें और हवा में नमी रखें। गर्म पानी में शहद वयस्कों और 1 साल से बड़े बच्चों के गले को आराम दे सकता है।",
               "यदि खांसी 3 हफ्ते से ज़्यादा चले, या खून, तेज़ बुखार, वज़न घटना, रात को पसीना या सांस फूलने के साथ हो तो डॉक्टर को दिखाएं।"),
    },
    "common_cold": {
        "hinglish": ("Common cold naak aur gale ka halka viral infection hai. Ye aam taur par 7 se 10 din mein apne aap theek ho jata hai.",
                     "Aaram karein, garam taral padarth peeyein, bhaap (steam) lein ya namak ke paani se naak saaf karein, aur phailne se rokne ke liye haath baar-baar dhoyein. Antibiotics cold par kaam nahi karti.",
                     "Agar lakshan 10 din se zyada rahein, tez bukhar ho, kaan ya seene mein dard ho, saans mein dikkat ho, ya baby, buzurg ya purani bimari wala vyakti prabhavit ho to doctor ko dikhayein."),
        "hi": ("सामान्य सर्दी-जुकाम नाक और गले का हल्का वायरल संक्रमण है। यह आमतौर पर 7 से 10 दिन में अपने आप ठीक हो जाता है।",
               "आराम करें, गर्म तरल पदार्थ पिएं, भाप लें या नमक के पानी से नाक साफ करें, और फैलने से रोकने के लिए हाथ बार-बार धोएं। एंटीबायोटिक सर्दी-जुकाम पर काम नहीं करती।",
               "यदि लक्षण 10 दिन से ज़्यादा रहें, तेज़ बुखार हो, कान या सीने में दर्द हो, सांस में दिक्कत हो, या शिशु, बुज़ुर्ग या पुरानी बीमारी वाला व्यक्ति प्रभावित हो तो डॉक्टर को दिखाएं।"),
    },
    "sore_throat": {
        "hinglish": ("Gale mein kharash aam taur par cold ya flu jaise viral infection se hoti hai. Allergy, sookhi hawa, dhuan aur strep throat jaise bacterial infection bhi iska karan ho sakte hain.",
                     "Garam namak ke paani se gargle karein, shahad ke saath garam peya peeyein (1 saal se chhote bachon ko shahad nahi), awaaz ko aaram dein, khoob taral padarth peeyein aur dhuein se bachein.",
                     "Agar gale ka dard ek hafte se zyada rahe, tez bukhar ho, nigalne ya saans lene mein dikkat ho, laar tapke, rash ho ya tonsils par safed dhabbe hon to doctor ko dikhayein."),
        "hi": ("गले में खराश आमतौर पर सर्दी या फ्लू जैसे वायरल संक्रमण से होती है। एलर्जी, सूखी हवा, धुआं और स्ट्रेप थ्रोट जैसे बैक्टीरियल संक्रमण भी इसका कारण हो सकते हैं।",
               "गर्म नमक के पानी से गरारे करें, शहद के साथ गर्म पेय पिएं (1 साल से छोटे बच्चों को शहद नहीं), आवाज़ को आराम दें, खूब तरल पदार्थ पिएं और धुएं से बचें।",
               "यदि गले का दर्द एक हफ्ते से ज़्यादा रहे, तेज़ बुखार हो, निगलने या सांस लेने में दिक्कत हो, लार टपके, रैश हो या टॉन्सिल पर सफेद धब्बे हों तो डॉक्टर को दिखाएं।"),
    },
    "dizziness": {
        "hinglish": ("Chakkar aane ke kai karan ho sakte hain, jaise paani ki kami, low blood sugar, low blood pressure, achanak khade hona, anaemia, kaan ki samasya, anxiety aur kuch dawaiyan.",
                     "Baith ya let jayein, paani peeyein, kuch khayein, aur dheere se khade hon. Jab tak chakkar na ruke, gaadi chalane ya oonchai par chadhne se bachein.",
                     "Agar chakkar ke saath seene mein dard, behoshi, bolne mein dikkat, kamzori, tez sir dard ya nazar mein badlav ho to emergency madad lein. Baar-baar aaye to doctor ko dikhayein."),
        "hi": ("चक्कर आने के कई कारण हो सकते हैं, जैसे पानी की कमी, लो ब्लड शुगर, लो ब्लड प्रेशर, अचानक खड़े होना, एनीमिया, कान की समस्या, चिंता और कुछ दवाएं।",
               "बैठ या लेट जाएं, पानी पिएं, कुछ खाएं, और धीरे से खड़े हों। जब तक चक्कर न रुके, गाड़ी चलाने या ऊंचाई पर चढ़ने से बचें।",
               "यदि चक्कर के साथ सीने में दर्द, बेहोशी, बोलने में दिक्कत, कमज़ोरी, तेज़ सिरदर्द या नज़र में बदलाव हो तो इमरजेंसी मदद लें। बार-बार आए तो डॉक्टर को दिखाएं।"),
    },
    "indigestion": {
        "hinglish": ("Ajeerna, acidity, pet phoolna aur kabz aam pachan ki samasyayein hain, jo aksar jaldi-jaldi khane, bhaari ya tele khane, kam fibre ya paani, stress ya kam activity se hoti hain.",
                     "Chhote-chhote meals dheere-dheere khayein, tela aur masaledar khana tatha der raat ka khana avoid karein, paani peeyein, fal, sabziyan aur sabut anaj jaise fibre wale khane khayein aur active rahein. Khane ke turant baad let na jayein.",
                     "Agar lakshan 2 hafte se zyada rahein, ya potty mein khoon, kala mal, ulti, bina wajah wazan ghatna ya nigalne mein dikkat ho to doctor ko dikhayein. Pet mein tez ya achanak dard ho to emergency madad lein."),
        "hi": ("अपच, एसिडिटी, पेट फूलना और कब्ज़ आम पाचन समस्याएं हैं, जो अक्सर जल्दी-जल्दी खाने, भारी या तैलीय खाने, कम फाइबर या पानी, तनाव या कम गतिविधि से होती हैं।",
               "छोटे-छोटे भोजन धीरे-धीरे खाएं, तैलीय और मसालेदार खाना तथा देर रात का खाना टालें, पानी पिएं, फल, सब्ज़ियां और साबुत अनाज जैसे फाइबर वाले खाद्य खाएं और सक्रिय रहें। खाने के तुरंत बाद लेटें नहीं।",
               "यदि लक्षण 2 हफ्ते से ज़्यादा रहें, या मल में खून, काला मल, उल्टी, बिना कारण वज़न घटना या निगलने में दिक्कत हो तो डॉक्टर को दिखाएं। पेट में तेज़ या अचानक दर्द हो तो इमरजेंसी मदद लें।"),
    },
    "food_poisoning": {
        "hinglish": ("Food poisoning kitanu wale khane ya paani se hone wali bimari hai. Ye aam taur par 1 se 3 din mein theek ho jati hai.",
                     "ORS ya saaf paani baar-baar ghoont-ghoont kar peeyein, aaram karein, aur jab theek lage to chawal, kela ya toast jaise halke khane khayein. Alcohol aur tela khana avoid karein.",
                     "Agar potty mein khoon, tez bukhar, dehydration ke sanket, ya 3 din se zyada lakshan hon, ya mareez baby, buzurg ya pregnant ho to doctor ko dikhayein."),
        "hi": ("फूड पॉइज़निंग कीटाणुओं वाले खाने या पानी से होने वाली बीमारी है। यह आमतौर पर 1 से 3 दिन में ठीक हो जाती है।",
               "ORS या साफ पानी बार-बार घूंट-घूंट करके पिएं, आराम करें, और जब ठीक लगे तो चावल, केला या टोस्ट जैसे हल्के खाने खाएं। शराब और तैलीय खाने से बचें।",
               "यदि मल में खून, तेज़ बुखार, डिहाइड्रेशन के संकेत, या 3 दिन से ज़्यादा लक्षण हों, या मरीज़ शिशु, बुज़ुर्ग या गर्भवती हो तो डॉक्टर को दिखाएं।"),
    },
    "fatigue": {
        "hinglish": ("Hamesha thakan mehsoos hona kam neend, stress, asantulit khana, kam exercise ya anaemia, thyroid, diabetes ya depression jaisi kisi chhipi samasya se ho sakta hai.",
                     "7 se 9 ghante soyein, time par santulit khana khayein, paani peeyein, halki exercise karein, caffeine aur alcohol kam karein aur aaram ka samay nikalein.",
                     "Agar thakan 2 hafte se zyada rahe, ya wazan ghatna, bukhar, saans phoolna, udasi ya koi naye lakshan hon to doctor ko dikhayein. Basic blood tests se karan pata chal sakta hai."),
        "hi": ("हमेशा थकान महसूस होना कम नींद, तनाव, असंतुलित खान-पान, कम व्यायाम या एनीमिया, थायरॉइड, डायबिटीज़ या डिप्रेशन जैसी किसी छिपी समस्या से हो सकता है।",
               "7 से 9 घंटे सोएं, समय पर संतुलित खाना खाएं, पानी पिएं, हल्का व्यायाम करें, कैफीन और शराब कम करें और आराम का समय निकालें।",
               "यदि थकान 2 हफ्ते से ज़्यादा रहे, या वज़न घटना, बुखार, सांस फूलना, उदासी या कोई नए लक्षण हों तो डॉक्टर को दिखाएं। बेसिक ब्लड टेस्ट से कारण पता चल सकता है।"),
    },
    "insomnia": {
        "hinglish": ("Insomnia ka matlab hai neend aane mein, neend banaye rakhne mein dikkat, ya bahut jaldi jaag jaana. Stress, aniyamit routine, caffeine, screen ka use aur kuch health conditions aam karan hain.",
                     "Roz ek hi samay par sone aur uthne ki aadat banayein, dopahar ke baad caffeine na lein, sone se ek ghanta pehle phone door rakhein, kamra thanda aur andhera rakhein, aur relaxation ya breathing exercise karein.",
                     "Agar kharab neend kuch hafton se zyada rahe ya din ke kaam par asar daale to doctor ko dikhayein. Doctor ki salah ke bina neend ki goliyon par nirbhar na rahein."),
        "hi": ("इनसोम्निया का मतलब है नींद आने में, नींद बनाए रखने में दिक्कत, या बहुत जल्दी जाग जाना। तनाव, अनियमित दिनचर्या, कैफीन, स्क्रीन का उपयोग और कुछ स्वास्थ्य स्थितियां आम कारण हैं।",
               "रोज़ एक ही समय पर सोने और उठने की आदत बनाएं, दोपहर के बाद कैफीन न लें, सोने से एक घंटा पहले फोन दूर रखें, कमरा ठंडा और अंधेरा रखें, और रिलैक्सेशन या ब्रीदिंग एक्सरसाइज़ करें।",
               "यदि खराब नींद कुछ हफ्तों से ज़्यादा रहे या दिन के काम पर असर डाले तो डॉक्टर को दिखाएं। डॉक्टर की सलाह के बिना नींद की गोलियों पर निर्भर न रहें।"),
    },
    "diabetes_basics": {
        "hinglish": ("Diabetes ek lambe samay ki sthiti hai jismein blood sugar bahut zyada rehta hai kyunki sharir insulin sahi tarah se nahi banata ya use nahi karta. Aam prakar hain type 1, type 2 aur gestational diabetes.",
                     "Apne doctor ya diabetes educator ki di hui yojana ka paalan karein, dawaiyan khud na badlein ya na chhodein, aur niyamit follow-up karwayein. Registered Dietitian meal planning mein madad kar sakte hain.",
                     "General Physician ya Endocrinologist/Diabetologist ko dikhayein. Confusion, behoshi, baar-baar ulti, phal jaisi gandh wali saans, ya bahut zyada ya bahut kam blood sugar mein turant ilaaj lein."),
        "hi": ("डायबिटीज़ एक लंबे समय की स्थिति है जिसमें ब्लड शुगर बहुत ज़्यादा रहता है क्योंकि शरीर इंसुलिन सही तरह से नहीं बनाता या उसका उपयोग नहीं करता। आम प्रकार हैं टाइप 1, टाइप 2 और गर्भावधि मधुमेह।",
               "अपने डॉक्टर या डायबिटीज़ एजुकेटर की दी हुई योजना का पालन करें, दवाएं खुद न बदलें या न छोड़ें, और नियमित फॉलो-अप करवाएं। रजिस्टर्ड डाइटीशियन भोजन योजना में मदद कर सकते हैं।",
               "General Physician या Endocrinologist/Diabetologist को दिखाएं। भ्रम, बेहोशी, बार-बार उल्टी, फल जैसी गंध वाली सांस, या बहुत ज़्यादा या बहुत कम ब्लड शुगर में तुरंत इलाज लें।"),
    },
    "blood_pressure": {
        "hinglish": ("High blood pressure (hypertension) mein aam taur par koi lakshan nahi hote, isliye ise silent killer kaha jata hai. Samay ke saath ye heart attack, stroke aur kidney disease ka khatra badhata hai.",
                     "Namak kam karein, active rahein, healthy wazan banaye rakhein, alcohol seemit karein, dhumrapan na karein, stress sambhalein aur niyamit roop se apna blood pressure check karein.",
                     "Baar-baar high reading aaye to doctor ko dikhayein. Bahut zyada pressure ke saath seene mein dard, tez sir dard, kamzori ya bolne mein dikkat ho to emergency ilaaj lein."),
        "hi": ("हाई ब्लड प्रेशर (हाइपरटेंशन) में आमतौर पर कोई लक्षण नहीं होते, इसीलिए इसे साइलेंट किलर कहा जाता है। समय के साथ यह हार्ट अटैक, स्ट्रोक और किडनी रोग का खतरा बढ़ाता है।",
               "नमक कम करें, सक्रिय रहें, स्वस्थ वज़न बनाए रखें, शराब सीमित करें, धूम्रपान न करें, तनाव संभालें और नियमित रूप से अपना ब्लड प्रेशर जांचें।",
               "बार-बार हाई रीडिंग आए तो डॉक्टर को दिखाएं। बहुत ज़्यादा प्रेशर के साथ सीने में दर्द, तेज़ सिरदर्द, कमज़ोरी या बोलने में दिक्कत हो तो इमरजेंसी इलाज लें।"),
    },
    "stress_signs": {
        "hinglish": ("Stress dabav ya maangon par sharir ki pratikriya hai. Thoda stress normal hai, lekin lambe samay ka stress aapki sehat par asar daal sakta hai.",
                     "Niyamit exercise, gehri saans, achhi neend, kaam se break, doston aur parivar ke saath samay, aur apni chintayein share karna aazmayein. Caffeine aur alcohol kam karein.",
                     "Agar stress hafton tak aapki daily life par asar daale to doctor ya counsellor se baat karein. Khud ko nuksan pahunchane ke vichar aayein to turant emergency services ya crisis helpline se sampark karein."),
        "hi": ("तनाव दबाव या मांगों पर शरीर की प्रतिक्रिया है। थोड़ा तनाव सामान्य है, लेकिन लंबे समय का तनाव आपकी सेहत पर असर डाल सकता है।",
               "नियमित व्यायाम, गहरी सांस, अच्छी नींद, काम से ब्रेक, दोस्तों और परिवार के साथ समय, और अपनी चिंताएं साझा करना आज़माएं। कैफीन और शराब कम करें।",
               "यदि तनाव हफ्तों तक आपकी रोज़मर्रा की ज़िंदगी पर असर डाले तो डॉक्टर या काउंसलर से बात करें। खुद को नुकसान पहुंचाने के विचार आएं तो तुरंत इमरजेंसी सेवा या क्राइसिस हेल्पलाइन से संपर्क करें।"),
    },
    "anxiety_signs": {
        "hinglish": ("Anxiety sharir ka alarm system hai jo chinta ya khatre par pratikriya deta hai. Kabhi-kabhi anxiety hona normal hai, lekin lagatar ya bahut zyada anxiety ka ilaaj ho sakta hai.",
                     "Dheeri gehri saans, niyamit exercise, fixed neend ki routine, kam caffeine, chintayein likhna, aur kisi bharosemand se baat karna aazmayein. Grounding madad kar sakti hai: paanch cheezein jo aap dekh sakte hain aur chaar jo chhoo sakte hain, unke naam lein.",
                     "Agar anxiety hafton tak rahe, zindagi mein dikkat daale, ya panic attacks ke saath ho to doctor ya mental health professional ko dikhayein. Seene mein dard ya khud ko nuksan ke vichar mein turant madad lein."),
        "hi": ("चिंता (एंग्ज़ायटी) शरीर का अलार्म सिस्टम है जो फिक्र या खतरे पर प्रतिक्रिया देता है। कभी-कभी चिंता होना सामान्य है, लेकिन लगातार या बहुत ज़्यादा चिंता का इलाज हो सकता है।",
               "धीमी गहरी सांस, नियमित व्यायाम, तय नींद की दिनचर्या, कम कैफीन, चिंताएं लिखना, और किसी भरोसेमंद से बात करना आज़माएं। ग्राउंडिंग मदद कर सकती है: पांच चीज़ें जो आप देख सकते हैं और चार जो छू सकते हैं, उनके नाम लें।",
               "यदि चिंता हफ्तों तक रहे, ज़िंदगी में बाधा डाले, या पैनिक अटैक के साथ हो तो डॉक्टर या मानसिक स्वास्थ्य विशेषज्ञ को दिखाएं। सीने में दर्द या खुद को नुकसान के विचार में तुरंत मदद लें।"),
    },
    "back_pain": {
        "hinglish": ("Zyadatar kamar dard maanspeshiyon ke khinchav, galat posture, der tak baithne ya bhaari saman uthane se hota hai, aur aam taur par kuch hafton mein theek ho jata hai.",
                     "Bed rest ke bajay halke active rahein, garam sek (heat pack) lein, peeth ko sahara dekar baithein, har 30 minute mein chalein-phirein, core ko majboot karein aur ghutne modkar saman uthayein.",
                     "Agar dard 4 se 6 hafte se zyada rahe, ya pair mein kamzori, sunnpan, bukhar ya wazan ghatna ho to doctor ko dikhayein. Peshab-potty par kaabu khone ya gambhir girne ke baad dard mein emergency madad lein."),
        "hi": ("ज़्यादातर कमर दर्द मांसपेशियों के खिंचाव, गलत पोस्चर, देर तक बैठने या भारी सामान उठाने से होता है, और आमतौर पर कुछ हफ्तों में ठीक हो जाता है।",
               "बेड रेस्ट के बजाय हल्के सक्रिय रहें, गर्म सेक (हीट पैक) लें, पीठ को सहारा देकर बैठें, हर 30 मिनट में चलें-फिरें, कोर को मज़बूत करें और घुटने मोड़कर सामान उठाएं।",
               "यदि दर्द 4 से 6 हफ्ते से ज़्यादा रहे, या पैर में कमज़ोरी, सुन्नपन, बुखार या वज़न घटना हो तो डॉक्टर को दिखाएं। पेशाब-शौच पर काबू खोने या गंभीर गिरने के बाद दर्द में इमरजेंसी मदद लें।"),
    },
    "joint_pain": {
        "hinglish": ("Jodon ka dard aksar chot, zyada istemal ya arthritis se hota hai. Osteoarthritis jodon ki ghisavat hai jo umar ke saath aam hai, jabki rheumatoid arthritis ek immune sthiti hai.",
                     "Walking, swimming ya cycling jaise low-impact exercise se chalte rahein, healthy wazan banaye rakhein, garam ya thande pack lein, aur haddiyon ki sehat ke liye paryapt calcium aur vitamin D lein.",
                     "Agar jod garam, laal aur soojha ho, dard kuch hafton se zyada rahe, subah akdan 30 minute se zyada rahe, ya aap jod hila na payein to doctor ko dikhayein."),
        "hi": ("जोड़ों का दर्द अक्सर चोट, ज़्यादा उपयोग या अर्थराइटिस से होता है। ऑस्टियोआर्थराइटिस जोड़ों की घिसावट है जो उम्र के साथ आम है, जबकि रूमेटॉइड अर्थराइटिस एक इम्यून स्थिति है।",
               "वॉकिंग, तैराकी या साइकिलिंग जैसे लो-इम्पैक्ट व्यायाम से चलते रहें, स्वस्थ वज़न बनाए रखें, गर्म या ठंडे पैक लें, और हड्डियों की सेहत के लिए पर्याप्त कैल्शियम और विटामिन D लें।",
               "यदि जोड़ गर्म, लाल और सूजा हो, दर्द कुछ हफ्तों से ज़्यादा रहे, सुबह अकड़न 30 मिनट से ज़्यादा रहे, या आप जोड़ हिला न पाएं तो डॉक्टर को दिखाएं।"),
    },
    "skin_rash": {
        "hinglish": ("Skin rash aur khujli allergy, garmi, sookhi twacha, eczema, infection, keede ke kaatne ya sabun aur dawaiyon ke reaction se ho sakti hai. Pimples band hui tel granthiyon aur hormone badlav se hote hain.",
                     "Khujlane aur jaane-pehchane triggers se bachein, halka sabun use karein, niyamit moisturise karein, dheele sooti kapde pehnein, twacha saaf rakhein aur pimples ko na dabayein.",
                     "Agar rash tezi se phaile, dard kare, chhale pade, peep ho, bukhar ke saath ho, ya 2 hafte se zyada rahe to doctor ko dikhayein. Chehre par sujan ya saans mein dikkat ho to emergency madad lein."),
        "hi": ("त्वचा पर रैश और खुजली एलर्जी, गर्मी, सूखी त्वचा, एक्ज़िमा, संक्रमण, कीड़े के काटने या साबुन और दवाओं के रिएक्शन से हो सकती है। मुंहासे बंद तेल ग्रंथियों और हार्मोन बदलाव से होते हैं।",
               "खुजलाने और जाने-पहचाने कारणों से बचें, हल्का साबुन इस्तेमाल करें, नियमित मॉइस्चराइज़ करें, ढीले सूती कपड़े पहनें, त्वचा साफ रखें और मुंहासों को न दबाएं।",
               "यदि रैश तेज़ी से फैले, दर्द करे, छाले पड़ें, मवाद हो, बुखार के साथ हो, या 2 हफ्ते से ज़्यादा रहे तो डॉक्टर को दिखाएं। चेहरे पर सूजन या सांस में दिक्कत हो तो इमरजेंसी मदद लें।"),
    },
    "toothache": {
        "hinglish": ("Daant dard aksar daant ke sadne (cavities) se hota hai, lekin masudon ki bimari, tuta daant, abscess ya daant pisna bhi iska karan ho sakte hain.",
                     "Garam namak ke paani se kulla karein, dheere se brush karein, phasa hua khana nikalne ke liye floss karein, aur dentist ko dikhane tak bahut garam, thande ya meethe khane se bachein.",
                     "Jald dentist ko dikhayein. Chehre par sujan, bukhar, ya nigalne ya saans lene mein dikkat ho to turant ilaaj lein."),
        "hi": ("दांत दर्द अक्सर दांत के सड़ने (कैविटी) से होता है, लेकिन मसूड़ों की बीमारी, टूटा दांत, एब्सेस या दांत पीसना भी इसका कारण हो सकते हैं।",
               "गर्म नमक के पानी से कुल्ला करें, धीरे से ब्रश करें, फंसा हुआ खाना निकालने के लिए फ्लॉस करें, और डेंटिस्ट को दिखाने तक बहुत गर्म, ठंडे या मीठे खाने से बचें।",
               "जल्द डेंटिस्ट को दिखाएं। चेहरे पर सूजन, बुखार, या निगलने या सांस लेने में दिक्कत हो तो तुरंत इलाज लें।"),
    },
    "hydration": {
        "hinglish": ("Paani sharir ka temperature, pachan, jodon aur kidney ke kaam ko sambhalne mein madad karta hai. Zyadatar swasth vayask ko roz lagbhag 2 se 3 litre taral padarth chahiye, garmi mein ya exercise ke samay zyada.",
                     "Din bhar ghoont-ghoont kar paani peeyein, zyada paani wale fal aur sabziyan khayein, aur garmi mein ya bimar hone par zyada peeyein. Halke peele rang ka peshab achha sanket hai.",
                     "Agar aap taral padarth rok na payein, bahut chakkar ya confusion ho, ya bahut kam peshab ho to doctor ko dikhayein. Dil ya kidney ke rogiyon ko poochna chahiye ki kitna peena hai."),
        "hi": ("पानी शरीर का तापमान, पाचन, जोड़ों और किडनी के काम को संभालने में मदद करता है। ज़्यादातर स्वस्थ वयस्कों को रोज़ लगभग 2 से 3 लीटर तरल पदार्थ चाहिए, गर्मी में या व्यायाम के समय ज़्यादा।",
               "दिन भर घूंट-घूंट करके पानी पिएं, ज़्यादा पानी वाले फल और सब्ज़ियां खाएं, और गर्मी में या बीमार होने पर ज़्यादा पिएं। हल्के पीले रंग का पेशाब अच्छा संकेत है।",
               "यदि आप तरल पदार्थ रोक न पाएं, बहुत चक्कर या भ्रम हो, या बहुत कम पेशाब हो तो डॉक्टर को दिखाएं। दिल या किडनी के रोगियों को पूछना चाहिए कि कितना पीना है।"),
    },
    "healthy_diet": {
        "hinglish": ("Healthy diet mein tarah-tarah ki sabziyan, fal, sabut anaj, protein wale khane aur achhi charbi shamil hoti hai, jabki cheeni, namak aur bahut processed khane ko seemit rakha jata hai.",
                     "Apni plate ka aadha hissa sabziyon aur falon se bharein, time par khana khayein, matra par dhyan dein, meethe peyon ke bajay paani peeyein aur jab ho sake ghar par pakayein.",
                     "Agar aapko diabetes, kidney disease, food allergy ho, aap pregnant hon, ya diet mein bade badlav karna chahte hon to doctor ya dietitian se baat karein."),
        "hi": ("स्वस्थ आहार में तरह-तरह की सब्ज़ियां, फल, साबुत अनाज, प्रोटीन वाले खाद्य और अच्छी वसा शामिल होती है, जबकि चीनी, नमक और बहुत प्रोसेस्ड खाने को सीमित रखा जाता है।",
               "अपनी प्लेट का आधा हिस्सा सब्ज़ियों और फलों से भरें, समय पर खाना खाएं, मात्रा पर ध्यान दें, मीठे पेयों के बजाय पानी पिएं और जब हो सके घर पर पकाएं।",
               "यदि आपको डायबिटीज़, किडनी रोग, फूड एलर्जी हो, आप गर्भवती हों, या आहार में बड़े बदलाव करना चाहते हों तो डॉक्टर या डाइटीशियन से बात करें।"),
    },
    "child_fever": {
        "hinglish": ("Bachon mein bukhar aam hai aur aam taur par viral infection se hota hai. Bachche ko aaramdayak, aaram mein aur achhi tarah hydrated rakhein.",
                     "Dekhein ki bachcha kaisa vyavhar kar raha hai: normal tarah se peena, khelna aur pratikriya dena achha sanket hai. Thande paani se nahlana ya alcohol se malish na karein.",
                     "3 mahine se chhote baby ko 38 C (100.4 F) ya usse zyada bukhar ho to turant doctor ke paas le jayein. Agar bachche ko 3 din se zyada bukhar ho, rash ho, gardan akdi ho, daura pade, saans mein dikkat ho, wo peene se mana kare ya bahut sust ho to doctor ko dikhayein."),
        "hi": ("बच्चों में बुखार आम है और आमतौर पर वायरल संक्रमण से होता है। बच्चे को आरामदायक, आराम में और अच्छी तरह हाइड्रेटेड रखें।",
               "देखें कि बच्चा कैसा व्यवहार कर रहा है: सामान्य तरह से पीना, खेलना और प्रतिक्रिया देना अच्छा संकेत है। ठंडे पानी से नहलाएं नहीं या अल्कोहल से मालिश न करें।",
               "3 महीने से छोटे शिशु को 38 C (100.4 F) या उससे ज़्यादा बुखार हो तो तुरंत डॉक्टर के पास ले जाएं। यदि बच्चे को 3 दिन से ज़्यादा बुखार हो, रैश हो, गर्दन अकड़ी हो, दौरा पड़े, सांस में दिक्कत हो, वह पीने से मना करे या बहुत सुस्त हो तो डॉक्टर को दिखाएं।"),
    },
    "breathing_difficulty": {
        "hinglish": ("Achanak ya gambhir saans lene mein dikkat ek medical emergency hai. Turant emergency services ko call karein.",
                     "Seedhe baithein, tight kapde dheele karein, shant rahne aur dheere saans lene ki koshish karein, aur agar aapke paas doctor ka diya reliever inhaler hai to use karein. Let na jayein.",
                     "Turant emergency services ko call karein, khaaskar agar saans lene mein dikkat badh rahi ho ya hont neele dikh rahe hon."),
        "hi": ("अचानक या गंभीर सांस लेने में दिक्कत एक मेडिकल इमरजेंसी है। तुरंत इमरजेंसी सेवा को कॉल करें।",
               "सीधे बैठें, तंग कपड़े ढीले करें, शांत रहने और धीरे सांस लेने की कोशिश करें, और यदि आपके पास डॉक्टर का दिया रिलीवर इन्हेलर है तो उपयोग करें। लेटें नहीं।",
               "तुरंत इमरजेंसी सेवा को कॉल करें, खासकर यदि सांस लेने में दिक्कत बढ़ रही हो या होंठ नीले दिख रहे हों।"),
    },
    "chest_pain_emergency": {
        "hinglish": ("Seene mein tez dard heart attack ka sanket ho sakta hai aur ye medical emergency hai. Turant apne local emergency number (jaise Bharat mein 112 ya 108) par call karein.",
                     "Sab gatividhi rok kar baith jayein, shant rahein, aur agar akele hon to darwaza khol dein. Khud gaadi chala kar hospital na jayein. Agar doctor ne pehle kaha ho to madad aane tak aspirin chaba lein.",
                     "Turant emergency services ko call karein. Ye dekhne ke liye ruke nahi ki dard apne aap chala jata hai ya nahi."),
        "hi": ("सीने में तेज़ दर्द हार्ट अटैक का संकेत हो सकता है और यह मेडिकल इमरजेंसी है। तुरंत अपने स्थानीय इमरजेंसी नंबर (जैसे भारत में 112 या 108) पर कॉल करें।",
               "सब गतिविधि रोककर बैठ जाएं, शांत रहें, और यदि अकेले हों तो दरवाज़ा खोल दें। खुद गाड़ी चलाकर अस्पताल न जाएं। यदि डॉक्टर ने पहले कहा हो तो मदद आने तक एस्पिरिन चबा लें।",
               "तुरंत इमरजेंसी सेवा को कॉल करें। यह देखने के लिए रुकें नहीं कि दर्द अपने आप चला जाता है या नहीं।"),
    },
    "menstrual_cramps": {
        "hinglish": ("Menstrual cramps pet ke neeche ke hisse mein dhadakne ya dukhne wala dard hai jo period se pehle ya uske dauran shuru hota hai. Ye bahut aam hai.",
                     "Garam sek (heat pad), halki exercise, aaram, garam peya aur relaxation madad kar sakte hain. Dard ki kaun si dawai theek hai, ye doctor ya pharmacist se poochein.",
                     "Agar dard tez ho, samay ke saath badhe, roz ke kaam rok de, bahut zyada bleeding ke saath ho, ya 25 saal ki umar ke baad shuru ho to doctor ko dikhayein."),
        "hi": ("मासिक धर्म की ऐंठन पेट के निचले हिस्से में धड़कने या दुखने वाला दर्द है जो पीरियड से पहले या उसके दौरान शुरू होता है। यह बहुत आम है।",
               "गर्म सेक (हीट पैड), हल्का व्यायाम, आराम, गर्म पेय और रिलैक्सेशन मदद कर सकते हैं। दर्द की कौन सी दवा ठीक है, यह डॉक्टर या फार्मासिस्ट से पूछें।",
               "यदि दर्द तेज़ हो, समय के साथ बढ़े, रोज़ के काम रोक दे, बहुत ज़्यादा ब्लीडिंग के साथ हो, या 25 साल की उम्र के बाद शुरू हो तो डॉक्टर को दिखाएं।"),
    },
    "uti": {
        "hinglish": ("Urinary tract infection (UTI) mutrashay ya mutra marg ka bacterial infection hai. Ye aam hai, khaaskar mahilaon mein, aur ismein doctor se ilaaj ki zaroorat hoti hai.",
                     "Khoob paani peeyein, peshab der tak na rokein, sambandh ke baad peshab karein, aage se peeche ki taraf pochhein aur nijee ang ko saaf rakhein.",
                     "Urine test aur ilaaj ke liye doctor ko dikhayein. Bukhar, kaampna, peeth ya kamar ke side mein dard, ulti ho, ya mareez pregnant, bachha ya buzurg ho to turant ilaaj lein."),
        "hi": ("मूत्र मार्ग संक्रमण (UTI) मूत्राशय या मूत्र मार्ग का बैक्टीरियल संक्रमण है। यह आम है, खासकर महिलाओं में, और इसमें डॉक्टर से इलाज की ज़रूरत होती है।",
               "खूब पानी पिएं, पेशाब देर तक न रोकें, संबंध के बाद पेशाब करें, आगे से पीछे की ओर पोंछें और निजी अंग को साफ रखें।",
               "यूरिन टेस्ट और इलाज के लिए डॉक्टर को दिखाएं। बुखार, कंपकंपी, पीठ या बगल में दर्द, उल्टी हो, या मरीज़ गर्भवती, बच्चा या बुज़ुर्ग हो तो तुरंत इलाज लें।"),
    },
    "medicine_precautions": {
        "hinglish": ("Dawaiyan sahi tarah se use karne par surakshit hoti hain. Hamesha doctor ya pharmacist ke nirdesh maanein aur use se pehle label padhein.",
                     "Likhi hui dawai khud se na rokein ya badlein, dawaiyan bachon ki pahunch se door rakhein, aur dawaiyan milane se pehle pharmacist se poochein.",
                     "Agar rash, sujan, saans mein dikkat, ulti ya koi anokhi pratikriya ho to doctor ya pharmacist se sampark karein. Zyada dawai khane ke shak mein turant emergency services ko call karein."),
        "hi": ("दवाएं सही तरह से उपयोग करने पर सुरक्षित होती हैं। हमेशा डॉक्टर या फार्मासिस्ट के निर्देश मानें और उपयोग से पहले लेबल पढ़ें।",
               "लिखी हुई दवा खुद से न रोकें या बदलें, दवाएं बच्चों की पहुंच से दूर रखें, और दवाएं मिलाने से पहले फार्मासिस्ट से पूछें।",
               "यदि रैश, सूजन, सांस में दिक्कत, उल्टी या कोई असामान्य प्रतिक्रिया हो तो डॉक्टर या फार्मासिस्ट से संपर्क करें। ज़्यादा दवा खाने के शक में तुरंत इमरजेंसी सेवा को कॉल करें।"),
    },
    "medication_dosage_request": {
        "hinglish": ("Main aapko personal dawai ki matra (dose) nahi bata sakta. Sahi matra umar, wazan, doosri bimariyon, doosri dawaiyon aur exact product par nirbhar karti hai, aur galat dose nuksan kar sakti hai.",
                     "Kripya label ya prescription dekhein, ya pharmacist ya apne doctor se poochein. Jaldi aaram ke liye extra dose na lein, aur ek hi ingredient wale products ko saath na lein.",
                     "Agar zyada dawai li gayi ho sakti hai, ya koi gambhir reaction hua ho to turant medical madad lein. 112 par call karein ya nazdeeki hospital jayein."),
        "hi": ("मैं आपको व्यक्तिगत दवा की मात्रा (डोज़) नहीं बता सकता। सही मात्रा उम्र, वज़न, दूसरी बीमारियों, दूसरी दवाओं और सटीक प्रोडक्ट पर निर्भर करती है, और गलत डोज़ नुकसान कर सकती है।",
               "कृपया लेबल या पर्चा देखें, या फार्मासिस्ट या अपने डॉक्टर से पूछें। जल्दी आराम के लिए अतिरिक्त डोज़ न लें, और एक ही तत्व वाले प्रोडक्ट साथ न लें।",
               "यदि ज़्यादा दवा ली गई हो सकती है, या कोई गंभीर रिएक्शन हुआ हो तो तुरंत चिकित्सा मदद लें। 112 पर कॉल करें या नज़दीकी अस्पताल जाएं।"),
    },
}
def strings(lang):
    return STR.get(lang) or STR["en"]


def topic_text(topic_id, lang):
    """(short, advice, doctor) in `lang`, or None when no translation exists."""
    entry = TOPIC_I18N.get(topic_id)
    return entry.get(lang) if entry and lang in entry else None


def small_talk_reply(kind, lang, seed=0):
    options = SMALL_TALK.get(kind, SMALL_TALK["greeting"]).get(lang) or SMALL_TALK[kind]["en"]
    return options[seed % len(options)] if lang == "en" else options[0]   # Hindi/Hinglish: the Namaste form, deterministic
