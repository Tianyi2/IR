# Register all common CloudFormation tags (used in the parser to load the template without causing error)
CFN_TAGS = ['!Ref', '!Sub', '!GetAtt', '!Join', '!Select', '!Split', '!Equals', '!If',
            '!FindInMap', '!GetAZs', '!Base64', '!Cidr', '!Transform', '!ImportValue',
            '!Not', '!And', '!Or', '!Condition', '!ForEach', '!ValueOf', '!Rain::Embed', '!Rain::Module']

# AWS pseudo-parameters
AWS_PSEUDO_PARAMETERS = ['AWS::StackName', 'AWS::Region', 'AWS::AccountId', 'AWS::NoValue',
                         'AWS::Partition', 'AWS::URLSuffix', 'AWS::StackId', 'AWS::NotificationARNs']

# Substitution pattern
SUBSTITUTION_PATTERN = r'\$\{([^}]+)\}'

# AWS pseudo-parameters pattern
AWS_PSEUDO_PARAMETERS_PATTERN = r'AWS::[A-Za-z0-9]+'

# Define resource attributes and meta-argument mappings
# TODO: Update regularly
ARGUMENT_MAPPINGS = {
    # IaC language: argument name: name in the IR
    'cloudformation': {
        'Condition': 'condition',
        'DependsOn': 'depends_on',
        'CreationPolicy': 'creation_policy',
        'UpdatePolicy': 'update_policy',
        'DeletionPolicy': 'deletion_policy',
        'UpdateReplacePolicy': 'update_replace_policy',
    },
    'terraform': {
        'count': 'count',
        'for_each': 'for_each',
        'depends_on': 'depends_on',
        'provider': 'provider',
        'lifecycle': 'lifecycle',
        'connection': 'connection',
        'provisioner': 'provisioner',
    }
}

TERRAFORM_PROVIDERS_RESOURCE_NAME = {"aws": "aws", "azurerm": "azure", "google": "google cloud platform"}

# The below prefix will be used to prefix the condition name in the IR, e.g. Cond.IsProduction to mitgate the risk of naming conflict (resource name, parameter name, etc.)
CFN_CONDITION_PREFIX = "Cond."
CFN_OUTPUT_PREFIX = "Out."

DEPENDENCY_GRAPH_EDGE_TYPE = {
    "condition-existence": "condition-existence",   # The condition that constraint the existence of the node
    "condition-property": "condition-property",     # The property of the condition that constraint the existence of the node
}