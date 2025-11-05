import json
import datetime
from typing import Dict, Any


class CloudFormationJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle CloudFormation-specific data types"""
    
    def default(self, obj):
        if isinstance(obj, datetime.date):
            # Convert date back to ISO format string
            return obj.isoformat()
        elif isinstance(obj, datetime.datetime):
            # Convert datetime back to ISO format string
            return obj.isoformat()
        return super().default(obj)


def main():
    pass


def save_parsed_result(parsed_result: Dict[str, Any]):
    """
    Save the parsed result to a JSON file named 'parser_result.json'
    
    Args:
        parsed_result: Dictionary containing the parsed result data
    """
    try:
        with open('parser_result.json', 'w', encoding='utf-8') as f:
            json.dump(parsed_result, f, indent=2, ensure_ascii=False, cls=CloudFormationJSONEncoder)
        print("Parsed result saved successfully to 'parser_result.json'")
    except Exception as e:
        print(f"Error saving parsed result: {e}")


if __name__ == "__main__":
    main()