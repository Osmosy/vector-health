#!/usr/bin/env python3
"""
Lab Result Interpretation Tool
Transforms complex biochemical test results into patient-friendly explanations.
"""

import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class LabResult:
    """Represents a single lab test result."""
    test_name: str
    value: float
    unit: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    status: str = "normal"  # normal, low, high, critical
    severity: str = "none"  # none, mild, moderate, severe
    explanation: str = ""
    recommendation: str = ""


class LabResultInterpreter:
    """Interprets lab test results and generates patient-friendly explanations."""
    
    # Common test name mappings (Chinese/English variations)
    TEST_NAME_MAPPINGS = {
        # Blood Routine
        "wbc": "white blood cell count", "leukocyte": "white blood cell count", "white blood cell": "white blood cell count",
        "rbc": "red blood cell count", "red blood cells": "red blood cell count", "red blood cell": "red blood cell count",
        "hgb": "hemoglobin", "hemoglobin": "hemoglobin", "hemoglobin": "hemoglobin",
        "plt": "platelet count", "platelets": "platelet count", "platelet": "platelet count",
        "hct": "Hematocrit", "Hematocrit": "Hematocrit", "hematocrit": "Hematocrit",
        
        # Lipid Panel
        "tc": "total cholesterol", "total cholesterol": "total cholesterol", "cholesterol": "total cholesterol",
        "ldl": "LDL cholesterol", "ldl-c": "LDL cholesterol", "low density lipoprotein": "LDL cholesterol",
        "hdl": "HDL cholesterol", "hdl-c": "HDL cholesterol", "HDL": "HDL cholesterol",
        "tg": "Triglycerides", "Triglycerides": "Triglycerides", "triglyceride": "Triglycerides",
        
        # Liver Function
        "alt": "alanine aminotransferase", "alanine aminotransferase": "alanine aminotransferase", "gpt": "alanine aminotransferase",
        "ast": "aspartate aminotransferase", "aspartate aminotransferase": "aspartate aminotransferase", "got": "aspartate aminotransferase",
        "alp": "alkaline phosphatase", "alkaline phosphatase": "alkaline phosphatase",
        "ggt": "γ-glutamyl transpeptidase", "ggt": "γ-glutamyl transpeptidase",
        "tbil": "total bilirubin", "total bilirubin": "total bilirubin", "bilirubin": "total bilirubin",
        "tp": "total protein", "total protein": "total protein", "total protein": "total protein",
        "alb": "albumin", "albumin": "albumin", "albumin": "albumin",
        
        # Kidney Function
        "crea": "Creatinine", "Creatinine": "Creatinine", "creatinine": "Creatinine",
        "bun": "Urea nitrogen", "Urea nitrogen": "Urea nitrogen", "urea": "Urea nitrogen",
        "egfr": "glomerular filtration rate", "gfr": "glomerular filtration rate",
        "ua": "uric acid", "uric acid": "uric acid", "uric acid": "uric acid",
        
        # Blood Sugar
        "glu": "fasting blood glucose", "fasting blood glucose": "fasting blood glucose", "glucose": "fasting blood glucose",
        "hba1c": "Glycated hemoglobin", "Glycated hemoglobin": "Glycated hemoglobin",
        
        # Thyroid
        "tsh": "thyroid stimulating hormone", "thyroid stimulating hormone": "thyroid stimulating hormone",
        "t3": "triiodothyronine", "triiodothyronine": "triiodothyronine",
        "t4": "Thyroxine", "Thyroxine": "Thyroxine",
        "ft3": "free triiodothyronine", "free triiodothyronine": "free triiodothyronine",
        "ft4": "free thyroxine", "free thyroxine": "free thyroxine",
        
        # Electrolytes
        "na": "sodium", "sodium": "sodium", "sodium": "sodium",
        "k": "Potassium", "Potassium": "Potassium", "potassium": "Potassium",
        "cl": "chlorine", "chlorine": "chlorine", "chloride": "chlorine",
        "ca": "calcium", "calcium": "calcium", "calcium": "calcium",
        "mg": "magnesium", "magnesium": "magnesium", "magnesium": "magnesium",
        
        # Inflammation
        "crp": "C-reactive protein", "c-reactive protein": "C-reactive protein",
        "esr": "ESR", "ESR": "ESR", "erythrocyte sedimentation rate": "ESR",
    }
    
    # Standard reference ranges
    REFERENCE_RANGES = {
        "white blood cell count": {"min": 4.0, "max": 10.0, "unit": "10^9/L"},
        "red blood cell count": {"min": 4.0, "max": 5.5, "unit": "10^12/L"},
        "hemoglobin": {"min": 120.0, "max": 160.0, "unit": "g/L"},
        "platelet count": {"min": 100.0, "max": 300.0, "unit": "10^9/L"},
        "Hematocrit": {"min": 0.40, "max": 0.50, "unit": "L/L"},
        "total cholesterol": {"min": 3.1, "max": 5.7, "unit": "mmol/L"},
        "LDL cholesterol": {"min": 0.0, "max": 3.4, "unit": "mmol/L"},
        "HDL cholesterol": {"min": 1.0, "max": 2.0, "unit": "mmol/L"},
        "Triglycerides": {"min": 0.0, "max": 1.7, "unit": "mmol/L"},
        "alanine aminotransferase": {"min": 0.0, "max": 40.0, "unit": "U/L"},
        "aspartate aminotransferase": {"min": 0.0, "max": 40.0, "unit": "U/L"},
        "alkaline phosphatase": {"min": 40.0, "max": 150.0, "unit": "U/L"},
        "γ-glutamyl transpeptidase": {"min": 10.0, "max": 60.0, "unit": "U/L"},
        "total bilirubin": {"min": 0.0, "max": 21.0, "unit": "μmol/L"},
        "total protein": {"min": 60.0, "max": 80.0, "unit": "g/L"},
        "albumin": {"min": 35.0, "max": 55.0, "unit": "g/L"},
        "Creatinine": {"min": 44.0, "max": 133.0, "unit": "μmol/L"},
        "Urea nitrogen": {"min": 2.6, "max": 7.5, "unit": "mmol/L"},
        "uric acid": {"min": 208.0, "max": 428.0, "unit": "μmol/L"},
        "fasting blood glucose": {"min": 3.9, "max": 6.1, "unit": "mmol/L"},
        "Glycated hemoglobin": {"min": 4.0, "max": 6.0, "unit": "%"},
        "thyroid stimulating hormone": {"min": 0.27, "max": 4.2, "unit": "mIU/L"},
        "sodium": {"min": 137.0, "max": 147.0, "unit": "mmol/L"},
        "Potassium": {"min": 3.5, "max": 5.3, "unit": "mmol/L"},
        "chlorine": {"min": 99.0, "max": 110.0, "unit": "mmol/L"},
        "calcium": {"min": 2.1, "max": 2.6, "unit": "mmol/L"},
        "C-reactive protein": {"min": 0.0, "max": 10.0, "unit": "mg/L"},
    }
    
    def __init__(self):
        self.disclaimer = "[Disclaimer] This interpretation is for reference only and cannot replace professional medical advice. If in doubt please consult your doctor."
    
    def normalize_test_name(self, name: str) -> str:
        """Normalize test name to standard form."""
        name_lower = name.lower().strip()
        return self.TEST_NAME_MAPPINGS.get(name_lower, name)
    
    def parse_lab_line(self, line: str) -> Optional[LabResult]:
        """Parse a single line of lab result."""
        # Pattern 1: "Name: Value Unit (Ref: Min-Max)" or "Name: Value (Min-Max)" or "Name: Value Unit"
        pattern1 = "(.+?)[:\\s]+([\\d.]+)\\s*(\\S*)?(?:\\s*[\\(\\(]?[^\\d]*([\\d.]+)?\\s*[-~to]\\s*([\\d.]+)?[^\\)]*[\\)\\)]?)?"
        
        # Pattern 2: "Name Value Unit" (simpler format)
        pattern2 = r"^(.+?)\s+([\d.]+)\s+(\S+)$"
        
        for pattern in [pattern1, pattern2]:
            match = re.search(pattern, line.strip())
            if match:
                groups = match.groups()
                test_name = self.normalize_test_name(groups[0].strip())
                value = float(groups[1])
                unit = groups[2] if groups[2] else ""
                ref_min = float(groups[3]) if groups[3] else None
                ref_max = float(groups[4]) if groups[4] else None
                
                # Use standard reference range if not provided
                if test_name in self.REFERENCE_RANGES:
                    std_range = self.REFERENCE_RANGES[test_name]
                    if ref_min is None:
                        ref_min = std_range["min"]
                    if ref_max is None:
                        ref_max = std_range["max"]
                    if not unit:
                        unit = std_range["unit"]
                
                return LabResult(
                    test_name=test_name,
                    value=value,
                    unit=unit,
                    reference_min=ref_min,
                    reference_max=ref_max
                )
        
        return None
    
    def determine_status(self, result: LabResult) -> tuple:
        """Determine status and severity of a result."""
        if result.reference_min is None or result.reference_max is None:
            return "unknown", "none"
        
        value = result.value
        min_val = result.reference_min
        max_val = result.reference_max
        
        if min_val <= value <= max_val:
            return "normal", "none"
        
        # Calculate deviation percentage
        if value < min_val:
            deviation = (min_val - value) / min_val if min_val > 0 else 0
            if deviation > 0.5:
                return "low", "severe"
            elif deviation > 0.2:
                return "low", "moderate"
            else:
                return "low", "mild"
        else:  # value > max_val
            deviation = (value - max_val) / max_val if max_val > 0 else 0
            if deviation > 0.5:
                return "high", "severe"
            elif deviation > 0.2:
                return "high", "moderate"
            else:
                return "high", "mild"
    
    def generate_explanation(self, result: LabResult) -> str:
        """Generate patient-friendly explanation."""
        explanations = {
            "white blood cell count": {
                "normal": "A white blood cell count within the normal range indicates that the immune system is functioning normally.",
                "low": "A low white blood cell count may indicate decreased immunity, so it is recommended to consult a doctor.",
                "high": "A high white blood cell count may indicate infection or inflammation."
            },
            "red blood cell count": {
                "normal": "The red blood cell count is normal and the blood's oxygen-carrying capacity is good.",
                "low": "The red blood cell count is low, anemia may be present, and further examination is recommended.",
                "high": "A high red blood cell count may indicate hemoconcentration or other conditions."
            },
            "hemoglobin": {
                "normal": "The hemoglobin level is normal and the blood's oxygen-carrying function is good.",
                "low": "Low hemoglobin may indicate symptoms of anemia, such as fatigue and weakness.",
                "high": "High hemoglobin may indicate dehydration or an increase in red blood cells."
            },
            "platelet count": {
                "normal": "The platelet count was normal and the coagulation function was good.",
                "low": "Low platelet count may affect coagulation function and requires attention.",
                "high": "A high platelet count may increase the risk of blood clots."
            },
            "total cholesterol": {
                "normal": "Total cholesterol levels are within the normal range and blood lipids are well controlled.",
                "low": "Total cholesterol is low, so you need to pay attention to nutritional balance.",
                "high": "Total cholesterol is on the high side. It is recommended to reduce the intake of high-fat foods and increase exercise."
            },
            "LDL cholesterol": {
                "normal": "LDL (bad cholesterol) is well controlled.",
                "high": "Elevated low-density lipoprotein is a risk factor for cardiovascular disease. It is recommended to improve diet and exercise."
            },
            "HDL cholesterol": {
                "normal": "HDL (good cholesterol) levels are good.",
                "low": "HDL is low, so it is recommended to increase aerobic exercise to protect cardiovascular health.",
                "high": "High-density lipoprotein is high and has a protective effect on cardiovascular disease."
            },
            "Triglycerides": {
                "normal": "Triglyceride levels were normal.",
                "high": "Triglycerides are on the high side. It is recommended to reduce sugar and fat intake and control weight."
            },
            "alanine aminotransferase": {
                "normal": "Liver function indicators were normal.",
                "high": "A high alanine aminotransferase may indicate liver cell damage, and further examination of liver function is recommended."
            },
            "aspartate aminotransferase": {
                "normal": "Liver function indicators were normal.",
                "high": "Elevated aspartate aminotransferase may indicate liver or myocardial damage."
            },
            "Creatinine": {
                "normal": "Renal function indicators were normal.",
                "high": "High creatinine may indicate decreased kidney function, and it is recommended to consult a nephrologist."
            },
            "uric acid": {
                "normal": "Uric acid levels are normal.",
                "high": "High uric acid may increase the risk of gout. It is recommended to drink more water and reduce high purine foods."
            },
            "fasting blood glucose": {
                "normal": "Blood sugar levels are normal.",
                "high": "If fasting blood sugar is high, there may be abnormal glucose metabolism. It is recommended to control the diet and review."
            },
            "Glycated hemoglobin": {
                "normal": "Glycated hemoglobin is normal, and blood sugar has been well controlled in the past 3 months.",
                "high": "High glycosylated hemoglobin indicates recent poor blood sugar control."
            },
        }
        
        test_explanations = explanations.get(result.test_name, {
            "normal": f"{result.test_name} is within normal range.",
            "low": f"{result.test_name} is on the low side.",
            "high": f"{result.test_name} is on the high side."
        })
        
        return test_explanations.get(result.status, test_explanations.get("normal", ""))
    
    def generate_recommendation(self, result: LabResult) -> str:
        """Generate health recommendations."""
        recommendations = {
            "total cholesterol": {
                "high": "Recommendation: Reduce animal fat intake, eat more fruits and vegetables, and exercise at least 150 minutes of moderate intensity per week."
            },
            "LDL cholesterol": {
                "high": "Recommendation: Limit the intake of saturated fat, choose healthy oils such as olive oil, and monitor blood lipids regularly."
            },
            "Triglycerides": {
                "high": "Recommendations: Control refined sugar and sweets, limit alcohol consumption, and increase aerobic exercise."
            },
            "alanine aminotransferase": {
                "high": "Recommendations: Avoid drinking alcohol, not abusing drugs, review liver function, and perform liver ultrasound if necessary."
            },
            "uric acid": {
                "high": "Recommendation: Drink more than 2000ml of water every day, and eat less high-purine foods such as seafood, animal offal, and thick broth."
            },
            "fasting blood glucose": {
                "high": "Suggestions: Control the amount of staple food, choose low-glycemic index foods, exercise appropriately after meals, and review regularly."
            },
        }
        
        test_recs = recommendations.get(result.test_name, {})
        return test_recs.get(result.status, "")
    
    def interpret(self, input_text: str) -> List[LabResult]:
        """Interpret lab results from input text."""
        results = []
        
        # Split by lines and common separators
        lines = re.split(r'[\n,;，；]', input_text)
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            result = self.parse_lab_line(line)
            if result:
                # Determine status and severity
                result.status, result.severity = self.determine_status(result)
                # Generate explanation
                result.explanation = self.generate_explanation(result)
                # Generate recommendation
                result.recommendation = self.generate_recommendation(result)
                results.append(result)
        
        return results
    
    def format_output(self, results: List[LabResult]) -> str:
        """Format results as patient-friendly output."""
        if not results:
            return "A valid test result could not be recognized, please check the input format."
        
        output_lines = ["=== Interpretation of test results ==="]
        
        for r in results:
            # Status emoji
            status_emoji = {
                "normal": "✅",
                "low": "⚠️",
                "high": "⚠️",
                "critical": "🚨",
                "unknown": "❓"
            }.get(r.status, "❓")
            
            # Status text
            status_text = {
                "normal": "normal",
                "low": "On the low side",
                "high": "On the high side",
                "critical": "critical",
                "unknown": "unknown"
            }.get(r.status, "unknown")
            
            ref_range = ""
            if r.reference_min is not None and r.reference_max is not None:
                ref_range = f" (Ref: {r.reference_min}-{r.reference_max} {r.unit})"

            output_lines.append(f"{status_emoji} {r.test_name}: {r.value} {r.unit}{ref_range}")
            output_lines.append(f"   Status: {status_text}")
            output_lines.append(f"   Interpretation: {r.explanation}")
            if r.recommendation:
                output_lines.append(f"   {r.recommendation}")
            output_lines.append("")
        
        output_lines.append(self.disclaimer)
        return "\n".join(output_lines)
    
    def to_dict(self, results: List[LabResult]) -> List[Dict[str, Any]]:
        """Convert results to dictionary format."""
        return [asdict(r) for r in results]


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Lab Result Interpretation Tool")
    parser.add_argument("--file", "-f", help="Input file containing lab results")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    interpreter = LabResultInterpreter()
    
    if args.interactive:
        print("Test Results Interpretation Tool - Interactive Mode")
        print("Enter the test results (one per line, or separated by commas), enter 'quit' to exit")
        print("Example: Total cholesterol: 5.8 mmol/L (Reference: 3.1-5.7)")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("Please enter the test results:").strip()
                if user_input.lower() in ["quit", "exit", "q"]:
                    break
                if not user_input:
                    continue
                
                results = interpreter.interpret(user_input)
                print(interpreter.format_output(results))
            except KeyboardInterrupt:
                print("goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            results = interpreter.interpret(content)
            
            if args.json:
                print(json.dumps(interpreter.to_dict(results), ensure_ascii=False, indent=2))
            else:
                print(interpreter.format_output(results))
        except FileNotFoundError:
            print(f"Error: File not found {args.file}")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        # Read from stdin
        print("Test result interpretation tools")
        print("How to use:")
        print("python main.py --interactive #Interactive mode")
        print("python main.py --file lab.txt # Read from file")
        print("echo 'Total cholesterol: 5.8' | python main.py # From standard input")
        print("Please enter the test results (Ctrl+D to end):")
        
        try:
            content = sys.stdin.read()
            if content.strip():
                results = interpreter.interpret(content)
                print(interpreter.format_output(results))
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
