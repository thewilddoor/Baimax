import sys
import os
import requests
import json
import random
import pandas as pd

class Coze:
    def __init__(self,
                 bot_id,
                 api_token,
                 user_id="default_user",
                 max_chat_rounds=3,
                 stream=False,
                 history=None,
                 conversation_id=None):
        """
        Initializes the Coze bot instance.

        Parameters:
        - bot_id (str): The unique identifier for your bot.
        - api_token (str): Your API token for authentication.
        - user_id (str): The user's unique identifier.
        - max_chat_rounds (int): The maximum number of chat rounds to keep in history.
        - stream (bool): Whether to use streaming responses.
        - history (list): The chat history.
        - conversation_id (str): The conversation identifier.
        """
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
            'Connection': 'keep-alive'
        }

    @staticmethod
    def generate_conversation_id():
        """
        Generates a random conversation ID.
        """
        return str(random.randint(100000000000, 999999999999))

    @staticmethod
    def build_messages(history):
        """
        Builds the message history in the required format.

        Parameters:
        - history (list): A list of (prompt, response) tuples.

        Returns:
        - messages (list): A list of message dictionaries.
        """
        messages = []
        for prompt, response in history:
            messages.append({
                "role": "user",
                "content": prompt,
                "content_type": "text"
            })
            messages.append({
                "role": "assistant",
                "content": response,
                "content_type": "text"
            })
        return messages

    @staticmethod
    def get_response(messages):
        """
        Extracts the assistant's response from the messages.

        Parameters:
        - messages (list): A list of message dictionaries.

        Returns:
        - response (str): The assistant's response.
        """
        response_parts = []
        for message in messages:
            if message.get('role') == 'assistant':
                response_parts.append(message.get('content', ''))
        response = ''.join(response_parts)
        return response.strip()

    def chat(self, query):
        """
        Sends a chat message to the Coze Bot API and returns the response.

        Parameters:
        - query (str): The user's input message.

        Returns:
        - response (str): The assistant's response.
        """
        # Limit the chat history to the maximum allowed rounds
        if len(self.history) > self.max_chat_rounds:
            self.history = self.history[-self.max_chat_rounds:]

        # Build the payload
        data = {
            "conversation_id": self.conversation_id,
            "bot_id": self.bot_id,
            "user": self.user_id,
            "query": query,
            "stream": self.stream,
            "chat_history": self.build_messages(self.history)
        }

        response_text = ""

        try:
            result = requests.post(
                self.url,
                headers=self.headers,
                json=data,
                stream=self.stream
            )

            if result.status_code == 200:
                if not self.stream:
                    result_json = result.json()
                    if 'messages' in result_json:
                        response_text = self.get_response(result_json['messages'])
                    else:
                        response_text = "I'm sorry, I didn't receive a proper response."
                else:
                    # Handle streaming responses
                    messages = []
                    for line in result.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith('data:'):
                                decoded_line = decoded_line[5:].strip()
                            try:
                                message_json = json.loads(decoded_line)
                                if message_json.get('event') == 'message':
                                    messages.append(message_json.get('message', {}))
                            except json.JSONDecodeError:
                                continue
                    response_text = self.get_response(messages)
            else:
                print(f"Request failed with status code: {result.status_code}", file=sys.stderr)
                response_text = "I'm sorry, there was an error processing your request."
        except requests.exceptions.RequestException as e:
            print(f"Request exception: {e}", file=sys.stderr)
            response_text = "I'm sorry, I couldn't reach the server."
        finally:
            result.close()

        # Update the history
        self.history.append((query, response_text))
        return response_text

    def __call__(self, query):
        """
        Enables the class instance to be called like a function.

        Parameters:
        - query (str): The user's input message.

        Returns:
        - response (str): The assistant's response.
        """
        return self.chat(query)

    def reset(self):
        """
        Resets the conversation history and generates a new conversation ID.
        """
        self.history = []
        self.conversation_id = self.generate_conversation_id()
        print("Conversation history has been reset.")
