import os
os.system('color')
import re
import time
import json
import configparser
from collections import Counter

import requests
import termcolor as tc
from bs4 import BeautifulSoup
from sbvirtualdisplay import Display
from seleniumbase import SB, Driver

CONFIG = configparser.ConfigParser(interpolation=None)
CONFIG.read("./config.yaml")

class endpoint():
    def __init__(self, textColor: str = "white", backgroundColor: str = "on_blue", undetectedChrome: bool = True, headless: bool = False, ingo: bool = True):
        self.textColor = textColor
        self.bgColor = backgroundColor
        self.chromeDriver = Driver(uc=undetectedChrome, headless=headless, incognito=ingo)

        with open("./oldChat.json") as f:
            self.oldMessages = json.load(f)

        self.squad = CONFIG.get("General", "freindly")
        self.threashold = int(CONFIG.get("General", "unknownThreash"))
        self.problems = json.loads(CONFIG.get("ProgramSettings", "knownproblems"))
        self.splitList = json.loads(CONFIG.get("ProgramSettings", "splitlist"))

    def _grabSource(self, target: str = "http://127.0.0.1:8111/") -> list:
        print(tc.colored(f'Grabbing Data From Game', color=self.textColor, on_color=self.bgColor))
        try:
            self.chromeDriver.uc_open_with_reconnect(target, 3)
            source = self.chromeDriver.get_page_source()
        finally:
            self.chromeDriver.quit()
        print(tc.colored(f'Data Acquired, parsing', color=self.textColor, on_color=self.bgColor))
        parse = BeautifulSoup(source, 'html5lib')

        self.chatline = parse.find_all(class_="chat-line msg-type-system")
        with open("./oldChat.json", "wb") as f:
            f.write(str(self.chatline).encode("utf8"))

        
        newData = self.chatline[self.chatline.index(self.oldMessages[-1]) + 1:]
        newMessages: list = []
        for mes in newData:
            string = str(mes.contents[1])
            foundTerm: str = None
            for term in self.splitList:
                index = string.find(term)
                if index != -1:
                    foundTerm = term
            if foundTerm != None:
                for message in string.split(foundTerm):
                    newMessages.append(message.strip())

        self.procMessages = newMessages
        print(tc.colored(f'Parsing Complete', color=self.textColor, on_color=self.bgColor))
        return newMessages

    def _processMessages(self):
        parsed: list = []
        players: list = []

        for i in self.procMessages:
            first = str(i).find(" ")
            last = str(i).find("(")
            middle = str(i)[first:last]
            first = str(i)[0:first]
            last = str(i)[last+1:-1]

            if first != self.squad:
                if tuple((first, middle, last)) not in players:
                    players.append(tuple((first, middle, last)))
                    # print(tuple((first, middle, last)))
                parsed.append(tuple((first, middle, last)))
            # else:
                # print(tuple((first, middle, last)))

        squads: dict = {}

        for player in players:
            if player[0] not in squads.keys():
                squads[player[0]] = [player[-1]]
            else:
                temp: list = squads[player[0]]
                temp.append(player[-1])
                squads[player[0]] = temp
        
        self.detectedSquads = squads

    def _vizualize(self):
        for squad in self.detectedSquads:
            types = []
            vc = {
            "tank": 0,
            "light_tank": 0,
            "medium_tank": 0,
            "heavy_tank": 0,
            "tank_destroyer": 0,
            "spaa": 0,
            "attack_helicopter": 0,
            "utility_helicopter": 0,
            "fighter": 0,
            "assault": 0,
            "bomber": 0
            }

            # print(squads[vehicles])
            if len(self.detectedSquads[squad]) >= self.threashold:
                for vehicle in self.detectedSquads[squad]:
                    found = re.search(r'([A-Z,a-z,0-9,\-, ]+)',str(vehicle)).group().strip().replace(" ", "_")
                    if found in self.problems:
                        found = self.problems[found]

                    # print(f'{vehicles} - {found}')
                    r = requests.get(f'https://www.wtvehiclesapi.sgambe.serv00.net/api/vehicles/search/{found}')
                    if r.status_code == 200:
                        response = r.json()[0]
                        r = requests.get(f'https://www.wtvehiclesapi.sgambe.serv00.net/api/vehicles/{response}')
                        response = r.json()
                        types.append(response["vehicle_type"])
                    # else:
                    #     print(f'{squad} - {found}')
                # print(squad)
                count = Counter(types)
                ukn = 8 - sum(count.values())
                for value in count:
                    vc[value] = count[value]

                print(f'{squad[1:-1]}  |  {vc["attack_helicopter"] + vc["utility_helicopter"]}H {vc["fighter"]}F {vc["bomber"]}B {vc["spaa"]}AA {vc["medium_tank"] + vc["tank"] + vc["heavy_tank"]}MBT {vc["light_tank"] + vc["tank_destroyer"]}LT {ukn}UKN')

    def run(self):
        self._grabSource()
        self._processMessages()
        self._vizualize()

if __name__ == "__main__":
    builder = endpoint()
    builder.run()