import requests
import time
import json
from rich.console import Console
from rich.table import Table

class DataHandler:

    def __init__(self, data_keys:list):
        self.keys = data_keys
        self.data = None
        self.formated_data = []
        self.url = None
        

    def make_request(self, url:str) -> dict:
        # data = requests.get(url)
        # self.data =  self.__format_data__(data.json())
        # self.url = url
        with open("./response.json", "r") as file:
            self.data = json.load(file)
        
        self.__format_data__()

    def __format_data__(self):
        temp = {}
        for key in self.keys:
            for datapoint in self.data:
                if value := datapoint.get(key, False):
                    temp[key] = value
                else:
                    temp[key] = "N/A"
            self.formated_data.append(temp)    
        

    def __display_data__(self) -> None:
        table = Table(title="My Data")
        # Add columns from keys of first dict
        for key in self.keys:
            table.add_column(key, style="cyan")

        for item in self.formated_data:
            table.add_row(*[str(item.get(k, "")) for k in self.keys])

        console = Console()
        console.print(table)

    def __live_updates__(self) -> None:
        # Implement an Async system that when an input is rechieved it stops the while loop
        while True:
            self.__display_data__(self.__format_data__(self.make_request(self.url)))