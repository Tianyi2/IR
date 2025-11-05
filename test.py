from smells.check import Check
from parsers.cloudformation_parser import CloudFormationParser
from parsers.terraform_parser import TerraformParser
from helper.save_parsed_result import save_parsed_result
from analysis.decision_tree import DecisionTree
from analysis.dependency_graph import DependencyGraph
from analysis.condition_analysis import ConditionAnalyzer
import json
import pandas as pd
import re


def test_check():
    """Check if the check is registered correctly."""
    check = Check("security", "sec_https", "test")
    # print(check.check_message)
    print(Check.CHECKS)

def test_aws_boto3_download():
    try:
        import boto3
        # Let's use Amazon S3
        s3 = boto3.resource('s3')
        print(f"AWS boto3 is downloaded.")
    except Exception as e:
        print(f"AWS boto3 is not downloaded. Error: {e}")

def test_cloudformation_metadata_parser():
    template_path = "tests/test_templates/metadata_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    # print(template_info)
    save_parsed_result(template_info)


def test_cloudformation_parameter_parser():
    template_path = "tests/test_templates/parameter_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    # print(template_info)
    save_parsed_result(template_info)


def test_cloudformation_mapping_parser():
    template_path = "tests/test_templates/mapping_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)


def test_cloudformation_rule_parser():
    template_path = "tests/test_templates/rule_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)


def test_cloudformation_condition_parser():
    template_path = "tests/test_templates/condition_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)


def test_cloudformation_resource_condition_parser():
    template_path = "tests/test_templates/resource_condition_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)


def test_cloudformation_output_parser():
    template_path = "tests/test_templates/output_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)


def test_cloudformation_resource_reference_parser():
    template_path = "tests/test_templates/resource_reference_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)


def test_cloudformation_resource_statement_parser():
    template_path = "tests/test_templates/resource_statement.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)


def test_decision_tree_analysis():
    template_path = "data/collected_templates/template_001_alert.yaml"
    # template_path = "tests/test_templates/resource_condition_test.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)
    analysis = DecisionTree(template_info)
    analysis.analyze()
    analysis.save_condition_dependency_graph()
    # analysis.display_analysis_result()

    # Test case 1 - Duplicate conditions
    # template_path = "tests/test_templates/condition_test.yaml"
    # parser = CloudFormationParser(template_path)
    # template_info = parser.parse()
    # save_parsed_result(template_info)
    # analysis = DecisionTree(template_info)
    # analysis.analyze()
    # analysis.save_condition_dependency_graph()


def test_terraform_parser():
    template_path = "data/iac_eval/template_001.tf"
    parser = TerraformParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)


# TODO: This is a temp testing function. It should be removed later!!!
def test_cloudforamtion_parser():
    """
    Parse all CloudFormation templates in the collected_templates folder,
    perform decision tree analysis, and save both parsed results and 
    analysis to the results folder.
    """
    import os
    import glob
    from parsers.cloudformation_parser import CloudFormationParser
    from analysis.decision_tree import DecisionTree
    import json
    import datetime
    
    # Define source and destination directories
    source_dir = "data/collected_templates"
    results_dir = "results"
    analysis_dir = os.path.join(results_dir, "decision_analysis")
    
    # Ensure directories exist
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(analysis_dir, exist_ok=True)
    
    # Get all YAML/YML files (CloudFormation templates)
    template_extensions = ['*.yaml', '*.yml']
    template_files = []
    for ext in template_extensions:
        template_files.extend(glob.glob(os.path.join(source_dir, ext)))
    
    # Custom JSON encoder to handle date objects
    class CloudFormationJSONEncoder(json.JSONEncoder):
        """Custom JSON encoder to handle CloudFormation-specific data types"""
        
        def default(self, obj):
            if isinstance(obj, datetime.date):
                return obj.isoformat()
            elif isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return super().default(obj)
    
    print(f"Found {len(template_files)} CloudFormation templates to parse:")
    print("=" * 60)
    
    successful_parses = 0
    failed_parses = 0
    successful_analyses = 0
    failed_analyses = 0
    parse_results = []
    
    for i, template_path in enumerate(template_files, 1):
        template_name = os.path.basename(template_path)
        template_name_without_ext = os.path.splitext(template_name)[0]
        
        print(f"[{i}/{len(template_files)}] Processing: {template_name}")
        
        try:
            # Step 1: Parse the CloudFormation template
            parser = CloudFormationParser(template_path)
            template_info = parser.parse()
            
            if template_info is None:
                print(f"  ❌ Failed to parse {template_name} - parser returned None")
                failed_parses += 1
                parse_results.append({
                    "template_file": template_name,
                    "status": "failed",
                    "error": "Parser returned None",
                    "analysis_status": "skipped"
                })
                continue
            
            # Step 2: Save parsed template data
            output_filename = f"{template_name_without_ext}_parsed.json"
            output_path = os.path.join(results_dir, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(template_info, f, indent=2, ensure_ascii=False, cls=CloudFormationJSONEncoder)
            
            print(f"  ✅ Template parsed and saved: {output_filename}")
            successful_parses += 1
            
            # Step 3: Perform Decision Tree Analysis
            try:
                print(f"  🔍 Running decision tree analysis...")
                
                # Create decision tree analysis
                analysis = DecisionTree(template_info)
                analysis.analyze()
                
                # Save condition dependency graph with template-specific filename
                analysis_filename = f"{template_name_without_ext}_analysis.json"
                analysis_path = os.path.join(analysis_dir, analysis_filename)
                analysis.save_condition_dependency_graph(analysis_path)
                
                print(f"  ✅ Decision tree analysis completed: {analysis_filename}")
                successful_analyses += 1
                analysis_status = "success"
                
            except Exception as analysis_error:
                print(f"  ⚠️  Decision tree analysis failed: {str(analysis_error)}")
                failed_analyses += 1
                analysis_status = f"failed: {str(analysis_error)}"
            
            # Record results
            parse_results.append({
                "template_file": template_name,
                "status": "success",
                "output_file": output_filename,
                "analysis_status": analysis_status,
                "analysis_file": f"{template_name_without_ext}_analysis.json" if analysis_status == "success" else None
            })
            
        except Exception as e:
            print(f"  ❌ Error processing {template_name}: {str(e)}")
            failed_parses += 1
            successful_analyses += 1  # Don't count as failed analysis if parsing failed
            parse_results.append({
                "template_file": template_name,
                "status": "failed",
                "error": str(e),
                "analysis_status": "skipped"
            })
    
    # Save comprehensive summary
    summary = {
        "total_templates": len(template_files),
        "successful_parses": successful_parses,
        "failed_parses": failed_parses,
        "successful_analyses": successful_analyses,
        "failed_analyses": failed_analyses,
        "parse_results": parse_results,
        "timestamp": datetime.datetime.now().isoformat(),
        "analysis_directory": "results/decision_analysis"
    }
    
    summary_path = os.path.join(results_dir, "comprehensive_analysis_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, cls=CloudFormationJSONEncoder)
    
    # Print comprehensive summary
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total templates processed: {len(template_files)}")
    print(f"Successful parsing: {successful_parses}")
    print(f"Failed parsing: {failed_parses}")
    print(f"Successful analysis: {successful_analyses}")
    print(f"Failed analysis: {failed_analyses}")
    print(f"Parse success rate: {(successful_parses/len(template_files)*100):.1f}%")
    print(f"Analysis success rate: {(successful_analyses/len(template_files)*100):.1f}%")
    print(f"Overall success rate: {((successful_parses + successful_analyses)/(len(template_files)*2)*100):.1f}%")
    
    print(f"\n📁 Output directories:")
    print(f"  Parsed templates: results/")
    print(f"  Decision analysis: {analysis_dir}")
    print(f"  Summary: {summary_path}")
    
    print(f"\n🎯 Files generated:")
    print(f"  Parsed templates: {successful_parses} files")
    print(f"  Analysis files: {successful_analyses} files")
    print(f"  Summary report: comprehensive_analysis_summary.json")


def test_dependency_graph():
    template_path = "data/cloudformation_collected_templates/template_0022_AutoScalingRollingUpdates.yaml"
    parser = CloudFormationParser(template_path)
    template_info = parser.parse()
    save_parsed_result(template_info)
    analysis = DependencyGraph(template_info)
    analysis.build_graph()
    analysis.analyze()
    analysis.save_dependency_graph()
    analysis.export_graph_to_png()
    analysis.display_analysis_result()
    # analysis.print_graph()
    # analysis.display_analysis_result()


def check_tf_template_from_iac_eval_csv():
    input_csv_path = "iac_eval.csv"
    df = pd.read_csv(input_csv_path, encoding='utf-8')
    for index, row in df.iterrows():
        template_content = row['Reference output']

        if 'data "' in template_content:
            data_pattern = r'data\s+"([^"]+)"\s+"([^"]+)"\s*\{[^}]*\}'
            
            matches = re.findall(data_pattern, template_content, re.DOTALL)
            
            if matches:
                for match in matches:
                    if 'aws_ami' not in match[0] and 'aws_region' not in match[0] and 'aws_availability_zone' not in match[0] and 'aws_iam_policy_document' not in match[0]:
                        print(f"{index}: {match[0]}")


def test_condition_analysis():
    template_path = "tests/test_templates/solver_test.json"
    with open(template_path, 'r') as f:
        template_info = json.load(f)

    analysis = ConditionAnalyzer(template_info)
    result = analysis.analyze()
    print(result)




def test():
    """Main Test Function."""
    # test_check()
    # test_aws_boto3_download()
    # test_cloudformation_metadata_parser()
    # test_cloudformation_parameter_parser()
    # test_cloudformation_mapping_parser()
    # test_cloudformation_rule_parser()
    # test_cloudformation_condition_parser()
    # test_cloudformation_resource_condition_parser()
    # test_cloudformation_output_parser()
    # test_cloudformation_resource_reference_parser()
    # test_cloudformation_resource_statement_parser()
    # test_decision_tree_analysis()
    # test_terraform_parser()
    # test_cloudforamtion_parser()
    # test_dependency_graph()   # Check the evalution result of the 5k dataset and update in needed
    test_condition_analysis()
    # check_tf_template_from_iac_eval_csv()




if __name__ == "__main__":
    test()

