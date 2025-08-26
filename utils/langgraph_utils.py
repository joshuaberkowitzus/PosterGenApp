"""LangGraph utilities"""

import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import json
import json_repair

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic  
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from langchain_community.callbacks.manager import get_openai_callback
from tenacity import retry, stop_after_attempt, wait_exponential

from src.state.poster_state import ModelConfig

load_dotenv()


def create_model(config: ModelConfig):
    """create chat model from config"""
    if config.provider == 'openai':
        openai_kwargs = {
            'model_name': config.model_name,
            'temperature': config.temperature,
            'max_tokens': config.max_tokens,
            'api_key': os.getenv('OPENAI_API_KEY')
        }
        base_url = os.getenv('OPENAI_BASE_URL')
        if base_url:
            openai_kwargs['base_url'] = base_url
            
        return ChatOpenAI(**openai_kwargs)
    elif config.provider == 'anthropic':
        anthropic_kwargs = {
            'model': config.model_name,
            'temperature': config.temperature,
            'max_tokens': config.max_tokens,
            'api_key': os.getenv('ANTHROPIC_API_KEY')
        }
        base_url = os.getenv('ANTHROPIC_BASE_URL')
        if base_url:
            anthropic_kwargs['base_url'] = base_url
            
        return ChatAnthropic(**anthropic_kwargs)
    elif config.provider == 'google':
        google_kwargs = {
            'model': config.model_name,
            'temperature': config.temperature,
            'max_output_tokens': config.max_tokens,
            'google_api_key': os.getenv('GOOGLE_API_KEY')
        }
        base_url = os.getenv('GOOGLE_BASE_URL')
        if base_url:
            google_kwargs['base_url'] = base_url
            
        return ChatGoogleGenerativeAI(**google_kwargs)
    else:
        raise ValueError(f"unsupported provider: {config.provider}")


class LangGraphAgent:
    """langgraph agent wrapper"""
    
    def __init__(self, system_msg: str, config: ModelConfig):
        self.system_msg = system_msg
        self.config = config
        self.model = create_model(config)
        self.history = [SystemMessage(content=system_msg)]
    
    def reset(self):
        """reset conversation"""
        self.history = [SystemMessage(content=self.system_msg)]
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def step(self, message: str) -> 'AgentResponse':
        """process message and return response"""
        # check if message is json with image data
        try:
            msg_data = json.loads(message)
            if isinstance(msg_data, list) and any("image_url" in item for item in msg_data):
                # vision model call
                return self._step_vision(msg_data)
        except:
            pass
        
        # regular text call
        self.history.append(HumanMessage(content=message))
        
        # keep conversation window
        if len(self.history) > 10:
            self.history = [self.history[0]] + self.history[-9:]
        
        # get response with token tracking
        input_tokens, output_tokens = 0, 0
        try:
            if self.config.provider == 'openai':
                with get_openai_callback() as cb:
                    response = self.model.invoke(self.history)
                    input_tokens = cb.prompt_tokens or 0
                    output_tokens = cb.completion_tokens or 0
            else:
                response = self.model.invoke(self.history)
                # estimate tokens for non-openai
                input_tokens = len(message.split()) * 1.3
                output_tokens = len(response.content.split()) * 1.3
        except Exception as e:
            print(f"model call failed: {e}")
            input_tokens = len(message.split()) * 1.3
            output_tokens = 100
            raise
        
        self.history.append(response)
        
        return AgentResponse(response.content, input_tokens, output_tokens)
    
    def _step_vision(self, messages: List[Dict]) -> 'AgentResponse':
        """handle vision model calls"""
        # convert to proper format
        content = []
        for msg in messages:
            if msg.get("type") == "text":
                content.append({"type": "text", "text": msg["text"]})
            elif msg.get("type") == "image_url":
                content.append({
                    "type": "image_url",
                    "image_url": msg["image_url"]
                })
        
        human_msg = HumanMessage(content=content)
        
        # get response
        input_tokens, output_tokens = 0, 0
        try:
            if self.config.provider == 'openai':
                with get_openai_callback() as cb:
                    response = self.model.invoke([self.history[0], human_msg])
                    input_tokens = cb.prompt_tokens or 0
                    output_tokens = cb.completion_tokens or 0
            else:
                response = self.model.invoke([self.history[0], human_msg])
                # estimate tokens
                input_tokens = 200  # rough estimate for image
                output_tokens = len(response.content.split()) * 1.3
        except Exception as e:
            print(f"vision model call failed: {e}")
            raise
        
        return AgentResponse(response.content, input_tokens, output_tokens)


class AgentResponse:
    """agent response with token tracking"""
    def __init__(self, content: str, input_tokens: int, output_tokens: int):
        self.content = content
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


def extract_json(response: str) -> Dict[str, Any]:
    """extract json from model response"""
    
    # find json code block
    start = response.find("```json")
    end = response.rfind("```")
    
    if start != -1 and end != -1 and end > start:
        json_content = response[start + 7:end].strip()
    else:
        json_content = response.strip()
    
    try:
        return json_repair.loads(json_content)
    except Exception as e:
        raise ValueError(f"failed to parse json: {e}")


def load_prompt(path: str) -> str:
    """load prompt template from file"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read() 