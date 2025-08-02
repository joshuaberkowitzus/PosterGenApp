"""logging utility for all LangGraph agents"""

from rich.console import Console
from rich.text import Text

console = Console()

def log(agent_name: str, level: str, message: str, max_width: int = 15):
    """
    centralized logging function for all agents
    
    args:
        agent_name: name of the agent (e.g., "parser", "color_agent")
        level: log level (e.g., "info", "warning", "error", "success")
        message: the message to log
        max_width: maximum width for the agent name padding
    """
    # clean agent name for display
    display_name = agent_name.replace("_agent", "").replace("_node", "").replace("_", " ").title()
    
    # color scheme based on level
    level_colors = {
        "info": "cyan",
        "warning": "yellow", 
        "error": "red",
        "success": "green",
        "debug": "blue"
    }
    
    level_color = level_colors.get(level.lower(), "white")
    
    # create header with fixed width
    header = Text(f"[ {display_name:^{max_width}} ]", style=f"bold {level_color}")
    body = Text(message)
    
    console.print(header, body)


def log_agent_start(agent_name: str):
    """log agent start with separator"""
    log(agent_name, "info", f"starting {agent_name}...")


def log_agent_success(agent_name: str, message: str):
    """log agent success"""
    log(agent_name, "success", f"✅ {message}")


def log_agent_error(agent_name: str, message: str):
    """log agent error"""
    log(agent_name, "error", f"❌ {message}")


def log_agent_warning(agent_name: str, message: str):
    """log agent warning"""
    log(agent_name, "warning", f"⚠️ {message}")


def log_agent_info(agent_name: str, message: str):
    """log agent info"""
    log(agent_name, "info", message)