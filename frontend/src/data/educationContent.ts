/**
 * Patient education content — plain language explanations of clinical metrics.
 * Used in MetricTooltip to help patients and care teams understand values.
 */

export interface MetricEducation {
  label: string;
  fullName: string;
  whatItMeasures: string;
  normalRange: string;
  whyItMatters: string;
  simpleAnalogy?: string;
}

export const educationContent: Record<string, MetricEducation> = {
  potassium: {
    label: "K+",
    fullName: "Potassium",
    whatItMeasures: "The level of potassium in your blood, a mineral that helps your heart beat regularly.",
    normalRange: "3.5 to 5.0 mEq/L",
    whyItMatters: "Too low can cause irregular heartbeats. Too high can be dangerous for your heart. Many heart failure medicines affect potassium levels.",
    simpleAnalogy: "Think of potassium like the oil in your car engine. Too little or too much can cause the engine to misfire.",
  },
  creatinine: {
    label: "Cr",
    fullName: "Creatinine",
    whatItMeasures: "A waste product filtered by your kidneys. Higher levels may mean your kidneys are working harder.",
    normalRange: "0.7 to 1.3 mg/dL",
    whyItMatters: "Heart failure medicines can affect kidney function. Your care team watches this closely when adjusting medications.",
    simpleAnalogy: "Creatinine is like the exhaust from a car. If the exhaust builds up, it might mean the engine (your kidneys) needs a checkup.",
  },
  egfr: {
    label: "eGFR",
    fullName: "Estimated Glomerular Filtration Rate",
    whatItMeasures: "How well your kidneys are filtering waste from your blood. Higher numbers are better.",
    normalRange: "Above 60 is generally normal. Below 30 may need special attention.",
    whyItMatters: "Your kidneys and heart work together. When kidney function drops, your care team may need to adjust heart medicines.",
    simpleAnalogy: "Think of eGFR like a speedometer for your kidneys. The higher the number, the faster and better they're working.",
  },
  bnp: {
    label: "BNP",
    fullName: "B type Natriuretic Peptide",
    whatItMeasures: "A hormone released by your heart when it is under stress or working too hard.",
    normalRange: "Below 100 pg/mL is generally normal. Heart failure patients often have higher levels.",
    whyItMatters: "Rising BNP can be an early warning that your heart failure may be getting worse, even before you feel symptoms.",
    simpleAnalogy: "BNP is like a stress alarm from your heart. The higher it goes, the harder your heart is working.",
  },
  sodium: {
    label: "Na+",
    fullName: "Sodium",
    whatItMeasures: "The level of sodium (salt) in your blood, which helps control fluid balance.",
    normalRange: "135 to 145 mEq/L",
    whyItMatters: "Low sodium can happen with heart failure and some diuretics (water pills). It can cause confusion and fatigue.",
    simpleAnalogy: "Sodium helps keep the right amount of water in your body, like a sponge that holds just the right amount of moisture.",
  },
  ejection_fraction: {
    label: "EF",
    fullName: "Ejection Fraction",
    whatItMeasures: "The percentage of blood your heart pumps out with each beat. A healthy heart pumps about 55 to 70%.",
    normalRange: "55% to 70% is normal. Below 40% is considered reduced.",
    whyItMatters: "A lower EF means your heart is not pumping as strongly. The goal of treatment is to help improve or maintain your EF.",
    simpleAnalogy: "Imagine squeezing a water balloon. EF is how much water comes out with each squeeze. A healthy heart squeezes out more than half.",
  },
  nyha_class: {
    label: "NYHA",
    fullName: "New York Heart Association Functional Class",
    whatItMeasures: "How much your heart failure symptoms limit your daily activities, rated from I (least) to IV (most).",
    normalRange: "Class I: No limits. Class II: Mild limits. Class III: Notable limits. Class IV: Symptoms at rest.",
    whyItMatters: "This helps your care team understand how heart failure affects your daily life and guides treatment decisions.",
  },
};
