from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseAnalysis(ABC):
    def __init__(self, ir: Dict[str, Any]):
        self.ir = ir
    
    @abstractmethod
    def analyze(self) -> Any:
        """Perform the analysis and return results"""
        pass
    
    @abstractmethod
    def display_analysis_result(self) -> None:
        """Helper method to display the analysis result"""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Helper method to get metadata from IR"""
        return self.ir.get('metadata', {})
    
    def get_resources(self) -> List[Dict[str, Any]]:
        """Helper method to get resources from IR"""
        return self.ir.get('resources', [])
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        """Helper method to get parameters from IR"""
        return self.ir.get('parameters', [])

    def get_conditions(self) -> List[Dict[str, Any]]:
        """Helper method to get conditions from IR"""
        return self.ir.get('conditions', [])

    def get_outputs(self) -> List[Dict[str, Any]]:
        """Helper method to get outputs from IR"""
        return self.ir.get('outputs', [])

