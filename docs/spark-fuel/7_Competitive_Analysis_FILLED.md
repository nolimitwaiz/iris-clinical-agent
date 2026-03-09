# COMPETITIVE ANALYSIS — Worksheet 8

**Founder Name:** Waiz Khan
**Venture Name:** Iris Health
**Venture Description:** Iris is an AI powered heart failure care agent providing 24/7 monitoring and medication optimization. Every clinical decision comes from deterministic Python tools following AHA/ACC guidelines. The language model only extracts patient info and communicates tool outputs.

---

## 1. Who are your competitors?

### Direct Competitors (AI/digital RPM platforms for heart failure)

**a. Biofourmis (RhythmAnalytics / Biovitals)**
- Series D funded ($300M+), headquartered in Boston
- AI powered remote patient monitoring with proprietary wearable sensors
- Provides predictive analytics on vital signs with nurse triage center
- FDA cleared for several biosensor applications
- Customers: major health systems, pharma companies for clinical trials
- Price: $100 to $200/patient/month

**b. Current Health (acquired by Best Buy Health, 2021)**
- Continuous wearable monitoring patch + cloud analytics platform
- Integrates with major EHR systems (Epic, Cerner)
- Nurse led triage and care coordination included
- Focus on post discharge monitoring for multiple conditions
- Price: $150 to $250/patient/month

**c. Optimize Health (formerly Preveta)**
- Software only RPM platform focused on billing optimization
- Helps clinics capture CPT 99457/99458 reimbursement
- Integrates with third party devices (scales, BP cuffs)
- No proprietary clinical reasoning — relies on human nurses for interpretation
- Price: $80 to $150/patient/month

### Indirect Competitors (traditional approaches)

**d. Traditional RPM Programs (in house)**
- Hospitals run their own RPM programs with Bluetooth scales and nurse phone calls
- Alert based: scale transmits weight, nurse reviews if threshold exceeded
- High labor cost: 1 RPM nurse can manage ~80 to 120 patients
- No clinical reasoning or guideline concordance checking built in
- Cost: $120 to $200/patient/month (mostly labor)

**e. Standard Care (no RPM)**
- Patient sees cardiologist every 3 to 6 months
- Self monitoring with education at discharge ("call if you gain 2 lbs")
- Results: 22% average 30 day readmission rate for HF
- Cost: $0 for monitoring, but $15,000 to $25,000 per readmission

---

## 2. Feature Comparison Matrix

| Feature | Iris Health | Biofourmis | Current Health | Optimize Health | In House RPM |
|---|---|---|---|---|---|
| 24/7 automated monitoring | Yes | Yes | Yes | Partial | No (business hours) |
| Clinical reasoning engine | Yes (deterministic) | Partial (ML based) | No | No | No |
| Guideline concordant recommendations | Yes (AHA/ACC cited) | No | No | No | Nurse dependent |
| Transparent decision audit trail | Yes (Action Packets) | Limited | Limited | No | Chart notes only |
| Voice first patient interface | Yes | No | No | No | Phone calls |
| Barrier aware planning | Yes (cost, access, literacy) | No | No | No | Nurse judgment |
| Predictive trajectory analysis | Yes | Yes | Partial | No | No |
| Requires proprietary hardware | No | Yes (wearable) | Yes (patch) | No | Yes (scales) |
| Requires dedicated nurse staff | No | Yes (triage center) | Yes | Yes | Yes |
| EHR integration (FHIR) | Export ready | Full integration | Full integration | Partial | Native |
| RPM billing support (CPT) | Yes | Yes | Yes | Core feature | Manual |
| Hallucination prevention | Yes (Response Validator) | N/A | N/A | N/A | N/A |
| FDA clearance | Not yet | Yes (select features) | Yes | No | N/A |
| Price per patient per month | $50 to $150 | $100 to $200 | $150 to $250 | $80 to $150 | $120 to $200 |

---

## 3. Competitive Advantages (What makes Iris different)

### Primary Differentiator: Tool First Architecture
Every competitor uses one of two approaches: (1) raw data + human nurse interpretation, or (2) ML based predictions that clinicians cannot audit. Iris is neither. Every clinical recommendation comes from deterministic Python tools that follow published AHA/ACC guidelines. The language model never makes clinical decisions — it only extracts patient information and communicates tool outputs. This means:
- Every recommendation has a traceable guideline citation
- No hallucination risk — the Response Validator blocks any invented clinical content
- Clinicians can audit exactly why a recommendation was made
- Regulatory positioning is clearer (Clinical Decision Support vs medical device)

### Secondary Differentiator: No Nurse Required for Routine Monitoring
Biofourmis, Current Health, and in house RPM programs all require dedicated nursing staff for clinical interpretation. This is their largest cost center and their scaling bottleneck. Iris automates the clinical reasoning, meaning:
- Lower cost per patient ($75 vs $150+)
- Infinite scalability (no nurse to patient ratio constraint)
- Consistent quality (no alert fatigue, no shift variation, no missed patterns)
- Nurses are freed to focus on complex cases that truly need human judgment

### Tertiary Differentiator: Voice First, Barrier Aware
No competitor offers a voice first patient interface combined with barrier aware planning. Most RPM platforms assume patients can use apps, afford medications, and get to pharmacies. Iris:
- Works via voice conversation — accessible to elderly and low literacy patients
- Checks insurance tier, pharmacy distance, and health literacy before recommending
- Suggests affordable alternatives when cost is a barrier
- Communicates in plain language calibrated to the patient's health literacy level

---

## 4. Competitive Disadvantages (Honest Assessment)

| Weakness | Impact | Mitigation Strategy |
|---|---|---|
| No FDA clearance yet | Cannot market as a medical device; some health systems require FDA cleared tools | Pursue Clinical Decision Support exemption (21st Century Cures Act criteria); if 510(k) required, engage regulatory consultant and plan 12 to 18 month timeline |
| No EHR integration (beyond FHIR export) | Health systems strongly prefer Epic/Cerner integrated tools; adds friction to adoption | FHIR R4 export is the bridge; prioritize Epic App Orchard listing in Year 2 |
| Solo founder, no clinical co founder | Investors and health systems prefer teams with MD/RN co founders | Build clinical advisory board (3+ cardiologists); recruit clinical co founder from pilot site relationships |
| No published clinical evidence | Competitors have case studies and peer reviewed publications | Pilot study at Hopkins generates first evidence; design pilot for publication from day one |
| Early stage — no customers yet | Risk perception is high for hospitals buying from a startup | Hopkins brand association reduces risk; start with pilot (low commitment) not enterprise sale |
| Limited drug classes implemented | Currently only diuretics and beta blockers; ARNI, MRA, SGLT2i are stubbed | Clear technical architecture for adding drug classes; full GDMT coverage planned for post pilot |

---

## 5. Barriers to Entry (Moats)

**What prevents a competitor from copying Iris?**

1. **Clinical knowledge engineering** — translating AHA/ACC guidelines into deterministic code is laborious, error prone, and requires deep clinical domain expertise. It took significant effort to implement just diuretics and beta blockers correctly. Competitors using ML based approaches would need to fundamentally rearchitect.

2. **Validation test suite** — 97 automated tests verify every clinical rule, edge case, and Action Packet format. This is a compounding asset — every new drug class adds more tests, making the system increasingly reliable and auditable.

3. **Tool first architecture is counterintuitive** — the current AI industry is moving toward giving LLMs more autonomy. Iris moves in the opposite direction, constraining the LLM to extraction and communication only. Established competitors are unlikely to reverse their architecture.

4. **Network effects (future)** — as more patients use Iris, trajectory predictions improve. As more clinicians review Action Packets, the system learns which recommendations get overridden and why (feedback loop for guideline refinement).

5. **Regulatory positioning** — by building deterministic, auditable tools, Iris may qualify for the CDS exemption under 21st Century Cures Act. Competitors using black box ML may face stricter regulatory scrutiny.

---

## 6. How will competitors respond?

| Competitor | Likely Response | Our Counter |
|---|---|---|
| Biofourmis | Add more AI features to existing platform; may attempt guideline based reasoning | Their architecture is ML first — retrofitting deterministic tools is a fundamental rebuild. Their hardware dependency also limits market reach |
| Current Health (Best Buy) | Leverage Best Buy retail distribution; may add AI triage | Best Buy's focus is consumer wellness, not clinical decision support. Their cost structure (hardware + nurses) makes them uncompetitive on price |
| Optimize Health | Could add clinical reasoning to their billing platform | Their core competency is billing optimization, not clinical AI. Would need to hire clinical engineers and rebuild |
| Epic/Cerner | Could build native RPM with clinical reasoning into EHR | EHR vendors move slowly (18 to 36 month product cycles). Their AI efforts are broad, not HF specific. But long term this is the biggest threat |

---

## 7. Positioning Statement

**For** heart failure clinics **who** need to reduce readmissions without adding nursing staff, **Iris is** an AI care agent **that** provides 24/7 guideline concordant monitoring with transparent, auditable clinical reasoning. **Unlike** existing RPM platforms that rely on human nurses for clinical interpretation or black box ML for predictions, **Iris** uses deterministic tools that follow published AHA/ACC guidelines — every recommendation comes with a citation, not a probability score.
