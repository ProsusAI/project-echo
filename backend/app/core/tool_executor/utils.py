from typing import Any, Dict, List

parallel_tool_name = "multi_tool_use.parallel"


def flatten_parallel(tool_name: str, tool_args: Dict[str, Any]) -> List[Dict[str, Any]]:
    if tool_name != parallel_tool_name:
        return [{"tool_name": tool_name, "tool_args": tool_args}]
    result = []
    tool_uses: List[Dict[str, Any]] = tool_args.get("tool_uses", [])
    for tool_use in tool_uses:
        tool_name = tool_use["recipient_name"].replace("functions.", "")
        tool_args = tool_use["parameters"]
        result.append({"tool_name": tool_name, "tool_args": tool_args})
    return result

def escape_markdown_special_characters(text):
    """
    Escapes special characters for Markdown in the given string.
    
    Args:
    text (str): The input string that needs special characters escaped for Markdown.
    
    Returns:
    str: The input string with special Markdown characters escaped.
    """
    special_characters = [
        '\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!', '|'
    ]
    
    # Escape each special character by preceding it with a backslash
    for char in special_characters:
        text = text.replace(char, '\\' + char)
    
    return text

def escape_markdown_ad_fields(dict_list):
    keys_to_replace = ["title", "description"]
    for item in dict_list:
        for key in keys_to_replace:
            item[key] = escape_markdown_special_characters(item[key])
    
    return dict_list
