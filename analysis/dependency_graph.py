import uuid
import graphviz
import json
from typing import Dict, Any, List
from analysis.base_analysis import BaseAnalysis
from analysis.dependency_graph_analysis import DependencyGraphAnalysis
from config.config import CFN_CONDITION_PREFIX, DEPENDENCY_GRAPH_EDGE_TYPE


class DependencyGraph(BaseAnalysis):
    def __init__(self, ir: Dict[str, Any]):
        self.graph = {}
        self.nodes = []
        self.edges = []
        self.node_id_to_name = {}
        self.ir = ir
        self.analysis_results = {}


    def build_graph(self) -> Dict[str, Any]:
        """
        Build dependency graph from IR according to the pseudocode algorithm.
        Returns a graph with nodes and edges representing dependencies.
        """
        # Step 1: CREATE ROOT NODE
        self._generate_node(str(uuid.uuid4()), "root", "root")
        
        # Step 2: CREATE ALL NODES for all sections
        self._create_nodes()
        
        # Step 3: PROCESS CONDITIONS
        for condition in self.get_conditions():
            self._generate_edge(condition, condition.get('ruled_para', "NA"))   # The ruled_para is pointed by the condition
            is_edge_generated = False
            # Note to put or is_edge_generated at the end of the function, otherwise the _generate_edge may not be called
            is_edge_generated = self._generate_edge(condition, condition.get('depend_para', "NA")) or is_edge_generated
            is_edge_generated = self._generate_edge(condition, condition.get('depend_cond', "NA")) or is_edge_generated
            if not is_edge_generated:
                self._create_edge("root", condition["name"])

        # Step 4: PROCESS RESOURCES
        for resource in self.get_resources():
            # Handle "direct" dependencies specified in arguments
            self._handle_dependencies_in_arguments(resource)

            # Handle "indirect" dependencies specified in properties
            properties = resource.get('properties', "NA")
            is_edge_generated = False
            if properties != "NA":
                for property in properties:
                    is_edge_generated = self._generate_edge(resource, property.get('parameter_refs', "NA")) or is_edge_generated
                    is_edge_generated = self._generate_edge(resource, property.get('resource_refs', "NA")) or is_edge_generated
                    is_edge_generated = self._generate_edge(resource, property.get('depend_conditions', "NA"), edge_type=DEPENDENCY_GRAPH_EDGE_TYPE["condition-property"]) or is_edge_generated
            if not is_edge_generated:
                # Create edge from root to current resource when the resource is not depended on any other nodes
                self._create_edge("root", resource["name"])

        # Step 5: PROCESS OUTPUTS
        for output in self.get_outputs():
            is_edge_generated = False
            is_edge_generated = self._generate_edge(output, output.get('source_resource', "NA")) or is_edge_generated
            is_edge_generated = self._generate_edge(output, output.get('source_parameter', "NA")) or is_edge_generated
            if not is_edge_generated:
                # Create edge from root to current output when the output's value is not depended on any resource or parameter
                self._create_edge("root", output["name"])
            self._generate_edge(output, output.get('depend_conditions', "NA"), edge_type=DEPENDENCY_GRAPH_EDGE_TYPE["condition-existence"]) 
            self._generate_edge(output, output.get('value', "NA").get('depend_conditions', "NA"), edge_type=DEPENDENCY_GRAPH_EDGE_TYPE["condition-property"]) 
            if output.get('export_name', "NA") != "NA":
                self._generate_edge(output, output.get('export_name').get('depend_para', "NA"))
                self._generate_edge(output, output.get('export_name').get('depend_resource', "NA"))
        
        # Step 6: Form dependency_graph
        self.graph = {
            "nodes": self.nodes,
            "edges": self.edges
        }

    
    def _handle_dependencies_in_arguments(self, resource):
        """
        Handle "direct" dependencies specified in arguments.
        """
        arguments = resource.get('arguments', "NA")
        if arguments != "NA":
            if "depends_on" in arguments:
                depended_nodes = arguments.get('depends_on', "NA")
                if depended_nodes == "NA":
                    pass
                elif isinstance(depended_nodes, list):
                    for depended_node in depended_nodes:
                        self._create_edge(depended_node, resource["name"])
                else:
                    self._create_edge(depended_nodes, resource["name"])
            if "condition" in arguments:
                depended_condition_node_name = arguments.get('condition', "NA")
                if depended_condition_node_name == "NA":
                    pass
                else:
                    self._create_edge(depended_condition_node_name, resource["name"], edge_type=DEPENDENCY_GRAPH_EDGE_TYPE["condition-existence"])

    
    def _create_nodes(self):
        """
        Create nodes for all sections in the IR.
        """
        # Process parameters
        parameters = self.get_parameters()
        for param in parameters:
            # Handle edge case for AWS pseudo-parameters that the :: will cause Graphviz namespace issues
            if '::' in param["name"]:
                param["name"] = param["name"].replace('::', '.')
            self._generate_node(param["id"], param["name"], "parameter")   
            # Add edge for parameter nodes (root -> current node)
            self._create_edge("root", param["name"])
        
        # Process conditions
        conditions = self.get_conditions()
        for condition in conditions:
            self._generate_node(condition["id"], condition["name"], "condition")

        # Process resources
        resources = self.get_resources()
        for resource in resources:
            self._generate_node(resource["id"], resource["name"], "resource")
        
        # Process outputs
        outputs = self.get_outputs()
        for output in outputs:
            self._generate_node(output["id"], output["name"], "output")


    def _generate_node(self, id: str, name: str, type: str) -> Dict[str, Any]:
        """
        Generate a node from the given node information and register the node to the graph.
        """
        node = {
            "id": id,
            "name": name,
            "type": type
        }
        self.nodes.append(node)
        self.node_id_to_name[id] = name


    def _create_edge(self, from_node, to_node, edge_type="") -> Dict[str, Any]:
        """"
        Create an edge between two nodes.
        """
        self.edges.append({
            "from": from_node,
            "to": to_node,
            "edge_type": edge_type
        })


    def _generate_edge(self, node, node_dependency_section, is_ruled_para=False, edge_type=""):
        """
        Iterate the node's dependency section and generate edges between the depended nodes and the current node.
        
        Returns True if an edge is generated, False otherwise.
        """
        is_edge_generated = False
        if node_dependency_section != "NA":
            for depended_node_id in node_dependency_section:
                depended_node_name = self.node_id_to_name.get(depended_node_id, None)
                if is_ruled_para:
                    depended_node_name = "root"
                    # Change the edge of root to that parameter to current condition to that parameter
                    for edge in self.edges:
                        if edge["from"] == "root" and edge["to"] == depended_node_name:
                            edge["from"] = node["name"]
                            break
                if depended_node_name:
                    self._create_edge(depended_node_name, node["name"], edge_type)
                    is_edge_generated = True
        return is_edge_generated


    def analyze(self):
        try:    
            analyzer = DependencyGraphAnalysis(self.ir, self.graph)
            self.analysis_results = analyzer.analyze()
        except Exception as e:
            print(f"Error during dependency graph analysis: {str(e)}")
            raise Exception(f"Error during dependency graph analysis: {str(e)}")


    def save_dependency_graph(self):
        """Save the dependency graph to a file."""
        with open("dependency_graph.json", "w", encoding='utf-8') as file:
            json.dump(self.graph, file, indent=2, ensure_ascii=False)
        print(f"Dependency graph saved to dependency_graph.json")


    # TODO: May not be needed
    def print_graph(self):
        """
        Print the dependency graph in a human-readable format.
        Shows nodes grouped by type and their dependencies.
        """
        if not self.graph or not self.graph.get('nodes') or not self.graph.get('edges'):
            print("No dependency graph data available.")
            return
        
        nodes = self.graph['nodes']
        edges = self.graph['edges']
        
        # Group nodes by type for better organization
        nodes_by_type = {}
        for node in nodes:
            node_type = node['type']
            if node_type not in nodes_by_type:
                nodes_by_type[node_type] = []
            nodes_by_type[node_type].append(node)
        
        # Create a mapping from node names to their types for edge display
        node_name_to_type = {node['name']: node['type'] for node in nodes}
        
        print("=" * 60)
        print("DEPENDENCY GRAPH")
        print("=" * 60)
        
        # Display nodes grouped by type
        print("\n📋 NODES:")
        print("-" * 30)
        
        type_icons = {
            'root': '🌳',
            'parameter': '📝',
            'condition': '🔀',
            'resource': '🔧',
            'output': '📤'
        }
        
        for node_type in ['root', 'parameter', 'condition', 'resource', 'output']:
            if node_type in nodes_by_type:
                icon = type_icons.get(node_type, '📄')
                print(f"\n{icon} {node_type.upper()}S:")
                for node in nodes_by_type[node_type]:
                    print(f"  • {node['name']} (ID: {node['id'][:8]}...)")
        
        # Display dependencies
        print("\n🔗 DEPENDENCIES:")
        print("-" * 30)
        
        if not edges:
            print("  No dependencies found.")
        else:
            # Group edges by source node for better readability
            edges_by_source = {}
            for edge in edges:
                source = edge['from']
                if source not in edges_by_source:
                    edges_by_source[source] = []
                edges_by_source[source].append(edge['to'])
            
            for source, targets in edges_by_source.items():
                source_type = node_name_to_type.get(source, 'unknown')
                source_icon = type_icons.get(source_type, '📄')
                print(f"\n{source_icon} {source} ({source_type})")
                for target in targets:
                    target_type = node_name_to_type.get(target, 'unknown')
                    target_icon = type_icons.get(target_type, '📄')
                    print(f"  └─→ {target_icon} {target} ({target_type})")
        
        # Display summary statistics
        print("\n📊 SUMMARY:")
        print("-" * 30)
        print(f"Total nodes: {len(nodes)}")
        print(f"Total dependencies: {len(edges)}")
        
        # Count by type
        for node_type, type_nodes in nodes_by_type.items():
            icon = type_icons.get(node_type, '📄')
            print(f"{icon} {node_type.capitalize()}s: {len(type_nodes)}")
        
        print("=" * 60)


    def export_graph_to_png(self, filename: str = "dependency_graph", format: str = "png"):
        """
        Export the dependency graph to a PNG file using Graphviz.
        Creates a visual representation similar to Terraform's graph output.
        
        Args:
            filename: Output filename (without extension)
            format: Output format ('png', 'svg', 'pdf', 'dot')
        """
        if not self.graph or not self.graph.get('nodes') or not self.graph.get('edges'):
            print("No dependency graph data available for export.")
            return
        
        nodes = self.graph['nodes']
        edges = self.graph['edges']
        
        # Create a new directed graph
        dot = graphviz.Digraph(comment='Dependency Graph')
        dot.attr(rankdir='TB')
        dot.attr('node', shape='box', style='rounded,filled', fontname='Arial', fontsize='10', margin='0.05,0.05', pad='0.05,0.05')
        dot.attr('edge', fontname='Arial', fontsize='8')
        
        # Define colors for different node types
        type_colors = {
            'root': '#FF6B6B',      # Red
            'parameter': '#4ECDC4', # Teal
            'condition': '#45B7D1', # Blue
            'resource': '#96CEB4',  # Green
            'output': '#FFEAA7'     # Yellow
        }
        
        type_shapes = {
            'root': 'hexagon',
            'parameter': 'ellipse',
            'condition': 'diamond',
            'resource': 'box',
            'output': 'parallelogram'
        }
        
        # Add nodes to the graph
        for node in nodes:
            node_name = node['name']
            node_type = node['type']
            color = type_colors.get(node_type, '#CCCCCC')
            shape = type_shapes.get(node_type, 'box')
            
            # Create a label with type information
            label = f"{node_name}\\n({node_type})"
            
            dot.node(
                node_name,
                label=label,
                fillcolor=color,
                shape=shape,
                fontcolor='black'
            )
        
        # Add edges to the graph
        for edge in edges:
            dot.edge(edge['from'], edge['to'], color='#666666')
        
        # Render the graph
        try:
            output_path = dot.render(filename, format=format, cleanup=True)
            print(f"Graph exported to: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error exporting graph: {str(e)}")
            return None


    # TODO: Check below function, not used yet
    def export_graph_to_dot(self, filename: str = "dependency_graph"):
        """
        Export the dependency graph to a DOT file for manual Graphviz processing.
        """
        if not self.graph or not self.graph.get('nodes') or not self.graph.get('edges'):
            print("No dependency graph data available for export.")
            return
        
        nodes = self.graph['nodes']
        edges = self.graph['edges']
        
        dot_content = "digraph DependencyGraph {\n"
        dot_content += "  rankdir=TB;\n"
        dot_content += "  size=\"12,8\";\n"
        dot_content += "  node [shape=box, style=rounded,filled, fontname=Arial, fontsize=10];\n"
        dot_content += "  edge [fontname=Arial, fontsize=8];\n\n"
        
        # Add nodes
        for node in nodes:
            node_name = node['name']
            node_type = node['type']
            dot_content += f"  \"{node_name}\" [label=\"{node_name}\\n({node_type})\"];\n"
        
        dot_content += "\n"
        
        # Add edges
        for edge in edges:
            dot_content += f"  \"{edge['from']}\" -> \"{edge['to']}\";\n"
        
        dot_content += "}\n"
        
        # Write to file
        with open(f"{filename}.dot", "w") as f:
            f.write(dot_content)
        
        print(f"DOT file exported to: {filename}.dot")
        return f"{filename}.dot"

        
    def display_analysis_result(self):
        print(self.analysis_results)