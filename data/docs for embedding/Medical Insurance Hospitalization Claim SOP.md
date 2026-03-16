# **Standard Operating Procedure: Medical Insurance Hospitalization Claim**

**Document ID:** SOP-MED-NS-001  
**Last Updated:** March 1, 2026  
**Department:** Claims Customer Service  
**Applies To:** Tier 1 Medical Claims Agents  
**System Role:** National Sentinel Insurance Source of Truth for Medical Claim Workflows

## **1\. Purpose and Scope**

This Standard Operating Procedure (SOP) serves as the primary source of truth for handling inbound medical insurance hospitalization claims at National Sentinel Insurance. Agents and AI intake assistants must follow these workflows to ensure timely and accurate claim processing while maintaining HIPAA compliance.

## **2\. Initial Call Handling and HIPAA Compliance**

When a National Sentinel medical policyholder calls to report a hospitalization or planned admission, agents must prioritize empathy and privacy compliance.

### **2.1 Mandatory Call Opening (Compliance Script)**

* **Greeting:** "Thank you for calling National Sentinel Insurance Medical Claims. My name is \[Agent Name\]. This call is recorded for quality and compliance purposes."  
* **HIPAA Disclosure:** "Before we proceed, I want to assure you that all medical and personal health information discussed on this call is protected under HIPAA regulations."  
* **Safety \& Empathy:** "I understand this may be a stressful time. I'm here to help you through the claim process as smoothly as possible."

## **3\. Policyholder Verification**

Before discussing medical details, the caller must be verified to prevent unauthorized disclosure of Protected Health Information (PHI).

* Ask for the **Policy Number** (starts with MED-) or the **Primary Phone Number**.  
* Verify the caller is the policyholder or an authorized representative.  
* Confirm two (2) of the following data points:  
  1. Full legal name of the insured  
  2. Date of birth  
  3. Address on file

## **4\. Hospitalization Claim Intake**

Once verified, gather the following information about the hospitalization:

### **4.1 Hospital & Admission Details**

* **Hospital Name:** Full name of the admitting facility.  
* **Date of Admission:** When the policyholder was or will be admitted.  
* **Diagnosis / Reason for Admission:** The medical condition or procedure.  
* **Treating Physician:** Name of the primary treating doctor, if known.

### **4.2 In-Network vs. Out-of-Network Determination**

* Check the policyholder's `networkHospitals` list to determine if the facility is in-network.  
* **In-Network:** The policyholder is eligible for direct billing (in-network benefits). The hospital's insurance desk will submit a pre-authorization request to National Sentinel's claims department.  
* **Out-of-Network:** The policyholder pays the hospital bill upfront and submits documentation for reimbursement.

### **4.3 Pre-Authorization Process (In-Network Only)**

* Pre-authorization must be obtained within 24 hours of planned admission, or within 48 hours for emergency admissions.  
* Approval is typically communicated within 2–4 hours for planned admissions and within 1 hour for emergencies.  
* Inform the caller that the hospital's insurance desk handles the pre-authorization paperwork.  
* The policyholder only pays the copay percentage and amounts exceeding sub-limits (room rent cap, ICU cap).

### **4.4 Reimbursement Process (Out-of-Network)**

* Required documents for reimbursement:  
  * Original hospital bills (itemized)  
  * Discharge summary  
  * Diagnostic reports and lab results  
  * Doctor's prescription  
  * Pharmacy bills  
  * Completed claim form (will be emailed or mailed to the policyholder)  
* All documents must be submitted within 30 days of discharge.  
* Reimbursement is processed within 45 days of receiving complete documentation.

## **5\. Sub-Limits and Cost-Sharing**

* **Room Rent Cap:** Charges above the daily room rent limit are the policyholder's responsibility.  
* **ICU Cap:** ICU charges above the daily ICU limit are the policyholder's responsibility.  
* **Copay:** The policyholder pays the copay percentage of the eligible claim amount.  
* **Deductible:** The annual deductible must be met before coverage applies.  
* Inform the caller of their specific sub-limit amounts from their policy data.

## **6\. Closing the Call**

* Confirm that a claims coordinator will contact the policyholder within 24 hours to assist with next steps.  
* Provide the claim reference number.  
* Ask: "Is there anything else I can assist you with today?"  
* Close with: "Thank you for being a National Sentinel policyholder. We wish you a speedy recovery."
