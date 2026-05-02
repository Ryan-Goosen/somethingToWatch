import requests
import time

class DataHandler:

    def __init__(self, data_keys:list):
        self.keys = data_keys
        self.data = None
        self.url = None
        

    def make_request(self, url:str) -> dict:
        data = requests.get(url)
        self.data =  self.__format_data__(data.json())
        self.url = url
        return self.data

    def __format_data__(self, data:dict):
        formated_data = {}
        for key in self.keys:
            if value := data.get(key, False):
                formated_data[key] = value
            else:
                formated_data[key] = "N/A"
        
        return formated_data

    def __display_data__(self) -> None:
        # PRINT THE DATA IN TABLE FORMAT
        for item in self.data:
            pass

    def __live_updates__(self) -> None:
        # Implement an Async system that when an input is rechieved it stops the while loop
        while True:
            self.__display_data__(self.__format_data__(self.make_request(self.url)))