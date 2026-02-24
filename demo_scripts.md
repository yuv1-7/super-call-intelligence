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
