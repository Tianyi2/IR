from cloudformation_parser import CloudFormationParser
from helper.save_parsed_result import save_parsed_result
# from parsers.terraform_parser import TerraformParser
from analysis.dependency_graph import DependencyGraph
import json
import pandas as pd
import re


def test_dependency_graph():
    template_path = "test_templates/resource_reference_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)
    analysis = DependencyGraph(template_info)
    analysis.build_graph()
    analysis.save_dependency_graph()
    analysis.export_graph_to_png()


def test():
    """Main Test Function."""
    test_dependency_graph()   # Check the evalution result of the 5k dataset and update in needed


if __name__ == "__main__":
    test()

