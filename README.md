## A Unified Intermediate Representation for Infrastructure as code
This project is used to transform IaC templates into an intermediate representation. The IR can be used as a in-context learning strategy for LLMs to understand the IaC template better and generate a more compliant one. The IR can also be used to create smell detectors which each smell only need to be implemented once and applied to all supporting IaC languages.

### About the files
file_loaded_result.json: A given IaC template will be loaded to python data structures and the file stores how an IaC template will be represented in python.  
parser_result.json: The file stores the intermediate representation of an IaC template.
dependency_graph.json: The raw data of the dependency graph which generated with the parser_result.json.
dependency_graph.png: The image form of the dependency graph (generated with graphviz)

### Support infrastructure as code language
1. CloudFormation
2. Terraform


### Future update
1. Support more IaC languages (Pulumi, Azure Resource Manager, Bicep)