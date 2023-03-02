import requests
import bs4


class Bkrs:
    REQUEST_URL = 'https://bkrs.info/slovo.php?ch='

    def __init__(self, word: str):
        self.word = word.lower()
        self.url = self.REQUEST_URL + self.word

    def __get_html(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            return response.text
        except(requests.RequestException, ValueError):
            return None

    def get_words(self):
        html = self.__get_html()
        if html:
            data = bs4.BeautifulSoup(html, features="html.parser")
            if data.find("div", {"id": "no-such-word"}):
                if data.find("div", {"id": "words_morphology"}):
                    result = {"type": "error_ru", "examples": data.find("div", {"id": "words_morphology"}).get_text()}
                    return result
                else:
                    result = {"type": "error"}
                    return result
            elif data.find("div", {"id": "ch"}):
                result = {"type": "ch",
                          "user_word": data.find("div", {"id": "ch"}).get_text(),
                          "py": data.find("div", {"class": "py"}).get_text(),
                          "ru": data.find("div", {"class": "ru"}).get_text()}
                return result
            elif data.find("div", {"id": "ru_ru"}):
                result = {"type": "ru",
                          "user_word": data.find("div", {"id": "ru_ru"}).get_text(),
                          "ch": data.find("div", {"class": "ch_ru"}).get_text()
                          }
                return result
            elif data.find("span", {"id": "py_search_py"}):
                result = {"type": "py",
                          "user_word": data.find("span", {"id": "py_search_py"}).get_text(),
                          "table": data.find("table", {"id": "py_table"}).get_text()
                          }
                return result
            elif data.find("div", {"id": "ch_long"}):
                result = {"type": "ch_long",
                          "user_word": data.find("div", {"id": "ch_long"}).get_text(),
                          "table": data.find("table", {"class": "tbl_bywords"}),
                          }
                return result