from typing import Dict, Any, List, Set, Tuple
from analysis.base_analysis import BaseAnalysis


class DependencyGraphAnalysis(BaseAnalysis):
    """
    Analysis class for dependency graphs to identify various code quality issues
    and infrastructure patterns in Infrastructure as Code templates.
    
    This class is designed to be initialized from DependencyGraph.analyze() method
    with both IR data and the built dependency graph.
    """
    
    def __init__(self, ir: Dict[str, Any], dependency_graph: Dict[str, Any]):
        """
        Initialize the analysis with IR data and dependency graph.
        
        Args:
            ir: The intermediate representation data
            dependency_graph: The built dependency graph containing nodes and edges
        """
        super().__init__(ir)  # Initialize BaseAnalysis with IR
        self.dependency_graph = dependency_graph
        self.nodes = dependency_graph.get('nodes', [])
        self.edges = dependency_graph.get('edges', [])
        self.analysis_results = {}
        
        # Build lookup structures for efficient analysis
        self._build_lookup_structures()
        
    
    def _build_lookup_structures(self):
        """Build efficient lookup structures for analysis."""
        # Node name to node mapping
        self.node_by_name = {node['name']: node for node in self.nodes}
        
        # Node type to nodes mapping
        self.nodes_by_type = {}   # {"node_type": [node1, node2, ...]}
        for node in self.nodes:
            node_type = node['type']
            if node_type not in self.nodes_by_type:
                self.nodes_by_type[node_type] = []
            self.nodes_by_type[node_type].append(node)
        
        # Build adjacency lists for graph traversal
        self.outgoing_edges = {}   # {"node_name": [node_name1, node_name2, ...]}
        self.incoming_edges = {}   # {"node_name": [node_name1, node_name2, ...]}
        
        for edge in self.edges:
            from_node = edge['from']
            to_node = edge['to']
            
            # Outgoing edges
            if from_node not in self.outgoing_edges:
                self.outgoing_edges[from_node] = []
            self.outgoing_edges[from_node].append(to_node)
            
            # Incoming edges
            if to_node not in self.incoming_edges:
                self.incoming_edges[to_node] = []
            self.incoming_edges[to_node].append(from_node)
    

    def analyze(self) -> Dict[str, Any]:
        """
        Perform all available analyses on the dependency graph.
        
        Returns:
            Dictionary containing all analysis results
        """
        # print("Starting dependency graph analysis...")
        
        # Run all analysis methods
        self.analyze_unused_parameters()
        self.analyze_unused_conditions()
        self.analyze_no_sourced_outputs()
        self.analyze_no_sourced_conditions()
        self.analyze_circular_dependencies()
        self.analyze_cascading_provision_failure()
        
        # print("Dependency graph analysis completed.")
        return self.analysis_results

    
    def analyze_unused_parameters(self):
        """
        Analyze and identify unused parameters in the dependency graph.
        
        A parameter is considered unused if:
        1. It doesn't have any outgoing edges to other nodes (except from root)
        """       
        unused_parameters = []
        
        # Get all parameter nodes
        parameters = self.nodes_by_type.get('parameter', [])
        
        for param in parameters:
            param_name = param['name']
            
            # Check if parameter has any outgoing edges (is used by other nodes)
            has_outgoing_edges = param_name in self.outgoing_edges

            if not has_outgoing_edges:   # A parameter is unused if it has no outgoing edges
                unused_parameters.append({
                    'name': param_name,
                    'id': param['id'],
                })

        # TODO: Add detailed analysis results if needed
        # result = {
        #     'unused_count': len(unused_parameters),
        #     'unused_parameters': unused_parameters,
        #     'total_parameters': len(parameters),
        #     'parameter_usage_details': parameter_usage,
        #     'usage_rate': (len(parameters) - len(unused_parameters)) / len(parameters) if parameters else 0
        # }
            
        if unused_parameters:
            self.analysis_results['unused_parameters'] = unused_parameters
    

    def analyze_unused_conditions(self):
        """
        Analyze and identify unused conditions in the dependency graph.
        
        A condition is considered unused if:
        1. It doesn't have any outgoing edges to other nodes
        """
        unused_conditions = []
        
        # Get all parameter nodes
        conditions = self.nodes_by_type.get('condition', [])
        condition_blocks = self.ir.get('conditions', [])
        
        for condition in conditions:
            condition_name = condition['name']
            
            # Check if parameter has any outgoing edges (is used by other nodes)
            has_outgoing_edges = condition_name in self.outgoing_edges

            # A condition is unused if it has no outgoing edges and is not a rule condition
            if not has_outgoing_edges and not self.check_rule_condition(condition_blocks, condition_name):  
                unused_conditions.append({
                    'name': condition_name,
                    'id': condition['id'],
                })
            
        if unused_conditions:
            self.analysis_results['unused_conditions'] = unused_conditions


    def check_rule_condition(self, condition_blocks, condition_name):
        for condition_block in condition_blocks:
            if condition_block['name'] == condition_name and condition_block['ruled_para'] != "NA":
                return True
        return False


    def analyze_no_sourced_outputs(self):
        """
        Analyze and identify outputs that don't have proper sourcing from parameters or resources.
        
        An output is considered "no sourced" if:
        1. It only has incoming edges from 'root' node
        
        This indicates the output may not be needed or properly connected to meaningful sources.
        Note that there wil not be any case when there is no incoming edges at all. Root <- Output will be existed in this case.
        """
        no_sourced_outputs = []
        
        # Get all output nodes
        outputs = self.nodes_by_type.get('output', [])
        
        for output in outputs:
            output_name = output['name']
            
            # Get all incoming edges for this output
            incoming_nodes = self.incoming_edges.get(output_name, [])
            
            for incoming_node in incoming_nodes:
                incoming_node_data = self.node_by_name.get(incoming_node)
                if incoming_node_data and incoming_node_data['type'] == "root":
                    no_sourced_outputs.append({
                        'name': output_name,
                        'id': output['id'],
                    })
                    break
        
        if no_sourced_outputs:
            self.analysis_results['no_sourced_outputs'] = no_sourced_outputs


    def analyze_no_sourced_conditions(self):
        """
        Analyze and identify conditions that don't have proper sourcing from parameters or resources.
            
        A condition is considered "no sourced" if:
        1. It only has incoming edges from 'root' node
            
        This indicates the condition may not be needed or properly connected to meaningful sources.
        Note that there wil not be any case when there is no incoming edges at all. Root <- Condition will be existed in this case.
        """
        no_sourced_conditions = []
            
        # Get all condition nodes
        conditions = self.nodes_by_type.get('condition', [])
        condition_blocks = self.ir.get('conditions', [])
            
        for condition in conditions:
            condition_name = condition['name']
                
            # Get all incoming edges for this condition
            incoming_nodes = self.incoming_edges.get(condition_name, [])
                
            for incoming_node in incoming_nodes:
                incoming_node_data = self.node_by_name.get(incoming_node)
                if incoming_node_data and incoming_node_data['type'] == "root" and not self.check_rule_condition(condition_blocks, condition_name):
                    no_sourced_conditions.append({
                        'name': condition_name,
                        'id': condition['id'],
                    })
                    break
            
        if no_sourced_conditions:
            self.analysis_results['no_sourced_conditions'] = no_sourced_conditions


    def analyze_circular_dependencies(self):
        """
        Analyze and identify circular dependencies in the dependency graph.
        
        Uses Depth-First Search (DFS) to detect cycles in the directed graph.
        A circular dependency occurs when there's a path from node A to node B 
        and a path from node B back to node A.
        
        Returns:
            List of circular dependency cycles found in the graph
        """
        circular_dependencies = []
        visited = set()
        rec_stack = set()  # Recursion stack to track nodes in current DFS path
        
        def dfs_cycle_detection(node, path):
            """
            DFS-based cycle detection using recursion stack.
            
            Args:
                node: Current node being visited
                path: Current path from start node to current node
                
            Returns:
                List of cycles found starting from this node, or None if no cycle
            """
            if node in rec_stack:
                # Found a cycle! Extract the cycle from the path
                cycle_start_index = path.index(node)
                cycle = path[cycle_start_index:] + [node]  # Complete the cycle
                return [cycle]
            
            if node in visited:
                return []  # Already processed this node
            
            # Mark current node as visited and add to recursion stack
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            cycles_found = []
            
            # Check all outgoing edges (dependencies)
            outgoing_nodes = self.outgoing_edges.get(node, [])
            for next_node in outgoing_nodes:
                cycles = dfs_cycle_detection(next_node, path.copy())
                cycles_found.extend(cycles)
            
            # Remove from recursion stack when backtracking
            rec_stack.remove(node)
            return cycles_found
        
        # Check for cycles starting from each unvisited node
        all_nodes = set(node['name'] for node in self.nodes)
        
        for node_name in all_nodes:
            if node_name not in visited:
                cycles = dfs_cycle_detection(node_name, [])
                circular_dependencies.extend(cycles)
        
        # Remove duplicate cycles (same cycle found from different starting points)
        unique_cycles = []
        seen_cycles = set()
        
        for cycle in circular_dependencies:
            # Normalize cycle by rotating to start with lexicographically smallest node
            min_index = cycle.index(min(cycle))
            normalized_cycle = cycle[min_index:] + cycle[:min_index]
            cycle_tuple = tuple(normalized_cycle)
            
            if cycle_tuple not in seen_cycles:
                seen_cycles.add(cycle_tuple)
                unique_cycles.append(cycle)
        
        # Format results with additional information
        formatted_cycles = []
        for cycle in unique_cycles:
            cycle_info = {
                'cycle': cycle,
                'cycle_length': len(cycle) - 1,  # -1 because last node repeats first
                'cycle_type': self._get_cycle_type(cycle),
                'nodes_involved': list(set(cycle[:-1]))  # Remove duplicate start/end node
            }
            formatted_cycles.append(cycle_info)
        
        if formatted_cycles:
            self.analysis_results['circular_dependencies'] = formatted_cycles


    def _get_cycle_type(self, cycle):
        """
        Determine the type of cycle based on node types involved.
        
        Args:
            cycle: List of node names forming a cycle
            
        Returns:
            String describing the cycle type
        """
        node_types = []
        for node_name in cycle[:-1]:  # Exclude the duplicate last node
            node_data = self.node_by_name.get(node_name)
            if node_data:
                node_types.append(node_data['type'])
        
        unique_types = set(node_types)
        
        if len(unique_types) == 1:
            return f"pure_{list(unique_types)[0]}_cycle"
        else:
            return f"mixed_cycle_{'_'.join(sorted(unique_types))}"


    def _get_condition_edges(self):
        """
        Get all condition edges in the dependency graph.
        """
        conditionally_gated_resources = {}
        conditionally_gated_resource_properties = {}

        for edge in self.edges:
            if edge.get('edge_type') == 'condition-existence':
                condition_name = edge['from']
                resource_name = edge['to']
                
                if condition_name not in conditionally_gated_resources:
                    conditionally_gated_resources[condition_name] = []
                conditionally_gated_resources[condition_name].append(resource_name)
            elif edge.get('edge_type') == 'condition-property':
                condition_name = edge['from']
                property_name = edge['to']
                
                if condition_name not in conditionally_gated_resource_properties:
                    conditionally_gated_resource_properties[condition_name] = []
                conditionally_gated_resource_properties[condition_name].append(property_name)
        return conditionally_gated_resources, conditionally_gated_resource_properties


    def analyze_cascading_provision_failure(self):
        """
        Analyze and identify cascading provisioning failure in the dependency graph.
        
        Uses recursive traversal to check if descendants of conditionally provisioned
        resources are properly protected by the same condition.
        """
        self.cascading_failures = []
        
        # Step 1: Find all conditionally provisioned resources
        conditionally_gated_resources, conditionally_gated_resource_properties = self._get_condition_edges()
        
        # Step 2: For each conditionally provisioned resource, recursively check descendants
        for condition_name, gated_resources in conditionally_gated_resources.items():
            condition_id = self._get_node_id_by_name(condition_name)
            
            for gated_resource in gated_resources:
                # Get immediate children of the gated resource
                children = self._get_immediate_children(gated_resource)
                
                # Recursively check each child
                for child in children:
                    self._check_cascading_failure_recursive(
                        child, 
                        condition_name, 
                        condition_id,
                        gated_resource, 
                        visited=set(),
                        conditionally_gated_resources=conditionally_gated_resources,
                        conditionally_gated_resource_properties=conditionally_gated_resource_properties
                    )
        
        if self.cascading_failures:
            self.analysis_results['cascading_provisioning_failures'] = self.cascading_failures


    def _check_cascading_failure_recursive(self, node_name, condition_name, condition_id, 
                                           gated_resource_name, visited, conditionally_gated_resources, conditionally_gated_resource_properties):
        """
        Recursively check if a node and its descendants are properly protected.
        
        Args:
            node_name: Current node being checked
            condition_name: Name of the protecting condition
            condition_id: ID of the protecting condition
            gated_resource_name: Name of the originally gated resource
            visited: Set of visited nodes to prevent infinite loops
        """
        # Prevent infinite loops
        if node_name in visited:
            return
        visited.add(node_name)
        
        # Step 1: Check if node has resource-level condition-existence protection
        if node_name in conditionally_gated_resources.get(condition_name, []):
            # Node is protected at resource level, stop recursion
            return
        
        # Step 2: Check if node has property-level condition-property protection
        if node_name in conditionally_gated_resource_properties.get(condition_name, []):
            # Node is safely protected at property level via !If, stop recursion
            return
        
        # Step 3: Node is not protected - register as cascading failure
        self.cascading_failures.append({
            'gated_resource': gated_resource_name,
            'dependent_resource': node_name,
            'condition': condition_name,
            # 'description': f"Resource '{node_name}' depends on conditionally provisioned resource '{gated_resource_name}' but is not protected by condition '{condition_name}'"
        })
        
        # Recursively check children
        children = self._get_immediate_children(node_name)
        for child in children:
            self._check_cascading_failure_recursive(
                child, condition_name, condition_id, gated_resource_name, visited, conditionally_gated_resources, conditionally_gated_resource_properties
            )


    # TODO: Apply this function to the step 2 of _check_cascading_failure_recursive
    def _has_safe_condition_property_edge(self, node_name, condition_name, condition_id, gated_resource_name):
        """
        Check if a node has property-level protection via !If that safely handles the gated resource.
        
        This checks if:
        1. There's a condition-property edge from the condition to the node
        2. The property that references the gated resource uses !If with the protecting condition
        
        Args:
            node_name: Name of the node to check
            condition_name: Name of the protecting condition
            condition_id: ID of the protecting condition
            gated_resource_name: Name of the gated resource being referenced
            
        Returns:
            True if safely protected at property level, False otherwise
        """
        # Check if there's a condition-property edge
        has_property_edge = False
        for edge in self.edges:
            if (edge.get('edge_type') == 'condition-property' and
                edge['from'] == condition_name and
                edge['to'] == node_name):
                has_property_edge = True
                break
        
        if not has_property_edge:
            return False
        
        # Get the gated resource ID
        gated_resource_id = self._get_node_id_by_name(gated_resource_name)
        if not gated_resource_id:
            return False
        
        # Find the node in IR and check its properties
        node_ir = self._find_resource_in_ir(node_name)
        if not node_ir:
            return False
        
        # Check each property
        properties = node_ir.get('properties', [])
        for prop in properties:
            # Check if this property references the gated resource
            resource_refs = prop.get('resource_refs', [])
            if isinstance(resource_refs, list) and gated_resource_id in resource_refs:
                # Check if this property has the protecting condition in depend_conditions
                depend_conditions = prop.get('depend_conditions', [])
                if isinstance(depend_conditions, list) and condition_id in depend_conditions:
                    # Property safely uses !If with the protecting condition
                    return True
        
        return False


    def _get_immediate_children(self, node_name):
        """
        Get immediate children (direct dependents) of a node.
        
        Args:
            node_name: Name of the node
            
        Returns:
            List of immediate children node names
        """
        children = []
        for edge in self.edges:
            # Skip condition-existence edges as they represent constraints, not data flow
            # if edge.get('edge_type') == 'condition-existence':
            #     continue
            
            if edge['from'] == node_name and edge['to'] != node_name:
                children.append(edge['to'])
        
        return children


    def _get_node_id_by_name(self, node_name):
        """Get node ID by node name."""
        node = self.node_by_name.get(node_name)
        return node['id'] if node else None


    def _find_resource_in_ir(self, resource_name):
        """Find a resource or output in the IR by name."""
        # Check resources
        resources = self.ir.get('resources', [])
        for resource in resources:
            if resource.get('name') == resource_name:
                return resource
        
        # Check outputs
        outputs = self.ir.get('outputs', [])
        for output in outputs:
            if output.get('name') == resource_name:
                return output
        
        return None


    def display_analysis_result(self) -> None:
        # This method will be implemented in the dependency_graph.py file
        pass
        
    
    # def get_analysis_summary(self) -> Dict[str, Any]:
    #     """
    #     Get a summary of all analysis results.
        
    #     Returns:
    #         Dictionary containing summary statistics
    #     """
    #     summary = {
    #         'total_analyses': len(self.analysis_results),
    #         'analyses_performed': list(self.analysis_results.keys())
    #     }
        
    #     # Add summary statistics for each analysis
    #     for analysis_name, results in self.analysis_results.items():
    #         if 'unused_count' in results and 'total_' in results:
    #             total_key = [k for k in results.keys() if k.startswith('total_')][0]
    #             summary[f"{analysis_name}_summary"] = {
    #                 'unused_count': results['unused_count'],
    #                 'total_count': results[total_key],
    #                 'usage_rate': results.get('usage_rate', 0)
    #             }
        
    #     return summary
    
    # def export_analysis_results(self, filename: str = "dependency_analysis_results.json") -> str:
    #     """
    #     Export analysis results to a JSON file.
        
    #     Args:
    #         filename: Name of the output file
            
    #     Returns:
    #         Path to the exported file
    #     """
    #     import json
        
    #     export_data = {
    #         'analysis_results': self.analysis_results,
    #         'summary': self.get_analysis_summary(),
    #         'graph_info': {
    #             'total_nodes': len(self.nodes),
    #             'total_edges': len(self.edges),
    #             'node_types': {node_type: len(nodes) for node_type, nodes in self.nodes_by_type.items()}
    #         }
    #     }
        
    #     with open(filename, 'w', encoding='utf-8') as f:
    #         json.dump(export_data, f, indent=2, ensure_ascii=False)
        
    #     print(f"Analysis results exported to: {filename}")
    #     return filename
