from helper_functions.data_class import DataHandler

import requests


WANTED_KEYS = [
                "session_type",
                "date_start",
                "country_name",
                "location",
            ]

def create_data_object() -> dict:
    data = DataHandler(WANTED_KEYS)
    response = data.make_request("https://api.openf1.org/v1/sessions?session_type=Race&year=2026")
    print(response)

    
if __name__ == "__main__":
    print("test")