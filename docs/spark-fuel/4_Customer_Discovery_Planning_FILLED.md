# CUSTOMER DISCOVERY PLANNING — Worksheet 4.2

**Founder Name:** Waiz Khan
**Venture Name:** Iris Health
**Venture Description:** Iris is an AI powered heart failure care agent providing 24/7 monitoring and medication optimization. Every clinical decision comes from deterministic Python tools following AHA/ACC guidelines. The language model only extracts patient info and communicates tool outputs. Iris monitors weight trends, optimizes GDMT medications, detects adherence barriers, predicts decompensation, and escalates to clinicians. Voice first interface, clinician dashboard with Action Packets, runs locally with no paid APIs.

---

## 1. Key stakeholder types that your idea affects

1. **Heart failure patients** — the end users who interact with Iris daily
2. **Heart failure clinic nurse practitioners / nurses** — front line care coordinators managing HF patient panels
3. **Cardiologists / HF program directors** — clinical leaders who set care protocols and evaluate new tools
4. **Hospital administrators / CMOs** — economic decision makers concerned with readmission penalties and operational costs
5. **Health system innovation / digital health officers** — technology evaluators who vet and procure new solutions
6. **Medicare Advantage plan medical directors** — payers who bear financial risk for HF hospitalizations
7. **Pharmacists** — involved in medication reconciliation, cost optimization, and formulary management
8. **Caregivers / family members** — support system for HF patients, often the ones noticing symptom changes

---

## 2. Critical assumptions that can be validated by interviews, and which stakeholders

| Assumption | Stakeholders to Interview |
|---|---|
| Patients lack continuous monitoring between visits and this leads to preventable hospitalizations | HF patients, HF nurses, cardiologists |
| Existing RPM tools create alert fatigue and add work without providing clinical reasoning | HF nurses, cardiologists, digital health officers |
| Clinicians would trust an AI system that provides transparent, guideline cited reasoning | Cardiologists, HF program directors, nurses |
| Clinics would pay $50 to $150/patient/month for automated monitoring | Hospital administrators, CMOs, digital health officers |
| Patients (including elderly, low literacy) would engage with a voice first AI agent | HF patients, caregivers |
| Barrier aware planning (cost, access, literacy) meaningfully improves adherence | HF patients, pharmacists, nurses |
| Medicare Advantage plans would contract with Iris to reduce their readmission costs | MA plan medical directors |

---

## 3. Hypotheses for each assumption

**H1 (Monitoring gap):** If heart failure patients have access to a 24/7 AI care agent that monitors their weight, symptoms, and medication adherence between clinic visits, they will experience fewer unplanned hospitalizations, because early detection of fluid retention and medication issues enables intervention before acute decompensation.

**H2 (Alert fatigue):** If we provide clinicians with AI generated Action Packets that include clinical reasoning, guideline citations, and confidence levels instead of raw vital sign alerts, they will experience less alert fatigue and act on more alerts, because the information is pre processed and clinically contextualized.

**H3 (Clinician trust):** If we show cardiologists that every Iris recommendation comes from deterministic guideline based tools (not language model generation) with full transparency into the reasoning chain, they will trust the system enough to integrate it into their workflow, because the tool first architecture eliminates the hallucination risk that makes clinicians skeptical of AI.

**H4 (Willingness to pay):** If heart failure clinics are shown that Iris reduces 30 day readmissions by even 10 to 15% at $75/patient/month, they will adopt it, because the ROI from CMS penalty avoidance and reduced hospitalization costs far exceeds the subscription fee.

**H5 (Patient engagement):** If elderly HF patients can check in with Iris via simple voice conversation rather than typing or navigating an app, they will engage daily, because voice interaction removes the technology literacy barrier that prevents adoption of existing patient portals and RPM apps.

**H6 (Barrier awareness):** If Iris accounts for a patient's insurance tier, pharmacy distance, and health literacy when recommending medication changes, patients will fill prescriptions at higher rates, because the recommendation is feasible for their actual life circumstances rather than just clinically ideal.

**H7 (Payer interest):** If Medicare Advantage plans see that Iris can reduce HF readmissions across their covered population with transparent, auditable clinical reasoning, they will contract directly with Iris, because each prevented readmission saves them $15,000 to $25,000 in direct costs.

---

## 3. Open ended interview questions (5+ per hypothesis)

### For HF Patients (H1, H5, H6):
1. Walk me through what happens between your cardiology appointments. How do you monitor your health at home?
2. Tell me about a time you had to go to the emergency room or hospital for your heart failure. Looking back, were there warning signs in the days before?
3. How do you currently keep track of your weight, blood pressure, and medications? What is hardest about that?
4. If you could talk to someone about your heart health anytime you wanted, what would you want to ask or share?
5. What has made it difficult for you to take your medications as prescribed? (probe: cost, side effects, forgetting, pharmacy access)
6. How comfortable are you talking to a voice assistant like Siri or Alexa? Would you be willing to check in daily by talking instead of typing?

### For HF Nurses / NPs (H1, H2):
1. Describe your typical day managing HF patients. How many patients are on your panel?
2. How do you currently get information about your patients between visits? What alerts or reports do you review?
3. When you receive a remote monitoring alert, what do you do with it? How often do alerts require action vs turn out to be nothing?
4. What information would you need alongside an alert to make it immediately actionable?
5. What is the biggest barrier to preventing readmissions in your patient population?
6. How much time do you spend on tasks that you feel could be automated without compromising patient safety?

### For Cardiologists / HF Program Directors (H2, H3):
1. What is your experience with AI tools in clinical practice? What has worked and what has not?
2. If an AI system recommended a diuretic dose increase for one of your patients, what would you need to see before you felt comfortable with that recommendation?
3. How important is it to you to understand why an AI made a particular recommendation vs just seeing the recommendation itself?
4. What would make you trust an AI monitoring system enough to let it handle routine medication adjustments with clinician oversight?
5. If you could redesign how your clinic monitors HF patients between visits, what would it look like?

### For Hospital Administrators / CMOs (H4):
1. How does your organization currently manage CMS readmission penalties for heart failure? What strategies have you tried?
2. What is your annual spend on remote patient monitoring programs? How do you measure their ROI?
3. What would a new digital health tool need to demonstrate before your organization would adopt it?
4. How does your procurement process work for clinical software? Who needs to approve it and how long does it typically take?
5. If a solution could demonstrate a 10 to 15% reduction in HF readmissions, what would that be worth to your organization?

### For MA Plan Medical Directors (H7):
1. How does your plan currently manage high risk heart failure members?
2. What is your average cost per HF hospitalization? How many are you seeing annually?
3. Would you consider contracting with a third party AI monitoring platform if it demonstrated readmission reduction?
4. What evidence would you need to see before authorizing coverage for AI powered remote monitoring?
5. How do you evaluate new care management technologies for your covered population?

---

## 4. Candidate interviewees (find on LinkedIn and trade publications)

### HF Patients (3 to 5):
- Hopkins HF clinic patient advisory council members (request through clinic staff)
- Mended Hearts patient advocacy group (local Baltimore chapter)
- Heart Failure Society of America patient forum participants

### HF Nurses / NPs (3 to 5):
- NPs at Johns Hopkins Heart Failure Bridge Clinic
- Nurse coordinators at University of Maryland HF program
- RPM program nurses at MedStar Health

### Cardiologists / HF Program Directors (3 to 5):
- HF program directors at Hopkins, UMD, MedStar
- ACC Heart Failure Council members (searchable on ACC website)
- HFSA conference presenters on remote monitoring topics

### Hospital Administrators (3 to 5):
- VP of Quality at Johns Hopkins Health System
- CMO at MedStar Washington Hospital Center (high HF volume)
- Digital health innovation officers at Inova Health, Christiana Care

### MA Plan Medical Directors (3 to 5):
- Medical director at CareFirst BlueCross (Maryland dominant MA plan)
- Population health lead at Kaiser Permanente Mid Atlantic
- Chief medical officer at Clover Health or Alignment Healthcare (tech forward MA plans)

---

## 5. Outreach message

Hi [First Name / Dr. ____],

It is a pleasure to reach out via [LinkedIn/email]. My name is Waiz Khan, and I am a graduate student in Engineering Data Science at Johns Hopkins University, developing a venture to address gaps in heart failure care between clinic visits. Given your expertise in [heart failure management / health system operations / remote patient monitoring], I wanted to connect after learning about [your work on HF readmission reduction / your presentation at ACC / your clinic's RPM program].

As additional context, our team is building Iris, an AI care agent that provides 24/7 heart failure monitoring using guideline based clinical tools rather than language model generated advice. We have developed a functional prototype and are currently in the customer discovery phase through the Johns Hopkins Spark program.

I am not trying to sell anything — I am looking to learn from practitioners like you about the real challenges of managing heart failure patients and whether our approach addresses a genuine need. Would it be possible to speak for 15 minutes over Zoom in the coming week?

Thanks very much for your time and consideration!

Best,
Waiz Khan
M.S. Engineering Data Science, Johns Hopkins University

---

## 6. Interview tracking

(To be completed after conducting interviews. Target: at least 3 before next Mastermind session.)
