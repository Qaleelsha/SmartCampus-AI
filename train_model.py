import os
import pickle
from datetime import datetime

import pandas as pd
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score, train_test_split

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")

# Same thresholds as the rule-based fallback in app.py
ATTENDANCE_CUTOFF = 75
MARKS_CUTOFF = 60

# The labels only depend on these two columns
features = ["attendance", "averageMarks"]
label_order = ["HIGH", "MEDIUM", "LOW"]


def get_risk(attendance, marks):
    low_attendance = attendance < ATTENDANCE_CUTOFF
    low_marks = marks < MARKS_CUTOFF

    if low_attendance and low_marks:
        return "HIGH"
    if low_attendance or low_marks:
        return "MEDIUM"
    return "LOW"


# --------------------------------------------------
# Load data
# --------------------------------------------------

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
records = list(
    client["smartcampus"]["students"].find(
        {},
        {"_id": 0, "studentId": 1, "attendance": 1, "averageMarks": 1}
    )
)
client.close()

df = pd.DataFrame(records)

if df.empty:
    raise SystemExit("No student records found in MongoDB.")

# Same cleaning as the dashboard
for col in features:
    df[col] = pd.to_numeric(df[col], errors="coerce")

before = len(df)
df = df.dropna(subset=features).copy()
print(f"Records loaded: {before} (dropped {before - len(df)} incomplete)")

# --------------------------------------------------
# Rule-generated labels
# --------------------------------------------------

df["riskLevel"] = df.apply(
    lambda row: get_risk(row["attendance"], row["averageMarks"]), axis=1
)

print("\nLabel counts:")
print(df["riskLevel"].value_counts().reindex(label_order).fillna(0).astype(int))

X = df[features]
y = df["riskLevel"]

smallest_class = y.value_counts().min()

# --------------------------------------------------
# Train and evaluate on a held-out split
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y if smallest_class >= 2 else None
)

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    class_weight="balanced"
)
model.fit(X_train, y_train)

predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

print("\nTraining records:", len(X_train))
print("Test records:", len(X_test))
print("Test accuracy against rule-generated labels:", round(accuracy, 3))

print("\nClassification report:")
print(classification_report(y_test, predictions, zero_division=0))

present_labels = [label for label in label_order if label in y.unique()]
print("Confusion matrix (rows = actual, columns = predicted):")
print(pd.DataFrame(
    confusion_matrix(y_test, predictions, labels=present_labels),
    index=present_labels,
    columns=present_labels
))

# Cross-validation, only if every class has enough records
if smallest_class >= 2:
    folds = min(5, smallest_class)
    cv_scores = cross_val_score(model, X, y, cv=folds)
    print(f"\n{folds}-fold CV accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

print("\nFeature importance:")
for name, score in zip(features, model.feature_importances_):
    print(f"  {name}: {score:.3f}")

# --------------------------------------------------
# Final model on all records
# --------------------------------------------------

final_model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    class_weight="balanced"
)
final_model.fit(X, y)

# How often does the saved model disagree with the rule?
df["modelPrediction"] = final_model.predict(X)
mismatches = df[df["modelPrediction"] != df["riskLevel"]]
print(f"\nModel vs rule disagreements on all records: {len(mismatches)} of {len(df)}")

if not mismatches.empty:
    print(mismatches[["studentId", "attendance", "averageMarks",
                      "riskLevel", "modelPrediction"]].head(10))

# Edge cases around the thresholds, including the 84% attendance case
edge_cases = pd.DataFrame({
    "attendance":   [84,       84,    70,     70,       75,    74.9],
    "averageMarks": [50,       70,    50,     70,       60,    59.9],
    "expected":     ["MEDIUM", "LOW", "HIGH", "MEDIUM", "LOW", "HIGH"],
})
edge_cases["predicted"] = final_model.predict(edge_cases[features])
print("\nEdge case check:")
print(edge_cases)

# --------------------------------------------------
# Save
# --------------------------------------------------

with open("risk_model.pkl", "wb") as file:
    pickle.dump(
        {
            "model": final_model,
            "features": features,
            "thresholds": {
                "attendance": ATTENDANCE_CUTOFF,
                "marks": MARKS_CUTOFF
            },
            "trained_on": len(df),
            "trained_at": datetime.now().isoformat(timespec="seconds"),
            "holdout_accuracy": round(accuracy, 3),
        },
        file
    )

print("\nModel saved as risk_model.pkl")