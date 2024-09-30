import sys
import os
import requests
import json
import random
import pandas as pd

class Coze:
    def __init__(self,
                 bot_id=None,
                 api_token=None,
                 user_id="default_user",
                 max_chat_rounds=3,
                 stream=False,
                 history=None,
                 conversation_id=None):
        self.bot_id = bot_id
        self.api_token = api_token
        self.user_id = user_id
        self.history = history if history is not None else []
        self.max_chat_rounds = max_chat_rounds
        self.stream = stream
        self.conversation_id = conversation_id or self.generate_conversation_id()
        self.url = 'https://api.coze.com/open_api/v2/chat'
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Host': 'api.coze.com',
            'Connection': 'keep-alive'
        }

    @staticmethod
    def generate_conversation_id():
        return str(random.randint(100000000000, 999999999999))

    @classmethod
    def build_messages(cls, history=None):
        messages = []
        history = history if history else [] 
        for prompt, response in history:
            pair = [{"role": "user", "content": prompt, "content_type": "text"},
                    {"role": "assistant", "content": response}]
            messages.extend(pair)
        return messages

    @staticmethod
    def get_response(messages):
        dfmsg = pd.DataFrame(messages)
        dftool = dfmsg.loc[dfmsg['type'] == 'function_call']
        for content in dftool['content']:
            info = json.loads(content)
            s = 'call function: ' + str(info['name']) + '; args =' + str(info['arguments'])
            print(s, file=sys.stderr)
        dfans = dfmsg.loc[dfmsg['type'] == 'answer']
        if len(dfans) > 0:
            response = ''.join(dfans['content'].tolist())
        else:
            response = ''
        return response

    def chat(self, query, stream=False):
        data = {
            "conversation_id": self.conversation_id,
            "bot_id": self.bot_id,
            "user": self.user_id,
            "query": query,
            "stream": stream,
            "chat_history": self.build_messages(self.history)
        }
        json_data = json.dumps(data)
        response = ""

        try:
            result = requests.post(self.url, headers=self.headers, 
                                   data=json_data, stream=data["stream"])

            if result.status_code == 200:
                if not data["stream"]:
                    dic = json.loads(result.content.decode('utf-8'))
                    if 'messages' in dic:
                        response = self.get_response(dic['messages'])
                    else:
                        response = "Sorry, I didn't understand the response from the server."
                else:
                    messages = []
                    for line in result.iter_lines():
                        if not line:
                            continue
                        try:
                            line = line.decode('utf-8')
                            line = line[5:] if line.startswith('data:') else line
                            dic = json.loads(line)
                            if dic['event'] == 'message':
                                messages.append(dic['message'])
                            if 'messages' in dic:
                                response = self.get_response(messages)
                        except Exception as err:
                            print(f"Error during streaming: {err}")
                            break 
            else:
                print(f"Request failed, status code: {result.status_code}")
                response = "Sorry, there was a problem with the request."

        except KeyError as e:
            print(f"KeyError: {e}")
            print(f"Full response was: {result.content.decode('utf-8')}")
            response = "Sorry, I encountered an error while processing the response."

        finally:
            result.close()

        return response

    def __call__(self, query):
        len_his = len(self.history)
        if len_his >= self.max_chat_rounds:
            self.history = self.history[len_his - self.max_chat_rounds:]
        response = self.chat(query, stream=self.stream)
        self.history.append((query, response))
        return response

    def reset(self):
        self.history = []
        self.conversation_id = self.generate_conversation_id()
        print("Conversation history reset.")
