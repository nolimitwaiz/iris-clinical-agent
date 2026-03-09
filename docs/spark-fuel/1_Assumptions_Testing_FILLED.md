# ASSUMPTIONS TESTING — Worksheet 1

**Founder Name:** Waiz Khan
**Venture Name:** Iris Health
**Venture Description:** Iris is an AI powered heart failure care agent that provides 24/7 patient monitoring and medication optimization. Unlike chatbots that generate medical advice from language models, Iris uses a tool first architecture where every clinical decision comes from deterministic Python tools following AHA/ACC guidelines. The language model only extracts patient information and communicates tool outputs in warm, plain language. A Response Validator blocks any hallucinated clinical content before it reaches the patient. Iris monitors weight trends, optimizes GDMT medications, detects barriers to adherence (cost, access, literacy), predicts decompensation before it happens, and escalates to clinicians when needed. It runs entirely locally with no paid APIs, making it accessible to safety net hospitals and underserved populations.

---

## 1. What is the problem you are solving?

Heart failure patients experience preventable hospitalizations because they lack continuous clinical monitoring between visits. The average HF patient sees their cardiologist every 3 to 6 months, but decompensation can develop in days. Weight gain of 2+ lbs over 5 days signals fluid retention that, if caught early, requires only a diuretic adjustment — but if missed, leads to an ER visit costing $15,000 to $25,000.

**How will you test this assumption?:**
Interview 15+ heart failure patients and 10+ HF clinic nurses/NPs about gaps between visits. Review published readmission data (CMS Hospital Readmissions Reduction Program penalties). Track how many patients in our pilot report issues that went unaddressed between appointments.

**What resources do you need to test this assumption?:**
Access to HF patients (through Hopkins cardiology clinics or patient advocacy groups), IRB approval for patient interviews, CMS readmission data (publicly available), and time to conduct interviews.

**What milestones will you need to have reached?:**
Customer discovery interviews complete (10+ patients, 5+ clinicians). Working prototype that can demonstrate the monitoring gap being filled.

---

## 2. What causes this problem to persist?

Three compounding factors: (1) Clinician shortage — there are not enough cardiologists to provide continuous monitoring for 6.7M HF patients in the US. (2) Existing remote monitoring tools (like weight scales connected to portals) generate alerts but do not provide clinical reasoning or patient communication — they add work to already overwhelmed nurses. (3) Patients with low health literacy, financial barriers, or transportation issues cannot self manage effectively even with education.

**How will you test this assumption?:**
Interview HF clinic staff about alert fatigue and workload from existing RPM tools. Survey patients about barriers to self management. Analyze published literature on RPM alert fatigue and HF self care gaps.

**What resources do you need to test this assumption?:**
Access to clinic staff at 2 to 3 HF programs, patient survey distribution channel, literature review time.

**What milestones will you need to have reached?:**
Complete customer discovery with both clinician and patient stakeholders. Have a clear understanding of current RPM workflows.

---

## 3. How are you going to solve that problem?

Iris acts as a 24/7 clinical care agent that sits between the patient and their care team. Patients check in daily via voice or text. Iris runs a fixed 6 tool pipeline every time: Adherence Monitor, Trajectory Analyzer, GDMT Engine, Safety Checker, Barrier Planner, and Escalation Manager. Each tool returns a structured Action Packet with the decision, guideline citation, confidence level, and monitoring requirements. The language model never makes clinical decisions — it only communicates what the tools determine. This means Iris can catch a 2 lb weight gain on day 3, recommend a diuretic increase per AHA guidelines, check that the patient can afford the change and get to the pharmacy, and escalate to the care team if needed — all before the patient would have their next appointment.

**How will you test this assumption?:**
Deploy the working prototype with 5 to 10 test patients (simulated or real with IRB approval). Measure whether Iris correctly identifies decompensation signals, makes guideline concordant recommendations, and successfully communicates with patients. Compare Iris recommendations against cardiologist review (concordance study).

**What resources do you need to test this assumption?:**
Working prototype (built), test patient data, a cardiologist willing to review Iris recommendations for concordance, and patient testers for usability.

**What milestones will you need to have reached?:**
Functional MVP with all 6 pipeline tools working. At least 5 test patient profiles with realistic clinical scenarios. Cardiologist advisor relationship established.

---

## 4. Who is your customer?

Our primary customer is the heart failure clinic (the institution), specifically the medical director or nurse manager who oversees HF patient panels. They are the economic buyer who experiences the pain of readmission penalties, staffing shortages, and RPM alert fatigue. The end user is the HF patient who interacts with Iris daily, and the clinician who receives escalation alerts and reviews Action Packets.

**How will you test this assumption?:**
Interview HF clinic directors and nurse managers at 3+ institutions about their willingness to adopt an AI care agent. Ask about budget authority, procurement process, and what outcomes would justify the investment.

**What resources do you need to test this assumption?:**
Connections to HF clinic leadership (Hopkins network, ACC conferences), prepared interview scripts, understanding of hospital procurement cycles.

**What milestones will you need to have reached?:**
Customer personas defined. At least 3 interviews with clinic decision makers completed.

---

## 5. What value does your solution bring to that customer?

For the clinic: reduced 30 day readmissions (directly tied to CMS penalty avoidance worth $500K+ per hospital annually), extended clinician capacity (one Iris instance can monitor hundreds of patients continuously), and reduced RPM alert fatigue (Iris triages and only escalates when clinically appropriate). For the patient: feeling heard and monitored between visits, plain language explanations of their care, barrier aware recommendations that account for their real life constraints.

**How will you test this assumption?:**
Pilot with 1 to 2 HF clinics measuring: readmission rate change, clinician time saved per patient, patient satisfaction scores (validated HF questionnaire), and escalation accuracy (true positive rate).

**What resources do you need to test this assumption?:**
Pilot site agreements, baseline readmission data, validated patient satisfaction instruments, 3 to 6 month pilot duration.

**What milestones will you need to have reached?:**
MVP deployed to pilot site. Data collection infrastructure in place. IRB approval if using real patients.

---

## 6. How will you make money?

SaaS subscription model: clinics pay per patient per month for Iris monitoring. Pricing based on value delivered — if Iris prevents even 1 readmission per 20 patients monitored, the clinic saves $15K to $25K while paying a fraction of that in subscription fees. Target price: $50 to $150 per patient per month depending on acuity tier and panel size.

**How will you test this assumption?:**
Present pricing models to 5+ HF clinic administrators and gauge willingness to pay. Compare against existing RPM service pricing (typically $100 to $200/patient/month for nurse led RPM). Survey payers (Medicare Advantage plans) about reimbursement for AI augmented RPM.

**What resources do you need to test this assumption?:**
Pricing model document, access to clinic administrators, knowledge of CPT/RPM reimbursement codes (99457, 99458).

**What milestones will you need to have reached?:**
Business model defined. At least 3 pricing conversations with potential customers completed.

---

## 7. How will you acquire new customers?

Three channels: (1) Clinical evidence — publish pilot results showing readmission reduction and present at ACC/HFSA conferences where HF clinic directors attend. (2) Hopkins network — leverage Johns Hopkins clinical relationships and Spark/Fuel advisor connections for warm introductions to health system innovation officers. (3) CMS penalty pressure — target hospitals with high HF readmission penalty rates (publicly available data) with direct outreach showing ROI calculations specific to their penalty exposure.

**How will you test this assumption?:**
Test channel 2 first (lowest cost): reach out to 5 Hopkins affiliated HF clinics through advisor introductions. Track conversion from introduction to demo to pilot interest. Test channel 3 by identifying 20 hospitals with highest CMS penalties and sending targeted outreach.

**What resources do you need to test this assumption?:**
Hopkins advisor network, CMS Hospital Compare data, outreach templates, demo ready prototype.

**What milestones will you need to have reached?:**
Polished demo. At least 1 pilot site secured. Initial clinical evidence or concordance study results.

---

## 8. What are the most important opportunities you need to pursue to reach your goals?

(1) ARPA-H ADVOCATE funding — if encouraged for full proposal (deadline April 1, 2026), this provides non dilutive capital and credibility. (2) FDA regulatory pathway clarity — determining whether Iris qualifies as a Clinical Decision Support tool (exempt from 510(k)) or requires device clearance. (3) Strategic partnership with a major health system for pilot deployment and clinical validation.

**How will you test this assumption?:**
Submit ARPA-H full proposal and track outcome. Consult with FDA regulatory experts (Hopkins has Regulatory Science program) to classify Iris. Pitch to 3+ health system innovation offices.

**What resources do you need to test this assumption?:**
ARPA-H proposal writing support, FDA regulatory consultant, health system innovation officer contacts.

**What milestones will you need to have reached?:**
ARPA-H solution summary submitted (done). Prototype functional (done). Regulatory pre submission meeting scheduled.

---

## 9. What are the most notable threats you foresee?

(1) Regulatory uncertainty — if FDA classifies Iris as a medical device requiring 510(k), timeline extends 12 to 18 months and costs increase significantly. (2) Clinician trust — physicians may resist delegating monitoring to an AI system, especially one not developed by an established health IT company. (3) EHR integration barriers — health systems may require Epic/Cerner integration before adoption, which adds development time and cost. (4) Competitor response — large RPM companies (Biofourmis, Current Health) could add AI features to existing platforms.

**How will you test this assumption?:**
Regulatory: consult with FDA and health law experts early. Trust: conduct clinician interviews and build concordance evidence. EHR: build FHIR R4 export capability (already done) as a bridge. Competition: monitor competitor product launches and maintain differentiation through the tool first architecture.

**What resources do you need to test this assumption?:**
FDA regulatory consultant, clinician advisory board, FHIR integration development time, competitive intelligence monitoring.

**What milestones will you need to have reached?:**
Regulatory strategy defined. Clinical advisory board of 3+ cardiologists assembled. FHIR export functional (done).

---

## 10. What work have you done to validate your idea thus far?

- Built a fully functional prototype demonstrating the complete architecture: 6 tool deterministic pipeline, Gemini LLM for extraction/communication only, Response Validator that blocks hallucinations, voice interface with real time conversation, clinician dashboard with Action Packets
- Submitted ARPA-H ADVOCATE solution summaries for both TA1 (Iris Core) and TA2 (Iris Sentinel) — received confirmation
- Created 5 realistic test patient profiles covering stable, decompensating, and edge case scenarios
- Implemented 97 automated tests verifying guideline concordance
- Built FHIR R4 data export demonstrating EHR integration readiness
- Developed caregiver/family view showing how Iris bridges the care team communication gap

---

## 11. How will the outcome of these tests impact your next steps?

If the core problem assumption is validated (patients lack continuous monitoring and this leads to preventable hospitalizations), we proceed with clinical pilot planning. If clinicians express skepticism about AI recommendations, we double down on the concordance study to build trust with evidence. If the pricing assumption fails (clinics won't pay $50 to $150/patient/month), we pivot to a payer focused model (selling to Medicare Advantage plans who bear the readmission cost). If ARPA-H does not fund, we pursue NSF I-Corps, SBIR, or angel investment to fund the pilot. If FDA requires 510(k), we engage a regulatory consultant and plan for a longer timeline while continuing the exempt CDS features.

---

## 12. What promise are you making to your customers? What do you think will resonate with them?

**To clinics:** "Iris extends your care team to 24/7 without adding headcount. Every recommendation follows your guidelines, every escalation is clinically justified, and you stay in control."

**To patients:** "Iris is here for you between visits. You can talk to Iris anytime about how you are feeling, and Iris will make sure your care team knows what matters."

What will resonate: For clinics, the combination of readmission reduction (financial) and staff relief (operational). For patients, the feeling of being heard and monitored — not just given a scale and told to call if something is wrong.
