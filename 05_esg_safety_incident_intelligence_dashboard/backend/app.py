
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import pandas as pd
import re
from collections import Counter

app = FastAPI(
    title="ESG / Safety Incident Intelligence Dashboard",
    description="Incident classification, severity analysis and ESG analytics",
    version="1.0.0"
)

# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
FRONTEND = BASE / "frontend"

CSV_FILE = DATA / "safety_esg_incidents.csv"

# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------

class Query(BaseModel):
    text: str = ""


# --------------------------------------------------
# LOAD DATASET
# --------------------------------------------------

def load_dataset():
    if not CSV_FILE.exists():
        return pd.DataFrame(
            columns=[
                "incident_id",
                "narrative",
                "target_category",
                "target_severity"
            ]
        )

    df = pd.read_csv(CSV_FILE)
    df.columns = df.columns.str.strip()

    return df


# --------------------------------------------------
# INCIDENT CLASSIFICATION
# --------------------------------------------------

CATEGORY_KEYWORDS = {
    "safety": [
        "injury", "slip", "fall", "near miss", "accident",
        "ppe", "unsafe", "contractor", "vehicle", "hazard",
        "fire", "electrical", "worker", "incident"
    ],
    "environment": [
        "oil", "spill", "leakage", "leak", "water",
        "pollution", "emission", "chemical", "contamination",
        "environment", "wastewater", "fuel"
    ],
    "esg_compliance": [
        "compliance", "violation", "segregation",
        "regulation", "audit", "policy", "reporting",
        "non-compliance", "deviation", "governance"
    ]
}


def classify_incident(text):

    text = text.lower()

    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():

        scores[category] = sum(
            1 for keyword in keywords
            if keyword in text
        )

    # Highest matching category
    category = max(scores, key=scores.get)

    # If no keywords match
    if scores[category] == 0:
        category = "safety"

    return category


# --------------------------------------------------
# SEVERITY PREDICTION
# --------------------------------------------------

HIGH_RISK = [
    "fatal", "death", "serious injury", "major injury",
    "critical", "explosion", "fire", "electrocution",
    "near miss", "vehicle movement", "high risk",
    "major spill", "large spill", "uncontrolled"
]

MEDIUM_RISK = [
    "minor injury", "slipped", "slip", "unsafe",
    "ppe", "leakage", "leak", "non-compliance",
    "deviation", "hazard", "observed", "damage"
]


def predict_severity(text):

    text = text.lower()

    if any(word in text for word in HIGH_RISK):
        return "high"

    if any(word in text for word in MEDIUM_RISK):
        return "medium"

    return "low"


# --------------------------------------------------
# INCIDENT SUMMARY
# --------------------------------------------------

def generate_summary(text):

    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return "No incident description provided."

    # Basic extractive summary
    sentences = re.split(r"[.!?]+", text)

    summary = sentences[0].strip()

    if len(summary) > 180:
        summary = summary[:177] + "..."

    return summary.capitalize() + (
        "." if not summary.endswith(".") else ""
    )


# --------------------------------------------------
# PREVENTIVE ACTIONS
# --------------------------------------------------

PREVENTIVE_ACTIONS = {
    "safety": [
        "Conduct a safety inspection of the affected area.",
        "Ensure appropriate PPE usage.",
        "Provide toolbox training to workers.",
        "Implement hazard identification and risk assessment.",
        "Improve housekeeping and safety monitoring."
    ],
    "environment": [
        "Contain and clean the affected area immediately.",
        "Inspect equipment for leakage or damage.",
        "Monitor environmental impact.",
        "Implement preventive maintenance.",
        "Review environmental compliance procedures."
    ],
    "esg_compliance": [
        "Review the applicable compliance requirements.",
        "Conduct an internal compliance audit.",
        "Provide contractor awareness training.",
        "Improve documentation and monitoring.",
        "Implement corrective action tracking."
    ]
}


def get_recommendations(category, severity):

    actions = PREVENTIVE_ACTIONS.get(
        category,
        PREVENTIVE_ACTIONS["safety"]
    )

    if severity == "high":
        return [
            "Immediately investigate and control the hazard.",
            "Escalate the incident to the responsible safety team."
        ] + actions[:3]

    return actions[:3]


# --------------------------------------------------
# ANALYZE INCIDENT
# --------------------------------------------------

def analyze_incident(text):

    if not text or not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Incident narrative cannot be empty."
        )

    category = classify_incident(text)
    severity = predict_severity(text)
    summary = generate_summary(text)

    recommendations = get_recommendations(
        category,
        severity
    )

    return {
        "category": category,
        "severity": severity,
        "summary": summary,
        "recommended_actions": recommendations
    }


# --------------------------------------------------
# FRONTEND
# --------------------------------------------------

@app.get("/")
def home():

    index_file = FRONTEND / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Frontend index.html not found."
        )

    return FileResponse(index_file)


# --------------------------------------------------
# DEMO
# --------------------------------------------------

@app.get("/api/demo")
def demo():

    return {
        "case_study": "ESG / Safety Incident Intelligence Dashboard",
        "status": "running",
        "dataset_available": CSV_FILE.exists()
    }


# --------------------------------------------------
# INCIDENT ANALYSIS API
# --------------------------------------------------

@app.post("/api/run")
def run_case(query: Query):

    result = analyze_incident(query.text)

    return {
        "input": query.text,
        "result": result
    }


# --------------------------------------------------
# DATASET API
# --------------------------------------------------

@app.get("/api/incidents")
def get_incidents():

    df = load_dataset()

    return df.fillna("").to_dict(orient="records")


# --------------------------------------------------
# DASHBOARD ANALYTICS
# --------------------------------------------------

@app.get("/api/metrics")
def get_metrics():

    df = load_dataset()

    if df.empty:
        return {
            "total_incidents": 0,
            "category_distribution": {},
            "severity_distribution": {}
        }

    return {
        "total_incidents": len(df),
        "category_distribution":
            df["target_category"].value_counts().to_dict(),
        "severity_distribution":
            df["target_severity"].value_counts().to_dict()
    }


# --------------------------------------------------
# TREND ANALYSIS
# --------------------------------------------------

@app.get("/api/trends")
def get_trends():

    df = load_dataset()

    if df.empty:
        return {
            "top_keywords": [],
            "category_distribution": {},
            "severity_distribution": {}
        }

    text = " ".join(
        df["narrative"].astype(str).tolist()
    ).lower()

    words = re.findall(r"\b[a-z]{4,}\b", text)

    stopwords = {
        "near", "during", "with", "from", "area",
        "observed", "found", "activity", "issue"
    }

    words = [
        word for word in words
        if word not in stopwords
    ]

    top_keywords = Counter(words).most_common(10)

    return {
        "top_keywords": [
            {"keyword": word, "count": count}
            for word, count in top_keywords
        ],
        "category_distribution":
            df["target_category"].value_counts().to_dict(),
        "severity_distribution":
            df["target_severity"].value_counts().to_dict()
    }


# --------------------------------------------------
# MODEL EVALUATION
# --------------------------------------------------

@app.get("/api/evaluation")
def evaluation():

    from sklearn.metrics import accuracy_score

    df = load_dataset()

    if df.empty:
        return {"message": "Dataset unavailable"}

    actual_categories = df["target_category"].astype(str).tolist()

    predicted_categories = [
        classify_incident(text)
        for text in df["narrative"].astype(str)
    ]

    accuracy = accuracy_score(
        actual_categories,
        predicted_categories
    )

    return {
        "evaluation_type": "Rule-based baseline",
        "dataset_size": len(df),
        "category_accuracy": round(
            float(accuracy), 4
        ),
        "category_accuracy_percentage": round(
            float(accuracy) * 100, 2
        )
    }
