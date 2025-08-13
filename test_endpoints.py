#!/usr/bin/env python
"""Test script for ASC 842 terms acceptance endpoints"""

import requests
import json

base_url = "http://localhost:8080"

# Test 1: Check acceptance without session
print("Test 1: Checking acceptance without session...")
response = requests.get(f"{base_url}/api/check-acceptance")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
print()

# Test 2: Accept terms
print("Test 2: Accepting terms...")
accept_data = {
    "name": "Test User",
    "email": "test@example.com",
    "accepted": True
}
session = requests.Session()
response = session.post(f"{base_url}/api/accept-terms", 
                       json=accept_data,
                       headers={'Content-Type': 'application/json'})
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
print()

# Test 3: Check acceptance with session
print("Test 3: Checking acceptance with session...")
response = session.get(f"{base_url}/api/check-acceptance")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
print()

# Test 4: Try calculation without accepting terms (new session)
print("Test 4: Trying calculation without accepting terms...")
calc_data = {
    "lease_commencement_date": "2024-01-01",
    "monthly_payment": 5000,
    "lease_term_months": 60,
    "payment_timing": "ARREARS",
    "discount_rate": 0.05,
    "fiscal_year_end": "12/31"
}
new_session = requests.Session()
response = new_session.post(f"{base_url}/api/unified-calculation", json=calc_data)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
print()

# Test 5: Try calculation with accepted terms
print("Test 5: Trying calculation with accepted terms...")
response = session.post(f"{base_url}/api/unified-calculation", json=calc_data)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Success: {result.get('success')}")
    print(f"Lease Type: {result.get('classification', {}).get('lease_type')}")
else:
    print(f"Response: {response.json()}")

print("\nTests completed!")