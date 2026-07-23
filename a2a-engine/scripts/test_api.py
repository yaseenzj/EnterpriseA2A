import httpx
import sys

def main():
    # First get token
    try:
        r1 = httpx.get("http://127.0.0.1:9006/api/v1/auth/token")
        r1.raise_for_status()
        token = r1.json()["access_token"]
    except Exception as e:
        print(f"Failed to get token: {e}")
        sys.exit(1)

    print("Got token, sending request...")
    # Now send request
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"request_text": "What is the rules for the booking conference room.. Book a conference room for 2 hours tomorrow and order 5 premium lunches"}
        r2 = httpx.post("http://127.0.0.1:9006/api/v1/orchestrate", json=payload, headers=headers)
        print(f"Status: {r2.status_code}")
        print(r2.text)
    except Exception as e:
        print(f"Failed to execute: {e}")

if __name__ == "__main__":
    main()
