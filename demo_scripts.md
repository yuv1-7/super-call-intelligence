# 📞 Super Call Intelligence: Live Demo Scripts

These scripts are designed to showcase the full power of your application. Read the **Agent** lines exactly as written, and have someone else read the **Customer** lines. Remember, Azure Speech is mapping the speakers, so the **Agent should ALWAYS speak first** to lock in "Guest-1".

---

## 🚗 Scenario 1: Phone Lookup & Towing (Natural Flow)
**Goal:** Show the AI handling a missing policy number gracefully by switching to a phone number lookup, deducing facts (date), and enforcing coverage limits naturally.

**Data Targeted:** Sarah Jenkins (`(555) 014-9921` - Rideshare Add-on only, NO Roadside Assistance)

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Insurance claims. This call is recorded for quality and compliance purposes. My name is Alex, how can I help you today?"

**Customer:** "Hi Alex. I just got into a car accident. My car is pretty messed up."
*(Wait for AI intent to classify as `car_accident` and show the Accident FNOL Knowledge Card. The AI should deduce the accident happened today.)*

**Agent:** "I am so sorry to hear that you've been involved in an incident. I know this can be a stressful time, but I am here to help you get this resolved. Are you currently in a safe location, and is anyone in need of emergency medical assistance?"

**Customer:** "Yeah, we're completely fine. The other guy is fine too. No injuries."
*(Wait for AI suggestion to update. It will likely ask for the policy number.)*

**Agent:** "I'm very glad to hear everyone is safe. Do you happen to have your policy number handy so I can pull up your account?"

**Customer:** "Actually no, I don't have my card on me. Is there another way to find it?"
*(The AI should pivot to ask for the phone number.)*

**Agent:** "Not a problem at all. Can I have the phone number associated with your account?"

**Customer:** "Sure, it's 555 014 9921."
*(Wait for the AI to instantly pull up Sarah Jenkins' profile based on the phone number.)*

**Agent:** "Thank you, Sarah. I see your 2018 Toyota RAV4 here. Is the car drivable, or do you need a tow?"

**Customer:** "It's definitely not drivable. Can you send a tow truck?"
*(Wait for the AI to check coverage. It should notice Sarah has NO 'Roadside Assistance' add-ons.)*

**Agent:** "I can certainly arrange a tow truck for you through our partner Agero. However, because your current policy does not include Roadside Assistance, the towing will be an out-of-pocket expense. Would you still like me to send one?"

**Customer:** "Ah, I see. Yes, please send one anyway. I need to get the car moved."

**Agent:** "Understood, I'll get that arranged. By the way, did you file a police report for this accident?"

**Customer:** "Yes, I did. The incident number is PR-2026-WA-881."
*(The AI should extract and track the police report number.)*

**Agent:** "Perfect, thank you for that detail. I have successfully filed your claim. A dedicated National Sentinel claims adjuster will contact you within 24 hours to discuss the repair process. Is there anything else I can help with?"

**Customer:** "No, that's all. Thank you."

**[⏹ END CALL]**

---

## 🚨 Scenario 2: Fake Policy & Identity Mismatch
**Goal:** Show the system gracefully recovering from a fake policy number, then dealing with a caller whose name doesn't match the primary policyholder, followed by HIPAA compliance during an injury report.

**Data Targeted:** Michael T. Henderson (`NS-88402911` - Caller is his wife, Jessica)

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Insurance claims. This call is being recorded for quality and compliance purposes. My name is Alex, how may I assist you?"

**Customer:** "Hi Alex, someone ran a red light and hit my husband's car. I need to file a claim for him."

**Agent:** "I am so sorry to hear that. Are you in a safe location and does anyone need emergency medical assistance?"

**Customer:** "We are safe now, the ambulance already came and left."

**Agent:** "I'm glad you're safe now. Can I start with the policy number please?"

**Customer:** "Yeah, it's N S 9 9 9 9 9 9 9 9."
*(Profile will not load. The AI will prompt the agent to double-check the number.)*

**Agent:** "I'm sorry, my system isn't bringing anything up for that number. Did you say N S 9 9 9 9 9 9 9 9? Or could we try using the phone number on the account?"

**Customer:** "Oops, that might be his old policy. Let's use his phone number, it's 555 019 8372."
*(Profile loads for Michael T. Henderson.)*

**Agent:** "Thank you. I see the policy here for the 2021 Honda Accord under the name Michael T. Henderson. Since you mentioned it's your husband's car, may I ask who I have the pleasure of speaking with?"

**Customer:** "I'm his wife, Jessica Henderson. I was in the passenger seat when it happened."
*(The AI should notice the mismatch and suggest confirming she has permission, while also noting the injury mention).*

**Agent:** "Thanks for clarifying, Jessica. Does Michael know about the claim, and do you have his permission to file this on his behalf?"

**Customer:** "Yes, he knows. He's actually the one who was injured."
*(The AI HIPAA compliance rule should trigger since injury/medical info is being discussed).*

**Agent:** "I understand. Please be advised that since we are discussing medical information, it is protected under HIPAA. To stick to what's strictly necessary for the claim, what type of injuries did Michael sustain, and was he transported to a hospital?"

**Customer:** "He had some severe whiplash and was taken to Columbus General Hospital for X-rays."
*(The AI captures these details and will move toward wrapping up).*

**Agent:** "Thank you for providing that. I have entered the medical and accident details into our system. Your claim has been filed, and an adjuster will reach out within 24 hours to discuss the next steps for both the vehicle and the medical bills. Is there anything else I can assist you with today?"

**Customer:** "No, that's everything. We'll wait for the adjuster."

**[⏹ END CALL]**

---

## 🪟 Scenario 3: Glass Claim & Zero Deductible Info
**Goal:** Show the AI perfectly extracting facts for a specific type of claim (Glass), using the Knowledge Base to determine replacement criteria, and informing the caller about their $0 deductible and ADAS calibration.

**Data Targeted:** David Alvez (`NS-77299104` - Has Full Glass Coverage $0 Deductible)

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Insurance claims. This call is being recorded for quality and compliance purposes. My name is Alex, how may I assist you?"

**Customer:** "Hi Alex, I was driving on the highway and a massive rock flew up and hit my windshield. It created a huge crack."

**Agent:** "I am so sorry to hear about that. First, are you in a safe location and is everyone okay?"

**Customer:** "Yeah, it just startled me. I'm safely pulled over now."

**Agent:** "I'm glad you're safe. Do you have your policy number handy?"

**Customer:** "Yes, it is N S 7 7 2 9 9 1 0 4."
*(Profile loads for David Alvez. AI verifies the account and policy).*

**Agent:** "Thank you, David. I have your policy open for the 2023 Ford F-150. Based on the damage, would you say the crack in the windshield is larger than a standard dollar bill?"

**Customer:** "Oh yeah, it's easily a foot long. It stretches right across my line of sight while driving."
*(AI uses Knowledge Base rules: larger than a dollar bill + line of sight = Replacement required).*

**Agent:** "Because the crack is larger than a dollar bill and in your line of sight, we will need to authorize a full windshield replacement rather than a repair. The good news is, your policy includes Full Glass Coverage, so your deductible for this replacement will be completely waived—it's zero dollars out of pocket for you."

**Customer:** "Wow, that's a relief. How do we get it fixed?"
*(AI uses Knowledge Base to mention Safelite and ADAS recalibration).*

**Agent:** "We partner exclusively with Safelite AutoGlass for mobile replacements. They will come to you. And since your Ford F-150 likely has cameras and sensors on the windshield, Safelite will also perform the necessary ADAS recalibration during the appointment, which is fully covered by your claim."

**Customer:** "That's perfect. Do I need to do anything else right now?"

**Agent:** "Nope, I have filed the glass claim for you. A representative from Safelite will contact you shortly to schedule the mobile replacement. Is there anything else I can help you with today?"

**Customer:** "No, that's it. Thanks a lot, Alex."

**[⏹ END CALL]**
