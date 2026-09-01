"""
ML Engine — Anomaly Detection, Demand Forecasting, Maintenance Risk & NL Summaries.

Exposes five main classes:
    AnomalyDetector      — rule-based + IsolationForest anomaly detection
    DemandForecaster     — Prophet + XGBoost demand forecasting
    MaintenanceRiskModel — weighted rule-based maintenance risk scoring
    NLSummarizer         — LLM-powered natural language alert summaries
    Simulator            — synthetic telemetry data generator (batch)
"""

from ml_engine.anomaly_detector import AnomalyDetector
from ml_engine.demand_forecaster import DemandForecaster
from ml_engine.maintenance_risk import MaintenanceRiskModel
from ml_engine.nl_summarizer import NLSummarizer
from ml_engine.simulator import Simulator

__all__ = [
    "AnomalyDetector",
    "DemandForecaster",
    "MaintenanceRiskModel",
    "NLSummarizer",
    "Simulator",
]
