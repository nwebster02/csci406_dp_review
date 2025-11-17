import subprocess
import sys
import json
from typing import List, Dict, Any, Tuple
import os
import tempfile
from pathlib import Path

class TestCaseGrader:
    def __init__(self, code_file: str, timeout: int = 5):
        """
        Initialize the grader with a Python code file.
        
        Args:
            code_file: Path to the Python file to test
            timeout: Maximum execution time per test case in seconds
        """
        self.code_file = code_file
        self.timeout = timeout
        self.results = []
        
    def run_test_case(self, input_data: str, expected_output: str, 
                      test_name: str = None) -> Dict[str, Any]:
        """
        Run a single test case.
        
        Args:
            input_data: Input to pass to the program (via stdin)
            expected_output: Expected output from the program
            test_name: Optional name for the test case
            
        Returns:
            Dictionary containing test results
        """
        try:
            # Run the Python file with the input
            result = subprocess.run(
                [sys.executable, self.code_file],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            actual_output = result.stdout.strip()
            expected_output = expected_output.strip()
            
            passed = actual_output == expected_output
            
            test_result = {
                'test_name': test_name or f'Test {len(self.results) + 1}',
                'passed': passed,
                'input': input_data,
                'expected_output': expected_output,
                'actual_output': actual_output,
                'stderr': result.stderr if result.stderr else None,
                'return_code': result.returncode
            }
            
            self.results.append(test_result)
            return test_result
            
        except subprocess.TimeoutExpired:
            test_result = {
                'test_name': test_name or f'Test {len(self.results) + 1}',
                'passed': False,
                'input': input_data,
                'expected_output': expected_output,
                'actual_output': None,
                'error': f'Timeout: Execution exceeded {self.timeout} seconds',
                'return_code': None
            }
            self.results.append(test_result)
            return test_result
            
        except Exception as e:
            test_result = {
                'test_name': test_name or f'Test {len(self.results) + 1}',
                'passed': False,
                'input': input_data,
                'expected_output': expected_output,
                'actual_output': None,
                'error': str(e),
                'return_code': None
            }
            self.results.append(test_result)
            return test_result
    
    def run_multiple_tests(self, test_cases: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Run multiple test cases.
        
        Args:
            test_cases: List of dictionaries with 'input', 'expected_output', and optional 'name'
            
        Returns:
            List of test results
        """
        self.results = []
        for test_case in test_cases:
            self.run_test_case(
                input_data=test_case.get('input', ''),
                expected_output=test_case.get('expected_output', ''),
                test_name=test_case.get('name')
            )
        return self.results
    
    def print_summary(self):
        """Print a summary of all test results."""
        if not self.results:
            print("No tests have been run yet.")
            return
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        
        print("\n" + "="*60)
        print(f"TEST SUMMARY: {passed}/{total} tests passed")
        print("="*60)
        
        for result in self.results:
            status = "✓ PASS" if result['passed'] else "✗ FAIL"
            print(f"\n{status}: {result['test_name']}")
            
            if not result['passed']:
                print(f"  Input: {repr(result['input'])}")
                print(f"  Expected: {repr(result['expected_output'])}")
                print(f"  Got: {repr(result['actual_output'])}")
                
                if result.get('error'):
                    print(f"  Error: {result['error']}")
                if result.get('stderr'):
                    print(f"  Stderr: {result['stderr']}")
        
        print("\n" + "="*60)
        print(f"Score: {passed}/{total} ({100*passed/total:.1f}%)")
        print("="*60 + "\n")
    
    def get_score(self) -> Tuple[int, int]:
        """
        Get the score as (passed, total).
        
        Returns:
            Tuple of (number_passed, total_tests)
        """
        if not self.results:
            return (0, 0)
        passed = sum(1 for r in self.results if r['passed'])
        return (passed, len(self.results))
    
    def load_tests_from_directory(self, test_dir: str, 
                                   input_pattern: str = "*.in",
                                   output_pattern: str = "*.out") -> List[Dict[str, str]]:
        """
        Load test cases from a directory containing input and output files.
        
        Expected structure:
        - Input files: test1.in, test2.in, etc.
        - Output files: test1.out, test2.out, etc.
        
        Or use custom patterns like:
        - input_*.txt / output_*.txt
        - *.input / *.output
        
        Args:
            test_dir: Directory containing test files
            input_pattern: Glob pattern for input files (default: "*.in")
            output_pattern: Glob pattern for output files (default: "*.out")
            
        Returns:
            List of test case dictionaries
        """
        test_dir_path = Path(test_dir)
        
        if not test_dir_path.exists():
            raise FileNotFoundError(f"Test directory not found: {test_dir}")
        
        # Find all input files
        input_files = sorted(test_dir_path.glob(input_pattern))
        
        if not input_files:
            raise ValueError(f"No input files found matching pattern '{input_pattern}' in {test_dir}")
        
        test_cases = []
        
        for input_file in input_files:
            # Determine the corresponding output file
            # Try to match based on the base name
            base_name = input_file.stem  # filename without extension
            
            # Try to find matching output file
            output_file = None
            
            # Method 1: Replace input extension with output extension
            # e.g., test1.in -> test1.out
            ext_input = input_file.suffix
            ext_output = Path(output_pattern).suffix
            
            if ext_output:  # If output pattern has an extension
                potential_output = input_file.with_suffix(ext_output)
                if potential_output.exists():
                    output_file = potential_output
            
            # Method 2: Look for files with same base name
            if not output_file:
                output_files = list(test_dir_path.glob(output_pattern))
                for out_file in output_files:
                    if out_file.stem == base_name:
                        output_file = out_file
                        break
            
            if not output_file or not output_file.exists():
                print(f"Warning: No matching output file found for {input_file.name}, skipping...")
                continue
            
            # Read input and output
            try:
                with open(input_file, 'r') as f:
                    input_data = f.read()
                
                with open(output_file, 'r') as f:
                    expected_output = f.read()
                
                test_cases.append({
                    'name': base_name,
                    'input': input_data,
                    'expected_output': expected_output
                })
                
            except Exception as e:
                print(f"Error reading test files {input_file.name}/{output_file.name}: {e}")
                continue
        
        return test_cases
    
    def run_tests_from_directory(self, test_dir: str,
                                  input_pattern: str = "*.in",
                                  output_pattern: str = "*.out") -> List[Dict[str, Any]]:
        """
        Load and run all test cases from a directory.
        
        Args:
            test_dir: Directory containing test files
            input_pattern: Glob pattern for input files (default: "*.in")
            output_pattern: Glob pattern for output files (default: "*.out")
            
        Returns:
            List of test results
        """
        test_cases = self.load_tests_from_directory(test_dir, input_pattern, output_pattern)
        
        if not test_cases:
            print("No valid test cases found!")
            return []
        
        print(f"Found {len(test_cases)} test case(s)")
        return self.run_multiple_tests(test_cases)


# Example usage
if __name__ == "__main__":
    # Check if dp.py exists
    if not os.path.exists('dp.py'):
        print("Error: dp.py not found in the current directory!")
        print("\nPlease ensure dp.py exists before running the grader.")
        sys.exit(1)
    
    # Check if tests directory exists
    test_dir = 'tests'
    if not os.path.exists(test_dir):
        print(f"Error: '{test_dir}' directory not found!")
        print(f"\nPlease create a '{test_dir}' directory with test files:")
        print("  tests/test1.in  - input for test 1")
        print("  tests/test1.out - expected output for test 1")
        print("  tests/test2.in  - input for test 2")
        print("  tests/test2.out - expected output for test 2")
        print("  ...")
        sys.exit(1)
    
    print("=" * 60)
    print("GRADING dp.py")
    print("=" * 60)
    
    # Create grader instance for dp.py
    grader = TestCaseGrader('dp.py', timeout=5)
    
    # Run tests from directory
    print(f"\nLoading tests from '{test_dir}/' directory...")
    results = grader.run_tests_from_directory(test_dir)
    
    if not results:
        print("\nNo test cases were run. Please check your test directory.")
        sys.exit(1)
    
    # Print summary
    grader.print_summary()
    
    # Get score
    passed, total = grader.get_score()
    print(f"Final Score: {passed}/{total} ({100*passed/total:.1f}%)")