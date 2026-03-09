# 📞 Super Call Intelligence: Live Demo Scripts

These scripts are designed to showcase the full power of your application. Read the **Agent** lines exactly as written, and have someone else read the **Customer** lines. Remember, Azure Speech is mapping the speakers, so the **Agent should ALWAYS speak first** to lock in "Guest-1".

---

## 🚗 Scenario 1: Phone Lookup & Towing (Natural Flow)
**Goal:** Show the AI handling a missing policy number gracefully by switching to a phone number lookup, deducing facts (date), and enforcing coverage limits naturally.

**Data Targeted:** Priya Sharma (`CAR-100002` / `+91 87654-32109` - Third Party Only)

**[🎤 START CALL]**

**Agent:** "Thank you for calling Super Insurance claims. This call is recorded for quality purposes. My name is Alex, how can I help you today?"

**Customer:** "Hi Alex. I just got into a car accident. My car is pretty messed up."
*(Wait for the AI intent to classify as `car_accident` and show the Accident FNOL Knowledge Card. The AI should deduce the accident happened today.)*

**Agent:** "I'm so sorry to hear that. Are you okay? "

**Customer:** "Yeah, we're completely fine. The other guy is fine too."
*(Wait for AI suggestion to update. It will likely ask for the policy number.)*

**Agent:** "I'm very glad to hear everyone is safe. Do you happen to have your policy number handy so I can pull up your account?"

**Customer:** "Actually no, I don't have my card on me. Is there another way to find it?"
*(The AI should pivot to ask for the phone number.)*

**Agent:** "Not a problem at all. Can I have the phone number associated with your account?"

**Customer:** "Sure, it's 876 543 2109."
*(Wait for Fast-Path to instantly pull up Priya Sharma's profile based on the phone number.)*

**Agent:** "Thank you, Priya. I see your 2022 Maruti Suzuki Swift here. Is the car drivable, or do you need a tow?"

**Customer:** "It's definitely not drivable. Can you send a tow truck?"
*(Wait for the AI to check coverage. It should notice Priya only has 'Third Party' coverage and NO towing add-ons.)*

**Agent:** "I can certainly arrange a tow truck for you. Because your current policy only includes Third-Party coverage, the towing won't be covered, so it will be an out-of-pocket expense. Would you still like me to send one?"

**Customer:** "Ah, I see. Yes, please send one anyway. I need to get the car moved."

**Agent:** "Understood, I'll get that arranged. By the way, did you file a police report for this accident?"

**Customer:** "Yes, I did. The FIR number is FIR-2026-MH-4521."
*(The AI should extract and track the police report number.)*

**Agent:** "Perfect, thank you for that. A claims adjuster will be in touch with you within 24-48 hours. Is there anything else I can help with?"

**Customer:** "No, that's all. Thank you."

**[⏹ END CALL]**

---

## 🚨 Scenario 2: Fake Policy & Identity Mismatch
**Goal:** Show the system gracefully recovering from a fake policy number, then dealing with a caller whose name doesn't match the primary policyholder.

**Data Targeted:** Rajesh Kumar (`CAR-100001` - but caller is his brother, Ravi)

**[🎤 START CALL]**

**Agent:** "Thank you for calling Super Insurance claims. This call is being recorded. My name is Alex, how may I assist you?"

**Customer:** "Hi Alex, someone backed into my car in the parking lot and drove off. I need to file a claim."

**Agent:** "I'm sorry to hear about that hit and run. I can definitely help you with that. Can I start with your policy number please?"

**Customer:** "Yeah, it's C A R 9 9 9 9 9 9."
*(Profile will not load. The AI will prompt the agent to double-check the number.)*

**Agent:** "I'm sorry, my system isn't bringing anything up for that number. Did you say C A R 9 9 9 9 9 9? Or is it possible there's a typo?"

**Customer:** "Ah man, this old card is so faded I can't even read it. Can we just use my phone number? It's 987 654 3210."
*(Profile loads for Rajesh Kumar.)*

**Agent:** "Thank you. I see the policy here for the 2023 Hyundai Creta under the name Rajesh Kumar. Am I speaking with Rajesh?"

**Customer:** "Actually no, I'm his brother, Ravi. I was driving his car when it happened."
*(The AI should notice the mismatch and suggest clarifying the relationship and ensuring Rajesh knows.)*

**Agent:** "Thanks for clarifying, Ravi. Just so I have it for the record, does Rajesh know about the damage, and do you have his permission to file the claim on his behalf?"

**Customer:** "Yes, he's standing right next to me."

**Agent:** "Perfect. Did you happen to get the license plate or any details of the car that backed into you?"

**Customer:** "No, they drove off too fast. I didn't see anything."

**Agent:** "That's alright. Since this was a hit and run, you'll need to file a police report to proceed with the vandalism claim under Rajesh's comprehensive coverage. Once you have that report, an adjuster will reach out to schedule repairs."

**Customer:** "Understood. We will go do that now. Thank you."

**[⏹ END CALL]**

---

## 🕊️ Scenario 3: Life Insurance Death Claim (Sensitive Flow)
**Goal:** Show the AI handling a highly sensitive life insurance claim. It should express condolences just once, verify the caller's identity against the beneficiary list, navigate HIPAA requirements, and carefully collect the date and cause of death without asking to speak to the deceased.

**Data Targeted:** Suresh Menon (`LIFE-200001` - Caller is his son, Anand Menon)

**[🎤 START CALL]**

**Agent:** "Thank you for calling Super Insurance claims. This call is being recorded for quality and training purposes. My name is Alex, how may I assist you?"

**Customer:** "Hi Alex... my father passed away recently. I need to start a life insurance claim."
*(Wait for AI intent to classify as `life_death_claim`. The AI will suggest asking for the policy number.)*

**Agent:** "I am so incredibly sorry for your loss. I can certainly guide you through this process. Do you happen to have his policy number or phone number?"

**Customer:** "Yes, his policy number is L I F E 2 0 0 0 0 1."
*(Profile loads for Suresh Menon. The AI sees he is the policyholder and sees his beneficiaries. The AI deduces the caller is a child since they said 'father'. The AI will suggest confirming the caller's name.)*

**Agent:** "Thank you. I have the policy pulled up for Suresh Menon. For my records to verify against the listed beneficiaries, could I please have your full name?"

**Customer:** "My name is Anand Menon."
*(The AI verifies Anand is listed as a 40% beneficiary (Son). The AI HIPAA compliance rule triggers.)*

**Agent:** "Thank you, Anand. Please be advised that all medical and personal information discussed is protected under HIPAA. To start the claim, could you provide the date, location, and cause of your father's passing?"

**Customer:** "He passed away on February 10th at City General Hospital after a severe heart attack."
*(The AI captures these details. Contestability expired is true, so no contestability warning triggers. The AI suggests closing and next steps based on the KB.)*

**Agent:** "Thank you for sharing that information with me. To proceed, we will need a certified copy of the death certificate, a completed claim form, and a copy of your photo ID. I will email the forms to the address on file now. Is there anything else I can do to assist you today?"

**Customer:** "No, that should be everything for now. Thank you for your help."
*(AI recognizes the caller needs no further assistance and suggests a definite sign off.)*

**Agent:** "You're very welcome, Anand. We are here if you need anything else during this difficult time. Take care and goodbye."
**[Agent: End Call]**

---

## 🏥 Scenario 4: Emergency Hospitalization — Cashless Claim
**Goal:** Show the AI recognizing a medical hospitalization intent, checking network hospital status, guiding through the cashless pre-authorization process, communicating sub-limits and copay, and gathering all medical FNOL facts.

**Data Targeted:** Kavita Reddy (`MED-300001` – Individual Health, 10% copay, Private room)

**Agent:** "Thank you for calling Super Insurance, this is Agent speaking. How can I assist you today?"

**Customer:** "Hi, my name is Kavita Reddy. I was rushed to Apollo Hospital last night. I've been admitted for emergency appendicitis surgery. My policy number is MED-300001."
*(AI immediately classifies as `medical_hospitalization`, extracts policy MED-300001, hospital name "Apollo Hospital", and diagnosis "appendicitis". Fast-path regex picks up MED-300001 and loads Kavita's profile. AI confirms Apollo is in the `networkHospitals` list and tells the agent to inform about cashless eligibility.)*

**Agent:** "I'm sorry to hear about your emergency, Kavita. I've pulled up your policy and I can see that Apollo Hospital is in your network — so you are eligible for cashless treatment. Let me guide you through the process."

**Customer:** "Oh that's a relief. So I don't have to pay anything upfront?"
*(AI suggests explaining the copay and pre-authorization process.)*

**Agent:** "For cashless claims, the hospital's insurance desk will submit a pre-authorization request to our TPA. This is usually approved within one hour for emergencies. You will only need to pay a 10% copay and any charges that exceed your policy sub-limits."

**Customer:** "What are my sub-limits?"
*(AI pulls sub-limit data from the member profile and suggests the agent communicate them.)*

**Agent:** "Your room rent sub-limit is ₹8,000 per day for a private room, ICU charges are capped at ₹15,000 per day, and ambulance is covered up to ₹3,000 per trip. Since you're in a private room, you should be within your room rent limit."

**Customer:** "Okay, and Dr. Mehta is my treating surgeon. He said I'll probably be discharged in two or three days."
*(AI extracts treating doctor "Dr. Mehta" and notes approximate discharge timeline.)*

**Agent:** "Thank you for that information. I'll note Dr. Mehta as your treating surgeon. Now, has the hospital's insurance desk already contacted us for the pre-authorization, or do you need us to follow up with them?"

**Customer:** "They said they submitted it but haven't heard back yet."
*(AI suggests the agent reassure and provide the expected timeline.)*

**Agent:** "I'll follow up with our TPA team to expedite the pre-authorization for your emergency surgery. You should receive confirmation shortly. In the meantime, please make sure you keep all discharge summary documents, diagnostic reports, and pharmacy bills — we'll need these for our records."

**Customer:** "Will do. Is there anything else I need to know?"

**Agent:** "Just a few things — a claims coordinator will contact you within 24 hours to help you through the rest of the process. You don't need to worry about the paperwork while you're recovering. Is there anything else I can help with?"

**Customer:** "No, that covers everything. Thank you so much."

**Agent:** "You're welcome, Kavita. I hope you have a speedy recovery. Take care and don't hesitate to call us if you need anything. Goodbye!"
**[Agent: End Call]**

---

## 🏥 Scenario 5: Pre-Existing Condition — Reimbursement Claim
**Goal:** Show the AI handling a sensitive pre-existing condition scenario: the caller's diabetes-related hospitalization may be subject to a waiting period exclusion. Demonstrate the AI guiding the agent through waiting period rules, copay implications, and the reimbursement process — all while being empathetic.

**Data Targeted:** Rohit Deshmukh (`MED-300002` – Family Floater, 20% copay, PED waiting period active with 2 years remaining)

**Agent:** "Thank you for calling Super Insurance, this is Agent speaking. How can I help you today?"

**Customer:** "Hello, I'm calling about my husband's policy. His name is Rohit Deshmukh, policy number MED-300002. He was admitted to City General Hospital two days ago for diabetic ketoacidosis. He's been in the ICU."
*(AI detects `medical_hospitalization` intent, extracts MED-300002, hospital "City General Hospital", diagnosis "diabetic ketoacidosis", and admission date (2 days ago). Loads Rohit's profile. AI flags two critical issues: (1) City General is NOT in the `networkHospitals` list, so cashless is not available; (2) the pre-existing waiting period for Type 2 Diabetes is ACTIVE with 2 years remaining.)*

**Agent:** "I'm very sorry to hear about your husband's condition. Let me pull up his policy details. I can see his Family Floater policy is active. However, I need to let you know about two things regarding this claim."

**Customer:** "Okay, what is it?"
*(AI suggests the agent communicate the network hospital status first, then the pre-existing condition waiting period — sensitively.)*

**Agent:** "First, City General Hospital is not in your policy's network hospital list. This means the claim will need to be processed as a reimbursement — meaning you'll pay the hospital bills upfront and then submit them to us for reimbursement."

**Customer:** "I understand. And the second thing?"

**Agent:** "Since diabetic ketoacidosis is related to Type 2 Diabetes, which was disclosed as a pre-existing condition at the time of policy purchase, there is a 4-year waiting period that applies. Based on your policy records, the waiting period has 2 years remaining. This means the claim related to this condition may be subject to exclusion under the pre-existing condition clause."

**Customer:** "Oh no... so we won't get anything covered?"
*(AI suggests the agent be empathetic but factual, and explain what options exist.)*

**Agent:** "I understand this is concerning, and I want to make sure you have all the information. While the pre-existing condition waiting period does apply, I'd recommend submitting the claim anyway. Our claims team will do a full review — there are sometimes partial coverages or complications that may be assessed separately. I'll also note that your copay percentage for this policy is 20%."

**Customer:** "Okay, so what documents do we need to submit?"
*(AI lists all required reimbursement documents in one go.)*

**Agent:** "For the reimbursement process, you'll need to submit the following: original hospital bills, the discharge summary, all diagnostic reports, the treating doctor's prescription, pharmacy bills, and a completed claim form which I can email to the address on file. All documents should be submitted within 15 days of discharge."

**Customer:** "Alright. His doctor's name is Dr. Sanjay Patil, for your records."
*(AI extracts treating doctor "Dr. Sanjay Patil".)*

**Agent:** "Thank you, I've noted that. The reimbursement is typically processed within 30 days of receiving complete documentation. A claims coordinator will also reach out to you within 24 hours. Is there anything else I can help with?"

**Customer:** "No, thank you for explaining everything so clearly."

**Agent:** "You're welcome. I hope your husband recovers well. Please don't hesitate to call if you have any questions about the documents or the process. Take care and goodbye."
**[Agent: End Call]**
