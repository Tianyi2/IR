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


def save_file_loaded_result(loaded_template_data: Dict[str, Any]):
    """
    Save the loaded template data (before parsing) to a JSON file.
    This captures the raw YAML/JSON data as loaded by the CloudFormation parser.
    
    Args:
        loaded_template_data: Dictionary containing the loaded template data
    """
    try:
        # Save the loaded template data with custom encoder
        with open('file_loaded_result.json', 'w', encoding='utf-8') as f:
            json.dump(loaded_template_data, f, indent=2, ensure_ascii=False, cls=CloudFormationJSONEncoder)
        
        # print(f"Loaded template data saved successfully to 'file_loaded_result.json'")
        
    except Exception as e:
        print(f"Error saving loaded template data: {e}")


def main():
    pass


if __name__ == "__main__":
    main()