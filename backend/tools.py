def format_response(response: dict) -> str:
    if isinstance(response, dict):
        if "choices" in response and response["choices"]:
            message = response["choices"][0].get("message", {})
            content = message.get("content", "")
            if content:
                return content
        if "error" in response:
            return str(response["error"])
        return str(response)
    return str(response)
