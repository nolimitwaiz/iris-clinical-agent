from src.utils.data_loader import load_patient, load_drug_database
from src.tools.trajectory_analyzer import analyze_trajectory
from src.tools.gdmt_engine import evaluate_gdmt
from datetime import date
from src.tools.safety_checker import check_safety

patient = load_patient("003")
drug_db = load_drug_database()
trajectory_packet = analyze_trajectory(patient)
proposed_changes = evaluate_gdmt(patient, trajectory_packet, drug_db, reference_date=date(2026, 2, 28))

print("GDMT output:")
for p in proposed_changes:
    print(f"{p['drug']} -> {p['decision']}")

safety_results = check_safety(proposed_changes, patient, drug_db)
print("\nSafety output:")
for p in safety_results:
    print(f"{p['drug']} -> {p['decision']}")
