import requests

# --- CONFIGURATION ---
APP_ID = "2777336095793629"
APP_SECRET = "f935f451236b766711e4b511b785165c"
SHORT_LIVED_USER_TOKEN = "EAAWPcdn8maABQK89nqoR3gDZBU1yHKPOkv7oyFaKHEhAxiBZC9GH3Op7tDSVAl0ZAJDM6UjVF8u5JLn2L3DWkwhuOO5H7A799K11n2J0AAfhIkzEncWcohgTJ2xud22ZCiytMCMFoErnpso0KkCgK080lxeHdL7KTWgQqNBVofEbkVjamM8A4R5hIZB3kKQmI2OgpUA5QNM6C2GW3HxBOlLX8ZB4IIxtTX1OiUArsd6Y9NuXHXhU8BL7mShHV6YjpPIyF7rihZBw2NM7AZDZD"
# ---------------------

def get_permanent_page_token():
    # 1. Exchange Short-Lived User Token for Long-Lived User Token
    exchange_url = "https://graph.facebook.com/v23.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": SHORT_LIVED_USER_TOKEN
    }
    
    try:
        resp = requests.get(exchange_url, params=params)
        data = resp.json()
        
        if "access_token" not in data:
            print("Error getting Long-Lived User Token:", data)
            return

        long_lived_user_token = data["access_token"]
        print(f"✅ Long-Lived User Token acquired (expires in ~60 days).")
        
        # 2. Get the Permanent Page Access Token
        # We query the 'accounts' endpoint to get the Pages this user manages
        accounts_url = "https://graph.facebook.com/v23.0/me/accounts"
        page_params = {
            "access_token": long_lived_user_token
        }
        
        page_resp = requests.get(accounts_url, params=page_params)
        page_data = page_resp.json()
        
        if "data" in page_data:
            print("\n👇 SELECT YOUR PAGE TOKEN BELOW 👇")
            for page in page_data["data"]:
                print(f"Page Name: {page['name']}")
                print(f"ID: {page['id']}")
                print(f"PERMANENT TOKEN: {page['access_token']}") # <--- THIS IS WHAT YOU WANT
                print("-" * 30)
        else:
            print("Error fetching pages:", page_data)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    get_permanent_page_token()