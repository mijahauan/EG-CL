import unittest
import os

def suite():
    """
    Discovers all tests in the 'tests' subdirectory and returns a test suite.
    """
    # Start discovery in the 'tests' subdirectory
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir='tests', pattern='test_*.py')
    return suite

if __name__ == '__main__':
    # Change to the script's directory to ensure correct discovery
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    runner = unittest.TextTestRunner(verbosity=2)
    test_suite = suite()
    result = runner.run(test_suite)

    # Exit with a non-zero status code if tests failed
    if not result.wasSuccessful():
        exit(1)