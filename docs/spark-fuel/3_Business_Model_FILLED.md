# BUSINESS MODEL — Worksheet 5

**Founder Name:** Waiz Khan
**Venture Name:** Iris Health
**Venture Description:** Iris is an AI powered heart failure care agent providing 24/7 monitoring and medication optimization using a tool first architecture. Every clinical decision comes from deterministic Python tools following AHA/ACC guidelines. The language model only extracts information and communicates results. A Response Validator blocks hallucinations. Iris monitors weight trends, optimizes GDMT medications, detects adherence barriers, predicts decompensation, and escalates to clinicians — all running locally with no paid APIs.

---

## 1. How are you making money?

**Who are you selling to?:**
Heart failure clinics and health systems — specifically HF program directors, chief medical officers, and VP of Digital Health/Innovation. Secondary: Medicare Advantage plans and ACOs bearing readmission risk.

**What are you selling:**
A SaaS platform that provides continuous AI powered heart failure monitoring per patient. The clinic gets: patient facing voice/text interface, clinician dashboard with transparent clinical reasoning, automated guideline concordant recommendations, escalation alerts, and predictive trajectory analytics.

**How often are you selling to them?:**
Monthly recurring subscription per patient monitored. Annual contracts with monthly billing. Expansion revenue as clinics add more patients to the platform.

**How will you reach them?:**
Clinical conference presentations (ACC, HFSA annual meetings), Hopkins network warm introductions, direct outreach to hospitals with high CMS readmission penalties (public data), and published pilot results.

**Why will they buy it?:**
CMS penalizes hospitals up to 3% of Medicare reimbursement for excess HF readmissions. The average HF readmission costs $15,000 to $25,000. Iris costs a fraction of that per patient and demonstrably reduces readmissions. Additionally, Iris extends care team capacity without adding headcount — critical given the nursing shortage.

---

## 2. Business model type

**Platform as a Service / SaaS Subscription Model** — similar to how Teladoc, Livongo (now part of Teladoc), and Omada Health sell chronic disease management platforms to health systems on a per member per month basis. This fits because:
- Healthcare buyers prefer predictable monthly costs over large upfront purchases
- Per patient pricing aligns cost with value delivered
- Recurring revenue creates predictable business for investors
- The platform improves with more patients (more data, better trajectory predictions)

---

## 3. Sources of revenue (prioritized)

a. **Per Patient Per Month (PPPM) subscription** — core revenue. Clinics pay $50 to $150/patient/month for Iris monitoring based on acuity tier. This is the primary and most scalable revenue stream.

b. **Remote Patient Monitoring (RPM) reimbursement pass through** — Iris activities qualify for CPT codes 99457 and 99458 (RPM management, $50 to $80/month reimbursable). Clinics can bill Medicare for Iris monitored patients, making Iris cost neutral or revenue positive. We take a percentage of facilitated reimbursement.

c. **Payer contracts** — Medicare Advantage plans and ACOs pay Iris directly to reduce their readmission costs across covered populations. Value based pricing tied to readmission reduction outcomes.

---

## 4. Unit of revenue for each stream

a. PPPM subscription: **1 patient monitored for 1 month.** Revenue recognized monthly per active patient on the platform.

b. RPM reimbursement: **1 qualifying RPM encounter billed.** Revenue is a percentage (15 to 25%) of the reimbursement the clinic captures using Iris.

c. Payer contracts: **1 covered life per month.** Revenue based on the number of HF patients in the plan that Iris monitors, with performance bonuses tied to readmission reduction.

---

## 5. Three similar products and their price points

**Biofourmis (RhythmAnalytics / Biovitals):**
- Health systems: $100 to $200/patient/month for RPM + AI analytics
- Includes wearable devices, nurse triage center
- Series D funded ($300M+)

**Current Health (acquired by Best Buy Health):**
- Health systems: $150 to $250/patient/month
- Includes wearable patch, care team dashboard, RPM billing support
- Requires hardware deployment

**Optimize Health (formerly Preveta):**
- Health systems: $80 to $150/patient/month for RPM platform
- Software only, integrates with existing devices
- Focused on RPM billing optimization

**Key difference:** All three rely on human nurses for clinical interpretation. Iris automates the clinical reasoning with deterministic, auditable tools — no nurse required for routine monitoring.

---

## 6. Cost of goods sold per unit (per patient per month)

- **Gemini API costs:** ~$0.50/patient/month (free tier covers prototype; at scale, ~15 to 20 API calls/patient/day at flash pricing)
- **Cloud hosting:** ~$2 to $5/patient/month (amortized server costs across patient panel)
- **Data storage:** ~$0.10/patient/month (JSON patient records, conversation history)
- **Customer support labor:** ~$5 to $10/patient/month (amortized across panel, for escalation review and onboarding support)
- **Clinical validation/quality:** ~$2 to $3/patient/month (cardiologist advisor review of edge cases)
- **Total COGS: ~$10 to $19/patient/month**

---

## 7. Estimated price point for each revenue stream

a. **PPPM subscription:**
- COGS: $10 to $19/patient/month
- Target price: $75/patient/month (standard), $125/patient/month (high acuity with daily voice check ins)
- Range: $50 to $150/patient/month
- Gross margin: 60 to 80%

b. **RPM reimbursement share:**
- Clinics bill $50 to $80/month per qualifying patient (CPT 99457/99458)
- Iris takes 20% = $10 to $16/patient/month
- This can offset or reduce the effective PPPM cost for the clinic

c. **Payer contracts:**
- Target: $30 to $75/covered life/month
- Lower than clinic pricing because payer volumes are much larger
- Performance bonus: additional $25 to $50/patient for documented readmission prevention

---

## 8. How often do you expect customers to buy?

a. **PPPM subscription:** Monthly, recurring. Average patient stays on the platform for the duration of their HF management (chronic condition = long lifetime value). Expected retention: 12 to 24+ months per patient. Clinics sign annual contracts.

b. **RPM reimbursement:** Monthly, ongoing as long as the patient is being monitored and qualifies for RPM billing.

c. **Payer contracts:** Annual contracts with quarterly performance reviews. Renewed annually based on demonstrated readmission reduction.

---

## 9. How does your price compare to competitors?

**Lower than most competitors** — Biofourmis ($100 to $200) and Current Health ($150 to $250) include hardware and human nurse triage. Iris is software only with no hardware cost and no per patient nurse cost, enabling lower pricing while maintaining margins.

**The justification for being lower:** Iris's tool first architecture automates clinical reasoning that competitors delegate to nurses. This is not a compromise on quality — the deterministic pipeline is actually more consistent than human triage (no alert fatigue, no shift changes, no missed patterns). The lower price point also opens the market to smaller clinics and safety net hospitals that cannot afford $200+/patient/month solutions.

**If competing with free alternatives** (basic weight scales + nurse phone calls): Iris is more expensive than doing nothing, but dramatically cheaper than the readmission it prevents ($75/month vs $15,000+ per hospitalization). The ROI case is straightforward: prevent 1 readmission per 15 patients monitored and the platform pays for itself many times over.
