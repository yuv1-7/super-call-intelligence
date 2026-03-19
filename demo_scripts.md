# 📞 Super Call Intelligence: Live Demo Scripts

These scripts are designed to showcase the full power of your application. Read the **Agent** lines exactly as written, and have someone else read the **Customer** lines. Remember, Azure Speech is mapping the speakers, so the **Agent should ALWAYS speak first** to lock in "Guest-1".

---

## 🚘 Scenario 1: Vehicle Vandalism (Comprehensive Cover)
**Goal:** Show the AI perfectly extracting facts for a malicious damage claim, using the Knowledge Base to inform the caller that a police report is strictly required, and confirming Comprehensive coverage applies.

**Data Targeted:** Michael T. Henderson (`(555) 019-8372` or `CAR-100001` - Has Comprehensive Cover)

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Insurance claims. This call is being recorded for quality and compliance purposes. My name is Alex, how may I assist you?"

**Customer:** "Hi Alex, I came out to my car this morning and someone smashed my window and keyed the side of my door. I need to file a claim."

**Agent:** "I am so sorry to hear that your vehicle was vandalized. Are you in a safe location?"

**Customer:** "Yes, I'm just parked in my driveway at home. Nothing was stolen, it's just the damage from the vandalism."

**Agent:** "I'm glad you're safe. Let's get this sorted out. Can I have your phone number to pull up your account?"

**Customer:** "Sure, it is 555 019 8372."
*(Profile loads for Michael T. Henderson. AI verifies the account and policy).*

**Agent:** "Thank you, Michael. I see your policy for the 2021 Honda Accord. Because this is an incident of vandalism, it falls under your Comprehensive coverage, which you do have active on this policy. However, before we can formally process the claim, have you filed a police report?"

**Customer:** "No, I haven't yet. Do I really need to do that?"
*(AI uses Knowledge Base rules: Vehicle Vandalism Claims Procedure requires a police report).*

**Agent:** "Yes, according to our vandalism claims procedure, a formal police report is strictly required to process this type of claim. Please contact your local non-emergency police line to file a report. Once you have the incident number, you can call us back with it."

**Customer:** "Okay, that makes sense. I'll get that done today."

**Agent:** "Perfect. I have opened the initial claim on my end. Call us back anytime with that report number. Is there anything else I can help you with today?"

**Customer:** "No, that's it. Thanks."

**[⏹ END CALL]**

---

## 🚫 Scenario 2: At-Fault Accident without Roadside (Coverage Denial)
**Goal:** Show the AI handling coverage checks properly by noticing the user only has Third Party coverage and lacks Roadside Assistance, enforcing out-of-pocket rules politely.

**Data Targeted:** Sarah Jenkins (`(555) 014-9921` or `CAR-100002` - Third Party Only, NO Roadside)

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Insurance. This call is recorded for quality purposes. My name is Alex, how can I help?"

**Customer:** "Hi Alex... I just messed up. I accidentally backed my car into a concrete pole in a parking garage. My bumper is completely destroyed."

**Agent:** "I am so sorry to hear about the accident. Are you in a safe location, and do you need any medical assistance?"

**Customer:** "No, I'm totally fine. Just shaken up. The car is undrivable though. Can you send a tow truck?"

**Agent:** "I am glad you are safe. Let me look up your policy to see your coverage. What is the policy number?"

**Customer:** "It's C A R 1 0 0 0 0 2."
*(Profile loads for Sarah Jenkins).*

**Agent:** "Thank you, Sarah. I have your 2018 Toyota RAV4 pulled up. I need to inform you that your current policy is 'Third Party Only'. This means we cover damage you cause to others, but we do not cover repairs to your own vehicle in an at-fault accident. Also, I don't see 'Roadside Assistance' on your policy."

**Customer:** "Oh no. So the tow truck isn't covered?"
*(AI references Towing and Rental Vehicle Coverage Policy).*

**Agent:** "I can still arrange a tow truck for you through our partner Agero to get your car out of the parking garage safely. However, the towing fee will be an out-of-pocket expense for you. Would you like me to dispatch them?"

**Customer:** "Wow, okay. Yes, please send them anyway, I have to move the car."

**Agent:** "I understand, and I'll get that arranged right away. Is there anything else I can assist with today?"

**Customer:** "No, just the tow truck please."

**[⏹ END CALL]**

---

## 🌟 Scenario 3: Major Collision with Full Add-ons (Premium Cover)
**Goal:** Demonstrate the AI rewarding a premium customer by automatically applying Zero Depreciation, Roadside, and Rental Reimbursement add-ons following a rear-end collision.

**Data Targeted:** David Alvez (`(555) 017-4433` or `CAR-100003` - Comprehensive + Collision, Full Add-ons)

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Insurance claims. This call is being recorded for quality and compliance purposes. My name is Alex, how may I assist you?"

**Customer:** "Hi Alex. I was just rear-ended perfectly on the highway. My truck is completely smashed in the back."

**Agent:** "I’m very sorry to hear that. First and foremost, are you okay? Do you need an ambulance?"

**Customer:** "No, I think I'm okay. Just a bit of neck pain, but I don't need an ambulance right now. We are pulled over safely."

**Agent:** "Okay, please make sure to seek medical attention if that neck pain persists. Can I get your phone number to find your policy?"

**Customer:** "It's 555 017 4433."
*(Profile loads for David Alvez).*

**Agent:** "Thank you, David. I see your policy for the 2023 Ford F-150. Given the damage, is the truck drivable, or do you need a tow and a rental vehicle?"

**Customer:** "Definitely not drivable. I'll need a tow, and how does a rental work?"
*(AI references Auto Policy Master Coverage Summary & checks his Add-ons).*

**Agent:** "Not a problem. Since you have Roadside Assistance and Rental Reimbursement as active add-ons, I will dispatch a free tow truck to your location right away. We will also arrange a rental vehicle for you through Enterprise for the duration of your repairs, fully covered up to your policy limit."

**Customer:** "That is amazing to hear."

**Agent:** "I also want to assure you that your Zero Depreciation add-on is active. This means your truck will be repaired with brand new parts without any deduction for wear and tear. I have filed the claim, and an adjuster will call you soon. Can I help with anything else?"

**Customer:** "You've been incredibly helpful, thank you."

**[⏹ END CALL]**

---

## ⏱️ Scenario 4: Pre-Existing Condition Limitation (Medical)
**Goal:** Test the AI's ability to cross-reference medical claims with pre-existing waiting periods, correctly warning the user about a potential denial.

**Data Targeted:** Thomas R. Nguyen (`(555) 066-9875` or `MED-300002` - Active waiting period for Diabetes)

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Health. This call is being recorded for quality and compliance purposes. My name is Alex, how may I assist you?"

**Customer:** "Hello Alex, I was just admitted to the Mayo Clinic for a severe spike in my blood sugar related to my Type 2 Diabetes. I need to start a hospitalization claim."

**Agent:** "I am sorry to hear you're in the hospital. I hope you're receiving the care you need. Let me look up your policy. Could I have your phone number?"

**Customer:** "It's 555 066 9875."
*(Profile loads for Thomas R. Nguyen).*

**Agent:** "Thank you, Thomas. I see your Family Health Plan. You mentioned you were admitted to the Mayo Clinic for a complication related to Type 2 Diabetes, correct?"

**Customer:** "Yes, that's exactly right."
*(AI cross-references 'Pre-Existing Waiting' status which is Active for Diabetes).*

**Agent:** "I need to transparently inform you that your policy has an active waiting period for pre-existing conditions, specifically listing Type 2 Diabetes, with two years remaining. Based on our guidelines, claims directly related to this condition during the waiting period may be subject to review or denial."

**Customer:** "Oh, what? I completely forgot about that waiting period. What happens now?"

**Agent:** "I will still proceed with filing the claim and notify our medical review board. The hospital can continue your treatment, but please be aware that you may be ultimately responsible for the bill if the claim is denied. Would you like me to submit the pre-authorization request for the review board?"

**Customer:** "Yes, please submit it and let's hope for the best."

**Agent:** "I've submitted the request. The review team will contact you within 48 hours with a decision. Is there anything else I can help with?"

**Customer:** "No, I'll wait to hear back."

**[⏹ END CALL]**

---

## 🏥 Scenario 5: Day-Care Procedure Approval (Medical)
**Goal:** Show the AI validating a day-care procedure against the policy limitations and explaining the financial breakdown (deductible & copay).

**Data Targeted:** Karen L. Mitchell (`(555) 055-3214` or `MED-300001` - Day-Care Active & Passed Waiting Period)

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Health. This call is being recorded for quality and compliance purposes. My name is Alex, how may I assist you?"

**Customer:** "Hi Alex, I am calling to see if my upcoming cataract surgery is covered. I won't be staying overnight at the hospital."

**Agent:** "I can certainly help you check the coverage for your surgery. Can I have your policy number?"

**Customer:** "Yes, it's M E D 3 0 0 0 0 1."
*(Profile loads for Karen L. Mitchell).*

**Agent:** "Thank you, Karen. I see your Individual Health policy. Because cataract surgery does not require an overnight stay, it is classified as a 'Day-Care Procedure'. The good news is that you specifically hold the Day-Care Procedures add-on, and your waiting periods have fully expired."

**Customer:** "Oh wonderful! So it's fully covered?"
*(AI checks financial sub-sections).*

**Agent:** "Yes, the procedure is covered under your plan. Keep in mind that you do have a 10 percent copay, and any costs will first be applied against your $2,500 annual deductible. We will coordinate directly with the surgical center for the billing."

**Customer:** "That sounds perfect. Do I need to send you the doctor's notes?"

**Agent:** "Yes, please have your doctor's office submit the pre-authorization form along with the medical notes at least 48 hours before the surgery. Is there anything else I can assist you with?"

**Customer:** "No, that answers all my questions. Thank you, Alex."

**[⏹ END CALL]**

---

## 🕊️ Scenario 6: Smooth Life Insurance Death Claim
**Goal:** Show the AI handling a sensitive Life Insurance claim smoothly, verifying beneficiaries, and confirming that the contestability period has safely expired.

**Data Targeted:** Robert J. Whitfield (`LIFE-200001` - Caller is Margaret (Spouse))

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Life. This call is being recorded for quality and compliance purposes. My name is Alex, how may I assist you?"

**Customer:** "Hi Alex... I am calling because my husband, Robert Whitfield, passed away yesterday. I need to start a life insurance claim."

**Agent:** "Please accept my deepest condolences for your loss, ma'am. I am so sorry you are going through this. I am here to help make this process as easy as possible for you. Can you provide Robert's policy number or phone number?"

**Customer:** "His phone number was 555 022 6891."
*(Profile loads for Robert J. Whitfield).*

**Agent:** "Thank you. I have the policy pulled up. For security purposes, may I ask your name and relationship to Robert?"

**Customer:** "My name is Margaret Whitfield, I'm his wife."
*(AI verifies Margaret is a beneficiary (60%) and notes Contestability is Expired).*

**Agent:** "Thank you, Margaret. I see you listed as the primary beneficiary, along with your son James. Since Robert's policy has been active for over ten years, the contestability period has completely expired, which will make this a very straightforward process for you."

**Customer:** "Okay, what do I need to send you?"
*(AI references Life Insurance Death Claim Filing Procedures).*

**Agent:** "We will simply need a certified copy of the death certificate and a completed claim form from both you and James. You can upload these documents directly through our secure portal. Once received, the funds are typically disbursed within 5 to 7 business days. Would you like me to email the secure upload link to you now?"

**Customer:** "Yes, please email that over. Thank you."

**Agent:** "The email has been sent. Please take all the time you need, and don't hesitate to call us back if you have any questions. We are here for you. Is there anything else you need right now?"

**Customer:** "No, that's all. Thank you for your help."

**[⏹ END CALL]**

---

## 🚨 Scenario 7: Contestability Period & Red Flags (Life/Fraud)
**Goal:** Test the AI's compliance rules by presenting a sudden death claim on a very brand-new policy. The AI must trigger the Contestability/Fraud flag subtly and professionally.

**Data Targeted:** Marcus A. Rivera (`LIFE-200003` - Caller is Elena (Spouse) - Policy is brand new)

**[🎤 START CALL]**

**Agent:** "Thank you for calling National Sentinel Life. This call is being recorded for quality and compliance purposes. My name is Alex, how may I assist you?"

**Customer:** "Hi Alex, I need to report a fatal accident. My husband Marcus died under strange circumstances while on vacation. I need to claim his life insurance immediately."

**Agent:** "I am incredibly sorry for your sudden loss. This must be a very difficult time. Let's get the process started. Can I have his policy number?"

**Customer:** "It is L I F E 2 0 0 0 0 3."
*(Profile loads for Marcus A. Rivera).*

**Agent:** "Thank you. Am I speaking with his wife, Elena?"

**Customer:** "Yes, that's me."
*(AI notices ContestabilityExpired is False (started late 2025). AI also references Fraud Indicators regarding sudden death on recent policies).*

**Agent:** "Thank you, Elena. I have located Marcus's Accidental Death and Dismemberment policy. Because this policy was opened very recently, within the last two years, it is currently in its standard contestability period. This means the claim will require a routine, but detailed, administrative review process by our specialized death claims team."

**Customer:** "A review? But he died in an accident. Give me the money, I need it right now for the funeral."
*(AI references Call Center Compliance Guidelines: remain calm, do not accuse, explain the process).*

**Agent:** "I truly understand the financial stress this puts on you, Elena. However, standard compliance regulations legally require us to review all claims made within the contestability period. We will need a certified death certificate, a full police report regarding the accident, and the coroner's report before any funds can be disbursed."

**Customer:** "Fine. I will get those documents. This is ridiculous."

**Agent:** "I appreciate your cooperation during this difficult process. A specialized claims examiner will be assigned to your case and will reach out to you within 24 hours to guide you through the next steps. Is there anything else I can assist you with?"

**Customer:** "No."

**[⏹ END CALL]**
