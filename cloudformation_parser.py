import yaml
import json
import os
import re
import uuid
from typing import Dict, Any, List, Optional, Tuple
from helper.save_file_loaded_result import save_file_loaded_result
from config.config import CFN_TAGS, AWS_PSEUDO_PARAMETERS, SUBSTITUTION_PATTERN, AWS_PSEUDO_PARAMETERS_PATTERN, ARGUMENT_MAPPINGS, CFN_CONDITION_PREFIX, CFN_OUTPUT_PREFIX

class CloudFormationParser:
    def __init__(self, template_path: str):
        self.template_path = template_path
        self.template_content = None
        self.para_name_to_id = {}
        self.condition_name_to_id = {}
        self.resource_name_to_id = {}
    

    def parse(self) -> Optional[Dict[str, Any]]:
        """
        Parse CloudFormation template and return structured information.
        """
        # 1. Read the template file
        try:
            if not self.read_template():   # content will be stored in self.template_content
                return None
            
        except Exception as e:
            # print(f"Error parsing template: {str(e)}")
            return None

        # 2. Parse the template file
        parsed_data = self.parse_template()
            
        # 3. Return the parsed template
        return parsed_data
            
    

    def read_template(self) -> bool:
        """Read the template file content."""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as file:
                self.template_content = file.read()
            return True
        except Exception as e:
            print(f"Error reading template file: {str(e)}")
            return False


    def parse_template(self) -> Dict[str, Any]:
        """Parse the YAML/JSON template content."""
        try:
            # Custom YAML loader for CloudFormation
            class CloudFormationLoader(yaml.SafeLoader):
                pass
            
            # Add constructors for CloudFormation intrinsic functions
            def construct_cfn_tag(loader, node):
                # Extract the tag name (e.g., '!Equals' -> 'Equals')
                tag_name = node.tag[1:]  # Remove the '!' prefix
                
                if isinstance(node, yaml.ScalarNode):
                    return {tag_name: node.value}
                elif isinstance(node, yaml.SequenceNode):
                    return {tag_name: loader.construct_sequence(node)}
                elif isinstance(node, yaml.MappingNode):
                    return {tag_name: loader.construct_mapping(node)}
            
            for tag in CFN_TAGS:
                CloudFormationLoader.add_constructor(tag, construct_cfn_tag)

            # Parse YAML content using custom loader
            template_data = yaml.load(self.template_content, Loader=CloudFormationLoader)

            # Print the loaded template data
            # print(template_data)
            save_file_loaded_result(template_data)  # Save the loaded template data
            
            # Extract file information
            file_name = os.path.basename(self.template_path)
            
            # Build the parsed structure according to IR format
            parsed_data = {
                'metadata': self.extract_metadata(template_data, file_name),
                'parameters': self.extract_parameters(template_data),
                'conditions': self.extract_conditions(template_data),
                'resources': self.extract_resources(template_data),
                'outputs': self.extract_outputs(template_data),
                # 'dependency_graph': self.build_dependency_graph(template_data)
            }
            
            return parsed_data
            
        except yaml.YAMLError as e:
            # print(f"YAML parsing error: {str(e)}")
            # NOTE: Only use below line of code during evaluation.
            raise yaml.YAMLError(f"There is an error when loading the CFN template: {str(e)}")   
            return {}
        except Exception as e:  
            # print(f"Template parsing error: {str(e)}")
            # NOTE: Only use below line of code during evaluation.
            raise Exception(f"There is an error when parsing the CFN template: {str(e)}")   
            return {}
        

    def extract_metadata(self, template_data: Dict[str, Any], file_name: str) -> Dict[str, Any]:
        """Extract metadata information."""
        aws_version = template_data.get('AWSTemplateFormatVersion')
        cloud_provider = f"AWS_{aws_version}" if aws_version else "AWS"
        additional_info = self._extract_metadata_helper(template_data)
        
        return {
            'template_id': str(uuid.uuid4()),
            'template_type': 'CloudFormation',
            'cloud_service_provider': cloud_provider,
            'file_name': file_name,
            'description': template_data.get('Description', 'NA'),
            'additional_info':  additional_info if additional_info else "NA"
        }
        

    def _extract_metadata_helper(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Help to extract metadata section information as mentioned in the documentation."""
        metadata = template_data.get('Metadata', {})
        additional_info = {}

        for key, value in metadata.items():
            if key == 'AWS::CloudFormation::Interface':
                pass
            elif key == 'AWS::CloudFormation::Designer':
                pass
            else:
                additional_info[key] = value

        return additional_info


    def extract_parameters(self, template_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract parameters section."""
        parameters = []
        params = template_data.get('Parameters', {})
        
        for param_name, param_data in params.items():
            # Handle default value for CommaDelimitedList to be a list
            type = param_data.get('Type', 'String')
            if type == 'CommaDelimitedList':
                default = param_data.get('Default', 'NA').split(',')
            else:
                default = param_data.get('Default', 'NA')
                
            param_info = {
                'id': str(uuid.uuid4()),
                'name': param_name,
                'type': type,
                'default': default,
                'constraints': self.extract_constraints_helper(param_data),
                'description': param_data.get('Description', 'NA')
            }
            self.para_name_to_id[param_name] = param_info['id']   # Store the name to id mapping for later referencing
            parameters.append(param_info)

        # Extract pseudo-parameters
        parameters.extend(self.extract_pseudo_parameters(template_data))
        
        # Extract mapping parameters
        parameters.extend(self.extract_mapping_parameters(template_data))

        return parameters


    def get_pseudo_parameters_search_scope(self, template_data: Dict[str, Any]) -> str:
        """Get the search scope for pseudo-parameters."""\
        # Extract pseudo parameters only from specific sections
        sections_to_search = []
        
        # 1. Parameters section (for default values, constraints, etc.)
        if 'Parameters' in template_data:
            sections_to_search.append(str(template_data['Parameters']))
        
        # 2. Conditions section
        if 'Conditions' in template_data:
            sections_to_search.append(str(template_data['Conditions']))
        
        # 3. Resources Properties sections only
        if 'Resources' in template_data:
            for resource_name, resource_data in template_data['Resources'].items():
                if isinstance(resource_data, dict) and 'Properties' in resource_data:
                    sections_to_search.append(str(resource_data['Properties']))
        
        # 4. Outputs section
        if 'Outputs' in template_data:
            sections_to_search.append(str(template_data['Outputs']))

        if 'Rules' in template_data:
            sections_to_search.append(str(template_data['Rules']))
        
        return sections_to_search

    
    def extract_pseudo_parameters(self, template_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract pseudo-parameters (${AWS::XXX} format) from the entire template.
        These are CloudFormation built-in parameters that don't need to be defined in Parameters section.
        """
        pseudo_params = []
        pseudo_param_names = set()
        
        # Convert template to string to search for ${xxx} patterns
        template_str = self.get_pseudo_parameters_search_scope(template_data)
        
        # Find all ${xxx} patterns
        # matches = re.findall(SUBSTITUTION_PATTERN, template_str)
        matches = re.findall(AWS_PSEUDO_PARAMETERS_PATTERN, "\n".join(template_str))
        # matches.extend(ref_matches)
        
        for match in matches:
            if match in AWS_PSEUDO_PARAMETERS and match not in pseudo_param_names:
                pseudo_param_names.add(match)
                
                param_info = {
                    'id': str(uuid.uuid4()),
                    'name': match,
                    'type': 'pseudo-parameter',
                    'default': 'NA',
                    'constraints': 'NA',
                    'description': "NA"
                }
                self.para_name_to_id[match] = param_info['id']
                pseudo_params.append(param_info)
        
        return pseudo_params
    

    def extract_mapping_parameters(self, template_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract mapping parameters."""
        mappings = template_data.get('Mappings', {})
        mapping_parameters = []

        for mapping_name, mapping_data in mappings.items():
            default = {mapping_name: mapping_data} if mapping_data else "NA"
                      
            param_info = {
                'id': str(uuid.uuid4()),
                'name': mapping_name,
                'type': 'mapping',
                'default': default,
                'constraints': "NA",
                'description': "NA"
            }
            self.para_name_to_id[mapping_name] = param_info['id'] 
            mapping_parameters.append(param_info)

        return mapping_parameters


    def extract_constraints_helper(self, param_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameter constraints."""
        constraints = {}
        
        if 'AllowedValues' in param_data:
            constraints['allowed_values'] = param_data['AllowedValues']

        if 'AllowedPattern' in param_data:
            constraints['allowed_pattern'] = param_data['AllowedPattern']
        
        if 'MinValue' in param_data:
            constraints['min_value'] = param_data['MinValue']
        
        if 'MaxValue' in param_data:
            constraints['max_value'] = param_data['MaxValue']
        
        if 'MinLength' in param_data:
            constraints['min_length'] = param_data['MinLength']
        
        if 'MaxLength' in param_data:
            constraints['max_length'] = param_data['MaxLength']
        
        return "NA" if not constraints else constraints
    

    def extract_conditions(self, template_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract conditions section."""
        output = []
        rules = template_data.get('Rules', {})
        conditions = template_data.get('Conditions', {})
        output = self.extract_rules_helper(output, rules)
        output = self.extract_conditions_helper(output, conditions)
        return output


    def extract_rules_helper(self, outputs: List, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract the Rules section in the CloudFormation template into the conditions section in the IR."""
        for rule_name, rule_data in rules.items():
            rule_name = f"{CFN_CONDITION_PREFIX}{rule_name}"
            # TODO: Handle the intrinsic function in the rule condition
            rule_condition = rule_data.get('RuleCondition', True)
            
            assertions = rule_data.get('Assertions', [])
            
            # Handle multiple assertions - constraint becomes an array
            constraints = []
            descriptions = []
            ruled_para = []
            depend_para = []
            
            for assertion in assertions:
                # Extract Assert and AssertDescription from each assertion
                assert_value = assertion.get('Assert', "NA")
                assert_desc = assertion.get('AssertDescription', "NA")
                
                constraints.append(assert_value)
                descriptions.append(assert_desc)
                
                # Extract parameters from constraint if it is a dictionary (Intrinsic Function)
                if isinstance(assert_value, dict):
                    ruled_para.extend(self._extract_refs_from_dict(assert_value))
            
            # Extract parameters from RuleCondition
            if isinstance(rule_condition, dict):
                depend_para.extend(self._extract_refs_from_dict(rule_condition))
            
            ruled_para = [self.para_name_to_id[para] for para in set(ruled_para)] if ruled_para else "NA"
            depend_para = [self.para_name_to_id[para] for para in set(depend_para)] if depend_para else "NA"

            rule_info = {
                'id': str(uuid.uuid4()),
                'name': rule_name,
                'condition': rule_condition,
                'ruled_para': ruled_para,
                'constraint': constraints if constraints else "NA",
                'description': descriptions if descriptions else "NA",
                'depend_para': depend_para,
                'depend_cond': "NA"
            }
            outputs.append(rule_info)
        return outputs


    def extract_conditions_helper(self, outputs: List, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract the Conditions section in the CloudFormation template into the conditions section in the IR."""
        # Register the condition name to id mapping in case the condition is not listed in sequence.
        for condition_name, condition_data in conditions.items():
            condition_name = f"{CFN_CONDITION_PREFIX}{condition_name}"
            self.condition_name_to_id[condition_name] = str(uuid.uuid4())

        for condition_name, condition_data in conditions.items():
            condition_name = f"{CFN_CONDITION_PREFIX}{condition_name}"
            # Extract parameters from Condition
            depend_para = []
            if isinstance(condition_data, dict):
                depend_para.extend(self._extract_refs_from_dict(condition_data))
            depend_para = [self.para_name_to_id[para] for para in set(depend_para)] if depend_para else "NA"

            # Extract condition dependencies
            depend_cond = []
            if isinstance(condition_data, dict):
                depend_cond = self._extract_condition_refs_from_dict(condition_data)
            depend_cond = [self.condition_name_to_id[cond] for cond in depend_cond if cond in self.condition_name_to_id] if depend_cond else "NA"

            condition_info = {
                'id': self.condition_name_to_id[condition_name],
                'name': condition_name,
                'condition': condition_data,
                'ruled_para': "NA",
                'constraint': "NA",
                'description': "NA",
                'depend_para': depend_para,
                'depend_cond': depend_cond
            }
            outputs.append(condition_info)
        return outputs


    def _extract_condition_refs_from_dict(self, data: Dict[str, Any]) -> List[str]:
        """
        Helper function to extract condition references from condition data.
        Looks for 'Condition' key in dictionaries and extracts the condition names.
        """
        condition_refs = []
        
        def extract_condition_refs_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'Condition':
                        value = f"{CFN_CONDITION_PREFIX}{value}"   # Add prefix to the condition name
                        # Extract the condition name
                        if isinstance(value, str):
                            condition_refs.append(value)
                        # elif isinstance(value, list):
                        #     # Handle cases where Condition might be a list
                        #     for item in value:
                        #         if isinstance(item, str):
                        #             condition_refs.append(item)
                    elif isinstance(value, (dict, list)):
                        extract_condition_refs_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_condition_refs_recursive(item)
        
        extract_condition_refs_recursive(data)
        return condition_refs


    def _extract_refs_from_dict(self, data: Dict[str, Any]) -> List[str]:
        """
        Helper function to extract parameter/resource references from normal or nested dictionaries (dictionary is like {'Ref': 'name'}).
        The choice of recursive is because the parameter can be nested in a dictionary which loaded from intrinsic functions.
        """
        refs = []
        
        def extract_refs_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():   # As !Ref: name will be loaded as a dictionary like {'Ref': 'name'}
                    if key == 'Ref' or key == 'Fn::Ref':
                        refs.append(value)
                    elif key == 'GetAtt' or key == 'Fn::GetAtt':
                        # GetAtt can be ['ResourceName', 'Attribute'] or 'ResourceName.Attribute'
                        if isinstance(value, list) and len(value) > 0:
                            refs.append(value[0])  # Extract just the resource name
                        elif isinstance(value, str):
                            refs.append(value.split('.')[0])  # Extract resource name before the dot
                    elif key == 'FindInMap' or key == 'Fn::FindInMap':
                        if isinstance(value, list) and len(value) > 0:
                            refs.append(value[0])  # Extract just the MapName from [MapName, TopLevelKey, SecondLevelKey ]
                        for item in value[1:]:  # Handle case when pseudo-parameters are used in the key such as !FindInMap [RegionMap, !Ref "AWS::Region", AMI]
                            extract_refs_recursive(item)
                    elif key == 'Sub' or key == 'Fn::Sub':
                        if isinstance(value, list) and len(value) > 0:   # Note: We are assuming the IaC template follows the syntax of !Sub.
                            # Get all references name from the string
                            matches = re.findall(SUBSTITUTION_PATTERN, value[0])
                            # Handle case when the reference name is not the name of referencing element. Such as !Sub ["Hello ${id}", {"id": !Ref "parameter/resource name"}]
                            for key, value in value[1].items():
                                if key in matches:
                                    extract_refs_recursive(value)
                                    matches.remove(key)
                            # Handle case when the reference name does not present in the list. Such as !Sub ["Hello ${id} ${AWS::StackName}", {"id": !Ref "parameter/resource name"}]
                            for match in matches:
                                if len(match.split(".")) > 1:   # Handle the edge case of resource references ${MyInstance.PublicIp}
                                    match = match.split(".")[0]
                                refs.append(match)
                        # !Sub "Hello ${AWS::StackName}" or !Sub ["Hello ${AWS::StackName}", {...}]
                        elif isinstance(value, str):
                            # Extract parameter references from the string
                            matches = re.findall(SUBSTITUTION_PATTERN, value)
                            for match in matches:
                                if len(match.split(".")) > 1:   # Handle the edge case of resource references ${MyInstance.PublicIp}
                                    match = match.split(".")[0]
                                refs.append(match)
                    elif key == 'Join' or key == 'Fn::Join':
                        # !Join [",", ["Hello", !Ref MyParam]]
                        if isinstance(value, list) and len(value) > 1:
                            join_items = value[1]  # The second element contains the items to join
                            if isinstance(join_items, list):
                                for item in join_items:
                                    if isinstance(item, dict):
                                        # Check for Ref, GetAtt, etc.
                                        extract_refs_recursive(item)  # Remove assignment - function works by side effect
                                    elif isinstance(item, str):
                                        # Handle string literals in Join - they don't contain references
                                        pass
                            elif isinstance(join_items, dict):   # Handle case when the join items is a list type parameter
                                extract_refs_recursive(join_items)
                    elif isinstance(value, (dict, list, str)):
                        extract_refs_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_refs_recursive(item)
            elif isinstance(obj, str):
                # Handle case of use of Pseudo-parameters in string
                matches = re.findall(AWS_PSEUDO_PARAMETERS_PATTERN, obj)
                if matches:
                    refs.extend(matches)
        
        extract_refs_recursive(data)
        return refs


    def filter_non_cfn_resources(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out non-CloudFormation resources."""
        res = template_data.get('Resources', {})
        new_res = {}
        for resource_name, resource_data in res.items():
            if isinstance(resource_data, list):
                continue
            elif resource_data.get('Type', 'NA') == 'NA':   # If there is not type for the resource
                continue
            else:
                type = str(resource_data.get('Type'))
                if type.startswith('Rain::'):
                    continue
                new_res[resource_name] = resource_data
        return new_res


    def extract_resources(self, template_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract resources section"""
        resources = []
        res = template_data.get('Resources', {})
       
        # Filter out non-CloudFormation resources such as Rain and For::Each
        # TODO: Handle the For::Each resources in later version
        res = self.filter_non_cfn_resources(template_data)
        if not res:
            return resources

        # Assign id before extracting resources
        for resource_name, resource_data in res.items():
            self.resource_name_to_id[resource_name] = str(uuid.uuid4())
        
        for resource_name, resource_data in res.items():
            # Extract individual properties
            properties_data = resource_data.get('Properties', {})
            arguments = self.extract_resource_arguments(resource_data)
            property_units = self.extract_resource_properties(properties_data)

            # Get overall resource references (for backward compatibility)
            # Note: This can be optimized by extracting references from properties_data instead of resource_data
            # resource_refs, parameter_refs = self.find_references(resource_data.get('Properties', {}))

            # Extract condition dependencies
            # depend_conditions = []
            # if resource_data.get('Condition'):
            #     depend_conditions.append(self.condition_name_to_id[resource_data.get('Condition')]) 
            # for property in property_units:
            #     temp_conditions = property.get('depend_conditions')
            #     if temp_conditions != "NA":
            #         depend_conditions.extend(temp_conditions)

            # If dependencies are manually specified, add it to the depend_conditions
            # if resource_data.get('DependsOn'):
                # Note the value can be a list or string
                # pass

            # print(resource_data)
            resource_info = {
                'id': self.resource_name_to_id[resource_name],
                'name': resource_name,
                'type': resource_data.get('Type', 'NA'),
                'properties': property_units,
                'arguments': arguments,
                # 'resource_refs': resource_refs if resource_refs else "NA",
                # 'parameter_refs': parameter_refs if parameter_refs else "NA",
                # 'depend_conditions': depend_conditions
            }
            resources.append(resource_info)
        return resources


    def extract_resource_arguments(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the resource attributes (arguments)"""
        if not resource_data:
            return "NA"
        arguments = {}
        for key, value in resource_data.items():
            if key == 'Condition':
                value = f"{CFN_CONDITION_PREFIX}{value}"   # Add prefix to the condition name
            if key in ARGUMENT_MAPPINGS['cloudformation']:
                key = ARGUMENT_MAPPINGS['cloudformation'][key]
                arguments[key] = value
        return arguments if arguments else "NA"
    

    def extract_resource_properties(self, properties_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract individual properties from resource properties data.
        Each property becomes a separate unit with its own dependencies.
        """
        property_units = []
        
        if not properties_data or not isinstance(properties_data, dict):   # If properties_data is not a dictionary or is an empty dictionary
            return "NA"
        
        for prop_name, prop_value in properties_data.items():
            # Find references in this specific property
            resource_refs, parameter_refs = self.find_references({prop_name: prop_value})
            
            # Check for condition dependencies in this property
            depend_conditions = self._extract_condition_refs_from_property(prop_value)
            depend_conditions = [self.condition_name_to_id[cond] for cond in depend_conditions if cond in self.condition_name_to_id] if depend_conditions else "NA"

            property_unit = {
                'name': prop_name,
                'value': prop_value,
                'resource_refs': resource_refs if resource_refs else "NA",
                'parameter_refs': parameter_refs if parameter_refs else "NA",
                'depend_conditions': depend_conditions
            }
            property_units.append(property_unit)
        
        return property_units


    def _extract_condition_refs_from_property(self, prop_value: Any) -> List[str]:
        """
        Extract condition references from a property value.
        Looks for !If, !Condition, and other condition-related intrinsic functions.
        """
        condition_refs = []
        
        def extract_conditions_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'If':
                        # !If [condition, true_value, false_value]
                        if isinstance(value, list) and len(value) > 0:
                            condition_name = value[0]
                            if isinstance(condition_name, str):
                                condition_refs.append(f"{CFN_CONDITION_PREFIX}{condition_name}")
                            extract_conditions_recursive(value[1])
                            extract_conditions_recursive(value[2])
                    elif isinstance(value, (dict, list)):   # TODO: Not sure if the list is needed for all this type of functions.
                        extract_conditions_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_conditions_recursive(item)
        
        extract_conditions_recursive(prop_value)
        return condition_refs


    def find_references(self, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Find resources that reference this resource with comprehensive reference detection.
        """
        resource_refs = []
        parameter_refs = []
        
        for data_name, data_value in data.items():
            if isinstance(data_value, (dict, list)):
                references = self._extract_refs_from_dict(data_value)
            elif isinstance(data_value, str):
                # Handle case of use of Pseudo-parameters in string
                matches = re.findall(AWS_PSEUDO_PARAMETERS_PATTERN, data_value)
                if matches:
                    references = matches
                else:
                    continue
            else:
                continue
            
            temp_resource_refs, temp_parameter_refs = self._extract_parameter_and_resource_refs(references)
            resource_refs.extend(temp_resource_refs)
            parameter_refs.extend(temp_parameter_refs)

        return resource_refs, parameter_refs


    def extract_outputs(self, template_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract outputs section"""
        outputs = []
        out = template_data.get('Outputs', {})
        if not out:
            return outputs
        
        for output_name, output_data in out.items():
            # TODO: Handle the Fn::ForEach outputs in later version
            if output_name.startswith('Fn::ForEach::'):
                continue
            output_pure_data = {k:v for k,v in output_data.items() if k != "Export"}
            source_resource, source_parameter = self.find_references(output_pure_data)

            export_name_info = self._extract_export_name_helper(output_data.get('Export', "NA"))
            
            depend_condition = []
            direct_condition = output_data.get('Condition', '')   # If the condition is not specified, it will be an empty string to avoid trigger the if statement
            if direct_condition:
                direct_condition = f"{CFN_CONDITION_PREFIX}{direct_condition}"
                depend_condition.append(self.condition_name_to_id[direct_condition])   # Change the condition name to id
            
            # Fomulate the value of the output
            value = {}
            value['value'] = output_data.get('Value', "NA")
            value['depend_conditions'] = "NA"
            if_depend_conditions = self._extract_condition_refs_from_property(output_data.get('Value', "NA"))
            if if_depend_conditions:
                value['depend_conditions'] = [self.condition_name_to_id[cond] for cond in if_depend_conditions if cond in self.condition_name_to_id]
            
            output_info = {
                'id': str(uuid.uuid4()),  
                'name': f"{CFN_OUTPUT_PREFIX}{output_name}",
                'description': output_data.get('Description', 'NA'),
                'value': value,
                'source_resource': source_resource if source_resource else "NA",
                'source_parameter': source_parameter if source_parameter else "NA",
                'export_name': export_name_info,
                'depend_conditions': depend_condition if depend_condition else "NA"
            }
            outputs.append(output_info)
        
        return outputs
    

    def _extract_export_name_helper(self, data: Dict[str, Any]):
        """
        Extract export name dependencies for Sub and Join intrinsic functions.
        Returns a dictionary with 'value' and 'depend_para' keys.
        This function is actually also handling the Sub and Join intrinsic functions.
        """
        if data == 'NA':
            return "NA"
        
        depend_elements = []      
        depend_conditions = []
        
        for export_element in data.values():    
            depend_elements.extend(self._extract_refs_from_dict(export_element))
            depend_conditions.extend(self._extract_condition_refs_from_property(export_element))

        depend_resource, depend_para = self._extract_parameter_and_resource_refs(depend_elements)
        
        depend_conditions = [self.condition_name_to_id[cond] for cond in depend_conditions if cond in self.condition_name_to_id] if depend_conditions else "NA"
        return {
            'name': data.get('Name', 'NA'),
            'depend_para': depend_para,
            'depend_resource': depend_resource if depend_resource else "NA",
            'depend_conditions': depend_conditions
        }


    def _extract_parameter_and_resource_refs(self, references: Any):
        parameter_refs = []
        resource_refs = []
        for reference in references:
            if self.resource_name_to_id.get(reference):
                resource_refs.append(self.resource_name_to_id[reference])
            elif self.para_name_to_id.get(reference):
                parameter_refs.append(self.para_name_to_id[reference])

        return resource_refs, parameter_refs
    

    # def contains_reference(self, resource: Dict[str, Any], target: str) -> bool:
    #     """Check if a resource contains a reference to the target"""
    #     import json
    #     resource_str = json.dumps(resource)
    #     return f'"{target}"' in resource_str or f"'{target}'" in resource_str
    

    # def find_parameter_refs(self, resource_data: Dict[str, Any]) -> List[str]:
    #     """Find parameter references in resource properties"""
    #     import json
    #     resource_str = json.dumps(resource_data)
    #     # Simple parameter reference detection - could be enhanced
    #     # This is a basic implementation that looks for Ref patterns
    #     return []
    

    # def build_dependency_graph(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
    #     """Build dependency graph between resources"""
    #     # TODO: Implement dependency graph building
    #     # This would analyze DependsOn, Ref, GetAtt, etc.
    #     return {
    #         'nodes': [],
    #         'edges': [],
    #         'metadata': 'Dependency graph not yet implemented'
    #     }