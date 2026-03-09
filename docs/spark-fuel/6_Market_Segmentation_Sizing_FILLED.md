# MARKET SEGMENTATION & SIZING — Worksheet 7

**Founder Name:** Waiz Khan
**Venture Name:** Iris Health
**Venture Description:** Iris is an AI powered heart failure care agent providing 24/7 monitoring and medication optimization. Every clinical decision comes from deterministic Python tools following AHA/ACC guidelines. The language model only extracts patient info and communicates tool outputs.

---

## 1. Market Segments

### Segment A: Heart Failure Clinics at Academic Medical Centers
- **Who:** HF program directors and nurse managers at teaching hospitals (Hopkins, Penn, Duke, Cleveland Clinic, UCSF, etc.)
- **Why this segment:** Early adopters of clinical technology, have research infrastructure for pilot studies, presence at ACC/HFSA conferences, high patient volumes, face significant CMS penalties
- **Size:** ~150 academic medical centers with dedicated HF programs in the US
- **Average HF panel:** 500 to 1,500 patients per center
- **Budget authority:** Department chairs and CMOs, typically $50K to $500K discretionary budget for quality improvement

### Segment B: Community Hospital Heart Failure Programs
- **Who:** Hospital administrators and quality officers at community hospitals (200 to 500 beds) with HF readmission penalty exposure
- **Why this segment:** Largest segment by count, face the same CMS penalties as academic centers but have fewer resources to address them, more price sensitive, less likely to pilot unproven technology
- **Size:** ~2,000 community hospitals with HF readmission rates above national average (per CMS Hospital Compare data)
- **Average HF panel:** 100 to 400 patients per hospital
- **Budget authority:** CMOs and VP of Quality, tighter budgets, need proven ROI before adopting

### Segment C: Medicare Advantage Plans
- **Who:** Medical directors and population health leaders at MA plans bearing financial risk for HF hospitalizations
- **Why this segment:** Each prevented HF readmission saves the plan $15,000 to $25,000. MA plans cover ~31M beneficiaries, with HF prevalence of ~10% in 65+ populations. They have direct financial incentive and can mandate care management programs across their network
- **Size:** ~600 MA plan contracts (operated by ~200 parent organizations)
- **Average HF membership:** 2,000 to 50,000 HF patients per plan depending on geographic coverage
- **Budget authority:** Chief medical officers and VP of Care Management

---

## 2. Primary Target Segment

**Segment A: Academic Medical Center HF Clinics**

**Why start here:**
1. Hopkins network provides warm introductions to the first 3 to 5 pilot sites
2. Academic centers publish results — a positive pilot becomes a peer reviewed paper that sells to every other segment
3. Higher tolerance for innovation and pilot programs
4. Larger patient panels mean faster statistical significance in readmission reduction
5. Their clinicians present at ACC/HFSA conferences — organic distribution channel
6. They have existing RPM infrastructure (scales, portals) that Iris enhances rather than replaces

---

## 3. Market Sizing

### Total Addressable Market (TAM)

**All heart failure patients in the US who could benefit from continuous AI monitoring:**
- 6.7 million Americans living with heart failure (AHA 2024 statistics)
- At $75/patient/month average (blended across acuity tiers): 6,700,000 x $75 x 12 = **$6.03 billion/year**

### Serviceable Addressable Market (SAM)

**HF patients at hospitals with above average readmission rates who are candidates for remote monitoring:**
- ~2,150 hospitals (academic + community) with HF readmission rates above national average
- Average 300 HF patients per hospital eligible for monitoring = 645,000 patients
- At $75/patient/month: 645,000 x $75 x 12 = **$580 million/year**

### Serviceable Obtainable Market (SOM) — Year 1 to 3

**Realistic capture: academic medical centers in the Mid Atlantic region**

**Year 1 (Pilot):**
- 2 to 3 academic medical centers (Hopkins network)
- 50 patients per site = 100 to 150 patients
- At $75/patient/month: 150 x $75 x 12 = **$135,000/year**

**Year 2 (Regional expansion):**
- 8 to 12 sites (Mid Atlantic academic and community hospitals)
- 200 patients per site average = 1,600 to 2,400 patients
- At $75/patient/month: 2,400 x $75 x 12 = **$2.16 million/year**

**Year 3 (National + first payer contract):**
- 30 to 40 hospital sites + 1 to 2 MA plan contracts
- 8,000 to 12,000 patients total
- At $75/patient/month: 12,000 x $75 x 12 = **$10.8 million/year**

---

## 4. Bottom Up Sizing Methodology

### Unit Economics per Hospital Site

| Item | Value |
|---|---|
| Average HF patient panel per site | 300 patients |
| Percentage eligible for Iris monitoring | 60% (exclude hospice, non compliant, no phone) |
| Patients monitored per site | 180 |
| Revenue per patient per month | $75 |
| Monthly revenue per site | $13,500 |
| Annual revenue per site | $162,000 |
| COGS per patient per month | $15 |
| Monthly COGS per site | $2,700 |
| Monthly gross profit per site | $10,800 |
| Gross margin | 80% |

### Value Created per Hospital Site

| Item | Value |
|---|---|
| Baseline readmission rate | 22% |
| Target readmission rate with Iris | 16% (27% relative reduction) |
| Readmissions prevented per year (180 patients) | ~11 |
| Cost per readmission | $20,000 average |
| Direct savings to hospital | $220,000/year |
| Iris cost to hospital | $162,000/year |
| Net savings | $58,000/year + CMS penalty reduction |
| ROI | 136% in direct savings alone |

---

## 5. Key Assumptions in Sizing

1. **HF prevalence remains stable or grows** — AHA projects HF prevalence to increase 46% by 2030 due to aging population. This assumption is well supported.

2. **Hospitals will pay $75/patient/month** — validated against competitor pricing ($100 to $250/patient/month for nurse led RPM). Iris is lower cost because it automates clinical reasoning. Needs customer discovery validation.

3. **60% of HF patients are eligible for monitoring** — excludes patients in hospice, those without phone access, those who decline. This may be conservative; voice first design increases eligibility vs app based solutions.

4. **Iris achieves 25 to 30% relative reduction in readmissions** — published literature shows RPM alone achieves 15 to 20% reduction. Iris adds clinical reasoning and barrier planning. Needs pilot data to validate.

5. **2 to 3 pilot sites achievable in Year 1** — depends on Hopkins network introductions, IRB timelines, and hospital procurement cycles. This is the highest risk assumption.

---

## 6. Competitive Landscape Summary (for sizing context)

| Competitor | Annual Revenue | Patients Monitored | Price Point |
|---|---|---|---|
| Biofourmis | ~$50M (estimated) | ~100,000 | $100 to $200/patient/month |
| Current Health (Best Buy) | ~$30M (estimated) | ~60,000 | $150 to $250/patient/month |
| Optimize Health | ~$20M (estimated) | ~50,000 | $80 to $150/patient/month |

**Total addressable competitor revenue: ~$100M** — confirming that the market is real, growing, and has room for a differentiated entrant.

---

## 7. Growth Strategy by Segment

**Phase 1 (Months 1 to 12): Prove with Segment A**
- Pilot at 2 to 3 Hopkins affiliated sites
- Publish readmission reduction data
- Build case studies with named clinicians

**Phase 2 (Months 12 to 24): Expand within A, enter B**
- Expand to 8 to 12 academic centers nationally (conference pipeline)
- Begin outreach to community hospitals with highest CMS penalties
- Hire first sales rep focused on Segment B

**Phase 3 (Months 24 to 36): Enter Segment C**
- Approach MA plans with published clinical evidence
- Offer population level pricing ($30 to $75/covered life/month)
- Performance based contracts (bonus for readmission reduction)

**Phase 4 (Months 36+): Platform expansion**
- Expand beyond HF to COPD, diabetes, CKD (same architecture, different clinical tools)
- Each new condition multiplies the addressable market by 2 to 3x
