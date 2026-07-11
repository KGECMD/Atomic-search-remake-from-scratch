"""
Tools routes for Atomic Search.

Provides built-in tools like calculator, converter, translator, etc.
"""

import re
import json
from flask import Blueprint, jsonify, request, render_template
from flask_wtf.csrf import CSRFProtect

from atomic_search.config import config


bp = Blueprint("tools", __name__, url_prefix="/tools")


# Unit conversion factors
LENGTH_CONVERSIONS = {
    'm': 1, 'meter': 1, 'meters': 1,
    'km': 1000, 'kilometer': 1000, 'kilometers': 1000,
    'cm': 0.01, 'centimeter': 0.01, 'centimeters': 0.01,
    'mm': 0.001, 'millimeter': 0.001, 'millimeters': 0.001,
    'mi': 1609.344, 'mile': 1609.344, 'miles': 1609.344,
    'yd': 0.9144, 'yard': 0.9144, 'yards': 0.9144,
    'ft': 0.3048, 'foot': 0.3048, 'feet': 0.3048,
    'in': 0.0254, 'inch': 0.0254, 'inches': 0.0254,
}

WEIGHT_CONVERSIONS = {
    'kg': 1, 'kilogram': 1, 'kilograms': 1,
    'g': 0.001, 'gram': 0.001, 'grams': 0.001,
    'mg': 0.000001, 'milligram': 0.000001, 'milligrams': 0.000001,
    'lb': 0.453592, 'pound': 0.453592, 'pounds': 0.453592,
    'oz': 0.0283495, 'ounce': 0.0283495, 'ounces': 0.0283495,
    'ton': 1000, 'tons': 1000,
}

TEMP_CONVERSIONS = {
    'c': ('f', lambda c: c * 9/5 + 32),
    'f': ('c', lambda f: (f - 32) * 5/9),
    'k': ('c', lambda k: k - 273.15),
}

CURRENCY_RATES = {
    'USD': 1.0, 'EUR': 0.85, 'GBP': 0.73, 'JPY': 110.0,
    'CAD': 1.25, 'AUD': 1.35, 'CHF': 0.92, 'CNY': 6.45,
}


@bp.route("/")
def index():
    """Tools index page."""
    return render_template("tools.html")


@bp.route("/calculate", methods=["POST"])
def calculate():
    """Evaluate a mathematical expression."""
    import math
    data = request.get_json()
    expression = data.get("expression", "")
    
    try:
        # Safely evaluate mathematical expression
        # Only allow basic math operations
        allowed_chars = set('0123456789+-*/().e sqrtloginsincostanpow ')
        if all(c in allowed_chars for c in expression):
            # Replace common functions with their math equivalents
            safe_expr = expression
            safe_expr = safe_expr.replace('sqrt(', 'math.sqrt(')
            safe_expr = safe_expr.replace('log(', 'math.log10(')
            safe_expr = safe_expr.replace('sin(', 'math.sin(')
            safe_expr = safe_expr.replace('cos(', 'math.cos(')
            safe_expr = safe_expr.replace('tan(', 'math.tan(')
            safe_expr = safe_expr.replace('pow(', 'math.pow(')
            result = eval(safe_expr, {"__builtins__": {}, "math": math})
            return jsonify({"success": True, "result": float(result)})
        else:
            return jsonify({"success": False, "error": "Invalid characters"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bp.route("/convert", methods=["POST"])
def convert():
    """Convert between units."""
    data = request.get_json()
    value = float(data.get("value", 0))
    from_unit = data.get("from", "").lower()
    to_unit = data.get("to", "").lower()
    convert_type = data.get("type", "length")
    
    try:
        if convert_type == "length":
            # Convert to base unit, then to target
            if from_unit in LENGTH_CONVERSIONS and to_unit in LENGTH_CONVERSIONS:
                base_value = value * LENGTH_CONVERSIONS[from_unit]
                result = base_value / LENGTH_CONVERSIONS[to_unit]
                return jsonify({
                    "success": True,
                    "result": round(result, 6),
                    "from": from_unit,
                    "to": to_unit
                })
        
        elif convert_type == "weight":
            if from_unit in WEIGHT_CONVERSIONS and to_unit in WEIGHT_CONVERSIONS:
                base_value = value * WEIGHT_CONVERSIONS[from_unit]
                result = base_value / WEIGHT_CONVERSIONS[to_unit]
                return jsonify({
                    "success": True,
                    "result": round(result, 6),
                    "from": from_unit,
                    "to": to_unit
                })
        
        elif convert_type == "temperature":
            if from_unit in TEMP_CONVERSIONS and to_unit in TEMP_CONVERSIONS:
                target, formula = TEMP_CONVERSIONS[from_unit]
                celsius = formula(value)
                
                if to_unit == 'c':
                    result = celsius
                elif to_unit == 'f':
                    result = celsius * 9/5 + 32
                elif to_unit == 'k':
                    result = celsius + 273.15
                
                return jsonify({
                    "success": True,
                    "result": round(result, 2),
                    "from": from_unit,
                    "to": to_unit
                })
        
        return jsonify({"success": False, "error": "Invalid conversion"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bp.route("/currency", methods=["POST"])
def currency():
    """Convert between currencies."""
    data = request.get_json()
    amount = float(data.get("amount", 0))
    from_currency = data.get("from", "USD").upper()
    to_currency = data.get("to", "EUR").upper()
    
    try:
        if from_currency in CURRENCY_RATES and to_currency in CURRENCY_RATES:
            # Convert to USD first, then to target
            usd = amount / CURRENCY_RATES[from_currency]
            result = usd * CURRENCY_RATES[to_currency]
            
            return jsonify({
                "success": True,
                "result": round(result, 2),
                "from": from_currency,
                "to": to_currency,
                "amount": amount
            })
        
        return jsonify({"success": False, "error": "Currency not supported"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bp.route("/translate", methods=["POST"])
def translate():
    """Translate text (basic implementation)."""
    data = request.get_json()
    text = data.get("text", "")
    target_lang = data.get("to", "en")
    
    # Basic language detection
    lang_map = {
        'en': 'English', 'es': 'Spanish', 'fr': 'French',
        'de': 'German', 'it': 'Italian', 'pt': 'Portuguese',
        'ru': 'Russian', 'zh': 'Chinese', 'ja': 'Japanese',
        'ko': 'Korean', 'ar': 'Arabic', 'hi': 'Hindi'
    }
    
    # For demo, return the original text with a note
    return jsonify({
        "success": True,
        "original": text,
        "translated": text,
        "from": "auto",
        "to": target_lang,
        "note": "Translation requires external API. Text returned as-is."
    })


@bp.route("/weather", methods=["GET"])
def weather():
    """Get weather info (placeholder)."""
    location = request.args.get("location", "New York")
    
    return jsonify({
        "success": True,
        "location": location,
        "temperature": "N/A",
        "condition": "Check external weather API",
        "note": "Weather data requires external API integration"
    })
